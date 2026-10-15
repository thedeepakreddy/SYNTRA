"""Independent behavioral acceptance tests derived from Phase10 sections 17–30.

Real repositories, artifact storage, runtime, MCP gateway and role policies run
against disposable SQLite state. Provider responses and container effects are
controlled doubles: these tests do not claim live Gemini or Docker verification.
Defects remain ordinary failing tests, never xfails or relaxed assertions.
"""

import asyncio
import base64
import hashlib
import posixpath
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_scheduling_phase8 import setup_test_org_and_mission

from syntra.agents.engineering_worker import EngineeringSandboxWorker
from syntra.agents.handoffs import (
    RoleArtifact,
    consume_handoff,
    persist_role_result,
    require_independent_review,
)
from syntra.agents.operational import (
    AgentInvocation,
    AgentRegistry,
    AgentResult,
    SpecialistAgent,
)
from syntra.agents.sandbox_gateway import build_sandbox_gateway
from syntra.core.telemetry import TokenUsage
from syntra.domain.entities import (
    AgentRole,
    ApprovalDecision,
    ArtifactType,
    AttemptState,
    MembershipRole,
    MissionState,
    TaskState,
)
from syntra.domain.exceptions import CrossTenantAccessError, DomainError
from syntra.llm.config import compute_token_cost
from syntra.llm.exceptions import (
    ModelBudgetExceededError,
    ModelOutputValidationError,
    ModelToolExecutionError,
)
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.models import LLMResponse, ToolDefinition
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.llm.schemas import AgentFinalResult, CodeReviewProposal, RequirementsAnalysis
from syntra.mcp.types import MCPInvocationRequest, MCPInvocationResult
from syntra.orchestration.engineering_service import EngineeringMissionService
from syntra.persistence.artifact_store import read_artifact, store_artifact
from syntra.persistence.models import (
    CapabilityGrantModel,
    MembershipModel,
    UsageRecordModel,
    UserModel,
    WorkerLeaseModel,
)
from syntra.sandbox.models import ContainerConfig, ExecutionResult, SandboxLease
from syntra.scheduling.consumer import SandboxWorkerConsumer
from syntra.scheduling.models import EngineeringTaskSpecification, TaskDispatchPayload, TaskExecutionResult
from syntra.scheduling.scheduler import TaskScheduler
from syntra.skills.profiles import get_agent_profile
from syntra.skills.registry import SkillRegistry

pytest_plugins = ["test_scheduling_phase8"]


@pytest.fixture
def qa_registry():
    skills = SkillRegistry()
    skills.discover_skills()
    return AgentRegistry(skills, model_name="mock-model")


@pytest.fixture
async def qa_scope(uow_factory):
    async with uow_factory() as uow:
        org, mission, plan = await setup_test_org_and_mission(uow, mission_state=MissionState.PLANNING)
        other_org, other_mission, _ = await setup_test_org_and_mission(uow)
        owner = await uow.missions.get_by_id_for_org(mission, org)
        task = await uow.tasks.create_task(
            uuid4(),
            plan,
            mission,
            org,
            "QA-10",
            "Correct input validation",
            "Reject nonpositive quantities",
            AgentRole.BACKEND_ENGINEER.value,
        )
        await uow.commit()
        return SimpleNamespace(
            org=org,
            mission=mission,
            plan=plan,
            project=owner.project_id,
            task=task.id,
            other_org=other_org,
            other_mission=other_mission,
        )


def qa_invocation(scope=None, **changes):
    role = changes.get("role", AgentRole.PRODUCT_MANAGER)
    values = {
        "org_id": scope.org if scope else uuid4(),
        "mission_id": scope.mission if scope else uuid4(),
        "task_id": scope.task if scope else None,
        "role": role,
        "approved_capabilities": get_agent_profile(role).allowed_tool_capabilities,
        "objective": "Reject nonpositive quantities and preserve positive inputs",
        "deadline": datetime.now(UTC) + timedelta(seconds=30),
    }
    return AgentInvocation(**(values | changes))


def independent_requirements():
    return RequirementsAnalysis(
        summary="Validate order quantities at the existing application boundary",
        functional_requirements=["Reject nonpositive integer quantities", "Accept positive integer quantities"],
        acceptance_criteria=[
            "Given a quantity of zero, When creating an order, Then reject the order",
            "Given a positive quantity, When creating an order, Then preserve that quantity",
        ],
        risk_assessment="Boundary errors can accept invalid orders",
        out_of_scope=["Production deployment"],
    )


def qa_result(invocation, **changes):
    values = {
        "invocation_id": invocation.invocation_id,
        "role": invocation.role,
        "status": "SUCCEEDED",
        "model_id": "mock-model",
        "output": independent_requirements(),
    }
    return AgentResult(**(values | changes))


async def persisted_handoff(uow, scope):
    invocation = qa_invocation(scope)
    handoff = await persist_role_result(
        uow,
        invocation,
        qa_result(invocation),
        AgentRole.SOFTWARE_ARCHITECT,
    )
    await uow.commit()
    return handoff


async def consume(uow, registry, handoff, **changes):
    values = {
        "org_id": handoff.org_id,
        "mission_id": handoff.mission_id,
        "consumer_role": handoff.consumer_role,
    }
    return await consume_handoff(uow, registry, handoff, **(values | changes))


async def test_handoff_round_trip_hashes_actual_durable_bytes(uow_factory, qa_scope, qa_registry):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
    # Read through a new transaction, not the producer's in-memory result.
    async with uow_factory() as uow:
        body = await read_artifact(
            uow,
            artifact_id=ref.artifact_id,
            mission_id=ref.mission_id,
            org_id=ref.org_id,
        )
        assert hashlib.sha256(body.encode()).hexdigest() == ref.artifact_hash
        assert RoleArtifact.model_validate_json(body).invocation_id == ref.invocation_id
        assert await consume(uow, qa_registry, ref) == independent_requirements()


@pytest.mark.parametrize("corruption", ["payload", "stored_hash", "handoff_hash", "size", "version", "missing"])
async def test_handoff_rejects_missing_stale_or_tampered_artifacts(
    uow_factory,
    qa_scope,
    qa_registry,
    corruption,
):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
        _, body = await uow.artifacts.get_by_id(ref.artifact_id)
        if corruption == "payload":
            raw = base64.b64decode(body.storage_path[7:])
            # Same-length corruption must still fail the digest check.
            damaged = raw.replace(b"positive", b"negative", 1)
            assert damaged != raw and len(damaged) == len(raw)
            body.storage_path = "inline:" + base64.b64encode(damaged).decode()
        elif corruption == "stored_hash":
            body.sha256_checksum = "0" * 64
        elif corruption == "handoff_hash":
            ref = ref.model_copy(update={"artifact_hash": "0" * 64})
        elif corruption == "size":
            body.size_bytes += 1
        elif corruption == "version":
            ref = ref.model_copy(update={"artifact_version": 2})
        else:
            ref = ref.model_copy(update={"artifact_id": uuid4()})
        await uow.session.flush()
        with pytest.raises(ValueError):
            await consume(uow, qa_registry, ref)


