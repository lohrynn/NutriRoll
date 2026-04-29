"""Process-wide configuration loaded from the environment.

All settings are validated by Pydantic. Reading from `os.environ` directly
elsewhere in the codebase is forbidden.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NUTRIROLL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://nutriroll:nutriroll@localhost:5432/nutriroll",
        description="SQLAlchemy async URL.",
    )

    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins.",
    )

    llm_key_master: str = Field(
        default="dev-only-not-for-prod-replace-me",
        description="Master key used to envelope-encrypt per-user LLM API keys.",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
