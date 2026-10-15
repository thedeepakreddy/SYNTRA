"""Comprehensive Test Suite for Phase 7: LangGraph Workflow Orchestration.

Verifies the 20 required scenarios:
1. Mission graph compilation
2. Task graph compilation
3. Valid mission transitions
4. Invalid mission transitions
5. Approval interrupt
6. Approval rejection
7. Authorized resume
8. Unauthorized resume
9. Expired approval
10. Modified action digest
11. Duplicate resume request (replay defense)
12. Workflow cancellation
13. Failure transition
14. Replanning transition
15. Checkpoint restoration
16. Process restart recovery
17. Outbox reconciliation
18. Replay without duplicate side effects
19. Budget enforcement
20. Existing service integration
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from syntra.domain.entities import (
    ApprovalDecision,
    MissionState,
)
from syntra.domain.exceptions import (
    ApprovalExpiredError,
    ApprovalReplayError,
    DigestMismatchError,
    InvalidStateTransitionError,
    UnauthorizedApprovalError,
)
from syntra.domain.state_machines import transition_mission_state
from syntra.llm.exceptions import ModelBudgetExceededError
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.runtime import ModelRuntime
from syntra.orchestration import (
    WorkflowOrchestrationEngine,
    build_mission_graph,
    build_mission_thread_id,
    build_task_graph,
    compile_mission_graph,
    compile_task_graph,
)
from syntra.orchestration.approval_interceptor import (
    _IN_MEMORY_APPROVALS,
    execute_approval_checkpoint,
    generate_deterministic_approval_id,
)
from syntra.orchestration.checkpointer import CheckpointerFactory
from syntra.orchestration.lifecycle_service import pause_mission
from syntra.persistence.models import BudgetModel
from syntra.persistence.unit_of_work import UnitOfWork
from syntra.storage.database import DatabaseManager

# ==============================================================================
# 1. Mission Graph Compilation
# ==============================================================================


def test_01_mission_graph_compilation():
    """Verify that the uncompiled builder and compiled Mission graph build cleanly."""
    builder = build_mission_graph()
    assert builder is not None

    compiled = compile_mission_graph()
    assert compiled is not None

    # Verify all 13 core nodes + 4 alternate nodes are present
    expected_nodes = {
        "intake",
        "requirements_analysis",
        "architecture_planning",
        "task_plan_generation",
        "plan_validation",
        "awaiting_approval",
        "ready",
        "task_scheduling",
        "execution_coordination",
        "integration",
        "independent_verification",
        "awaiting_delivery_approval",
        "completed",
        "paused",
        "replanning",
        "failed",
        "cancelled",
    }
    assert expected_nodes.issubset(set(compiled.nodes.keys()))


# ==============================================================================
# 2. Task Graph Compilation
# ==============================================================================


def test_02_task_graph_compilation():
    """Verify that the uncompiled builder and compiled Task execution graph build cleanly."""
    builder = build_task_graph()
    assert builder is not None

    compiled = compile_task_graph()
    assert compiled is not None

    expected_stages = {
        "prepare_context",
        "resolve_skills",
        "prepare_capabilities",
        "execute_agent",
        "collect_artifacts",
        "request_review",
        "await_verification",
        "resolve_outcome",
    }
    assert expected_stages.issubset(set(compiled.nodes.keys()))


# ==============================================================================
# 3. Valid Mission Transitions
# ==============================================================================


def test_03_valid_mission_transitions():
    """Verify standard legal progression across all domain lifecycle states."""
    s = MissionState.DRAFT
    s = transition_mission_state(s, MissionState.PLANNING)
    assert s == MissionState.PLANNING

    s = transition_mission_state(s, MissionState.AWAITING_APPROVAL)
    assert s == MissionState.AWAITING_APPROVAL

    s = transition_mission_state(s, MissionState.READY, decision_context=ApprovalDecision.APPROVED)
    assert s == MissionState.READY

    s = transition_mission_state(s, MissionState.RUNNING)
    assert s == MissionState.RUNNING

    s = transition_mission_state(s, MissionState.VERIFYING)
    assert s == MissionState.VERIFYING

    s = transition_mission_state(s, MissionState.AWAITING_DELIVERY_APPROVAL)
    assert s == MissionState.AWAITING_DELIVERY_APPROVAL

    s = transition_mission_state(s, MissionState.COMPLETED, decision_context=ApprovalDecision.APPROVED)
    assert s == MissionState.COMPLETED


# ==============================================================================
# 4. Invalid Mission Transitions
# ==============================================================================


def test_04_invalid_mission_transitions():
    """Verify illegal transitions are strictly rejected by domain state machine."""
    # Cannot jump DRAFT directly to COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        transition_mission_state(MissionState.DRAFT, MissionState.COMPLETED)

    # Cannot transition AWAITING_APPROVAL to READY without APPROVED decision
    with pytest.raises(InvalidStateTransitionError):
        transition_mission_state(MissionState.AWAITING_APPROVAL, MissionState.READY, decision_context=None)

    # Terminal COMPLETED cannot transition back to RUNNING
    with pytest.raises(InvalidStateTransitionError):
        transition_mission_state(MissionState.COMPLETED, MissionState.RUNNING)


# ==============================================================================
# 5. Approval Interrupt
# ==============================================================================


@pytest.mark.asyncio
async def test_05_approval_interrupt():
    """Verify Mission graph pauses execution at AWAITING_APPROVAL with interrupt payload."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(
        mission_id=m_id,
        org_id=org_id,
        objective="Build authenticated user service",
    )

    # Must contain interrupt signal and have halted
    assert "__interrupt__" in result
    interrupts = result["__interrupt__"]
    assert len(interrupts) > 0
    payload = interrupts[0].value
    assert payload["action_type"] == "TASK_PLAN_APPROVAL"
    assert "action_digest" in payload
    assert payload["mission_id"] == str(m_id)

    # Check graph state snapshot
    state_snap = await engine.get_mission_state(m_id)
    assert state_snap["values"]["domain_state"] == "AWAITING_APPROVAL"
    assert state_snap["values"]["current_phase"] == "AWAITING_APPROVAL"


