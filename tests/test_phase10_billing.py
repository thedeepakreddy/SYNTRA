"""SDK contract checks are offline and do not assert live provider access."""

from types import SimpleNamespace
from decimal import Decimal

import pytest

from syntra.llm.gemini_provider import GeminiModelProvider
from syntra.llm.provider import ModelRequest
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.llm.exceptions import ModelOutputValidationError
from syntra.llm.schemas import RequirementsAnalysis


def sdk_provider(text):
    captured = {}
    async def generate_content(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(prompt_token_count=10,
            candidates_token_count=3, thoughts_token_count=7))
    provider = GeminiModelProvider()
    provider._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    return provider, captured


async def test_structured_generation_honors_output_cap_and_accounts_thinking():
    output = RequirementsAnalysis(summary="Correct input validation in an authorized fixture",
        functional_requirements=["Reject zero"], acceptance_criteria=["Given zero, When submitted, Then reject"],
        risk_assessment="Invalid orders must be rejected")
    provider, captured = sdk_provider(output.model_dump_json())
    _, response = await provider.generate_structured(ModelRequest(messages=[], model="gemini-2.5-flash", max_tokens=11,
        max_provider_retries=0), RequirementsAnalysis)
    assert captured["config"].max_output_tokens == 11
    assert response.usage.prompt_tokens == 10 and response.usage.completion_tokens == 10
    assert response.usage.total_tokens == 20


async def test_invalid_structured_response_retains_measured_billed_usage():
    provider, _ = sdk_provider('{"invalid_contract": true}')
    meter = RuntimeUsage(max_tokens=100000, max_cost_usd=Decimal("0.25"))
    with pytest.raises(ModelOutputValidationError):
        await ModelRuntime(provider).execute_turn("product_manager", "Analyze fixture validation",
            model_name="gemini-2.5-flash", response_model=RequirementsAnalysis, usage_meter=meter)
    assert meter.prompt_tokens == 10 and meter.completion_tokens == 10
    assert meter.cost_usd > 0 and not meter.unknown_usage


async def test_unknown_model_cannot_borrow_another_models_pricing():
    from syntra.llm.mock_provider import MockModelProvider
    from syntra.llm.exceptions import ModelProviderUnavailableError
    provider = MockModelProvider()
    with pytest.raises(ModelProviderUnavailableError):
        await ModelRuntime(provider).execute_turn("backend_engineer", "Inspect a controlled fixture", model_name="unregistered-expensive-model")
    assert not provider.call_history
