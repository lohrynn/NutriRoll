"""Process-wide configuration loaded from the environment.

All settings are validated by Pydantic. Reading from `os.environ` directly
elsewhere in the codebase is forbidden.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
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
    llm_provider: Literal["openai", "anthropic", "google", "ollama", "custom"] = Field(
        default="openai",
        description="Default LLM provider used when the user has not overridden it.",
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("NUTRIOLL_LLM_MODEL", "NUTRIROLL_LLM_MODEL"),
        description="Default model used for prompt-based component generation.",
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("NUTRIROLL_LLM_BASE_URL", "OPENAI_BASE_URL"),
        description="Base URL for the chat-completions compatible LLM provider.",
    )
    openai_api_key: str = Field(
        default="",
        validation_alias="OPENAI_API_KEY",
        description="API key used for prompt-based component generation.",
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
        description="OpenAI-compatible base URL for the OpenAI provider.",
    )
    anthropic_api_key: str = Field(
        default="",
        validation_alias="ANTHROPIC_API_KEY",
        description="Default Anthropic API key fallback.",
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com/v1",
        validation_alias="ANTHROPIC_BASE_URL",
        description="Anthropic API base URL.",
    )
    google_api_key: str = Field(
        default="",
        validation_alias="GOOGLE_API_KEY",
        description="Default Google Generative AI API key fallback.",
    )
    google_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias="GOOGLE_BASE_URL",
        description="Google Generative AI API base URL.",
    )
    ollama_api_key: str = Field(
        default="",
        validation_alias="OLLAMA_API_KEY",
        description="Optional Ollama API key for proxied deployments.",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434/v1",
        validation_alias="OLLAMA_BASE_URL",
        description="Ollama OpenAI-compatible base URL.",
    )
    custom_llm_api_key: str = Field(
        default="",
        validation_alias="CUSTOM_LLM_API_KEY",
        description="Default API key for the custom OpenAI-compatible provider.",
    )
    custom_llm_base_url: str = Field(
        default="",
        validation_alias="CUSTOM_LLM_BASE_URL",
        description="Base URL for the custom OpenAI-compatible provider.",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
