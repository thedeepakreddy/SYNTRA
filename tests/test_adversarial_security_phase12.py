"""Adversarial security test suite verifying Categories M, S, and R (Milestone 12.3).

Categories:
- Category M: Malicious Patches, Test Deletion, and Test Suppression Invariants
- Category S: Systemic Secret Scrubbing, OpenTelemetry Spans, and Sandbox Quarantine
- Category R: Replay Attacks, Cryptographic Tampering, and Delivery Gate Enforcement
"""

import logging
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.domain.entities import (
    MissionState,
    VerificationEvidence,
    VerificationRecord,
    VerificationStatus,
    compute_verification_signature,
    verify_verification_signature,
)
from syntra.domain.exceptions import (
    AuditLoggingError,
    DeliveryBlockedError,
    ProtectedTestViolationError,
    VerificationTamperedError,
)
from syntra.observability.audit_logger import (
    AUDIT_TASK_ATTEMPT_STARTED,
    AuditLogger,
)
from syntra.observability.tracer import (
    SPAN_SANDBOX_COMMAND_RUN,
    clear_in_memory_spans,
    get_in_memory_spans,
    init_tracer_provider,
    reset_tracer_provider,
    start_span,
)
from syntra.persistence.models import MissionModel, ProjectModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.sandbox.safety import is_sensitive_env_key, sanitize_env, validate_safe_path
from syntra.storage.database import DatabaseManager
from syntra.verification.registry import ProtectedTestRegistry
from syntra.verification.service import IndependentVerificationService


@pytest.fixture(autouse=True)
def clean_test_environment():
    reset_tracer_provider()
    clear_in_memory_spans()
    yield
    clear_in_memory_spans()


@pytest.fixture
async def test_uow_factory():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()

    def _factory():
        return SqlAlchemyUnitOfWork(session_factory)

    yield _factory
    await db.close()


# ==============================================================================
# Category M: Malicious Patches, Test Deletion, and Test Suppression
# ==============================================================================
def test_category_m_patch_modifying_protected_test_suite_blocked():
    """Category M: Patches touching protected test paths are rejected."""
    registry = ProtectedTestRegistry()

    malicious_patch = """--- a/tests/protected/test_calculator.py
+++ b/tests/protected/test_calculator.py
@@ -10,3 +10,3 @@
-    assert calc.add(2, 2) == 4
+    assert True
"""
    with pytest.raises(ProtectedTestViolationError, match="mutate protected regression test files"):
        registry.check_patch(malicious_patch)


def test_category_m_patch_inserting_test_suppression_blocked():
    """Category M: Patches introducing pytest.skip or sys.exit are rejected."""
    registry = ProtectedTestRegistry()

    skip_patch = """--- a/src/syntra/calculator.py
+++ b/src/syntra/calculator.py
@@ -1,3 +1,4 @@
+    pytest.skip('skip test')
 def add(a, b):
     return a + b
"""
    with pytest.raises(ProtectedTestViolationError, match="test suppression/skipping directive"):
        registry.check_patch(skip_patch)


def test_category_m_tampered_workspace_detected_by_manifest(tmp_path: Path):
    """Category M: Protected test file modification in workspace fails manifest validation."""
    registry = ProtectedTestRegistry()
    test_file = tmp_path / "tests" / "protected" / "test_auth.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_login(): assert True\n", encoding="utf-8")

    manifest = registry.compute_manifest(tmp_path)
    assert "tests/protected/test_auth.py" in manifest.protected_files

    # Tamper with file
    test_file.write_text("def test_login(): pass\n", encoding="utf-8")

    with pytest.raises(ProtectedTestViolationError, match="Protected test file tampered in workspace"):
        registry.validate_workspace(tmp_path, manifest)


# ==============================================================================
# Category S: Systemic Secret Scrubbing, OpenTelemetry Spans, & Sandbox Quarantine
# ==============================================================================
def test_category_s_secret_leakage_in_logging_filter_scrubbed():
    """Category S: Credentials in log message, args, and tracebacks are scrubbed."""
    from syntra.core.redactor import SecretScrubbingLogFilter

    log_filter = SecretScrubbingLogFilter()
    record = logging.LogRecord(
        name="adversarial_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=100,
        msg="API call failed with sk-abcdef12345678901234567890 for user %s",
        args=("token=AIzaSyD-12345678901234567890",),
        exc_info=None,
    )

    allowed = log_filter.filter(record)
    assert allowed is True
    assert "sk-" not in str(record.msg)
    assert "[REDACTED_API_TOKEN]" in str(record.msg)
    assert "AIzaSyD-" not in str(record.args)
    assert "[REDACTED_API_KEY]" in str(record.args)


