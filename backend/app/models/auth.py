from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.chat import TeamName


class SessionResponse(BaseModel):
    user_id: UUID
    expires_at: int | None = None


class ProfileUpsert(BaseModel):
    employee_name: str = Field(min_length=1, max_length=50)
    hire_date: date
    team: TeamName


class ProfileResponse(ProfileUpsert):
    user_id: UUID