@pytest.mark.parametrize("field", ["org_id", "mission_id", "consumer_role"])
async def test_handoff_cannot_cross_consumer_or_tenant_scope(uow_factory, qa_scope, qa_registry, field):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
        forged = {
            "org_id": qa_scope.other_org,
            "mission_id": qa_scope.other_mission,
            "consumer_role": AgentRole.BACKEND_ENGINEER,
        }
        with pytest.raises((ValueError, CrossTenantAccessError)):
            await consume(uow, qa_registry, ref, **{field: forged[field]})


async def test_relabeling_handoff_cannot_read_another_tenants_artifact(uow_factory, qa_scope, qa_registry):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
        forged = ref.model_copy(update={"org_id": qa_scope.other_org, "mission_id": qa_scope.other_mission})
        with pytest.raises((ValueError, CrossTenantAccessError)):
            await consume(uow, qa_registry, forged)


async def test_previous_plan_handoff_is_unusable_after_plan_revision(uow_factory, qa_scope, qa_registry):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        mission.active_plan_version = 2
        await uow.commit()
    async with uow_factory() as uow:
        with pytest.raises(ValueError, match="[Ss]tale|[Pp]lan"):
            await consume(uow, qa_registry, ref)


@pytest.mark.parametrize("field", ["org_id", "mission_id", "producer_role", "invocation_id", "task_id", "plan_version"])
async def test_valid_hash_does_not_excuse_envelope_provenance_mismatch(
    uow_factory,
    qa_scope,
    qa_registry,
    field,
):
    async with uow_factory() as uow:
        ref = await persisted_handoff(uow, qa_scope)
        _, stored = await uow.artifacts.get_by_id(ref.artifact_id)
        raw = base64.b64decode(stored.storage_path[7:]).decode()
        envelope = RoleArtifact.model_validate_json(raw)
        replacement = {
            "org_id": qa_scope.other_org,
            "mission_id": qa_scope.other_mission,
            "producer_role": AgentRole.CODE_REVIEWER,
            "invocation_id": uuid4(),
            "task_id": uuid4(),
            "plan_version": 2,
        }[field]
        rewritten = envelope.model_copy(update={field: replacement}).model_dump_json().encode()
        stored.storage_path = "inline:" + base64.b64encode(rewritten).decode()
        stored.sha256_checksum = hashlib.sha256(rewritten).hexdigest()
        stored.size_bytes = len(rewritten)
        ref = ref.model_copy(update={"artifact_hash": stored.sha256_checksum})
        await uow.session.flush()
        with pytest.raises(ValueError, match="[Pp]rovenance"):
            await consume(uow, qa_registry, ref)


@pytest.mark.parametrize("status", ["FAILED", "BLOCKED", "CANCELLED", "NEEDS_APPROVAL", "NEEDS_CLARIFICATION"])
async def test_unsuccessful_result_cannot_become_validated_handoff(uow_factory, qa_scope, status):
    async with uow_factory() as uow:
        inv = qa_invocation(qa_scope)
        with pytest.raises(ValueError):
            await persist_role_result(uow, inv, qa_result(inv, status=status), AgentRole.SOFTWARE_ARCHITECT)
        artifacts, _, _ = await uow.artifacts.list_for_mission(qa_scope.mission, qa_scope.org)
        assert artifacts == []


@pytest.mark.parametrize("invalidity", ["foreign_invocation", "wrong_output_contract"])
async def test_handoff_producer_rejects_result_with_invalid_identity_or_schema(uow_factory, qa_scope, invalidity):
    async with uow_factory() as uow:
        inv = qa_invocation(qa_scope)
        changes = (
            {"invocation_id": uuid4()}
            if invalidity == "foreign_invocation"
            else {
                "output": AgentFinalResult(
                    summary="An implementation result is not a requirements document",
                    verdict="SUCCESS",
                    evidence_notes=["Wrong role contract supplied deliberately"],
                ),
            }
        )
        with pytest.raises((ValueError, ValidationError)):
            await persist_role_result(uow, inv, qa_result(inv, **changes), AgentRole.SOFTWARE_ARCHITECT)


@pytest.mark.parametrize("reviewer", [AgentRole.QA_ENGINEER, AgentRole.CODE_REVIEWER, AgentRole.SECURITY_REVIEWER])
def test_independent_review_accepts_distinct_invocation_and_role(reviewer):
    require_independent_review(AgentRole.BACKEND_ENGINEER, reviewer, uuid4(), uuid4())


@pytest.mark.parametrize("reviewer", list(AgentRole))
def test_same_invocation_cannot_certify_itself_even_when_role_changes(reviewer):
    producer = uuid4()
    with pytest.raises(ValueError):
        require_independent_review(AgentRole.BACKEND_ENGINEER, reviewer, producer, producer)


@pytest.mark.parametrize(
    "reviewer", [AgentRole.BACKEND_ENGINEER, AgentRole.FRONTEND_ENGINEER, AgentRole.DEVOPS_ENGINEER]
)
def test_implementation_role_cannot_act_as_independent_reviewer(reviewer):
    with pytest.raises(ValueError):
        require_independent_review(AgentRole.BACKEND_ENGINEER, reviewer, uuid4(), uuid4())


@pytest.mark.parametrize("defect", ["rejected", "failed_check", "missing_coverage"])
async def test_review_output_cannot_approve_failed_checks(qa_registry, defect):
    provider = MockModelProvider()
    review = CodeReviewProposal(
        verdict="REJECTED" if defect == "rejected" else "APPROVED",
        summary_evaluation="Evaluate the supplied patch against independent acceptance evidence",
        checklist_verifications={"tests_pass": defect != "failed_check"},
        test_coverage_adequate=defect != "missing_coverage",
    )
    provider.queue_response(review)
    result = await SpecialistAgent(qa_registry, ModelRuntime(provider, qa_registry.skills)).execute(
        qa_invocation(role=AgentRole.CODE_REVIEWER),
    )
    assert result.status == "BLOCKED"


@pytest.mark.parametrize("limit", ["tokens", "cost"])
async def test_shared_meter_cannot_expand_invocation_budget(qa_registry, limit):
    provider = MockModelProvider()
    provider.queue_response(independent_requirements())
    inv = qa_invocation(**({"max_tokens": 1} if limit == "tokens" else {"max_cost_usd": Decimal("0")}))
    meter = RuntimeUsage(max_tokens=1_000_000, max_cost_usd=Decimal("10"))
    with pytest.raises(ModelBudgetExceededError):
        await SpecialistAgent(qa_registry, ModelRuntime(provider, qa_registry.skills)).execute(inv, usage_meter=meter)
    assert provider.call_history == [], "Budget denial must happen before provider effects"


