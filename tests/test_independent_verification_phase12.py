"""Independent Verification Service and VerificationRecord Tests (Phase 12 Milestone 12.1)."""

import hashlib
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from syntra.domain.entities import (
    AgentRole,
    AttemptState,
    MissionState,
    TaskPlanStatus,
    VerificationEvidence,
    VerificationRecord,
    VerificationStatus,
    compute_verification_signature,
    verify_verification_signature,
)
from syntra.domain.exceptions import (
    VerificationError,
    VerificationTamperedError,
)
from syntra.persistence.models import MissionModel, ProjectModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager
from syntra.verification.models import VerificationRequest
from syntra.verification.service import (
    IndependentVerificationService,
    require_independent_verifier,
)

POSTGRES_TEST_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/syntra_test"


def is_postgres_available() -> bool:
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        res = sock.connect_ex(("127.0.0.1", 5432))
        sock.close()
        return res == 0
    except Exception:
        return False


@pytest.fixture
async def memory_uow():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory)
    yield uow
    await db.close()


async def setup_test_hierarchy(uow: SqlAlchemyUnitOfWork) -> tuple[UUID, UUID, UUID, UUID]:
    org_id = uuid4()
    await uow.organizations.create(org_id=org_id, name="Test Org", slug=f"org-{org_id.hex[:8]}")

    proj_id = uuid4()
    proj = ProjectModel(id=proj_id, org_id=org_id, name="Test Project", slug=f"proj-{proj_id.hex[:8]}")
    uow.session.add(proj)
    await uow.session.flush()

    mission_id = uuid4()
    mission = MissionModel(
        id=mission_id,
        org_id=org_id,
        project_id=proj_id,
        objective="Verification Test Mission",
        state=MissionState.RUNNING,
        active_plan_version=1,
    )
    uow.session.add(mission)
    await uow.session.flush()

    plan_id = uuid4()
    await uow.tasks.create_plan(plan_id=plan_id, mission_id=mission_id, version=1, status=TaskPlanStatus.APPROVED)

    task_id = uuid4()
    await uow.tasks.create_task(
        task_id=task_id,
        task_plan_id=plan_id,
        mission_id=mission_id,
        org_id=org_id,
        identifier="TASK-1",
        title="Calculator Enhancement",
        description="Add operations to calculator",
        assigned_role=AgentRole.BACKEND_ENGINEER.value,
    )

    attempt_id = uuid4()
    await uow.tasks.create_attempt(
        task_id=task_id,
        attempt_number=1,
        state=AttemptState.RUNNING,
        attempt_id=attempt_id,
    )
    await uow.commit()
    return org_id, mission_id, task_id, attempt_id


# ==============================================================================
# 1. Pure Domain Entity and Signature Tests
# ==============================================================================
def test_verification_record_domain_validation() -> None:
    evidence = VerificationEvidence(
        exit_code=0,
        execution_duration_ms=120,
        stdout_digest="a" * 64,
        stderr_digest="b" * 64,
        tests_passed=5,
    )
    rec = VerificationRecord(
        id=uuid4(),
        org_id=uuid4(),
        mission_id=uuid4(),
        task_id=uuid4(),
        task_attempt_id=uuid4(),
        plan_version=1,
        status=VerificationStatus.PASSED,
        clean_base_commit="c" * 64,
        patch_hash="d" * 64,
        protected_test_suite_hash="e" * 64,
        evidence=evidence,
        verifier_signature="f" * 64,
    )
    rec.validate()  # Validates cleanly

    # Invalid patch hash length
    rec.patch_hash = "short"
    with pytest.raises(VerificationError):
        rec.validate()


def test_compute_and_verify_signature() -> None:
    secret = "test-secret-key-123"
    org_id = uuid4()
    mission_id = uuid4()
    task_id = uuid4()
    attempt_id = uuid4()
    patch_hash = "1" * 64
    base_commit = "2" * 64
    manifest_hash = "3" * 64

    sig = compute_verification_signature(
        secret=secret,
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        patch_hash=patch_hash,
        clean_base_commit=base_commit,
        protected_test_suite_hash=manifest_hash,
        status="PASSED",
        exit_code=0,
    )

    assert len(sig) == 64
    assert verify_verification_signature(
        secret=secret,
        expected_signature=sig,
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        patch_hash=patch_hash,
        clean_base_commit=base_commit,
        protected_test_suite_hash=manifest_hash,
        status="PASSED",
        exit_code=0,
    )

    # Any modification invalidates signature
    assert not verify_verification_signature(
        secret=secret,
        expected_signature=sig,
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        patch_hash="9" * 64,  # tampered
        clean_base_commit=base_commit,
        protected_test_suite_hash=manifest_hash,
        status="PASSED",
        exit_code=0,
    )


