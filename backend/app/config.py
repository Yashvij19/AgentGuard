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

    e2b_base_url: str = Field(
        default="https://api.e2b.dev",
        description="E2B REST API endpoint base URL",
    )

    # OPA Policy Engine
    opa_url: str = Field(
        default="http://localhost:8181",
        description="OPA REST sidecar URL or 'embedded'",
    )

    # Dedicated Provider Overrides (Configured in .env)
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_models: str = "llama-3.3-70b-versatile,llama-3.1-8b-instant"

    gemini_api_key: str | None = None
    gemini_models: str = "gemini-2.0-flash"

    nvidia_nim_api_key: str | None = None
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_models: str = "meta/llama-3.1-8b-instruct"

    openai_compat_api_key: str | None = None
    openai_compat_base_url: str = "https://api.openai.com/v1"
    openai_compat_models: str = "gpt-4o,gpt-4o-mini"

    # Notification Webhooks (Slack / Discord)
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    dashboard_base_url: str = "http://localhost:3000"

    # CORS Settings
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated allowed CORS origins, or '*' to allow all",
    )

    # OpenTelemetry & Observability (Grafana Cloud)
    otel_service_name: str = "agentguard-backend"
    otel_exporter_otlp_endpoint: str | None = (
        None  # e.g. "https://otlp-gateway-prod-us-east-0.grafana.net/otlp"
    )
    otel_exporter_otlp_headers: str | None = None  # e.g. "Authorization=Basic <token>"

    @field_validator("database_url")
    @classmethod
    def validate_async_pg_driver(cls, v: str) -> str:
        """Ensure the connection string strictly specifies PostgreSQL with asyncpg."""
        if v.startswith("postgresql://"):
            # Auto-upgrade standard postgresql:// to asyncpg dialect if omitted
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "AgentGuard strictly requires PostgreSQL with the asyncpg driver (postgresql+asyncpg://...).\n"
                "Non-PostgreSQL databases (including SQLite) are prohibited because AgentGuard relies on "
                "transaction-scoped advisory locks (pg_try_advisory_xact_lock) for concurrency security."
            )
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

    @field_validator("github_private_key")
    @classmethod
    def format_private_key(cls, v: str) -> str:
        """Support unescaping literal \n or loading key directly from a .pem file path."""
        import os
        cleaned = v.strip().strip('"').strip("'")
        if cleaned.endswith(".pem") or cleaned.endswith(".key") or cleaned.startswith("/") or cleaned.startswith("./"):
            if not os.path.exists(cleaned):
                raise ValueError(
                    f"GitHub private key file specified at '{cleaned}' was not found inside the container! "
                    "Make sure the file exists and is mounted with -v $(pwd)/github_key.pem:/app/github_key.pem:ro."
                )
            with open(cleaned, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError(f"GitHub private key file at '{cleaned}' is empty!")
                return content
        return cleaned.replace("\\n", "\n")

    def get_llm_gateway_config(self) -> dict[str, Any]:
        """
        Build the canonical provider dictionary by combining dedicated env vars
        with any overrides in llm_providers_config.
        """
        providers: dict[str, Any] = {}

        # Groq
        groq_key = self.groq_api_key or self.llm_providers_config.get("providers", {}).get(
            "groq", {}
        ).get("api_key", "")
        if groq_key:
            providers["groq"] = {
                "name": "groq",
                "api_key": groq_key,
                "base_url": self.groq_base_url,
                "models": [m.strip() for m in self.groq_models.split(",") if m.strip()],
                "role": "fallback",
                "task_types": ["classification", "formatting", "general"],
            }

        # Gemini
        gemini_key = self.gemini_api_key or self.llm_providers_config.get("providers", {}).get(
            "gemini", {}
        ).get("api_key", "")
        if gemini_key:
            providers["gemini"] = {
                "name": "gemini",
                "api_key": gemini_key,
                "models": [m.strip() for m in self.gemini_models.split(",") if m.strip()],
                "role": "primary",
                "task_types": ["reasoning", "code_generation", "general"],
            }

        # NVIDIA NIM
        nim_key = self.nvidia_nim_api_key or self.llm_providers_config.get("providers", {}).get(
            "nvidia_nim", {}
        ).get("api_key", "")
        if nim_key:
            providers["nvidia_nim"] = {
                "name": "nvidia_nim",
                "api_key": nim_key,
                "base_url": self.nvidia_nim_base_url,
                "models": [m.strip() for m in self.nvidia_nim_models.split(",") if m.strip()],
                "role": "fallback",
                "task_types": ["reasoning", "general"],
            }

        # OpenAI-Compatible (Local vLLM, Ollama, DeepSeek, or OpenAI)
        openai_key = self.openai_compat_api_key or self.llm_providers_config.get("providers", {}).get(
            "openai_compat", {}
        ).get("api_key", "")
        if openai_key:
            providers["openai_compat"] = {
                "name": "openai_compat",
                "api_key": openai_key,
                "base_url": self.openai_compat_base_url,
                "models": [m.strip() for m in self.openai_compat_models.split(",") if m.strip()],
                "role": "specialist",
                "task_types": ["reasoning", "general"],
            }

        return {
            "providers": providers,
            "default_primary": "gemini"
            if "gemini" in providers
            else ("groq" if "groq" in providers else "openai_compat"),
            "default_fallback": "groq" if "groq" in providers else "nvidia_nim",
        }


# Global cached settings instance
settings = Settings()