class MeteredProvider(MockModelProvider):
    """A provider returning exact usage, including deliberate overspend responses."""

    def __init__(self, prompt_tokens, completion_tokens):
        super().__init__()
        self.reported_prompt = prompt_tokens
        self.reported_completion = completion_tokens

    async def generate_with_tools(self, request):
        response = await super().generate_with_tools(request)
        response.usage = TokenUsage(
            prompt_tokens=self.reported_prompt,
            completion_tokens=self.reported_completion,
            total_tokens=self.reported_prompt + self.reported_completion,
        )
        return response


@pytest.mark.parametrize("limit", ["tokens", "cost"])
async def test_provider_overspend_is_rejected_and_usage_is_preserved(limit):
    provider = MeteredProvider(1_000_000, 100)
    provider.queue_response("Completed output")
    meter = RuntimeUsage(
        2_000_000 if limit == "cost" else 100_000, Decimal("0.1") if limit == "cost" else Decimal("10")
    )
    with pytest.raises(ModelBudgetExceededError):
        await ModelRuntime(provider).execute_turn(
            "backend_engineer",
            "Bound the provider response",
            usage_meter=meter,
            model_name="gemini-2.5-flash" if limit == "cost" else "mock-model",
        )
    assert meter.total_tokens == 1_000_100
    assert meter.model_calls == 1
    if limit == "cost":
        assert meter.cost_usd == compute_token_cost("gemini-2.5-flash", 1_000_000, 100)


async def test_runtime_shared_meter_reports_per_invocation_deltas():
    provider = MeteredProvider(41, 7)
    provider.queue_response("First complete response")
    provider.queue_response("Second complete response")
    runtime = ModelRuntime(provider)
    meter = RuntimeUsage()
    first = await runtime.execute_turn(
        "backend_engineer", "First bounded turn", model_name="mock-model", usage_meter=meter
    )
    second = await runtime.execute_turn(
        "backend_engineer", "Second bounded turn", model_name="mock-model", usage_meter=meter
    )
    assert first.total_tokens == second.total_tokens == 48
    assert meter.total_tokens == 96 and meter.model_calls == 2


async def test_cancellation_during_provider_call_stops_invocation(qa_registry):
    entered, release, cancellation = asyncio.Event(), asyncio.Event(), asyncio.Event()
    provider = MockModelProvider()

    async def waiting_provider(request):
        entered.set()
        await release.wait()
        return LLMResponse(model="mock-model", text=independent_requirements().model_dump_json())

    provider.set_handler(waiting_provider)
    tool = ToolDefinition(name="syntra.read_file", description="Read sandbox evidence", parameters={"type": "object"})
    inv = qa_invocation()
    running = asyncio.create_task(
        SpecialistAgent(qa_registry, ModelRuntime(provider, qa_registry.skills)).execute(
            inv,
            tools=[tool],
            cancellation=cancellation,
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        cancellation.set()
        try:
            outcome = await asyncio.wait_for(asyncio.shield(running), timeout=0.5)
        except asyncio.CancelledError:
            return  # Propagated cancellation also prevents a success artifact.
        assert outcome.status == "CANCELLED"
        assert outcome.output is None
    finally:
        release.set()
        if not running.done():
            running.cancel()
        await asyncio.gather(running, return_exceptions=True)


async def test_malformed_final_json_is_failure_and_usage_survives():
    provider = MeteredProvider(50, 20)
    provider.queue_response('{"summary":"Incomplete requirements"}')
    meter = RuntimeUsage()
    # Advertise a tool so generation returns raw bytes to the runtime validator.
    with pytest.raises(ModelOutputValidationError):
        await ModelRuntime(provider).execute_turn(
            "product_manager",
            "Validate structured final output",
            model_name="mock-model",
            response_model=RequirementsAnalysis,
            usage_meter=meter,
            available_tools=[
                ToolDefinition(name="syntra.read_file", description="read", parameters={"type": "object"})
            ],
        )
    assert meter.total_tokens == 70


@pytest.mark.parametrize("maximum", [0, 1])
async def test_tool_call_limit_blocks_entire_oversized_batch_before_effects(maximum):
    provider = MockModelProvider()
    provider.queue_response(
        {"tool_calls": [{"id": str(i), "name": "syntra.read_file", "arguments": {}} for i in range(2)]}
    )
    effects = []

    class Gateway:
        async def execute_tool_call(self, request, uow=None):
            effects.append(request)
            return MCPInvocationResult(invocation_id=request.invocation_id, status="SUCCESS")

    with pytest.raises(ModelToolExecutionError):
        await ModelRuntime(provider, tool_gateway=Gateway()).execute_turn(
            "backend_engineer",
            "Read only within tool quota",
            model_name="mock-model",
            max_tool_calls=maximum,
            available_tools=[
                ToolDefinition(name="syntra.read_file", description="read", parameters={"type": "object"})
            ],
        )
    assert effects == []


class RecordingBridge:
    """Container boundary double: records effects, never runs host commands."""

    def __init__(self, root):
        self.sandbox = SimpleNamespace(
            config=ContainerConfig(),
            lease=SimpleNamespace(worktree_path=root),
        )
        self.files = {"src/quantity.py": "original source", "tests/test_quantity.py": "original test"}
        self.effects = []

    async def isolated_file_operation(self, operation, relative_path, content=""):
        path = posixpath.normpath(relative_path)
        self.effects.append((operation, path))
        if operation == "write":
            self.files[path] = content
            return "written"
        return self.files.get(path, "fixture evidence")

    async def execute_command(self, command, timeout_seconds=None):
        self.effects.append(("command", command))
        return ExecutionResult(exit_code=0, stdout="1 passed", stderr="", duration_ms=1, command=command)

    async def get_unified_diff(self):
        return "--- a/src/quantity.py\n+++ b/src/quantity.py\n@@ -1 +1 @@\n-old\n+fixed\n"


async def granted_gateway(
    uow_factory, scope, tmp_path, *, role=AgentRole.BACKEND_ENGINEER, guard=None, **grant_changes
):
    inv = qa_invocation(
        scope, role=role, approved_capabilities=["syntra.read_file", "syntra.write_file", "syntra.run_command"]
    )
    async with uow_factory() as uow:
        for tool in inv.approved_capabilities:
            attrs = {
                "org_id": scope.org,
                "agent_role": role.value,
                "tool_name_pattern": tool,
                "is_allowed": True,
            } | grant_changes
            uow.session.add(CapabilityGrantModel(**attrs))
        await uow.commit()

    async def active_guard():
        return None

    bridge = RecordingBridge(tmp_path)
    gateway, tools = build_sandbox_gateway(inv, bridge, uow_factory, guard or active_guard)
    return inv, bridge, gateway, tools


def tool_request(inv, **changes):
    values = {
        "org_id": inv.org_id,
        "mission_id": inv.mission_id,
        "task_id": inv.task_id,
        "caller_role": inv.role.value,
        "server_name": "syntra",
        "tool_name": "read_file",
        "arguments": {"relative_path": "src/quantity.py"},
    }
    return MCPInvocationRequest(**(values | changes))


async def test_authorized_gateway_reads_container_evidence(uow_factory, qa_scope, tmp_path):
    inv, bridge, gateway, tools = await granted_gateway(uow_factory, qa_scope, tmp_path)
    result = await gateway.execute_tool_call(tool_request(inv))
    assert result.status == "SUCCESS" and not result.is_error
    assert "original source" in result.output
    assert bridge.effects == [("read", "src/quantity.py")]
    assert {tool.name for tool in tools} == set(inv.approved_capabilities)


@pytest.mark.parametrize("field", ["org_id", "mission_id", "task_id", "caller_role", "server_name"])
async def test_bound_gateway_rejects_forged_identity_before_container_effects(
    uow_factory,
    qa_scope,
    tmp_path,
    field,
):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path)
    forged = {
        "org_id": qa_scope.other_org,
        "mission_id": qa_scope.other_mission,
        "task_id": uuid4(),
        "caller_role": AgentRole.DEVOPS_ENGINEER.value,
        "server_name": "untrusted",
    }
    result = await gateway.execute_tool_call(tool_request(inv, **{field: forged[field]}))
    assert result.status == "BLOCKED_BY_POLICY" and result.is_error
    assert bridge.effects == []


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "tests/../../outside.py"])
async def test_gateway_rejects_paths_outside_worktree(uow_factory, qa_scope, tmp_path, path):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path)
    result = await gateway.execute_tool_call(tool_request(inv, arguments={"relative_path": path}))
    assert result.status == "BLOCKED_BY_POLICY"
    assert bridge.effects == []


