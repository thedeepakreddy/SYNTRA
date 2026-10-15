"""SYNTRA Agent Capability Profiles.

Defines authoritative capability profiles for all 10 specialized engineering personas
in accordance with AGENTS.md. Declares supported skills, required artifact types,
allowed tool capabilities, and hard execution limitations.

Note: The backend Capability Policy Engine remains the final permission authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from syntra.domain.entities import AgentRole


@dataclass(frozen=True)
class AgentCapabilityProfile:
    """Authoritative capability profile for an agent role."""

    role: AgentRole
    display_name: str
    supported_skills: list[str] = field(default_factory=list)
    required_artifact_types: list[str] = field(default_factory=list)
    allowed_tool_capabilities: list[str] = field(default_factory=list)
    execution_limitations: list[str] = field(default_factory=list)

    def is_skill_supported(self, skill_id: str) -> bool:
        """Check whether a skill is allowed for this role."""
        normalized = skill_id.strip().lower()
        return normalized in [s.lower() for s in self.supported_skills]

    def is_capability_allowed(self, capability: str) -> bool:
        """Check whether a capability prefix or pattern is nominally allowed."""
        cap = capability.strip().lower()
        for allowed in self.allowed_tool_capabilities:
            if allowed.endswith(".*"):
                prefix = allowed[:-2]
                if cap.startswith(prefix):
                    return True
            elif cap == allowed.lower():
                return True
        return False


AGENT_CAPABILITY_PROFILES: dict[AgentRole, AgentCapabilityProfile] = {
    AgentRole.PRODUCT_MANAGER: AgentCapabilityProfile(
        role=AgentRole.PRODUCT_MANAGER,
        display_name="Product Manager",
        supported_skills=[
            "requirements-analysis",
            "technical-documentation",
            "documentation-generation",
        ],
        required_artifact_types=[
            "PRDDocument",
            "AmbiguityLog",
            "UserStoryMap",
        ],
        allowed_tool_capabilities=[
            "syntra.workspace_search",
            "syntra.read_file",
            "syntra.list_directory",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "Must never modify source code directly",
            "Must never execute bash or terminal commands",
            "Must never approve pull requests or external releases",
        ],
    ),
    AgentRole.SOFTWARE_ARCHITECT: AgentCapabilityProfile(
        role=AgentRole.SOFTWARE_ARCHITECT,
        display_name="Software Architect",
        supported_skills=[
            "system-architecture",
            "database-engineering",
            "technical-documentation",
            "documentation-generation",
        ],
        required_artifact_types=[
            "ArchitectureSpecification",
            "ArchitectureDecisionRecord",
            "DataModelSpec",
        ],
        allowed_tool_capabilities=[
            "syntra.workspace_search",
            "syntra.read_file",
            "syntra.list_directory",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "Must never write implementation code directly into repositories",
            "Must never execute unverified shell scripts",
            "Must never approve external Git pushes",
        ],
    ),
    AgentRole.ENGINEERING_MANAGER: AgentCapabilityProfile(
        role=AgentRole.ENGINEERING_MANAGER,
        display_name="Engineering Manager",
        supported_skills=[
            "task-decomposition",
            "git-workflow",
            "technical-documentation",
            "documentation-generation",
        ],
        required_artifact_types=[
            "TaskPlan",
            "TaskDAG",
            "IterationMilestone",
        ],
        allowed_tool_capabilities=[
            "syntra.workspace_search",
            "syntra.read_file",
            "syntra.list_directory",
            "syntra.validate_dag",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "Must never execute engineering tasks directly",
            "Must never bypass capability grants or DAG cycle validation",
            "Must not execute shell commands",
        ],
    ),
    AgentRole.BACKEND_ENGINEER: AgentCapabilityProfile(
        role=AgentRole.BACKEND_ENGINEER,
        display_name="Backend Engineer",
        supported_skills=[
            "backend-api-development",
            "database-engineering",
            "test-driven-development",
            "dependency-management",
        ],
        required_artifact_types=[
            "UnifiedDiff",
            "UnitTestSuite",
            "MigrationScript",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.write_file",
            "syntra.run_command",
            "syntra.workspace_search",
            "syntra.git_diff",
        ],
        execution_limitations=[
            "Must never access host filesystem or host environment variables",
            "Must never self-approve or self-review own unified diffs",
            "Must execute exclusively inside isolated sandbox",
        ],
    ),
    AgentRole.FRONTEND_ENGINEER: AgentCapabilityProfile(
        role=AgentRole.FRONTEND_ENGINEER,
        display_name="Frontend Engineer",
        supported_skills=[
            "frontend-development",
            "test-driven-development",
            "api-contract-testing",
        ],
        required_artifact_types=[
            "UnifiedDiff",
            "ComponentTestSuite",
            "ClientBundle",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.write_file",
            "syntra.run_command",
            "syntra.workspace_search",
            "syntra.git_diff",
        ],
        execution_limitations=[
            "Modifications strictly restricted to target repositories (never SYNTRA core)",
            "Must never touch SYNTRA platform code or backend models",
            "Must execute inside target repo sandbox",
        ],
    ),
    AgentRole.QA_ENGINEER: AgentCapabilityProfile(
        role=AgentRole.QA_ENGINEER,
        display_name="QA Engineer",
        supported_skills=[
            "test-driven-development",
            "integration-testing",
            "api-contract-testing",
        ],
        required_artifact_types=[
            "VerificationRun",
            "TestFailureReport",
            "ContractDriftReport",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.write_file",
            "syntra.run_command",
            "syntra.workspace_search",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "Must never modify production source code to artificially make tests pass",
            "Must never execute outside of test runner sandbox",
            "Must test against PRD criteria independently",
        ],
    ),
    AgentRole.DEVOPS_ENGINEER: AgentCapabilityProfile(
        role=AgentRole.DEVOPS_ENGINEER,
        display_name="DevOps Engineer",
        supported_skills=[
            "devops-and-ci",
            "git-workflow",
            "dependency-management",
        ],
        required_artifact_types=[
            "ContainerManifest",
            "CIPipelineConfig",
            "BuildLog",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.write_file",
            "syntra.run_command",
            "syntra.workspace_search",
            "syntra.git_branch",
            "syntra.git_diff",
        ],
        execution_limitations=[
            "Must never push to external remote Git without explicit human authorization",
            "Must never execute privileged commands on host",
            "Must enforce non-root container baselines",
        ],
    ),
    AgentRole.SECURITY_REVIEWER: AgentCapabilityProfile(
        role=AgentRole.SECURITY_REVIEWER,
        display_name="Security Reviewer",
        supported_skills=[
            "security-review",
            "code-review",
        ],
        required_artifact_types=[
            "SecurityAuditReport",
            "SecretScanReport",
            "VulnerabilityFinding",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.workspace_search",
            "syntra.list_directory",
            "syntra.security_scan",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "Must never modify source code",
            "Must never approve diffs with unresolved Critical or High findings",
            "Cannot review patches authored by itself",
        ],
    ),
    AgentRole.CODE_REVIEWER: AgentCapabilityProfile(
        role=AgentRole.CODE_REVIEWER,
        display_name="Code Reviewer",
        supported_skills=[
            "code-review",
            "technical-documentation",
            "documentation-generation",
        ],
        required_artifact_types=[
            "ReviewVerdict",
            "LineCommentSummary",
            "DiffEvaluation",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.workspace_search",
            "syntra.list_directory",
            "syntra.artifact_read",
            "syntra.artifact_write",
        ],
        execution_limitations=[
            "May not review code authored by itself (Anti-Collusion Invariant)",
            "May not modify source code directly",
            "Must reject patches with failing QA tests",
        ],
    ),
    AgentRole.DEBUGGING_SPECIALIST: AgentCapabilityProfile(
        role=AgentRole.DEBUGGING_SPECIALIST,
        display_name="Debugging Specialist",
        supported_skills=[
            "debugging-and-root-cause-analysis",
            "test-driven-development",
            "backend-api-development",
        ],
        required_artifact_types=[
            "RootCauseAnalysisReport",
            "ReproducingTestCase",
            "MinimalFixPatch",
        ],
        allowed_tool_capabilities=[
            "syntra.read_file",
            "syntra.write_file",
            "syntra.run_command",
            "syntra.workspace_search",
            "syntra.git_diff",
        ],
        execution_limitations=[
            "Must not disable or weaken existing test assertions to bypass failures",
            "Must produce minimal reproducing tests before fixing",
            "Scattered non-surgical fixes rejected",
        ],
    ),
}


def get_agent_profile(role: AgentRole | str) -> AgentCapabilityProfile:
    """Retrieve capability profile for a given role (by enum or string)."""
    if isinstance(role, AgentRole):
        return AGENT_CAPABILITY_PROFILES[role]

    normalized = role.strip().lower()
    for agent_role, profile in AGENT_CAPABILITY_PROFILES.items():
        if agent_role.value.lower() == normalized or profile.display_name.lower() == normalized:
            return profile

    raise ValueError(f"Unknown or unsupported agent role: '{role}'")
