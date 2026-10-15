"""Functional and integration tests for SYNTRA Control Plane API v1 endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import jwt
import pytest

from syntra.api.app import app
from syntra.api.auth.dependencies import get_settings, get_uow
from syntra.core.config import Settings
from syntra.domain.entities import (
    ApprovalActionType,
    ArtifactType,
    MembershipRole,
    compute_action_digest,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

TEST_SECRET = "syntra-v1-api-test-secret-key-32bytes!"
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
async def v1_client():
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
        await uow.organizations.create(org_id, "Primary Org", "primary-org")
        await uow.commit()

    token = generate_jwt(user_id=user_id, org_id=org_id, role=MembershipRole.DEVELOPER)
    admin_token = generate_jwt(user_id=user_id, org_id=org_id, role=MembershipRole.ADMIN)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "org_id": org_id,
            "user_id": user_id,
            "token": token,
            "admin_token": admin_token,
        }

    app.dependency_overrides.clear()
    await db.close()


@pytest.mark.asyncio
async def test_openapi_schema_generation():
    """Verify OpenAPI 3.x schema generates without errors and documents v1 routes."""
    schema = app.openapi()
    assert schema["info"]["title"] == "SYNTRA API"
    assert "/v1/projects" in schema["paths"]
    assert "/v1/missions" in schema["paths"]
    assert "/v1/approvals/{approval_id}/decision" in schema["paths"]
    assert "/v1/tasks/{task_id}" in schema["paths"]


@pytest.mark.asyncio
async def test_project_lifecycle_v1(v1_client):
    """Test full project creation, retrieval, and listing."""
    client: httpx.AsyncClient = v1_client["client"]
    token = v1_client["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create project
    create_resp = await client.post(
        "/v1/projects",
        json={"name": "Syntra Core", "description": "Autonomous multi-agent platform"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    proj_data = create_resp.json()
    assert proj_data["name"] == "Syntra Core"
    assert proj_data["slug"] == "syntra-core"
    assert proj_data["default_branch"] == "main"
    project_id = proj_data["id"]

    # 2. Retrieve project
    get_resp = await client.get(f"/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id

    # 3. List projects
    list_resp = await client.get("/v1/projects", headers=headers)
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == project_id for p in projects)


@pytest.mark.asyncio
async def test_mission_and_planning_lifecycle_v1(v1_client):
    """Test mission creation, planning capability stub, and sub-resource queries."""
    client: httpx.AsyncClient = v1_client["client"]
    token = v1_client["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup project
    proj_resp = await client.post("/v1/projects", json={"name": "Mission Host Project"}, headers=headers)
    project_id = proj_resp.json()["id"]

    # 1. Create mission
    mission_resp = await client.post(
        "/v1/missions",
        json={
            "project_id": project_id,
            "title": "Build Auth",
            "objective": "Implement OIDC authentication and authorization",
            "budget_max_tokens": 500_000,
            "budget_max_cost_usd": "25.00",
        },
        headers=headers,
    )
    assert mission_resp.status_code == 201
    mission_data = mission_resp.json()
    mission_id = mission_data["id"]
    assert mission_data["state"] == "DRAFT"
    assert mission_data["version"] == 1

    # 2. Get mission
    get_mission_resp = await client.get(f"/v1/missions/{mission_id}", headers=headers)
    assert get_mission_resp.status_code == 200
    assert get_mission_resp.json()["id"] == mission_id

    # 3. Post plan (Phase 3 capability stub returns 501 typed response)
    plan_resp = await client.post(f"/v1/missions/{mission_id}/plan", headers=headers)
    assert plan_resp.status_code == 501
    cap_data = plan_resp.json()
    assert cap_data["status"] == "CAPABILITY_SCHEDULED"
    assert cap_data["phase"] == "PHASE_3_API_CONTROL_PLANE"
    assert cap_data["target_phase"] == "PHASE_4_AGENT_EXECUTION_FABRIC"

    # 4. Seed tasks and plan in persistence to test GET /v1/missions/{id}/tasks and GET /v1/tasks/{id}
    session_factory = v1_client["session_factory"]
    plan_id = uuid.uuid4()
    task_1_id = uuid.uuid4()
    task_2_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.tasks.create_plan(plan_id, uuid.UUID(mission_id), version=1)
        await uow.tasks.create_task(
            task_id=task_1_id,
            task_plan_id=plan_id,
            mission_id=uuid.UUID(mission_id),
            org_id=v1_client["org_id"],
            identifier="TASK-1",
            title="Setup database schema",
            description="Define PostgreSQL schema",
            assigned_role="backend_engineer",
        )
        await uow.tasks.create_task(
            task_id=task_2_id,
            task_plan_id=plan_id,
            mission_id=uuid.UUID(mission_id),
            org_id=v1_client["org_id"],
            identifier="TASK-2",
            title="Implement endpoints",
            description="Write FastAPI routes",
            assigned_role="backend_engineer",
        )
        await uow.tasks.add_dependency(task_id=task_2_id, depends_on_task_id=task_1_id)
        # Seed an artifact
        art = await uow.artifacts.create(uuid.UUID(mission_id), "PRD Document", type=ArtifactType.PRD)
        await uow.artifacts.add_version(art.id, 1, "/artifacts/prd.md", "hash-1234", 1024)
        # Seed an event
        await uow.outbox.record_event(
            v1_client["org_id"], "test.event", {"info": "test"}, mission_id=uuid.UUID(mission_id)
        )
        # Seed usage
        await uow.budgets.add_usage_record(
            v1_client["org_id"],
            uuid.UUID(mission_id),
            model_name="gemini-2.5-flash",
            prompt_tokens=1000,
            completion_tokens=500,
            cost_usd=Decimal("0.0015"),
        )
        await uow.commit()

    # 5. List mission tasks
    tasks_resp = await client.get(f"/v1/missions/{mission_id}/tasks", headers=headers)
    assert tasks_resp.status_code == 200
    task_page = tasks_resp.json()
    assert len(task_page["items"]) == 2
    task_2 = next(t for t in task_page["items"] if t["id"] == str(task_2_id))
    assert str(task_1_id) in task_2["dependencies"]

    # 6. Retrieve single task
    task_resp = await client.get(f"/v1/tasks/{task_1_id}", headers=headers)
    assert task_resp.status_code == 200
    assert task_resp.json()["title"] == "Setup database schema"

    # 7. List mission artifacts
    artifacts_resp = await client.get(f"/v1/missions/{mission_id}/artifacts", headers=headers)
    assert artifacts_resp.status_code == 200
    assert len(artifacts_resp.json()["items"]) == 1
    assert artifacts_resp.json()["items"][0]["artifact_type"] == "PRD"

    # 8. List mission events
    events_resp = await client.get(f"/v1/missions/{mission_id}/events", headers=headers)
    assert events_resp.status_code == 200
    assert len(events_resp.json()["items"]) >= 1

    # 9. Get mission usage financial ledger
    usage_resp = await client.get(f"/v1/missions/{mission_id}/usage", headers=headers)
    assert usage_resp.status_code == 200
    usage_data = usage_resp.json()
    assert usage_data["total_tokens"] >= 1500
    assert len(usage_data["records"]) == 1


@pytest.mark.asyncio
async def test_validation_error_rfc7807(v1_client):
    """Verify that Pydantic schema validation failures return RFC 7807 problem details with invalid_params."""
    client: httpx.AsyncClient = v1_client["client"]
    token = v1_client["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Empty name should fail min_length=1
    resp = await client.post("/v1/projects", json={"name": ""}, headers=headers)
    assert resp.status_code == 422
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 422
    assert data["title"] == "Validation Error"
    assert "invalid_params" in data
    assert len(data["invalid_params"]) > 0


@pytest.mark.asyncio
async def test_approval_decision_workflow_v1(v1_client):
    """Test human approval gate decision resolution happy path."""
    client: httpx.AsyncClient = v1_client["client"]
    admin_token = v1_client["admin_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Setup project and mission
    proj_resp = await client.post("/v1/projects", json={"name": "Approval Flow Project"}, headers=headers)
    project_id = proj_resp.json()["id"]
    mission_resp = await client.post(
        "/v1/missions",
        json={"project_id": project_id, "title": "Approval Mission", "objective": "Deploy gate"},
        headers=headers,
    )
    mission_id = mission_resp.json()["id"]

    # Seed approval
    approval_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    async with SqlAlchemyUnitOfWork(v1_client["session_factory"]) as uow:
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=v1_client["org_id"],
            mission_id=uuid.UUID(mission_id),
            action_type=ApprovalActionType.DEPLOYMENT.value,
            target_resource="prod-cluster",
            mission_version=1,
            expires_at=expires_at,
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    digest = compute_action_digest(
        secret=TEST_SECRET,
        mission_id=uuid.UUID(mission_id),
        action_type=ApprovalActionType.DEPLOYMENT.value,
        target_resource="prod-cluster",
        mission_version=1,
        expires_at=expires_at,
    )

    # Approve checkpoint
    dec_resp = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": digest, "reason": "Authorized by security lead"},
        headers=headers,
    )
    assert dec_resp.status_code == 200
    res_data = dec_resp.json()
    assert res_data["decision"] == "APPROVED"
    assert res_data["reason"] == "Authorized by security lead"
    assert res_data["resolved_at"] is not None
