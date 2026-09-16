from fastapi import Cookie, Depends, HTTPException, status

from app.services.auth_service import AuthenticatedUser, auth_service
from app.services.repository import SupabaseRepository


def require_user(
    access_token: str | None = Cookie(default=None, alias="planet_access_token"),
) -> AuthenticatedUser:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="먼저 사용자 세션을 만들어줘.",
        )
    return auth_service.authenticate(access_token)


def get_repository(
    user: AuthenticatedUser = Depends(require_user),
) -> SupabaseRepository:
    return SupabaseRepository(user)
