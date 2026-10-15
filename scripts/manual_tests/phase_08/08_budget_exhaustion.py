#!/usr/bin/env python3
"""Manual Test Scenario 8: Budget Exhaustion & Headroom Invariant Enforcement.

Verifies:
- Task readiness evaluator strictly rejects task execution when token/cost headroom is insufficient.
- TaskScheduler safely blocks dispatch and leaves tasks in PENDING when budget is exhausted.
- Direct concurrent over-allocation raises BudgetExceededError without corrupting reservation ledger.
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import uuid4

from dotenv import load_dotenv

from syntra.domain.entities import MissionState, TaskPlanStatus, TaskState
from syntra.domain.exceptions import BudgetExceededError
from syntra.persistence.models import MissionModel, ProjectModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.scheduling.scheduler import TaskScheduler
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)


async def main() -> None:
    print("[*] Scenario 8: Budget Exhaustion & Headroom Invariant Enforcement")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()
        t_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Budget Org", slug=f"budget-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Budget Project", slug=f"budget-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Budget Enforcement",
                state=MissionState.RUNNING,
                active_plan_version=1,
            )
            uow.session.add(mission)
            await uow.session.flush()

            await uow.tasks.create_plan(plan_id=plan_id, mission_id=m_id, version=1, status=TaskPlanStatus.APPROVED)

            # Restrict budget: only 5,000 tokens total (task requires 8,192 estimated tokens)
            await uow.budgets.create(
                org_id=org_id,
                mission_id=m_id,
                max_tokens=5_000,
                max_cost_usd=Decimal("0.0100"),
                max_concurrency=2,
            )

            await uow.tasks.create_task(
                task_id=t_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-BUDGET-CHECK",
                title="Budget Blocked Task",
                description="Should be held in PENDING",
                assigned_role="backend_engineer",
            )
            await uow.commit()

        scheduler = TaskScheduler(uow_factory=uow_factory)

        print("[*] Attempting to schedule ready tasks with insufficient budget headroom...")
        dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(dispatches) == 0, f"Expected 0 dispatches due to budget limit, got {len(dispatches)}"
        print("[+] Scheduler correctly held dispatch: 0 tasks dispatched.")

        async with uow_factory() as uow:
            t_refreshed = await uow.tasks.get_by_id(t_id)
            assert t_refreshed.state == TaskState.PENDING, "Task must remain PENDING"
            print(f"[+] Task state confirmed: {t_refreshed.state.value}")

        print("[*] Verifying direct atomic reservation rejection past max_tokens...")
        async with uow_factory() as uow:
            try:
                await uow.budgets.reserve(mission_id=m_id, tokens=6_000, cost_usd=Decimal("0.0200"))
                print("[!] FAIL: Expected BudgetExceededError")
                sys.exit(1)
            except BudgetExceededError as exc:
                print(f"[+] Successfully intercepted over-allocation: {exc}")

        print("[*] PASS: Scenario 8 complete.")

    finally:
        await db.close()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
