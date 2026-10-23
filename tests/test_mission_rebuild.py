"""Test Rebuild Mission Endpoint."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from syntra.api.app import app
from syntra.api.auth.dependencies import get_settings, get_uow, require_developer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.core.config import AutonomyMode, Settings
from syntra.domain.entities import MembershipRole
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

TEST_SECRET = "syntra-rebuild-test-secret-key-32b!"
TEST_ISSUER = "https://auth.syntra.io"
TEST_AUDIENCE = "syntra-api"


def make_rebuild_settings() -> Settings:
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
async def test_rebuild_mission_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "")

    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    settings = make_rebuild_settings()

    async def override_get_uow():
        async with SqlAlchemyUnitOfWork(session_factory) as uow_instance:
            yield uow_instance

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_uow] = override_get_uow

    # Redirect generated apps output to tmp_path
    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend" / "public" / "generated_apps").mkdir(parents=True, exist_ok=True)

    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mission_id = uuid.uuid4()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Engineering Org", "eng-org")
        await uow.projects.create(project_id, org_id, "Crypto Tracker", "crypto-tracker")
        m = await uow.missions.create(
            mission_id=mission_id,
            org_id=org_id,
            project_id=project_id,
            objective="Build an interactive cryptocurrency portfolio tracker with Bitcoin and Ethereum",
            autonomy_mode=AutonomyMode.SEMI_AUTONOMOUS.value,
        )
        await uow.budgets.create(
            org_id=org_id,
            mission_id=mission_id,
            max_tokens=250000,
            max_cost_usd="5.0000",
        )
        plan = await uow.tasks.create_plan(uuid.uuid4(), mission_id)
        await uow.tasks.create_task(uuid.uuid4(), plan.id, m.id, org_id, "TASK-001-PRD", "PRD", "Objective", "product_manager", 1)
        await uow.commit()

    # Pre-populate a fake old cache to verify purge
    mission_dir = tmp_path / "frontend" / "public" / "generated_apps" / str(mission_id)
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "old_stale_file.txt").write_text("stale data", encoding="utf-8")

    test_user = AuthenticatedUser(
        user_id=uuid.uuid4(),
        email="dev@syntra.io",
        org_id=org_id,
        role=MembershipRole.DEVELOPER,
    )
    app.dependency_overrides[require_developer_or_above] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/v1/missions/{mission_id}/rebuild")
        if resp.status_code != 200:
            raise AssertionError(f"Status: {resp.status_code}, Body: {resp.text}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(mission_id)
        assert data["state"] == "RUNNING"

    # Verify stale file is purged and fresh index.html + backend files are synthesized
    assert not (mission_dir / "old_stale_file.txt").exists()
    assert (mission_dir / "index.html").exists()
    html_content = (mission_dir / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "Crypto Assets" in html_content

    backend_dir = mission_dir / "backend"
    assert backend_dir.exists()
    assert (backend_dir / "models.py").exists()
    models_content = (backend_dir / "models.py").read_text(encoding="utf-8")
    assert "CryptoAssetModel" in models_content

    app.dependency_overrides.clear()
    await db.close()
