#!/usr/bin/env python3
"""Manual Test Scenario 7: Worker Failure Recovery & Cascading Failure Propagation.

Verifies:
- Task failure within retry budget automatically re-queues task to READY.
- Attempt count increments monotonically.
- Exhausting retry budget transitions task to FAILED.
- Downstream dependent tasks automatically cascade to BLOCKED status.
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
from syntra.scheduling.scheduler import TaskScheduler
from syntra.scheduling.worker_adapter import TestWorkerAdapter
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)


async def main() -> None:
    print("[*] Scenario 7: Worker Failure Recovery & Cascading Failure Propagation")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()
        t1_id, t2_id = uuid4(), uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Failure Org", slug=f"fail-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Fail Project", slug=f"fail-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Failure Cascading",
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

            # T1 has max_attempts=2
            await uow.tasks.create_task(
                task_id=t1_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-RETRY",
                title="Retry Task",
                description="Simulated flaking task",
                assigned_role="backend_engineer",
                max_attempts=2,
            )
            # T2 depends on T1
            await uow.tasks.create_task(
                task_id=t2_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-DEPENDENT",
                title="Dependent Task",
                description="Downstream dependent",
                assigned_role="backend_engineer",
            )
            await uow.tasks.add_dependency(task_id=t2_id, depends_on_task_id=t1_id)
            await uow.commit()

        scheduler = TaskScheduler(uow_factory=uow_factory)
        worker = TestWorkerAdapter(worker_id="worker-flaky-01")

        # Turn 1: Attempt 1 fails
        print("[*] Scheduling Turn 1 (Attempt 1 of 2)...")
        d1 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(d1) == 1 and d1[0].task_id == t1_id
        res1 = await worker.execute_task(d1[0], simulate_failure=True, error_message="Network glitch")
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res1)

        async with uow_factory() as uow:
            t1_after_1 = await uow.tasks.get_by_id(t1_id)
            print(f"[+] After failure 1: T1 state={t1_after_1.state.value}, attempts={t1_after_1.attempt_count}")
            assert t1_after_1.state == TaskState.READY, "T1 should be re-queued to READY"
            assert t1_after_1.attempt_count == 1

        # Turn 2: Attempt 2 fails and exhausts retries
        print("[*] Scheduling Turn 2 (Attempt 2 of 2)...")
        d2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(d2) == 1 and d2[0].task_id == t1_id
        res2 = await worker.execute_task(d2[0], simulate_failure=True, error_message="Syntax crash")
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res2)

        async with uow_factory() as uow:
            t1_final = await uow.tasks.get_by_id(t1_id)
            t2_final = await uow.tasks.get_by_id(t2_id)
            print(f"[+] Final T1 state: {t1_final.state.value} (attempts: {t1_final.attempt_count})")
            print(f"[+] Final T2 state: {t2_final.state.value}")

            assert t1_final.state == TaskState.FAILED, "T1 must transition to FAILED"
            assert t2_final.state == TaskState.BLOCKED, "T2 must cascade to BLOCKED"

        print("[*] PASS: Scenario 7 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
