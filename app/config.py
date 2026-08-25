from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-dev-secret-not-for-production"

    database_url: str = "sqlite+aiosqlite:///./data/satyascan.db"

    field_encryption_key: Optional[str] = None

    chroma_persist_dir: str = "./data/chroma"

    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    google_fact_check_api_key: Optional[str] = None
    google_cloud_vision_api_key: Optional[str] = None
    google_translate_api_key: Optional[str] = None

    sightengine_api_user: Optional[str] = None
    sightengine_api_secret: Optional[str] = None

    serper_api_key: Optional[str] = None

    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    whatsapp_app_secret: Optional[str] = None

    message_retention_days: int = 0
    rate_limit_per_minute: int = 10

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
