"""Phase 11 Milestone 11.1 Test Suite: Persistent Memory Foundation.

Verifies:
1. Pure domain MemoryRecord validation, scopes, provenance, and deprecation lifecycle.
2. Mandatory secret redaction with SecretRedactor, fail-closed enforcement, and high-entropy detection.
3. Transactional MemoryRepository persistence, rollback semantics, and Unit of Work integration.
4. Server-side multi-tenant isolation, cross-organization fences, and cross-project boundaries.
5. Live PostgreSQL integration verification.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from syntra.core.redactor import SecretRedactor
from syntra.domain.entities import (
    MemoryRecord,
    MemoryScope,
)
from syntra.domain.exceptions import (
    CrossTenantAccessError,
    MemoryValidationError,
    SecretRedactionError,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager

POSTGRES_TEST_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/syntra_test"


def is_postgres_available() -> bool:
    """Check whether a real PostgreSQL test database is reachable."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        res = sock.connect_ex(("127.0.0.1", 5432))
        sock.close()
        return res == 0
    except Exception:
        return False


# ==============================================================================
# Database Fixtures
# ==============================================================================
@pytest.fixture
async def test_db():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    yield db
    await db.close()


@pytest.fixture
async def uow(test_db):
    session_factory = test_db.get_session_factory()
    return SqlAlchemyUnitOfWork(session_factory)


# ==============================================================================
# 1. Pure Domain MemoryRecord Tests
# ==============================================================================
def test_memory_record_domain_defaults():
    rec = MemoryRecord(
        org_id=uuid4(),
        category="architecture",
        lesson_key="use_fastapi",
        content="Always use FastAPI for async APIs.",
    )
    rec.validate()
    assert rec.scope == MemoryScope.ORGANIZATION
    assert rec.confidence_score == Decimal("1.00")
    assert not rec.is_deprecated


def test_memory_record_domain_validation_project_scope_requires_project_id():
    rec = MemoryRecord(
        org_id=uuid4(),
        scope=MemoryScope.PROJECT,
        project_id=None,
        category="testing",
        lesson_key="pytest_async",
        content="Use anyio marker.",
    )
    with pytest.raises(MemoryValidationError, match="project_id is mandatory"):
        rec.validate()

    rec.project_id = uuid4()
    rec.validate()  # Now valid


def test_memory_record_domain_validation_execution_scope_requires_task_id():
    rec = MemoryRecord(
        org_id=uuid4(),
        scope=MemoryScope.EXECUTION,
        provenance_task_id=None,
        category="debugging",
        lesson_key="flaky_socket",
        content="Close socket in tearDown.",
    )
    with pytest.raises(MemoryValidationError, match="provenance_task_id is mandatory"):
        rec.validate()

    rec.provenance_task_id = uuid4()
    rec.validate()  # Now valid


def test_memory_record_domain_validation_required_fields():
    org_id = uuid4()
    # Missing category
    with pytest.raises(MemoryValidationError, match="category must be a non-empty string"):
        MemoryRecord(org_id=org_id, category="", lesson_key="k", content="c").validate()

    # Category too long
    with pytest.raises(MemoryValidationError, match="category cannot exceed 100 characters"):
        MemoryRecord(org_id=org_id, category="x" * 101, lesson_key="k", content="c").validate()

    # Missing lesson_key
    with pytest.raises(MemoryValidationError, match="lesson_key must be a non-empty string"):
        MemoryRecord(org_id=org_id, category="c", lesson_key="", content="c").validate()

    # Lesson key too long
    with pytest.raises(MemoryValidationError, match="lesson_key cannot exceed 255 characters"):
        MemoryRecord(org_id=org_id, category="c", lesson_key="k" * 256, content="c").validate()

    # Missing content
    with pytest.raises(MemoryValidationError, match="content must be a non-empty string"):
        MemoryRecord(org_id=org_id, category="c", lesson_key="k", content="   ").validate()


def test_memory_record_domain_confidence_score_boundaries():
    org_id = uuid4()
    # Negative confidence
    with pytest.raises(MemoryValidationError, match="confidence_score must be between 0.00 and 1.00"):
        MemoryRecord(
            org_id=org_id,
            category="c",
            lesson_key="k",
            content="content",
            confidence_score=Decimal("-0.01"),
        ).validate()

    # Exceeding 1.00
    with pytest.raises(MemoryValidationError, match="confidence_score must be between 0.00 and 1.00"):
        MemoryRecord(
            org_id=org_id,
            category="c",
            lesson_key="k",
            content="content",
            confidence_score=Decimal("1.01"),
        ).validate()


