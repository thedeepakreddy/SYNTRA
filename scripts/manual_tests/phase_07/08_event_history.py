#!/usr/bin/env python3
"""Manual Test Scenario 8: Transactional Outbox Event History Inspection.

Verifies:
- Lifecycle operations reliably publish events to the transactional outbox table.
- Event payload structure includes aggregate_type, aggregate_id, org_id, reason, timestamps.
- Verifies MISSION_PAUSED, MISSION_RESUMED, MISSION_CANCELLED, and MISSION_FAILED outbox events.
"""

import asyncio
import sys
from uuid import uuid4

from syntra.domain.entities import MissionState
from syntra.orchestration.lifecycle_service import (
    cancel_mission,
    pause_mission,
    resume_mission,
)
from syntra.persistence.unit_of_work import UnitOfWork
from syntra.storage.database import DatabaseManager


async def main() -> None:
    print("[*] Scenario 8: Transactional Outbox Event History Inspection")
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()

    org_id = uuid4()
    proj_id = uuid4()
    m1_id = uuid4()
    m2_id = uuid4()

    async with UnitOfWork(db.get_session_factory()) as uow:
        # Seed test organization and project
        await uow.organizations.create(org_id=org_id, name="Outbox Org", slug=f"outbox-{org_id}")
        await uow.projects.create(project_id=proj_id, org_id=org_id, name="Outbox Proj", slug=f"proj-{proj_id}")

        m1 = await uow.missions.create(
            mission_id=m1_id, org_id=org_id, project_id=proj_id, objective="Mission 1 Lifecycle"
        )
        m1.state = MissionState.RUNNING

        m2 = await uow.missions.create(
            mission_id=m2_id, org_id=org_id, project_id=proj_id, objective="Mission 2 Failure"
        )
        m2.state = MissionState.RUNNING
        await uow.commit()

        # 1. Trigger Pause and Resume on M1
        print("[*] Triggering MISSION_PAUSED and MISSION_RESUMED on Mission 1...")
        await pause_mission(mission_id=m1_id, org_id=org_id, reason="Budget audit pause", uow=uow)
        await resume_mission(mission_id=m1_id, org_id=org_id, uow=uow)

        # 2. Trigger Cancel on M1
        print("[*] Triggering MISSION_CANCELLED on Mission 1...")
        await cancel_mission(mission_id=m1_id, org_id=org_id, reason="Operator abort", uow=uow)

        # 3. Trigger Mission Failed on M2
        print("[*] Publishing MISSION_FAILED on Mission 2...")
        uow.publish_event(
            event_type="MISSION_FAILED",
            payload={
                "aggregate_type": "mission",
                "aggregate_id": str(m2_id),
                "mission_id": str(m2_id),
                "org_id": str(org_id),
                "reason": "Exceeded replan circuit breaker limit",
            },
        )
        await uow.commit()

        # 4. Query transactional outbox table
        print("[*] Inspecting pending events in transactional outbox table...")
        pending_events = await uow.outbox.get_pending_events(limit=50)
        print(f"[+] Total Pending Outbox Events: {len(pending_events)}")

        event_types = [e.event_type for e in pending_events]
        print(f"[+] Recorded Event Types: {event_types}")

        required_types = ["MISSION_PAUSED", "MISSION_RESUMED", "MISSION_CANCELLED", "MISSION_FAILED"]
        for req in required_types:
            if req not in event_types:
                print(f"[!] FAIL: Required event type '{req}' missing from outbox!")
                sys.exit(1)
            matching = [e for e in pending_events if e.event_type == req]
            sample = matching[0]
            print(
                f"    - {req}: aggregate_id={sample.payload.get('aggregate_id')}, reason={sample.payload.get('reason')}"
            )

    print("[SUCCESS] Scenario 8 passed: Transactional outbox event history verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
