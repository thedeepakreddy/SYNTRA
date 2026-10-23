"""Tests for Phase 14 Control Center API endpoints and wiring."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest

from syntra.api.app import app
from syntra.api.auth.dependencies import get_settings, get_uow
from syntra.core.config import Settings
from syntra.domain.entities import (
    ApprovalActionType,
    MembershipRole,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

TEST_SECRET = "syntra-phase14-test-secret-key-32b!"
TEST_ISSUER = "https://auth.syntra.io"
TEST_AUDIENCE = "syntra-api"


def make_test_settings() -> Settings:
    return Settings(
        environment="development",
        jwt_secret_key=TEST_SECRET,
        jwt_algorithm="HS256",
        oidc_issuer=TEST_ISSUER,
        oidc_audience=TEST_AUDIENCE,
        approval_secret_key=TEST_SECRET,
        max_request_body_bytes=10 * 1024 * 1024,
    )


def generate_jwt(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: MembershipRole = MembershipRole.DEVELOPER,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": f"{user_id}@syntra.local",
        "org_id": str(org_id),
        "role": role.value,
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
async def p14_client():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    settings = make_test_settings()

    async def override_get_uow():
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            yield uow

    app.dependency_overrides[get_uow] = override_get_uow
    app.dependency_overrides[get_settings] = lambda: settings

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Phase 14 Org", "p14-org")
        await uow.commit()

    dev_token = generate_jwt(user_id=user_id, org_id=org_id, role=MembershipRole.DEVELOPER)
    admin_token = generate_jwt(user_id=user_id, org_id=org_id, role=MembershipRole.ADMIN)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "org_id": org_id,
            "user_id": user_id,
            "dev_token": dev_token,
            "admin_token": admin_token,
        }

    app.dependency_overrides.clear()
    await db.close()


@pytest.mark.asyncio
async def test_system_overview_endpoint(p14_client):
    """Verify GET /v1/system/overview returns consolidated dashboard metrics."""
    client = p14_client["client"]
    token = p14_client["dev_token"]

    resp = await client.get("/v1/system/overview", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "projects_count" in data
    assert "missions_count" in data
    assert "pending_approvals_count" in data
    assert data["active_agents_count"] == 10
    assert data["system_health"] == "HEALTHY"


@pytest.mark.asyncio
async def test_agents_list_endpoint(p14_client):
    """Verify GET /v1/agents returns all 10 canonical personas from AGENTS.md."""
    client = p14_client["client"]
    token = p14_client["dev_token"]

    resp = await client.get("/v1/agents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    personas = resp.json()
    assert len(personas) == 10
    roles = {p["role"] for p in personas}
    expected_roles = {
        "product_manager",
        "software_architect",
        "engineering_manager",
        "backend_engineer",
        "frontend_engineer",
        "qa_engineer",
        "devops_engineer",
        "security_reviewer",
        "code_reviewer",
        "debugging_specialist",
    }
    assert roles == expected_roles
    for p in personas:
        assert len(p["allowed_tools"]) >= 1
        assert len(p["forbidden_actions"]) >= 1
        assert len(p["primary_inputs"]) >= 1
        assert len(p["authoritative_outputs"]) >= 1


@pytest.mark.asyncio
async def test_models_list_and_routing_endpoints(p14_client):
    """Verify GET /v1/models and GET /v1/models/routing expose model specifications and policies."""
    client = p14_client["client"]
    token = p14_client["dev_token"]

    # 1. Models list
    resp = await client.get("/v1/models", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 1
    model_ids = [m["model_id"] for m in models]
    assert "gemini-2.5-pro" in model_ids or "gemini-2.5-flash" in model_ids

    # 2. Routing policy
    resp_routing = await client.get("/v1/models/routing", headers={"Authorization": f"Bearer {token}"})
    assert resp_routing.status_code == 200
    routing = resp_routing.json()
    assert "role_defaults" in routing
    assert routing["role_defaults"]["product_manager"] == "reasoning"
    assert routing["role_defaults"]["backend_engineer"] == "balanced"


@pytest.mark.asyncio
async def test_models_routing_simulation(p14_client):
    """Verify POST /v1/models/routing/simulate resolves models correctly."""
    client = p14_client["client"]
    token = p14_client["dev_token"]

    # Simulation for product manager (reasoning tier)
    resp = await client.post(
        "/v1/models/routing/simulate",
        headers={"Authorization": f"Bearer {token}"},
        json={"agent_role": "product_manager"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned_tier"] == "reasoning"
    assert "reasoning" in data["rationale"].lower()

    # Simulation with explicit model override
    resp_override = await client.post(
        "/v1/models/routing/simulate",
        headers={"Authorization": f"Bearer {token}"},
        json={"requested_model": "custom-tuned-model"},
    )
    assert resp_override.status_code == 200
    data_override = resp_override.json()
    assert data_override["resolved_model"] == "custom-tuned-model"
    assert data_override["assigned_tier"] == "EXPLICIT"


@pytest.mark.asyncio
async def test_approvals_list_and_get_endpoints(p14_client):
    """Verify GET /v1/approvals lists and retrieves human approval requests."""
    client = p14_client["client"]
    token = p14_client["dev_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]

    # Seed an approval request
    approval_id = uuid.uuid4()
    mission_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "Approval Test Project", "approval-test-project")
        m = await uow.missions.create(mission_id, org_id, p.id, "Approval Mission")
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=m.id,
            action_type=ApprovalActionType.DEPLOYMENT.value,
            target_resource="migrations/0002_add_table.py",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    # 1. List approvals
    resp = await client.get("/v1/approvals", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    approvals = resp.json()
    assert len(approvals) == 1
    assert approvals[0]["id"] == str(approval_id)
    assert approvals[0]["decision"] == "PENDING"

    # 2. Get single approval
    resp_single = await client.get(f"/v1/approvals/{approval_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp_single.status_code == 200
    assert resp_single.json()["target_resource"] == "migrations/0002_add_table.py"


@pytest.mark.asyncio
async def test_missions_list_endpoint(p14_client):
    """Verify GET /v1/missions lists missions for tenant."""
    client = p14_client["client"]
    token = p14_client["dev_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]

    # Seed project and mission
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "Mission Test Project", "mission-test-project")
        await uow.missions.create(uuid.uuid4(), org_id, p.id, "Test Objective 1")
        await uow.missions.create(uuid.uuid4(), org_id, p.id, "Test Objective 2")
        await uow.commit()

    resp = await client.get("/v1/missions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    missions = resp.json()
    assert len(missions) == 2


@pytest.mark.asyncio
async def test_mission_run_endpoint(p14_client):
    """Verify POST /v1/missions/{id}/run transitions state to EXECUTING and creates DAG tasks."""
    client = p14_client["client"]
    token = p14_client["dev_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]

    mission_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "Run Test Project", "run-test-project")
        await uow.missions.create(mission_id, org_id, p.id, "Test Objective for Run")
        await uow.commit()

    resp = await client.post(f"/v1/missions/{mission_id}/run", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "RUNNING"

    # Verify task plan and DAG were generated
    tasks_resp = await client.get(f"/v1/missions/{mission_id}/tasks", headers={"Authorization": f"Bearer {token}"})
    assert tasks_resp.status_code == 200
    tasks_data = tasks_resp.json()
    assert len(tasks_data["items"]) == 7
    roles = [t["assigned_role"] for t in tasks_data["items"]]
    assert "product_manager" in roles
    assert "software_architect" in roles
    assert "backend_engineer" in roles


@pytest.mark.asyncio
async def test_benchmarks_endpoints(p14_client, tmp_path, monkeypatch):
    """Verify GET /v1/benchmarks and GET /v1/benchmarks/{run_id}."""
    import syntra.api.v1.routes.benchmarks as bm_module

    # Point BENCHMARK_RESULTS_DIR to tmp_path
    monkeypatch.setattr(bm_module, "BENCHMARK_RESULTS_DIR", tmp_path)

    # Seed a fake run dir
    run_dir = tmp_path / "bm-test-run-001"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text(
        '{"run_id": "bm-test-run-001", "mode": "mode_a_deterministic_mock", "status": "PASSED", "duration_ms": 1200, "metrics": {"TASK_SUCCESS_RATE": {"value": 1.0}}}',
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text('{"run_id": "bm-test-run-001", "seed": 42}', encoding="utf-8")

    client = p14_client["client"]
    token = p14_client["dev_token"]

    # 1. List
    resp = await client.get("/v1/benchmarks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "bm-test-run-001"

    # 2. Detail
    resp_det = await client.get("/v1/benchmarks/bm-test-run-001", headers={"Authorization": f"Bearer {token}"})
    assert resp_det.status_code == 200
    detail = resp_det.json()
    assert detail["status"] == "PASSED"
    assert detail["manifest"]["seed"] == 42


@pytest.mark.asyncio
async def test_audit_list_endpoint(p14_client):
    """Verify GET /v1/audit returns audit records."""
    from syntra.observability.audit_logger import get_audit_logger

    logger = get_audit_logger()
    logger.log_event("DIFF_GENERATED", mission_id=uuid.uuid4(), payload={"patch_hash": "abc"})

    client = p14_client["client"]
    token = p14_client["dev_token"]

    resp = await client.get("/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "DIFF_GENERATED" for e in events)


@pytest.mark.asyncio
async def test_human_approval_resolution_and_completion(p14_client):
    """Verify POST /v1/approvals/{id}/respond resolves delivery gate and transitions mission to COMPLETED."""
    from datetime import UTC, datetime, timedelta

    from syntra.api.app import app
    from syntra.core.config import get_settings
    from syntra.domain.entities import MissionState

    client = p14_client["client"]
    admin_token = p14_client["admin_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]
    settings = app.dependency_overrides.get(get_settings, get_settings)()

    mission_id = uuid.uuid4()
    approval_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=24)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "Approval Project", "approval-proj")
        m = await uow.missions.create(mission_id, org_id, p.id, "Objective for Delivery Approval")
        m.state = MissionState.AWAITING_APPROVAL
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="DELIVERY_APPROVAL",
            target_resource=f"mission:{mission_id}:delivery",
            mission_version=m.version,
            expires_at=expires_at,
            secret_key=settings.approval_secret_key,
            feedback="Ready for delivery",
        )
        digest = appr.action_digest
        await uow.commit()

    # Submit decision via /respond alias with digest and comment
    resp = await client.post(
        f"/v1/approvals/{approval_id}/respond",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "APPROVED",
            "digest": digest,
            "responder": "lead-architect@syntra.local",
            "comment": "Deliverables and QA assertions independently verified.",
        },
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["decision"] == "APPROVED"
    assert res_data["action_digest"] == digest
    assert res_data["signature_digest"] == digest

    # Verify mission transitioned to COMPLETED
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        m_after = await uow.missions.get_by_id_for_org(mission_id, org_id)
        assert m_after.state == MissionState.COMPLETED


@pytest.mark.asyncio
async def test_mission_artifacts_content_retrieval(p14_client):
    """Verify GET /v1/missions/{id}/artifacts decodes inline base64 content and provides clean filenames."""
    import base64

    from syntra.domain.entities import ArtifactType

    client = p14_client["client"]
    token = p14_client["dev_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]

    mission_id = uuid.uuid4()
    raw_markdown = "# Generated PRD\n\nGiven an industrial calculator when rendered then show holographic HUD."
    b64_content = base64.b64encode(raw_markdown.encode("utf-8")).decode("utf-8")

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "Artifacts Project", "art-proj")
        await uow.missions.create(mission_id, org_id, p.id, "Objective for Artifacts")
        art = await uow.artifacts.create(
            mission_id=mission_id,
            title="Calculator PRD Spec",
            type=ArtifactType.PRD,
        )
        await uow.artifacts.add_version(
            artifact_id=art.id,
            version=1,
            storage_path=f"inline:{b64_content}",
            sha256_checksum="abc",
            size_bytes=len(raw_markdown),
        )
        await uow.commit()

    resp = await client.get(f"/v1/missions/{mission_id}/artifacts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["artifact_type"] == "PRD"
    assert item["content"] == raw_markdown
    assert item["path"] == "Calculator_PRD_Spec.md"


@pytest.mark.asyncio
async def test_mission_app_endpoint(p14_client):
    """Verify GET /v1/missions/{id}/app returns synthesized application HTML and launch URL."""
    import base64

    from syntra.domain.entities import ArtifactType

    client = p14_client["client"]
    token = p14_client["dev_token"]
    session_factory = p14_client["session_factory"]
    org_id = p14_client["org_id"]

    mission_id = uuid.uuid4()
    app_html = "<!DOCTYPE html><html><head><title>Test App</title></head><body><h1>Hello World</h1></body></html>"
    b64_content = base64.b64encode(app_html.encode("utf-8")).decode("utf-8")

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        p = await uow.projects.create(uuid.uuid4(), org_id, "App Project", "app-proj")
        await uow.missions.create(mission_id, org_id, p.id, "Objective for App Serving")
        art = await uow.artifacts.create(
            mission_id=mission_id,
            title="Built Application: Test App",
            type=ArtifactType.UNIFIED_DIFF,
        )
        await uow.artifacts.add_version(
            artifact_id=art.id,
            version=1,
            storage_path=f"inline:{b64_content}",
            sha256_checksum="abc",
            size_bytes=len(app_html),
        )
        await uow.commit()

    resp = await client.get(f"/v1/missions/{mission_id}/app", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mission_id"] == str(mission_id)
    assert "<!DOCTYPE html>" in data["html"]
    assert "url" in data
