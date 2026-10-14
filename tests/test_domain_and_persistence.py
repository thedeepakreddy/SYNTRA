"""Test-First specification for Phase 2: PostgreSQL and Domain Foundation.

Covers 10 mandatory test scenarios:
1. Invalid mission transitions
2. Cross-tenant data access
3. Cyclic task graphs
4. Concurrent mission updates (optimistic locking)
5. Duplicate idempotency keys
6. Transaction rollback
7. Outbox consistency
8. Budget constraints
9. Cross-mission task references
10. Artifact ownership consistency
"""

import uuid
from decimal import Decimal

import pytest

from syntra.domain.dag_validator import validate_task_dag
from syntra.domain.entities import (
    ApprovalDecision,
    ArtifactType,
    MissionState,
)
from syntra.domain.exceptions import (
    ArtifactOwnershipError,
    BudgetExceededError,
    CrossMissionDependencyError,
    CrossTenantAccessError,
    CyclicDependencyError,
    DuplicateIdempotencyKeyError,
    InvalidStateTransitionError,
    OptimisticLockError,
)
from syntra.domain.state_machines import (
    transition_mission_state,
)
from syntra.persistence.repositories import (
    MissionRepository,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager


@pytest.fixture
async def test_db():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    yield db
    await db.close()


@pytest.fixture
async def uow(test_db):
    session_factory = test_db.get_session_factory()
    return SqlAlchemyUnitOfWork(session_factory)


# ==============================================================================
# 1. Invalid Mission Transitions
# ==============================================================================
def test_invalid_mission_transitions():
    """Verify mission state machine rejects illegal jumps and requires authorization context."""
    # Cannot jump from DRAFT directly to COMPLETED or RUNNING
    with pytest.raises(InvalidStateTransitionError):
        transition_mission_state(current_state=MissionState.DRAFT, target_state=MissionState.COMPLETED)

    with pytest.raises(InvalidStateTransitionError):
        transition_mission_state(current_state=MissionState.DRAFT, target_state=MissionState.RUNNING)

    # Valid transition to PLANNING
    s1 = transition_mission_state(current_state=MissionState.DRAFT, target_state=MissionState.PLANNING)
    assert s1 == MissionState.PLANNING

    # Transitioning to AWAITING_APPROVAL
    s2 = transition_mission_state(current_state=s1, target_state=MissionState.AWAITING_APPROVAL)
    assert s2 == MissionState.AWAITING_APPROVAL

    # Transitioning from AWAITING_APPROVAL to READY requires valid approval decision
    with pytest.raises(InvalidStateTransitionError, match="requires APPROVED decision"):
        transition_mission_state(
            current_state=s2,
            target_state=MissionState.READY,
            decision_context=ApprovalDecision.REJECTED,
        )

    s3 = transition_mission_state(
        current_state=s2,
        target_state=MissionState.READY,
        decision_context=ApprovalDecision.APPROVED,
    )
    assert s3 == MissionState.READY


# ==============================================================================
# 2. Cross-Tenant Data Access
# ==============================================================================
@pytest.mark.asyncio
async def test_cross_tenant_data_access(uow):
    """Verify tenant isolation prevents accessing or modifying entities of another organization."""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    async with uow:
        org_repo = uow.organizations
        await org_repo.create(org_id=org1_id, name="Acme Corp", slug="acme")
        await org_repo.create(org_id=org2_id, name="Beta Inc", slug="beta")

        mission_repo = uow.missions
        await mission_repo.create(
            mission_id=mission_id,
            org_id=org1_id,
            project_id=uuid.uuid4(),
            objective="Private Acme Mission",
        )
        await uow.commit()

    # Attempt to retrieve Org1's mission using Org2 context
    async with uow:
        mission_repo = uow.missions
        with pytest.raises(CrossTenantAccessError):
            await mission_repo.get_by_id_for_org(mission_id=mission_id, org_id=org2_id)


# ==============================================================================
# 3. Cyclic Task Graphs
# ==============================================================================
def test_cyclic_task_graphs():
    """Verify task DAG validator detects and rejects circular dependencies and self dependencies."""
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    t3 = uuid.uuid4()

    # Cycle: T1 -> T2 -> T3 -> T1
    tasks = [
        {"id": t1, "mission_id": uuid.uuid4(), "identifier": "T1"},
        {"id": t2, "mission_id": uuid.uuid4(), "identifier": "T2"},
        {"id": t3, "mission_id": uuid.uuid4(), "identifier": "T3"},
    ]
    # Set all mission_ids to same
    m_id = uuid.uuid4()
    for t in tasks:
        t["mission_id"] = m_id

    dependencies = [
        {"task_id": t2, "depends_on_task_id": t1},
        {"task_id": t3, "depends_on_task_id": t2},
        {"task_id": t1, "depends_on_task_id": t3},
    ]

    with pytest.raises(CyclicDependencyError):
        validate_task_dag(tasks=tasks, dependencies=dependencies)

    # Self dependency: T1 -> T1
    self_deps = [{"task_id": t1, "depends_on_task_id": t1}]
    with pytest.raises(CyclicDependencyError, match="Self-dependency"):
        validate_task_dag(tasks=tasks, dependencies=self_deps)


# ==============================================================================
# 4. Concurrent Mission Updates (Optimistic Concurrency)
# ==============================================================================
@pytest.mark.asyncio
async def test_concurrent_mission_updates(test_db):
    """Verify optimistic locking detects version collision on concurrent mutations."""
    org_id = uuid.uuid4()
    mission_id = uuid.uuid4()
    factory = test_db.get_session_factory()

    # Seed
    async with factory() as session:
        uow1 = SqlAlchemyUnitOfWork(factory, session=session)
        await uow1.organizations.create(org_id=org_id, name="Test Org", slug="test-org")
        await uow1.missions.create(
            mission_id=mission_id,
            org_id=org_id,
            project_id=uuid.uuid4(),
            objective="Initial Mission",
        )
        await session.commit()

    # Client A and Client B read version 1
    async with factory() as session_a, factory() as session_b:
        repo_a = MissionRepository(session_a)
        repo_b = MissionRepository(session_b)

        m_a = await repo_a.get_by_id_for_org(mission_id=mission_id, org_id=org_id)
        m_b = await repo_b.get_by_id_for_org(mission_id=mission_id, org_id=org_id)
        assert m_a.version == 1
        assert m_b.version == 1

        # Client A updates version 1 -> 2 and commits
        await repo_a.update_objective(
            mission_id=mission_id, org_id=org_id, expected_version=1, new_objective="Updated by A"
        )
        await session_a.commit()

        # Client B attempts to update assuming version 1 -> should raise OptimisticLockError
        with pytest.raises(OptimisticLockError):
            await repo_b.update_objective(
                mission_id=mission_id, org_id=org_id, expected_version=1, new_objective="Updated by B"
            )


# ==============================================================================
# 5. Duplicate Idempotency Keys
# ==============================================================================
@pytest.mark.asyncio
async def test_duplicate_idempotency_keys(uow):
    """Verify idempotency registry prevents duplicate execution and rejects mismatched payloads."""
    key = "cmd-deploy-12345"
    org_id = uuid.uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_id, name="Idem Org", slug="idem-org")
        idem_repo = uow.idempotency
        # First execution saves response
        await idem_repo.record(
            key=key,
            org_id=org_id,
            response_code=200,
            response_body={"status": "success", "deployment_id": "dep-1"},
            payload_hash="sha256-hash-abc",
        )
        await uow.commit()

    async with uow:
        idem_repo = uow.idempotency
        existing = await idem_repo.get(key=key, org_id=org_id)
        assert existing is not None
        assert existing.response_code == 200
        assert existing.response_body["deployment_id"] == "dep-1"

        # Duplicate recording with DIFFERENT payload hash raises error
        with pytest.raises(DuplicateIdempotencyKeyError):
            await idem_repo.record(
                key=key,
                org_id=org_id,
                response_code=200,
                response_body={"status": "conflict"},
                payload_hash="sha256-hash-DIFFERENT",
            )