def test_category_s_secret_leakage_in_spans_scrubbed():
    """Category S: Secret attributes and string tokens in spans are scrubbed on end."""
    init_tracer_provider()

    with start_span(
        SPAN_SANDBOX_COMMAND_RUN,
        mission_id=uuid4(),
        attributes={
            "authorization": "Bearer secret_token_xyz",
            "api_key": "AIzaSyD-12345678901234567890",
            "db_password": "ProductionPassword123!",
            "command": "curl -H 'Authorization: sk-abcdef12345678901234567890' https://api.syntra.io",
        },
    ):
        pass

    spans = get_in_memory_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs is not None

    # Sensitive keys redacted
    assert attrs["authorization"] == "[REDACTED_SPAN_ATTR]"
    assert attrs["api_key"] == "[REDACTED_SPAN_ATTR]"
    assert attrs["db_password"] == "[REDACTED_SPAN_ATTR]"

    # Substring in command redacted
    assert "sk-" not in str(attrs["command"])
    assert "[REDACTED_API_TOKEN]" in str(attrs["command"])


def test_category_s_child_process_environment_scrubbing():
    """Category S: Host secrets and credentials are quarantined from sandbox subprocesses."""
    host_env = {
        "PATH": "/usr/bin:/bin",
        "GEMINI_API_KEY": "AIzaSyD-host-key-1234567890",
        "DATABASE_URL": "postgresql://postgres:secret@localhost:5432/db",
        "REDIS_URL": "redis://:secret@localhost:6379",
        "SYN_AUTH_TOKEN": "sk-auth-token-1234567890",
        "SAFE_VAR": "public_data",
    }

    assert is_sensitive_env_key("GEMINI_API_KEY") is True
    assert is_sensitive_env_key("DATABASE_URL") is True
    assert is_sensitive_env_key("REDIS_URL") is True
    assert is_sensitive_env_key("SYN_AUTH_TOKEN") is True
    assert is_sensitive_env_key("SAFE_VAR") is False

    cleaned_env = sanitize_env(host_env)
    assert "GEMINI_API_KEY" not in cleaned_env
    assert "DATABASE_URL" not in cleaned_env
    assert "REDIS_URL" not in cleaned_env
    assert "SYN_AUTH_TOKEN" not in cleaned_env
    assert cleaned_env["SAFE_VAR"] == "public_data"


def test_category_s_sandbox_symlink_escape_blocked(tmp_path: Path):
    """Category S: Symlink pointing outside workspace root raises SandboxSecurityViolationError."""
    workspace = tmp_path / "sandbox"
    workspace.mkdir()
    outside_dir = tmp_path / "host_secrets"
    outside_dir.mkdir()
    secret_file = outside_dir / "keys.txt"
    secret_file.write_text("SUPER_SECRET", encoding="utf-8")

    # Create symlink pointing outside
    malicious_link = workspace / "escape_link"
    malicious_link.symlink_to(secret_file)

    from syntra.core.exceptions import SandboxSecurityViolationError

    with pytest.raises(SandboxSecurityViolationError, match="escapes workspace root"):
        validate_safe_path(workspace, "escape_link")


# ==============================================================================
# Category R: Replay, Tampering, and Delivery Gate Defense
# ==============================================================================
def test_category_r_tampered_verification_signature_rejected():
    """Category R: Verification record signature tampering is detected and rejected."""
    secret = "hmac-signing-key"
    org_id = uuid4()
    mission_id = uuid4()
    task_id = uuid4()
    attempt_id = uuid4()
    patch_hash = "a" * 64
    base_commit = "main-commit-1"
    suite_hash = "b" * 64

    valid_sig = compute_verification_signature(
        secret=secret,
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        patch_hash=patch_hash,
        clean_base_commit=base_commit,
        protected_test_suite_hash=suite_hash,
        status="PASSED",
        exit_code=0,
    )

    # Valid signature passes
    assert (
        verify_verification_signature(
            secret=secret,
            expected_signature=valid_sig,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            patch_hash=patch_hash,
            clean_base_commit=base_commit,
            protected_test_suite_hash=suite_hash,
            status="PASSED",
            exit_code=0,
        )
        is True
    )

    # Tampered signature fails
    tampered_sig = "f" * 64
    assert (
        verify_verification_signature(
            secret=secret,
            expected_signature=tampered_sig,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            patch_hash=patch_hash,
            clean_base_commit=base_commit,
            protected_test_suite_hash=suite_hash,
            status="PASSED",
            exit_code=0,
        )
        is False
    )

    # VerificationRecord domain validation detects signature mismatch
    rec = VerificationRecord(
        id=uuid4(),
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=attempt_id,
        plan_version=1,
        status=VerificationStatus.PASSED,
        clean_base_commit=base_commit,
        patch_hash=patch_hash,
        protected_test_suite_hash=suite_hash,
        evidence=VerificationEvidence(
            exit_code=0,
            execution_duration_ms=50,
            stdout_digest="x" * 64,
            stderr_digest="y" * 64,
            tests_passed=10,
        ),
        verifier_signature=tampered_sig,
    )
    with pytest.raises(VerificationTamperedError, match="signature verification failed"):
        IndependentVerificationService.verify_record_integrity(rec, secret=secret)


