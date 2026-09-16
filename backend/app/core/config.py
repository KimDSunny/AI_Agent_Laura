from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PLANET Laura API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:4173,http://127.0.0.1:4173"
        )
    )
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_redirect_uri: str = (
        "http://127.0.0.1:8000/api/v1/integrations/google-calendar/callback"
    )
    google_oauth_state_secret: str | None = None
    google_token_encryption_key: str | None = None
    frontend_url: str = "http://127.0.0.1:5173"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.google.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(
            self.supabase_url
            and (self.supabase_secret_key or self.supabase_publishable_key)
        )

    @property
    def google_calendar_configured(self) -> bool:
        return bool(
            self.supabase_secret_key
            and self.google_client_id
            and self.google_client_secret
            and self.google_oauth_state_secret
            and self.google_token_encryption_key
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
