"""Mock and deterministic replay LLM client for test suites and offline operation."""

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from syntra.core.telemetry import get_telemetry
from syntra.llm.client import BaseLLMClient
from syntra.llm.models import (
    LLMMessage,
    LLMResponse,
    ToolCall,
    ToolDefinition,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMClient(BaseLLMClient):
    """In-memory deterministic mock LLM client for testing and simulation."""

    def __init__(self) -> None:
        self._responses_queue: list[LLMResponse | str | dict[str, Any]] = []
        self._custom_handler: Callable[[list[LLMMessage], list[ToolDefinition] | None], LLMResponse] | None = None
        self.call_history: list[dict[str, Any]] = []

    def queue_response(self, response: LLMResponse | str | dict[str, Any]) -> None:
        """Enqueue a canned response to be returned by next generate call."""
        self._responses_queue.append(response)

    def set_handler(self, handler: Callable[[list[LLMMessage], list[ToolDefinition] | None], LLMResponse]) -> None:
        """Set a dynamic callback handler to generate responses based on input."""
        self._custom_handler = handler

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        session_id: str = "default",
        agent_id: str = "agent",
        agent_role: str = "assistant",
    ) -> LLMResponse:
        self.call_history.append(
            {
                "messages": messages,
                "model": model,
                "tools": tools,
                "session_id": session_id,
                "agent_id": agent_id,
                "agent_role": agent_role,
            }
        )

        if self._custom_handler:
            resp = self._custom_handler(messages, tools)
            # Record telemetry
            get_telemetry().record_call(
                session_id=session_id,
                agent_id=agent_id,
                agent_role=agent_role,
                model=model or "mock-model",
                latency_seconds=0.01,
                prompt_tokens=50,
                completion_tokens=50,
            )
            return resp

        if self._responses_queue:
            item = self._responses_queue.pop(0)
            if isinstance(item, LLMResponse):
                resp = item
            elif isinstance(item, str):
                resp = LLMResponse(text=item, model=model or "mock-model")
            elif isinstance(item, dict):
                resp = LLMResponse(
                    text=item.get("text", ""),
                    tool_calls=[ToolCall(**tc) for tc in item.get("tool_calls", [])],
                    model=model or "mock-model",
                )
            else:
                resp = LLMResponse(text=str(item), model=model or "mock-model")
        else:
            resp = LLMResponse(
                text=f"Mock response for {agent_role} with {len(messages)} messages.",
                model=model or "mock-model",
            )

        metric = get_telemetry().record_call(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            model=model or "mock-model",
            latency_seconds=0.005,
            prompt_tokens=20,
            completion_tokens=20,
        )
        resp.usage = metric.usage
        return resp

    async def generate_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
        model: str | None = None,
        temperature: float | None = None,
        session_id: str = "default",
        agent_id: str = "agent",
        agent_role: str = "assistant",
    ) -> tuple[T, LLMResponse]:
        self.call_history.append(
            {
                "messages": messages,
                "response_model": response_model.__name__,
                "model": model,
                "session_id": session_id,
                "agent_id": agent_id,
                "agent_role": agent_role,
            }
        )

        if self._responses_queue:
            item = self._responses_queue.pop(0)
            if isinstance(item, response_model):
                parsed = item
                json_str = item.model_dump_json()
            elif isinstance(item, dict):
                parsed = response_model.model_validate(item)  # type: ignore[assignment]
                json_str = json.dumps(item)
            elif isinstance(item, str):
                parsed = response_model.model_validate_json(item)  # type: ignore[assignment]
                json_str = item
            else:
                raise ValueError(f"Cannot parse queued item to {response_model}")
        else:
            # Generate default instance or mock data
            try:
                parsed = response_model()  # type: ignore
                json_str = parsed.model_dump_json()
            except Exception:
                raise ValueError(f"MockLLMClient has no queued response for structured type {response_model.__name__}")

        metric = get_telemetry().record_call(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            model=model or "mock-model",
            latency_seconds=0.005,
            prompt_tokens=30,
            completion_tokens=30,
        )

        resp = LLMResponse(
            text=json_str,
            usage=metric.usage,
            model=model or "mock-model",
        )
        return parsed, resp
