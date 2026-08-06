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


class ApifySettings(BaseModel):
    api_token: str = ""
    career_actor_id: str = "apify/website-content-crawler"
    linkedin_actor_id: str = ""
    x_actor_id: str = ""
    career_urls: str = ""
    linkedin_urls: str = ""
    x_urls: str = ""


class CompileSettings(BaseModel):
    compile_service_url: str = "http://localhost:8001"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    supabase_url: str
    supabase_service_key: str
    database_url: str = ""  # postgresql+asyncpg://... for Procrastinate

    compile_service_url: str = "http://localhost:8001"
    compile_service_hostport: str = ""

    gemini_api_key: str = ""
    groq_api_key: str = ""
    resend_api_key: str = ""
    resend_from: str = "noreply@gethired.ai"
    hunter_api_key: str = ""
    apollo_api_key: str = ""

    adzuna_app_id: str = ""
    adzuna_api_key: str = ""

    apify_api_token: str = ""
    apify_career_actor_id: str = "apify/website-content-crawler"
    apify_linkedin_actor_id: str = ""
    apify_x_actor_id: str = ""
    apify_career_urls: str = ""
    apify_linkedin_urls: str = ""
    apify_x_urls: str = ""

    user_email: str = "tecmaths4mumbai@gmail.com"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

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
    def apify(self) -> ApifySettings:
        return ApifySettings(
            api_token=self.apify_api_token,
            career_actor_id=self.apify_career_actor_id,
            linkedin_actor_id=self.apify_linkedin_actor_id,
            x_actor_id=self.apify_x_actor_id,
            career_urls=self.apify_career_urls,
            linkedin_urls=self.apify_linkedin_urls,
            x_urls=self.apify_x_urls,
        )

    @property
    def compile(self) -> CompileSettings:
        compile_service_url = self.compile_service_url
        if self.compile_service_hostport and compile_service_url == "http://localhost:8001":
            compile_service_url = f"http://{self.compile_service_hostport}"
        return CompileSettings(compile_service_url=compile_service_url)


settings = Settings()
