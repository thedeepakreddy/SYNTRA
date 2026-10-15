"""Operational contracts and deterministic execution for every specialist role."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from syntra.agents.operational import AgentInvocation, AgentRegistry, SpecialistAgent
from syntra.domain.entities import AgentRole
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.runtime import ModelRuntime
from syntra.llm.schemas import RequirementsAnalysis
from syntra.skills.profiles import get_agent_profile
from syntra.skills.registry import SkillRegistry


def make_registry():
    skills = SkillRegistry()
    skills.discover_skills()
    return AgentRegistry(skills, model_name="mock-model")


def invocation(role=AgentRole.PRODUCT_MANAGER, **extra):
    return AgentInvocation(
        org_id=uuid4(),
        mission_id=uuid4(),
        role=role,
        objective="Analyze the approved fixture task",
        deadline=datetime.now(UTC) + timedelta(seconds=60),
        approved_capabilities=get_agent_profile(role).allowed_tool_capabilities,
        **extra,
    )


@pytest.mark.parametrize("role", list(AgentRole))
def test_all_ten_definitions_resolve_valid_skills_and_schemas(role):
    registry = make_registry()
    definition = registry.get(role)
    assert definition.role == role and definition.maximum_turns > 0
    assert definition.master_skills and definition.input_schema is AgentInvocation
    for skill in definition.allowed_skill_ids:
        pkg = registry.skills.resolve_skill_version(skill)
        assert role.value in pkg.manifest.supported_roles
    definition.output_schema.model_json_schema()


async def test_pm_executes_runtime_with_progressive_skills_and_provenance():
    registry = make_registry()
    provider = MockModelProvider()
    provider.queue_response(
        RequirementsAnalysis(
            summary="Correct input validation in the fixture application",
            functional_requirements=["Reject amounts less than one"],
            risk_assessment="Invalid orders risk incorrect totals",
            acceptance_criteria=["Given an amount of zero, When submitted, Then reject it"],
        )
    )
    result = await SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(invocation())
    assert result.status == "SUCCEEDED"
    assert result.output.functional_requirements == ["Reject amounts less than one"]
    assert result.skill_versions == ["requirements-analysis@1.0.0"]
    assert result.model_id == "mock-model" and result.prompt_tokens > 0


async def test_pm_material_ambiguity_requires_clarification():
    registry = make_registry()
    provider = MockModelProvider()
    provider.queue_response(
        RequirementsAnalysis(
            summary="Unknown input validation behavior requires clarification",
            functional_requirements=["Validate amount"],
            risk_assessment="Behavior is unspecified",
            acceptance_criteria=["Given an invalid amount, When submitted, Then follow the approved policy"],
            open_questions=["Should zero be permitted?"],
        )
    )
    result = await SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(invocation())
    assert result.status == "NEEDS_CLARIFICATION"


@pytest.mark.parametrize("skills", [["unknown"], ["backend-api-development"]])
async def test_unknown_or_unauthorized_skill_fails_before_model(skills):
    registry = make_registry()
    provider = MockModelProvider()
    with pytest.raises(ValueError, match="skill"):
        await SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(invocation(skill_ids=skills))
    assert not provider.call_history


def test_unknown_role_and_duplicate_registration_rejected():
    registry = make_registry()
    with pytest.raises(ValueError):
        registry.get("random_role")
    with pytest.raises(ValueError, match="Duplicate"):
        registry.register(registry.get(AgentRole.PRODUCT_MANAGER))


async def test_cancelled_invocation_does_not_call_model():
    import asyncio

    registry = make_registry()
    provider = MockModelProvider()
    cancelled = asyncio.Event()
    cancelled.set()
    result = await SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(
        invocation(), cancellation=cancelled
    )
    assert result.status == "CANCELLED" and not provider.call_history


def role_output(role):
    from syntra.agents.operational import QAProposal, SecurityReport
    from syntra.llm.schemas import (
        AgentFinalResult,
        ArchitectureProposal,
        CodeReviewProposal,
        FailureAnalysis,
        TaskPlanItem,
        TaskPlanProposal,
    )

    if role == AgentRole.PRODUCT_MANAGER:
        return RequirementsAnalysis(
            summary="Validate quantities in the controlled test application",
            functional_requirements=["Reject zero"],
            acceptance_criteria=["Given zero, When submitted, Then reject"],
            risk_assessment="Invalid orders risk incorrect totals",
        )
    if role == AgentRole.SOFTWARE_ARCHITECT:
        return ArchitectureProposal(
            title="Minimal validation architecture",
            architectural_decisions=["Keep FastAPI"],
            component_contracts=["Preserve POST /orders"],
            data_persistence_spec="No persistence change",
            security_invariants=["Reject invalid requests"],
            tradeoffs_and_alternatives=["Minimal compatible fix"],
            requirement_refs=["Reject zero"],
        )
    if role == AgentRole.ENGINEERING_MANAGER:
        return TaskPlanProposal(
            plan_summary="One bounded task with independently verifiable output",
            tasks=[
                TaskPlanItem(
                    task_key="FIX-1",
                    role="backend_engineer",
                    objective="Correct validation",
                    acceptance_criteria=["Zero rejected"],
                    required_skills=["backend-api-development"],
                    required_capabilities=["syntra.read_file"],
                    expected_artifacts=["UnifiedDiff"],
                    verification_requirements=["HTTP tests"],
                )
            ],
            critical_path=["FIX-1"],
        )
    if role == AgentRole.QA_ENGINEER:
        return QAProposal(
            test_plan=["Check zero and negative quantities"],
            acceptance_commands=["python -m pytest tests"],
            requirement_refs=["Reject zero"],
        )
    if role == AgentRole.CODE_REVIEWER:
        return CodeReviewProposal(
            verdict="APPROVED",
            summary_evaluation="Reviewed the actual patch against scoped acceptance evidence",
            checklist_verifications={"scope": True},
            test_coverage_adequate=True,
        )
    if role == AgentRole.SECURITY_REVIEWER:
        return SecurityReport(
            summary="No high severity finding in the supplied patch",
            findings=[],
            limitations=["Model reasoning alone is not a complete audit"],
        )
    if role == AgentRole.DEBUGGING_SPECIALIST:
        return FailureAnalysis(
            error_type="AssertionError",
            root_cause_hypothesis="Zero bypasses the existing negative-only guard",
            reproducing_steps=["Submit a zero quantity"],
            affected_components=["app.py"],
            proposed_surgical_fix="Reject nonpositive quantities and add an independent regression",
        )
    return AgentFinalResult(
        summary="Implementation proposal produced for independent sandbox verification",
        verdict="SUCCESS",
        evidence_notes=["This unit check validates the role contract, not source execution"],
    )


@pytest.mark.parametrize("role", list(AgentRole))
async def test_each_specialist_executes_a_typed_model_turn(role):
    registry = make_registry()
    provider = MockModelProvider()
    provider.queue_response(role_output(role))
    result = await SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(invocation(role))
    assert result.status == "SUCCEEDED"
    assert isinstance(result.output, registry.get(role).output_schema)
    assert provider.call_history[0].agent_role == role.value
    assert result.prompt_version == "1.0.0" and result.skill_versions


async def test_cancellation_during_provider_call_stops_the_agent():
    import asyncio

    from syntra.llm.models import LLMResponse

    registry = make_registry()
    provider = MockModelProvider()
    # Use a tool-capable turn so the custom asynchronous provider handler is used.
    from syntra.llm.models import ToolDefinition

    entered = asyncio.Event()

    async def blocked(request):
        entered.set()
        await asyncio.sleep(30)
        return LLMResponse(text="late")

    provider.set_handler(blocked)
    cancel = asyncio.Event()
    task = asyncio.create_task(
        SpecialistAgent(registry, ModelRuntime(provider, registry.skills)).execute(
            invocation(),
            tools=[ToolDefinition(name="syntra.read_file", description="Read", parameters={"type": "object"})],
            cancellation=cancel,
        )
    )
    await asyncio.wait_for(entered.wait(), timeout=1)
    cancel.set()
    result = await asyncio.wait_for(task, timeout=1)
    assert result.status == "CANCELLED" and result.prompt_tokens > 0
