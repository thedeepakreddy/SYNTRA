#!/usr/bin/env python3
"""Manual Test Scenario 7: Administrative Lifecycle Pause, Resume, and Cancellation.

Verifies:
- Administrative pause of running mission (RUNNING -> PAUSED).
- Resumption of paused mission (PAUSED -> RUNNING).
- Administrative cancellation of running mission (RUNNING -> CANCELLED).
- Automatic cancellation of pending tasks when mission is cancelled.
- Rejection of invalid transitions from terminal CANCELLED state.
"""

import asyncio
import sys
from uuid import uuid4

from syntra.domain.entities import MissionState, TaskState
from syntra.domain.exceptions import InvalidStateTransitionError
from syntra.orchestration.lifecycle_service import (
    cancel_mission,
    pause_mission,
    resume_mission,
)
from syntra.persistence.unit_of_work import UnitOfWork
from syntra.storage.database import DatabaseManager


async def main() -> None:
    print("[*] Scenario 7: Administrative Pause, Resume, and Cancellation")
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()

    org_id = uuid4()
    proj_id = uuid4()
    mission_id = uuid4()
    task1_id = uuid4()
    task2_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        # Seed test organization, project, and running mission
        await uow.organizations.create(org_id=org_id, name="Lifecycle Org", slug=f"lifecycle-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="Lifecycle Proj", slug=f"proj-{proj_id}")
        mission = await uow.missions.create(
            mission_id=mission_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Lifecycle Pause and Cancel Test",
        )
        mission.state = MissionState.RUNNING

        # Seed a plan and tasks
        plan_id = uuid4()
        plan = await uow.tasks.create_plan(
            plan_id=plan_id,
            mission_id=mission_id,
            version=1,
        )
        await uow.tasks.create_task(
            task_id=task1_id,
            task_plan_id=plan.id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-01",
            title="Task 1",
            description="Task 1 description",
            assigned_role="backend_engineer",
        )
        t2 = await uow.tasks.create_task(
            task_id=task2_id,
            task_plan_id=plan.id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-02",
            title="Task 2",
            description="Task 2 description",
            assigned_role="backend_engineer",
        )
        t2.state = TaskState.READY
        await uow.commit()

        # 1. Pause
        print(f"[*] Pausing running mission {mission_id}...")
        pause_res = await pause_mission(mission_id=mission_id, org_id=org_id, reason="Maintenance", uow=uow)
        print(f"[+] Paused status: {pause_res['status']}")
        if pause_res["status"] != "PAUSED":
            print("[!] FAIL: Expected PAUSED status")
            sys.exit(1)

        # 2. Resume
        print(f"[*] Resuming paused mission {mission_id}...")
        resume_res = await resume_mission(mission_id=mission_id, org_id=org_id, uow=uow)
        print(f"[+] Resumed status: {resume_res['status']}")
        if resume_res["status"] != "RUNNING":
            print("[!] FAIL: Expected RUNNING status")
            sys.exit(1)

        # 3. Cancel
        print(f"[*] Cancelling running mission {mission_id}...")
        cancel_res = await cancel_mission(mission_id=mission_id, org_id=org_id, reason="Operator abort", uow=uow)
        print(f"[+] Cancelled status: {cancel_res['status']}")
        if cancel_res["status"] != "CANCELLED":
            print("[!] FAIL: Expected CANCELLED status")
            sys.exit(1)

        # 4. Verify tasks were automatically cancelled
        t1_updated = await uow.tasks.get_by_id_for_org(task1_id, org_id)
        t2_updated = await uow.tasks.get_by_id_for_org(task2_id, org_id)
        print(f"[+] Task 1 state after cancel: {t1_updated.state}")
        print(f"[+] Task 2 state after cancel: {t2_updated.state}")
        if t1_updated.state != TaskState.CANCELLED or t2_updated.state != TaskState.CANCELLED:
            print("[!] FAIL: Pending tasks were not set to CANCELLED!")
            sys.exit(1)

        # 5. Verify cancel on terminal state raises InvalidStateTransitionError
        print("[*] Attempting to cancel already cancelled mission...")
        try:
            await cancel_mission(mission_id=mission_id, org_id=org_id, reason="Second cancel", uow=uow)
            print("[!] FAIL: Cancelling terminal mission did not raise InvalidStateTransitionError!")
            sys.exit(1)
        except InvalidStateTransitionError:
            print("[+] Caught expected InvalidStateTransitionError on terminal mission.")

    print("[SUCCESS] Scenario 7 passed: Pause, resume, and cancellation verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
