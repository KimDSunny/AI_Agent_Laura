from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


def create_public_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError("SUPABASE_URL과 SUPABASE_PUBLISHABLE_KEY가 필요해.")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


def create_user_supabase_client(access_token: str) -> Client:
    client = create_public_supabase_client()
    client.postgrest.auth(access_token)
    client.functions.set_auth(access_token)
    return client


def create_admin_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError("SUPABASE_URL과 SUPABASE_SECRET_KEY가 필요해.")
    return create_client(settings.supabase_url, settings.supabase_secret_key)


@lru_cache
def get_supabase_client() -> Client | None:
    settings = get_settings()
    if not settings.supabase_configured:
        return None

    key = settings.supabase_secret_key or settings.supabase_publishable_key
    return create_client(settings.supabase_url, key)
