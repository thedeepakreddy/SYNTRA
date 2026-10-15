"""Strongly typed Pydantic v2 schemas for agent structured outputs.

All agent-generated specifications, proposals, actions, and review verdicts
are strictly validated against these contracts. Reject malformed or incomplete output;
never convert invalid data into successful results with silent defaults.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequirementsAnalysis(BaseModel):
    """Structured PRD and requirements analysis produced by the Product Manager."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., min_length=10, description="Executive summary of the product requirement")
    functional_requirements: list[str] = Field(..., min_length=1, description="Explicit functional behaviors required")
    non_functional_requirements: list[str] = Field(
        default_factory=list, description="Performance, latency, scalability, and security constraints"
    )
    acceptance_criteria: list[str] = Field(
        ..., min_length=1, description="Given-When-Then structured acceptance criteria"
    )
    assumptions_and_ambiguities: list[str] = Field(
        default_factory=list, description="Explicit assumptions recorded to eliminate ambiguity"
    )
    risk_assessment: str = Field(..., min_length=5, description="Identified risks and operational failure modes")

    @field_validator("summary", "risk_assessment")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be empty or whitespace only")
        return v.strip()


class ArchitectureProposal(BaseModel):
    """Architecture specification and technical decisions produced by the Software Architect."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5, description="Architecture document or ADR title")
    architectural_decisions: list[str] = Field(
        ..., min_length=1, description="Immutable architectural decisions and component boundaries"
    )
    component_contracts: list[str] = Field(
        ..., min_length=1, description="Interface and contract definitions between modules"
    )
    data_persistence_spec: str = Field(
        ..., min_length=5, description="Storage models, transactions, and migration plan"
    )
    security_invariants: list[str] = Field(
        ..., min_length=1, description="Security boundaries, isolation guarantees, and auth rules"
    )
    tradeoffs_and_alternatives: list[str] = Field(
        ..., min_length=1, description="Considered alternatives and technical tradeoffs"
    )


class TaskPlanItem(BaseModel):
    """Individual atomic task specification within an engineering plan."""

    model_config = ConfigDict(extra="forbid")

    task_key: str = Field(..., min_length=2, description="Unique task key, e.g. TASK-001")
    role: str = Field(..., description="Target specialized agent persona assigned to the task")
    objective: str = Field(..., min_length=5, description="Atomic, verifiable task outcome")
    dependencies: list[str] = Field(default_factory=list, description="Task keys that must complete before this task")
    acceptance_criteria: list[str] = Field(..., min_length=1, description="Verification criteria for task signoff")
    estimated_tokens: int = Field(default=8192, ge=100, le=1000000)


class TaskPlanProposal(BaseModel):
    """Cycle-free engineering task DAG produced by the Engineering Manager."""

    model_config = ConfigDict(extra="forbid")

    plan_summary: str = Field(..., min_length=10, description="Overview of the execution plan")
    tasks: list[TaskPlanItem] = Field(..., min_length=1, description="Ordered atomic task definitions")
    critical_path: list[str] = Field(..., min_length=1, description="Sequence of task keys on the critical path")
    concurrency_limits: int = Field(default=2, ge=1, le=16, description="Maximum concurrent worker sandboxes")


class AgentToolAction(BaseModel):
    """Proposed tool action emitted during turn execution for MCP policy validation."""

    model_config = ConfigDict(extra="forbid")

    thought_process: str = Field(..., min_length=5, description="Agent reasoning explaining why this tool is needed")
    tool_name: str = Field(..., min_length=3, description="Canonical tool identifier, e.g. 'syntra.read_file'")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Typed parameters for tool invocation")
    action_classification: Literal["READ_ONLY", "WORKSPACE_WRITE", "DESTRUCTIVE", "EXTERNAL_DISPATCH"] = Field(
        default="READ_ONLY", description="Declared capability classification"
    )
    justification: str = Field(..., min_length=5, description="Safety and policy justification for execution")


class AgentFinalResult(BaseModel):
    """Final outcome and deliverables concluding an agent's assignment."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., min_length=10, description="Comprehensive outcome description")
    verdict: Literal["SUCCESS", "FAILURE", "BLOCKED"] = Field(..., description="Task execution verdict")
    produced_artifact_names: list[str] = Field(default_factory=list, description="Names of artifacts generated")
    unified_diff: str | None = Field(default=None, description="Standard unified diff patch if code was modified")
    next_recommended_role: str | None = Field(default=None, description="Recommended downstream persona")
    evidence_notes: list[str] = Field(..., min_length=1, description="Bullet-point verification evidence and test logs")


class FailureAnalysis(BaseModel):
    """Diagnostic root-cause report produced by the Debugging Specialist."""

    model_config = ConfigDict(extra="forbid")

    error_type: str = Field(..., min_length=3, description="Exception class or failure category")
    root_cause_hypothesis: str = Field(..., min_length=10, description="Detailed causal diagnosis")
    reproducing_steps: list[str] = Field(..., min_length=1, description="Step-by-step reproduction sequence")
    affected_components: list[str] = Field(..., min_length=1, description="Specific files or services affected")
    proposed_surgical_fix: str = Field(..., min_length=10, description="Minimal, non-invasive code fix proposal")
    prevention_recommendations: list[str] = Field(
        default_factory=list, description="Architectural or testing improvements to prevent recurrence"
    )


class CodeReviewComment(BaseModel):
    """Line-level review remark on a code diff."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., min_length=1)
    line_number: int = Field(..., ge=1)
    comment: str = Field(..., min_length=5)
    severity: Literal["INFO", "WARNING", "BLOCKER"] = Field(default="WARNING")


class CodeReviewProposal(BaseModel):
    """Independent peer review report produced by the Code Reviewer."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["APPROVED", "REJECTED", "CHANGES_REQUESTED"] = Field(..., description="Peer review verdict")
    summary_evaluation: str = Field(..., min_length=10, description="Holistic assessment of patch quality")
    checklist_verifications: dict[str, bool] = Field(
        ..., description="Verification checklist (e.g. tests_pass, no_secrets, typed)"
    )
    line_level_comments: list[CodeReviewComment] = Field(
        default_factory=list, description="Granular code review comments"
    )
    test_coverage_adequate: bool = Field(..., description="Whether tests cover the modified code paths")