def test_require_independent_verifier_enforcement() -> None:
    """Category F: Implementer cannot verify or self-certify its own patch."""
    inv_id = uuid4()

    # Same invocation ID -> rejected
    with pytest.raises(ValueError) as exc:
        require_independent_verifier(
            implementer_role=AgentRole.BACKEND_ENGINEER,
            implementer_invocation_id=inv_id,
            verifier_id=inv_id,
        )
    assert "Implementer invocation cannot act as independent verifier" in str(exc.value)

    # Different invocation ID -> allowed
    other_id = uuid4()
    require_independent_verifier(
        implementer_role=AgentRole.BACKEND_ENGINEER,
        implementer_invocation_id=inv_id,
        verifier_id=other_id,
    )


# ==============================================================================
# 2. Service Verification Tests with Ephemeral Git Repositories
# ==============================================================================
@pytest.fixture
def clean_git_repo(tmp_path: Path) -> Path:
    """Create a pristine initialized git repository for hermetic testing."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Syntra Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@syntra.local"], cwd=repo, check=True)

    # Add application file and test file
    app_file = repo / "calculator.py"
    app_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    test_file = repo / "test_calc.py"
    test_file.write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "Initial commit"], cwd=repo, check=True)
    return repo


@pytest.mark.asyncio
async def test_verify_patch_passing(clean_git_repo: Path, memory_uow: SqlAlchemyUnitOfWork) -> None:
    """Verification of a clean, correct patch passes hermetically."""
    service = IndependentVerificationService()

    # Unified diff adding a multiply function and a passing test
    patch = """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -2,1 +2,3 @@
     return a + b
+def multiply(a: int, b: int) -> int:
+    return a * b
diff --git a/test_calc.py b/test_calc.py
--- a/test_calc.py
+++ b/test_calc.py
@@ -4,1 +4,3 @@
     assert add(2, 3) == 5
+def test_multiply():
+    from calculator import multiply
+    assert multiply(3, 4) == 12
"""

    async with memory_uow:
        org_id, mission_id, task_id, attempt_id = await setup_test_hierarchy(memory_uow)

    request = VerificationRequest(
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        plan_version=1,
        patch=patch,
        clean_base_commit="HEAD",
        implementer_role=AgentRole.BACKEND_ENGINEER,
        implementer_invocation_id=uuid4(),
        verifier_id=uuid4(),
    )

    async with memory_uow:
        result = await service.verify_patch(
            uow=memory_uow,
            request=request,
            repo_root=clean_git_repo,
            test_command=[sys.executable, "-m", "pytest", "test_calc.py", "-v"],
        )
        await memory_uow.commit()

    assert result.status == VerificationStatus.PASSED
    assert result.record.status == VerificationStatus.PASSED
    assert result.record.evidence.exit_code == 0
    assert result.record.evidence.tests_passed >= 2

    # Verify persisted in database
    async with memory_uow:
        persisted = await memory_uow.verifications.get_record_by_id(result.record.id)
        assert persisted is not None
        assert persisted.status == "PASSED"
        assert persisted.patch_hash == hashlib.sha256(patch.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_false_success_rejection(clean_git_repo: Path, memory_uow: SqlAlchemyUnitOfWork) -> None:
    """Category A: False success rejection - patch introduces defect that fails tests."""
    service = IndependentVerificationService()

    # Patch that breaks calculator.add
    adversarial_patch = """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def add(a: int, b: int) -> int:
