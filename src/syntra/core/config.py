"""SYNTRA configuration management powered by Pydantic Settings."""

from enum import Enum
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutonomyMode(str, Enum):
    """Autonomy modes supported by SYNTRA."""

    AUTONOMOUS = "autonomous"  # Auto-executes everything; pauses only on unrecoverable error
    SEMI_AUTONOMOUS = "semi_autonomous"  # Auto-executes read/test; requires approval for file writes/shell execution
    SUPERVISED = "supervised"  # Pauses at each major agent lifecycle gate
    STRICT_APPROVAL = "strict_approval"  # Explicit human approval for every mutation/tool call


class Settings(BaseSettings):
    """Global SYNTRA application settings."""

    model_config = SettingsConfigDict(
        env_prefix="SYNTRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Environment
    environment: Literal["development", "test", "production"] = "development"
    dev_auth_enabled: bool = True

    # Security & Authentication (OIDC / JWT)
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    approval_secret_key: str = "syntra-default-approval-hmac-secret-change-in-prod"
    max_request_body_bytes: int = 10 * 1024 * 1024  # 10MB

    # Gemini LLM Settings
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    default_model: str = "gemini-2.5-flash"
    reasoning_model: str = "gemini-2.5-pro"
    fast_model: str = "gemini-2.0-flash-lite"
    max_tokens_per_request: int = 8192
    temperature: float = 0.2
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Autonomy & Checkpoints
    autonomy_mode: AutonomyMode = AutonomyMode.SEMI_AUTONOMOUS
    max_agent_steps: int = 30
    auto_approve_safe_reads: bool = True

    # Execution Sandbox
    sandbox_base_dir: Path = Path("./.syntra/sandboxes")
    sandbox_timeout_seconds: int = 120
    sandbox_max_output_bytes: int = 1048576  # 1MB
    sandbox_allow_network: bool = True

    # Storage & Persistence
    database_url: str = "sqlite+aiosqlite:///./syntra.db"

    # Queue & Streaming (Redis Streams)
    redis_url: str = "redis://localhost:6379/0"

    # Artifact Storage (MinIO / S3)
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "syntra_minio"
    s3_secret_key: str = "syntra_minio_secret"
    s3_bucket: str = "syntra-artifacts"
    s3_secure: bool = False

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False

    @model_validator(mode="after")
    def validate_production_guards(self) -> Self:
        """Enforce production security invariants."""
        if self.environment == "production":
            if self.dev_auth_enabled:
                raise ValueError(
                    "Development authentication (dev_auth_enabled=True) cannot be enabled in production environment."
                )
            if "sqlite" in self.database_url:
                raise ValueError("SQLite database is not permitted in production environment.")
        return self

    def is_api_key_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key.strip() and not self.gemini_api_key.startswith("your_"))


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Retrieve the cached singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    """Reset the settings cache (useful for testing)."""
    global _settings_instance
    _settings_instance = None
