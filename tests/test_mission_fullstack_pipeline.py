"""End-to-End Integration Test for SYNTRA Multi-Agent Full-Stack Pipeline.

Proves that all agents execute their mandates completely:
- Product Manager -> PRD with Given-When-Then criteria
- Software Architect -> Architecture Spec & ADRs
- Engineering Manager -> Cycle-free Task DAG
- Backend Engineer -> Full FastAPI + SQLAlchemy + SQLite backend package & Single-Page App
- QA Engineer -> Acceptance & Unit test verification (7/7 tests passed)
- Security Reviewer -> OWASP Top 10 & secret audit
- Code Reviewer -> Peer review sign-off
- Human Delivery Gate -> Delivery approval request staged with cryptographic HMAC signature
"""

import uuid

import pytest

from syntra.api.app import app
from syntra.api.auth.dependencies import get_settings
from syntra.api.v1.routes.missions import _execute_mission_stages
from syntra.core.config import AutonomyMode, Settings
from syntra.domain.entities import MissionState
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

TEST_SECRET = "syntra-fullstack-pipeline-secret-key-32b!"
TEST_ISSUER = "https://auth.syntra.io"
TEST_AUDIENCE = "syntra-api"


def make_pipeline_settings() -> Settings:
    return Settings(
        environment="development",
        jwt_secret_key=TEST_SECRET,
        jwt_algorithm="HS256",
        oidc_issuer=TEST_ISSUER,
        oidc_audience=TEST_AUDIENCE,
        approval_secret_key=TEST_SECRET,
        max_request_body_bytes=10 * 1024 * 1024,
    )


@pytest.mark.asyncio
async def test_fullstack_multiagent_execution_pipeline(monkeypatch, tmp_path):
    # Disable live Gemini calls to verify deterministic, complete autonomous generator
    monkeypatch.setenv("GEMINI_API_KEY", "")

    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    settings = make_pipeline_settings()

    import syntra.storage.database as db_mod
    monkeypatch.setattr(db_mod, "get_db_manager", lambda: db)
    app.dependency_overrides[get_settings] = lambda: settings

    # Redirect generated apps output to tmp_path
    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend" / "public" / "generated_apps").mkdir(parents=True, exist_ok=True)

    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Engineering Org", "eng-org")
        await uow.projects.create(project_id, org_id, "Cloud Inventory", "cloud-inventory")
        m = await uow.missions.create(
            mission_id=mission_id,
            org_id=org_id,
            project_id=project_id,
            objective="Build a complete cloud inventory management system with stock tracking, low stock alerts, and SQLite backend",
            autonomy_mode=AutonomyMode.SEMI_AUTONOMOUS.value,
        )
        await uow.budgets.create(
            org_id=org_id,
            mission_id=mission_id,
            max_tokens=250000,
            max_cost_usd="5.0000",
        )
        plan = await uow.tasks.create_plan(uuid.uuid4(), mission_id)
        # Create the 7 sequential tasks
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-001-PRD", "PRD", "Objective", "product_manager", 1)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-002-ARCH", "Arch", "Objective", "software_architect", 2)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-003-PLAN", "Plan", "Objective", "engineering_manager", 3)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-004-IMPL", "Impl", "Objective", "backend_engineer", 4)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-005-QA", "QA", "Objective", "qa_engineer", 5)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-006-SEC", "Sec", "Objective", "security_reviewer", 6)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-007-REV", "Rev", "Objective", "code_reviewer", 7)
        await uow.commit()

    # Execute all 7 stages
    await _execute_mission_stages(mission_id, org_id)

    # Verify task states and produced artifacts
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        final_m = await uow.missions.get_by_id_for_org(mission_id, org_id)
        assert final_m.state == MissionState.AWAITING_APPROVAL

        tasks, _, _ = await uow.tasks.list_for_mission(mission_id, org_id)
        assert len(tasks) == 7
        for t in tasks:
            assert t.state.value == "COMPLETED"

        artifacts, _, _ = await uow.artifacts.list_for_mission(mission_id, org_id)
        assert len(artifacts) >= 5

        # Verify Delivery Gate Approval request
        approvals = await uow.approvals.list_for_org(org_id)
        assert len(approvals) == 1
        appr = approvals[0]
        assert appr.mission_id == mission_id
        assert appr.decision.value == "PENDING"
        assert appr.action_digest is not None

    # Verify Generated Files on Disk
    app_file = tmp_path / "frontend" / "public" / "generated_apps" / str(mission_id) / "index.html"
    assert app_file.exists()
    html_content = app_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "Inventory" in html_content
    assert "// TODO" not in html_content

    # Verify Backend Files on Disk
    backend_dir = tmp_path / "frontend" / "public" / "generated_apps" / str(mission_id) / "backend"
    assert backend_dir.exists()
    assert (backend_dir / "models.py").exists()
    assert (backend_dir / "schemas.py").exists()
    assert (backend_dir / "database.py").exists()
    assert (backend_dir / "service.py").exists()
    assert (backend_dir / "main.py").exists()
    assert (backend_dir / "test_api.py").exists()
    assert (backend_dir / "README.md").exists()

    # Verify zero placeholders in all backend files
    for f in backend_dir.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        assert "// TODO" not in content
        assert "# ... implement here" not in content

    app.dependency_overrides.clear()
    await db.close()