@pytest.mark.asyncio
async def test_category_r_delivery_gate_blocks_plan_version_mismatch(test_uow_factory):
    """Category R: Stale verification record from old plan version is blocked at delivery gate."""
    async with test_uow_factory() as test_uow:
        org_id = uuid4()
        await test_uow.organizations.create(org_id=org_id, name="Adversarial Org", slug=f"adv-{org_id.hex[:8]}")

        proj_id = uuid4()
        proj = ProjectModel(id=proj_id, org_id=org_id, name="Adv Project", slug=f"proj-{proj_id.hex[:8]}")
        test_uow.session.add(proj)
        await test_uow.session.flush()

        mission_id = uuid4()
        mission = MissionModel(
            id=mission_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Adversarial Mission",
            state=MissionState.RUNNING,
            active_plan_version=2,  # Current active plan is version 2!
        )
        test_uow.session.add(mission)
        await test_uow.session.flush()

        task_id = uuid4()
        attempt_id = uuid4()
        patch_hash = "e" * 64

        # Record was verified for plan_version=1 (STALE)
        v_rec = VerificationRecord(
            id=uuid4(),
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            plan_version=1,  # STALE PLAN VERSION
            status=VerificationStatus.PASSED,
            clean_base_commit="main-commit-1",
            patch_hash=patch_hash,
            protected_test_suite_hash="0" * 64,
            evidence=VerificationEvidence(
                exit_code=0,
                execution_duration_ms=100,
                stdout_digest="a" * 64,
                stderr_digest="b" * 64,
                tests_passed=5,
            ),
            verifier_signature="0" * 64,
        )
        await test_uow.verifications.create_record(v_rec)
        await test_uow.commit()

        from syntra.agents.operational import AgentRegistry
        from syntra.llm.mock_provider import MockModelProvider
        from syntra.llm.runtime import ModelRuntime
        from syntra.orchestration.engineering_service import EngineeringMissionService
        from syntra.skills.registry import SkillRegistry

        skills = SkillRegistry()
        skills.discover_skills()
        runtime = ModelRuntime(MockModelProvider(), skills)
        service = EngineeringMissionService(
            uow_factory=test_uow_factory,
            registry=AgentRegistry(skills, model_name="mock-model"),
            runtime=runtime,
            verification_commands=["pytest"],
        )

        state = {
            "org_id": str(org_id),
            "mission_id": str(mission_id),
            "mission_version": 2,
            "selected_results": [
                {
                    "task_id": str(task_id),
                    "attempt_id": str(attempt_id),
                    "patch_hash": patch_hash,
                }
            ],
        }

        with pytest.raises(DeliveryBlockedError, match="Plan version mismatch"):
            await service.verify_delivery_gate(test_uow, state)


def test_category_r_audit_log_tampering_detected(tmp_path: Path):
    """Category R: Modification of audit logs fails sha256 tamper verification."""
    log_file = tmp_path / "tamper_test_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    logger.log_event(
        event_type=AUDIT_TASK_ATTEMPT_STARTED,
        mission_id=uuid4(),
        outcome="SUCCESS",
        payload={"task_attempt": 1, "status": "AUTHORIZED"},
    )

    # File without modifications passes
    records = AuditLogger.verify_log_file(log_file)
    assert len(records) == 1

    # Tamper with file
    content = log_file.read_text(encoding="utf-8")
    tampered_content = content.replace("AUTHORIZED", "COMPROMISED")
    log_file.write_text(tampered_content, encoding="utf-8")

    with pytest.raises(AuditLoggingError, match="Audit log digest mismatch"):
        AuditLogger.verify_log_file(log_file)
