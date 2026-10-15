"""Operational Phase 10 commands. No implicit mock provider or host execution path."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import typer
from sqlalchemy import select

from syntra.agents.engineering_worker import EngineeringSandboxWorker
from syntra.agents.operational import AgentRegistry
from syntra.core.config import get_settings
from syntra.domain.entities import MissionState
from syntra.llm.gemini_provider import GeminiModelProvider
from syntra.llm.runtime import ModelRuntime
from syntra.orchestration.checkpointer import CheckpointerFactory
from syntra.orchestration.engine import WorkflowOrchestrationEngine
from syntra.orchestration.engineering_service import EngineeringMissionService
from syntra.persistence.models import MissionModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.sandbox.models import ContainerConfig
from syntra.scheduling.consumer import SandboxWorkerConsumer
from syntra.scheduling.outbox_relay import OutboxRelay
from syntra.scheduling.reconciliation import SchedulerReconciler
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.skills.registry import SkillRegistry
from syntra.storage.database import DatabaseManager

engineering_app = typer.Typer(help="Operational agents, durable missions and sandbox workers")


def registry() -> AgentRegistry:
    skills = SkillRegistry(root_dir=Path(__file__).resolve().parents[3] / "skills")
    skills.discover_skills()
    return AgentRegistry(skills)


@engineering_app.command("agents")
def list_agents() -> None:
    for definition in registry().definitions.values():
        typer.echo(
            json.dumps(
                {
                    "role": definition.role.value,
                    "version": definition.version,
                    "model": definition.model_id,
                    "skills": definition.allowed_skill_ids,
                    "capabilities": definition.allowed_tool_capabilities,
                    "maximum_turns": definition.maximum_turns,
                    "maximum_tool_calls": definition.maximum_tool_calls,
                    "timeout_seconds": definition.timeout_seconds,
                    "input_schema": definition.input_schema.__name__,
                    "output_schema": definition.output_schema.__name__,
                }
            )
        )


@asynccontextmanager
async def composition(verify: list[str]):
    settings = get_settings()
    provider = GeminiModelProvider()
    if not provider.is_configured():
        raise RuntimeError(
            "BLOCKED_BY_CREDENTIALS: live Gemini credentials are required; deterministic demonstrations are in the manual test harness"
        )
    if not settings.database_url.startswith("postgres"):
        raise RuntimeError("Operational missions require PostgreSQL; configure SYNTRA_DATABASE_URL")
    db = DatabaseManager(settings.database_url)
    factory = db.get_session_factory()

    def uow_factory():
        return SqlAlchemyUnitOfWork(factory)

    reg = registry()
    runtime = ModelRuntime(provider, reg.skills)
    service = EngineeringMissionService(uow_factory, reg, runtime, verify)
    pool, saver = await CheckpointerFactory.create_postgres_checkpointer(settings.database_url)
    dispatcher = RedisTaskDispatcher(settings.redis_url)
    engine = WorkflowOrchestrationEngine(runtime, saver, reg.skills, engineering_service=service)
    try:
        yield uow_factory, engine, service, dispatcher, reg, provider
    finally:
        await pool.close()
        await dispatcher.close()
        await db.close()


def print_state(state: dict) -> None:
    typer.echo(
        json.dumps(
            {
                "phase": state.get("current_phase"),
                "domain_state": state.get("domain_state"),
                "interrupts": [i.value for i in state.get("__interrupt__", [])],
                "error": state.get("error_message"),
            },
            default=str,
        )
    )


@engineering_app.command("start")
def start(
    mission_id: UUID,
    org_id: UUID,
    verify: list[str] = typer.Option(
        ..., "--verify-command", help="Operator-approved command executed inside the target sandbox"
    ),
) -> None:
    async def run():
        async with composition(verify) as (factory, engine, *_):
            async with factory() as uow:
                mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
                print_state(await engine.start_mission(mission_id, org_id, mission.objective, uow=uow))

    asyncio.run(run())


@engineering_app.command("advance")
def advance(mission_id: UUID, org_id: UUID, verify: list[str] = typer.Option(..., "--verify-command")) -> None:
    async def run():
        async with composition(verify) as (factory, engine, *_):
            async with factory() as uow:
                await uow.missions.get_by_id_for_org(mission_id, org_id)
                print_state(await engine.resume_approval(mission_id, {"org_id": str(org_id)}, uow=uow))

    asyncio.run(run())


@engineering_app.command("decide")
def decide(
    mission_id: UUID,
    org_id: UUID,
    user_id: UUID,
    digest: str,
    decision: str = typer.Option("APPROVED", "--decision"),
    verify: list[str] = typer.Option(..., "--verify-command"),
) -> None:
    if decision not in {"APPROVED", "REJECTED", "CANCELLED"}:
        raise typer.BadParameter("Decision must be APPROVED, REJECTED or CANCELLED")

    async def run():
        async with composition(verify) as (factory, engine, *_):
            async with factory() as uow:
                await uow.missions.get_by_id_for_org(mission_id, org_id)
                print_state(
                    await engine.resume_approval(
                        mission_id,
                        {"org_id": str(org_id), "user_id": str(user_id), "action_digest": digest, "decision": decision},
                        uow=uow,
                    )
                )

    asyncio.run(run())


@engineering_app.command("worker")
def worker(
    org_id: UUID,
    project_id: UUID,
    repository: Path,
    worker_id: str = "engineering-worker",
    image: str = "syntra-sandbox:latest",
    once: bool = False,
) -> None:
    async def run():
        async with composition(["python -m pytest -q"]) as (factory, _, service, dispatcher, reg, provider):
            adapter = EngineeringSandboxWorker(
                repository,
                registry=reg,
                provider_model=provider,
                uow_factory=factory,
                authorized_org_id=org_id,
                authorized_project_id=project_id,
                worker_id=worker_id,
                config=ContainerConfig(image=image),
            )
            consumer = SandboxWorkerConsumer(service.scheduler, dispatcher, adapter, worker_id)
            relay = OutboxRelay(factory, dispatcher)
            reconciler = SchedulerReconciler(factory)
            while True:
                # Recovery does not depend on a Redis notification surviving.
                # Only this explicitly authorized organization/project is swept.
                async with factory() as uow:
                    missions = list(
                        (
                            await uow.session.execute(
                                select(MissionModel.id).where(
                                    MissionModel.org_id == org_id,
                                    MissionModel.project_id == project_id,
                                    MissionModel.state.in_(
                                        [MissionState.READY, MissionState.RUNNING, MissionState.CANCELLED]
                                    ),
                                )
                            )
                        ).scalars()
                    )
                for mission_id in missions:
                    await reconciler.reconcile_mission(mission_id, org_id)
                    await service.scheduler.schedule_ready_tasks(mission_id, org_id)
                await relay.relay_batch()
                for mid, dispatch in await dispatcher.reclaim_abandoned_messages(worker_id):
                    await consumer.process(mid, dispatch)
                processed = await consumer.run_once()
                if once:
                    typer.echo(json.dumps({"processed": processed, "execution_mode": "GEMINI_DOCKER"}))
                    return

    asyncio.run(run())
