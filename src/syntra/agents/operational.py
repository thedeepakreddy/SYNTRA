"""Ten executable specialist policies on the existing runtime, skills and role enum."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from syntra.domain.entities import AgentRole
from syntra.llm.config import MODEL_REGISTRY
from syntra.llm.models import ToolDefinition
from syntra.llm.router import ModelRouter
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.llm.schemas import (
    AgentFinalResult,
    ArchitectureProposal,
    CodeReviewProposal,
    FailureAnalysis,
    RequirementsAnalysis,
    TaskPlanProposal,
)
from syntra.scheduling.dag_engine import TaskDAGEngine
from syntra.skills.profiles import get_agent_profile
from syntra.skills.registry import SkillRegistry


class QAProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_plan: list[str] = Field(min_length=1)
    acceptance_commands: list[str] = Field(min_length=1, max_length=10)
    requirement_refs: list[str] = Field(min_length=1)
    defects: list[str] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(min_length=1)
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    component: str = Field(min_length=1)
    evidence: str = Field(min_length=5)
    impact: str = Field(min_length=5)
    remediation: str = Field(min_length=5)
    verification: str = Field(min_length=5)


class SecurityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=10)
    findings: list[SecurityFinding]
    limitations: list[str] = Field(min_length=1)


class AgentInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    invocation_id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    mission_id: UUID
    task_id: UUID | None = None
    task_attempt_id: UUID | None = None
    plan_version: int = Field(default=1, ge=1)
    role: AgentRole
    objective: str = Field(min_length=5, max_length=100000)
    skill_ids: list[str] = Field(default_factory=list)
    approved_capabilities: list[str] = Field(default_factory=list)
    deadline: datetime
    max_tokens: int = Field(default=100000, ge=1, le=1000000)
    max_cost_usd: Decimal = Field(default=Decimal("0.25"), ge=0)
    input_artifacts: list[dict[str, str]] = Field(default_factory=list)
    approved_technologies: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: UUID
    role: AgentRole
    status: Literal["SUCCEEDED", "FAILED", "BLOCKED", "NEEDS_CLARIFICATION", "NEEDS_APPROVAL", "CANCELLED"]
    output: SerializeAsAny[BaseModel] | None = None
    model_id: str
    agent_version: str = "1.0.0"
    prompt_version: str = "1.0.0"
    skill_versions: list[str] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Decimal = Decimal("0")


@dataclass(frozen=True)
class AgentDefinition:
    role: AgentRole
    display_name: str
    description: str
    master_skills: tuple[str, ...]
    allowed_skill_ids: tuple[str, ...]
    allowed_tool_capabilities: tuple[str, ...]
    output_schema: type[BaseModel]
    model_id: str
    input_schema: type[BaseModel] = AgentInvocation
    version: str = "1.0.0"
    prompt_version: str = "1.0.0"
    maximum_turns: int = 12
    maximum_tool_calls: int = 30
    timeout_seconds: int = 120
    budget_tokens: int = 100000
    budget_cost_usd: Decimal = Decimal("0.25")
    review_requirements: tuple[str, ...] = ("independent_peer", "independent_qa")


ROLE_CONTRACTS: dict[AgentRole, tuple[type[BaseModel], str, tuple[str, ...]]] = {
    AgentRole.PRODUCT_MANAGER: (
        RequirementsAnalysis,
        "requirements-analysis",
        ("Requirements analysis", "Acceptance criteria", "Scope and risk"),
    ),
    AgentRole.SOFTWARE_ARCHITECT: (
        ArchitectureProposal,
        "system-architecture",
        ("Component contracts", "Database and API design", "ADRs and compatibility"),
    ),
    AgentRole.ENGINEERING_MANAGER: (
        TaskPlanProposal,
        "task-decomposition",
        ("DAG decomposition", "Resource estimates", "Task ownership and handoffs"),
    ),
    AgentRole.BACKEND_ENGINEER: (
        AgentFinalResult,
        "backend-api-development",
        ("Python and FastAPI", "SQLAlchemy and PostgreSQL", "TDD and patch workflows"),
    ),
    AgentRole.FRONTEND_ENGINEER: (
        AgentFinalResult,
        "frontend-development",
        ("TypeScript and React", "Accessibility and API integration", "Build and component testing"),
    ),
    AgentRole.QA_ENGINEER: (
        QAProposal,
        "integration-testing",
        ("Independent acceptance tests", "Negative and boundary cases", "Evidence collection"),
    ),
    AgentRole.DEVOPS_ENGINEER: (
        AgentFinalResult,
        "devops-and-ci",
        ("Docker and CI", "Build validation", "Secret boundaries and rollback"),
    ),
    AgentRole.CODE_REVIEWER: (
        CodeReviewProposal,
        "code-review",
        ("Patch review", "Compatibility and regression analysis", "Requirements traceability"),
    ),
    AgentRole.SECURITY_REVIEWER: (
        SecurityReport,
        "security-review",
        ("Threat modeling", "Injection and authorization", "Secrets and dependency analysis"),
    ),
    AgentRole.DEBUGGING_SPECIALIST: (
        FailureAnalysis,
        "debugging-and-root-cause-analysis",
        ("Failure reproduction", "Root cause diagnosis", "Minimal corrections and regression prevention"),
    ),
}


class AgentRegistry:
    def __init__(self, skills: SkillRegistry, model_name: str | None = None) -> None:
        self.skills = skills
        self.definitions: dict[AgentRole, AgentDefinition] = {}
        for role, (schema, primary, master) in ROLE_CONTRACTS.items():
            profile = get_agent_profile(role)
            compatible = []
            for skill in profile.supported_skills:
                pkg = skills.resolve_skill_version(skill)
                if role.value in pkg.manifest.supported_roles:
                    compatible.append(skill)
            if primary not in compatible:
                raise ValueError(f"Primary skill {primary} is not compatible with {role.value}")
            self.register(
                AgentDefinition(
                    role,
                    profile.display_name,
                    profile.execution_limitations[0],
                    master,
                    tuple([primary] + [s for s in compatible if s != primary]),
                    tuple(profile.allowed_tool_capabilities),
                    schema,
                    model_name or ModelRouter.resolve_model(role.value),
                )
            )

    def register(self, definition: AgentDefinition) -> None:
        if definition.role in self.definitions:
            raise ValueError(f"Duplicate role {definition.role.value}")
        if (
            definition.model_id not in MODEL_REGISTRY
            or not MODEL_REGISTRY[definition.model_id].enabled
            or MODEL_REGISTRY[definition.model_id].lifecycle_status == "SHUTDOWN"
        ):
            raise ValueError("Invalid agent model configuration")
        profile = get_agent_profile(definition.role)
        if any(not profile.is_capability_allowed(c) for c in definition.allowed_tool_capabilities):
            raise ValueError("Unsupported capability")
        for skill in definition.allowed_skill_ids:
            pkg = self.skills.resolve_skill_version(skill)
            if not profile.is_skill_supported(skill) or definition.role.value not in pkg.manifest.supported_roles:
                raise ValueError("Unauthorized skill registration")
        definition.input_schema.model_json_schema()
        definition.output_schema.model_json_schema()
        if min(definition.maximum_turns, definition.timeout_seconds, definition.budget_tokens) <= 0:
            raise ValueError("Invalid agent execution limits")
        self.definitions[definition.role] = definition

    def get(self, role: AgentRole | str) -> AgentDefinition:
        return self.definitions[AgentRole(role)]

    def validate_plan(self, plan: TaskPlanProposal, invocation: AgentInvocation) -> None:
        keys = [t.task_key for t in plan.tasks]
        if len(keys) != len(set(keys)) or any(k not in keys for k in plan.critical_path):
            raise ValueError("Duplicate task key or unknown critical-path reference")
        for task in plan.tasks:
            definition = self.get(task.role)
            if (
                not task.required_skills
                or not task.required_capabilities
                or not task.expected_artifacts
                or not task.verification_requirements
            ):
                raise ValueError("Task plan is missing skills, capabilities, artifacts or verification requirements")
            if any(s not in definition.allowed_skill_ids for s in task.required_skills):
                raise ValueError("Task plan requests an unauthorized skill")
            if any(c not in definition.allowed_tool_capabilities for c in task.required_capabilities):
                raise ValueError("Task plan requests unauthorized capabilities")
        if sum(t.estimated_tokens for t in plan.tasks) > invocation.max_tokens:
            raise ValueError("Task plan exceeds approved budget")
        if sum(t.estimated_cost_usd for t in plan.tasks) > invocation.max_cost_usd:
            raise ValueError("Task plan exceeds approved cost budget")
        ids = {key: uuid5(NAMESPACE_URL, f"{invocation.mission_id}:{invocation.plan_version}:{key}") for key in keys}
        if any(d not in ids for t in plan.tasks for d in t.dependencies):
            raise ValueError("Unknown or cross-mission task dependency")
        TaskDAGEngine().validate_graph(
            [{"id": ids[t.task_key], "mission_id": invocation.mission_id} for t in plan.tasks],
            [{"task_id": ids[t.task_key], "depends_on_task_id": ids[d]} for t in plan.tasks for d in t.dependencies],
        )


class SpecialistAgent:
    """Executable role policy; authority and tool execution stay in deterministic services."""

    def __init__(self, registry: AgentRegistry, runtime: ModelRuntime) -> None:
        self.registry, self.runtime = registry, runtime

    async def execute(
        self,
        invocation: AgentInvocation,
        *,
        tools: list[ToolDefinition] | None = None,
        usage_meter: RuntimeUsage | None = None,
        cancellation: asyncio.Event | None = None,
        retrieved_memories: list[Any] | str | None = None,
        uow: Any | None = None,
    ) -> AgentResult:
        definition = self.registry.get(invocation.role)
        if invocation.deadline.tzinfo is None:
            raise ValueError("Agent deadline must be timezone aware")
        remaining = (invocation.deadline - datetime.now(UTC)).total_seconds()
        if cancellation and cancellation.is_set():
            return AgentResult(
                invocation_id=invocation.invocation_id,
                role=invocation.role,
                status="CANCELLED",
                model_id=definition.model_id,
            )
        if remaining <= 0:
            raise ValueError("Agent deadline expired")
        skills = invocation.skill_ids or [definition.allowed_skill_ids[0]]
        if any(s not in definition.allowed_skill_ids for s in skills):
            raise ValueError("Unknown or unauthorized skill requested")
        if any(c not in definition.allowed_tool_capabilities for c in invocation.approved_capabilities):
            raise ValueError("Capabilities exceed role policy")
        for tool in tools or []:
            if (
                tool.name not in invocation.approved_capabilities
                or tool.name not in definition.allowed_tool_capabilities
            ):
                raise ValueError("Unauthorized tool for specialist role")
        meter = usage_meter or RuntimeUsage(
            min(invocation.max_tokens, definition.budget_tokens),
            min(invocation.max_cost_usd, definition.budget_cost_usd),
        )
        meter.max_tokens = min(
            meter.max_tokens, meter.total_tokens + invocation.max_tokens, meter.total_tokens + definition.budget_tokens
        )
        meter.max_cost_usd = min(
            meter.max_cost_usd, meter.cost_usd + invocation.max_cost_usd, meter.cost_usd + definition.budget_cost_usd
        )
        operation = self.runtime.execute_turn(
            invocation.role.value,
            invocation.objective,
            mission_id=invocation.mission_id,
            task_id=invocation.task_id,
            org_id=invocation.org_id,
            requested_skills=skills,
            active_grants=invocation.approved_capabilities,
            available_tools=tools,
            response_model=definition.output_schema,
            input_artifacts=invocation.input_artifacts,
            max_tool_steps=definition.maximum_turns,
            max_tool_calls=definition.maximum_tool_calls,
            timeout_seconds=min(remaining, definition.timeout_seconds),
            model_name=definition.model_id,
            prompt_version=definition.prompt_version,
            usage_meter=meter,
            uow=uow,
            retrieved_memories=retrieved_memories,
        )
        if cancellation:
            from contextlib import suppress

            run = asyncio.create_task(operation)
            cancelled = asyncio.create_task(cancellation.wait())
            try:
                done, _ = await asyncio.wait({run, cancelled}, return_when=asyncio.FIRST_COMPLETED)
                if cancelled in done:
                    run.cancel()
                    with suppress(asyncio.CancelledError):
                        await run
                    return AgentResult(
                        invocation_id=invocation.invocation_id,
                        role=invocation.role,
                        status="CANCELLED",
                        model_id=definition.model_id,
                        prompt_tokens=meter.prompt_tokens,
                        completion_tokens=meter.completion_tokens,
                        cost_usd=meter.cost_usd,
                    )
                outcome = await run
            finally:
                cancelled.cancel()
                with suppress(asyncio.CancelledError):
                    await cancelled
        else:
            outcome = await operation
        output = outcome.structured_output
        status = "SUCCEEDED"
        if isinstance(output, RequirementsAnalysis):
            if any(
                not all(word in c.lower() for word in ("given", "when", "then")) for c in output.acceptance_criteria
            ):
                raise ValueError("Acceptance criteria must use Given-When-Then")
            if output.open_questions:
                status = "NEEDS_CLARIFICATION"
        elif isinstance(output, ArchitectureProposal):
            if not output.requirement_refs:
                raise ValueError("Architecture must reference approved requirements")
            if invocation.approved_technologies and any(
                t not in invocation.approved_technologies for t in output.technology_choices
            ):
                raise ValueError("Unsupported technology proposal")
        elif isinstance(output, TaskPlanProposal):
            self.registry.validate_plan(output, invocation)
        elif isinstance(output, AgentFinalResult):
            status = {"SUCCESS": "SUCCEEDED", "FAILURE": "FAILED", "BLOCKED": "BLOCKED"}[output.verdict]
        elif isinstance(output, SecurityReport):
            if any(f.severity in {"HIGH", "CRITICAL"} for f in output.findings):
                status = "BLOCKED"
        elif isinstance(output, CodeReviewProposal):
            if (
                output.verdict != "APPROVED"
                or not output.test_coverage_adequate
                or not all(output.checklist_verifications.values())
                or any(c.severity == "BLOCKER" for c in output.line_level_comments)
            ):
                status = "BLOCKED"
        return AgentResult(
            invocation_id=invocation.invocation_id,
            role=invocation.role,
            status=cast(AnyStatus, status),
            output=output,
            model_id=definition.model_id,
            prompt_version=definition.prompt_version,
            skill_versions=outcome.skill_versions,
            prompt_tokens=outcome.prompt_tokens,
            completion_tokens=outcome.completion_tokens,
            cost_usd=outcome.estimated_cost_usd,
        )


AnyStatus = Literal["SUCCEEDED", "FAILED", "BLOCKED", "NEEDS_CLARIFICATION", "NEEDS_APPROVAL", "CANCELLED"]
