"""Google Gemini Model Provider implementation using official google-genai SDK."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from syntra.core.config import get_settings
from syntra.core.telemetry import TokenUsage, get_telemetry
from syntra.llm.config import compute_token_cost, get_model_spec
from syntra.llm.exceptions import (
    ModelAuthenticationError,
    ModelOutputValidationError,
    ModelProviderUnavailableError,
    ModelQuotaExceededError,
    ModelRetryExhaustedError,
    ModelTimeoutError,
)
from syntra.llm.models import LLMMessage, LLMResponse, MessageRole, ToolCall, ToolDefinition
from syntra.llm.provider import ModelProvider, ModelRequest

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _resolve_api_model(target_model: str) -> str:
    """Map legacy/retired models to live Google GenAI active models while preserving spec."""
    aliases = {
        "gemini-2.5-pro": "gemini-3.8-flash",
        "gemini-2.5-flash": "gemini-3.8-flash",
        "gemini-2.5-flash-lite": "gemini-3.5-flash",
        "gemini-2.0-flash-lite": "gemini-3.5-flash",
    }
    return aliases.get(target_model, target_model)


class GeminiModelProvider(ModelProvider):
    """Production ModelProvider utilizing Google's Gemini models via the google-genai SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._raw_api_key = api_key or settings.gemini_api_key
        self._client: Any = None

        if self._raw_api_key and not self._raw_api_key.startswith("your_"):
            try:
                from google import genai

                self._client = genai.Client(api_key=self._raw_api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Google GenAI SDK: %s", exc)

    def __repr__(self) -> str:
        status = "configured" if self.is_configured() else "unconfigured"
        return f"<GeminiModelProvider(status={status}, api_key=[REDACTED])>"

    def __str__(self) -> str:
        return self.__repr__()

    def is_configured(self) -> bool:
        """Check if valid credentials are available for real API connectivity."""
        return bool(self._raw_api_key and not self._raw_api_key.startswith("your_"))

    async def list_available_models(self) -> list[str]:
        """List available model IDs for the authenticated account using official SDK."""
        client = self._ensure_client()
        model_ids: list[str] = []
        try:
            pager = await client.aio.models.list()
            async for m in pager:
                name = getattr(m, "name", "")
                if name:
                    clean = name.replace("models/", "")
                    model_ids.append(clean)
        except Exception as exc:
            raise self.classify_error(exc) from exc
        return model_ids

    async def verify_model_access(self, model_id: str) -> bool:
        """Verify whether a specific model ID is enabled and accessible for the current account."""
        available = await self.list_available_models()
        clean = model_id.replace("models/", "").lower()
        return any(clean == m.lower() for m in available)

    def _ensure_client(self) -> Any:
        if self._client is None:
            settings = get_settings()
            key = self._raw_api_key or settings.gemini_api_key
            if not key or key.startswith("your_"):
                raise ModelAuthenticationError(
                    "Gemini API key is not configured. Set GEMINI_API_KEY environment variable "
                    "or pass a valid key to GeminiModelProvider."
                )
            from google import genai

            self._client = genai.Client(api_key=key)
        return self._client

    def _convert_messages(self, messages: list[LLMMessage]) -> list[Any]:
        """Convert standard LLMMessage list to Google GenAI Content types."""
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
            elif msg.role == MessageRole.USER:
                parts.append(types.Part.from_text(text=msg.content))
                contents.append(types.Content(role="user", parts=parts))
            elif msg.role == MessageRole.SYSTEM:
                # System messages handled via GenerateContentConfig.system_instruction,
                # but if present in message list, prepend as user instruction
                parts.append(types.Part.from_text(text=f"[SYSTEM INSTRUCTION]: {msg.content}"))
                contents.append(types.Content(role="user", parts=parts))

        return contents

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Any]:
        """Convert ToolDefinition list to Google GenAI Tool types."""
        from google.genai import types

        function_declarations: list[types.FunctionDeclaration] = []
        for tool in tools:
            params_schema: types.Schema | None = None
            if tool.parameters:
                try:
                    params_schema = types.Schema.model_validate(tool.parameters)
                except Exception:
                    params_schema = types.Schema(type=types.Type.OBJECT)

            decl = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=params_schema,
            )
            function_declarations.append(decl)

        return [types.Tool(function_declarations=function_declarations)]

    async def _execute_with_retry(
        self,
        call_fn: Any,
        timeout_seconds: float,
        retries: int = 3,
        initial_delay: float = 1.0,
    ) -> Any:
        """Execute async API call with timeout enforcement, exponential backoff, and jitter."""
        delay = initial_delay

        for attempt in range(retries + 1):
            try:
                # Apply strict timeout to every execution
                async with asyncio.timeout(timeout_seconds):
                    return await call_fn()
            except TimeoutError as exc:
                raise ModelTimeoutError(f"Gemini API request timed out after {timeout_seconds:.1f}s") from exc
            except asyncio.CancelledError:
                logger.info("Gemini request was cancelled by caller")
                raise
            except Exception as exc:
                err_msg = str(exc).lower()
                is_quota = (
                    "quota" in err_msg or "429" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg
                )
                is_transient = (
                    "503" in err_msg or "unavailable" in err_msg or "connection" in err_msg or "reset" in err_msg
                )

                if (is_quota or is_transient) and attempt < retries:
                    jitter = random.uniform(0.1, 0.5)
                    backoff_time = delay + jitter
                    logger.warning(
                        "Transient error from Gemini (%s). Backing off %.2fs (attempt %d/%d)",
                        err_msg,
                        backoff_time,
                        attempt + 1,
                        retries,
                    )
                    await asyncio.sleep(backoff_time)
                    delay *= 2.0
                    continue
                elif is_quota:
                    raise ModelQuotaExceededError(
                        f"Gemini API rate limit or quota exceeded after {retries} retries: {exc}"
                    ) from exc
                elif is_transient:
                    raise ModelRetryExhaustedError(f"Gemini API request failed after {retries} retries: {exc}") from exc
                elif "auth" in err_msg or "api_key" in err_msg or "permission" in err_msg or "403" in err_msg:
                    raise ModelAuthenticationError(f"Gemini API authentication failed: {exc}") from exc
                else:
                    raise ModelProviderUnavailableError(f"Gemini API request failed: {exc}") from exc

    async def generate_with_tools(self, request: ModelRequest) -> LLMResponse:
        """Call Gemini model asynchronously for text generation or tool calling."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = request.model or settings.default_model
        spec = get_model_spec(target_model)

        temp = request.temperature if request.temperature is not None else spec.default_temperature
        max_output_tokens = request.max_tokens or spec.max_output_tokens
        timeout_sec = request.timeout_seconds or spec.timeout_seconds

        contents = self._convert_messages(request.messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=max_output_tokens,
        )

        if request.system_instruction:
            config.system_instruction = request.system_instruction

        if request.tools:
            config.tools = self._convert_tools(request.tools)

        start_time = time.perf_counter()

        api_model = _resolve_api_model(target_model)

        async def _call():
            return await client.aio.models.generate_content(
                model=api_model,
                contents=contents,
                config=config,
            )

        raw_response = await self._execute_with_retry(
            _call,
            timeout_seconds=timeout_sec,
            retries=request.max_provider_retries if request.max_provider_retries is not None else settings.max_retries,
            initial_delay=settings.retry_delay_seconds,
        )

        latency = time.perf_counter() - start_time

        # Extract text and tool calls
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
                                id=getattr(fc, "id", "") or f"call_{int(time.time() * 1000)}",
                                name=fc.name,
                                arguments=args,
                            )
                        )

        # Token counting and cost calculation
        usage_meta = getattr(raw_response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else len(str(request.messages)) // 4
        comp_tokens = (
            (getattr(usage_meta, "candidates_token_count", 0) or 0)
            + (getattr(usage_meta, "thoughts_token_count", 0) or 0)
            if usage_meta
            else len(response_text) // 4
        )
        cached_tokens = getattr(usage_meta, "cached_content_token_count", 0) if usage_meta else 0
        total_tokens = prompt_tokens + comp_tokens

        cost_usd = compute_token_cost(target_model, prompt_tokens, comp_tokens)

        # Record telemetry
        get_telemetry().record_call(
            session_id=request.session_id,
            agent_id=request.agent_id,
            agent_role=request.agent_role,
            model=target_model,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            cached_tokens=cached_tokens,
            success=True,
        )

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            cached_tokens=cached_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=float(cost_usd),
        )

        finish_reason = None
        if raw_response.candidates:
            finish_reason = str(raw_response.candidates[0].finish_reason)

        return LLMResponse(
            text=response_text,
            usage_known=usage_meta is not None,
            tool_calls=tool_calls,
            usage=usage,
            model=target_model,
            finish_reason=finish_reason,
            raw=raw_response,
        )

    async def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[T],
    ) -> tuple[T, LLMResponse]:
        """Execute structured generation adhering strictly to a Pydantic schema."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = request.model or settings.reasoning_model
        spec = get_model_spec(target_model)

        contents = self._convert_messages(request.messages)

        import json

        from google.genai import types

        schema_json = json.dumps(response_model.model_json_schema())
        enhanced_system_instruction = (
            (request.system_instruction + "\n\n" if request.system_instruction else "")
            + f"You are a strict structured output generator. You must respond with ONLY a single valid JSON object strictly matching this schema:\n{schema_json}\nDo not wrap in markdown or backticks."
        )

        config = types.GenerateContentConfig(
            temperature=request.temperature if request.temperature is not None else 0.1,
            max_output_tokens=request.max_tokens or spec.max_output_tokens,
            response_mime_type="application/json",
            system_instruction=enhanced_system_instruction,
        )

        timeout_sec = request.timeout_seconds or spec.timeout_seconds
        start_time = time.perf_counter()

        api_model = _resolve_api_model(target_model)

        async def _call():
            return await client.aio.models.generate_content(
                model=api_model,
                contents=contents,
                config=config,
            )

        raw_response = await self._execute_with_retry(
            _call,
            timeout_seconds=timeout_sec,
            retries=request.max_provider_retries if request.max_provider_retries is not None else settings.max_retries,
            initial_delay=settings.retry_delay_seconds,
        )

        latency = time.perf_counter() - start_time
        raw_text = raw_response.text or "{}"

        usage_meta = getattr(raw_response, "usage_metadata", None)
        prompt_count = (
            (getattr(usage_meta, "prompt_token_count", 0) or 0) if usage_meta else len(str(request.messages)) // 4
        )
        completion_count = (
            (
                (getattr(usage_meta, "candidates_token_count", 0) or 0)
                + (getattr(usage_meta, "thoughts_token_count", 0) or 0)
            )
            if usage_meta
            else len(raw_text) // 4
        )
        # Validate structured JSON output against Pydantic schema
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            parsed = response_model.model_validate_json(cleaned_text)
        except Exception as exc:
            error = ModelOutputValidationError(f"Model output failed schema validation for {response_model.__name__}")
            setattr(error, "response_usage", (prompt_count, completion_count) if usage_meta is not None else None)
            raise error from exc

        # Token counting
        usage_meta = getattr(raw_response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else len(str(request.messages)) // 4
        comp_tokens = completion_count
        total_tokens = prompt_tokens + comp_tokens
        cost_usd = compute_token_cost(target_model, prompt_tokens, comp_tokens)

        get_telemetry().record_call(
            session_id=request.session_id,
            agent_id=request.agent_id,
            agent_role=request.agent_role,
            model=target_model,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            success=True,
        )

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=float(cost_usd),
        )

        response = LLMResponse(
            text=raw_text,
            usage_known=usage_meta is not None,
            usage=usage,
            model=target_model,
            raw=raw_response,
        )
        return parsed, response

    def count_tokens_if_supported(
        self, text_or_messages: str | list[LLMMessage], model: str | None = None
    ) -> int | None:
        """Estimate or compute token count using Gemini heuristic or character model."""
        return self.count_tokens(text_or_messages, model=model)

    def count_tokens(self, text_or_messages: str | list[LLMMessage], model: str | None = None) -> int:
        """Estimate token count for input text or message history."""
        if isinstance(text_or_messages, str):
            return max(1, len(text_or_messages) // 4)
        total_chars = sum(len(m.content) for m in text_or_messages)
        return max(1, total_chars // 4)

    def classify_error(self, error: Exception) -> Exception:
        """Classify raw Gemini/API exceptions into strongly typed SYNTRA LLM exceptions."""
        from syntra.llm.context import redact_secrets

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

        sanitized_msg = redact_secrets(str(error))
        err_lower = sanitized_msg.lower()
        if "quota" in err_lower or "429" in err_lower or "rate limit" in err_lower or "resource_exhausted" in err_lower:
            return ModelQuotaExceededError(f"Gemini API rate limit or quota exceeded: {sanitized_msg}")
        if "timeout" in err_lower or "timed out" in err_lower:
            return ModelTimeoutError(f"Gemini request timed out: {sanitized_msg}")
        if (
            "auth" in err_lower
            or "api_key" in err_lower
            or "permission" in err_lower
            or "403" in err_lower
            or "401" in err_lower
            or "unauthenticated" in err_lower
        ):
            return ModelAuthenticationError(f"Gemini authentication failed: {sanitized_msg}")
        if "503" in err_lower or "unavailable" in err_lower or "connection" in err_lower or "reset" in err_lower:
            return ModelProviderUnavailableError(f"Gemini service unavailable: {sanitized_msg}")
        return ModelProviderUnavailableError(f"Gemini request failed: {sanitized_msg}")
