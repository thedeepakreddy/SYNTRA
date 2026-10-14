"""Authoritative SQLAlchemy 2.x declarative models for SYNTRA PostgreSQL persistence (30 Tables).

Adheres to docs/architecture/database-design.md.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from syntra.domain.entities import (
    ADRStatus,
    ApprovalDecision,
    ArtifactType,
    AttemptState,
    MCPTransportType,
    MembershipRole,
    MemoryScope,
    MissionState,
    OutboxStatus,
    RequirementType,
    SandboxStatus,
    TaskPlanStatus,
    TaskState,
    VerificationVerdict,
)
from syntra.storage.database import Base

# Universal JSON type compatible with Postgres JSONB and SQLite JSON
UniversalJSON = JSON().with_variant(JSONB(), "postgresql")


# ==============================================================================
# 3.1 Tenancy & Identity Layer (1-5)
# ==============================================================================
class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    memberships: Mapped[list["MembershipModel"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    projects: Mapped[list["ProjectModel"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    missions: Mapped[list["MissionModel"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    budgets: Mapped[list["BudgetModel"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_service_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    memberships: Mapped[list["MembershipModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MembershipModel(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),
        Index("idx_memberships_org_id", "org_id"),
        Index("idx_memberships_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role", native_enum=True), default=MembershipRole.ENGINEER, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    organization: Mapped["OrganizationModel"] = relationship(back_populates="memberships")
    user: Mapped["UserModel"] = relationship(back_populates="memberships")


class ProjectModel(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_projects_org_slug"),
        Index("idx_projects_org_id", "org_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    organization: Mapped["OrganizationModel"] = relationship(back_populates="projects")
    repositories: Mapped[list["RepositoryModel"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    missions: Mapped[list["MissionModel"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class RepositoryModel(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_repositories_project_name"),
        Index("idx_repositories_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    clone_url: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    project: Mapped["ProjectModel"] = relationship(back_populates="repositories")


# ==============================================================================
# 3.2 Mission & Architecture Planning Layer (6-8)
# ==============================================================================
class MissionModel(Base):
    __tablename__ = "missions"
    __table_args__ = (
        Index("idx_missions_org_state", "org_id", "state"),
        Index("idx_missions_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    repository_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[MissionState] = mapped_column(
        Enum(MissionState, name="mission_state", native_enum=True), default=MissionState.DRAFT, nullable=False
    )
    autonomy_mode: Mapped[str] = mapped_column(String(50), default="semi_autonomous", nullable=False)
    active_plan_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    organization: Mapped["OrganizationModel"] = relationship(back_populates="missions")
    project: Mapped["ProjectModel"] = relationship(back_populates="missions")
    task_plans: Mapped[list["TaskPlanModel"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
    requirements: Mapped[list["RequirementModel"]] = relationship(
        back_populates="mission", cascade="all, delete-orphan"
    )
    architecture_decisions: Mapped[list["ArchitectureDecisionModel"]] = relationship(
        back_populates="mission", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
    approvals: Mapped[list["HumanApprovalModel"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


class RequirementModel(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint("mission_id", "identifier", name="uq_requirements_mission_identifier"),
        Index("idx_requirements_mission_id", "mission_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, name="requirement_type", native_enum=True),
        default=RequirementType.FUNCTIONAL,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[list[dict[str, Any]]] = mapped_column(UniversalJSON, default=list, nullable=False)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    mission: Mapped["MissionModel"] = relationship(back_populates="requirements")


class ArchitectureDecisionModel(Base):
    __tablename__ = "architecture_decisions"
    __table_args__ = (
        UniqueConstraint("mission_id", "adr_number", name="uq_adr_mission_number"),
        Index("idx_adr_mission_id", "mission_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    adr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ADRStatus] = mapped_column(
        Enum(ADRStatus, name="adr_status", native_enum=True), default=ADRStatus.PROPOSED, nullable=False
    )
    context: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    consequences: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    mission: Mapped["MissionModel"] = relationship(back_populates="architecture_decisions")


# ==============================================================================
# 3.3 Task Graph & Scheduling Layer (9-13)
# ==============================================================================
class TaskPlanModel(Base):
    __tablename__ = "task_plans"
    __table_args__ = (
        UniqueConstraint("mission_id", "plan_version", name="uq_task_plans_mission_version"),
        Index("idx_task_plans_mission", "mission_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    plan_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[TaskPlanStatus] = mapped_column(
        Enum(TaskPlanStatus, name="task_plan_status", native_enum=True), default=TaskPlanStatus.DRAFT, nullable=False
    )
    total_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    mission: Mapped["MissionModel"] = relationship(back_populates="task_plans")
    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="task_plan", cascade="all, delete-orphan")


class TaskModel(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("task_plan_id", "identifier", name="uq_tasks_plan_identifier"),
        Index("idx_tasks_mission_state", "mission_id", "state"),
        Index("idx_tasks_org_state", "org_id", "state"),
        Index("idx_tasks_plan_id", "task_plan_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("task_plans.id", ondelete="CASCADE"), nullable=False
    )
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_role: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[TaskState] = mapped_column(
        Enum(TaskState, name="task_state", native_enum=True), default=TaskState.PENDING, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    task_plan: Mapped["TaskPlanModel"] = relationship(back_populates="tasks")
    attempts: Mapped[list["TaskAttemptModel"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskDependencyModel(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        CheckConstraint("task_id <> depends_on_task_id", name="chk_no_self_dependency"),
        Index("idx_task_dependencies_task_id", "task_id"),
        Index("idx_task_dependencies_depends_on", "depends_on_task_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    depends_on_task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class TaskAttemptModel(Base):
    __tablename__ = "task_attempts"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt_number", name="uq_task_attempt_number"),
        Index("idx_task_attempts_task_id", "task_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[AttemptState] = mapped_column(
        Enum(AttemptState, name="attempt_state", native_enum=True), default=AttemptState.INITIALIZING, nullable=False
    )
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped["TaskModel"] = relationship(back_populates="attempts")
    executions: Mapped[list["AgentExecutionModel"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class AgentExecutionModel(Base):
    __tablename__ = "agent_executions"
    __table_args__ = (Index("idx_agent_executions_attempt", "task_attempt_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_attempt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("task_attempts.id", ondelete="CASCADE"), nullable=False
    )
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    attempt: Mapped["TaskAttemptModel"] = relationship(back_populates="executions")


# ==============================================================================
# 3.4 Worker & Sandbox Execution Layer (14-15)
# ==============================================================================
class SandboxJobModel(Base):
    __tablename__ = "sandbox_jobs"
    __table_args__ = (
        Index("idx_sandbox_jobs_attempt", "task_attempt_id"),
        Index("idx_sandbox_jobs_worker", "worker_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_attempt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("task_attempts.id", ondelete="CASCADE"), nullable=False
    )
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    workspace_path: Mapped[str] = mapped_column(Text, nullable=False)
    git_worktree_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SandboxStatus] = mapped_column(
        Enum(SandboxStatus, name="sandbox_status", native_enum=True), default=SandboxStatus.PROVISIONING, nullable=False
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerLeaseModel(Base):
    __tablename__ = "worker_leases"
    __table_args__ = (Index("idx_worker_leases_expires_at", "lease_expires_at"),)

    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    fencing_token: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ==============================================================================
# 3.5 Artifact & Verification Layer (16-18)
# ==============================================================================
class ArtifactModel(Base):
    __tablename__ = "artifacts"
    __table_args__ = (Index("idx_artifacts_mission_type", "mission_id", "type"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, name="artifact_type", native_enum=True), default=ArtifactType.PRD, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    mission: Mapped["MissionModel"] = relationship(back_populates="artifacts")
    versions: Mapped[list["ArtifactVersionModel"]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )


class ArtifactVersionModel(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),
        Index("idx_artifact_versions_artifact", "artifact_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    artifact: Mapped["ArtifactModel"] = relationship(back_populates="versions")


class VerificationRunModel(Base):
    __tablename__ = "verification_runs"
    __table_args__ = (Index("idx_verification_runs_task", "task_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    artifact_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    verdict: Mapped[VerificationVerdict] = mapped_column(
        Enum(VerificationVerdict, name="verification_verdict", native_enum=True),
        default=VerificationVerdict.PASS,
        nullable=False,
    )
    tests_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tests_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coverage_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ==============================================================================
# 3.6 Tool, MCP & Skills Governance Layer (19-23)
# ==============================================================================
class MCPServerModel(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    transport: Mapped[MCPTransportType] = mapped_column(
        Enum(MCPTransportType, name="mcp_transport_type", native_enum=True),
        default=MCPTransportType.STDIO,
        nullable=False,
    )
    command_or_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    tool_versions: Mapped[list["MCPToolVersionModel"]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )


class MCPToolVersionModel(Base):
    __tablename__ = "mcp_tool_versions"
    __table_args__ = (
        UniqueConstraint("mcp_server_id", "tool_name", "version", name="uq_tool_server_name_version"),
        Index("idx_tool_versions_server", "mcp_server_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mcp_server_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any]] = mapped_column(UniversalJSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    server: Mapped["MCPServerModel"] = relationship(back_populates="tool_versions")


class SkillModel(Base):
    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    versions: Mapped[list["SkillVersionModel"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class SkillVersionModel(Base):
    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_version"),
        Index("idx_skill_versions_skill", "skill_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    instruction_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    compatible_roles: Mapped[list[str]] = mapped_column(UniversalJSON, default=list, nullable=False)
    required_tools: Mapped[list[str]] = mapped_column(UniversalJSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    skill: Mapped["SkillModel"] = relationship(back_populates="versions")


class CapabilityGrantModel(Base):
    __tablename__ = "capability_grants"
    __table_args__ = (Index("idx_capability_grants_org_role", "org_id", "agent_role"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ==============================================================================
# 3.7 Governance, Budgeting & Approvals Layer (24-26)
# ==============================================================================
class HumanApprovalModel(Base):
    __tablename__ = "human_approvals"
    __table_args__ = (Index("idx_human_approvals_mission_decision", "mission_id", "decision"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[ApprovalDecision] = mapped_column(
        Enum(ApprovalDecision, name="approval_decision", native_enum=True),
        default=ApprovalDecision.PENDING,
        nullable=False,
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mission: Mapped["MissionModel"] = relationship(back_populates="approvals")


class BudgetModel(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("mission_id", name="uq_budgets_mission"),
        Index("idx_budgets_org", "org_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=True
    )
    max_tokens: Mapped[int] = mapped_column(BigInteger, default=1_000_000, nullable=False)
    max_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("50.0000"), nullable=False)
    reserved_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    consumed_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    consumed_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0000"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    organization: Mapped["OrganizationModel"] = relationship(back_populates="budgets")


class UsageRecordModel(Base):
    __tablename__ = "usage_records"
    __table_args__ = (Index("idx_usage_records_org_mission", "org_id", "mission_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    mission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ==============================================================================
# 3.8 Observability, Memory & Reliable Messaging Layer (27-30)
# ==============================================================================
class EventRecordModel(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_mission", "mission_id", "created_at"),
        Index("idx_events_type", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(UniversalJSON, default=dict, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), default="orchestrator", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class TransactionalOutboxModel(Base):
    __tablename__ = "transactional_outbox"
    __table_args__ = (Index("idx_outbox_pending", "status", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(UniversalJSON, default=dict, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status", native_enum=True), default=OutboxStatus.PENDING, nullable=False
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (Index("idx_idempotency_expires", "expires_at"),)

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(UniversalJSON, default=dict, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MemoryRecordModel(Base):
    __tablename__ = "memory_records"
    __table_args__ = (Index("idx_memory_records_org_scope", "org_id", "scope", "category"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    scope: Mapped[MemoryScope] = mapped_column(
        Enum(MemoryScope, name="memory_scope", native_enum=True), default=MemoryScope.ORGANIZATION, nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    lesson_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("1.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
