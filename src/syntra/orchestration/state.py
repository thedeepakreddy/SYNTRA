"""Typed state definitions for LangGraph Mission and Task workflows."""

from __future__ import annotations

from typing import Any, TypedDict


class MissionWorkflowState(TypedDict, total=False):
    """Execution state for the macro Mission workflow graph."""

    # 1. Identity & Tenancy
    mission_id: str
    org_id: str
    mission_version: int
    thread_id: str

    # 2. Lifecycle & Domain State
    current_phase: str  # e.g. INTAKE, REQUIREMENTS_ANALYSIS, AWAITING_APPROVAL, etc.
    domain_state: str  # Authoritative MissionState: DRAFT, PLANNING, READY, RUNNING, etc.

    # 3. Input & High-level Objectives
    objective: str
    context_files: list[str]

    # 4. Specifications & Artifact References (Bounded Payloads)
    prd_summary: str | None
    prd_artifact_id: str | None
    architecture_summary: str | None
    architecture_artifact_id: str | None
    task_dag: list[dict[str, Any]]
    plan_digest: str | None
    prd_handoff: dict[str, Any]
    architecture_handoff: dict[str, Any]
    plan_handoff: dict[str, Any]

    # 5. Approval Governance & Interruption Context
    active_approval_id: str | None
    approval_action_type: str | None
    approval_decision: str | None
    approval_feedback: str | None
    approval_secret_key: str | None

    # 6. Task Tracking & Coordination
    pending_task_ids: list[str]
    running_task_ids: list[str]
    completed_task_ids: list[str]
    failed_task_ids: list[str]

    # 7. Delivery & Verification Outcomes
    delivery_digest: str | None
    integration_artifact_id: str | None
    verification_passed: bool | None
    error_message: str | None
    replan_count: int
    max_replan_limit: int

    # 8. Control Signals & Side-effect Boundaries
    control_signal: str | None  # PAUSE | CANCEL | REPLAN | None
    executed_nodes: list[str]
    idempotency_keys: dict[str, str]
    advisory_memory_context: str | None


class TaskExecutionState(TypedDict, total=False):
    """Execution state for micro Task execution workflows."""

    # 1. Task Identity
    task_id: str
    mission_id: str
    org_id: str
    thread_id: str
    attempt_number: int

    # 2. Stage & Task Status
    current_stage: str  # PREPARE_CONTEXT, RESOLVE_SKILLS, EXECUTE_AGENT, etc.
    task_state: str  # Authoritative TaskState: PENDING, ASSIGNED, IN_PROGRESS, REVIEW, etc.

    # 3. Specification & Role
    agent_role: str
    objective: str
    task_specification: str

    # 4. Capabilities & Skills
    requested_skills: list[str]
    loaded_skills: list[str]
    active_grants: list[str]

    # 5. Telemetry & Cost Accounting
    context_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float

    # 6. Outputs & Artifacts
    output_text: str | None
    unified_diff: str | None
    produced_artifact_ids: list[str]

    # 7. Review & Verification
    review_verdict: str | None  # APPROVED | REJECTED
    review_comments: list[str]
    verification_outcome: str | None  # SUCCESS | FAILED
    error_message: str | None

    # 8. Test Adapter Flag
    is_test_adapter: bool