# ==============================================================================
# 6. Transaction Rollback
# ==============================================================================
@pytest.mark.asyncio
async def test_transaction_rollback(uow):
    """Verify that any exception within Unit of Work rolls back all database modifications."""
    org_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    try:
        async with uow:
            await uow.organizations.create(org_id=org_id, name="Rollback Org", slug="rb-org")
            await uow.missions.create(
                mission_id=mission_id,
                org_id=org_id,
                project_id=uuid.uuid4(),
                objective="Should be rolled back",
            )
            # Simulate unexpected failure before commit
            raise RuntimeError("Database connection interrupted during work")
    except RuntimeError:
        pass

    # Verify neither org nor mission exists
    async with uow:
        found_org = await uow.organizations.get_by_id(org_id=org_id)
        assert found_org is None


# ==============================================================================
# 7. Outbox Consistency
# ==============================================================================
@pytest.mark.asyncio
async def test_outbox_consistency(uow):
    """Verify that domain operations atomically record outbox events in the same transaction."""
    org_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_id, name="Outbox Org", slug="outbox-org")
        await uow.missions.create(
            mission_id=mission_id,
            org_id=org_id,
            project_id=uuid.uuid4(),
            objective="Outbox Mission",
        )
        uow.publish_event(
            event_type="mission.created",
            payload={"mission_id": str(mission_id), "org_id": str(org_id)},
        )
        await uow.commit()

    # Verify outbox has pending event
    async with uow:
        pending_events = await uow.outbox.get_pending_events(limit=10)
        assert len(pending_events) == 1
        assert pending_events[0].event_type == "mission.created"
        assert pending_events[0].status == "PENDING"
        assert pending_events[0].payload["mission_id"] == str(mission_id)


