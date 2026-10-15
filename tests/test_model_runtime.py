"""Comprehensive test suite for SYNTRA Phase 6: Gemini Integration and Model Runtime.

Deterministic tests for the 12 required behaviors:
1. Provider selection
2. Structured response validation
3. Invalid output
4. Model timeout
5. Rate limits
6. Retry exhaustion
7. Budget accounting & reconciliation
8. Tool-call authorization
9. Prompt version recording
10. Context truncation
11. Secret redaction
12. Cancellation
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.domain.entities import AgentRole
from syntra.llm import (
    AgentContextBuilder,
    GeminiModelProvider,
    LLMMessage,
    MessageRole,
    MockModelProvider,
    ModelBudgetExceededError,
    ModelOutputValidationError,
    ModelQuotaExceededError,
    ModelRequest,
    ModelRetryExhaustedError,
    ModelRouter,
    ModelRuntime,
    ModelTier,
    ModelTimeoutError,
    RequirementsAnalysis,
    ToolDefinition,
    compute_token_cost,
    get_model_spec,
)
from syntra.llm.context import redact_secrets
from syntra.mcp.client_manager import MCPClientManager
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.policy import CapabilityPolicyEngine
from syntra.mcp.registry import MCPRegistry
from syntra.mcp.types import MCPInvocationResult
from syntra.persistence.models import BudgetModel
from syntra.skills.registry import SkillRegistry


@pytest.fixture
def skill_registry() -> SkillRegistry:
    reg = SkillRegistry(root_dir=Path("skills"))
    reg.discover_skills()
    return reg


@pytest.fixture
def mock_gateway() -> ToolGateway:
    mcp_reg = MCPRegistry()
    policy_eng = CapabilityPolicyEngine()
    client_mgr = MCPClientManager(registry=mcp_reg)
    return ToolGateway(registry=mcp_reg, policy_engine=policy_eng, client_manager=client_mgr)


# ==============================================================================
# 1. Provider Selection
# ==============================================================================


def test_01_provider_selection():
    """Verify provider and tier resolution from agent role and models.yaml registry."""
    # Architect and Reviewer resolve to reasoning tier
    assert "pro" in ModelRouter.resolve_model("architect")
    assert "pro" in ModelRouter.resolve_model(AgentRole.SOFTWARE_ARCHITECT.value)
    assert "pro" in ModelRouter.resolve_model(AgentRole.PRODUCT_MANAGER.value)
    assert "pro" in ModelRouter.resolve_model(AgentRole.CODE_REVIEWER.value)

    # Coder and Tester resolve to balanced tier
    assert "flash" in ModelRouter.resolve_model("coder")
    assert "flash" in ModelRouter.resolve_model(AgentRole.BACKEND_ENGINEER.value)
    assert "flash" in ModelRouter.resolve_model(AgentRole.QA_ENGINEER.value)

    # Summarizer resolves to fast tier
    assert "lite" in ModelRouter.resolve_model("summarizer")

    # Explicit request overrides default
    assert ModelRouter.resolve_model(requested_model="custom-model") == "custom-model"

    # Verify ModelSpec details
    pro_spec = get_model_spec("gemini-2.5-pro")
    assert pro_spec.tier == ModelTier.REASONING
    assert pro_spec.context_window_tokens >= 2_000_000
    assert pro_spec.cost_per_input_token == Decimal("0.00000125")
    assert pro_spec.cost_per_output_token == Decimal("0.00000500")

    flash_spec = get_model_spec("gemini-2.5-flash")
    assert flash_spec.tier == ModelTier.BALANCED
    assert flash_spec.cost_per_input_token == Decimal("0.00000015")
    assert flash_spec.cost_per_output_token == Decimal("0.00000060")


# ==============================================================================
# 2. Structured Response Validation
# ==============================================================================


@pytest.mark.asyncio
async def test_02_structured_response_validation():
    """Verify strongly typed Task 3 output contracts validate accurately."""
    provider = MockModelProvider()
    prd_output = RequirementsAnalysis(
        summary="User Authentication and Session Management Service",
        functional_requirements=["User Registration", "Password Login", "JWT Issue"],
        acceptance_criteria=["Given valid credentials, When POST /login, Then return 200 with JWT"],
        risk_assessment="Brute-force attacks mitigated by rate limiter",
    )
    provider.queue_response(prd_output)

    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Analyze requirements for auth")],
        agent_role="product_manager",
    )
    parsed, resp = await provider.generate_structured(req, RequirementsAnalysis)

    assert isinstance(parsed, RequirementsAnalysis)
    assert parsed.summary == "User Authentication and Session Management Service"
    assert len(parsed.functional_requirements) == 3
    assert len(parsed.acceptance_criteria) == 1
    assert resp.usage.total_tokens > 0


# ==============================================================================
# 3. Invalid Output
# ==============================================================================


@pytest.mark.asyncio
async def test_03_invalid_output():
    """Verify invalid or malformed structured output is strictly rejected without silent defaults."""
    provider = MockModelProvider()
    # Missing required 'summary', 'functional_requirements', 'acceptance_criteria', 'risk_assessment'
    provider.queue_response('{"irrelevant_key": "some value"}')

    req = ModelRequest(
        messages=[LLMMessage(role=MessageRole.USER, content="Analyze requirements")],
        agent_role="product_manager",
    )
    with pytest.raises(ModelOutputValidationError, match="Mock JSON parsing failed"):
        await provider.generate_structured(req, RequirementsAnalysis)


# ==============================================================================
# 4. Model Timeout
# ==============================================================================


@pytest.mark.asyncio
async def test_04_model_timeout():
    """Verify requests exceeding timeout raise ModelTimeoutError."""
    provider = GeminiModelProvider(api_key="mock_key")

    async def _slow_call():
        await asyncio.sleep(0.5)
        return "slow_result"

    with pytest.raises(ModelTimeoutError, match="timed out after 0.0s"):
        await provider._execute_with_retry(
            _slow_call,
            timeout_seconds=0.02,
            retries=0,
        )


# ==============================================================================
# 5. Rate Limits
# ==============================================================================


@pytest.mark.asyncio
async def test_05_rate_limits():
    """Verify 429 quota exceptions are mapped to ModelQuotaExceededError."""
    provider = GeminiModelProvider(api_key="mock_key")

    async def _quota_exhausted():
        raise Exception("429 Resource has been exhausted (rate limit exceeded)")

    with pytest.raises(ModelQuotaExceededError, match="rate limit or quota exceeded"):
        await provider._execute_with_retry(_quota_exhausted, timeout_seconds=1.0, retries=0)


# ==============================================================================
# 6. Retry Exhaustion
# ==============================================================================


@pytest.mark.asyncio
async def test_06_retry_exhaustion():
    """Verify bounded retry policy exhausts retries after configured attempts."""
    provider = GeminiModelProvider(api_key="mock_key")
    call_count = 0

    async def _transient_fail():
        nonlocal call_count
        call_count += 1
        raise Exception("503 Service Unavailable in cluster")

    with pytest.raises(ModelRetryExhaustedError, match="failed after 2 retries"):
        await provider._execute_with_retry(
            _transient_fail,
            timeout_seconds=5.0,
            retries=2,
            initial_delay=0.01,
        )

    # 1 initial attempt + 2 retries = 3 total attempts
    assert call_count == 3


# ==============================================================================
# 7. Budget Accounting & Reconciliation
# ==============================================================================


@pytest.mark.asyncio
async def test_07_budget_accounting_and_reconciliation(skill_registry: SkillRegistry):
    """Verify budget reservation, token accounting, and mission limit halts."""
    # Pricing formula check
    cost = compute_token_cost("gemini-2.5-flash", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == Decimal("0.75")  # $0.15 + $0.60 = $0.75

    pro_cost = compute_token_cost("gemini-2.5-pro", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert pro_cost == Decimal("6.25")  # $1.25 + $5.00 = $6.25

    # Budget limit enforcement
    provider = MockModelProvider()
    provider.queue_response("Simulated model output")

    runtime = ModelRuntime(provider=provider, skill_registry=skill_registry)

    class MockBudgetRepo:
        def __init__(self):
            self.model = BudgetModel(mission_id=uuid4(), max_tokens=100, max_cost_usd=Decimal("1.0"))
            self.model.consumed_tokens = 100
            self.model.consumed_cost_usd = Decimal("0.0")

        async def get_for_mission(self, mission_id):
            return self.model

    class MockUOW:
        def __init__(self):
            self.budgets = MockBudgetRepo()

    uow = MockUOW()
    with pytest.raises(ModelBudgetExceededError, match="Token budget exceeded for mission"):
        await runtime.execute_turn(
            agent_role="backend_engineer",
            user_prompt="Exceed remaining budget",
            mission_id=uuid4(),
            task_id=uuid4(),
            uow=uow,  # type: ignore[arg-type]
        )


# ==============================================================================
# 8. Tool-Call Authorization
# ==============================================================================


@pytest.mark.asyncio
async def test_08_tool_call_authorization(
    skill_registry: SkillRegistry,
    mock_gateway: ToolGateway,
):
    """Verify ModelRuntime routes model tool calls through MCP Gateway and records outcomes."""
    provider = MockModelProvider()

    provider.queue_response(
        {
            "text": "I will search workspace.",
            "tool_calls": [
                {
                    "id": "tc-501",
                    "name": "syntra.workspace_search",
                    "arguments": {"pattern": "def "},
                }
            ],
        }
    )
    provider.queue_response("Search completed with 5 files found.")

    async def _mock_exec(req, uow=None):
        return MCPInvocationResult(
            invocation_id=uuid4(),
            status="SUCCESS",
            raw_output="Found 5 matches in src/",
            is_error=False,
        )

    mock_gateway.execute_tool_call = _mock_exec  # type: ignore[assignment]

    runtime = ModelRuntime(
        provider=provider,
        skill_registry=skill_registry,
        tool_gateway=mock_gateway,
    )

    result = await runtime.execute_turn(
        agent_role="backend_engineer",
        user_prompt="Search workspace",
        mission_id=uuid4(),
        task_id=uuid4(),
        available_tools=[
            ToolDefinition(
                name="syntra.workspace_search", description="Search workspace", parameters={"type": "object"}
            )
        ],
    )

    assert result.text == "Search completed with 5 files found."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "syntra.workspace_search"
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["status"] == "SUCCESS"
    assert "Found 5 matches" in result.tool_results[0]["output"]


# ==============================================================================
# 9. Prompt Version Recording
# ==============================================================================


@pytest.mark.asyncio
async def test_09_prompt_version_recording(skill_registry: SkillRegistry):
    """Verify prompt version is recorded in runtime telemetry and context assembly."""
    provider = MockModelProvider()
    provider.queue_response("Task completed")

    runtime = ModelRuntime(provider=provider, skill_registry=skill_registry)

    result = await runtime.execute_turn(
        agent_role="software_architect",
        user_prompt="Design high level architecture",
        prompt_version="1.0.0",
    )

    assert result.prompt_version == "1.0.0"
    assert result.agent_role == "software_architect"
    assert result.validation_outcome == "SUCCESS"
    assert result.model_id == "gemini-2.5-pro"


# ==============================================================================
# 10. Context Truncation
# ==============================================================================


def test_10_context_truncation(skill_registry: SkillRegistry):
    """Verify ContextBuilder truncates older messages when token allocation limit is exceeded."""
    builder = AgentContextBuilder(skill_registry=skill_registry, max_context_tokens=100)

    # Create long history exceeding budget
    history = [
        LLMMessage(role=MessageRole.USER, content="Initial user instruction: Setup repo"),
        LLMMessage(role=MessageRole.ASSISTANT, content="A" * 500),  # ~125 tokens
        LLMMessage(role=MessageRole.USER, content="B" * 500),  # ~125 tokens
        LLMMessage(role=MessageRole.ASSISTANT, content="C" * 500),  # ~125 tokens
    ]

    system_instruction, messages = builder.build_context(
        agent_role="backend_engineer",
        user_prompt="Latest instruction: run tests",
        conversation_history=history,
        token_budget=150,
    )

    # Intermediate bloated messages were pruned, keeping total message count bounded
    assert len(messages) < len(history) + 1
    assert "Latest instruction: run tests" in messages[-1].content


# ==============================================================================
# 11. Secret Redaction
# ==============================================================================


def test_11_secret_redaction():
    """Verify secrets and API keys are redacted before entering LLM context."""
    raw_prompt = (
        "Configure service with AIzaSyD9xExampleKey1234567890abcdef and "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload and "
        "password = 'SuperSecretPassword123' and sk-proj-1234567890abcdef1234567890abcdef."
    )

    sanitized = redact_secrets(raw_prompt)

    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_BEARER_TOKEN]" in sanitized
    assert "[REDACTED_CREDENTIAL]" in sanitized
    assert "[REDACTED_API_TOKEN]" in sanitized


# ==============================================================================
# 12. Cancellation
# ==============================================================================


@pytest.mark.asyncio
async def test_12_cancellation(skill_registry: SkillRegistry):
    """Verify cancellation propagates cleanly without state corruption."""
    provider = MockModelProvider()

    async def _cancelled_call(req):
        raise asyncio.CancelledError()

    provider.set_handler(_cancelled_call)

    runtime = ModelRuntime(provider=provider, skill_registry=skill_registry)

    with pytest.raises(asyncio.CancelledError):
        await runtime.execute_turn(
            agent_role="backend_engineer",
            user_prompt="Task cancelled during execution",
        )
