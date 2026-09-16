from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from cryptography.fernet import Fernet

from app.services.auth_service import AuthenticatedUser
from app.services.google_calendar_service import GoogleCalendarService


class CalendarRepository:
    def __init__(self) -> None:
        self.user = AuthenticatedUser(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            access_token="test-access-token",
        )
        self.connection = None

    def get_google_calendar_connection(self):
        return self.connection

    def save_google_calendar_connection(self, encrypted_credentials: str, scope: str):
        self.connection = {
            "encrypted_credentials": encrypted_credentials,
            "scope": scope,
            "connected_at": "2026-09-15T00:00:00Z",
        }


def configured_settings():
    return SimpleNamespace(
        google_calendar_configured=True,
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_oauth_redirect_uri="http://127.0.0.1:8000/callback",
        google_oauth_state_secret="state-secret-with-enough-entropy",
        google_token_encryption_key=Fernet.generate_key().decode(),
    )


def test_authorization_url_uses_offline_access_and_signed_state(monkeypatch):
    service = GoogleCalendarService()
    repository = CalendarRepository()
    settings = configured_settings()
    monkeypatch.setattr(
        "app.services.google_calendar_service.get_settings", lambda: settings
    )

    authorization_url = service.authorization_url(repository)
    parameters = parse_qs(urlparse(authorization_url).query)

    assert parameters["access_type"] == ["offline"]
    assert parameters["prompt"] == ["consent"]
    assert parameters["state"][0]
    assert settings.google_client_secret not in authorization_url


def test_connect_encrypts_google_credentials(monkeypatch):
    service = GoogleCalendarService()
    repository = CalendarRepository()
    settings = configured_settings()
    monkeypatch.setattr(
        "app.services.google_calendar_service.get_settings", lambda: settings
    )
    state = service._create_state(str(repository.user.user_id))
    monkeypatch.setattr(
        service,
        "_request_json",
        lambda *args, **kwargs: {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
            "scope": "calendar.events",
        },
    )

    service.connect(repository, code="authorization-code", state_token=state)

    encrypted = repository.connection["encrypted_credentials"]
    assert "google-access-token" not in encrypted
    assert service._decrypt(encrypted)["refresh_token"] == "google-refresh-token"


def test_connect_returns_resumable_action_id(monkeypatch):
    service = GoogleCalendarService()
    repository = CalendarRepository()
    settings = configured_settings()
    monkeypatch.setattr(
        "app.services.google_calendar_service.get_settings", lambda: settings
    )
    state = service._create_state(
        str(repository.user.user_id),
        resume_action_id="00000000-0000-0000-0000-000000000099",
    )
    monkeypatch.setattr(
        service,
        "_request_json",
        lambda *args, **kwargs: {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
        },
    )

    action_id = service.connect(repository, code="authorization-code", state_token=state)

    assert action_id == "00000000-0000-0000-0000-000000000099"
