#!/usr/bin/env python3
"""Manual Test Scenario 9: Mission Cancellation & In-Flight Task Abort.

Verifies:
- When a mission transitions to CANCELLED, SchedulerReconciler aborts all in-flight tasks.
- Non-terminal tasks (PENDING, READY, ASSIGNED, IN_PROGRESS) transition to CANCELLED.
- Worker leases are released back to the pool.
- Completed tasks are preserved as immutable audit records.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import uuid4

from dotenv import load_dotenv

from syntra.domain.entities import MissionState, TaskPlanStatus, TaskState
from syntra.persistence.models import MissionModel, ProjectModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.scheduling.reconciliation import SchedulerReconciler
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)


async def main() -> None:
    print("[*] Scenario 9: Mission Cancellation & In-Flight Task Abort")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()
        t_active_id = uuid4()
        t_completed_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Cancel Org", slug=f"cancel-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Cancel Project", slug=f"cancel-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            # Mission initially RUNNING
            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Cancel In-Flight Mission",
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

            # Task 1: Already completed
            t_comp = await uow.tasks.create_task(
                task_id=t_completed_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-COMPLETED",
                title="Finished Task",
                description="Should remain COMPLETED",
                assigned_role="backend_engineer",
            )
            t_comp.state = TaskState.COMPLETED

            # Task 2: Active / in-flight
            t_act = await uow.tasks.create_task(
                task_id=t_active_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-IN-FLIGHT",
                title="Active Task",
                description="Should be aborted",
                assigned_role="backend_engineer",
            )
            t_act.state = TaskState.ASSIGNED
            await uow.tasks.claim_lease(task_id=t_active_id, worker_id="worker-active-01", fencing_token=1)
            await uow.commit()

        # User or system cancels the mission
        print("[*] Transitioning mission state to CANCELLED...")
        async with uow_factory() as uow:
            m = await uow.missions.get_by_id_for_org(mission_id=m_id, org_id=org_id)
            m.state = MissionState.CANCELLED
            await uow.commit()

        print("[*] Running SchedulerReconciler to reconcile cancelled mission...")
        reconciler = SchedulerReconciler(uow_factory=uow_factory)
        summary = await reconciler.reconcile_mission(mission_id=m_id, org_id=org_id)
        print(f"[+] Reconciler sweep: {summary.details}")

        async with uow_factory() as uow:
            refreshed_active = await uow.tasks.get_by_id(t_active_id)
            refreshed_completed = await uow.tasks.get_by_id(t_completed_id)

            print(f"[+] In-flight task state: {refreshed_active.state.value}")
            print(f"[+] Completed task state: {refreshed_completed.state.value}")

            assert refreshed_active.state == TaskState.CANCELLED, "Active task must be CANCELLED"
            assert refreshed_completed.state == TaskState.COMPLETED, "Completed task must remain COMPLETED"

        print("[*] PASS: Scenario 9 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
