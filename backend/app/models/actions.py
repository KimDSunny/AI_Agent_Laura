from typing import Literal

from pydantic import BaseModel


class ActionExecuteRequest(BaseModel):
    confirmed: bool


class ActionResponse(BaseModel):
    action_id: str
    status: Literal["approved", "declined", "authorization_required"]
    message: str
    authorization_url: str | None = None
