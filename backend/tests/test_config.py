from app.core.config import Settings


def test_url_settings_strip_surrounding_whitespace() -> None:
    settings = Settings(
        frontend_url=" https://ai.sunnywallet.app ",
        google_oauth_redirect_uri=(
            " https://ai.sunnywallet.app/api/v1/integrations/google-calendar/callback "
        ),
    )

    assert settings.frontend_url == "https://ai.sunnywallet.app"
    assert settings.google_oauth_redirect_uri == (
        "https://ai.sunnywallet.app/api/v1/integrations/google-calendar/callback"
    )
