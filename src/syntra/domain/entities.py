"""Pure domain entities, value objects, and enumerations for SYNTRA.

Zero framework or database dependencies.
"""

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# ==============================================================================
# Enumerations
# ==============================================================================
class MembershipRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class AgentRole(str, Enum):
    PRODUCT_MANAGER = "product_manager"
    SOFTWARE_ARCHITECT = "software_architect"
    ENGINEERING_MANAGER = "engineering_manager"
    BACKEND_ENGINEER = "backend_engineer"
    FRONTEND_ENGINEER = "frontend_engineer"
    QA_ENGINEER = "qa_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    SECURITY_REVIEWER = "security_reviewer"
    CODE_REVIEWER = "code_reviewer"
    DEBUGGING_SPECIALIST = "debugging_specialist"


class MissionState(str, Enum):
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    REPLANNING = "REPLANNING"
    VERIFYING = "VERIFYING"
    AWAITING_DELIVERY_APPROVAL = "AWAITING_DELIVERY_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY = "security"
    INTERFACE = "interface"


class ADRStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class TaskPlanStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class TaskState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AttemptState(str, Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    AWAITING_TOOL = "AWAITING_TOOL"
    EVALUATING = "EVALUATING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class SandboxStatus(str, Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class ArtifactType(str, Enum):
    PRD = "PRD"
    ARCHITECTURE_SPEC = "ARCHITECTURE_SPEC"
    UNIFIED_DIFF = "UNIFIED_DIFF"
    TEST_REPORT = "TEST_REPORT"
    SECURITY_REPORT = "SECURITY_REPORT"
    LOG_ARCHIVE = "LOG_ARCHIVE"


class VerificationVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class MCPTransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    STREAMABLE_HTTP = "streamable_http"


class TrustClassification(str, Enum):
    LOCAL_TRUSTED = "LOCAL_TRUSTED"
    VERIFIED_ENTERPRISE = "VERIFIED_ENTERPRISE"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"


class AuthPolicyType(str, Enum):
    NONE = "NONE"
    BEARER_TOKEN = "BEARER_TOKEN"
    API_KEY = "API_KEY"
    MTLS = "MTLS"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    QUARANTINED = "QUARANTINED"


class ActionClassification(str, Enum):
    READ_ONLY = "READ_ONLY"
    SANDBOX_WRITE = "SANDBOX_WRITE"
    SANDBOX_EXECUTION = "SANDBOX_EXECUTION"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    SENSITIVE_EXTERNAL_ACTION = "SENSITIVE_EXTERNAL_ACTION"


class ApprovalActionType(str, Enum):
    INITIAL_PLAN = "INITIAL_PLAN"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    EXTERNAL_REPOSITORY_WRITE = "EXTERNAL_REPOSITORY_WRITE"
    PULL_REQUEST_CREATION = "PULL_REQUEST_CREATION"
    PROTECTED_BRANCH_MERGE = "PROTECTED_BRANCH_MERGE"
    DEPLOYMENT = "DEPLOYMENT"
    BUDGET_INCREASE = "BUDGET_INCREASE"
    SECURITY_POLICY_CHANGE = "SECURITY_POLICY_CHANGE"
    DELIVERY_APPROVAL = "DELIVERY_APPROVAL"


class ApprovalDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class MemoryScope(str, Enum):
    EXECUTION = "EXECUTION"
    PROJECT = "PROJECT"
    ORGANIZATION = "ORGANIZATION"


# ==============================================================================
# Domain Entities
# ==============================================================================
@dataclass
class Organization:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    email: str = ""
    full_name: str = ""
    is_active: bool = True
    is_service_account: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Membership:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    role: MembershipRole = MembershipRole.ENGINEER
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Project:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Repository:
    id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    name: str = ""
    clone_url: str = ""
    default_branch: str = "main"
    is_private: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Mission:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    repository_id: UUID | None = None
    objective: str = ""
    state: MissionState = MissionState.DRAFT
    autonomy_mode: str = "semi_autonomous"
    active_plan_version: int = 1
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Requirement:
    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    identifier: str = ""
    type: RequirementType = RequirementType.FUNCTIONAL
    title: str = ""
    description: str = ""
    acceptance_criteria: list[dict[str, Any]] = field(default_factory=list)
    is_ambiguous: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ArchitectureDecision:
    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    adr_number: int = 1
    title: str = ""
    status: ADRStatus = ADRStatus.PROPOSED
    context: str = ""
    decision: str = ""
    consequences: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TaskPlan:
    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    plan_version: int = 1
    status: TaskPlanStatus = TaskPlanStatus.DRAFT
    total_tasks: int = 0
    estimated_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Task:
    id: UUID = field(default_factory=uuid4)
    task_plan_id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    identifier: str = ""
    title: str = ""
    description: str = ""
    assigned_role: str = ""
    state: TaskState = TaskState.PENDING
    priority: int = 0
    max_attempts: int = 3
    attempt_count: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TaskDependency:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    depends_on_task_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TaskAttempt:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    attempt_number: int = 1
    state: AttemptState = AttemptState.INITIALIZING
    exit_code: int | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass
class AgentRun:
    id: UUID = field(default_factory=uuid4)
    task_attempt_id: UUID = field(default_factory=uuid4)
    agent_role: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Artifact:
    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    type: ArtifactType = ArtifactType.PRD
    title: str = ""
    current_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ArtifactVersion:
    id: UUID = field(default_factory=uuid4)
    artifact_id: UUID = field(default_factory=uuid4)
    version: int = 1
    storage_path: str = ""
    sha256_checksum: str = ""
    size_bytes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VerificationRun:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    artifact_version_id: UUID = field(default_factory=uuid4)
    verdict: VerificationVerdict = VerificationVerdict.PASS
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_percentage: Decimal | None = None
    raw_output: str | None = None
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Approval:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    action_type: str = ""
    target_resource: str = ""
    action_digest: str = ""
    mission_version: int = 1
    decision: ApprovalDecision = ApprovalDecision.PENDING
    feedback: str | None = None
    resolved_by: UUID | None = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None


@dataclass
class Budget:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    mission_id: UUID | None = None
    max_tokens: int = 1_000_000
    max_cost_usd: Decimal = field(default_factory=lambda: Decimal("50.0000"))
    max_concurrency: int = 4
    max_task_attempts: int = 3
    max_mission_duration_seconds: int = 3600
    reserved_tokens: int = 0
    consumed_tokens: int = 0
    reserved_cost_usd: Decimal = field(default_factory=lambda: Decimal("0.0000"))
    consumed_cost_usd: Decimal = field(default_factory=lambda: Decimal("0.0000"))
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class UsageRecord:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    model_name: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Decimal = field(default_factory=lambda: Decimal("0.000000"))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Event:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    mission_id: UUID | None = None
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    actor_type: str = "system"
    actor_id: str = "orchestrator"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class OutboxEvent:
    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None


@dataclass
class IdempotencyKey:
    key: str = ""
    org_id: UUID = field(default_factory=uuid4)
    response_code: int = 200
    response_body: dict[str, Any] = field(default_factory=dict)
    payload_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MCPServer:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    transport: MCPTransportType = MCPTransportType.STDIO
    trust_classification: TrustClassification = TrustClassification.LOCAL_TRUSTED
    command_or_url: str = ""
    auth_policy: AuthPolicyType = AuthPolicyType.NONE
    allowed_capabilities: list[str] = field(default_factory=list)
    is_enabled: bool = True
    version: str = "1.0.0"
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MCPServerVersion:
    id: UUID = field(default_factory=uuid4)
    server_id: UUID = field(default_factory=uuid4)
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"
    server_info: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MCPConnection:
    connection_id: UUID = field(default_factory=uuid4)
    server_name: str = ""
    transport: MCPTransportType = MCPTransportType.STDIO
    status: str = "DISCONNECTED"
    last_connected_at: datetime | None = None
    last_error: str | None = None
    reconnect_attempts: int = 0


@dataclass
class MCPToolDefinition:
    name: str = ""
    server_name: str = ""
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    action_classification: ActionClassification = ActionClassification.READ_ONLY


@dataclass
class MCPToolVersion:
    id: UUID = field(default_factory=uuid4)
    mcp_server_id: UUID = field(default_factory=uuid4)
    tool_name: str = ""
    version: str = "1.0.0"
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    action_classification: ActionClassification = ActionClassification.READ_ONLY
    sha256_checksum: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MCPToolSchemaVersion:
    id: UUID = field(default_factory=uuid4)
    server_name: str = ""
    tool_name: str = ""
    version: str = "1.0.0"
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    schema_hash: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MCPInvocation:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    mission_id: UUID | None = None
    task_id: UUID | None = None
    server_name: str = ""
    tool_name: str = ""
    caller_role: str = ""
    caller_user_id: UUID | None = None
    arguments_scrubbed: dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"
    error_message: str | None = None
    result_summary: str | None = None
    result_hash: str | None = None
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass
class MCPInvocationResult:
    invocation_id: UUID = field(default_factory=uuid4)
    status: str = "SUCCESS"
    content: list[dict[str, Any]] = field(default_factory=list)
    raw_output: str | None = None
    is_error: bool = False
    error_code: int | None = None
    error_message: str | None = None
    duration_ms: int = 0
    result_hash: str | None = None


@dataclass
class Skill:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SkillVersion:
    id: UUID = field(default_factory=uuid4)
    skill_id: UUID = field(default_factory=uuid4)
    version: str = "1.0.0"
    manifest_yaml: str = ""
    instruction_markdown: str = ""
    compatible_roles: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class CapabilityGrant:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    agent_role: str = ""
    tool_name_pattern: str = ""
    is_allowed: bool = True
    requires_approval: bool = False
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class WorkerJobMetadata:
    id: UUID = field(default_factory=uuid4)
    task_attempt_id: UUID = field(default_factory=uuid4)
    worker_id: str = ""
    workspace_path: str = ""
    git_worktree_branch: str = ""
    status: SandboxStatus = SandboxStatus.PROVISIONING
    timeout_seconds: int = 120
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    terminated_at: datetime | None = None


@dataclass
class WorkerLease:
    task_id: UUID = field(default_factory=uuid4)
    worker_id: str = ""
    fencing_token: int = 1
    lease_expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    acquired_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MemoryRecord:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    project_id: UUID | None = None
    scope: MemoryScope = MemoryScope.ORGANIZATION
    category: str = ""
    lesson_key: str = ""
    content: str = ""
    provenance_task_id: UUID | None = None
    confidence_score: Decimal = field(default_factory=lambda: Decimal("1.00"))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = None

    def validate(self) -> None:
        """Validate required fields, supported scopes, provenance, confidence score, and optional embedding."""
        from syntra.domain.exceptions import MemoryValidationError

        if not isinstance(self.id, UUID):
            raise MemoryValidationError(f"Invalid memory id: expected UUID, got {type(self.id).__name__}.")

        if not isinstance(self.org_id, UUID):
            raise MemoryValidationError("Organization ID (org_id) is mandatory and must be a UUID.")

        if not isinstance(self.scope, MemoryScope):
            try:
                self.scope = MemoryScope(self.scope)
            except ValueError:
                raise MemoryValidationError(
                    f"Unsupported memory scope: {self.scope}. Must be one of {[s.value for s in MemoryScope]}."
                )

        if self.scope == MemoryScope.PROJECT and self.project_id is None:
            raise MemoryValidationError("project_id is mandatory when memory scope is PROJECT.")

        if self.scope == MemoryScope.EXECUTION and self.provenance_task_id is None:
            raise MemoryValidationError("provenance_task_id is mandatory when memory scope is EXECUTION.")

        if not self.category or not self.category.strip():
            raise MemoryValidationError("category must be a non-empty string.")

        if len(self.category) > 100:
            raise MemoryValidationError("category cannot exceed 100 characters.")

        if not self.lesson_key or not self.lesson_key.strip():
            raise MemoryValidationError("lesson_key must be a non-empty string.")

        if len(self.lesson_key) > 255:
            raise MemoryValidationError("lesson_key cannot exceed 255 characters.")

        if not self.content or not self.content.strip():
            raise MemoryValidationError("content must be a non-empty string.")

        if not isinstance(self.confidence_score, Decimal):
            try:
                self.confidence_score = Decimal(str(self.confidence_score))
            except Exception:
                raise MemoryValidationError("confidence_score must be a valid Decimal value.")

        if self.confidence_score < Decimal("0.00") or self.confidence_score > Decimal("1.00"):
            raise MemoryValidationError(f"confidence_score must be between 0.00 and 1.00, got {self.confidence_score}.")

        if self.embedding is not None:
            if not isinstance(self.embedding, list):
                raise MemoryValidationError(f"embedding must be a list of floats, got {type(self.embedding).__name__}.")
            if len(self.embedding) == 0:
                raise MemoryValidationError("embedding list cannot be empty when provided.")
            for idx, val in enumerate(self.embedding):
                if not isinstance(val, (int, float)) or not math.isfinite(val):
                    raise MemoryValidationError(
                        f"embedding element at index {idx} must be a finite float, got {val!r}."
                    )

    @property
    def is_deprecated(self) -> bool:
        """Return True if this memory record has been deprecated."""
        return self.confidence_score <= Decimal("0.00")

    def deprecate(self) -> None:
        """Deprecate this memory record by setting its confidence score to 0.00."""
        self.confidence_score = Decimal("0.00")

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory record to a dictionary."""
        return {
            "id": self.id,
            "org_id": self.org_id,
            "project_id": self.project_id,
            "scope": self.scope.value if isinstance(self.scope, MemoryScope) else str(self.scope),
            "category": self.category,
            "lesson_key": self.lesson_key,
            "content": self.content,
            "provenance_task_id": self.provenance_task_id,
            "confidence_score": str(self.confidence_score),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "embedding": self.embedding,
        }

    @classmethod
    def from_model(cls, model: Any) -> "MemoryRecord":
        """Construct a domain MemoryRecord from a persistence model."""
        return cls(
            id=model.id,
            org_id=model.org_id,
            project_id=model.project_id,
            scope=model.scope if isinstance(model.scope, MemoryScope) else MemoryScope(model.scope),
            category=model.category,
            lesson_key=model.lesson_key,
            content=model.content,
            provenance_task_id=model.provenance_task_id,
            confidence_score=Decimal(str(model.confidence_score)),
            created_at=model.created_at,
            embedding=getattr(model, "embedding", None),
        )


@dataclass
class MemoryFeedbackEvent:
    id: UUID = field(default_factory=uuid4)
    org_id: UUID = field(default_factory=uuid4)
    memory_id: UUID = field(default_factory=uuid4)
    outcome: str = ""
    confidence_delta: Decimal = field(default_factory=lambda: Decimal("0.00"))
    resulting_confidence_score: Decimal = field(default_factory=lambda: Decimal("1.00"))
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    project_id: UUID | None = None
    task_id: UUID | None = None
    attempt_id: UUID | None = None
    source_artifact_id: UUID | None = None
    source_artifact_version: str | None = None
    source_artifact_checksum: str | None = None
    patch_hash: str | None = None

    def validate(self) -> None:
        from syntra.domain.exceptions import MemoryValidationError

        if not isinstance(self.id, UUID):
            raise MemoryValidationError(f"Invalid feedback id: expected UUID, got {type(self.id).__name__}.")
        if not isinstance(self.org_id, UUID):
            raise MemoryValidationError("Organization ID (org_id) is mandatory and must be a UUID.")
        if not isinstance(self.memory_id, UUID):
            raise MemoryValidationError("Memory ID (memory_id) is mandatory and must be a UUID.")
        if not self.outcome or not self.outcome.strip():
            raise MemoryValidationError("outcome must be a non-empty string.")
        if not self.idempotency_key or not self.idempotency_key.strip():
            raise MemoryValidationError("idempotency_key must be a non-empty string.")
        if not isinstance(self.confidence_delta, Decimal):
            try:
                self.confidence_delta = Decimal(str(self.confidence_delta))
            except Exception:
                raise MemoryValidationError("confidence_delta must be a valid Decimal value.")
        if not isinstance(self.resulting_confidence_score, Decimal):
            try:
                self.resulting_confidence_score = Decimal(str(self.resulting_confidence_score))
            except Exception:
                raise MemoryValidationError("resulting_confidence_score must be a valid Decimal value.")
        if self.resulting_confidence_score < Decimal("0.00") or self.resulting_confidence_score > Decimal("1.00"):
            raise MemoryValidationError(
                f"resulting_confidence_score must be between 0.00 and 1.00, got {self.resulting_confidence_score}."
            )


@dataclass
class VerificationEvidence:
    exit_code: int
    execution_duration_ms: int
    stdout_digest: str
    stderr_digest: str
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    tests_errored: int = 0
    raw_stdout: str = ""
    raw_stderr: str = ""
    error_message: str | None = None


@dataclass
class VerificationRecord:
    id: UUID
    org_id: UUID
    mission_id: UUID
    task_id: UUID
    task_attempt_id: UUID
    plan_version: int
    status: VerificationStatus
    clean_base_commit: str
    patch_hash: str
    protected_test_suite_hash: str
    evidence: VerificationEvidence
    verifier_signature: str
    trace_id: str | None = None
    span_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate(self) -> None:
        from syntra.domain.exceptions import VerificationError

        if not isinstance(self.id, UUID):
            raise VerificationError("id must be a UUID")
        if not isinstance(self.org_id, UUID):
            raise VerificationError("org_id must be a UUID")
        if not isinstance(self.mission_id, UUID):
            raise VerificationError("mission_id must be a UUID")
        if not isinstance(self.task_id, UUID):
            raise VerificationError("task_id must be a UUID")
        if not isinstance(self.task_attempt_id, UUID):
            raise VerificationError("task_attempt_id must be a UUID")
        if not self.patch_hash or len(self.patch_hash) != 64:
            raise VerificationError("patch_hash must be a 64-character SHA-256 hexadecimal string")
        if not self.verifier_signature or len(self.verifier_signature) != 64:
            raise VerificationError("verifier_signature must be a 64-character SHA-256 hexadecimal string")


@dataclass
class ProtectedTestSuiteManifest:
    manifest_hash: str
    protected_files: dict[str, str] = field(default_factory=dict)
    registered_patterns: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ==============================================================================
# Canonical Action Digest Functions (Anti-Tampering)
# ==============================================================================
def compute_action_digest(
    secret: str,
    mission_id: UUID,
    action_type: str,
    target_resource: str,
    mission_version: int,
    expires_at: datetime,
) -> str:
    """Compute HMAC-SHA256 digest over canonical action details."""
    import hashlib
    import hmac

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    canonical_payload = f"{mission_id}:{action_type}:{target_resource}:{mission_version}:{expires_at.isoformat()}"
    return hmac.new(secret.encode("utf-8"), canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_action_digest(
    secret: str,
    expected_digest: str,
    mission_id: UUID,
    action_type: str,
    target_resource: str,
    mission_version: int,
    expires_at: datetime,
) -> bool:
    """Verify HMAC-SHA256 digest matching canonical action details."""
    import hmac

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    computed = compute_action_digest(
        secret=secret,
        mission_id=mission_id,
        action_type=action_type,
        target_resource=target_resource,
        mission_version=mission_version,
        expires_at=expires_at,
    )
    return hmac.compare_digest(computed, expected_digest)


def compute_verification_signature(
    secret: str,
    org_id: UUID,
    mission_id: UUID,
    task_id: UUID,
    task_attempt_id: UUID,
    patch_hash: str,
    clean_base_commit: str,
    protected_test_suite_hash: str,
    status: str,
    exit_code: int,
) -> str:
    """Compute HMAC-SHA256 signature over canonical independent verification outcome."""
    import hashlib
    import hmac

    canonical_payload = (
        f"{org_id}:{mission_id}:{task_id}:{task_attempt_id}:{patch_hash}:"
        f"{clean_base_commit}:{protected_test_suite_hash}:{status}:{exit_code}"
    )
    return hmac.new(secret.encode("utf-8"), canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_verification_signature(
    secret: str,
    expected_signature: str,
    org_id: UUID,
    mission_id: UUID,
    task_id: UUID,
    task_attempt_id: UUID,
    patch_hash: str,
    clean_base_commit: str,
    protected_test_suite_hash: str,
    status: str,
    exit_code: int,
) -> bool:
    """Verify HMAC-SHA256 signature over canonical verification record."""
    import hmac

    computed = compute_verification_signature(
        secret=secret,
        org_id=org_id,
        mission_id=mission_id,
        task_id=task_id,
        task_attempt_id=task_attempt_id,
        patch_hash=patch_hash,
        clean_base_commit=clean_base_commit,
        protected_test_suite_hash=protected_test_suite_hash,
        status=status,
        exit_code=exit_code,
    )
    return hmac.compare_digest(computed, expected_signature)
