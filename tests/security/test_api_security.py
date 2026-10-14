"""Security Verification Test Suite for SYNTRA Phase 3 Control Plane.

Demonstrates rigorous rejection of:
1. Missing credentials
2. Invalid JWT signatures
3. Expired tokens
4. Wrong audience
5. Cross-tenant access attempts (IDOR)
6. Viewer role mutation attempts
7. Unauthorized approvals (RBAC)
8. Expired approvals
9. Changed action digests (tampering)
10. Replayed approvals (single-use invariant)
11. Duplicate idempotency keys with different payloads
12. Oversubscribed budgets
"""

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
    MembershipRole,
    compute_action_digest,
)
from syntra.domain.exceptions import BudgetExceededError
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

TEST_SECRET = "syntra-super-secret-test-key-32bytes-long!"
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
    secret: str = TEST_SECRET,
    issuer: str = TEST_ISSUER,
    audience: str = TEST_AUDIENCE,
    expired: bool = False,
) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    payload = {
        "sub": str(user_id),
        "email": f"{user_id}@syntra.local",
        "org_id": str(org_id),
        "role": role.value,
        "iss": issuer,
        "aud": audience,
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
async def sec_env():
    """Sets up an isolated SQLite in-memory database and wires FastAPI dependency overrides."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    settings = make_test_settings()

    async def override_get_uow():
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            yield uow

    def override_get_settings():
        return settings

    app.dependency_overrides[get_uow] = override_get_uow
    app.dependency_overrides[get_settings] = override_get_settings

    # Pre-seed Organization A and Organization B
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_a_id, "Org Alpha", "org-alpha")
        await uow.organizations.create(org_b_id, "Org Beta", "org-beta")
        await uow.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "settings": settings,
            "org_a_id": org_a_id,
            "org_b_id": org_b_id,
        }

    app.dependency_overrides.clear()
    await db.close()


@pytest.mark.asyncio
async def test_01_missing_credentials(sec_env):
    """1. Missing credentials must be rejected with HTTP 401 and RFC 7807 problem details."""
    client: httpx.AsyncClient = sec_env["client"]
    resp = await client.get("/v1/projects")
    assert resp.status_code == 401
    assert resp.headers["content-type"] == "application/problem+json"
    data = resp.json()
    assert data["status"] == 401
    assert "credentials missing" in data["detail"].lower()


@pytest.mark.asyncio
async def test_02_invalid_jwt_signature(sec_env):
    """2. Invalid JWT signature must be rejected with HTTP 401."""
    client: httpx.AsyncClient = sec_env["client"]
    token = generate_jwt(
        user_id=uuid.uuid4(),
        org_id=sec_env["org_a_id"],
        secret="invalid-forged-secret-key-123456",
    )
    resp = await client.get("/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "signature verification failed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_03_expired_tokens(sec_env):
    """3. Expired tokens must be rejected with HTTP 401."""
    client: httpx.AsyncClient = sec_env["client"]
    token = generate_jwt(
        user_id=uuid.uuid4(),
        org_id=sec_env["org_a_id"],
        expired=True,
    )
    resp = await client.get("/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_04_wrong_audience(sec_env):
    """4. Wrong audience claim must be rejected with HTTP 401."""
    client: httpx.AsyncClient = sec_env["client"]
    token = generate_jwt(
        user_id=uuid.uuid4(),
        org_id=sec_env["org_a_id"],
        audience="unauthorized-foreign-audience",
    )
    resp = await client.get("/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "audience" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_05_cross_tenant_access_idor(sec_env):
    """5. Cross-tenant access attempts must be rejected with HTTP 403 / 404 RFC 7807 problem details."""
    client: httpx.AsyncClient = sec_env["client"]
    token_a = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.DEVELOPER)
    token_b = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_b_id"], role=MembershipRole.DEVELOPER)

    # Org A creates a project
    create_resp = await client.post(
        "/v1/projects",
        json={"name": "Alpha Repo", "default_branch": "main"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_resp.status_code == 201
    project_a_id = create_resp.json()["id"]

    # Org B attempts to read Org A's project
    idor_resp = await client.get(
        f"/v1/projects/{project_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert idor_resp.status_code == 403
    assert idor_resp.headers["content-type"] == "application/problem+json"
    assert "cross-tenant" in idor_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_06_viewer_role_mutation_attempts(sec_env):
    """6. Viewer role cannot mutate resources (POST /v1/projects rejected with HTTP 403)."""
    client: httpx.AsyncClient = sec_env["client"]
    token_viewer = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.VIEWER)

    # Viewer attempts project creation
    resp = await client.post(
        "/v1/projects",
        json={"name": "Forbidden By Viewer"},
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert "does not have sufficient permissions" in data["detail"].lower()


@pytest.mark.asyncio
async def test_07_unauthorized_approvals(sec_env):
    """7. Unauthorized approval submissions by non-admins must be rejected with HTTP 403."""
    client: httpx.AsyncClient = sec_env["client"]
    admin_token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.ADMIN)
    dev_token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.DEVELOPER)

    # Create project and mission
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Approval Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]

    mission_resp = await client.post(
        "/v1/missions",
        json={"project_id": project_id, "title": "Deploy Gate", "objective": "Deploy safely"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    mission_id = mission_resp.json()["id"]

    # Create an approval request directly in persistence
    approval_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    async with SqlAlchemyUnitOfWork(sec_env["session_factory"]) as uow:
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=sec_env["org_a_id"],
            mission_id=uuid.UUID(mission_id),
            action_type=ApprovalActionType.DEPLOYMENT.value,
            target_resource="prod-us-east-1",
            mission_version=1,
            expires_at=expires_at,
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    digest = compute_action_digest(
        secret=TEST_SECRET,
        mission_id=uuid.UUID(mission_id),
        action_type=ApprovalActionType.DEPLOYMENT.value,
        target_resource="prod-us-east-1",
        mission_version=1,
        expires_at=expires_at,
    )

    # Developer attempts to approve
    resp = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": digest},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_08_expired_approvals(sec_env):
    """8. Expired approval checkpoints must be rejected with HTTP 410 Gone."""
    client: httpx.AsyncClient = sec_env["client"]
    admin_token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.ADMIN)

    # Create project and mission
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Expired Gate Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    mission_resp = await client.post(
        "/v1/missions",
        json={"project_id": project_id, "title": "Expired Gate", "objective": "Test expiration"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    mission_id = mission_resp.json()["id"]

    approval_id = uuid.uuid4()
    past_expiration = datetime.now(UTC) - timedelta(hours=2)
    async with SqlAlchemyUnitOfWork(sec_env["session_factory"]) as uow:
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=sec_env["org_a_id"],
            mission_id=uuid.UUID(mission_id),
            action_type=ApprovalActionType.INITIAL_PLAN.value,
            target_resource="plan-v1",
            mission_version=1,
            expires_at=past_expiration,
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    digest = compute_action_digest(
        secret=TEST_SECRET,
        mission_id=uuid.UUID(mission_id),
        action_type=ApprovalActionType.INITIAL_PLAN.value,
        target_resource="plan-v1",
        mission_version=1,
        expires_at=past_expiration,
    )

    resp = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": digest},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 410
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_09_changed_action_digests(sec_env):
    """9. Altered or forged action digests must be rejected with HTTP 409 Conflict."""
    client: httpx.AsyncClient = sec_env["client"]
    admin_token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.ADMIN)

    # Setup project and mission
    proj = await client.post(
        "/v1/projects",
        json={"name": "Digest Tamper Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    miss = await client.post(
        "/v1/missions",
        json={"project_id": proj.json()["id"], "title": "Tamper Test", "objective": "Digest check"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    mission_id = miss.json()["id"]

    approval_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=10)
    async with SqlAlchemyUnitOfWork(sec_env["session_factory"]) as uow:
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=sec_env["org_a_id"],
            mission_id=uuid.UUID(mission_id),
            action_type=ApprovalActionType.EXTERNAL_REPOSITORY_WRITE.value,
            target_resource="github.com/repo",
            mission_version=1,
            expires_at=expires_at,
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    # Pass an invalid digest
    resp = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": "a" * 64},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409
    assert "digest mismatch" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_10_replayed_approvals(sec_env):
    """10. Replaying an already resolved approval must be rejected with HTTP 409 Conflict."""
    client: httpx.AsyncClient = sec_env["client"]
    admin_token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.ADMIN)

    proj = await client.post(
        "/v1/projects",
        json={"name": "Replay Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    miss = await client.post(
        "/v1/missions",
        json={"project_id": proj.json()["id"], "title": "Replay Mission", "objective": "Test replay"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    mission_id = miss.json()["id"]

    approval_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=10)
    async with SqlAlchemyUnitOfWork(sec_env["session_factory"]) as uow:
        await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=sec_env["org_a_id"],
            mission_id=uuid.UUID(mission_id),
            action_type=ApprovalActionType.INITIAL_PLAN.value,
            target_resource="plan-dag-v1",
            mission_version=1,
            expires_at=expires_at,
            secret_key=TEST_SECRET,
        )
        await uow.commit()

    digest = compute_action_digest(
        secret=TEST_SECRET,
        mission_id=uuid.UUID(mission_id),
        action_type=ApprovalActionType.INITIAL_PLAN.value,
        target_resource="plan-dag-v1",
        mission_version=1,
        expires_at=expires_at,
    )

    # First attempt: SUCCESS (200 OK)
    resp1 = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": digest},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["decision"] == "APPROVED"

    # Second attempt (Replay): REJECTED (409 Conflict)
    resp2 = await client.post(
        f"/v1/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "action_digest": digest},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 409
    assert "already been resolved" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_11_duplicate_idempotency_keys_different_payloads(sec_env):
    """11. Reusing an Idempotency-Key with a different payload must be rejected with HTTP 409 Conflict."""
    client: httpx.AsyncClient = sec_env["client"]
    token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.DEVELOPER)

    idem_key = "idemp-key-unique-789"

    # Request 1
    resp1 = await client.post(
        "/v1/projects",
        json={"name": "Payload One"},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
    )
    assert resp1.status_code == 201
    assert resp1.json()["name"] == "Payload One"

    # Repeated Request with SAME payload: returns cached response
    resp1_cached = await client.post(
        "/v1/projects",
        json={"name": "Payload One"},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
    )
    assert resp1_cached.status_code == 201
    assert resp1_cached.json()["name"] == "Payload One"

    # Reused Request with DIFFERENT payload: 409 Conflict
    resp_conflict = await client.post(
        "/v1/projects",
        json={"name": "Different Payload Two"},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
    )
    assert resp_conflict.status_code == 409
    assert "idempotency key" in resp_conflict.json()["detail"].lower()


@pytest.mark.asyncio
async def test_12_oversubscribed_budgets(sec_env):
    """12. Budget reservation exceeding limits must raise BudgetExceededError."""
    session_factory = sec_env["session_factory"]
    mission_id = uuid.uuid4()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.budgets.create(
            org_id=sec_env["org_a_id"],
            mission_id=mission_id,
            max_tokens=100_000,
            max_cost_usd=Decimal("50.00"),
        )
        await uow.commit()

    # Attempt to reserve over the limit (150,000 tokens)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        with pytest.raises(BudgetExceededError) as exc_info:
            await uow.budgets.reserve(mission_id=mission_id, tokens=150_000, cost_usd=Decimal("10.00"))
        assert "exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_13_request_size_limit_middleware(sec_env):
    """Bonus: Request body exceeding 10MB limit must be rejected with HTTP 413."""
    client: httpx.AsyncClient = sec_env["client"]
    token = generate_jwt(user_id=uuid.uuid4(), org_id=sec_env["org_a_id"], role=MembershipRole.DEVELOPER)

    # Simulate request with Content-Length larger than 10MB
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Length": str(15 * 1024 * 1024),  # 15MB
    }
    resp = await client.post("/v1/projects", content=b"{}", headers=headers)
    assert resp.status_code == 413
    assert resp.headers["content-type"] == "application/problem+json"
    assert "payload too large" in resp.json()["title"].lower()


@pytest.mark.asyncio
async def test_14_dev_auth_prohibited_in_production(sec_env):
    """Bonus: Dev auth headers must be rejected in production."""
    prod_settings = Settings(
        environment="production",
        dev_auth_enabled=False,
        database_url="postgresql+asyncpg://syntra_app:secret@localhost:5432/syntra_prod",
        jwt_secret_key=TEST_SECRET,
    )
    app.dependency_overrides[get_settings] = lambda: prod_settings

    client: httpx.AsyncClient = sec_env["client"]
    resp = await client.get(
        "/v1/projects",
        headers={"X-Dev-User-Id": str(uuid.uuid4()), "X-Dev-Org-Id": str(sec_env["org_a_id"])},
    )
    assert resp.status_code == 401
    assert "strictly prohibited" in resp.json()["detail"].lower()