-    return a + b
+    return a - b
"""

    async with memory_uow:
        org_id, mission_id, task_id, attempt_id = await setup_test_hierarchy(memory_uow)

    request = VerificationRequest(
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        plan_version=1,
        patch=adversarial_patch,
        clean_base_commit="HEAD",
        implementer_role=AgentRole.BACKEND_ENGINEER,
        implementer_invocation_id=uuid4(),
        verifier_id=uuid4(),
    )

    async with memory_uow:
        result = await service.verify_patch(
            uow=memory_uow,
            request=request,
            repo_root=clean_git_repo,
            test_command=[sys.executable, "-m", "pytest", "test_calc.py", "-v"],
        )
        await memory_uow.commit()

    assert result.status == VerificationStatus.FAILED
    assert result.record.status == VerificationStatus.FAILED
    assert result.evidence.exit_code != 0
    assert result.evidence.tests_failed >= 1


@pytest.mark.asyncio
async def test_tampered_signature_rejection(memory_uow: SqlAlchemyUnitOfWork) -> None:
    """Category H: Verification record signature tampering is detected."""
    service = IndependentVerificationService()
    async with memory_uow:
        org_id, mission_id, task_id, attempt_id = await setup_test_hierarchy(memory_uow)

        # Store record with fraudulent signature
        evidence = VerificationEvidence(
            exit_code=0,
            execution_duration_ms=50,
            stdout_digest="0" * 64,
            stderr_digest="0" * 64,
            tests_passed=1,
        )
        tampered_record = VerificationRecord(
            id=uuid4(),
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            plan_version=1,
            status=VerificationStatus.PASSED,
            clean_base_commit="0" * 64,
            patch_hash="1" * 64,
            protected_test_suite_hash="2" * 64,
            evidence=evidence,
            verifier_signature="0" * 64,  # fraudulent signature
        )
        await memory_uow.verifications.create_record(tampered_record)
        await memory_uow.commit()

    async with memory_uow:
        with pytest.raises(VerificationTamperedError) as exc_info:
            await service.verify_mission(memory_uow, org_id=org_id, mission_id=mission_id)
        assert "Cryptographic signature mismatch" in str(exc_info.value)


@pytest.mark.asyncio
async def test_postgres_verification_record_persistence() -> None:
    """Direct PostgreSQL live integration verification on syntra_test with migration 0005."""
    if not is_postgres_available():
        pytest.skip("PostgreSQL test database not reachable on port 5432")

    db = DatabaseManager(POSTGRES_TEST_URL)
    session_factory = db.get_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory)

    try:
        async with uow:
            org_id, mission_id, task_id, attempt_id = await setup_test_hierarchy(uow)

        patch_hash = "a" * 64
        evidence = VerificationEvidence(
            exit_code=0,
            execution_duration_ms=88,
            stdout_digest="b" * 64,
            stderr_digest="c" * 64,
            tests_passed=10,
            tests_failed=0,
        )
        record = VerificationRecord(
            id=uuid4(),
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            plan_version=1,
            status=VerificationStatus.PASSED,
            clean_base_commit="d" * 64,
            patch_hash=patch_hash,
            protected_test_suite_hash="e" * 64,
            evidence=evidence,
            verifier_signature="f" * 64,
            trace_id="trace-12345",
            span_id="span-67890",
        )

        async with uow:
            created_model = await uow.verifications.create_record(record)
            assert created_model is not None
            await uow.commit()

        # Query back through various access paths
        async with uow:
            retrieved = await uow.verifications.get_record_by_id(record.id)
            assert retrieved is not None
            assert retrieved.status == "PASSED"
            assert retrieved.trace_id == "trace-12345"
            assert retrieved.span_id == "span-67890"

            by_attempt = await uow.verifications.get_latest_record_for_attempt(
                org_id=org_id, mission_id=mission_id, task_id=task_id, task_attempt_id=attempt_id
            )
            assert by_attempt is not None
            assert by_attempt.id == record.id

            by_patch = await uow.verifications.get_record_by_patch_hash(
                org_id=org_id, mission_id=mission_id, patch_hash=patch_hash
            )
            assert by_patch is not None
            assert by_patch.id == record.id

            mission_records = await uow.verifications.get_records_for_mission(org_id, mission_id)
            assert len(mission_records) >= 1
            domain_rec = mission_records[0].to_domain()
            assert domain_rec.evidence.tests_passed == 10

    finally:
        await db.close()