def test_memory_record_deprecation_lifecycle():
    rec = MemoryRecord(
        org_id=uuid4(),
        category="architecture",
        lesson_key="deprecated_pattern",
        content="Old pattern.",
        confidence_score=Decimal("0.95"),
    )
    assert not rec.is_deprecated
    rec.deprecate()
    assert rec.is_deprecated
    assert rec.confidence_score == Decimal("0.00")
    rec.validate()  # 0.00 is a valid confidence score for deprecated memories


# ==============================================================================
# 2. Secret Redaction & Fail-Closed Security Tests
# ==============================================================================
def test_secret_redactor_api_keys():
    # Google API Key
    text_google = "Connecting with key AIzaSyD-1234567890abcdefghijklmnopqrstuv"
    assert SecretRedactor.redact(text_google) == "Connecting with key [REDACTED_API_KEY]"

    # OpenAI Key
    text_openai = "Use sk-abcdef1234567890abcdef1234567890 for embeddings"
    assert SecretRedactor.redact(text_openai) == "Use [REDACTED_API_TOKEN] for embeddings"

    # GitHub PAT
    text_ghp = "Clone with ghp_123456789012345678901234567890123456"
    assert SecretRedactor.redact(text_ghp) == "Clone with [REDACTED_GITHUB_TOKEN]"

    # Bearer Token
    text_bearer = "Authorization: Bearer mySecretToken1234567890abcdef"
    assert SecretRedactor.redact(text_bearer) == "Authorization: Bearer [REDACTED_BEARER_TOKEN]"

    # JWT Token
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG4mHq_someSignatureVal123"
    assert SecretRedactor.redact(f"Token: {jwt}") == "Token: [REDACTED_JWT_TOKEN]"


def test_secret_redactor_private_keys():
    rsa_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y1+r...fakeKeyData...\n-----END RSA PRIVATE KEY-----"
    assert SecretRedactor.redact(f"Config:\n{rsa_key}") == "Config:\n[REDACTED_PRIVATE_KEY]"


def test_secret_redactor_key_value_assignments():
    json_creds = '{"password": "SuperSecretPassword123!", "api_key": "someKeyABC12345"}'
    redacted = SecretRedactor.redact(json_creds)
    assert "SuperSecretPassword123!" not in redacted
    assert "[REDACTED_CREDENTIAL]" in redacted


def test_secret_redactor_high_entropy_secrets():
    # Random high entropy hex token (32 chars)
    random_secret = "f4c93a8b27e10d9f8a3c5e7b1a2d4f6c"
    text = f"api_token is {random_secret} for staging"
    redacted = SecretRedactor.redact(text)
    assert random_secret not in redacted
    assert "[REDACTED_" in redacted


def test_secret_redactor_fail_closed_on_invalid_input():
    # Non-string inputs must raise SecretRedactionError rather than returning or silencing
    with pytest.raises(SecretRedactionError):
        SecretRedactor.redact(None)  # type: ignore

    with pytest.raises(SecretRedactionError):
        SecretRedactor.redact(12345)  # type: ignore

    with pytest.raises(SecretRedactionError):
        SecretRedactor.redact({"secret": "key"})  # type: ignore


def test_secret_redactor_dict_and_list_redaction():
    payload = {
        "user": "alice",
        "api_key": "raw_secret_value",
        "nested": {
            "token": "nested_secret",
            "normal_field": "public_text",
        },
        "items": ["safe", "sk-proj-1234567890abcdef1234567890abcdef"],
    }
    cleaned = SecretRedactor.redact_sensitive_data(payload)
    assert cleaned["user"] == "alice"
    assert cleaned["api_key"] == "[REDACTED_SECRET]"
    assert cleaned["nested"]["token"] == "[REDACTED_SECRET]"
    assert cleaned["nested"]["normal_field"] == "public_text"
    assert cleaned["items"][0] == "safe"
    assert cleaned["items"][1] == "[REDACTED_API_TOKEN]"


# ==============================================================================
# 3. Transactional MemoryRepository & CRUD Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_memory_repository_create_and_get(uow):
    org_id = uuid4()
    async with uow:
        # Create organization
        await uow.organizations.create(org_id=org_id, name="Syntra AI", slug="syntra-ai")

        # Create memory record with sensitive token in content
        record = await uow.memories.create(
            org_id=org_id,
            category="security",
            lesson_key="rotate_keys",
            content="Rotate key AIzaSyD-1234567890abcdefghijklmnopqrstuv immediately.",
            scope=MemoryScope.ORGANIZATION,
            confidence_score=Decimal("0.95"),
        )
        assert record.id is not None
        # Verify secret was redacted BEFORE persistence
        assert "AIza" not in record.content
        assert "[REDACTED_API_KEY]" in record.content

        # Retrieve by id
        fetched = await uow.memories.get_by_id(memory_id=record.id, org_id=org_id)
        assert fetched is not None
        assert fetched.id == record.id
        assert fetched.lesson_key == "rotate_keys"
        assert fetched.confidence_score == Decimal("0.95")
        await uow.commit()


