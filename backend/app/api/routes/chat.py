import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_repository
from app.models.chat import ChatRequest, ChatResponse, ConversationResponse, TeamName
from app.services.agent_service import agent_service
from app.services.repository import SupabaseRepository


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    repository: SupabaseRepository = Depends(get_repository),
) -> ChatResponse:
    response = await agent_service.chat(request, repository=repository)
    await asyncio.to_thread(repository.save_exchange, request, response)
    return response


@router.post("/chat/stream")
async def stream_chat_message(
    request: ChatRequest,
    repository: SupabaseRepository = Depends(get_repository),
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        status_queue: asyncio.Queue[dict[str, str | None]] = asyncio.Queue()

        async def publish_status(payload: dict[str, str | None]) -> None:
            await status_queue.put(payload)

        response_task = asyncio.create_task(
            agent_service.chat(request, repository=repository, on_status=publish_status)
        )
        while not response_task.done() or not status_queue.empty():
            try:
                status_payload = await asyncio.wait_for(status_queue.get(), timeout=0.1)
            except TimeoutError:
                continue
            yield f"event: status\ndata: {json.dumps(status_payload, ensure_ascii=False)}\n\n"

        response = await response_task
        await asyncio.to_thread(repository.save_exchange, request, response)
        for character in response.text:
            payload = json.dumps({"delta": character}, ensure_ascii=False)
            yield f"event: delta\ndata: {payload}\n\n"
            await asyncio.sleep(0.018)
        final = json.dumps(response.model_dump(mode="json"), ensure_ascii=False)
        yield f"event: done\ndata: {final}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    team: TeamName,
    repository: SupabaseRepository = Depends(get_repository),
) -> ConversationResponse:
    return ConversationResponse(
        conversation_id=conversation_id,
        messages=repository.get_conversation(conversation_id, team),
    )
