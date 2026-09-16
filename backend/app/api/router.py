from fastapi import APIRouter

from app.api.routes import actions, auth, chat, health, integrations, onboarding, profile, team_chat


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(chat.router)
api_router.include_router(team_chat.router)
api_router.include_router(onboarding.router)
api_router.include_router(actions.router)
api_router.include_router(integrations.router)
