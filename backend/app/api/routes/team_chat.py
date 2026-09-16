import asyncio

from fastapi import APIRouter, Depends

from app.api.dependencies import get_repository
from app.models.chat import TeamName
from app.models.team_chat import TeamMessage, TeamMessageCreate, TeamMessagesResponse
from app.services.repository import SupabaseRepository


router = APIRouter(tags=["team-chat"])


@router.get("/team-chats/{team}/messages", response_model=TeamMessagesResponse)
async def get_team_messages(
    team: TeamName,
    repository: SupabaseRepository = Depends(get_repository),
) -> TeamMessagesResponse:
    messages = await asyncio.to_thread(repository.get_team_messages, team)
    return TeamMessagesResponse(team=team, messages=messages)


@router.post("/team-chats/{team}/messages", response_model=TeamMessage)
async def send_team_message(
    team: TeamName,
    request: TeamMessageCreate,
    repository: SupabaseRepository = Depends(get_repository),
) -> TeamMessage:
    return await asyncio.to_thread(repository.send_team_message, team, request.content)