# ==============================================================================
# 6. Approval Rejection
# ==============================================================================


@pytest.mark.asyncio
async def test_06_approval_rejection():
    """Verify rejecting human plan approval transitions workflow into REPLANNING."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Build service")
    interrupt_payload = result["__interrupt__"][0].value

    # Resume with rejection decision
    resume_payload = {
        "approval_id": interrupt_payload["approval_id"],
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "REJECTED",
        "feedback": "Add database migration task first",
        "action_digest": interrupt_payload["action_digest"],
    }

    resumed_result = await engine.resume_approval(m_id, resume_payload)
    # Rejection routes through replanning -> task_plan_generation -> plan_validation -> awaiting_approval (2nd interrupt)
    assert resumed_result["replan_count"] == 1
    assert resumed_result["domain_state"] in {"REPLANNING", "AWAITING_APPROVAL"}


# ==============================================================================
# 7. Authorized Resume
# ==============================================================================


@pytest.mark.asyncio
async def test_07_authorized_resume():
    """Verify that valid approval decision with correct HMAC digest advances workflow."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Build service")
    interrupt_payload = result["__interrupt__"][0].value

    # Approve plan
    resume_payload = {
        "approval_id": interrupt_payload["approval_id"],
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "APPROVED",
        "action_digest": interrupt_payload["action_digest"],
    }

    resumed = await engine.resume_approval(m_id, resume_payload)
    # Execution advances past READY -> TASK_SCHEDULING -> EXECUTION_COORDINATION -> INTEGRATION -> INDEPENDENT_VERIFICATION -> AWAITING_DELIVERY_APPROVAL (2nd interrupt)
    assert resumed["current_phase"] in {
        "READY",
        "TASK_SCHEDULING",
        "EXECUTION_COORDINATION",
        "INTEGRATION",
        "INDEPENDENT_VERIFICATION",
        "AWAITING_DELIVERY_APPROVAL",
    }


