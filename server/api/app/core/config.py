from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DbSettings(BaseModel):
    supabase_url: str
    supabase_service_key: str
    database_url: str = ""


class LlmSettings(BaseModel):
    gemini_api_key: str = ""
    groq_api_key: str = ""


class EmailSettings(BaseModel):
    resend_api_key: str = ""
    resend_from: str = "noreply@gethired.ai"


class ContactsSettings(BaseModel):
    hunter_api_key: str = ""
    apollo_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_api_key: str = ""


class CompileSettings(BaseModel):
    compile_service_url: str = "http://localhost:8001"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    database_url: str = ""  # postgresql+asyncpg://... for Procrastinate

    compile_service_url: str = "http://localhost:8001"

    gemini_api_key: str = ""
    groq_api_key: str = ""
    resend_api_key: str = ""
    resend_from: str = "noreply@gethired.ai"
    hunter_api_key: str = ""
    apollo_api_key: str = ""

    adzuna_app_id: str = ""
    adzuna_api_key: str = ""

    user_email: str = "tecmaths4mumbai@gmail.com"

    @property
    def db(self) -> DbSettings:
        return DbSettings(
            supabase_url=self.supabase_url,
            supabase_service_key=self.supabase_service_key,
            database_url=self.database_url,
        )

    @property
    def llm(self) -> LlmSettings:
        return LlmSettings(gemini_api_key=self.gemini_api_key, groq_api_key=self.groq_api_key)

    @property
    def email(self) -> EmailSettings:
        return EmailSettings(resend_api_key=self.resend_api_key, resend_from=self.resend_from)

    @property
    def contacts(self) -> ContactsSettings:
        return ContactsSettings(
            hunter_api_key=self.hunter_api_key,
            apollo_api_key=self.apollo_api_key,
            adzuna_app_id=self.adzuna_app_id,
            adzuna_api_key=self.adzuna_api_key,
        )

    @property
    def compile(self) -> CompileSettings:
        return CompileSettings(compile_service_url=self.compile_service_url)


settings = Settings()
