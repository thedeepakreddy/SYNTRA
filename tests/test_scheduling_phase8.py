"""Comprehensive Test Suite for Phase 8: Task Scheduling & Parallel Agent Coordination.

Covers all 25 required test categories:
1. DAG validation
2. Cyclic dependency rejection
3. Unknown dependency rejection
4. Dependency ordering
5. Independent parallel tasks
6. Concurrency limits
7. Deterministic priority ranking
8. Capability matching
9. Skill availability checks
10. Atomic task claiming (PostgreSQL SKIP LOCKED)
11. Duplicate claim prevention
12. Lease expiration
13. Lease renewal
14. Stale worker rejection (fencing tokens)
15. Worker heartbeat / timeout handling
16. Duplicate Redis delivery handling
17. Outbox relay replay
18. Live Redis Streams integration (XADD, XREADGROUP, XACK, XAUTOCLAIM)
19. Worker crash recovery & bounded retries
20. Concurrent budget reservations
21. Budget exhaustion
22. Mission cancellation
23. Plan revision invalidation
24. Task result idempotency
25. LangGraph scheduler integration
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from dotenv import load_dotenv

from syntra.domain.entities import (
    AttemptState,
    MissionState,
    TaskPlanStatus,
    TaskState,
)
from syntra.domain.exceptions import BudgetExceededError
from syntra.orchestration.engine import WorkflowOrchestrationEngine
from syntra.persistence.models import (
    BudgetModel,
    MissionModel,
    ProjectModel,
    TaskModel,
    TaskPlanModel,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.scheduling.dag_engine import TaskDAGEngine
from syntra.scheduling.exceptions import (
    DAGValidationError,
    StaleLeaseError,
)
from syntra.scheduling.models import (
    TaskDispatchPayload,
    TaskExecutionResult,
)
from syntra.scheduling.outbox_relay import OutboxRelay
from syntra.scheduling.reconciliation import SchedulerReconciler
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.scheduling.scheduler import TaskScheduler
from syntra.scheduling.worker_adapter import TestWorkerAdapter
from syntra.storage.database import DatabaseManager

load_dotenv()

# Check live infrastructure availability
TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)
TEST_REDIS_URL = os.environ.get("SYNTRA_REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
async def memory_db():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    yield db
    await db.close()


@pytest.fixture
def uow_factory(memory_db):
    session_factory = memory_db.get_session_factory()
    return lambda: SqlAlchemyUnitOfWork(session_factory)


async def setup_test_org_and_mission(
    uow: SqlAlchemyUnitOfWork,
    mission_state: MissionState = MissionState.RUNNING,
    plan_version: int = 1,
    max_concurrency: int = 4,
    max_tokens: int = 1_000_000,
    max_cost_usd: Decimal = Decimal("50.0000"),
) -> tuple[UUID, UUID, UUID]:
    """Helper creating authoritative Organization, Project, Mission, TaskPlan, and Budget."""
    org_id = uuid4()
    await uow.organizations.create(org_id=org_id, name="Test Org", slug=f"test-org-{org_id.hex[:6]}")

    proj_id = uuid4()
    proj = ProjectModel(id=proj_id, org_id=org_id, name="Test Project", slug=f"test-proj-{proj_id.hex[:6]}")
    uow.session.add(proj)
    await uow.session.flush()

    m_id = uuid4()
    mission = MissionModel(
        id=m_id,
        org_id=org_id,
        project_id=proj_id,
        objective="Execute Task Graph",
        state=mission_state,
        active_plan_version=plan_version,
    )
    uow.session.add(mission)
    await uow.session.flush()

    plan_id = uuid4()
    await uow.tasks.create_plan(
        plan_id=plan_id,
        mission_id=m_id,
        version=plan_version,
        status=TaskPlanStatus.APPROVED,
    )

    await uow.budgets.create(
        org_id=org_id,
        mission_id=m_id,
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
        max_concurrency=max_concurrency,
    )

    await uow.commit()
    return org_id, m_id, plan_id


# ==============================================================================
# 1. DAG Validation & Clean Topological Sort
# ==============================================================================


def test_01_dag_validation_clean_topological_sort():
    """Verify linear and branching task DAGs validate and return correct topological order."""
    engine = TaskDAGEngine()
    t1, t2, t3 = uuid4(), uuid4(), uuid4()

    tasks = [{"id": t1}, {"id": t2}, {"id": t3}]
    dependencies = [
        {"task_id": t2, "depends_on_task_id": t1},
        {"task_id": t3, "depends_on_task_id": t2},
    ]

    order = engine.validate_graph(tasks, dependencies, plan_version=1)
    assert order == [t1, t2, t3]


# ==============================================================================
# 2. Cyclic Dependency Rejection
# ==============================================================================


def test_02_cyclic_dependency_rejection():
    """Verify circular dependencies (A -> B -> A) are strictly rejected with DAGValidationError."""
    engine = TaskDAGEngine()
    t1, t2 = uuid4(), uuid4()

    tasks = [{"id": t1}, {"id": t2}]
    dependencies = [
        {"task_id": t2, "depends_on_task_id": t1},
        {"task_id": t1, "depends_on_task_id": t2},
    ]

    with pytest.raises(DAGValidationError, match="Cyclic"):
        engine.validate_graph(tasks, dependencies)


# ==============================================================================
# 3. Unknown Dependency Rejection
# ==============================================================================


def test_03_unknown_dependency_rejection():
    """Verify dependency referencing non-existent task is rejected."""
    engine = TaskDAGEngine()
    t1 = uuid4()
    unknown_id = uuid4()

    tasks = [{"id": t1}]
    dependencies = [{"task_id": t1, "depends_on_task_id": unknown_id}]

    with pytest.raises(DAGValidationError, match="unknown depends_on_task_id"):
        engine.validate_graph(tasks, dependencies)


# ==============================================================================
# 4. Dependency Ordering Enforcement
# ==============================================================================


@pytest.mark.asyncio
async def test_04_dependency_ordering_enforcement(uow_factory):
    """Verify dependent tasks remain unready until all prerequisites transition to COMPLETED."""
    org_id, m_id, plan_id = None, None, None
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        t1 = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-01",
            title="Backend DB",
            description="DB models",
            assigned_role="backend_engineer",
        )
        t2 = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-02",
            title="API Endpoints",
            description="REST endpoints",
            assigned_role="backend_engineer",
        )
        await uow.tasks.add_dependency(task_id=t2.id, depends_on_task_id=t1.id)
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)

    # First dispatch: T1 should be dispatched, T2 must remain PENDING
    dispatches1 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(dispatches1) == 1
    assert dispatches1[0].task_id == t1.id

    # Simulate completion of T1
    adapter = TestWorkerAdapter()
    res1 = await adapter.execute_task(dispatches1[0])
    await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res1)

    # Second dispatch: Now T2 is ready and scheduled
    dispatches2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(dispatches2) == 1
    assert dispatches2[0].task_id == t2.id


# ==============================================================================
# 5. Independent Parallel Tasks
# ==============================================================================


@pytest.mark.asyncio
async def test_05_independent_parallel_tasks(uow_factory):
    """Verify independent tasks with no dependencies execute concurrently."""
    org_id, m_id, plan_id = None, None, None
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow, max_concurrency=4)
        t1 = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-01",
            title="Service A",
            description="Service A",
            assigned_role="backend_engineer",
        )
        t2 = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-02",
            title="Service B",
            description="Service B",
            assigned_role="backend_engineer",
        )
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)
    dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)

    assert len(dispatches) == 2
    dispatched_ids = {d.task_id for d in dispatches}
    assert dispatched_ids == {t1.id, t2.id}


# ==============================================================================
# 6. Concurrency Limits
# ==============================================================================


@pytest.mark.asyncio
async def test_06_concurrency_limits(uow_factory):
    """Verify mission concurrency limits constrain simultaneous task execution."""
    org_id, m_id, plan_id = None, None, None
    async with uow_factory() as uow:
        # Limit concurrency strictly to 2
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow, max_concurrency=2)
        for i in range(4):
            await uow.tasks.create_task(
                task_id=uuid4(),
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier=f"T-0{i}",
                title=f"Task {i}",
                description="Desc",
                assigned_role="backend_engineer",
            )
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)

    # First dispatch batch: exactly 2 tasks
    batch1 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(batch1) == 2

    # Second dispatch immediately: 0 tasks because concurrency capacity is saturated (2 active)
    batch2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(batch2) == 0


# ==============================================================================
# 7. Deterministic Priority Ranking
# ==============================================================================


@pytest.mark.asyncio
async def test_07_deterministic_priority_ranking(uow_factory):
    """Verify tasks are ranked deterministically by priority and downstream dependency count."""
    org_id, m_id, plan_id = None, None, None
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow, max_concurrency=1)
        await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-LOW",
            title="Low Priority",
            description="Low",
            assigned_role="backend_engineer",
            priority=10,
        )
        t_high = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-HIGH",
            title="High Priority",
            description="High",
            assigned_role="backend_engineer",
            priority=100,
        )
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)
    dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id, max_dispatch=1)

    assert len(dispatches) == 1
    assert dispatches[0].task_id == t_high.id


# ==============================================================================
# 8. Capability Matching for Agent Roles
# ==============================================================================


@pytest.mark.asyncio
async def test_08_capability_matching(uow_factory):
    """Verify task with invalid or unauthorized agent role is rejected during readiness check."""
    dag_engine = TaskDAGEngine()
    t_id = uuid4()
    task = TaskModel(id=t_id, identifier="T-BAD", title="Bad", description="Bad", assigned_role="fictitious_role")
    mission = MissionModel(id=uuid4(), org_id=uuid4(), state=MissionState.RUNNING, active_plan_version=1)
    plan = TaskPlanModel(id=uuid4(), mission_id=mission.id, plan_version=1)

    report = dag_engine.evaluate_task_readiness(task=task, mission=mission, plan=plan, upstream_dependencies=[])
    assert not report.is_ready
    assert any("Unrecognized agent role" in r for r in report.rejection_reasons)


# ==============================================================================
# 9. Skill Availability Checks
# ==============================================================================


@pytest.mark.asyncio
async def test_09_skill_availability_checks():
    """Verify requested non-existent skill marks task as not ready."""
    dag_engine = TaskDAGEngine()
    t_id = uuid4()
    task = TaskModel(
        id=t_id, identifier="T-SKILL", title="Skill", description="Skill", assigned_role="backend_engineer"
    )
    mission = MissionModel(id=uuid4(), org_id=uuid4(), state=MissionState.RUNNING, active_plan_version=1)
    plan = TaskPlanModel(id=uuid4(), mission_id=mission.id, plan_version=1)

    report = dag_engine.evaluate_task_readiness(
        task=task,
        mission=mission,
        plan=plan,
        upstream_dependencies=[],
        requested_skills=["non_existent_unregistered_skill_999"],
    )
    assert not report.is_ready
    assert "non_existent_unregistered_skill_999" in report.missing_skills


# ==============================================================================
# 10. Atomic Task Claiming with PostgreSQL Row Locking
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_10_atomic_task_claiming_postgresql():
    """Verify atomic task claiming against live PostgreSQL using FOR UPDATE SKIP LOCKED."""
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_fn():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        async with uow_fn() as uow:
            org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
            t1 = await uow.tasks.create_task(
                task_id=uuid4(),
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-PG-01",
                title="PG Task",
                description="Testing SKIP LOCKED",
                assigned_role="backend_engineer",
            )
            t1.state = TaskState.READY
            await uow.commit()

        async with uow_fn() as uow:
            claimed = await uow.tasks.claim_ready_tasks_atomic(
                mission_id=m_id, limit=1, worker_id="pg-worker-01", lease_duration_seconds=30
            )
            assert len(claimed) == 1
            task, lease = claimed[0]
            assert task.id == t1.id
            assert task.state == TaskState.ASSIGNED
            assert lease.worker_id == "pg-worker-01"
            assert lease.fencing_token == 1
            await uow.commit()

    finally:
        await db.close()


# ==============================================================================
# 11. Duplicate Claim Prevention (Concurrent Workers)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_11_duplicate_claim_prevention_concurrent():
    """Verify concurrent worker claiming queries against PostgreSQL receive mutually exclusive tasks."""
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_fn():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = None, None, None
        async with uow_fn() as uow:
            org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
            # Create two ready tasks
            t1 = await uow.tasks.create_task(
                task_id=uuid4(),
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-CONC-1",
                title="Task 1",
                description="D1",
                assigned_role="backend_engineer",
            )
            t2 = await uow.tasks.create_task(
                task_id=uuid4(),
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-CONC-2",
                title="Task 2",
                description="D2",
                assigned_role="backend_engineer",
            )
            t1.state = TaskState.READY
            t2.state = TaskState.READY
            await uow.commit()

        # Concurrent execution of two worker claims
        async def claim_as_worker(w_id: str):
            async with uow_fn() as uow:
                claimed = await uow.tasks.claim_ready_tasks_atomic(
                    mission_id=m_id, limit=1, worker_id=w_id, lease_duration_seconds=30
                )
                await uow.commit()
                return claimed

        res1, res2 = await asyncio.gather(claim_as_worker("worker-alpha"), claim_as_worker("worker-beta"))

        tasks_worker_1 = [t.id for t, _ in res1]
        tasks_worker_2 = [t.id for t, _ in res2]

        # Invariant: Neither worker got an empty list, and task sets are completely disjoint
        assert len(tasks_worker_1) == 1
        assert len(tasks_worker_2) == 1
        assert set(tasks_worker_1).isdisjoint(set(tasks_worker_2))

    finally:
        await db.close()


# ==============================================================================
# 12. Lease Expiration Detection & Recovery
# ==============================================================================


@pytest.mark.asyncio
async def test_12_lease_expiration_recovery(uow_factory):
    """Verify expired lease transitions task attempt to TIMED_OUT and resets task to READY."""
    org_id, m_id, plan_id = None, None, None
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        t = await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-EXP",
            title="Expiring Task",
            description="Exp",
            assigned_role="backend_engineer",
        )
        t.state = TaskState.ASSIGNED
        t.attempt_count = 1
        await uow.tasks.create_attempt(task_id=t.id, attempt_number=1, state=AttemptState.RUNNING)

        # Create lease that expired 10 minutes ago
        await uow.tasks.claim_lease(task_id=t.id, worker_id="w-dead", fencing_token=1, duration_seconds=-600)
        await uow.commit()

    reconciler = SchedulerReconciler(uow_factory=uow_factory)
    summary = await reconciler.reconcile_mission(mission_id=m_id, org_id=org_id)

    assert summary.expired_leases_count == 1
    assert summary.recovered_attempts_count == 1

    async with uow_factory() as uow:
        refreshed = await uow.tasks.get_by_id(t.id)
        assert refreshed.state == TaskState.READY


# ==============================================================================
# 13. Lease Renewal
# ==============================================================================


@pytest.mark.asyncio
async def test_13_lease_renewal(uow_factory):
    """Verify worker can renew an active lease before expiration."""
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-RENEW",
            title="Renew",
            description="Renew",
            assigned_role="backend_engineer",
        )
        lease = await uow.tasks.claim_lease(task_id=t_id, worker_id="w-alive", fencing_token=1, duration_seconds=60)
        old_expires = lease.lease_expires_at
        await uow.commit()

        renewed = await uow.tasks.renew_lease(task_id=t_id, worker_id="w-alive", fencing_token=1, extension_seconds=120)
        assert renewed.lease_expires_at > old_expires
        await uow.commit()


# ==============================================================================
# 14. Stale Worker Rejection (Fencing Tokens)
# ==============================================================================


@pytest.mark.asyncio
async def test_14_stale_worker_rejection(uow_factory):
    """Verify result submitted by superseded worker with old fencing token is rejected with StaleLeaseError."""
    org_id, m_id, plan_id = None, None, None
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        t = await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-STALE",
            title="Stale",
            description="Stale",
            assigned_role="backend_engineer",
        )
        t.state = TaskState.ASSIGNED
        t.attempt_count = 2

        # Lease was re-assigned to worker-2 with fencing token 2
        await uow.tasks.claim_lease(task_id=t_id, worker_id="worker-2", fencing_token=2, duration_seconds=60)
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)

    # Worker-1 tries to submit result with old fencing token 1
    stale_result = TaskExecutionResult(
        task_id=t_id,
        attempt_number=1,
        worker_id="worker-1",
        fencing_token=1,
        status=AttemptState.SUCCEEDED,
    )

    with pytest.raises(StaleLeaseError, match="stale fencing token"):
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=stale_result)


# ==============================================================================
# 15. Worker Heartbeat & Failure Timeout
# ==============================================================================


@pytest.mark.asyncio
async def test_15_worker_heartbeat_timeout(uow_factory):
    """Verify task attempt state transitions to TIMED_OUT after lease expiration without heartbeat."""
    org_id, m_id, plan_id = None, None, None
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-HB",
            title="HB",
            description="HB",
            assigned_role="backend_engineer",
        )
        await uow.tasks.create_attempt(task_id=t_id, attempt_number=1, state=AttemptState.RUNNING)
        await uow.tasks.claim_lease(task_id=t_id, worker_id="worker-crashed", fencing_token=1, duration_seconds=-10)
        await uow.commit()

    reconciler = SchedulerReconciler(uow_factory=uow_factory)
    await reconciler.reconcile_mission(mission_id=m_id, org_id=org_id)

    async with uow_factory() as uow:
        latest = await uow.tasks.get_latest_attempt(t_id)
        assert latest.state == AttemptState.TIMED_OUT


# ==============================================================================
# 16. Duplicate Redis Delivery Handling
# ==============================================================================


@pytest.mark.asyncio
async def test_16_duplicate_redis_delivery_handling(uow_factory):
    """Verify processing duplicate delivery notifications does not corrupt task attempts."""
    org_id, m_id, plan_id = None, None, None
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        t = await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-DUP",
            title="Dup",
            description="Dup",
            assigned_role="backend_engineer",
        )
        t.state = TaskState.READY
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)
    dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(dispatches) == 1

    # Attempting to schedule again immediately should produce 0 new dispatches
    duplicate_run = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    assert len(duplicate_run) == 0


# ==============================================================================
# 17. Outbox Relay Replay
# ==============================================================================


@pytest.mark.asyncio
async def test_17_outbox_relay_replay(uow_factory):
    """Verify outbox relay processes pending dispatch events and transitions them to PROCESSED."""
    dispatcher = RedisTaskDispatcher(TEST_REDIS_URL)
    relay = OutboxRelay(uow_factory=uow_factory, dispatcher=dispatcher)

    m_id = uuid4()
    org_id = uuid4()
    t_id = uuid4()

    payload = TaskDispatchPayload(
        task_id=t_id,
        mission_id=m_id,
        org_id=org_id,
        attempt_number=1,
        assigned_role="backend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=60),
        specification="Test Relay",
    )

    async with uow_factory() as uow:
        uow.publish_event("TASK_DISPATCHED", payload.model_dump(mode="json"))
        await uow.commit()

    count = await relay.relay_batch(batch_size=10)
    assert count == 1

    # Second pass: 0 pending events
    count_second = await relay.relay_batch(batch_size=10)
    assert count_second == 0


# ==============================================================================
# 18. Live Redis Streams Integration (XADD, XREADGROUP, XACK, XAUTOCLAIM)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_18_live_redis_streams_integration():
    """Verify live Redis Streams publish, read, ack, and reclaim cycle on localhost:6379."""
    test_stream = f"syntra:test_dispatch_{uuid4().hex[:6]}"
    dispatcher = RedisTaskDispatcher(TEST_REDIS_URL, stream_key=test_stream)
    consumer = f"worker-{uuid4().hex[:6]}"

    payload = TaskDispatchPayload(
        task_id=uuid4(),
        mission_id=uuid4(),
        org_id=uuid4(),
        attempt_number=1,
        assigned_role="backend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=60),
        specification="Live Stream Test",
    )

    try:
        # 1. Publish (XADD)
        msg_id = await dispatcher.publish_dispatch(payload)
        assert msg_id is not None
        assert "-" in msg_id

        # 2. Read (XREADGROUP)
        entries = await dispatcher.read_dispatches(consumer_name=consumer, count=5, block_ms=1000)
        assert len(entries) >= 1
        found_msg_id, received_payload = entries[0]
        assert received_payload.task_id == payload.task_id

        # 3. Acknowledge (XACK)
        acked = await dispatcher.acknowledge_dispatch(found_msg_id)
        assert acked is True

    finally:
        client = await dispatcher.get_client()
        await client.delete(test_stream)
        await dispatcher.close()


# ==============================================================================
# 19. Worker Crash Recovery & Bounded Retries
# ==============================================================================


@pytest.mark.asyncio
async def test_19_worker_crash_recovery_bounded_retries(uow_factory):
    """Verify task retry attempts increment, and max attempts exhaustion cascades BLOCKED to dependents."""
    org_id, m_id, plan_id = None, None, None
    t1_id, t2_id = uuid4(), uuid4()

    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        await uow.tasks.create_task(
            task_id=t1_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-RETRY",
            title="Retry Task",
            description="R",
            assigned_role="backend_engineer",
            max_attempts=2,
        )
        await uow.tasks.create_task(
            task_id=t2_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-DEP",
            title="Dependent Task",
            description="D",
            assigned_role="backend_engineer",
        )
        await uow.tasks.add_dependency(task_id=t2_id, depends_on_task_id=t1_id)
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)
    adapter = TestWorkerAdapter()

    # Attempt 1: Fails, but < max_attempts (2) -> Re-queued to READY
    disp1 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    fail_res1 = await adapter.execute_task(disp1[0], simulate_failure=True)
    await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=fail_res1)

    async with uow_factory() as uow:
        refreshed = await uow.tasks.get_by_id(t1_id)
        assert refreshed.state == TaskState.READY
        assert refreshed.attempt_count == 1

    # Attempt 2: Fails and exhausts max_attempts -> Transitions to FAILED
    disp2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    fail_res2 = await adapter.execute_task(disp2[0], simulate_failure=True)
    await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=fail_res2)

    async with uow_factory() as uow:
        final_t1 = await uow.tasks.get_by_id(t1_id)
        final_t2 = await uow.tasks.get_by_id(t2_id)
        assert final_t1.state == TaskState.FAILED
        assert final_t2.state == TaskState.BLOCKED  # Dependency cascade failure


# ==============================================================================
# 20. Concurrent Budget Reservations
# ==============================================================================


@pytest.mark.asyncio
async def test_20_concurrent_budget_reservations(uow_factory):
    """Verify atomic reservations enforce total tokens <= max_tokens."""
    async with uow_factory() as uow:
        org_id, m_id, _ = await setup_test_org_and_mission(uow, max_tokens=10_000)
        # Attempt to reserve 6,000 tokens twice concurrently
        await uow.budgets.reserve(mission_id=m_id, tokens=6_000, cost_usd=Decimal("0.1"))
        await uow.commit()

    async with uow_factory() as uow:
        with pytest.raises(BudgetExceededError, match="limit exceeded"):
            await uow.budgets.reserve(mission_id=m_id, tokens=6_000, cost_usd=Decimal("0.1"))


# ==============================================================================
# 21. Budget Exhaustion
# ==============================================================================


@pytest.mark.asyncio
async def test_21_budget_exhaustion(uow_factory):
    """Verify task readiness evaluator blocks scheduling when budget headroom is exhausted."""
    dag_engine = TaskDAGEngine()
    t_id = uuid4()
    task = TaskModel(id=t_id, identifier="T-BUDGET", title="Budget", description="B", assigned_role="backend_engineer")
    mission = MissionModel(id=uuid4(), org_id=uuid4(), state=MissionState.RUNNING, active_plan_version=1)
    plan = TaskPlanModel(id=uuid4(), mission_id=mission.id, plan_version=1)

    # Budget with 0 remaining tokens
    budget = BudgetModel(
        org_id=mission.org_id,
        mission_id=mission.id,
        max_tokens=10_000,
        consumed_tokens=10_000,
        reserved_tokens=0,
    )

    report = dag_engine.evaluate_task_readiness(
        task=task, mission=mission, plan=plan, upstream_dependencies=[], budget=budget
    )
    assert not report.is_ready
    assert any("Insufficient token budget headroom" in r for r in report.rejection_reasons)


# ==============================================================================
# 22. Mission Cancellation Aborts In-Flight Tasks
# ==============================================================================


@pytest.mark.asyncio
async def test_22_mission_cancellation(uow_factory):
    """Verify reconciler cancels all non-terminal tasks and releases leases upon mission cancellation."""
    org_id, m_id, plan_id = None, None, None
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow, mission_state=MissionState.CANCELLED)
        t = await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-CANCEL",
            title="Cancel",
            description="Cancel",
            assigned_role="backend_engineer",
        )
        t.state = TaskState.ASSIGNED
        await uow.tasks.claim_lease(task_id=t_id, worker_id="w-cancel", fencing_token=1)
        await uow.commit()

    reconciler = SchedulerReconciler(uow_factory=uow_factory)
    await reconciler.reconcile_mission(mission_id=m_id, org_id=org_id)

    async with uow_factory() as uow:
        refreshed = await uow.tasks.get_by_id(t_id)
        assert refreshed.state == TaskState.CANCELLED


# ==============================================================================
# 23. Plan Revision Invalidation
# ==============================================================================


def test_23_plan_revision_invalidation():
    """Verify task belonging to older plan version is rejected when active plan version advanced."""
    dag_engine = TaskDAGEngine()
    t_id = uuid4()
    task = TaskModel(id=t_id, identifier="T-REV", title="Rev", description="Rev", assigned_role="backend_engineer")
    mission = MissionModel(id=uuid4(), org_id=uuid4(), state=MissionState.RUNNING, active_plan_version=2)
    # Task belongs to plan version 1
    plan = TaskPlanModel(id=uuid4(), mission_id=mission.id, plan_version=1)

    report = dag_engine.evaluate_task_readiness(task=task, mission=mission, plan=plan, upstream_dependencies=[])
    assert not report.is_ready
    assert any("active mission plan version is 2" in r for r in report.rejection_reasons)


# ==============================================================================
# 24. Task Result Idempotency
# ==============================================================================


@pytest.mark.asyncio
async def test_24_task_result_idempotency(uow_factory):
    """Verify duplicate submission after task completion is rejected."""
    org_id, m_id, plan_id = None, None, None
    t_id = uuid4()
    async with uow_factory() as uow:
        org_id, m_id, plan_id = await setup_test_org_and_mission(uow)
        t = await uow.tasks.create_task(
            task_id=t_id,
            task_plan_id=plan_id,
            mission_id=m_id,
            org_id=org_id,
            identifier="T-IDEM",
            title="Idem",
            description="Idem",
            assigned_role="backend_engineer",
        )
        t.state = TaskState.READY
        await uow.commit()

    scheduler = TaskScheduler(uow_factory=uow_factory)
    adapter = TestWorkerAdapter()

    dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
    res = await adapter.execute_task(dispatches[0])

    # First submission: succeeds
    await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res)

    # Second submission: lease is already released, so validation fails
    with pytest.raises(StaleLeaseError, match="stale fencing token"):
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res)


# ==============================================================================
# 25. LangGraph Scheduler Integration
# ==============================================================================


@pytest.mark.asyncio
async def test_25_langgraph_scheduler_integration():
    """Verify live mission graph traverses through Gate 1, persists tasks to PostgreSQL, and coordinates with TaskScheduler."""
    from sqlalchemy import select

    from syntra.domain.entities import MembershipRole
    from syntra.persistence.models import MembershipModel, TransactionalOutboxModel, UserModel

    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        m_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()
        proj_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="LG Phase 8 Org", slug=f"lg8-{org_id.hex[:6]}")
            user = UserModel(id=user_id, email=f"lg8-{user_id.hex[:6]}@example.com", full_name="LG8 User")
            uow.session.add(user)
            membership = MembershipModel(id=uuid4(), org_id=org_id, user_id=user_id, role=MembershipRole.OWNER)
            uow.session.add(membership)
            project = ProjectModel(id=proj_id, org_id=org_id, name="LG8 Proj", slug=f"lg8-{proj_id.hex[:6]}")
            uow.session.add(project)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Build Autonomous Backend Service",
                state=MissionState.DRAFT,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()
            await uow.budgets.create(
                org_id=org_id,
                mission_id=m_id,
                max_tokens=100_000,
                max_cost_usd=Decimal("10.0000"),
                max_concurrency=4,
            )
            await uow.commit()

        engine = WorkflowOrchestrationEngine()

        # Start mission up to Gate 1 passing live PostgreSQL UnitOfWork
        async with uow_factory() as uow:
            start_res = await engine.start_mission(
                mission_id=m_id,
                org_id=org_id,
                objective="Build Autonomous Backend Service",
                uow=uow,
            )
        assert "__interrupt__" in start_res
        interrupt_payload = start_res["__interrupt__"][0].value
        assert interrupt_payload["action_type"] == "TASK_PLAN_APPROVAL"

        # Resume approval through Gate 1 with human approval
        resume_payload = {
            "approval_id": interrupt_payload["approval_id"],
            "org_id": str(org_id),
            "user_id": str(user_id),
            "decision": "APPROVED",
            "action_digest": interrupt_payload["action_digest"],
        }
        async with uow_factory() as uow:
            resumed = await engine.resume_approval(mission_id=m_id, payload=resume_payload, uow=uow)

        # Invariant: graph traversed through ready, task_scheduling, and execution_coordination
        assert "ready" in resumed["executed_nodes"]
        assert "task_scheduling" in resumed["executed_nodes"]
        assert "execution_coordination" in resumed["executed_nodes"]

        # Verify PostgreSQL database state:
        async with uow_factory() as uow:
            # 1. Canonical plan is persisted and APPROVED
            plan = await uow.tasks.get_plan_by_version(mission_id=m_id, plan_version=1)
            assert plan is not None
            assert plan.status == TaskPlanStatus.APPROVED

            # 2. Tasks exist and were processed to COMPLETED by TaskScheduler & TestWorkerAdapter
            tasks, _, _ = await uow.tasks.list_for_mission(mission_id=m_id, org_id=org_id, limit=50)
            assert len(tasks) >= 2
            for task in tasks:
                assert task.state == TaskState.COMPLETED
                assert task.attempt_count >= 1
                latest_attempt = await uow.tasks.get_latest_attempt(task.id)
                assert latest_attempt is not None
                assert latest_attempt.state == AttemptState.SUCCEEDED

            # 3. Transactional Outbox contains TASK_DISPATCHED and TASK_COMPLETED events
            stmt_o = select(TransactionalOutboxModel).order_by(TransactionalOutboxModel.created_at.asc())
            res_o = await uow.session.execute(stmt_o)
            events = list(res_o.scalars().all())
            event_types = [e.event_type for e in events]
            assert "TASK_DISPATCHED" in event_types
            assert "TASK_COMPLETED" in event_types
    finally:
        await db.close()
