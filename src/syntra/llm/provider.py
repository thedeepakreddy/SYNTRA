"""Abstract interface and contracts for SYNTRA Model Providers."""

from __future__ import annotations

import abc
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from syntra.llm.config import ModelSpec, get_model_spec
from syntra.llm.models import LLMMessage, LLMResponse, ToolDefinition

T = TypeVar("T", bound=BaseModel)


class ModelRequest(BaseModel):
    """Encapsulates all parameters for an LLM provider invocation."""

    model_config = ConfigDict(extra="ignore")

    messages: list[LLMMessage] = Field(..., description="Ordered conversation history")
    max_provider_retries: int | None = Field(default=None, ge=0, le=10)
    model: str | None = Field(default=None, description="Target model name")
    tools: list[ToolDefinition] | None = Field(default=None, description="Available tool definitions")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    max_tokens: int | None = Field(default=None, description="Maximum completion tokens")
    timeout_seconds: float = Field(default=60.0, description="Execution timeout deadline in seconds")
    session_id: str = Field(default="default", description="Tracing session identifier")
    agent_id: str = Field(default="agent", description="Calling agent identifier")
    agent_role: str = Field(default="assistant", description="Calling agent role name")
    system_instruction: str | None = Field(default=None, description="Primary system instruction/prompt")


class ModelProvider(abc.ABC):
    """Abstract interface implemented by all LLM runtime providers."""

    @abc.abstractmethod
    async def generate_with_tools(self, request: ModelRequest) -> LLMResponse:
        """Execute text generation and function/tool calling."""

    async def generate(self, request: ModelRequest) -> LLMResponse:
        """Standard generation alias calling generate_with_tools."""
        return await self.generate_with_tools(request)

    @abc.abstractmethod
    async def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[T],
    ) -> tuple[T, LLMResponse]:
        """Execute generation with output guaranteed to adhere to a Pydantic schema."""

    @abc.abstractmethod
    def count_tokens_if_supported(
        self, text_or_messages: str | list[LLMMessage], model: str | None = None
    ) -> int | None:
        """Compute or estimate token count if supported by provider."""

    def count_tokens(self, text_or_messages: str | list[LLMMessage], model: str | None = None) -> int:
        """Estimate or compute token count."""
        counted = self.count_tokens_if_supported(text_or_messages, model=model)
        if counted is not None:
            return counted
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages) // 4)
        return max(1, sum(len(m.content) for m in text_or_messages) // 4)

    def get_usage(self, response: LLMResponse) -> Any:
        """Extract or calculate token usage from an LLM response."""
        return response.usage

    @abc.abstractmethod
    def classify_error(self, error: Exception) -> Exception:
        """Classify a provider-specific exception into SYNTRA model runtime exceptions."""

    def get_model_info(self, model: str | None = None) -> ModelSpec:
        """Retrieve model specification and cost profile."""
        return get_model_spec(model)
