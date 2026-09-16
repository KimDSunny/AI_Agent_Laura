from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_repository
from app.models.auth import ProfileResponse, ProfileUpsert
from app.services.repository import SupabaseRepository


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse | None)
def get_profile(
    repository: SupabaseRepository = Depends(get_repository),
) -> ProfileResponse | None:
    return repository.get_profile()


@router.put("", response_model=ProfileResponse)
def save_profile(
    profile: ProfileUpsert,
    repository: SupabaseRepository = Depends(get_repository),
) -> ProfileResponse:
    return repository.save_profile(profile)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    repository: SupabaseRepository = Depends(get_repository),
) -> Response:
    repository.delete_profile()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