@pytest.mark.parametrize("grant", ["denied", "expired", "approval", "foreign_org"])
async def test_database_grant_is_authoritative_over_invocation_claims(uow_factory, qa_scope, tmp_path, grant):
    changes = {
        "denied": {"is_allowed": False},
        "expired": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
        "approval": {"requires_approval": True},
        "foreign_org": {"org_id": qa_scope.other_org},
    }[grant]
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path, **changes)
    result = await gateway.execute_tool_call(tool_request(inv))
    assert result.status == "BLOCKED_BY_POLICY"
    assert bridge.effects == []


@pytest.mark.parametrize("exhaustion", ["tokens", "cost"])
async def test_gateway_blocks_tools_when_authoritative_budget_is_exhausted(
    uow_factory,
    qa_scope,
    tmp_path,
    exhaustion,
):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path)
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        if exhaustion == "tokens":
            budget.consumed_tokens = budget.max_tokens
        else:
            budget.consumed_cost_usd = budget.max_cost_usd
        await uow.commit()
    result = await gateway.execute_tool_call(tool_request(inv))
    assert result.status == "BLOCKED_BY_POLICY"
    assert bridge.effects == []


async def test_revoked_lease_guard_prevents_container_effects(uow_factory, qa_scope, tmp_path):
    from syntra.scheduling.exceptions import StaleLeaseError

    async def revoked():
        raise StaleLeaseError("Lease was cancelled or superseded")

    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path, guard=revoked)
    with pytest.raises(StaleLeaseError):
        await gateway.execute_tool_call(tool_request(inv))
    assert bridge.effects == []


async def test_revoking_database_grant_blocks_next_call_on_existing_gateway(uow_factory, qa_scope, tmp_path):
    from sqlalchemy import select

    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path)
    assert (await gateway.execute_tool_call(tool_request(inv))).status == "SUCCESS"
    async with uow_factory() as uow:
        grants = (await uow.session.execute(select(CapabilityGrantModel))).scalars().all()
        for grant in grants:
            grant.is_allowed = False
        await uow.commit()
    result = await gateway.execute_tool_call(tool_request(inv))
    assert result.status == "BLOCKED_BY_POLICY"
    assert bridge.effects == [("read", "src/quantity.py")]


@pytest.mark.parametrize("path", ["src/quantity.py", "tests/../src/quantity.py"])
async def test_qa_write_policy_cannot_be_bypassed_by_path_normalization(uow_factory, qa_scope, tmp_path, path):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path, role=AgentRole.QA_ENGINEER)
    result = await gateway.execute_tool_call(
        tool_request(
            inv,
            tool_name="write_file",
            arguments={"relative_path": path, "content": "weakened validation"},
        )
    )
    assert result.is_error and result.status != "SUCCESS"
    assert bridge.files["src/quantity.py"] == "original source"


async def test_qa_may_write_independent_acceptance_tests(uow_factory, qa_scope, tmp_path):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path, role=AgentRole.QA_ENGINEER)
    result = await gateway.execute_tool_call(
        tool_request(
            inv,
            tool_name="write_file",
            arguments={"relative_path": "tests/test_zero.py", "content": "assert rejects(0)"},
        )
    )
    assert result.status == "SUCCESS"
    assert bridge.files["tests/test_zero.py"] == "assert rejects(0)"


async def test_reviewer_cannot_use_model_claimed_write_capability(uow_factory, qa_scope, tmp_path):
    inv, bridge, gateway, _ = await granted_gateway(uow_factory, qa_scope, tmp_path, role=AgentRole.CODE_REVIEWER)
    result = await gateway.execute_tool_call(
        tool_request(
            inv,
            tool_name="write_file",
            arguments={"relative_path": "src/quantity.py", "content": "modified"},
        )
    )
    assert result.status == "BLOCKED_BY_POLICY"
    assert bridge.effects == []


def engineering_spec():
    return EngineeringTaskSpecification(
        objective="Correct quantity validation with a regression test",
        acceptance_criteria=independent_requirements().acceptance_criteria,
        required_skills=["backend-api-development"],
        required_capabilities=["syntra.read_file"],
        verification_commands=["python -m pytest -q tests"],
    )


