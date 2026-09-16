from datetime import datetime

from pydantic import BaseModel


class GoogleCalendarStatus(BaseModel):
    configured: bool
    connected: bool
    connected_at: datetime | None = None


class GoogleCalendarAuthorization(BaseModel):
    authorization_url: str
