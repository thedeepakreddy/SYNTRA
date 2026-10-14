"""DevSwarm core exception hierarchy."""


class DevSwarmError(Exception):
    """Base exception for all DevSwarm runtime errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(DevSwarmError):
    """Raised when configuration is invalid or missing."""


class LLMError(DevSwarmError):
    """Base exception for LLM-related errors."""


class LLMQuotaExceededError(LLMError):
    """Raised when LLM API quota or rate limit is reached."""


class LLMInvalidResponseError(LLMError):
    """Raised when the LLM output fails schema validation."""


class SandboxError(DevSwarmError):
    """Base exception for sandbox and workspace isolation errors."""


class SandboxSecurityViolationError(SandboxError):
    """Raised when an agent attempts an unsafe action (e.g. path traversal, forbidden command)."""


class SandboxExecutionTimeoutError(SandboxError):
    """Raised when a sandbox command exceeds its execution timeout."""


class AgentError(DevSwarmError):
    """Base exception for agent errors."""


class AgentMaxStepsExceededError(AgentError):
    """Raised when an agent loop exceeds maximum reasoning/tool execution steps."""


class CheckpointError(DevSwarmError):
    """Base exception for hybrid autonomy checkpoint errors."""


class CheckpointPendingError(CheckpointError):
    """Raised when an operation cannot proceed because a checkpoint approval is pending."""


class SwarmOrchestrationError(DevSwarmError):
    """Raised when swarm workflow execution fails or encounters deadlock."""


class StorageError(DevSwarmError):
    """Raised when database or state persistence fails."""
