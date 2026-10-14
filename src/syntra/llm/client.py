"""Google GenAI SDK client integration and LLM client interface."""

import abc
import json
import logging
import time
from typing import Any, TypeVar
from pydantic import BaseModel
from syntra.core.config import get_settings
from syntra.core.exceptions import LLMError, LLMQuotaExceededError
from syntra.core.telemetry import TokenUsage, get_telemetry
from syntra.llm.models import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(abc.ABC):
    """Abstract interface for LLM client implementations."""

    @abc.abstractmethod
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
        """Generate response given a conversation history and optional tools."""

    @abc.abstractmethod
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
        """Generate response adhering strictly to a Pydantic schema."""


class GeminiClient(BaseLLMClient):
    """Production Gemini client using the official Google GenAI SDK (google-genai)."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self._client: Any = None

        if self.api_key and not self.api_key.startswith("your_"):
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Google GenAI SDK client: %s", exc)

    def _ensure_client(self) -> Any:
        if self._client is None:
            settings = get_settings()
            key = self.api_key or settings.gemini_api_key
            if not key or key.startswith("your_"):
                raise LLMError(
                    "Gemini API key is not configured. Set GEMINI_API_KEY environment variable "
                    "or pass a valid key to GeminiClient."
                )
            from google import genai
            self._client = genai.Client(api_key=key)
        return self._client

    def _convert_messages(self, messages: list[LLMMessage]) -> list[Any]:
        """Convert standard LLMMessages to Google GenAI Content types."""
        from google.genai import types

        contents: list[types.Content] = []
        for msg in messages:
            parts: list[types.Part] = []
            if msg.role == MessageRole.TOOL:
                parts.append(
                    types.Part.from_function_response(
                        name=msg.name or "tool_result",
                        response={"result": msg.content},
                    )
                )
                contents.append(types.Content(role="tool", parts=parts))
            elif msg.role == MessageRole.ASSISTANT:
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                for tc in msg.tool_calls:
                    parts.append(
                        types.Part.from_function_call(
                            name=tc.name,
                            args=tc.arguments,
                        )
                    )
                contents.append(types.Content(role="model", parts=parts))
            elif msg.role == MessageRole.SYSTEM:
                # System instructions in GenAI are passed via config, but as fallback prepend to user
                parts.append(types.Part.from_text(text=f"[SYSTEM INSTRUCTION]: {msg.content}"))
                contents.append(types.Content(role="user", parts=parts))
            else:
                parts.append(types.Part.from_text(text=msg.content))
                contents.append(types.Content(role="user", parts=parts))

        return contents

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Any]:
        """Convert ToolDefinitions into Google GenAI Tool types."""
        from google.genai import types

        function_declarations: list[types.FunctionDeclaration] = []
        for tool in tools:
            decl = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            )
            function_declarations.append(decl)

        return [types.Tool(function_declarations=function_declarations)]

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
        """Call Gemini model asynchronously."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = model or settings.default_model
        temp = temperature if temperature is not None else settings.temperature
        max_output_tokens = max_tokens or settings.max_tokens_per_request

        contents = self._convert_messages(messages)

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_output_tokens,
        )

        if tools:
            config.tools = self._convert_tools(tools)

        start_time = time.perf_counter()
        retries = settings.max_retries
        backoff = settings.retry_delay_seconds

        for attempt in range(retries + 1):
            try:
                raw_response = await client.aio.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
                break
            except Exception as exc:
                err_str = str(exc).lower()
                is_quota = "quota" in err_str or "429" in err_str or "rate limit" in err_str
                if is_quota and attempt < retries:
                    logger.warning("Quota hit, backing off %0.1fs (attempt %d/%d)", backoff, attempt + 1, retries)
                    import asyncio
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                elif is_quota:
                    raise LLMQuotaExceededError(f"Gemini API rate limit exceeded: {exc}") from exc
                else:
                    raise LLMError(f"Gemini API invocation failed: {exc}") from exc

        latency = time.perf_counter() - start_time

        # Extract output text and function calls
        response_text = ""
        tool_calls: list[ToolCall] = []

        if raw_response.candidates:
            candidate = raw_response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                        tool_calls.append(
                            ToolCall(
                                id=getattr(fc, "id", "") or f"call_{int(time.time()*1000)}",
                                name=fc.name,
                                arguments=args,
                            )
                        )

        # Token counting
        usage_meta = getattr(raw_response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else len(str(messages)) // 4
        comp_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else len(response_text) // 4
        cached_tokens = getattr(usage_meta, "cached_content_token_count", 0) if usage_meta else 0

        metric = get_telemetry().record_call(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            model=target_model,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            cached_tokens=cached_tokens,
            success=True,
        )

        return LLMResponse(
            text=response_text,
            tool_calls=tool_calls,
            usage=metric.usage,
            model=target_model,
            finish_reason=str(raw_response.candidates[0].finish_reason) if raw_response.candidates else None,
            raw=raw_response,
        )

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
        """Generate structured response validated against a Pydantic model."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = model or settings.reasoning_model
        contents = self._convert_messages(messages)

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=temperature if temperature is not None else 0.1,
            response_mime_type="application/json",
            response_schema=response_model,
        )

        start_time = time.perf_counter()
        raw_response = await client.aio.models.generate_content(
            model=target_model,
            contents=contents,
            config=config,
        )
        latency = time.perf_counter() - start_time

        text = raw_response.text or "{}"
        parsed = response_model.model_validate_json(text)

        usage_meta = getattr(raw_response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else len(str(messages)) // 4
        comp_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else len(text) // 4

        metric = get_telemetry().record_call(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            model=target_model,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            success=True,
        )

        resp = LLMResponse(
            text=text,
            usage=metric.usage,
            model=target_model,
            raw=raw_response,
        )
        return parsed, resp
