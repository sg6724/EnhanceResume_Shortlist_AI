from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    database_url: str = ""  # postgresql+asyncpg://... for Procrastinate

    compile_service_url: str = "http://localhost:8001"

    gemini_api_key: str = ""
    resend_api_key: str = ""
    resend_from: str = "noreply@jobhunt.ai"
    hunter_api_key: str = ""

    adzuna_app_id: str = ""
    adzuna_api_key: str = ""

    user_email: str = "tecmaths4mumbai@gmail.com"


settings = Settings()
