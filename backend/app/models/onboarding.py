from pydantic import BaseModel, computed_field

from app.models.chat import TeamName


class OnboardingProgress(BaseModel):
    team: TeamName
    completed: int
    total: int

    @computed_field
    @property
    def percentage(self) -> int:
        return round((self.completed / self.total) * 100) if self.total else 0