# ==============================================================================
# 8. Unauthorized Resume
# ==============================================================================


@pytest.mark.asyncio
async def test_08_unauthorized_resume():
    """Verify resume without user_id or cross-tenant org_id is rejected."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Build service")
    interrupt_payload = result["__interrupt__"][0].value

    # Missing user_id
    with pytest.raises(UnauthorizedApprovalError, match="Missing authorized approver"):
        await engine.resume_approval(
            m_id,
            {"approval_id": interrupt_payload["approval_id"], "decision": "APPROVED"},
        )

    # Cross-tenant org_id (separate mission thread)
    m2_id = uuid4()
    result2 = await engine.start_mission(mission_id=m2_id, org_id=org_id, objective="Build service 2")
    interrupt_payload2 = result2["__interrupt__"][0].value
    with pytest.raises(UnauthorizedApprovalError, match="Cross-tenant"):
        await engine.resume_approval(
            m2_id,
            {
                "approval_id": interrupt_payload2["approval_id"],
                "org_id": str(uuid4()),  # foreign org
                "user_id": str(uuid4()),
                "decision": "APPROVED",
                "action_digest": interrupt_payload2["action_digest"],
            },
        )


# ==============================================================================
# 9. Expired Approval
# ==============================================================================


@pytest.mark.asyncio
async def test_09_expired_approval():
    """Verify expired approval request raises ApprovalExpiredError upon resume."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    # 1. Start mission to reach human approval interrupt checkpoint
    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Build service with expiration check")
    assert "__interrupt__" in result
    interrupt_payload = result["__interrupt__"][0].value
    approval_id = UUID(interrupt_payload["approval_id"])

    # 2. Fast-forward approval expiration to the past
    _IN_MEMORY_APPROVALS[approval_id]["expires_at"] = datetime.now(UTC) - timedelta(seconds=10)

    # 3. Attempt to resume workflow using the real public resume_approval API
    resume_payload = {
        "approval_id": str(approval_id),
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "APPROVED",
        "action_digest": interrupt_payload["action_digest"],
    }

    # 4. Assert that the actual ApprovalExpiredError exception is raised
    with pytest.raises(ApprovalExpiredError, match="has expired"):
        await engine.resume_approval(m_id, resume_payload)

    # 5. Verify the mission does not advance (remains at AWAITING_APPROVAL)
    snap = await engine.get_mission_state(m_id)
    assert snap["values"]["domain_state"] == "AWAITING_APPROVAL"
    assert snap["values"]["current_phase"] == "AWAITING_APPROVAL"

    # 7. Verify an otherwise valid, non-expired approval can resume through the same execution path
    m2_id = uuid4()
    res2 = await engine.start_mission(
        mission_id=m2_id, org_id=org_id, objective="Build service with unexpired approval"
    )
    p2 = res2["__interrupt__"][0].value
    resumed_result = await engine.resume_approval(
        m2_id,
        {
            "approval_id": p2["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": p2["action_digest"],
        },
    )
    assert resumed_result["current_phase"] in {
        "READY",
        "TASK_SCHEDULING",
        "EXECUTION_COORDINATION",
        "INTEGRATION",
        "INDEPENDENT_VERIFICATION",
        "AWAITING_DELIVERY_APPROVAL",
    }


# ==============================================================================
# 10. Modified Action Digest
# ==============================================================================


@pytest.mark.asyncio
async def test_10_modified_action_digest():
    """Verify tampered action digest raises DigestMismatchError."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Build service")
    interrupt_payload = result["__interrupt__"][0].value

    tampered_payload = {
        "approval_id": interrupt_payload["approval_id"],
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "APPROVED",
        "action_digest": "tampered_digest_value_1234567890abcdef",
    }

    with pytest.raises(DigestMismatchError, match="Action digest mismatch"):
        await engine.resume_approval(m_id, tampered_payload)


# ==============================================================================
# 11. Duplicate Resume Request (Replay Defense)
# ==============================================================================


@pytest.mark.asyncio
async def test_11_duplicate_resume_request():
    """Verify replay protection blocks reusing an already consumed approval."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    m_id = uuid4()
    org_id = uuid4()
    proj_id = uuid4()
    user_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        # Create test org, project, and mission
        await uow.organizations.create(org_id=org_id, name="Test Org", slug=f"org-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="Test Proj", slug=f"proj-{proj_id}")
        mission = await uow.missions.create(
            mission_id=m_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Replay",
        )
        mission.state = MissionState.PLANNING
        await uow.commit()

        engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
        result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Replay", uow=uow)
        interrupt_payload = result["__interrupt__"][0].value

        resume_payload = {
            "approval_id": interrupt_payload["approval_id"],
            "org_id": str(org_id),
            "user_id": str(user_id),
            "decision": "APPROVED",
            "action_digest": interrupt_payload["action_digest"],
        }

        # First consumption: SUCCESS
        await engine.resume_approval(m_id, resume_payload, uow=uow)

        # Check DB record is now CONSUMED
        approval_rec = await uow.approvals.get_by_id_for_org(UUID(interrupt_payload["approval_id"]), org_id)
        assert approval_rec.decision == ApprovalDecision.CONSUMED

        # Second attempt to consume same approval: REPLAY BLOCKED
        with pytest.raises(ApprovalReplayError, match="already been consumed"):
            await uow.approvals.verify_and_consume_for_execution(
                approval_id=UUID(interrupt_payload["approval_id"]),
                org_id=org_id,
                mission_id=m_id,
                action_type="TASK_PLAN_APPROVAL",
                provided_digest=interrupt_payload["action_digest"],
                secret_key="syntra-default-approval-hmac-secret-change-in-prod",
                current_mission_version=1,
            )


# ==============================================================================
# 12. Workflow Cancellation
# ==============================================================================


@pytest.mark.asyncio
async def test_12_workflow_cancellation():
    """Verify cancelling mission halts graph and marks state CANCELLED."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Test Cancel")
    assert "__interrupt__" in result

    cancel_res = await engine.cancel_mission(mission_id=m_id, org_id=org_id, reason="Operator abort")
    assert cancel_res["status"] == "CANCELLED"


# ==============================================================================
# 13. Failure Transition
# ==============================================================================


@pytest.mark.asyncio
async def test_13_failure_transition():
    """Verify unrecoverable generation failure transitions state to FAILED."""
    mock_provider = MockModelProvider()
    # Queue invalid non-JSON to force parsing failure
    mock_provider.queue_response("Invalid non-json output that fails Pydantic validation")

    runtime = ModelRuntime(provider=mock_provider)
    engine = WorkflowOrchestrationEngine(runtime=runtime, checkpointer=MemorySaver())

    m_id = uuid4()
    org_id = uuid4()

    result = await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Test Failure")
    assert result["current_phase"] == "FAILED"
    assert result["domain_state"] == "FAILED"
    assert "error_message" in result


# ==============================================================================
# 14. Replanning Transition
# ==============================================================================


@pytest.mark.asyncio
async def test_14_replanning_transition():
    """Verify cyclic replanning loop increments replan_count, tests boundaries, and trips circuit breaker."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    m_id = uuid4()
    org_id = uuid4()
    proj_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        await uow.organizations.create(org_id=org_id, name="Replan Org", slug=f"replan-org-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="Replan Proj", slug=f"replan-proj-{proj_id}")
        await uow.missions.create(mission_id=m_id, org_id=org_id, project_id=proj_id, objective="Replan Mission")
        await uow.commit()

        engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())

        # Max limit set to 2 allowed replanning iterations
        # Boundary 0: Initial start
        result = await engine.start_mission(
            mission_id=m_id,
            org_id=org_id,
            objective="Test Replanning Circuit Breaker",
            max_replan_limit=2,
            uow=uow,
        )
        assert "__interrupt__" in result
        p1 = result["__interrupt__"][0].value

        # Boundary 1: Below limit (replan_count 1 <= max_replan_limit 2)
        r1 = await engine.resume_approval(
            m_id,
            {
                "approval_id": p1["approval_id"],
                "org_id": str(org_id),
                "user_id": str(uuid4()),
                "decision": "REJECTED",
                "action_digest": p1["action_digest"],
            },
            uow=uow,
        )
        assert r1["replan_count"] == 1
        assert r1["current_phase"] == "AWAITING_APPROVAL"
        assert "__interrupt__" in r1
        p2 = r1["__interrupt__"][0].value

        # Boundary 2: At limit (replan_count 2 == max_replan_limit 2)
        r2 = await engine.resume_approval(
            m_id,
            {
                "approval_id": p2["approval_id"],
                "org_id": str(org_id),
                "user_id": str(uuid4()),
                "decision": "REJECTED",
                "action_digest": p2["action_digest"],
            },
            uow=uow,
        )
        assert r2["replan_count"] == 2
        assert r2["current_phase"] == "AWAITING_APPROVAL"
        assert "__interrupt__" in r2
        p3 = r2["__interrupt__"][0].value

        # Boundary 3: Above limit (replan_count 3 > max_replan_limit 2) -> Circuit Breaker trips!
        r3 = await engine.resume_approval(
            m_id,
            {
                "approval_id": p3["approval_id"],
                "org_id": str(org_id),
                "user_id": str(uuid4()),
                "decision": "REJECTED",
                "action_digest": p3["action_digest"],
            },
            uow=uow,
        )
        assert r3["replan_count"] == 3
        assert r3["current_phase"] == "FAILED"
        assert r3["domain_state"] == "FAILED"
        assert "exceeded maximum replan limit" in r3["error_message"]
        assert len(r3["running_task_ids"]) == 0

        # Verify domain aggregate in DB is also FAILED
        mission_db = await uow.missions.get_by_id_for_org(m_id, org_id)
        assert mission_db.state == MissionState.FAILED

        # Verify failure reason is recorded in mission's outbox event history
        events = await uow.outbox.get_pending_events(limit=20)
        failed_events = [
            e for e in events if e.event_type == "MISSION_FAILED" and e.payload.get("mission_id") == str(m_id)
        ]
        assert len(failed_events) >= 1
        assert "exceeded maximum replan limit" in failed_events[0].payload["reason"]

        # Verify repeated resume requests cannot restart the failed mission
        r4 = await engine.resume_approval(
            m_id,
            {
                "approval_id": str(uuid4()),
                "org_id": str(org_id),
                "user_id": str(uuid4()),
                "decision": "APPROVED",
                "action_digest": "dummy",
            },
            uow=uow,
        )
        assert r4["current_phase"] == "FAILED"
        assert r4["domain_state"] == "FAILED"


# ==============================================================================
# 15. Checkpoint Restoration
# ==============================================================================


@pytest.mark.asyncio
async def test_15_checkpoint_restoration():
    """Verify saving and restoring state from LangGraph checkpointer."""
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)
    m_id = uuid4()
    org_id = uuid4()

    await engine.start_mission(mission_id=m_id, org_id=org_id, objective="Checkpoint Test")

    thread_id = build_mission_thread_id(m_id)
    tuple_state = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
    assert tuple_state is not None
    assert tuple_state.checkpoint["channel_values"]["domain_state"] == "AWAITING_APPROVAL"


# ==============================================================================
# 16. Process Restart Recovery
# ==============================================================================


@pytest.mark.asyncio
async def test_16_process_restart_recovery():
    """Verify that a brand new engine instance resumes seamlessly from a saved checkpoint."""
    shared_checkpointer = MemorySaver()

    # Process 1: Starts mission and reaches human interrupt
    engine_process_1 = WorkflowOrchestrationEngine(checkpointer=shared_checkpointer)
    m_id = uuid4()
    org_id = uuid4()

    res1 = await engine_process_1.start_mission(mission_id=m_id, org_id=org_id, objective="Crash Recovery")
    digest = res1["__interrupt__"][0].value["action_digest"]
    approval_id = res1["__interrupt__"][0].value["approval_id"]

    # Process 1 exits / crashes. Process 2 boots up with the same checkpointer:
    engine_process_2 = WorkflowOrchestrationEngine(checkpointer=shared_checkpointer)

    # Process 2 inspects current state
    snap = await engine_process_2.get_mission_state(m_id)
    assert snap["values"]["domain_state"] == "AWAITING_APPROVAL"

    # Process 2 resumes execution from interrupt
    res2 = await engine_process_2.resume_approval(
        m_id,
        {
            "approval_id": approval_id,
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": digest,
        },
    )

    # Verified: Process 2 completed execution without re-running intake
    assert "intake" in res2["executed_nodes"]
    assert res2["executed_nodes"].count("intake") == 1


# ==============================================================================
# 17. Outbox Reconciliation
# ==============================================================================


@pytest.mark.asyncio
async def test_17_outbox_reconciliation():
    """Verify lifecycle events are recorded in the transactional outbox."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    m_id = uuid4()
    org_id = uuid4()
    proj_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        await uow.organizations.create(org_id=org_id, name="Outbox Org", slug=f"outbox-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="Outbox Proj", slug=f"proj-{proj_id}")
        mission = await uow.missions.create(
            mission_id=m_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Outbox",
        )
        mission.state = MissionState.RUNNING
        await uow.commit()

        # Pause mission
        await pause_mission(mission_id=m_id, org_id=org_id, reason="Budget audit", uow=uow)

        # Inspect outbox
        events = await uow.outbox.get_pending_events(limit=5)
        paused_events = [
            e for e in events if e.event_type == "MISSION_PAUSED" and e.payload.get("aggregate_id") == str(m_id)
        ]
        assert len(paused_events) >= 1


# ==============================================================================
# 18. Replay Without Duplicate Side Effects
# ==============================================================================


def test_18_replay_without_duplicate_side_effects():
    """Verify deterministic approval ID computation prevents duplicate approval records."""
    m_id = uuid4()
    a1 = generate_deterministic_approval_id(m_id, "TASK_PLAN_APPROVAL", 1)
    a2 = generate_deterministic_approval_id(m_id, "TASK_PLAN_APPROVAL", 1)
    assert a1 == a2, "Approval ID must be completely deterministic for identical version"

    a_v2 = generate_deterministic_approval_id(m_id, "TASK_PLAN_APPROVAL", 2)
    assert a1 != a_v2, "New mission version must produce a distinct approval ID"


# ==============================================================================
# 19. Budget Enforcement
# ==============================================================================


@pytest.mark.asyncio
async def test_19_budget_enforcement():
    """Verify budget limits halt execution turns in ModelRuntime."""
    m_id = uuid4()
    mock_provider = MockModelProvider()
    mock_provider.queue_response("Simple test response")

    runtime = ModelRuntime(provider=mock_provider)

    class MockBudgetRepo:
        def __init__(self):
            self.model = BudgetModel(mission_id=m_id, max_tokens=50, max_cost_usd=Decimal("0.50"))
            self.model.consumed_tokens = 50
            self.model.consumed_cost_usd = Decimal("0.0")

        async def get_for_mission(self, mission_id):
            return self.model

    class MockUOW:
        def __init__(self):
            self.budgets = MockBudgetRepo()

    with pytest.raises(ModelBudgetExceededError, match="Token budget exceeded"):
        await runtime.execute_turn(
            agent_role="backend_engineer",
            user_prompt="Run turn exceeding budget",
            mission_id=m_id,
            uow=MockUOW(),  # type: ignore[arg-type]
        )


# ==============================================================================
# 20. Existing Service Integration
# ==============================================================================


@pytest.mark.asyncio
async def test_20_existing_service_integration():
    """Verify Task execution graph executes all 8 stages with ModelRuntime and SkillRegistry."""
    engine = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
    t_id = uuid4()
    m_id = uuid4()
    org_id = uuid4()

    result = await engine.execute_task(
        task_id=t_id,
        mission_id=m_id,
        org_id=org_id,
        agent_role="backend_engineer",
        objective="Implement database model",
        task_specification="Author SQLAlchemy models for user entity",
        requested_skills=[],
        is_test_adapter=True,
    )

    assert result["current_stage"] == "RESOLVE_OUTCOME"
    assert result["task_state"] == "COMPLETED"
    assert result["unified_diff"] is not None
    assert result["review_verdict"] == "APPROVED"
    assert result["verification_outcome"] == "SUCCESS"
    assert len(result["produced_artifact_ids"]) >= 1


# ==============================================================================
# 21. Approval Replay Protection Across Process Restarts
# ==============================================================================


@pytest.mark.asyncio
async def test_21_approval_replay_protection_cross_process():
    """Verify approval replay protection remains effective across process restarts via DB authority."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    m_id = uuid4()
    org_id = uuid4()
    proj_id = uuid4()
    user_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        await uow.organizations.create(org_id=org_id, name="CrossProc Org", slug=f"cporg-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="CrossProc Proj", slug=f"cpproj-{proj_id}")
        mission = await uow.missions.create(
            mission_id=m_id, org_id=org_id, project_id=proj_id, objective="Replay Cross"
        )
        mission.state = MissionState.PLANNING
        await uow.commit()

        # Process 1 creates approval and consumes it
        engine1 = WorkflowOrchestrationEngine(checkpointer=MemorySaver())
        res1 = await engine1.start_mission(mission_id=m_id, org_id=org_id, objective="Replay Cross", uow=uow)
        p = res1["__interrupt__"][0].value
        approval_id = UUID(p["approval_id"])

        await engine1.resume_approval(
            m_id,
            {
                "approval_id": str(approval_id),
                "org_id": str(org_id),
                "user_id": str(user_id),
                "decision": "APPROVED",
                "action_digest": p["action_digest"],
            },
            uow=uow,
        )

        # Verify DB record is CONSUMED
        db_approval = await uow.approvals.get_by_id_for_org(approval_id, org_id)
        assert db_approval.decision == ApprovalDecision.CONSUMED

        # Simulate process exit: In-memory cache is completely discarded!
        _IN_MEMORY_APPROVALS.clear()

        # 1. Direct checkpoint replay attempt in a new process context raises ApprovalReplayError from DB
        with pytest.raises(ApprovalReplayError, match="already been consumed"):
            await execute_approval_checkpoint(
                state={"mission_id": str(m_id), "org_id": str(org_id), "mission_version": 1},
                action_type="TASK_PLAN_APPROVAL",
                target_resource=f"mission:{m_id}",
                prompt_message="Review plan",
                uow=uow,
            )

        # 2. Direct CAS verify_and_consume attempt in a new worker also raises ApprovalReplayError from DB
        with pytest.raises(ApprovalReplayError, match="already been consumed"):
            await uow.approvals.verify_and_consume_for_execution(
                approval_id=approval_id,
                org_id=org_id,
                mission_id=m_id,
                action_type="TASK_PLAN_APPROVAL",
                provided_digest=p["action_digest"],
                secret_key="syntra-default-approval-hmac-secret-change-in-prod",
                current_mission_version=1,
            )


# ==============================================================================
# 22. Checkpointer Refuses Silent In-Memory Downgrade
# ==============================================================================


@pytest.mark.asyncio
async def test_22_checkpointer_no_silent_downgrade():
    """Verify CheckpointerFactory refuses silent downgrade to in-memory checkpointer in production."""
    # Production PostgreSQL connection failure must raise ConnectionError when allow_fallback is False
    with pytest.raises(ConnectionError, match="Refusing to silently downgrade"):
        await CheckpointerFactory.create_checkpointer(
            conn_string="postgresql://non-existent-cluster:5432/syntra",
            force_memory=False,
            allow_fallback=False,
        )

    # When fallback is explicitly allowed, logs warning and returns MemorySaver
    saver, is_pg = await CheckpointerFactory.create_checkpointer(
        conn_string="postgresql://non-existent-cluster:5432/syntra",
        force_memory=False,
        allow_fallback=True,
    )
    assert is_pg is False
    assert isinstance(saver, MemorySaver)
