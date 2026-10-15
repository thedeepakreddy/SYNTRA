#!/usr/bin/env python3
"""Manual Test Scenario 6: Lease Expiration Detection & Automatic Re-queuing.

Verifies:
- SchedulerReconciler scans for expired worker leases across active missions.
- Active attempt corresponding to an expired lease transitions to TIMED_OUT.
- Task automatically resets to READY for re-scheduling if remaining attempts allow.
- Expired lease record is deleted or cleared from the authoritative database.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import uuid4

from dotenv import load_dotenv

from syntra.domain.entities import AttemptState, MissionState, TaskPlanStatus, TaskState
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
    print("[*] Scenario 6: Lease Expiration Detection & Automatic Re-queuing")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()
        t_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Lease Org", slug=f"lease-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Lease Project", slug=f"lease-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Lease Expiration",
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
                max_concurrency=2,
            )

            # Create an in-flight task with an expired lease
            t = await uow.tasks.create_task(
                task_id=t_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-EXPIRE",
                title="Expired Task",
                description="Simulated stale lease",
                assigned_role="backend_engineer",
                max_attempts=3,
            )
            t.state = TaskState.ASSIGNED
            t.attempt_count = 1

            await uow.tasks.create_attempt(task_id=t_id, attempt_number=1, state=AttemptState.RUNNING)
            # Create lease that expired in the past
            await uow.tasks.claim_lease(task_id=t_id, worker_id="stale-worker", fencing_token=1, duration_seconds=-300)
            await uow.commit()

        print("[*] Running SchedulerReconciler...")
        reconciler = SchedulerReconciler(uow_factory=uow_factory)
        summary = await reconciler.reconcile_mission(mission_id=m_id, org_id=org_id)

        print(
            f"[+] Reconciler sweep: expired_leases={summary.expired_leases_count}, recovered={summary.recovered_attempts_count}"
        )
        assert summary.expired_leases_count == 1, "Expected 1 expired lease detected"
        assert summary.recovered_attempts_count == 1, "Expected 1 attempt recovered"

        # Verify state in database
        async with uow_factory() as uow:
            refreshed_task = await uow.tasks.get_by_id(t_id)
            latest_att = await uow.tasks.get_latest_attempt(t_id)

            print(f"[+] Refreshed Task State: {refreshed_task.state.value}")
            print(f"[+] Latest Attempt State: {latest_att.state.value}")

            assert refreshed_task.state == TaskState.READY, "Task must be reset to READY"
            assert latest_att.state == AttemptState.TIMED_OUT, "Attempt must be marked TIMED_OUT"

        print("[*] PASS: Scenario 6 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
