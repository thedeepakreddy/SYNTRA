"""SYNTRA Model Runtime Exception Hierarchy.

Categorized exceptions for LLM provider operations, authentication, quotas,
timeouts, retries, and structured validation.
"""

from __future__ import annotations

from typing import Any

from syntra.core.exceptions import LLMError, LLMInvalidResponseError, LLMQuotaExceededError


class ModelRuntimeError(LLMError):
    """Base exception for all Model Runtime operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)
        self.details = details or {}


class ModelAuthenticationError(ModelRuntimeError):
    """Raised when provider API credentials are missing, invalid, or expired."""


class ModelQuotaExceededError(ModelRuntimeError, LLMQuotaExceededError):
    """Raised when provider rate limits, token quotas, or concurrency limits are exceeded."""


class ModelTimeoutError(ModelRuntimeError):
    """Raised when an LLM request exceeds its configured timeout deadline."""


class ModelRetryExhaustedError(ModelRuntimeError):
    """Raised when bounded retry policy exhausts all retry attempts."""


class ModelOutputValidationError(ModelRuntimeError, LLMInvalidResponseError):
    """Raised when model output fails JSON parsing or Pydantic schema validation."""


class ModelToolExecutionError(ModelRuntimeError):
    """Raised when model proposes an invalid or rejected tool invocation."""


class ModelProviderUnavailableError(ModelRuntimeError):
    """Raised when downstream LLM service is unreachable or returning 5xx status codes."""


class ModelBudgetExceededError(ModelRuntimeError):
    """Raised when token or USD cost budget reserved for the task is exceeded."""


class ModelPricingError(ModelRuntimeError):
    """Raised when model pricing is missing, unverified, or violates cost policies."""
