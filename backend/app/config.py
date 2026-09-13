"""
Configuration module for AgentGuard.
Uses pydantic-settings to enforce type-safety and fail-fast validation on startup.
"""

import json
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BACKEND_DIR / ".env"

class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    """
    Application settings validated against environment variables.
    Fails closed: If any critical variable is absent, instantiation raises ValidationError.
    """

    model_config = SettingsConfigDict(
        env_file=(ENV_FILE_PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra env vars without failing
    )

    # Core Application
    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        ...,
        description="Async connection string (e.g. postgresql+asyncpg://user:pass@host/dbname)",
    )

    # GitHub App Integration
    github_app_id: str = Field(..., description="GitHub App ID")
    github_webhook_secret: str = Field(
        ..., description="Secret used to verify HMAC-SHA256 signatures"
    )
    github_private_key: str = Field(
        ..., description="RSA private key in PEM format for GitHub App JWT generation"
    )

    # LLM Gateway Configuration
    llm_providers_config: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON configuration containing providers, keys, and routing rules",
    )

    # Sandbox Runner
    sandbox_provider: str = Field(default="e2b", description="e2b or github_actions")
    e2b_api_key: str | None = None

    # OPA Policy Engine
    opa_url: str = Field(
        default="http://localhost:8181",
        description="OPA REST sidecar URL or 'embedded'",
    )

    @field_validator("database_url")
    @classmethod
    def validate_async_pg_driver(cls, v: str) -> str:
        """Ensure the connection string specifies the asyncpg driver."""
        if v.startswith("postgresql://"):
            # Auto-upgrade standard postgresql:// to asyncpg dialect if omitted
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use the postgresql+asyncpg driver")
        return v

    @field_validator("llm_providers_config", mode="before")
    @classmethod
    def parse_llm_json(cls, v: Any) -> dict[str, Any]:
        """Allow JSON string parsing from environment variables."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return cast(dict[str, Any], parsed)
                raise ValueError("LLM_PROVIDERS_CONFIG must decode to a JSON object")
            except json.JSONDecodeError as err:
                raise ValueError(f"Invalid JSON string for LLM_PROVIDERS_CONFIG: {err}") from err

        if isinstance(v, dict):
            return cast(dict[str, Any], v)
        return {}


# Global cached settings instance
settings = Settings()
