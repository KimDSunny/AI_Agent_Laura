import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_repository
from app.models.actions import ActionExecuteRequest, ActionResponse
from app.services.repository import SupabaseRepository
from app.services.google_calendar_service import google_calendar_service


router = APIRouter(tags=["actions"])


@router.post("/actions/{action_id}/execute", response_model=ActionResponse)
async def execute_action(
    action_id: str,
    request: ActionExecuteRequest,
    repository: SupabaseRepository = Depends(get_repository),
) -> ActionResponse:
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자 승인이 필요해.",
        )
    if (
        repository.action_requires_calendar(action_id)
        and repository.get_google_calendar_connection() is None
    ):
        return ActionResponse(
            action_id=action_id,
            status="authorization_required",
            message="Google Calendar 권한을 한 번만 연결하면 승인한 일정을 바로 등록할게.",
            authorization_url=google_calendar_service.authorization_url(
                repository,
                resume_action_id=action_id,
            ),
        )
    message = await asyncio.to_thread(repository.execute_action, action_id)
    return ActionResponse(action_id=action_id, status="approved", message=message)


@router.post("/actions/{action_id}/decline", response_model=ActionResponse)
def decline_action(
    action_id: str,
    repository: SupabaseRepository = Depends(get_repository),
) -> ActionResponse:
    message = repository.decline_action(action_id)
    return ActionResponse(action_id=action_id, status="declined", message=message)