@pytest.mark.asyncio
async def test_memory_repository_transaction_rollback(uow):
    org_id = uuid4()
    memory_id = uuid4()

    # Step 1: Create organization
    async with uow:
        await uow.organizations.create(org_id=org_id, name="Rollback Org", slug="rollback-org")
        await uow.commit()

    # Step 2: Attempt creation and rollback
    async with uow:
        await uow.memories.create(
            record_id=memory_id,
            org_id=org_id,
            category="temp",
            lesson_key="ephemeral",
            content="This should not persist.",
        )
        await uow.rollback()

    # Step 3: Verify record does NOT exist
    async with uow:
        res = await uow.memories.get_by_id(memory_id=memory_id, org_id=org_id)
        assert res is None


@pytest.mark.asyncio
async def test_memory_repository_save_domain_entity(uow):
    org_id = uuid4()
    async with uow:
        await uow.organizations.create(org_id=org_id, name="Entity Org", slug="entity-org")

        domain_rec = MemoryRecord(
            org_id=org_id,
            category="patterns",
            lesson_key="unit_of_work_pattern",
            content="Commit only at transaction boundaries.",
            confidence_score=Decimal("0.90"),
        )
        model = await uow.memories.save(domain_rec)
        assert model.id == domain_rec.id
        assert model.lesson_key == "unit_of_work_pattern"

        # Domain conversion check
        reconstructed = model.to_domain()
        assert reconstructed.id == domain_rec.id
        assert reconstructed.lesson_key == domain_rec.lesson_key
        assert reconstructed.confidence_score == domain_rec.confidence_score
        await uow.commit()


@pytest.mark.asyncio
async def test_memory_repository_deprecate(uow):
    org_id = uuid4()
    async with uow:
        await uow.organizations.create(org_id=org_id, name="Deprecate Org", slug="dep-org")
        rec = await uow.memories.create(
            org_id=org_id,
            category="obsolete",
            lesson_key="legacy_migration",
            content="Do not use raw SQL queries.",
            confidence_score=Decimal("0.85"),
        )
        await uow.commit()

    async with uow:
        success = await uow.memories.deprecate(memory_id=rec.id, org_id=org_id)
        assert success is True
        await uow.commit()

    async with uow:
        updated = await uow.memories.get_by_id(memory_id=rec.id, org_id=org_id)
        assert updated is not None
        assert updated.confidence_score == Decimal("0.00")
        assert updated.to_domain().is_deprecated


# ==============================================================================
# 4. Multi-Tenant Isolation & Fencing Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_memory_repository_cross_tenant_access_denied(uow):
    org_a = uuid4()
    org_b = uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_a, name="Org A", slug="org-a")
        await uow.organizations.create(org_id=org_b, name="Org B", slug="org-b")

        rec_a = await uow.memories.create(
            org_id=org_a,
            category="internal",
            lesson_key="confidential_sop",
            content="Internal proprietary design.",
        )
        await uow.commit()

    # Attempting to read Org A's memory using Org B's ID must raise CrossTenantAccessError
    async with uow:
        with pytest.raises(CrossTenantAccessError, match="Unauthorized cross-tenant access"):
            await uow.memories.get_by_id(memory_id=rec_a.id, org_id=org_b)


@pytest.mark.asyncio
async def test_memory_repository_cross_tenant_deprecation_denied(uow):
    org_a = uuid4()
    org_b = uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_a, name="Org A Dep", slug="org-a-dep")
        await uow.organizations.create(org_id=org_b, name="Org B Dep", slug="org-b-dep")

        rec_a = await uow.memories.create(
            org_id=org_a,
            category="internal",
            lesson_key="important_rule",
            content="Never bypass security audits.",
        )
        await uow.commit()

    # Attempting to deprecate Org A's memory from Org B must fail with CrossTenantAccessError
    async with uow:
        with pytest.raises(CrossTenantAccessError, match="Unauthorized cross-tenant deprecation"):
            await uow.memories.deprecate(memory_id=rec_a.id, org_id=org_b)


