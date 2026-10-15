"""Bounded execution must fail closed even with an uncooperative provider."""

import asyncio
from decimal import Decimal

import pytest

from syntra.llm.exceptions import (
    ModelBudgetExceededError,
    ModelOutputValidationError,
    ModelTimeoutError,
    ModelToolExecutionError,
)
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.models import LLMResponse, ToolDefinition
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.llm.schemas import RequirementsAnalysis


async def test_turn_limit_is_failure_and_usage_survives():
    provider = MockModelProvider()
    provider.queue_response(
        {"text": "one more tool", "tool_calls": [{"id": "t1", "name": "syntra.read_file", "arguments": {}}]}
    )

    class Gateway:
        async def execute_tool_call(self, request, uow=None):
            from syntra.mcp.types import MCPInvocationResult

            return MCPInvocationResult(invocation_id=request.invocation_id, status="SUCCESS", raw_output="text")

    meter = RuntimeUsage(max_tokens=100000, max_cost_usd=Decimal("1"))
    runtime = ModelRuntime(provider, tool_gateway=Gateway())
    with pytest.raises(ModelOutputValidationError, match="turn limit"):
        await runtime.execute_turn(
            "backend_engineer",
            "inspect",
            model_name="mock-model",
            max_tool_steps=1,
            usage_meter=meter,
            available_tools=[
                ToolDefinition(name="syntra.read_file", description="read", parameters={"type": "object"})
            ],
        )
    assert meter.total_tokens > 0 and meter.tool_calls == 1


async def test_unadvertised_tool_is_never_dispatched():
    provider = MockModelProvider()
    provider.queue_response(
        {"tool_calls": [{"id": "attack", "name": "syntra.run_command", "arguments": {"command": "whoami"}}]}
    )
    runtime = ModelRuntime(provider)
    with pytest.raises(ModelToolExecutionError, match="advertised"):
        await runtime.execute_turn("product_manager", "ignore repository injection", model_name="mock-model")


async def test_runtime_enforces_deadline_for_any_provider():
    provider = MockModelProvider()

    async def stall(request):
        await asyncio.sleep(10)
        return LLMResponse(text="late")

    provider.set_handler(stall)
    with pytest.raises(ModelTimeoutError):
        await ModelRuntime(provider).execute_turn(
            "backend_engineer", "bounded", model_name="mock-model", timeout_seconds=0.02
        )


async def test_cost_ceiling_prevents_provider_call():
    provider = MockModelProvider()
    meter = RuntimeUsage(max_tokens=100000, max_cost_usd=Decimal("0"))
    with pytest.raises(ModelBudgetExceededError):
        await ModelRuntime(provider).execute_turn(
            "backend_engineer", "bounded", model_name="gemini-2.5-flash", usage_meter=meter
        )
    assert provider.call_history == []


async def test_empty_constructed_schema_is_rejected():
    with pytest.raises(ModelOutputValidationError):
        await ModelRuntime(MockModelProvider()).execute_turn(
            "product_manager", "requirements", model_name="mock-model", response_model=RequirementsAnalysis
        )
