from fastapi import APIRouter, Depends

from app.api.dependencies import get_repository
from app.models.chat import TeamName
from app.models.onboarding import OnboardingProgress
from app.services.repository import SupabaseRepository


router = APIRouter(tags=["onboarding"])


@router.get("/onboarding/progress", response_model=OnboardingProgress)
def get_onboarding_progress(
    team: TeamName,
    repository: SupabaseRepository = Depends(get_repository),
) -> OnboardingProgress:
    return repository.get_onboarding_progress(team)
