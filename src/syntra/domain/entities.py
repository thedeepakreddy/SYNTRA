"""Pure domain entities, value objects, and enumerations for SYNTRA.

Zero framework or database dependencies.
"""

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
    FAILED = "FAILED"


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
