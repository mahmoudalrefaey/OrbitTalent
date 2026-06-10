"""Application settings, loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./orbittalent.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Models — keep exactly as-is, no date suffixes.
    model_deep: str = "claude-opus-4-8"
    model_cheap: str = "claude-haiku-4-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
