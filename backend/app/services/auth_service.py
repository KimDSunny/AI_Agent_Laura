from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError

from app.services.supabase_service import create_public_supabase_client


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    access_token: str


class AuthSession:
    def __init__(
        self,
        *,
        user_id: UUID,
        access_token: str,
        refresh_token: str,
        expires_at: int | None,
    ) -> None:
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at


class AuthService:
    def create_anonymous_session(self) -> AuthSession:
        client = create_public_supabase_client()
        try:
            response = client.auth.sign_in_anonymously()
        except AuthApiError as error:
            if "disabled" in str(error).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Supabase 대시보드에서 Anonymous Sign-Ins를 켜줘.",
                ) from error
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase 익명 세션을 만들지 못했습니다.",
            ) from error

        return self._to_session(response)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        client = create_public_supabase_client()
        try:
            response = client.auth.refresh_session(refresh_token)
        except AuthApiError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="세션이 만료되었습니다. 새 세션이 필요합니다.",
            ) from error
        return self._to_session(response)

    def authenticate(self, access_token: str) -> AuthenticatedUser:
        client = create_public_supabase_client()
        try:
            response = client.auth.get_user(access_token)
        except AuthApiError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인 세션이 유효하지 않아.",
            ) from error

        if response is None or response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인 세션을 확인할 수 없어.",
            )
        return AuthenticatedUser(user_id=UUID(str(response.user.id)), access_token=access_token)

    @staticmethod
    def _to_session(response: object) -> AuthSession:
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if user is None or session is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase 세션 응답이 올바르지 않습니다.",
            )
        return AuthSession(
            user_id=UUID(str(user.id)),
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
        )


auth_service = AuthService()
