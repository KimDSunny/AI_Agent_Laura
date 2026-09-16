from time import time

from fastapi import APIRouter, Cookie, HTTPException, Response

from app.core.config import get_settings
from app.models.auth import SessionResponse
from app.services.auth_service import AuthSession, auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookies(response: Response, session: AuthSession) -> None:
    settings = get_settings()
    secure = settings.app_env == "production"
    access_max_age = max(60, (session.expires_at or int(time()) + 3600) - int(time()))
    response.set_cookie(
        "planet_access_token",
        session.access_token,
        max_age=access_max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "planet_refresh_token",
        session.refresh_token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


@router.post("/session", response_model=SessionResponse)
def ensure_session(
    response: Response,
    access_token: str | None = Cookie(default=None, alias="planet_access_token"),
    refresh_token: str | None = Cookie(default=None, alias="planet_refresh_token"),
) -> SessionResponse:
    if access_token:
        try:
            user = auth_service.authenticate(access_token)
            return SessionResponse(user_id=user.user_id)
        except HTTPException:
            pass

    if refresh_token:
        try:
            session = auth_service.refresh_session(refresh_token)
            _set_session_cookies(response, session)
            return SessionResponse(user_id=session.user_id, expires_at=session.expires_at)
        except HTTPException:
            pass

    session = auth_service.create_anonymous_session()
    _set_session_cookies(response, session)
    return SessionResponse(user_id=session.user_id, expires_at=session.expires_at)


@router.delete("/session", status_code=204)
def clear_session(response: Response) -> Response:
    response.delete_cookie("planet_access_token", path="/")
    response.delete_cookie("planet_refresh_token", path="/")
    response.status_code = 204
    return response

