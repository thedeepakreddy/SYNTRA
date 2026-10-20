"""Independent Verification Service coordinating hermetic verification and tamper-evident records."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Sequence
from uuid import UUID, uuid4

from syntra.domain.entities import (
    AgentRole,
    VerificationRecord,
    VerificationStatus,
    compute_verification_signature,
    verify_verification_signature,
)
from syntra.domain.exceptions import (
    VerificationFailedError,
    VerificationTamperedError,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.verification.hermetic_runner import HermeticVerificationRunner
from syntra.verification.models import VerificationRequest, VerificationResult
from syntra.verification.registry import ProtectedTestRegistry


def require_independent_verifier(
    implementer_role: AgentRole,
    implementer_invocation_id: UUID,
    verifier_id: UUID,
) -> None:
    """Enforce separation of powers: implementer cannot verify its own patch."""
    if implementer_invocation_id == verifier_id:
        raise ValueError("Implementer invocation cannot act as independent verifier for its own patch")
    if (
        implementer_role
        in {
            AgentRole.BACKEND_ENGINEER,
            AgentRole.FRONTEND_ENGINEER,
            AgentRole.DEVOPS_ENGINEER,
        }
        and implementer_invocation_id == verifier_id
    ):
        raise ValueError("Implementer role cannot self-certify patch deliverables")


class IndependentVerificationService:
    """Out-of-band verification service providing cryptographic proof of deliverable correctness."""

    def __init__(
        self,
        registry: ProtectedTestRegistry | None = None,
        runner: HermeticVerificationRunner | None = None,
        default_secret: str = "syntra-verification-hmac-secret-v1",
    ) -> None:
        self.registry = registry or ProtectedTestRegistry()
        self.runner = runner or HermeticVerificationRunner(registry=self.registry)
        self.default_secret = default_secret

    async def verify_patch(
        self,
        uow: SqlAlchemyUnitOfWork,
        request: VerificationRequest,
        repo_root: Path | str,
        test_command: Sequence[str] = ("pytest", "-v"),
        secret: str | None = None,
    ) -> VerificationResult:
        """Execute independent out-of-band verification and persist a cryptographic record.

        Raises:
            ValueError: If separation of powers is violated.
            ProtectedTestViolationError: If patch alters protected tests.
        """
        # 1. Enforce separation of powers
        require_independent_verifier(
            implementer_role=request.implementer_role,
            implementer_invocation_id=request.implementer_invocation_id,
            verifier_id=request.verifier_id,
        )

        patch_hash = hashlib.sha256(request.patch.encode("utf-8")).hexdigest()
        signing_secret = secret or self.default_secret

        from syntra.observability.audit_logger import (
            AUDIT_VERIFICATION_FAILED,
            AUDIT_VERIFICATION_INITIATED,
            AUDIT_VERIFICATION_PASSED,
            get_audit_logger,
        )
        from syntra.observability.propagation import get_current_span_id, get_current_trace_id
        from syntra.observability.tracer import SPAN_VERIFICATION_RUN, start_span

        # Log verification initiation audit event
        get_audit_logger().log_event(
            AUDIT_VERIFICATION_INITIATED,
            mission_id=request.mission_id,
            task_id=request.task_id,
            payload={
                "task_attempt_id": str(request.task_attempt_id),
                "plan_version": request.plan_version,
                "patch_hash": patch_hash,
            },
        )

        with start_span(
            SPAN_VERIFICATION_RUN,
            mission_id=str(request.mission_id),
            task_id=str(request.task_id),
            attributes={"patch_hash": patch_hash, "plan_version": request.plan_version},
        ):
            # 2. Fast-path protected test mutation check
            self.registry.check_patch(request.patch)

            # 3. Compute baseline protected test manifest
            manifest = self.registry.compute_manifest(repo_root)

            # 4. Execute hermetic runner against clean worktree
            evidence = await self.runner.run_verification(
                repo_root=repo_root,
                clean_base_commit=request.clean_base_commit,
                patch=request.patch,
                test_command=test_command,
                manifest=manifest,
            )

            # 5. Determine verification status
            if evidence.exit_code == 0 and evidence.tests_failed == 0 and evidence.tests_errored == 0:
                status = VerificationStatus.PASSED
            else:
                status = VerificationStatus.FAILED

            # 6. Compute cryptographic HMAC-SHA256 signature
            signature = compute_verification_signature(
                secret=signing_secret,
                org_id=request.org_id,
                mission_id=request.mission_id,
                task_id=request.task_id,
                task_attempt_id=request.task_attempt_id,
                patch_hash=patch_hash,
                clean_base_commit=request.clean_base_commit,
                protected_test_suite_hash=manifest.manifest_hash,
                status=status.value,
                exit_code=evidence.exit_code,
            )

            resolved_trace_id = request.trace_id or get_current_trace_id()
            resolved_span_id = request.span_id or get_current_span_id()

            record = VerificationRecord(
                id=uuid4(),
                org_id=request.org_id,
                mission_id=request.mission_id,
                task_id=request.task_id,
                task_attempt_id=request.task_attempt_id,
                plan_version=request.plan_version,
                status=status,
                clean_base_commit=request.clean_base_commit,
                patch_hash=patch_hash,
                protected_test_suite_hash=manifest.manifest_hash,
                evidence=evidence,
                verifier_signature=signature,
                trace_id=resolved_trace_id,
                span_id=resolved_span_id,
            )

            # 7. Persist record via Unit of Work
            await uow.verifications.create_record(record)

            # 8. Emit transactional outbox event
            outbox_event_type = "VERIFICATION_PASSED" if status == VerificationStatus.PASSED else "VERIFICATION_FAILED"
            uow.outbox.stage_event(
                event_type=outbox_event_type,
                payload={
                    "verification_id": str(record.id),
                    "org_id": str(record.org_id),
                    "mission_id": str(record.mission_id),
                    "task_id": str(record.task_id),
                    "task_attempt_id": str(record.task_attempt_id),
                    "status": status.value,
                    "exit_code": evidence.exit_code,
                    "patch_hash": patch_hash,
                    "signature": signature,
                },
            )

            # 9. Emit audit event
            audit_event_type = (
                AUDIT_VERIFICATION_PASSED if status == VerificationStatus.PASSED else AUDIT_VERIFICATION_FAILED
            )
            get_audit_logger().log_event(
                audit_event_type,
                mission_id=request.mission_id,
                task_id=request.task_id,
                outcome=status.value,
                payload={
                    "verification_id": str(record.id),
                    "exit_code": evidence.exit_code,
                    "tests_passed": evidence.tests_passed,
                    "tests_failed": evidence.tests_failed,
                    "patch_hash": patch_hash,
                },
            )

        return VerificationResult(
            status=status,
            record=record,
            evidence=evidence,
            reason=evidence.error_message,
        )

    @classmethod
    def verify_record_integrity(cls, record: VerificationRecord, secret: str) -> None:
        """Verify the cryptographic signature of a single verification record.

        Raises:
            VerificationTamperedError: If the record's signature is invalid or tampered.
        """
        valid = verify_verification_signature(
            secret=secret,
            expected_signature=record.verifier_signature,
            org_id=record.org_id,
            mission_id=record.mission_id,
            task_id=record.task_id,
            task_attempt_id=record.task_attempt_id,
            patch_hash=record.patch_hash,
            clean_base_commit=record.clean_base_commit,
            protected_test_suite_hash=record.protected_test_suite_hash,
            status=record.status.value,
            exit_code=record.evidence.exit_code,
        )
        if not valid:
            raise VerificationTamperedError(
                f"Cryptographic signature mismatch: signature verification failed for verification record {record.id} (task {record.task_id})"
            )

    async def verify_mission(
        self,
        uow: SqlAlchemyUnitOfWork,
        org_id: UUID,
        mission_id: UUID,
        secret: str | None = None,
    ) -> list[VerificationRecord]:
        """Verify that all tasks for the mission possess valid, tamper-free verification records."""
        records_models = await uow.verifications.get_records_for_mission(org_id, mission_id)
        if not records_models:
            raise VerificationFailedError(f"No verification records found for mission {mission_id}")

        signing_secret = secret or self.default_secret
        verified_records: list[VerificationRecord] = []

        for model in records_models:
            rec = model.to_domain()
            # Verify cryptographic signature
            self.verify_record_integrity(rec, secret=signing_secret)
            if rec.status != VerificationStatus.PASSED:
                raise VerificationFailedError(
                    f"Task {rec.task_id} failed independent verification (status: {rec.status})"
                )
            verified_records.append(rec)

        return verified_records
