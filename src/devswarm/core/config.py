"""DevSwarm configuration management powered by Pydantic Settings."""

from enum import Enum
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutonomyMode(str, Enum):
    """Autonomy modes supported by DevSwarm."""
    AUTONOMOUS = "autonomous"            # Auto-executes everything; pauses only on unrecoverable error
    SEMI_AUTONOMOUS = "semi_autonomous"  # Auto-executes read/test; requires approval for file writes/shell execution
    SUPERVISED = "supervised"            # Pauses at each major agent lifecycle gate
    STRICT_APPROVAL = "strict_approval"  # Explicit human approval for every mutation/tool call


class Settings(BaseSettings):
    """Global DevSwarm application settings."""

    model_config = SettingsConfigDict(
        env_prefix="DEVSWARM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    sandbox_base_dir: Path = Path("./.devswarm/sandboxes")
    sandbox_timeout_seconds: int = 120
    sandbox_max_output_bytes: int = 1048576  # 1MB
    sandbox_allow_network: bool = True

    # Storage & Persistence
    database_url: str = "sqlite+aiosqlite:///./devswarm.db"

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False

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
