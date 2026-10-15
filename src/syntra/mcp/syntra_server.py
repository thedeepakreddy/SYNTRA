"""Internal SYNTRA MCP Server providing authoritative platform operations."""

import json
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from syntra.domain.entities import ArtifactType, TaskState
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork


def create_syntra_mcp_server(session_factory: async_sessionmaker[AsyncSession]) -> MCPServer:
    """Construct and configure the official SYNTRA internal MCP Server."""
    server = MCPServer("syntra", version="0.1.0")

    @server.tool(
        name="syntra.get_project_context",
        description="Retrieve project context, repositories, and active missions by project ID.",
    )
    async def get_project_context(project_id: str, org_id: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            proj = await uow.projects.get_by_id_for_org(UUID(project_id), UUID(org_id))
            return json.dumps(
                {
                    "project_id": str(proj.id),
                    "org_id": str(proj.org_id),
                    "name": proj.name,
                    "slug": proj.slug,
                    "description": proj.description,
                    "created_at": proj.created_at.isoformat(),
                },
                indent=2,
            )

    @server.tool(
        name="syntra.list_tasks",
        description="List all engineering tasks bound to a mission.",
    )
    async def list_tasks(mission_id: str, org_id: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            tasks, _, _ = await uow.tasks.list_for_mission(UUID(mission_id), UUID(org_id), limit=100)
            items = []
            for t in tasks:
                deps = await uow.tasks.get_dependencies_for_task(t.id)
                items.append(
                    {
                        "task_id": str(t.id),
                        "identifier": t.identifier,
                        "title": t.title,
                        "description": t.description,
                        "state": t.state.value if hasattr(t.state, "value") else str(t.state),
                        "assigned_role": t.assigned_role,
                        "dependencies": [str(d) for d in deps],
                    }
                )
            return json.dumps({"mission_id": mission_id, "tasks": items}, indent=2)

    @server.tool(
        name="syntra.get_task",
        description="Retrieve complete task details, description, dependencies, and state by task ID.",
    )
    async def get_task(task_id: str, org_id: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            task = await uow.tasks.get_by_id_for_org(UUID(task_id), UUID(org_id))
            deps = await uow.tasks.get_dependencies_for_task(task.id)
            return json.dumps(
                {
                    "task_id": str(task.id),
                    "mission_id": str(task.mission_id),
                    "org_id": str(task.org_id),
                    "identifier": task.identifier,
                    "title": task.title,
                    "description": task.description,
                    "state": task.state.value if hasattr(task.state, "value") else str(task.state),
                    "assigned_role": task.assigned_role,
                    "dependencies": [str(d) for d in deps],
                    "created_at": task.created_at.isoformat(),
                },
                indent=2,
            )

    @server.tool(
        name="syntra.get_artifact",
        description="Retrieve artifact metadata, storage path, and cryptographic hash by artifact ID.",
    )
    async def get_artifact(artifact_id: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            res = await uow.artifacts.get_by_id(UUID(artifact_id))
            if not res:
                return json.dumps({"error": f"Artifact {artifact_id} not found."})
            art, ver = res
            return json.dumps(
                {
                    "artifact_id": str(art.id),
                    "mission_id": str(art.mission_id),
                    "name": art.title,
                    "artifact_type": art.type.value if hasattr(art.type, "value") else str(art.type),
                    "current_version": art.current_version,
                    "storage_path": ver.storage_path if ver else None,
                    "sha256_checksum": ver.sha256_checksum if ver else None,
                    "size_bytes": ver.size_bytes if ver else 0,
                },
                indent=2,
            )

    @server.tool(
        name="syntra.submit_artifact",
        description="Submit a verified project artifact (e.g. PRD, Architecture Spec, Diff) to persistence.",
    )
    async def submit_artifact(
        mission_id: str,
        name: str,
        artifact_type: str,
        storage_path: str,
        content_hash: str,
        size_bytes: int,
    ) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            type_enum = ArtifactType(artifact_type)
            art = await uow.artifacts.create(
                mission_id=UUID(mission_id),
                title=name,
                type=type_enum,
            )
            ver = await uow.artifacts.add_version(
                artifact_id=art.id,
                version=1,
                storage_path=storage_path,
                sha256_checksum=content_hash,
                size_bytes=size_bytes,
            )
            await uow.commit()
            return json.dumps(
                {
                    "artifact_id": str(art.id),
                    "version": ver.version,
                    "name": art.title,
                    "status": "STORED",
                },
                indent=2,
            )

    @server.tool(
        name="syntra.request_review",
        description="Transition a task to REVIEW state and notify human / peer reviewer agents.",
    )
    async def request_review(task_id: str, notes: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            task = await uow.tasks.update_status(UUID(task_id), TaskState.REVIEW, reason=notes)
            uow.publish_event(
                event_type="task.review_requested",
                payload={
                    "task_id": str(task.id),
                    "mission_id": str(task.mission_id),
                    "notes": notes,
                },
            )
            await uow.commit()
            return json.dumps(
                {
                    "task_id": str(task.id),
                    "state": TaskState.REVIEW.value,
                    "notes": notes,
                },
                indent=2,
            )

    @server.tool(
        name="syntra.report_blocker",
        description="Mark a task as BLOCKED, recording the blocker rationale in application state.",
    )
    async def report_blocker(task_id: str, reason: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            task = await uow.tasks.update_status(UUID(task_id), TaskState.BLOCKED, reason=reason)
            uow.publish_event(
                event_type="task.blocked",
                payload={
                    "task_id": str(task.id),
                    "mission_id": str(task.mission_id),
                    "reason": reason,
                },
            )
            await uow.commit()
            return json.dumps(
                {
                    "task_id": str(task.id),
                    "state": TaskState.BLOCKED.value,
                    "reason": reason,
                },
                indent=2,
            )

    @server.tool(
        name="syntra.get_verification_result",
        description="Fetch the latest automated test and verification results for a task.",
    )
    async def get_verification_result(task_id: str) -> str:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            run = await uow.verifications.get_latest_for_task(UUID(task_id))
            if not run:
                return json.dumps({"task_id": task_id, "verdict": "NO_RUNS_RECORDED"})
            return json.dumps(
                {
                    "task_id": str(run.task_id),
                    "verdict": run.verdict.value if hasattr(run.verdict, "value") else str(run.verdict),
                    "tests_passed": run.tests_passed,
                    "tests_failed": run.tests_failed,
                    "coverage_percentage": str(run.coverage_percentage) if run.coverage_percentage else None,
                    "verified_at": run.verified_at.isoformat(),
                },
                indent=2,
            )

    return server
