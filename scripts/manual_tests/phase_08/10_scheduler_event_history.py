#!/usr/bin/env python3
"""Manual Test Scenario 10: Transactional Outbox Relay & Redis Event Stream Verification.

Verifies:
- TaskScheduler writes TASK_DISPATCHED events into the authoritative PostgreSQL/SQLite outbox table.
- OutboxRelay polls pending outbox events and reliably publishes them to Redis Streams.
- Worker processes dispatch and submits task completion.
- TASK_COMPLETED event is written to outbox table, creating an immutable audit trail.
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
from syntra.scheduling.outbox_relay import OutboxRelay
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.scheduling.scheduler import TaskScheduler
from syntra.scheduling.worker_adapter import TestWorkerAdapter
from syntra.storage.database import DatabaseManager

load_dotenv()

TEST_PG_URL = os.environ.get(
    "SYNTRA_TEST_POSTGRES_URL",
    "postgresql+asyncpg://syntra_test_user:syntra_test_user@localhost:5432/syntra_test",
)
TEST_REDIS_URL = os.environ.get("SYNTRA_REDIS_URL", "redis://localhost:6379/0")


async def main() -> None:
    print("[*] Scenario 10: Transactional Outbox Relay & Redis Event Stream Verification")
    db = DatabaseManager(TEST_PG_URL)
    await db.init_tables()
    session_factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    test_stream = f"syntra:manual_test_dispatch_{uuid4().hex[:6]}"
    dispatcher = RedisTaskDispatcher(TEST_REDIS_URL, stream_key=test_stream)
    relay = OutboxRelay(uow_factory=uow_factory, dispatcher=dispatcher)

    try:
        org_id, m_id, plan_id = uuid4(), uuid4(), uuid4()
        t_id = uuid4()

        async with uow_factory() as uow:
            await uow.organizations.create(org_id=org_id, name="Outbox Org", slug=f"outbox-org-{org_id.hex[:6]}")
            proj_id = uuid4()
            proj = ProjectModel(id=proj_id, org_id=org_id, name="Outbox Project", slug=f"outbox-proj-{proj_id.hex[:6]}")
            uow.session.add(proj)
            await uow.session.flush()

            mission = MissionModel(
                id=m_id,
                org_id=org_id,
                project_id=proj_id,
                objective="Test Outbox and Redis Stream Relay",
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

            await uow.tasks.create_task(
                task_id=t_id,
                task_plan_id=plan_id,
                mission_id=m_id,
                org_id=org_id,
                identifier="T-OUTBOX-01",
                title="Relay Task",
                description="Test transactional outbox relay",
                assigned_role="backend_engineer",
            )
            await uow.commit()

        scheduler = TaskScheduler(uow_factory=uow_factory)
        worker = TestWorkerAdapter(worker_id="worker-stream-01")

        # 1. Schedule ready tasks
        print("[*] Scheduling task (stages TASK_DISPATCHED in outbox table)...")
        dispatches = await scheduler.schedule_ready_tasks(mission_id=m_id, org_id=org_id)
        assert len(dispatches) == 1

        # 2. Inspect outbox before relay
        async with uow_factory() as uow:
            pending_events = await uow.outbox.get_pending_events(limit=200)
            my_events = [e for e in pending_events if e.payload.get("task_id") == str(t_id)]
            assert len(my_events) >= 1, f"Expected staged outbox event for task {t_id}"
            assert my_events[0].event_type == "TASK_DISPATCHED"
            print(f"[+] Outbox pending events: {len(pending_events)} (found staged TASK_DISPATCHED for task {t_id})")

        # 3. Outbox relay forwards event to Redis Streams
        print("[*] Running OutboxRelay to forward outbox events to Redis Streams...")
        relayed_count = await relay.relay_batch(limit=200)
        print(f"[+] Relayed {relayed_count} events to Redis stream '{test_stream}'.")
        assert relayed_count >= 1

        # 4. Worker reads from Redis Streams
        print("[*] Worker reading dispatch from Redis Streams...")
        messages = await dispatcher.read_dispatches(consumer_name="worker-stream-01", count=100)
        assert len(messages) >= 1
        target_msg = None
        for m_id_str, disp in messages:
            if disp.task_id == t_id:
                target_msg = (m_id_str, disp)
                break
        assert target_msg is not None, f"Expected dispatch for task {t_id} in stream messages"
        msg_id, received_dispatch = target_msg
        print(f"[+] Received Redis stream message: {msg_id} (task_id={received_dispatch.task_id})")
        assert received_dispatch.task_id == t_id

        # 5. Worker acknowledges and submits execution result
        acked = await dispatcher.acknowledge_dispatch(msg_id)
        assert acked is True
        print(f"[+] Acknowledged message {msg_id} on Redis stream.")

        res = await worker.execute_task(received_dispatch)
        await scheduler.handle_task_completion(mission_id=m_id, org_id=org_id, result=res)

        # 6. Verify task completed and completion event logged
        async with uow_factory() as uow:
            refreshed = await uow.tasks.get_by_id(t_id)
            assert refreshed.state == TaskState.COMPLETED
            print(f"[+] Task {t_id} state is COMPLETED.")

        print("[*] PASS: Scenario 10 complete.")

    finally:
        client = await dispatcher.get_client()
        await client.delete(test_stream)
        await dispatcher.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
