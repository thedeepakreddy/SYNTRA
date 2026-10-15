#!/usr/bin/env python3
"""Manual Test Scenario 3: Parallel Execution of Independent Tasks.

Verifies:
- Multiple independent tasks (branching DAG) are evaluated as READY simultaneously.
- TaskScheduler dispatches all independent tasks concurrently within concurrency limits.
- Worker simulates execution and submits valid results.
- Tasks transition to COMPLETED in database.
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
    print("[*] Scenario 3: Parallel Execution of Independent Tasks")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id = uuid4()
        m_id = uuid4()
        plan_id = uuid4()
        t_ids = [uuid4() for _ in range(3)]

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Parallel Org", slug=f"parallel-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(
                id=proj_id, org_id=org_id, name="Parallel Project", slug=f"parallel-proj-{proj_id.hex[:6]}"
            )
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Execute Parallel Tasks",
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

            # Create 3 independent tasks
            for idx, t_id in enumerate(t_ids, 1):
                await uow.tasks.create_task(
                    task_id=t_id,
                    task_plan_id=plan_id,
                    mission_id=m_id,
                    org_id=org_id,
                    identifier=f"T-PAR-{idx}",
                    title=f"Parallel Task {idx}",
                    description=f"Independent task {idx}",
                    assigned_role="backend_engineer",
                )
            await uow.commit()

        scheduler = TaskScheduler(
            uow_factory=uow_factory,
            role_concurrency_limits={"backend_engineer": 4},
        )
        worker = TestWorkerAdapter(worker_id="worker-parallel-01")

        print("[*] Scheduling ready tasks...")
        dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        print(f"[+] Dispatched {len(dispatches)} tasks in parallel.")
        assert len(dispatches) == 3, f"Expected 3 parallel dispatches, got {len(dispatches)}"

        print("[*] Simulating worker execution turns in parallel...")
        results = await asyncio.gather(*(worker.execute_task(d) for d in dispatches))

        print("[*] Handling task completion submissions...")
        for res in results:
            await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res)

        async with uow_factory() as uow:
            for t_id in t_ids:
                refreshed = await uow.tasks.get_by_id(t_id)
                assert refreshed.state == TaskState.COMPLETED, f"Task {t_id} expected COMPLETED, got {refreshed.state}"

        print("[+] All 3 parallel tasks successfully executed and completed.")
        print("[*] PASS: Scenario 3 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
