"""Deterministic Mock Model Provider for test suites and offline operation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from syntra.core.telemetry import TokenUsage, get_telemetry
from syntra.llm.config import compute_token_cost
from syntra.llm.exceptions import ModelOutputValidationError
from syntra.llm.models import LLMMessage, LLMResponse, ToolCall
from syntra.llm.provider import ModelProvider, ModelRequest

T = TypeVar("T", bound=BaseModel)


class MockModelProvider(ModelProvider):
    """In-memory deterministic mock ModelProvider for robust testing and simulation."""

    def __init__(self) -> None:
        self._responses_queue: list[LLMResponse | str | dict[str, Any] | BaseModel | Exception] = []
        self._custom_handler: Callable[[ModelRequest], LLMResponse] | None = None
        self.call_history: list[ModelRequest] = []

    def queue_response(self, response: LLMResponse | str | dict[str, Any] | BaseModel | Exception) -> None:
        """Enqueue a response or simulated exception for the next generate call."""
        self._responses_queue.append(response)

    def set_handler(self, handler: Callable[[ModelRequest], LLMResponse]) -> None:
        """Set a dynamic callback handler to generate responses based on the request."""
        self._custom_handler = handler

    async def generate_with_tools(self, request: ModelRequest) -> LLMResponse:
        """Execute simulated generation or raise enqueued exception."""
        self.call_history.append(request)

        # Check for simulated delay / cancellation
        if request.timeout_seconds and request.timeout_seconds < 0.01:
            await asyncio.sleep(0.02)

        if self._responses_queue:
            item = self._responses_queue.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, LLMResponse):
                resp = item
            elif isinstance(item, str):
                resp = LLMResponse(text=item, model=request.model or "mock-model")
            elif isinstance(item, dict):
                tool_calls = [ToolCall(**tc) for tc in item.get("tool_calls", [])]
                resp = LLMResponse(
                    text=item.get("text", ""),
                    tool_calls=tool_calls,
                    model=request.model or "mock-model",
                )
            else:
                resp = LLMResponse(text=str(item), model=request.model or "mock-model")
        elif self._custom_handler:
            if asyncio.iscoroutinefunction(self._custom_handler):
                resp = await self._custom_handler(request)
            else:
                resp = self._custom_handler(request)
                if asyncio.iscoroutine(resp):
                    resp = await resp

        else:
            resp = LLMResponse(
                text=f"Mock response for {request.agent_role} with {len(request.messages)} messages.",
                model=request.model or "mock-model",
            )

        # Token counting and cost calculation
        prompt_tokens = self.count_tokens(request.messages)
        comp_tokens = self.count_tokens(resp.text)
        cost_usd = compute_token_cost(request.model or "mock-model", prompt_tokens, comp_tokens)

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            total_tokens=prompt_tokens + comp_tokens,
            estimated_cost_usd=float(cost_usd),
        )
        resp.usage = usage

        get_telemetry().record_call(
            session_id=request.session_id,
            agent_id=request.agent_id,
            agent_role=request.agent_role,
            model=request.model or "mock-model",
            latency_seconds=0.005,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            success=True,
        )

        return resp

    async def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[T],
    ) -> tuple[T, LLMResponse]:
        """Execute simulated structured generation returning validated Pydantic model."""
        self.call_history.append(request)

        if self._responses_queue:
            item = self._responses_queue.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, response_model):
                parsed = item
                text = item.model_dump_json()
            elif isinstance(item, dict):
                try:
                    parsed = response_model.model_validate(item)
                    text = parsed.model_dump_json()
                except Exception as exc:
                    raise ModelOutputValidationError(f"Mock validation failed: {exc}") from exc
            elif isinstance(item, str):
                try:
                    parsed = response_model.model_validate_json(item)
                    text = item
                except Exception as exc:
                    raise ModelOutputValidationError(f"Mock JSON parsing failed: {exc}") from exc
            else:
                raise ModelOutputValidationError(f"Unsupported mock response type: {type(item)}")
        else:
            # Generate minimal dummy instance if model has defaults
            try:
                parsed = response_model.model_construct()
                text = parsed.model_dump_json()
            except Exception as exc:
                raise ModelOutputValidationError(f"Could not construct empty mock model: {exc}") from exc

        prompt_tokens = self.count_tokens(request.messages)
        comp_tokens = self.count_tokens(text)
        cost_usd = compute_token_cost(request.model or "mock-model", prompt_tokens, comp_tokens)

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            total_tokens=prompt_tokens + comp_tokens,
            estimated_cost_usd=float(cost_usd),
        )

        resp = LLMResponse(
            text=text,
            usage=usage,
            model=request.model or "mock-model",
        )
        return parsed, resp

    def count_tokens_if_supported(
        self, text_or_messages: str | list[LLMMessage], model: str | None = None
    ) -> int | None:
        """Estimate token count for mock provider."""
        return self.count_tokens(text_or_messages, model=model)

    def count_tokens(self, text_or_messages: str | list[LLMMessage], model: str | None = None) -> int:
        """Estimate token count."""
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages) // 4)
        total_chars = sum(len(m.content) for m in text_or_messages)
        return max(1, total_chars // 4)

    def classify_error(self, error: Exception) -> Exception:
        """Classify exceptions for MockModelProvider."""
        from syntra.llm.exceptions import (
            ModelAuthenticationError,
            ModelOutputValidationError,
            ModelProviderUnavailableError,
            ModelQuotaExceededError,
            ModelRetryExhaustedError,
            ModelTimeoutError,
        )

        if isinstance(
            error,
            (
                ModelAuthenticationError,
                ModelQuotaExceededError,
                ModelTimeoutError,
                ModelOutputValidationError,
                ModelProviderUnavailableError,
                ModelRetryExhaustedError,
            ),
        ):
            return error

        err_msg = str(error).lower()
        if "quota" in err_msg or "429" in err_msg or "rate limit" in err_msg:
            return ModelQuotaExceededError(str(error))
        if "timeout" in err_msg or "timed out" in err_msg:
            return ModelTimeoutError(str(error))
        if "auth" in err_msg or "api_key" in err_msg:
            return ModelAuthenticationError(str(error))
        return ModelProviderUnavailableError(str(error))