@pytest.mark.parametrize("restriction", ["foreign_org", "foreign_project", "planning_role", "no_lease_guard"])
async def test_engineering_worker_rejects_unauthorized_execution_before_provisioning(
    uow_factory,
    qa_scope,
    qa_registry,
    tmp_path,
    restriction,
):
    class NoProvisionProvider:
        created = 0

        async def create_sandbox(self, **kwargs):
            self.created += 1
            raise AssertionError("Unauthorized worker provisioned a sandbox")

    provider = NoProvisionProvider()
    worker = EngineeringSandboxWorker(
        tmp_path,
        provider=provider,
        registry=qa_registry,
        provider_model=MockModelProvider(),
        uow_factory=uow_factory,
        authorized_org_id=qa_scope.org,
        authorized_project_id=uuid4() if restriction == "foreign_project" else qa_scope.project,
    )
    dispatch = TaskDispatchPayload(
        task_id=qa_scope.task,
        mission_id=qa_scope.mission,
        org_id=qa_scope.other_org if restriction == "foreign_org" else qa_scope.org,
        attempt_number=1,
        assigned_role="product_manager" if restriction == "planning_role" else "backend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=30),
        specification=engineering_spec().model_dump_json(),
    )
    with pytest.raises((ValueError, CrossTenantAccessError)):
        await worker.execute_task(dispatch)
    assert provider.created == 0


@pytest.mark.parametrize("subdirectory", [".", "src", "tests", "docs"])
async def test_frontend_worker_cannot_target_syntra_or_its_subdirectories(
    uow_factory,
    qa_scope,
    qa_registry,
    subdirectory,
):
    class NoProvisionProvider:
        created = 0

        async def create_sandbox(self, **kwargs):
            self.created += 1
            raise AssertionError("Frontend target escaped the platform repository restriction")

    provider = NoProvisionProvider()
    platform_root = Path(__file__).resolve().parents[1]
    worker = EngineeringSandboxWorker(
        platform_root / subdirectory,
        provider=provider,
        registry=qa_registry,
        provider_model=MockModelProvider(),
        uow_factory=uow_factory,
        authorized_org_id=qa_scope.org,
        authorized_project_id=qa_scope.project,
    )
    spec = engineering_spec().model_copy(update={"required_skills": ["frontend-development"]})
    dispatch = TaskDispatchPayload(
        task_id=qa_scope.task,
        mission_id=qa_scope.mission,
        org_id=qa_scope.org,
        attempt_number=1,
        assigned_role="frontend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=30),
        specification=spec.model_dump_json(),
    )

    async def guard():
        return None

    with pytest.raises(ValueError):
        await worker.execute_task(dispatch, before_effect=guard)
    assert provider.created == 0


@pytest.fixture
async def qa_planner(uow_factory, qa_scope, qa_registry):
    async with uow_factory() as uow:
        for capability in get_agent_profile(AgentRole.PRODUCT_MANAGER).allowed_tool_capabilities:
            uow.session.add(
                CapabilityGrantModel(
                    org_id=qa_scope.org,
                    agent_role=AgentRole.PRODUCT_MANAGER.value,
                    tool_name_pattern=capability,
                    is_allowed=True,
                )
            )
        await uow.commit()
    provider = MockModelProvider()
    provider.queue_response(independent_requirements())
    service = EngineeringMissionService(
        uow_factory, qa_registry, ModelRuntime(provider, qa_registry.skills), ["pytest"]
    )
    state = {
        "org_id": str(qa_scope.org),
        "mission_id": str(qa_scope.mission),
        "mission_version": 1,
        "objective": "Reject zero quantities",
    }
    return SimpleNamespace(service=service, state=state, provider=provider)


async def test_successful_planning_replay_reuses_artifact_without_duplicate_model_spend(
    uow_factory,
    qa_scope,
    qa_planner,
):
    first = await qa_planner.service.node("requirements_analysis", qa_planner.state)
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        consumed = budget.consumed_tokens
        assert consumed > 0 and budget.reserved_tokens == 0
    second = await qa_planner.service.node("requirements_analysis", qa_planner.state)
    assert first["prd_artifact_id"] == second["prd_artifact_id"]
    assert len(qa_planner.provider.call_history) == 1
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        assert budget.consumed_tokens == consumed and budget.reserved_tokens == 0


@pytest.mark.parametrize("field", ["org_id", "mission_id", "invocation_id"])
async def test_planning_cache_revalidates_envelope_identity(uow_factory, qa_scope, qa_planner, field):
    from uuid import UUID

    first = await qa_planner.service.node("requirements_analysis", qa_planner.state)
    async with uow_factory() as uow:
        _, stored = await uow.artifacts.get_by_id(UUID(first["prd_artifact_id"]))
        envelope = RoleArtifact.model_validate_json(base64.b64decode(stored.storage_path[7:]))
        rewritten = envelope.model_copy(update={field: uuid4()}).model_dump_json().encode()
        stored.storage_path = "inline:" + base64.b64encode(rewritten).decode()
        stored.sha256_checksum = hashlib.sha256(rewritten).hexdigest()
        stored.size_bytes = len(rewritten)
        await uow.commit()
    with pytest.raises((ValueError, CrossTenantAccessError)):
        await qa_planner.service.node("requirements_analysis", qa_planner.state)


async def test_planning_replay_rejects_cache_after_authoritative_plan_revision(uow_factory, qa_scope, qa_planner):
    await qa_planner.service.node("requirements_analysis", qa_planner.state)
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        mission.active_plan_version = 2
        mission.state = MissionState.REPLANNING
        await uow.commit()
    with pytest.raises(ValueError):
        await qa_planner.service.node("requirements_analysis", qa_planner.state)


async def test_planning_cancellation_does_not_publish_successful_role_artifact(uow_factory, qa_scope, qa_registry):
    async with uow_factory() as uow:
        for capability in get_agent_profile(AgentRole.PRODUCT_MANAGER).allowed_tool_capabilities:
            uow.session.add(
                CapabilityGrantModel(
                    org_id=qa_scope.org,
                    agent_role=AgentRole.PRODUCT_MANAGER.value,
                    tool_name_pattern=capability,
                    is_allowed=True,
                )
            )
        await uow.commit()

    class CancellingProvider(MockModelProvider):
        async def generate_structured(self, request, response_model):
            async with uow_factory() as uow:
                mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
                mission.state = MissionState.CANCELLED
                await uow.commit()
            return await super().generate_structured(request, response_model)

    provider = CancellingProvider()
    provider.queue_response(independent_requirements())
    service = EngineeringMissionService(
        uow_factory, qa_registry, ModelRuntime(provider, qa_registry.skills), ["pytest"]
    )
    state = {
        "org_id": str(qa_scope.org),
        "mission_id": str(qa_scope.mission),
        "mission_version": 1,
        "objective": "Reject zero quantities",
    }
    try:
        await service.node("requirements_analysis", state)
    except (ValueError, asyncio.CancelledError):
        pass
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        assert mission.state == MissionState.CANCELLED
        artifacts, _, _ = await uow.artifacts.list_for_mission(qa_scope.mission, qa_scope.org)
        assert artifacts == [], "Cancelled planning must not publish consumable success artifacts"
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        assert budget.reserved_tokens == 0 and budget.reserved_cost_usd == 0


