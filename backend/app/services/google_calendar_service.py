import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.integrations import GoogleCalendarStatus
from app.services.repository import SupabaseRepository


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleCalendarService:
    def status(self, repository: SupabaseRepository) -> GoogleCalendarStatus:
        settings = get_settings()
        if not settings.google_calendar_configured:
            return GoogleCalendarStatus(configured=False, connected=False)
        connection = repository.get_google_calendar_connection()
        return GoogleCalendarStatus(
            configured=True,
            connected=connection is not None,
            connected_at=connection.get("connected_at") if connection else None,
        )

    def authorization_url(
        self,
        repository: SupabaseRepository,
        resume_action_id: str | None = None,
    ) -> str:
        settings = self._settings()
        state = self._create_state(
            str(repository.user.user_id),
            resume_action_id=resume_action_id,
        )
        parameters = {
            'client_id': settings.google_client_id,
            'redirect_uri': settings.google_oauth_redirect_uri,
            'response_type': 'code',
            'scope': CALENDAR_SCOPE,
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'prompt': 'consent',
            'state': state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(parameters)}"

    def connect(
        self,
        repository: SupabaseRepository,
        *,
        code: str,
        state_token: str,
    ) -> str | None:
        settings = self._settings()
        state_payload = self._verify_state(state_token, str(repository.user.user_id))
        token_data = self._request_json(
            GOOGLE_TOKEN_URL,
            form={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
            error_message="Google 인증 코드를 교환하지 못했어.",
        )
        if not token_data.get("refresh_token"):
            previous = repository.get_google_calendar_connection()
            if previous:
                old_credentials = self._decrypt(previous["encrypted_credentials"])
                token_data["refresh_token"] = old_credentials.get("refresh_token")
        if not token_data.get("access_token") or not token_data.get("refresh_token"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google에서 오프라인 접근 토큰을 받지 못했어. 다시 연결해줘.",
            )
        token_data["expires_at"] = self._expires_at(token_data)
        repository.save_google_calendar_connection(
            self._encrypt(token_data),
            token_data.get("scope", CALENDAR_SCOPE),
        )
        return state_payload.get("action_id")

    def disconnect(self, repository: SupabaseRepository) -> None:
        connection = repository.get_google_calendar_connection()
        if not connection:
            return
        credentials = self._decrypt(connection["encrypted_credentials"])
        token = credentials.get("refresh_token") or credentials.get("access_token")
        if token:
            try:
                self._request_json(
                    GOOGLE_REVOKE_URL,
                    form={"token": token},
                    error_message="Google 권한 해제에 실패했어.",
                    allow_empty=True,
                )
            except HTTPException:
                # 로컬 연결 정보는 지워 재사용을 막고, Google 측 해제 실패는 재연결로 복구한다.
                pass
        repository.delete_google_calendar_connection()

    def create_event(
        self,
        repository: SupabaseRepository,
        *,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        description: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        connection = repository.get_google_calendar_connection()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="먼저 Google Calendar를 연결해줘.",
            )
        credentials = self._decrypt(connection["encrypted_credentials"])
        credentials = self._refresh_if_needed(repository, credentials)
        body = {
            "summary": title,
            "description": description or "PLANET · AI Agent 로라가 등록한 일정",
            "start": {"dateTime": starts_at.isoformat(), "timeZone": "Asia/Seoul"},
            "end": {"dateTime": ends_at.isoformat(), "timeZone": "Asia/Seoul"},
        }
        if event_id:
            body["id"] = event_id
        return self._request_json(
            GOOGLE_CALENDAR_EVENTS_URL,
            json_body=body,
            bearer_token=credentials["access_token"],
            error_message="Google Calendar에 일정을 등록하지 못했어.",
            conflict_url=(
                f"{GOOGLE_CALENDAR_EVENTS_URL}/{event_id}" if event_id else None
            ),
        )

    def _refresh_if_needed(
        self,
        repository: SupabaseRepository,
        credentials: dict[str, Any],
    ) -> dict[str, Any]:
        expires_at = float(credentials.get("expires_at", 0))
        if expires_at > datetime.now(timezone.utc).timestamp() + 60:
            return credentials
        settings = self._settings()
        refreshed = self._request_json(
            GOOGLE_TOKEN_URL,
            form={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token",
            },
            error_message="Google Calendar 인증을 갱신하지 못했어.",
        )
        credentials.update(refreshed)
        credentials["expires_at"] = self._expires_at(refreshed)
        repository.save_google_calendar_connection(
            self._encrypt(credentials),
            credentials.get("scope", CALENDAR_SCOPE),
        )
        return credentials

    def _create_state(self, user_id: str, resume_action_id: str | None = None) -> str:
        settings = self._settings()
        payload = {
            "sub": user_id,
            "exp": int(datetime.now(timezone.utc).timestamp()) + 600,
            "nonce": secrets.token_urlsafe(18),
        }
        if resume_action_id:
            payload["action_id"] = resume_action_id
        encoded = self._urlsafe(json.dumps(payload, separators=(",", ":")).encode())
        signature = hmac.new(
            settings.google_oauth_state_secret.encode(), encoded.encode(), hashlib.sha256
        ).digest()
        return f"{encoded}.{self._urlsafe(signature)}"

    def _verify_state(self, state_token: str, user_id: str) -> dict[str, Any]:
        settings = self._settings()
        try:
            encoded, supplied_signature = state_token.split(".", 1)
            expected_signature = hmac.new(
                settings.google_oauth_state_secret.encode(),
                encoded.encode(),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(
                self._urlsafe(expected_signature), supplied_signature
            ):
                raise ValueError
            payload = json.loads(self._decode_urlsafe(encoded))
            if payload.get("sub") != user_id:
                raise ValueError
            if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
                raise ValueError
            return payload
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google 연결 요청이 만료됐거나 올바르지 않아. 다시 시도해줘.",
            ) from error

    def _encrypt(self, value: dict[str, Any]) -> str:
        return self._fernet().encrypt(json.dumps(value).encode()).decode()

    def _decrypt(self, value: str) -> dict[str, Any]:
        try:
            return json.loads(self._fernet().decrypt(value.encode()).decode())
        except (InvalidToken, json.JSONDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="저장된 Google 연결 정보를 읽지 못했어.",
            ) from error

    def _fernet(self) -> Fernet:
        settings = self._settings()
        try:
            return Fernet(settings.google_token_encryption_key.encode())
        except (ValueError, AttributeError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GOOGLE_TOKEN_ENCRYPTION_KEY 설정이 올바르지 않아.",
            ) from error

    @staticmethod
    def _request_json(
        url: str,
        *,
        form: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        bearer_token: str | None = None,
        error_message: str,
        allow_empty: bool = False,
        conflict_url: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        data = None
        if form is not None:
            data = urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        try:
            with urlopen(Request(url, data=data, headers=headers), timeout=15) as response:
                content = response.read()
                if not content and allow_empty:
                    return {}
                return json.loads(content.decode())
        except HTTPError as error:
            if error.code == 409 and conflict_url and bearer_token:
                return GoogleCalendarService._request_json(
                    conflict_url,
                    bearer_token=bearer_token,
                    error_message=error_message,
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_message,
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_message,
            ) from error

    @staticmethod
    def _expires_at(token_data: dict[str, Any]) -> float:
        return (
            datetime.now(timezone.utc)
            + timedelta(seconds=int(token_data.get("expires_in", 3600)))
        ).timestamp()

    @staticmethod
    def _urlsafe(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    @staticmethod
    def _decode_urlsafe(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    @staticmethod
    def _settings():
        settings = get_settings()
        if not settings.google_calendar_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Calendar 연동 설정이 아직 완료되지 않았어.",
            )
        return settings


google_calendar_service = GoogleCalendarService()