# ==============================================================================
# 8. Budget Constraints
# ==============================================================================
@pytest.mark.asyncio
async def test_budget_constraints(uow):
    """Verify budget enforces maximum token reservations and cost boundaries."""
    org_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_id, name="Budget Org", slug="budget-org")
        await uow.budgets.create(
            org_id=org_id,
            mission_id=mission_id,
            max_tokens=10000,
            max_cost_usd=Decimal("10.00"),
        )
        await uow.commit()

    async with uow:
        budget_repo = uow.budgets
        # Reserve within limit
        await budget_repo.reserve(mission_id=mission_id, tokens=5000)
        await uow.commit()

    async with uow:
        budget_repo = uow.budgets
        # Reserve exceeding limit (5000 + 6000 > 10000)
        with pytest.raises(BudgetExceededError):
            await budget_repo.reserve(mission_id=mission_id, tokens=6000)


# ==============================================================================
# 9. Cross-Mission Task References
# ==============================================================================
def test_cross_mission_task_references():
    """Verify task DAG validator rejects dependencies across different missions."""
    m1 = uuid.uuid4()
    m2 = uuid.uuid4()
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()

    tasks = [
        {"id": t1, "mission_id": m1, "identifier": "T1"},
        {"id": t2, "mission_id": m2, "identifier": "T2"},
    ]
    dependencies = [
        {"task_id": t1, "depends_on_task_id": t2},
    ]

    with pytest.raises(CrossMissionDependencyError):
        validate_task_dag(tasks=tasks, dependencies=dependencies)


# ==============================================================================
# 10. Artifact Ownership Consistency
# ==============================================================================
@pytest.mark.asyncio
async def test_artifact_ownership_consistency(uow):
    """Verify artifacts must belong to the same mission that owns the referenced task."""
    org_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()
    plan1_id = uuid.uuid4()
    t1_id = uuid.uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_id, name="Artifact Org", slug="art-org")
        await uow.missions.create(mission_id=m1_id, org_id=org_id, project_id=uuid.uuid4(), objective="Mission 1")
        await uow.missions.create(mission_id=m2_id, org_id=org_id, project_id=uuid.uuid4(), objective="Mission 2")

        # Create task under Mission 1
        await uow.tasks.create_plan(plan_id=plan1_id, mission_id=m1_id, version=1)
        await uow.tasks.create_task(
            task_id=t1_id,
            task_plan_id=plan1_id,
            mission_id=m1_id,
            org_id=org_id,
            identifier="TASK-1",
            title="Task in M1",
            description="desc",
            assigned_role="backend_engineer",
        )
        await uow.commit()

    async with uow:
        art_repo = uow.artifacts
        # Attempt to create artifact for Task 1 (Mission 1) under Mission 2 -> Must fail
        with pytest.raises(ArtifactOwnershipError):
            await art_repo.create(
                mission_id=m2_id,
                task_id=t1_id,
                type=ArtifactType.UNIFIED_DIFF,
                title="Patch",
            )