@pytest.mark.asyncio
async def test_memory_repository_cross_tenant_project_binding_denied(uow):
    org_a = uuid4()
    org_b = uuid4()
    project_b = uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_a, name="Org Alpha", slug="org-alpha")
        await uow.organizations.create(org_id=org_b, name="Org Beta", slug="org-beta")
        await uow.projects.create(project_id=project_b, org_id=org_b, name="Beta Proj", slug="beta-proj")
        await uow.commit()

    # Creating a memory in Org A that references a project in Org B must fail with CrossTenantAccessError
    async with uow:
        with pytest.raises(CrossTenantAccessError, match="Cross-tenant violation"):
            await uow.memories.create(
                org_id=org_a,
                project_id=project_b,
                scope=MemoryScope.PROJECT,
                category="cross_ref",
                lesson_key="illegal_binding",
                content="Illegal cross-tenant reference.",
            )


@pytest.mark.asyncio
async def test_memory_repository_query_by_scope_isolation(uow):
    org_a = uuid4()
    org_b = uuid4()
    project_a = uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_a, name="Query Org A", slug="query-org-a")
        await uow.organizations.create(org_id=org_b, name="Query Org B", slug="query-org-b")
        await uow.projects.create(project_id=project_a, org_id=org_a, name="Proj A", slug="proj-a")

        # Org A records
        await uow.memories.create(
            org_id=org_a,
            scope=MemoryScope.ORGANIZATION,
            category="style",
            lesson_key="naming_rules",
            content="Use snake_case for functions.",
            confidence_score=Decimal("0.90"),
        )
        await uow.memories.create(
            org_id=org_a,
            scope=MemoryScope.PROJECT,
            project_id=project_a,
            category="style",
            lesson_key="project_naming",
            content="Prefix all test modules with test_.",
            confidence_score=Decimal("0.95"),
        )

        # Org B record
        await uow.memories.create(
            org_id=org_b,
            scope=MemoryScope.ORGANIZATION,
            category="style",
            lesson_key="org_b_rule",
            content="Org B internal rule.",
            confidence_score=Decimal("1.00"),
        )
        await uow.commit()

    # Query Org A by organization scope
    async with uow:
        results_a = await uow.memories.query_by_scope(
            org_id=org_a,
            scope=MemoryScope.ORGANIZATION,
        )
        assert len(results_a) == 1
        assert results_a[0].lesson_key == "naming_rules"

        # Query Org A by project scope
        results_proj = await uow.memories.query_by_scope(
            org_id=org_a,
            scope=MemoryScope.PROJECT,
            project_id=project_a,
        )
        assert len(results_proj) == 1
        assert results_proj[0].lesson_key == "project_naming"

        # Query Org B: must NOT see Org A records
        results_b = await uow.memories.query_by_scope(
            org_id=org_b,
            scope=MemoryScope.ORGANIZATION,
        )
        assert len(results_b) == 1
        assert results_b[0].lesson_key == "org_b_rule"


# ==============================================================================
# 5. Live PostgreSQL Integration Tests (When DB is available)
# ==============================================================================
@pytest.mark.asyncio
async def test_live_postgres_memory_persistence():
    if not is_postgres_available():
        pytest.skip("Live PostgreSQL service not reachable on port 5432.")

    db = DatabaseManager(POSTGRES_TEST_URL)
    session_factory = db.get_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory)

    org_id = uuid4()
    memory_id = uuid4()

    async with uow:
        await uow.organizations.create(org_id=org_id, name="PG Live Org", slug=f"pg-live-{org_id.hex[:6]}")
        rec = await uow.memories.create(
            record_id=memory_id,
            org_id=org_id,
            category="postgres_live",
            lesson_key="live_transaction",
            content="Token: sk-proj-1234567890abcdef1234567890 should be redacted on live Postgres.",
            confidence_score=Decimal("0.99"),
        )
        assert "[REDACTED_API_TOKEN]" in rec.content
        await uow.commit()

    async with uow:
        fetched = await uow.memories.get_by_id(memory_id=memory_id, org_id=org_id)
        assert fetched is not None
        assert fetched.confidence_score == Decimal("0.99")
        assert "sk-proj-" not in fetched.content

        # Deprecate on live Postgres
        dep_res = await uow.memories.deprecate(memory_id=memory_id, org_id=org_id)
        assert dep_res is True
        await uow.commit()

    async with uow:
        fetched_dep = await uow.memories.get_by_id(memory_id=memory_id, org_id=org_id)
        assert fetched_dep is not None
        assert fetched_dep.confidence_score == Decimal("0.00")

    await db.close()
