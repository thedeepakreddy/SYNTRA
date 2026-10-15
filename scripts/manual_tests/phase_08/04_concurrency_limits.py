#!/usr/bin/env python3
"""Manual Test Scenario 4: Concurrency Limit Enforcement.

Verifies:
- Mission with 5 READY tasks and max_concurrency=2 only dispatches 2 tasks concurrently.
- Re-invoking scheduler while active slots are saturated dispatches 0 tasks.
- As active tasks complete, freed slots are immediately dispatched on subsequent cycles.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import uuid4

from dotenv import load_dotenv

from syntra.domain.entities import MissionState, TaskPlanStatus
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
    print("[*] Scenario 4: Concurrency Limit Enforcement")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Conc Org", slug=f"conc-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Conc Project", slug=f"conc-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Concurrency",
                state=MissionState.RUNNING,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()

            await uow.tasks.create_plan(plan_id=plan_id, mission_id=m_id, version=1, status=TaskPlanStatus.APPROVED)
            # Strict limit: max_concurrency=2
            await uow.budgets.create(
                org_id=org_id,
                mission_id=m_id,
                max_tokens=100_000,
                max_cost_usd=Decimal("10.0000"),
                max_concurrency=2,
            )

            # Create 5 independent tasks
            for idx in range(1, 6):
                await uow.tasks.create_task(
                    task_id=uuid4(),
                    task_plan_id=plan_id,
                    mission_id=m_id,
                    org_id=org_id,
                    identifier=f"T-CONC-{idx}",
                    title=f"Task {idx}",
                    description=f"Concurrency test task {idx}",
                    assigned_role="backend_engineer",
                )
            await uow.commit()

        scheduler = TaskScheduler(uow_factory=uow_factory)
        worker = TestWorkerAdapter(worker_id="worker-conc-01")

        # Step 1: Dispatch cycle 1
        print("[*] Dispatch cycle 1: Expecting exactly 2 dispatches (concurrency limit)...")
        batch1 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(batch1) == 2, f"Expected 2 dispatches, got {len(batch1)}"
        print(f"[+] Cycle 1 correctly dispatched {len(batch1)} tasks.")

        # Step 2: Attempt dispatch cycle 2 while 2 are in progress
        print("[*] Dispatch cycle 2: Concurrency slots saturated, expecting 0 dispatches...")
        batch2 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(batch2) == 0, f"Expected 0 dispatches due to saturation, got {len(batch2)}"
        print("[+] Cycle 2 correctly dispatched 0 tasks.")

        # Step 3: Complete 1 task
        print("[*] Completing 1 task to free 1 slot...")
        res = await worker.execute_task(batch1[0])
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res)

        # Step 4: Dispatch cycle 3: exactly 1 task dispatched
        print("[*] Dispatch cycle 3: Expecting 1 task dispatched into freed slot...")
        batch3 = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(batch3) == 1, f"Expected 1 dispatch into freed slot, got {len(batch3)}"
        print(f"[+] Cycle 3 correctly dispatched {len(batch3)} task.")

        print("[*] PASS: Scenario 4 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
