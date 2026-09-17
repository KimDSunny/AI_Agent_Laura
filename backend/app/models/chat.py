from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


TeamName = Literal["개발팀", "인사팀", "마케팅팀", "디자인팀", "기획팀"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    team: TeamName
    conversation_id: str = Field(default="demo", min_length=1, max_length=100)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("메시지를 입력해 주세요.")
        return cleaned


class Source(BaseModel):
    title: str
    section: str
    # 이전 단계에서 저장된 대화의 출처도 계속 읽을 수 있게 기본값을 둔다.
    relevant_sentence: str = ""


class AgentAction(BaseModel):
    id: str
    type: Literal["create_schedule", "update_checklist"] = "create_schedule"
    title: str
    detail: str
    schedule_title: str | None = None
    starts_at: datetime | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "running", "approved", "declined"] = "pending"


class ChatResponse(BaseModel):
    text: str
    conversation_id: str
    sources: list[Source] = Field(default_factory=list)
    action: AgentAction | None = None


class ConversationMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: Literal["user", "agent"]
    text: str
    sources: list[Source] = Field(default_factory=list)
    action: AgentAction | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list[ConversationMessage]