async def test_verification_does_not_trust_claimed_success_for_pending_task(uow_factory, qa_scope, qa_registry):
    claimed = TaskExecutionResult(
        task_id=qa_scope.task,
        attempt_number=1,
        worker_id="unowned-worker",
        fencing_token=1,
        status=AttemptState.SUCCEEDED,
        execution_evidence=[
            {"stage": "QA", "command": "python -m pytest -q", "exit_code": 0, "timed_out": False},
        ],
    )
    async with uow_factory() as uow:
        task = await uow.tasks.get_by_id(qa_scope.task)
        assert task.state == TaskState.PENDING
        await store_artifact(
            uow,
            org_id=qa_scope.org,
            mission_id=qa_scope.mission,
            task_id=qa_scope.task,
            title="Execution attempt claimed",
            type=ArtifactType.TEST_REPORT,
            content=claimed.model_dump_json(),
        )
        await uow.commit()
    service = EngineeringMissionService(uow_factory, qa_registry, ModelRuntime(MockModelProvider()), ["pytest"])
    result = await service.node(
        "independent_verification",
        {
            "org_id": str(qa_scope.org),
            "mission_id": str(qa_scope.mission),
            "mission_version": 1,
            "task_dag": [{"task_key": str(qa_scope.task)}],
        },
    )
    assert result["verification_passed"] is False, (
        "Unowned result artifact cannot replace authoritative task completion"
    )


@pytest.fixture
async def qa_dispatch(uow_factory, qa_scope):
    """An authentic scheduler reservation, attempt and unclaimed worker lease."""
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        mission.state = MissionState.RUNNING
        task = await uow.tasks.get_by_id(qa_scope.task)
        task.description = engineering_spec().model_dump_json()
        for capability in get_agent_profile(AgentRole.BACKEND_ENGINEER).allowed_tool_capabilities:
            uow.session.add(
                CapabilityGrantModel(
                    org_id=qa_scope.org,
                    agent_role=AgentRole.BACKEND_ENGINEER.value,
                    tool_name_pattern=capability,
                    is_allowed=True,
                )
            )
        await uow.commit()
    scheduler = TaskScheduler(uow_factory)
    dispatches = await scheduler.schedule_ready_tasks(qa_scope.mission, qa_scope.org)
    assert len(dispatches) == 1
    return scheduler, dispatches[0]


class RecordingDispatcher:
    """Redis transport double; authoritative task state stays in real repositories."""

    def __init__(self):
        self.acknowledged = []

    async def acknowledge_dispatch(self, message_id):
        self.acknowledged.append(message_id)


@pytest.mark.parametrize("timing", ["before_checkpoint", "after_checkpoint"])
async def test_database_cancellation_cannot_be_overwritten_by_delivery_approval(
    uow_factory,
    qa_scope,
    qa_registry,
    timing,
):
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    from syntra.orchestration.checkpointer import build_mission_thread_id
    from syntra.orchestration.engine import WorkflowOrchestrationEngine
    from syntra.orchestration.lifecycle_service import cancel_mission
    from syntra.orchestration.mission_graph import (
        awaiting_delivery_approval_node,
        cancelled_node,
        completed_node,
        route_from_delivery_approval,
    )
    from syntra.orchestration.state import MissionWorkflowState

    human = uuid4()
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        mission.state = MissionState.VERIFYING
        uow.session.add(
            UserModel(
                id=human,
                email=f"{human}@qa.invalid",
                full_name="Independent QA Approver",
                is_active=True,
                is_service_account=False,
            )
        )
        await uow.session.flush()
        uow.session.add(MembershipModel(org_id=qa_scope.org, user_id=human, role=MembershipRole.ADMIN))
        await uow.commit()
    runtime = ModelRuntime(MockModelProvider(), qa_registry.skills)
    service = EngineeringMissionService(uow_factory, qa_registry, runtime, ["pytest"])
    saver = MemorySaver()
    engine = WorkflowOrchestrationEngine(runtime, saver, qa_registry.skills, engineering_service=service)
    # Isolate the real delivery tail without simulating requirements or workers.
    graph = StateGraph(MissionWorkflowState)
    graph.add_node("delivery", awaiting_delivery_approval_node)
    graph.add_node("completed", completed_node)
    graph.add_node("cancelled", cancelled_node)
    graph.add_edge(START, "delivery")
    graph.add_conditional_edges(
        "delivery",
        route_from_delivery_approval,
        {
            "completed": "completed",
            "cancelled": "cancelled",
            "replanning": END,
            "failed": END,
        },
    )
    graph.add_edge("completed", END)
    graph.add_edge("cancelled", END)
    engine.mission_graph = graph.compile(checkpointer=saver)
    state = {
        "org_id": str(qa_scope.org),
        "mission_id": str(qa_scope.mission),
        "mission_version": 1,
        "domain_state": MissionState.VERIFYING.value,
        "verification_passed": True,
        "delivery_digest": hashlib.sha256(b"independently reviewed fixture patch").hexdigest(),
    }
    if timing == "before_checkpoint":
        async with uow_factory() as uow:
            await cancel_mission(qa_scope.mission, qa_scope.org, "Cancelled before delivery checkpoint", uow=uow)
    started = None
    try:
        async with uow_factory() as uow:
            started = await engine.mission_graph.ainvoke(
                state,
                config={
                    "configurable": {
                        "thread_id": build_mission_thread_id(qa_scope.mission),
                        "runtime": runtime,
                        "uow": uow,
                        "engineering_service": service,
                    }
                },
            )
    except (ValueError, DomainError):
        if timing == "after_checkpoint":
            raise
    except RuntimeError as exc:
        if timing == "after_checkpoint":
            raise
        assert isinstance(exc.__cause__, DomainError), "Unexpected failure before cancellation validation"
    if timing == "after_checkpoint":
        assert started and started.get("__interrupt__"), "Valid delivery must initially require approval"
        approval_payload = started["__interrupt__"][0].value
        assert approval_payload["action_type"] == "DELIVERY_APPROVAL"
        async with uow_factory() as uow:
            await cancel_mission(qa_scope.mission, qa_scope.org, "Cancelled while awaiting human delivery", uow=uow)
        try:
            async with uow_factory() as uow:
                await engine.resume_approval(
                    qa_scope.mission,
                    {
                        "decision": "APPROVED",
                        "org_id": str(qa_scope.org),
                        "user_id": str(human),
                        "action_digest": approval_payload["action_digest"],
                    },
                    uow=uow,
                )
        except (ValueError, DomainError):
            pass  # Refusing the stale approval is an acceptable terminal outcome.
        except RuntimeError as exc:
            assert isinstance(exc.__cause__, DomainError), "Unexpected failure instead of rejecting stale delivery"
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        assert mission.state == MissionState.CANCELLED, "Stale checkpoint resurrected a cancelled mission"
        if timing == "after_checkpoint":
            from uuid import UUID

            approval = await uow.approvals.get_by_id_for_org(UUID(approval_payload["approval_id"]), qa_scope.org)
            assert approval.decision != ApprovalDecision.CONSUMED, "Cancellation must invalidate delivery authority"


