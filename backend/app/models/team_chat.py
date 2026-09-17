from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.chat import TeamName


class TeamMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("메시지를 입력해 주세요.")
        return cleaned


class TeamMessage(BaseModel):
    id: str
    team: TeamName
    sender_name: str
    content: str
    is_own: bool
    created_at: datetime


class TeamMessagesResponse(BaseModel):
    team: TeamName
    messages: list[TeamMessage]
