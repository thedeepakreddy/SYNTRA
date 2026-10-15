#!/usr/bin/env python3
"""Manual Test Scenario 5: Duplicate Claim Prevention with PostgreSQL Row Locks.

Verifies:
- Live PostgreSQL row-level locks (FOR UPDATE SKIP LOCKED) guarantee atomic task claiming.
- Two worker routines simultaneously requesting task leases receive mutually exclusive tasks.
- Zero duplicate task executions under high concurrency.
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
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)


async def main() -> None:
    print("[*] Scenario 5: Duplicate Claim Prevention with PostgreSQL Row Locks")
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
        t2_id = uuid4()

        print("[*] Creating 2 READY tasks in live PostgreSQL test database...")
        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Lock Org", slug=f"lock-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Lock Project", slug=f"lock-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Row Locking",
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
                identifier="T-LOCK-1",
                title="Lock Task 1",
                description="Atomic claim test",
                assigned_role="backend_engineer",
            )
            t2 = await uow.tasks.create_task(
                task_id=t2_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-LOCK-2",
                title="Lock Task 2",
                description="Atomic claim test",
                assigned_role="backend_engineer",
            )
            t1.state = TaskState.READY
            t2.state = TaskState.READY
            await uow.commit()

        print("[*] Launching simultaneous worker claim requests...")

        async def worker_claim(worker_id: str):
            async with uow_factory() as uow:
                claimed = await uow.tasks.claim_ready_tasks_atomic(
                    mission_id=m_id,
                    limit=1,
                    worker_id=worker_id,
                    lease_duration_seconds=30,
                )
                await uow.commit()
                return claimed

        results = await asyncio.gather(
            worker_claim("worker-gamma"),
            worker_claim("worker-delta"),
        )

        res_gamma = results[0]
        res_delta = results[1]

        assert len(res_gamma) == 1, "worker-gamma should claim exactly 1 task"
        assert len(res_delta) == 1, "worker-delta should claim exactly 1 task"

        t_gamma_id = res_gamma[0][0].id
        t_delta_id = res_delta[0][0].id

        print(f"[+] Worker Gamma claimed: {t_gamma_id}")
        print(f"[+] Worker Delta claimed: {t_delta_id}")

        assert t_gamma_id != t_delta_id, "CRITICAL ERROR: Duplicate task claimed across concurrent workers!"
        print("[+] Mutual exclusivity invariant verified successfully.")
        print("[*] PASS: Scenario 5 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