@pytest.mark.parametrize("forged_roles", [False, True], ids=["qa_dict_only", "forged_role_dicts"])
async def test_completed_task_with_fabricated_qa_dict_cannot_replace_reviewer_artifacts(
    uow_factory,
    qa_scope,
    qa_registry,
    qa_dispatch,
    forged_roles,
):
    scheduler, dispatch = qa_dispatch
    assert await scheduler.begin_dispatch(dispatch, "independent-qa-worker")
    evidence = [{"stage": "QA", "command": "python -m pytest -q", "exit_code": 0, "timed_out": False}]
    if forged_roles:
        evidence.extend(
            {
                "stage": "ROLE_RESULT",
                "role": role.value,
                "status": "SUCCEEDED",
                "invocation_id": str(uuid4()),
            }
            for role in (AgentRole.QA_ENGINEER, AgentRole.CODE_REVIEWER, AgentRole.SECURITY_REVIEWER)
        )
    claimed = TaskExecutionResult(
        task_id=dispatch.task_id,
        attempt_number=dispatch.attempt_number,
        worker_id="independent-qa-worker",
        fencing_token=dispatch.fencing_token,
        status=AttemptState.SUCCEEDED,
        unified_diff="--- a/quantity.py\n+++ b/quantity.py\n@@ -1 +1 @@\n-old\n+fixed\n",
        execution_evidence=evidence,
        produced_artifact_ids=[],
    )
    try:
        await scheduler.handle_task_completion(dispatch.mission_id, dispatch.org_id, claimed)
    except (ValueError, DomainError):
        async with uow_factory() as uow:
            assert (await uow.tasks.get_by_id(dispatch.task_id)).state != TaskState.COMPLETED
        return  # Rejecting fabricated evidence at submission also satisfies the boundary.
    service = EngineeringMissionService(uow_factory, qa_registry, ModelRuntime(MockModelProvider()), ["pytest"])
    try:
        result = await service.node(
            "independent_verification",
            {
                "org_id": str(qa_scope.org),
                "mission_id": str(qa_scope.mission),
                "mission_version": 1,
                "task_dag": [{"task_key": str(qa_scope.task)}],
            },
        )
    except (ValueError, DomainError):
        return
    assert result["verification_passed"] is False, (
        "Invented QA/role dictionaries are not independent reviewer artifacts"
    )


async def test_wrong_project_consumer_cannot_claim_authoritative_task(
    uow_factory,
    qa_scope,
    qa_registry,
    qa_dispatch,
    tmp_path,
):
    scheduler, dispatch = qa_dispatch

    class NoProvisionProvider:
        created = 0

        async def create_sandbox(self, **kwargs):
            self.created += 1
            raise AssertionError("Wrong-project consumer reached container provisioning")

    provider = NoProvisionProvider()
    adapter = EngineeringSandboxWorker(
        tmp_path,
        worker_id="wrong-project-worker",
        provider=provider,
        registry=qa_registry,
        provider_model=MockModelProvider(),
        uow_factory=uow_factory,
        authorized_org_id=qa_scope.org,
        authorized_project_id=uuid4(),
    )
    consumer = SandboxWorkerConsumer(scheduler, RecordingDispatcher(), adapter, adapter.worker_id)
    try:
        outcome = await consumer.process("qa-wrong-project", dispatch)
        assert outcome is False
    except (ValueError, DomainError):
        pass
    async with uow_factory() as uow:
        task = await uow.tasks.get_by_id(dispatch.task_id)
        attempt = await uow.tasks.get_latest_attempt(dispatch.task_id)
        lease = await uow.session.get(WorkerLeaseModel, dispatch.task_id)
        assert task.state == TaskState.ASSIGNED, "Unauthorized project consumer took task ownership"
        assert attempt.state == AttemptState.INITIALIZING
        assert lease.worker_id != adapter.worker_id
    assert provider.created == 0
    assert await scheduler.begin_dispatch(dispatch, "correct-project-worker"), (
        "Wrong-project delivery stranded valid work"
    )


@pytest.mark.parametrize("forged_roles", [False, True], ids=["qa_dict_only", "forged_role_dicts"])
async def test_service_revalidates_reviewer_artifacts_even_for_completed_database_task(
    uow_factory,
    qa_scope,
    qa_registry,
    qa_dispatch,
    forged_roles,
):
    _, dispatch = qa_dispatch
    evidence = [{"stage": "QA", "command": "python -m pytest -q", "exit_code": 0, "timed_out": False}]
    if forged_roles:
        evidence.extend(
            {
                "stage": "ROLE_RESULT",
                "role": role.value,
                "status": "SUCCEEDED",
                "invocation_id": str(uuid4()),
            }
            for role in (AgentRole.QA_ENGINEER, AgentRole.CODE_REVIEWER, AgentRole.SECURITY_REVIEWER)
        )
    claimed = TaskExecutionResult(
        task_id=dispatch.task_id,
        attempt_number=dispatch.attempt_number,
        worker_id="claimed-review-worker",
        fencing_token=dispatch.fencing_token,
        status=AttemptState.SUCCEEDED,
        unified_diff="--- a/quantity.py\n+++ b/quantity.py\n@@ -1 +1 @@\n-old\n+fixed\n",
        execution_evidence=evidence,
    )
    # Model a persisted record accepted before the submission gate was hardened.
    # Completion state alone must not turn fabricated review claims into evidence.
    async with uow_factory() as uow:
        task = await uow.tasks.get_by_id(dispatch.task_id)
        task.state = TaskState.COMPLETED
        attempt = await uow.tasks.get_latest_attempt(dispatch.task_id)
        attempt.state = AttemptState.SUCCEEDED
        attempt.exit_code = 0
        await store_artifact(
            uow,
            org_id=qa_scope.org,
            mission_id=qa_scope.mission,
            task_id=dispatch.task_id,
            title=f"Execution attempt {dispatch.attempt_number}",
            type=ArtifactType.TEST_REPORT,
            content=claimed.model_dump_json(),
        )
        await uow.commit()
    service = EngineeringMissionService(uow_factory, qa_registry, ModelRuntime(MockModelProvider()), ["pytest"])
    try:
        result = await service.node(
            "independent_verification",
            {
                "org_id": str(qa_scope.org),
                "mission_id": str(qa_scope.mission),
                "mission_version": 1,
                "task_dag": [{"task_key": str(qa_scope.task)}],
            },
        )
    except (ValueError, DomainError):
        return
    assert result["verification_passed"] is False, (
        "Completed task state cannot substitute for independent review artifacts"
    )


