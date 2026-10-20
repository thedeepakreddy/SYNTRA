"""Unit and integration tests for Distributed Observability and Security Audit Pipeline (Milestone 12.3)."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from syntra.api.app import create_app
from syntra.domain.entities import (
    AgentRole,
    ArtifactType,
    AttemptState,
    MissionState,
    TaskPlanStatus,
    TaskState,
    VerificationEvidence,
    VerificationRecord,
    VerificationStatus,
)
from syntra.domain.exceptions import AuditLoggingError, DeliveryBlockedError
from syntra.observability.audit_logger import (
    AUDIT_DIFF_GENERATED,
    AUDIT_TASK_ATTEMPT_STARTED,
    AUDIT_VERIFICATION_PASSED,
    AuditLogger,
    compute_payload_digest,
)
from syntra.observability.propagation import (
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    inject_trace_context,
    parse_traceparent,
)
from syntra.observability.tracer import (
    SPAN_AGENT_REACT_LOOP,
    SPAN_MCP_TOOL_INVOCATION,
    SPAN_MISSION_EXECUTE,
    SPAN_MODEL_GEMINI_GENERATE,
    SPAN_ORCHESTRATOR_NODE,
    SPAN_SANDBOX_COMMAND_RUN,
    SPAN_VERIFICATION_RUN,
    clear_in_memory_spans,
    get_in_memory_spans,
    init_tracer_provider,
    reset_tracer_provider,
    start_span,
)
from syntra.persistence.models import MissionModel, ProjectModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.scheduling.models import TaskExecutionResult
from syntra.storage.database import DatabaseManager


@pytest.fixture(autouse=True)
def clean_observability():
    """Reset tracer and clear in-memory spans before and after each test."""
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
# 1. OpenTelemetry Tracer and Span Lifecycle Tests
# ==============================================================================
def test_opentelemetry_tracer_initialization_and_span_emission():
    """TracerProvider initializes cleanly with in-memory exporter and records standard spans."""
    provider, exporter = init_tracer_provider()
    assert provider is not None
    assert exporter is not None

    spans_to_test = [
        SPAN_MISSION_EXECUTE,
        SPAN_ORCHESTRATOR_NODE,
        SPAN_AGENT_REACT_LOOP,
        SPAN_MODEL_GEMINI_GENERATE,
        SPAN_MCP_TOOL_INVOCATION,
        SPAN_SANDBOX_COMMAND_RUN,
        SPAN_VERIFICATION_RUN,
    ]

    mission_id = uuid4()
    task_id = uuid4()

    for span_name in spans_to_test:
        with start_span(
            span_name,
            mission_id=mission_id,
            task_id=task_id,
            agent_role="backend_engineer",
            attributes={"custom_attr": "ok"},
        ) as s:
            assert s.is_recording()

    finished = get_in_memory_spans()
    assert len(finished) == len(spans_to_test)
    recorded_names = [s.name for s in finished]
    for name in spans_to_test:
        assert name in recorded_names


def test_span_boundary_attributes_and_secret_scrubbing():
    """Spans attach boundary attributes and SecretScrubbingSpanProcessor redacts secrets."""
    mission_id = uuid4()
    task_id = uuid4()

    with start_span(
        SPAN_AGENT_REACT_LOOP,
        mission_id=mission_id,
        task_id=task_id,
        agent_role="backend_engineer",
        attributes={
            "api_key": "AIzaSyD-secret12345678901234567890",
            "auth_token": "sk-123456789012345678901234567890",
            "nested_info": "User sk-abcdef12345678901234567890 password was exposed",
            "safe_metric": 42,
        },
    ):
        pass

    finished = get_in_memory_spans()
    assert len(finished) == 1
    span = finished[0]
    attrs = span.attributes
    assert attrs is not None

    # Check boundary attributes
    assert attrs["mission_id"] == str(mission_id)
    assert attrs["task_id"] == str(task_id)
    assert attrs["agent_role"] == "backend_engineer"
    assert attrs["safe_metric"] == "42"

    # Check secret redaction on sensitive keys
    assert attrs["api_key"] == "[REDACTED_SPAN_ATTR]"
    assert attrs["auth_token"] == "[REDACTED_SPAN_ATTR]"

    # Check secret redaction inside string values
    assert "sk-" not in str(attrs["nested_info"])
    assert "[REDACTED_API_TOKEN]" in str(attrs["nested_info"])


# ==============================================================================
# 2. W3C traceparent Propagation Tests
# ==============================================================================
def test_traceparent_injection_and_extraction():
    """Trace context correctly injects and extracts W3C traceparent headers."""
    carrier: dict[str, str] = {}

    with start_span(SPAN_MISSION_EXECUTE, mission_id="test-m"):
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        assert trace_id is not None
        assert span_id is not None
        assert len(trace_id) == 32
        assert len(span_id) == 16

        inject_trace_context(carrier)
        assert "traceparent" in carrier
        tp = carrier["traceparent"]
        assert tp.startswith("00-")
        assert trace_id in tp
        assert span_id in tp

    # Extract context and verify trace identity matches
    extracted_ctx = extract_trace_context(carrier)
    assert extracted_ctx is not None
    parsed = parse_traceparent(carrier["traceparent"])
    assert parsed is not None
    extracted_trace_id, extracted_span_id, sampled = parsed
    assert extracted_trace_id == trace_id
    assert extracted_span_id == span_id
    assert sampled is True


def test_parse_traceparent_validation():
    """parse_traceparent strictly validates W3C headers and rejects invalid formats."""
    # Valid
    valid_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    res = parse_traceparent(valid_tp)
    assert res is not None
    tid, sid, sampled = res
    assert tid == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert sid == "00f067aa0ba902b7"
    assert sampled is True

    # Invalid: non-version 00
    assert parse_traceparent("01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01") is None

    # Invalid: all zeros trace_id
    assert parse_traceparent("00-00000000000000000000000000000000-00f067aa0ba902b7-01") is None

    # Invalid: all zeros span_id
    assert parse_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01") is None

    # Invalid: malformed characters or length
    assert parse_traceparent("invalid-traceparent") is None
    assert parse_traceparent("") is None


@pytest.mark.asyncio
async def test_fastapi_trace_propagation_middleware():
    """TracePropagationMiddleware extracts incoming traceparent and echoes it in responses."""
    app = create_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    incoming_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    response = await client.get("/health", headers={"traceparent": incoming_tp})
    assert response.status_code == 200
    assert "traceparent" in response.headers
    # Response traceparent must preserve the trace ID
    assert "4bf92f3577b34da6a3ce929d0e0e4736" in response.headers["traceparent"]


# ==============================================================================
# 3. Structured Audit Logger Tests
# ==============================================================================
def test_audit_logger_jsonl_output_and_digest(tmp_path: Path):
    """AuditLogger writes valid JSONL records with UTC timestamp and SHA-256 tamper digest."""
    log_file = tmp_path / "security_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    mission_id = uuid4()
    task_id = uuid4()

    event = logger.log_event(
        event_type=AUDIT_TASK_ATTEMPT_STARTED,
        mission_id=mission_id,
        task_id=task_id,
        agent_role="backend_engineer",
        payload={"attempt_number": 1, "action": "checkout_worktree"},
    )

    assert event["event_type"] == AUDIT_TASK_ATTEMPT_STARTED
    assert event["mission_id"] == str(mission_id)
    assert event["task_id"] == str(task_id)
    assert "sha256" in event
    assert len(event["sha256"]) == 64

    # Verify JSONL log file integrity
    verified_records = AuditLogger.verify_log_file(log_file)
    assert len(verified_records) == 1
    assert verified_records[0]["event_type"] == AUDIT_TASK_ATTEMPT_STARTED
    assert verified_records[0]["sha256"] == compute_payload_digest(verified_records[0]["payload"])


def test_audit_logger_tamper_detection(tmp_path: Path):
    """AuditLogger.verify_log_file detects modified payloads and raises AuditLoggingError."""
    log_file = tmp_path / "tampered_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    logger.log_event(
        event_type=AUDIT_VERIFICATION_PASSED,
        mission_id=uuid4(),
        outcome="PASSED",
        payload={"exit_code": 0, "tests_passed": 10},
    )

    # Tamper with file content
    content = log_file.read_text(encoding="utf-8")
    tampered_content = content.replace('"tests_passed": 10', '"tests_passed": 999')
    log_file.write_text(tampered_content, encoding="utf-8")

    with pytest.raises(AuditLoggingError, match="Audit log digest mismatch"):
        AuditLogger.verify_log_file(log_file)


def test_audit_logger_secret_redaction(tmp_path: Path):
    """AuditLogger sanitizes credentials before writing to audit records."""
    log_file = tmp_path / "sanitized_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    logger.log_event(
        event_type=AUDIT_DIFF_GENERATED,
        mission_id=uuid4(),
        payload={
            "token": "sk-123456789012345678901234567890",
            "api_key": "AIzaSyD-123456789012345678901234567890",
            "password": "SuperSecretPassword123!",
            "message": "Connected with sk-abcdef12345678901234567890 securely",
        },
    )

    records = logger.get_records()
    assert len(records) == 1
    p = records[0]["payload"]
    assert p["token"] == "[REDACTED_SECRET]"
    assert p["api_key"] == "[REDACTED_SECRET]"
    assert p["password"] == "[REDACTED_SECRET]"
    assert "sk-" not in p["message"]
    assert "[REDACTED_API_TOKEN]" in p["message"]


def test_audit_logger_fail_closed_on_io_error(tmp_path: Path):
    """AuditLogger raises AuditLoggingError fail-closed if write fails."""
    # Point logger to a directory instead of a file to trigger an IOError
    bad_path = tmp_path / "is_a_directory"
    bad_path.mkdir()

    logger = AuditLogger(log_path=bad_path)
    with pytest.raises(AuditLoggingError, match="Audit log write failed"):
        logger.log_event(event_type=AUDIT_TASK_ATTEMPT_STARTED, mission_id=uuid4())


# ==============================================================================
# 4. Delivery Gate Enforcement Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_delivery_gate_allowed_with_valid_verification(test_uow_factory):
    """Delivery gate allows transition when VerificationRecord is valid, PASSED, and matching."""
    async with test_uow_factory() as test_uow:
        org_id = uuid4()
        await test_uow.organizations.create(org_id=org_id, name="Gate Org", slug=f"gate-{org_id.hex[:8]}")

        proj_id = uuid4()
        proj = ProjectModel(id=proj_id, org_id=org_id, name="Gate Project", slug=f"proj-{proj_id.hex[:8]}")
        test_uow.session.add(proj)
        await test_uow.session.flush()

        mission_id = uuid4()
        mission = MissionModel(
            id=mission_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Delivery Gate Mission",
            state=MissionState.RUNNING,
            active_plan_version=1,
        )
        test_uow.session.add(mission)
        await test_uow.session.flush()

        plan_id = uuid4()
        await test_uow.tasks.create_plan(
            plan_id=plan_id, mission_id=mission_id, version=1, status=TaskPlanStatus.APPROVED
        )

        task_id = uuid4()
        await test_uow.tasks.create_task(
            task_id=task_id,
            task_plan_id=plan_id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-1",
            title="Delivery Candidate",
            description="Delivery candidate task",
            assigned_role=AgentRole.BACKEND_ENGINEER.value,
        )
        await test_uow.tasks.update_status(task_id=task_id, new_state=TaskState.COMPLETED)

        attempt_id = uuid4()
        await test_uow.tasks.create_attempt(
            task_id=task_id,
            attempt_number=1,
            state=AttemptState.SUCCEEDED,
            attempt_id=attempt_id,
        )

        diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
        patch_hash = hashlib.sha256(diff.encode()).hexdigest()

        result = TaskExecutionResult(
            task_id=task_id,
            attempt_number=1,
            status=AttemptState.SUCCEEDED,
            unified_diff=diff,
            base_commit="main-commit-1",
            worker_id="test-worker",
            fencing_token=1,
        )
        from syntra.domain.entities import ArtifactType
        from syntra.persistence.artifact_store import store_artifact

        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title="Execution attempt 1",
            content=result.model_dump_json(),
            type=ArtifactType.TEST_REPORT,
        )

        # Add code reviewer attestation
        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title=f"Review by {AgentRole.CODE_REVIEWER.value}",
            content=json.dumps({"review_verdict": "APPROVED", "target_diff_hash": patch_hash}),
            type=ArtifactType.TEST_REPORT,
        )
        await test_uow.commit()

        # Create matching VerificationRecord
        v_rec = VerificationRecord(
            id=uuid4(),
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            plan_version=1,
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

        # Test delivery gate
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
            "mission_version": 1,
            "selected_results": [
                {
                    "task_id": str(task_id),
                    "attempt_id": str(attempt_id),
                    "patch_hash": patch_hash,
                }
            ],
        }

        # Should succeed without raising
        await service.verify_delivery_gate(test_uow, state)


@pytest.mark.asyncio
async def test_delivery_gate_blocks_missing_verification_record(test_uow_factory):
    """Delivery gate raises DeliveryBlockedError when VerificationRecord is missing."""
    async with test_uow_factory() as test_uow:
        org_id = uuid4()
        await test_uow.organizations.create(org_id=org_id, name="Gate Org 2", slug=f"gate2-{org_id.hex[:8]}")

        proj_id = uuid4()
        proj = ProjectModel(id=proj_id, org_id=org_id, name="Gate Project 2", slug=f"proj2-{proj_id.hex[:8]}")
        test_uow.session.add(proj)
        await test_uow.session.flush()

        mission_id = uuid4()
        mission = MissionModel(
            id=mission_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Delivery Gate Mission 2",
            state=MissionState.RUNNING,
            active_plan_version=1,
        )
        test_uow.session.add(mission)
        await test_uow.session.flush()

        plan_id = uuid4()
        await test_uow.tasks.create_plan(
            plan_id=plan_id, mission_id=mission_id, version=1, status=TaskPlanStatus.APPROVED
        )

        task_id = uuid4()
        await test_uow.tasks.create_task(
            task_id=task_id,
            task_plan_id=plan_id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-1",
            title="Candidate",
            description="Candidate task",
            assigned_role=AgentRole.BACKEND_ENGINEER.value,
        )
        await test_uow.tasks.update_status(task_id=task_id, new_state=TaskState.COMPLETED)

        attempt_id = uuid4()
        await test_uow.tasks.create_attempt(
            task_id=task_id,
            attempt_number=1,
            state=AttemptState.SUCCEEDED,
            attempt_id=attempt_id,
        )

        diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
        patch_hash = hashlib.sha256(diff.encode()).hexdigest()

        from syntra.persistence.artifact_store import store_artifact

        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title="Execution attempt 1",
            content=TaskExecutionResult(
                task_id=task_id,
                attempt_number=1,
                status=AttemptState.SUCCEEDED,
                unified_diff=diff,
                base_commit="main-commit-1",
                worker_id="test-worker",
                fencing_token=1,
            ).model_dump_json(),
            type=ArtifactType.TEST_REPORT,
        )
        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title=f"Review by {AgentRole.CODE_REVIEWER.value}",
            content=json.dumps({"review_verdict": "APPROVED", "target_diff_hash": patch_hash}),
            type=ArtifactType.TEST_REPORT,
        )
        await test_uow.commit()

        # Note: NO VerificationRecord is created!
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
            "mission_version": 1,
            "selected_results": [
                {
                    "task_id": str(task_id),
                    "attempt_id": str(attempt_id),
                    "patch_hash": patch_hash,
                }
            ],
        }

        with pytest.raises(DeliveryBlockedError, match="No VerificationRecord found"):
            await service.verify_delivery_gate(test_uow, state)


@pytest.mark.asyncio
async def test_delivery_gate_blocks_mismatched_patch_hash(test_uow_factory):
    """Delivery gate raises DeliveryBlockedError when VerificationRecord patch_hash does not match."""
    async with test_uow_factory() as test_uow:
        org_id = uuid4()
        await test_uow.organizations.create(org_id=org_id, name="Gate Org 3", slug=f"gate3-{org_id.hex[:8]}")

        proj_id = uuid4()
        proj = ProjectModel(id=proj_id, org_id=org_id, name="Gate Project 3", slug=f"proj3-{proj_id.hex[:8]}")
        test_uow.session.add(proj)
        await test_uow.session.flush()

        mission_id = uuid4()
        mission = MissionModel(
            id=mission_id,
            org_id=org_id,
            project_id=proj_id,
            objective="Delivery Gate Mission 3",
            state=MissionState.RUNNING,
            active_plan_version=1,
        )
        test_uow.session.add(mission)
        await test_uow.session.flush()

        plan_id = uuid4()
        await test_uow.tasks.create_plan(
            plan_id=plan_id, mission_id=mission_id, version=1, status=TaskPlanStatus.APPROVED
        )

        task_id = uuid4()
        await test_uow.tasks.create_task(
            task_id=task_id,
            task_plan_id=plan_id,
            mission_id=mission_id,
            org_id=org_id,
            identifier="TASK-1",
            title="Candidate",
            description="Candidate task",
            assigned_role=AgentRole.BACKEND_ENGINEER.value,
        )
        await test_uow.tasks.update_status(task_id=task_id, new_state=TaskState.COMPLETED)

        attempt_id = uuid4()
        await test_uow.tasks.create_attempt(
            task_id=task_id,
            attempt_number=1,
            state=AttemptState.SUCCEEDED,
            attempt_id=attempt_id,
        )

        diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
        patch_hash = hashlib.sha256(diff.encode()).hexdigest()

        from syntra.persistence.artifact_store import store_artifact

        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title="Execution attempt 1",
            content=TaskExecutionResult(
                task_id=task_id,
                attempt_number=1,
                status=AttemptState.SUCCEEDED,
                unified_diff=diff,
                base_commit="main-commit-1",
                worker_id="test-worker",
                fencing_token=1,
            ).model_dump_json(),
            type=ArtifactType.TEST_REPORT,
        )
        await store_artifact(
            test_uow,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            title=f"Review by {AgentRole.CODE_REVIEWER.value}",
            content=json.dumps({"review_verdict": "APPROVED", "target_diff_hash": patch_hash}),
            type=ArtifactType.TEST_REPORT,
        )

        # VerificationRecord has DIFFERENT patch hash
        v_rec = VerificationRecord(
            id=uuid4(),
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            task_attempt_id=attempt_id,
            plan_version=1,
            status=VerificationStatus.PASSED,
            clean_base_commit="main-commit-1",
            patch_hash="a" * 64,
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
            "mission_version": 1,
            "selected_results": [
                {
                    "task_id": str(task_id),
                    "attempt_id": str(attempt_id),
                    "patch_hash": patch_hash,
                }
            ],
        }

        with pytest.raises(DeliveryBlockedError, match="Patch hash mismatch"):
            await service.verify_delivery_gate(test_uow, state)
