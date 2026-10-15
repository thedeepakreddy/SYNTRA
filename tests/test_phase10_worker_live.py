"""Mandatory real PostgreSQL -> outbox -> Redis -> Docker -> result handoff gate."""

import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_scheduling_phase8 import setup_test_org_and_mission

from syntra.domain.entities import TaskState
from syntra.persistence.artifact_store import read_artifact
from syntra.persistence.models import Base
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.sandbox.worker_bridge import SandboxWorkerAdapter
from syntra.scheduling.consumer import SandboxWorkerConsumer
from syntra.scheduling.outbox_relay import OutboxRelay
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.scheduling.scheduler import TaskScheduler

pytest_plugins = ["test_sandbox_phase9"]


@pytest.mark.integration
@pytest.mark.docker
async def test_live_authoritative_worker_handoff(test_git_repo):
    load_dotenv()
    url = os.environ.get("SYNTRA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("BLOCKED_BY_DEPENDENCY: SYNTRA_TEST_POSTGRES_URL is required")
    if "test" not in (make_url(url).database or "").lower():
        raise ValueError("Live acceptance requires a dedicated test database")
    schema = "phase10_" + uuid4().hex
    admin = create_async_engine(url)
    engine = None
    dispatcher = RedisTaskDispatcher(
        os.environ.get("SYNTRA_REDIS_URL", "redis://localhost:6379/0"), stream_key=f"syntra:phase10:{uuid4().hex}"
    )
    try:
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        def uow_factory():
            return SqlAlchemyUnitOfWork(factory)

        async with uow_factory() as uow:
            org, mission, plan = await setup_test_org_and_mission(uow)
            task = await uow.tasks.create_task(
                task_id=uuid4(),
                task_plan_id=plan,
                mission_id=mission,
                org_id=org,
                identifier="LIVE-10",
                title="Correct fixture",
                description="Correct the deliberate fixture defect",
                assigned_role="backend_engineer",
            )
            await uow.commit()
        scheduler = TaskScheduler(uow_factory)
        (dispatch,) = await scheduler.schedule_ready_tasks(mission, org)
        assert await OutboxRelay(uow_factory, dispatcher).relay_batch() == 1
        mid, delivered = (await dispatcher.read_dispatches("live-worker", block_ms=1000))[0]
        repo, base = test_git_repo
        adapter = SandboxWorkerAdapter(repo, worker_id="live-worker", base_commit=base)
        consumer = SandboxWorkerConsumer(scheduler, dispatcher, adapter, "live-worker")
        assert await consumer.process(
            mid,
            delivered,
            code_changes={"src/service.py": "def run():\n    return True\n"},
            commands_to_run=["python -c 'from src.service import run; assert run() is True'"],
        )
        # A duplicate notification must never recreate a worktree or execute again.
        duplicate = await dispatcher.publish_dispatch(dispatch)
        assert not await consumer.process(duplicate, dispatch)
        async with uow_factory() as uow:
            stored = await uow.tasks.get_by_id(task.id)
            assert stored.state == TaskState.COMPLETED
            artifacts, _, _ = await uow.artifacts.list_for_mission(mission, org)
            bodies = [await read_artifact(uow, artifact_id=a.id, mission_id=mission, org_id=org) for a, _ in artifacts]
            assert any("+    return True" in b for b in bodies)
            assert any('"exit_code": 0' in b and '"command"' in b for b in bodies)
        assert "return False" in (repo / "src/service.py").read_text()
        assert not list((repo / ".syntra/sandboxes").glob("wt_*"))
        client = await dispatcher.get_client()
        assert (await client.xpending(dispatcher.stream_key, dispatcher.consumer_group))["pending"] == 0
    finally:
        client = await dispatcher.get_client()
        await client.delete(dispatcher.stream_key)
        await dispatcher.close()
        if engine:
            await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()