async def test_cancelled_worker_result_preserves_spend_and_releases_reservation(
    uow_factory,
    qa_scope,
    qa_dispatch,
):
    scheduler, dispatch = qa_dispatch
    spent_prompt, spent_completion, spent_cost = 73, 17, Decimal("0.0012")

    class CancelledResultAdapter:
        worker_id = "cancelled-result-worker"

        async def execute_task(self, payload, before_effect):
            await before_effect()
            async with uow_factory() as uow:
                mission = await uow.missions.get_by_id_for_org(payload.mission_id, payload.org_id)
                mission.state = MissionState.CANCELLED
                await uow.commit()
            return TaskExecutionResult(
                task_id=payload.task_id,
                attempt_number=payload.attempt_number,
                worker_id=self.worker_id,
                fencing_token=payload.fencing_token,
                status=AttemptState.FAILED,
                exit_code=1,
                error_message="Mission cancelled after measured model work",
                actual_prompt_tokens=spent_prompt,
                actual_completion_tokens=spent_completion,
                actual_cost_usd=spent_cost,
            )

    adapter = CancelledResultAdapter()
    consumer = SandboxWorkerConsumer(scheduler, RecordingDispatcher(), adapter, adapter.worker_id)
    assert await consumer.process("qa-cancelled-result", dispatch) is False
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        task = await uow.tasks.get_by_id(dispatch.task_id)
        mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
        assert budget.consumed_tokens == spent_prompt + spent_completion, "Cancelled result lost model usage"
        assert budget.consumed_cost_usd == spent_cost
        assert budget.reserved_tokens == 0 and budget.reserved_cost_usd == 0
        assert mission.state == MissionState.CANCELLED and task.state != TaskState.COMPLETED
    assert await consumer.process("qa-cancelled-result-redelivery", dispatch) is False
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        assert budget.consumed_tokens == spent_prompt + spent_completion
        assert budget.consumed_cost_usd == spent_cost, "Redelivered cancellation double-charged usage"


async def test_cancellation_mid_model_call_preserves_known_worker_usage_in_ledger(
    uow_factory,
    qa_scope,
    qa_registry,
    qa_dispatch,
    tmp_path,
):
    from sqlalchemy import select

    scheduler, dispatch = qa_dispatch
    waiting, parked = asyncio.Event(), asyncio.Event()
    prompt_tokens, completion_tokens = 73, 17

    class PausingProvider(MeteredProvider):
        async def generate_with_tools(self, request):
            if self.call_history:
                waiting.set()
                await parked.wait()
                raise AssertionError("Cancelled provider unexpectedly resumed generation")
            return await super().generate_with_tools(request)

    model_provider = PausingProvider(prompt_tokens, completion_tokens)
    model_provider.queue_response(
        {
            "tool_calls": [
                {
                    "id": "qa-read-before-cancel",
                    "name": "syntra.read_file",
                    "arguments": {"relative_path": "quantity.py"},
                }
            ]
        }
    )

    class VirtualSandbox:
        def __init__(self):
            self.config = ContainerConfig()
            self.lease = SandboxLease(task_id=dispatch.task_id, worktree_path=tmp_path)
            self.cleaned = False

        async def execute_command(self, command, timeout_seconds=None):
            return ExecutionResult(
                exit_code=0, stdout="quantity validation fixture", stderr="", duration_ms=1, command=command
            )

        async def get_unified_diff(self):
            return ""

        async def cleanup(self):
            self.cleaned = True

    sandbox = VirtualSandbox()

    class VirtualProvider:
        async def create_sandbox(self, **kwargs):
            return sandbox

    registry = AgentRegistry(qa_registry.skills, model_name="gemini-2.5-flash")
    adapter = EngineeringSandboxWorker(
        tmp_path,
        worker_id="cancelled-model-worker",
        provider=VirtualProvider(),
        registry=registry,
        provider_model=model_provider,
        uow_factory=uow_factory,
        authorized_org_id=qa_scope.org,
        authorized_project_id=qa_scope.project,
    )
    consumer = SandboxWorkerConsumer(
        scheduler, RecordingDispatcher(), adapter, adapter.worker_id, heartbeat_seconds=0.05
    )
    running = asyncio.create_task(consumer.process("qa-mid-model-cancellation", dispatch))
    try:
        await asyncio.wait_for(waiting.wait(), timeout=3)
        async with uow_factory() as uow:
            mission = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
            mission.state = MissionState.CANCELLED
            await uow.commit()
        assert await asyncio.wait_for(asyncio.shield(running), timeout=3) is False
    finally:
        if not running.done():
            running.cancel()
        await asyncio.gather(running, return_exceptions=True)
    known_cost = compute_token_cost("gemini-2.5-flash", prompt_tokens, completion_tokens).quantize(Decimal("0.000001"))
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        rows = (
            (
                await uow.session.execute(
                    select(UsageRecordModel).where(
                        UsageRecordModel.mission_id == qa_scope.mission,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert sandbox.cleaned, "Cancelling a provider call must still release the sandbox"
        assert budget.consumed_tokens >= prompt_tokens + completion_tokens, "Known pre-cancellation usage disappeared"
        assert budget.consumed_cost_usd >= known_cost
        assert budget.reserved_tokens == 0 and budget.reserved_cost_usd == 0
        assert sum(r.prompt_tokens + r.completion_tokens for r in rows) >= prompt_tokens + completion_tokens
        assert sum((r.cost_usd for r in rows), Decimal("0")) >= known_cost
        assert (await uow.tasks.get_by_id(dispatch.task_id)).state != TaskState.COMPLETED


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual_prompt_tokens", -1),
        ("actual_completion_tokens", -1),
        ("actual_cost_usd", Decimal("-0.000001")),
    ],
)
def test_audit_p1_worker_result_rejects_negative_usage(field, value):
    values = {
        "task_id": uuid4(), "attempt_number": 1, "worker_id": "independent-qa-worker",
        "fencing_token": 1, "status": AttemptState.FAILED,
        "actual_prompt_tokens": 0, "actual_completion_tokens": 0, "actual_cost_usd": Decimal("0"),
    }
    with pytest.raises(ValidationError) as failure:
        TaskExecutionResult(**(values | {field: value}))
    assert any(error["loc"] == (field,) for error in failure.value.errors())
