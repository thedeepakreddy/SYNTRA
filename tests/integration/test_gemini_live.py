"""Opt-in live integration test for Google Gemini models via google-genai SDK.

This test requires a valid, funded GEMINI_API_KEY. It is skipped automatically
in offline, CI, or mock test environments to prevent unverified failure or unexpected cost.
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel, Field

from syntra.llm.gemini_provider import GeminiModelProvider
from syntra.llm.models import LLMMessage, MessageRole
from syntra.llm.provider import ModelRequest
from syntra.llm.schemas import RequirementsAnalysis

# Determine whether live Gemini testing is configured
raw_api_key = os.getenv("GEMINI_API_KEY", "").strip()
live_available = bool(
    raw_api_key
    and not raw_api_key.startswith("your_")
    and not raw_api_key.startswith("mock_")
    and len(raw_api_key) > 10
)


class SimpleHealthCheck(BaseModel):
    status: str = Field(..., description="System health status (e.g. 'OK')")
    latency_ms: int = Field(default=0)


@pytest.mark.skipif(
    not live_available,
    reason="GEMINI_API_KEY is not configured or valid. Live Gemini integration remains UNVERIFIED in this environment.",
)
@pytest.mark.asyncio
async def test_live_gemini_text_generation():
    """Live connectivity verification: execute asynchronous generation with Gemini 2.5 Flash."""
    provider = GeminiModelProvider()
    assert provider.is_configured(), "Gemini provider reports not configured despite valid key"

    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Reply with exactly 'SYNTRA_GEMINI_ONLINE'")],
        model="gemini-2.5-flash",
        max_tokens=64,
        timeout_seconds=30.0,
    )

    response = await provider.generate_with_tools(req)
    assert response.text, "Live Gemini response text was empty"
    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0
    assert response.usage.estimated_cost_usd >= 0.0


@pytest.mark.skipif(
    not live_available,
    reason="GEMINI_API_KEY is not configured or valid. Live Gemini integration remains UNVERIFIED in this environment.",
)
@pytest.mark.asyncio
async def test_live_gemini_structured_output():
    """Live connectivity verification: execute schema-constrained structured output."""
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
    assert len(parsed.summary) >= 10
    assert len(parsed.functional_requirements) >= 1
    assert len(parsed.acceptance_criteria) >= 1
    assert response.usage.total_tokens > 0
