"""Structured security audit logger emitting tamper-evident JSONL events with fail-closed semantics."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from syntra.core.redactor import SecretRedactor
from syntra.domain.exceptions import AuditLoggingError
from syntra.observability.propagation import get_current_trace_id

# Canonical audit event types mandated by Phase 12 architecture
AUDIT_TASK_ATTEMPT_STARTED = "TASK_ATTEMPT_STARTED"
AUDIT_DIFF_GENERATED = "DIFF_GENERATED"
AUDIT_REVIEW_ATTESTATION_ISSUED = "REVIEW_ATTESTATION_ISSUED"
AUDIT_VERIFICATION_INITIATED = "VERIFICATION_INITIATED"
AUDIT_VERIFICATION_PASSED = "VERIFICATION_PASSED"
AUDIT_VERIFICATION_FAILED = "VERIFICATION_FAILED"
AUDIT_DELIVERY_APPROVED = "DELIVERY_APPROVED"
AUDIT_DELIVERY_BLOCKED = "DELIVERY_BLOCKED"
AUDIT_POLICY_VIOLATION_REJECTED = "POLICY_VIOLATION_REJECTED"
AUDIT_PROTECTED_TEST_VIOLATION_REJECTED = "PROTECTED_TEST_VIOLATION_REJECTED"
AUDIT_SECRET_REDACTION_APPLIED = "SECRET_REDACTION_APPLIED"

VALID_AUDIT_EVENTS = {
    AUDIT_TASK_ATTEMPT_STARTED,
    AUDIT_DIFF_GENERATED,
    AUDIT_REVIEW_ATTESTATION_ISSUED,
    AUDIT_VERIFICATION_INITIATED,
    AUDIT_VERIFICATION_PASSED,
    AUDIT_VERIFICATION_FAILED,
    AUDIT_DELIVERY_APPROVED,
    AUDIT_DELIVERY_BLOCKED,
    AUDIT_POLICY_VIOLATION_REJECTED,
    AUDIT_PROTECTED_TEST_VIOLATION_REJECTED,
    AUDIT_SECRET_REDACTION_APPLIED,
}


def compute_payload_digest(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of sanitized payload for tamper detection."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class AuditLogger:
    """Thread-safe, fail-closed structured audit logger writing JSONL records."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        self.log_path = Path(log_path) if log_path else None
        self._lock = threading.Lock()
        self._in_memory_records: list[dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        mission_id: str | UUID,
        outcome: str = "SUCCESS",
        task_id: str | UUID | None = None,
        agent_role: str | None = None,
        trace_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a security audit event with automatic secret redaction and tamper detection.

        Fails closed: if writing to disk or recording raises an error, raises AuditLoggingError.
        """
        try:
            # 1. Resolve trace_id if omitted
            resolved_trace_id = trace_id or get_current_trace_id()

            # 2. Deeply scrub secrets from payload
            raw_payload = payload or {}
            scrubbed_payload = SecretRedactor.redact_sensitive_data(raw_payload)

            # 3. Compute SHA-256 payload digest for tamper detection
            digest = compute_payload_digest(scrubbed_payload)

            # 4. Construct immutable audit record
            record: dict[str, Any] = {
                "event_type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "trace_id": resolved_trace_id,
                "mission_id": str(mission_id),
                "task_id": str(task_id) if task_id else None,
                "agent_role": str(agent_role) if agent_role else None,
                "outcome": outcome,
                "sha256": digest,
                "payload": scrubbed_payload,
            }

            # 5. Thread-safe write to disk and memory buffer
            with self._lock:
                self._in_memory_records.append(record)
                if self.log_path:
                    self.log_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record, sort_keys=True) + "\n")
                        f.flush()

            return record

        except Exception as exc:
            # Fail closed: never silently swallow audit logging failures
            if isinstance(exc, AuditLoggingError):
                raise
            raise AuditLoggingError(f"Audit log write failed for event {event_type}: {exc}") from exc

    def get_records(self) -> list[dict[str, Any]]:
        """Return a copy of the in-memory audit record buffer."""
        with self._lock:
            return list(self._in_memory_records)

    def clear(self) -> None:
        """Clear the in-memory audit buffer."""
        with self._lock:
            self._in_memory_records.clear()

    @staticmethod
    def verify_log_file(file_path: Path | str) -> list[dict[str, Any]]:
        """Verify the integrity of a JSONL audit log file on disk.

        Validates JSON structure, required fields, and recomputes the SHA-256 digest.
        Raises AuditLoggingError if tampering or corruption is detected.
        """
        path = Path(file_path)
        if not path.exists():
            raise AuditLoggingError(f"Audit log file not found: {path}")

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    entry = json.loads(clean_line)
                except Exception as exc:
                    raise AuditLoggingError(f"Corrupt JSON at line {line_no} in {path}: {exc}") from exc

                for req_key in ("event_type", "timestamp", "mission_id", "outcome", "sha256", "payload"):
                    if req_key not in entry:
                        raise AuditLoggingError(f"Missing required key '{req_key}' at line {line_no} in {path}")

                expected_digest = compute_payload_digest(entry["payload"])
                if entry["sha256"] != expected_digest:
                    raise AuditLoggingError(
                        f"Audit log digest mismatch at line {line_no}: recorded {entry['sha256']} != computed {expected_digest}"
                    )
                records.append(entry)

        return records


_default_audit_logger: AuditLogger | None = None


def get_audit_logger(log_path: Path | str | None = None) -> AuditLogger:
    """Return the global audit logger instance, or create one for the specified path."""
    global _default_audit_logger
    if log_path is not None:
        return AuditLogger(log_path=log_path)
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger


def set_global_audit_logger(logger: AuditLogger | None) -> None:
    """Set the global default audit logger instance (for test isolation)."""
    global _default_audit_logger
    _default_audit_logger = logger
