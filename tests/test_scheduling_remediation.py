"""Remediation verification tests for Phase 8.

Tests:
1. Concurrent TaskScheduler claims on PostgreSQL without duplicate attempt collisions.
2. Agent-role concurrency limits (e.g. backend_engineer=1, qa_engineer=2).
3. LangGraph canonical plan persistence into PostgreSQL and real TaskScheduler dispatch.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from dotenv import load_dotenv

from syntra.domain.entities import (
    AgentRole,
    AttemptState,
    MissionState,
    TaskPlanStatus,
    TaskState,
)
from syntra.persistence.models import (
    MissionModel,
    ProjectModel,
    UserModel,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.scheduling.scheduler import TaskScheduler
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_scheduler_claims_pg():
    """Verify concurrent TaskScheduler dispatches on live PostgreSQL do not collide on uq_task_attempt_number."""
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id = uuid4()
        m_id = uuid4()
        plan_id = uuid4()
        t1_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Conc Org", slug=f"conc-{org_id.hex[:6]}")
            proj = ProjectModel(id=uuid4(), org_id=org_id, name="Conc Proj", slug=f"conc-{uuid4().hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj.id,
                objective="Concurrent Dispatch Test",
                state=MissionState.RUNNING,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()

            await uow.tasks.create_plan(plan_id=plan_id, mission_id=m_id, version=1, status=TaskPlanStatus.APPROVED)
            await uow.budgets.create(
                org_id=org_id,
                mission_id=m_id,
                max_tokens=100_000,
                max_cost_usd=Decimal("10.0000"),
                max_concurrency=4,
            )

            t1 = await uow.tasks.create_task(
                task_id=t1_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-CONC-PG-1",
                title="Concurrent Task",
                description="Testing concurrent schedule_ready_tasks",
                assigned_role="backend_engineer",
            )
            t1.state = TaskState.READY
            await uow.commit()

        scheduler1 = TaskScheduler(uow_factory=uow_factory)
        scheduler2 = TaskScheduler(uow_factory=uow_factory)

        # Simultaneous dispatches
        res1, res2 = await asyncio.gather(
            scheduler1.schedule_ready_tasks(mission_id=m_id, org_id=org_id, worker_id="sched-1"),
            scheduler2.schedule_ready_tasks(mission_id=m_id, org_id=org_id, worker_id="sched-2"),
        )

        total_dispatches = len(res1) + len(res2)
        assert total_dispatches == 1, f"Expected exactly 1 dispatch across both schedulers, got {total_dispatches}"

        async with uow_factory() as uow:
            refreshed = await uow.tasks.get_by_id(t1_id)
            assert refreshed.state == TaskState.ASSIGNED
            assert refreshed.attempt_count == 1
            latest_attempt = await uow.tasks.get_latest_attempt(t1_id)
            assert latest_attempt is not None
            assert latest_attempt.attempt_number == 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_agent_role_concurrency_limits():
    """Verify scheduler enforces both mission-wide and per-role concurrency limits."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id = uuid4()
        m_id = uuid4()
        plan_id = uuid4()

        # 3 backend tasks, 2 QA tasks
        b_ids = [uuid4() for _ in range(3)]
        q_ids = [uuid4() for _ in range(2)]

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Role Org", slug="role-org")
            proj = ProjectModel(id=uuid4(), org_id=org_id, name="Role Proj", slug="role-proj")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj.id,
                objective="Role Concurrency Test",
                state=MissionState.RUNNING,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()

            await uow.tasks.create_plan(plan_id=plan_id, mission_id=m_id, version=1, status=TaskPlanStatus.APPROVED)
            # Mission max concurrency is 4
            await uow.budgets.create(
                org_id=org_id,
                mission_id=m_id,
                max_tokens=100_000,
                max_cost_usd=Decimal("10.0000"),
                max_concurrency=4,
            )

            for idx, b_id in enumerate(b_ids, 1):
                t = await uow.tasks.create_task(
                    task_id=b_id,
                    task_plan_id=plan_id,
                    mission_id=m_id,
                    org_id=org_id,
                    identifier=f"B-{idx}",
                    title=f"Backend Task {idx}",
                    description="Backend",
                    assigned_role=AgentRole.BACKEND_ENGINEER.value,
                    priority=10 - idx,  # B-1 has highest priority
                )
                t.state = TaskState.READY

            for idx, q_id in enumerate(q_ids, 1):
                t = await uow.tasks.create_task(
                    task_id=q_id,
                    task_plan_id=plan_id,
                    mission_id=m_id,
                    org_id=org_id,
                    identifier=f"Q-{idx}",
                    title=f"QA Task {idx}",
                    description="QA",
                    assigned_role=AgentRole.QA_ENGINEER.value,
                    priority=5 - idx,
                )
                t.state = TaskState.READY

            await uow.commit()

        # Configured role limits: backend_engineer=1, qa_engineer=2
        role_limits = {
            AgentRole.BACKEND_ENGINEER.value: 1,
            AgentRole.QA_ENGINEER.value: 2,
        }
        scheduler = TaskScheduler(uow_factory=uow_factory, role_concurrency_limits=role_limits)

        dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)

        # Expected: exactly 3 tasks dispatched (1 backend, 2 QA)
        assert len(dispatches) == 3

        dispatched_roles = [d.assigned_role for d in dispatches]
        assert dispatched_roles.count(AgentRole.BACKEND_ENGINEER.value) == 1
        assert dispatched_roles.count(AgentRole.QA_ENGINEER.value) == 2

        # The backend task dispatched must be B-1 (highest priority)
        dispatched_task_ids = [d.task_id for d in dispatches]
        assert b_ids[0] in dispatched_task_ids
        assert b_ids[1] not in dispatched_task_ids
        assert b_ids[2] not in dispatched_task_ids

        # Immediate second dispatch must dispatch 0 tasks because role limits are saturated
        dispatches_2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(dispatches_2) == 0
    finally:
        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_langgraph_postgresql_persistence_and_scheduler():
    """Verify LangGraph persists canonical plan in PostgreSQL and coordinates with TaskScheduler."""
    from syntra.orchestration.engine import WorkflowOrchestrationEngine
    from syntra.persistence.models import TransactionalOutboxModel

    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id = uuid4()
        user_id = uuid4()
        m_id = uuid4()
        proj_id = uuid4()

        async with uow_factory() as uow:
            from syntra.domain.entities import MembershipRole
            from syntra.persistence.models import MembershipModel

            await uow.organizations.create(org_id=org_id, name="LG Org", slug=f"lg-{org_id.hex[:6]}")
            u = UserModel(
                id=user_id,
                email=f"lg-{user_id.hex[:6]}@example.com",
                full_name="LG User",
            )
            uow.session.add(u)
            mem = MembershipModel(
                id=uuid4(),
                org_id=org_id,
                user_id=user_id,
                role=MembershipRole.OWNER,
            )
            uow.session.add(mem)
            proj = ProjectModel(id=proj_id, org_id=org_id, name="LG Proj", slug=f"lg-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj.id,
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

        # Resume through Gate 1 with human approval
        resume_payload = {
            "approval_id": interrupt_payload["approval_id"],
            "org_id": str(org_id),
            "user_id": str(user_id),
            "decision": "APPROVED",
            "action_digest": interrupt_payload["action_digest"],
        }

        async with uow_factory() as uow:
            resumed = await engine.resume_approval(
                mission_id=m_id,
                payload=resume_payload,
                uow=uow,
            )

        # Invariant: nodes executed
        assert "ready" in resumed["executed_nodes"]
        assert "task_scheduling" in resumed["executed_nodes"]
        assert "execution_coordination" in resumed["executed_nodes"]

        # Verify PostgreSQL database state
        async with uow_factory() as uow:
            # 1. Task plan exists and is APPROVED
            plan = await uow.tasks.get_plan_by_version(mission_id=m_id, plan_version=1)
            assert plan is not None
            assert plan.status == TaskPlanStatus.APPROVED

            # 2. Tasks exist and are COMPLETED
            tasks, _, _ = await uow.tasks.list_for_mission(mission_id=m_id, org_id=org_id, limit=50)
            assert len(tasks) >= 2
            for t in tasks:
                assert t.state == TaskState.COMPLETED
                assert t.attempt_count >= 1
                latest_attempt = await uow.tasks.get_latest_attempt(t.id)
                assert latest_attempt is not None
                assert latest_attempt.state == AttemptState.SUCCEEDED

            # 3. Transactional Outbox contains TASK_DISPATCHED and TASK_COMPLETED
            from sqlalchemy import select

            stmt_o = select(TransactionalOutboxModel).order_by(TransactionalOutboxModel.created_at.asc())
            res_o = await uow.session.execute(stmt_o)
            events = list(res_o.scalars().all())
            event_types = [e.event_type for e in events]
            assert "TASK_DISPATCHED" in event_types
            assert "TASK_COMPLETED" in event_types

    finally:
        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_rollback_and_outbox_atomicity():
    """Verify that failures during dispatch roll back task mutations, attempt rows, leases, and outbox events atomically."""
    from sqlalchemy import select

    from syntra.persistence.models import TaskAttemptModel, TransactionalOutboxModel, WorkerLeaseModel

    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id = uuid4()
        m_id = uuid4()
        plan_id = uuid4()
        t_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Rollback Org", slug=f"rb-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="RB Proj", slug=f"rb-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Atomicity Rollback",
                state=MissionState.RUNNING,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()

            await uow.tasks.create_plan(plan_id=plan_id, mission_id=m_id, version=1, status=TaskPlanStatus.APPROVED)
            t = await uow.tasks.create_task(
                task_id=t_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-RB-01",
                title="Rollback Task",
                description="Atomic rollback test",
                assigned_role="backend_engineer",
            )
            t.state = TaskState.READY
            await uow.commit()

        # Simulate simulated crash mid-transaction
        with pytest.raises(RuntimeError, match="Simulated crash mid-dispatch"):
            async with uow_factory() as uow:
                task = await uow.tasks.get_by_id(t_id)
                task.state = TaskState.ASSIGNED
                task.attempt_count += 1
                await uow.tasks.create_attempt(task_id=task.id, attempt_number=task.attempt_count)
                await uow.tasks.claim_lease(task_id=task.id, worker_id="worker-crash", fencing_token=1)
                uow.publish_event(
                    event_type="TASK_DISPATCHED",
                    payload={"task_id": str(task.id), "mission_id": str(m_id)},
                )
                # Crash before commit
                raise RuntimeError("Simulated crash mid-dispatch")

        # Invariant: Nothing committed to PostgreSQL
        async with uow_factory() as uow:
            refreshed = await uow.tasks.get_by_id(t_id)
            assert refreshed.state == TaskState.READY
            assert refreshed.attempt_count == 0

            # Zero attempts
            stmt_att = select(TaskAttemptModel).where(TaskAttemptModel.task_id == t_id)
            res_att = await uow.session.execute(stmt_att)
            assert len(list(res_att.scalars().all())) == 0

            # Zero leases
            stmt_l = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == t_id)
            res_l = await uow.session.execute(stmt_l)
            assert len(list(res_l.scalars().all())) == 0

            # Zero outbox events for this task
            stmt_o = select(TransactionalOutboxModel)
            res_o = await uow.session.execute(stmt_o)
            events = [e for e in res_o.scalars().all() if e.payload.get("task_id") == str(t_id)]
            assert len(events) == 0

    finally:
        await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repeated_checkpoint_resume_idempotency():
    """Verify that repeated resume of an already-processed checkpoint does not duplicate side effects."""
    from syntra.domain.entities import MembershipRole
    from syntra.orchestration.engine import WorkflowOrchestrationEngine
    from syntra.persistence.models import MembershipModel

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
            await uow.organizations.create(org_id=org_id, name="Idemp Org", slug=f"idemp-{org_id.hex[:6]}")
            user = UserModel(id=user_id, email=f"idemp-{user_id.hex[:6]}@example.com", full_name="Idemp User")
            uow.session.add(user)
            membership = MembershipModel(id=uuid4(), org_id=org_id, user_id=user_id, role=MembershipRole.OWNER)
            uow.session.add(membership)
            project = ProjectModel(id=proj_id, org_id=org_id, name="Idemp Proj", slug=f"idemp-{proj_id.hex[:6]}")
            uow.session.add(project)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Idempotent Mission",
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

        async with uow_factory() as uow:
            start_res = await engine.start_mission(
                mission_id=m_id,
                org_id=org_id,
                objective="Idempotent Mission",
                uow=uow,
            )

        interrupt_payload = start_res["__interrupt__"][0].value
        resume_payload = {
            "approval_id": interrupt_payload["approval_id"],
            "org_id": str(org_id),
            "user_id": str(user_id),
            "decision": "APPROVED",
            "action_digest": interrupt_payload["action_digest"],
        }

        # First resume (Gate 1: TASK_PLAN_APPROVAL)
        async with uow_factory() as uow:
            res1 = await engine.resume_approval(mission_id=m_id, payload=resume_payload, uow=uow)
        assert "task_scheduling" in res1["executed_nodes"]
        assert "__interrupt__" in res1
        gate2_interrupt = res1["__interrupt__"][0].value
        assert gate2_interrupt["action_type"] == "DELIVERY_APPROVAL"

        # Check DB record for Gate 1 is now CONSUMED in PostgreSQL
        async with uow_factory() as uow:
            from syntra.domain.entities import ApprovalDecision
            from syntra.domain.exceptions import ApprovalReplayError

            approval_rec = await uow.approvals.get_by_id_for_org(UUID(interrupt_payload["approval_id"]), org_id)
            assert approval_rec.decision == ApprovalDecision.CONSUMED

            # Replay attempt of consumed Gate 1 approval is blocked with ApprovalReplayError
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

        # Resume Gate 2 with valid delivery approval
        gate2_payload = {
            "approval_id": gate2_interrupt["approval_id"],
            "org_id": str(org_id),
            "user_id": str(user_id),
            "decision": "APPROVED",
            "action_digest": gate2_interrupt["action_digest"],
        }
        async with uow_factory() as uow:
            res2 = await engine.resume_approval(mission_id=m_id, payload=gate2_payload, uow=uow)
        assert "completed" in res2["executed_nodes"]
        assert res2["domain_state"] == "COMPLETED"

        # Invariant: Zero duplicate task or plan rows created
        async with uow_factory() as uow:
            tasks, _, _ = await uow.tasks.list_for_mission(mission_id=m_id, org_id=org_id, limit=50)
            assert len(tasks) == 2
            plan = await uow.tasks.get_plan_by_version(mission_id=m_id, plan_version=1)
            assert plan is not None

    finally:
        await db.close()
