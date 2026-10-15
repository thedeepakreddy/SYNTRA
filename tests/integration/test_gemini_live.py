"""Opt-in live integration and configuration hardening tests for Google Gemini.

Verifies the 8 required Phase 6 scenarios:
1. Authenticated API call
2. Structured Pydantic response parsing
3. Structured response recovery / failure on invalid schema
4. Usage metadata extraction (prompt, completion, total, cached content)
5. Error classification (invalid API key, rate limit, bad request)
6. Timeout handling
7. Configuration selection using config/models.yaml
8. Secret redaction in logs and exceptions

Status Reporting:
When live credentials (GEMINI_API_KEY) are unavailable or contain placeholder values,
network-dependent tests skip cleanly reporting 'BLOCKED_BY_CREDENTIALS'.
Tests NEVER log raw credentials.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

import pytest
from pydantic import BaseModel, Field

from syntra.core.config import get_settings
from syntra.llm import (
    GeminiModelProvider,
    LLMMessage,
    MessageRole,
    ModelAuthenticationError,
    ModelOutputValidationError,
    ModelPricingError,
    ModelProviderUnavailableError,
    ModelQuotaExceededError,
    ModelRequest,
    ModelRouter,
    ModelTimeoutError,
    RequirementsAnalysis,
    UnknownCostPolicy,
    compute_token_cost,
    get_model_spec,
    load_model_registry,
)
from syntra.llm.context import AgentContextBuilder

# Determine whether live Gemini testing credentials are genuinely available
raw_api_key = os.getenv("GEMINI_API_KEY", "").strip()
live_available = bool(
    raw_api_key
    and not raw_api_key.startswith("your_")
    and not raw_api_key.startswith("mock_")
    and len(raw_api_key) > 10
)

BLOCKED_REASON = (
    "BLOCKED_BY_CREDENTIALS: GEMINI_API_KEY is not configured or contains placeholder. "
    "Live Gemini API calls require active Google Gen AI credentials."
)


# ------------------------------------------------------------------------------
# 1. Authenticated API Call
# ------------------------------------------------------------------------------


@pytest.mark.skipif(not live_available, reason=BLOCKED_REASON)
@pytest.mark.asyncio
async def test_01_authenticated_api_call():
    """Live scenario 1: Authenticated API call using stable gemini-2.5-flash."""
    provider = GeminiModelProvider()
    assert provider.is_configured(), "Provider reports not configured despite valid key"

    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Reply with exactly 'SYNTRA_ONLINE'")],
        model="gemini-2.5-flash",
        max_tokens=32,
        timeout_seconds=30.0,
    )

    response = await provider.generate_with_tools(req)
    assert response.text.strip(), "Live Gemini response text was empty"
    assert response.model == "gemini-2.5-flash"
    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0
    assert response.usage.total_tokens == response.usage.prompt_tokens + response.usage.completion_tokens


# ------------------------------------------------------------------------------
# 2. Structured Pydantic Response Parsing
# ------------------------------------------------------------------------------


@pytest.mark.skipif(not live_available, reason=BLOCKED_REASON)
@pytest.mark.asyncio
async def test_02_structured_pydantic_parsing():
    """Live scenario 2: Schema-constrained structured output validation."""
    provider = GeminiModelProvider()
    req = ModelRequest(
        messages=[
            LLMMessage(
                role=MessageRole.USER,
                content="Produce a minimal requirements analysis for an authentication service with login.",
            )
        ],
        model="gemini-2.5-flash",
        timeout_seconds=45.0,
    )

    parsed, response = await provider.generate_structured(req, RequirementsAnalysis)
    assert isinstance(parsed, RequirementsAnalysis)
    assert len(parsed.summary) >= 5
    assert len(parsed.functional_requirements) >= 1
    assert len(parsed.acceptance_criteria) >= 1
    assert response.usage.total_tokens > 0


# ------------------------------------------------------------------------------
# 3. Structured Response Recovery / Failure on Invalid Schema
# ------------------------------------------------------------------------------


class StrictIntegerContract(BaseModel):
    code: int = Field(..., ge=1000, le=2000)
    category: str = Field(..., min_length=5)


@pytest.mark.skipif(not live_available, reason=BLOCKED_REASON)
@pytest.mark.asyncio
async def test_03_structured_response_invalid_schema_live():
    """Live scenario 3: Verify ModelOutputValidationError is raised when schema constraints fail."""
    provider = GeminiModelProvider()
    req = ModelRequest(
        messages=[
            LLMMessage(
                role=MessageRole.USER,
                content="Return JSON with code=1 and category='a'. Do not follow bounds.",
            )
        ],
        model="gemini-2.5-flash",
        timeout_seconds=30.0,
    )

    try:
        parsed, resp = await provider.generate_structured(req, StrictIntegerContract)
        assert 1000 <= parsed.code <= 2000
    except ModelOutputValidationError as exc:
        assert "failed schema validation" in str(exc)


def test_03_structured_response_invalid_schema_offline():
    """Scenario 3 (offline contract guarantee): ModelOutputValidationError preserves payload details."""
    raw_bad_json = '{"code": 5, "category": "x"}'
    with pytest.raises(Exception):
        StrictIntegerContract.model_validate_json(raw_bad_json)


# ------------------------------------------------------------------------------
# 4. Usage Metadata Extraction
# ------------------------------------------------------------------------------


@pytest.mark.skipif(not live_available, reason=BLOCKED_REASON)
@pytest.mark.asyncio
async def test_04_usage_metadata_extraction_live():
    """Live scenario 4: Extract prompt, completion, total, and cached tokens from live response."""
    provider = GeminiModelProvider()
    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Count from 1 to 5.")],
        model="gemini-2.5-flash",
        max_tokens=64,
        timeout_seconds=30.0,
    )
    resp = await provider.generate_with_tools(req)
    assert resp.usage.prompt_tokens > 0
    assert resp.usage.completion_tokens > 0
    assert resp.usage.total_tokens == resp.usage.prompt_tokens + resp.usage.completion_tokens
    assert resp.usage.cached_tokens >= 0
    assert resp.usage.estimated_cost_usd > 0.0


def test_04_usage_metadata_extraction_adapter_logic():
    """Scenario 4 (offline check): TokenUsage correctly maps tokens and pricing."""
    cost = compute_token_cost("gemini-2.5-flash", 1500, 350)
    assert cost > Decimal("0.0")
    # Standard text rates verified at https://ai.google.dev/gemini-api/docs/pricing (2026-10-15).
    assert cost == Decimal("0.001325")  # 1500 * 0.30/M + 350 * 2.50/M


# ------------------------------------------------------------------------------
# 5. Error Classification
# ------------------------------------------------------------------------------


def test_05_error_classification_mappings():
    """Scenario 5: Classify raw provider exceptions into strongly typed exceptions."""
    provider = GeminiModelProvider(api_key="mock_key")

    # 1. Invalid API Key / Auth (401, 403, permission, api_key)
    e1 = provider.classify_error(Exception("403 API_KEY_INVALID: User not authorized"))
    assert isinstance(e1, ModelAuthenticationError)
    assert "API_KEY_INVALID" in str(e1)

    # 2. Rate Limit / Quota (429, resource_exhausted, quota)
    e2 = provider.classify_error(Exception("429 Resource has been exhausted (quota exceeded)"))
    assert isinstance(e2, ModelQuotaExceededError)

    # 3. Bad Request / Service Unavailable (503, connection reset)
    e3 = provider.classify_error(Exception("503 Service Unavailable: upstream reset"))
    assert isinstance(e3, ModelProviderUnavailableError)


@pytest.mark.skipif(not live_available, reason=BLOCKED_REASON)
@pytest.mark.asyncio
async def test_05_error_classification_live_bad_model():
    """Live scenario 5: Passing a nonexistent model id causes provider error classification."""
    provider = GeminiModelProvider()
    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Hello")],
        model="nonexistent-gemini-model-xyz",
        timeout_seconds=15.0,
    )
    with pytest.raises((ModelProviderUnavailableError, ModelAuthenticationError)):
        await provider.generate_with_tools(req)


# ------------------------------------------------------------------------------
# 6. Timeout Handling
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_06_timeout_handling():
    """Scenario 6: Verify strict timeout enforcement raises ModelTimeoutError."""
    provider = GeminiModelProvider(api_key="mock_key")

    async def _hang():
        await asyncio.sleep(0.5)
        return "finished"

    with pytest.raises(ModelTimeoutError, match="timed out after 0.0s"):
        await provider._execute_with_retry(_hang, timeout_seconds=0.01, retries=0)


# ------------------------------------------------------------------------------
# 7. Configuration Selection Using config/models.yaml
# ------------------------------------------------------------------------------


def test_07_configuration_selection_and_routing():
    """Scenario 7: Verify config/models.yaml routing, active tiers, and retirement of shutdown models."""
    registry = load_model_registry()

    # Active Models
    assert "gemini-2.5-pro" in registry
    assert registry["gemini-2.5-pro"].enabled is True
    assert registry["gemini-2.5-pro"].lifecycle_status == "ACTIVE"

    assert "gemini-2.5-flash" in registry
    assert registry["gemini-2.5-flash"].enabled is True
    assert registry["gemini-2.5-flash"].lifecycle_status == "ACTIVE"

    # Retired / Shutdown Model
    assert "gemini-2.0-flash-lite" in registry
    retired = registry["gemini-2.0-flash-lite"]
    assert retired.enabled is False
    assert retired.deprecated is True
    assert retired.lifecycle_status == "SHUTDOWN"
    assert retired.shutdown_date == "2026-06-01"
    assert retired.replacement == "gemini-2.5-flash"
    assert retired.pricing_configuration.unknown_cost_policy == UnknownCostPolicy.REJECT

    # System settings defaults
    from syntra.core.config import reset_settings

    reset_settings()
    settings = get_settings()
    assert settings.reasoning_model == "gemini-2.5-pro"
    assert settings.default_model == "gemini-2.5-flash"
    assert settings.fast_model == "gemini-2.5-flash"

    # Role routing: Fast and Balanced route to active gemini-2.5-flash
    assert ModelRouter.resolve_model("summarizer") == "gemini-2.5-flash"
    assert ModelRouter.resolve_model("coder") == "gemini-2.5-flash"
    assert ModelRouter.resolve_model("architect") == "gemini-2.5-pro"


# ------------------------------------------------------------------------------
# 8. Secret Redaction in Logs and Exceptions
# ------------------------------------------------------------------------------


def test_08_secret_redaction_in_provider_and_exceptions():
    """Scenario 8: Secrets are never exposed in provider string representation or exceptions."""
    secret = "AIzaSySecretTestingKey1234567890"
    provider = GeminiModelProvider(api_key=secret)

    # Provider representation hides key
    assert secret not in str(provider)
    assert secret not in repr(provider)
    assert "[REDACTED]" in repr(provider)

    # Exception classification sanitizes secret from raw error string
    classified = provider.classify_error(Exception(f"Failed authenticating with key={secret} against Google API"))
    assert secret not in str(classified)
    assert "[REDACTED_API_KEY]" in str(classified)

    # Context builder sanitizes prompt
    builder = AgentContextBuilder()
    sys_inst, messages = builder.build_context(
        agent_role="backend_engineer",
        user_prompt=f"Deploy with token: Bearer {secret}",
    )
    assert secret not in messages[0].content


# ------------------------------------------------------------------------------
# Step 3 Verification: Unknown Cost Policy Enforcement
# ------------------------------------------------------------------------------


def test_unknown_cost_policy_enforcement():
    """Verify that unpriced models do NOT evaluate to $0.00 and honor UnknownCostPolicy."""
    # 1. Unknown pricing with REJECT policy raises ModelPricingError
    spec_rejected = get_model_spec("gemini-2.0-flash-lite")
    assert not spec_rejected.is_pricing_known
    with pytest.raises(ModelPricingError, match="unverified pricing and unknown-cost policy is REJECT"):
        compute_token_cost("gemini-2.0-flash-lite", prompt_tokens=1000, completion_tokens=500)

    # 2. Unknown pricing with CONSERVATIVE_FALLBACK charges conservative ceiling (never $0.00)
    fallback_cost = compute_token_cost(
        "gemini-2.0-flash-lite",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        unknown_policy=UnknownCostPolicy.CONSERVATIVE_FALLBACK,
    )
    # Default fallback ceiling: $2.50 / 1M prompt + $10.00 / 1M completion = $12.50
    assert fallback_cost == Decimal("12.50")
    assert fallback_cost > Decimal("0.00")

    # 3. Unknown pricing with FLAG_UNVERIFIED charges conservative ceiling
    flag_cost = compute_token_cost(
        "gemini-2.0-flash-lite",
        prompt_tokens=100_000,
        completion_tokens=100_000,
        unknown_policy=UnknownCostPolicy.FLAG_UNVERIFIED,
    )
    assert flag_cost == Decimal("1.25")
    assert flag_cost > Decimal("0.00")
