"""Pydantic v2 schemas and models for independent verification requests and results."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from syntra.domain.entities import AgentRole, VerificationEvidence, VerificationRecord, VerificationStatus


class VerificationRequest(BaseModel):
    """Authoritative request to verify a unified diff patch out-of-band."""

    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    mission_id: UUID
    task_id: UUID
    task_attempt_id: UUID
    plan_version: int = Field(ge=1)
    patch: str = Field(min_length=1)
    clean_base_commit: str = Field(min_length=1)
    implementer_role: AgentRole
    implementer_invocation_id: UUID
    verifier_id: UUID
    trace_id: str | None = None
    span_id: str | None = None


class VerificationResult(BaseModel):
    """Result of an out-of-band hermetic verification run."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    status: VerificationStatus
    record: VerificationRecord
    evidence: VerificationEvidence
    reason: str | None = None


class ProtectedFileEntry(BaseModel):
    """Metadata entry for an immutable protected test file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int


class ProtectedTestSuiteManifestModel(BaseModel):
    """Cryptographic manifest of protected test suites."""

    model_config = ConfigDict(extra="forbid")

    manifest_hash: str
    protected_files: dict[str, str] = Field(default_factory=dict)
    registered_patterns: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
