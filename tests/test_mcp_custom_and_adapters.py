"""Tests for Custom SYNTRA MCP Server operations and Scoped Workspace Adapters."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.domain.entities import ArtifactType, TaskState, VerificationVerdict
from syntra.mcp.adapters.tools import (
    ScopedFilesystemTools,
    create_workspace_mcp_server,
    resolve_safe_path,
)
from syntra.mcp.policy import ScopeViolationError
from syntra.mcp.syntra_server import create_syntra_mcp_server
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager


@pytest.fixture
async def uow_db():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    yield session_factory
    await db.close()


@pytest.mark.asyncio
async def test_custom_syntra_mcp_server_operations(uow_db):
    """Test all 8 backed domain operations on the official SYNTRA internal MCP server."""
    server = create_syntra_mcp_server(uow_db)

    org_id = uuid4()
    project_id = uuid4()
    mission_id = uuid4()
    task_id = uuid4()

    # 1. Seed initial project and mission in DB
    async with SqlAlchemyUnitOfWork(uow_db) as uow:
        await uow.organizations.create(org_id, "Syntra Org", "syntra-org")
        proj = await uow.projects.create(project_id, org_id, "Syntra Core", "syntra-core", "Core platform")
        await uow.missions.create(mission_id, org_id, proj.id, "Build Core Architecture")
        plan = await uow.tasks.create_plan(uuid4(), mission_id, version=1)
        await uow.tasks.create_task(
            task_id=task_id,
            task_plan_id=plan.id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-01",
            title="Implement MCP Gateway",
            description="Build Phase 4 MCP subsystem",
            assigned_role="backend_engineer",
        )
        art = await uow.artifacts.create(mission_id, "Patch Diff", ArtifactType.UNIFIED_DIFF)
        ver = await uow.artifacts.add_version(art.id, 1, "/patches/diff.patch", "hashdiff123", 512)
        await uow.verifications.create_run(
            task_id=task_id,
            artifact_version_id=ver.id,
            verdict=VerificationVerdict.PASS,
            tests_passed=14,
            tests_failed=0,
        )
        await uow.commit()

    # Test 1: syntra.get_project_context
    ctx_res = await server.call_tool(
        "syntra.get_project_context", {"project_id": str(project_id), "org_id": str(org_id)}
    )
    assert not ctx_res.is_error
    ctx_data = json.loads(ctx_res.content[0].text)
    assert ctx_data["name"] == "Syntra Core"
    assert ctx_data["slug"] == "syntra-core"

    # Test 2: syntra.list_tasks
    list_res = await server.call_tool("syntra.list_tasks", {"mission_id": str(mission_id), "org_id": str(org_id)})
    assert not list_res.is_error
    tasks_data = json.loads(list_res.content[0].text)
    assert len(tasks_data["tasks"]) == 1
    assert tasks_data["tasks"][0]["identifier"] == "TASK-01"

    # Test 3: syntra.get_task
    task_res = await server.call_tool("syntra.get_task", {"task_id": str(task_id), "org_id": str(org_id)})
    assert not task_res.is_error
    task_data = json.loads(task_res.content[0].text)
    assert task_data["title"] == "Implement MCP Gateway"

    # Test 4: syntra.submit_artifact
    submit_res = await server.call_tool(
        "syntra.submit_artifact",
        {
            "mission_id": str(mission_id),
            "name": "Architecture Spec",
            "artifact_type": "ARCHITECTURE_SPEC",
            "storage_path": "/artifacts/arch.md",
            "content_hash": "hash123456",
            "size_bytes": 4096,
        },
    )
    assert not submit_res.is_error
    sub_data = json.loads(submit_res.content[0].text)
    artifact_id = sub_data["artifact_id"]
    assert sub_data["status"] == "STORED"

    # Test 5: syntra.get_artifact
    get_art_res = await server.call_tool("syntra.get_artifact", {"artifact_id": artifact_id})
    assert not get_art_res.is_error
    art_data = json.loads(get_art_res.content[0].text)
    assert art_data["name"] == "Architecture Spec"
    assert art_data["sha256_checksum"] == "hash123456"

    # Test 6: syntra.request_review
    rev_res = await server.call_tool("syntra.request_review", {"task_id": str(task_id), "notes": "Ready for QA"})
    assert not rev_res.is_error
    rev_data = json.loads(rev_res.content[0].text)
    assert rev_data["state"] == TaskState.REVIEW.value

    # Test 7: syntra.report_blocker
    block_res = await server.call_tool("syntra.report_blocker", {"task_id": str(task_id), "reason": "Missing secret"})
    assert not block_res.is_error
    block_data = json.loads(block_res.content[0].text)
    assert block_data["state"] == TaskState.BLOCKED.value

    # Test 8: syntra.get_verification_result
    ver_res = await server.call_tool("syntra.get_verification_result", {"task_id": str(task_id)})
    assert not ver_res.is_error
    ver_data = json.loads(ver_res.content[0].text)
    assert ver_data["verdict"] == "PASS"
    assert ver_data["tests_passed"] == 14


@pytest.mark.asyncio
async def test_scoped_workspace_tool_adapters(tmp_path: Path):
    """Test scoped filesystem and git adapters and path confinement rules."""
    ws_root = tmp_path / "sandbox"
    ws_root.mkdir()

    # Create dummy files
    (ws_root / "src").mkdir()
    (ws_root / "src" / "main.py").write_text("print('Hello SYNTRA')", encoding="utf-8")
    (ws_root / "README.md").write_text("# Test Workspace", encoding="utf-8")

    server = create_workspace_mcp_server(workspace_root=ws_root)

    # 1. filesystem.read_scoped
    read_res = await server.call_tool("filesystem.read_scoped", {"relative_path": "src/main.py"})
    assert not read_res.is_error
    assert read_res.content[0].text == "print('Hello SYNTRA')"

    # 2. filesystem.list_scoped
    list_res = await server.call_tool("filesystem.list_scoped", {"relative_path": "."})
    assert not list_res.is_error
    entries = json.loads(list_res.content[0].text)
    names = [e["name"] for e in entries]
    assert "src" in names
    assert "README.md" in names

    # 3. filesystem.search_scoped
    search_res = await server.call_tool("filesystem.search_scoped", {"pattern": "*.py"})
    assert not search_res.is_error
    matches = json.loads(search_res.content[0].text)
    assert "src/main.py" in matches

    # 4. Path traversal prevention check: attempting to read outside sandbox
    with pytest.raises(ScopeViolationError):
        resolve_safe_path(ws_root, "../../etc/passwd")

    with pytest.raises(ScopeViolationError):
        ScopedFilesystemTools.read_scoped(ws_root, "../outside.txt")


@pytest.mark.asyncio
async def test_workspace_artifact_and_git_tools(uow_db, tmp_path: Path):
    """Test artifact.read_metadata and git tools with workspace server."""
    ws_root = tmp_path / "sandbox_git"
    ws_root.mkdir()

    # Seed an artifact
    mission_id = uuid4()
    async with SqlAlchemyUnitOfWork(uow_db) as uow:
        art = await uow.artifacts.create(mission_id, "DesignDoc", ArtifactType.ARCHITECTURE_SPEC)
        await uow.artifacts.add_version(art.id, 1, "/docs/spec.md", "spechash789", 1024)
        await uow.commit()
        artifact_id = art.id

    server = create_workspace_mcp_server(workspace_root=ws_root, session_factory=uow_db)

    # Test artifact.read_metadata
    meta_res = await server.call_tool("artifact.read_metadata", {"artifact_id": str(artifact_id)})
    assert not meta_res.is_error
    meta = json.loads(meta_res.content[0].text)
    assert meta["title"] == "DesignDoc"
    assert meta["version"] == 1
    assert meta["sha256_checksum"] == "spechash789"

    # Test git.status in non-git directory returns error gracefully
    git_res = await server.call_tool("git.status", {})
    assert not git_res.is_error
    assert "Git status failed" in git_res.content[0].text or "fatal" in git_res.content[0].text
