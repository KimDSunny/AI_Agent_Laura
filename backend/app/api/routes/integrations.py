import asyncio
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_repository
from app.core.config import get_settings
from app.models.integrations import (
    GoogleCalendarAuthorization,
    GoogleCalendarStatus,
)
from app.services.google_calendar_service import google_calendar_service
from app.services.repository import SupabaseRepository


router = APIRouter(prefix="/integrations/google-calendar", tags=["integrations"])


@router.get("/status", response_model=GoogleCalendarStatus)
def google_calendar_status(
    repository: SupabaseRepository = Depends(get_repository),
) -> GoogleCalendarStatus:
    return google_calendar_service.status(repository)


@router.get("/connect", response_model=GoogleCalendarAuthorization)
def connect_google_calendar(
    repository: SupabaseRepository = Depends(get_repository),
) -> GoogleCalendarAuthorization:
    return GoogleCalendarAuthorization(
        authorization_url=google_calendar_service.authorization_url(repository)
    )


@router.get("/callback", response_class=RedirectResponse)
async def google_calendar_callback(
    code: str | None = Query(default=None),
    state_token: str | None = Query(default=None, alias="state"),
    error: str | None = Query(default=None),
    repository: SupabaseRepository = Depends(get_repository),
) -> RedirectResponse:
    settings = get_settings()
    if error:
        return RedirectResponse(
            f"{settings.frontend_url}?{urlencode({'calendar': 'denied'})}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not code or not state_token:
        raise HTTPException(status_code=400, detail="Google 인증 응답이 올바르지 않습니다.")
    resume_action_id = await asyncio.to_thread(
        google_calendar_service.connect,
        repository,
        code=code,
        state_token=state_token,
    )
    action_result = "none"
    if resume_action_id:
        try:
            await asyncio.to_thread(repository.execute_action, resume_action_id)
            action_result = "executed"
        except HTTPException:
            action_result = "failed"
    return RedirectResponse(
        f"{settings.frontend_url}?{urlencode({'calendar': 'connected', 'action': action_result})}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google_calendar(
    repository: SupabaseRepository = Depends(get_repository),
) -> None:
    await asyncio.to_thread(google_calendar_service.disconnect, repository)
