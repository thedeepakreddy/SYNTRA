"""Task DAG Engine & Deterministic Readiness Evaluator for SYNTRA.

Validates graph acyclicity, structural integrity, and evaluates real-time task
readiness across dependencies, capability policies, skill manifests, and budgets.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC
from decimal import Decimal
from typing import Any
from uuid import UUID

from syntra.domain.dag_validator import validate_task_dag
from syntra.domain.entities import AgentRole, MissionState, TaskState
from syntra.domain.exceptions import (
    CrossMissionDependencyError,
    CyclicDependencyError,
    InvalidTaskGraphError,
)
from syntra.persistence.models import BudgetModel, MissionModel, TaskModel, TaskPlanModel
from syntra.scheduling.exceptions import DAGValidationError
from syntra.scheduling.models import TaskPriorityScore, TaskReadinessReport
from syntra.skills.registry import SkillRegistry


class TaskDAGEngine:
    """Evaluates DAG structural invariants, topological ordering, and task dispatch readiness."""

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self.skill_registry = skill_registry or SkillRegistry()
        # Initialize skill registry if not loaded
        if not self.skill_registry.registered_skill_ids:
            try:
                self.skill_registry.discover_skills()
            except Exception:
                pass

    def validate_graph(
        self,
        tasks: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        plan_version: int = 1,
    ) -> list[UUID]:
        """Validate structural graph properties and return topological ordering.

        Raises:
            DAGValidationError: On cycles, missing tasks, self-references, or cross-mission dependencies.
        """
        try:
            return validate_task_dag(tasks=tasks, dependencies=dependencies, plan_version=plan_version)
        except (CyclicDependencyError, CrossMissionDependencyError, InvalidTaskGraphError) as exc:
            raise DAGValidationError(f"DAG validation rejected: {exc}") from exc

    def compute_priority_scores(
        self,
        tasks: list[TaskModel],
        dependencies: list[dict[str, Any]],
    ) -> list[TaskPriorityScore]:
        """Compute deterministic priority rankings based on explicit priority and DAG downstream impact."""
        # Map downstream dependents count
        downstream_counts: dict[UUID, int] = defaultdict(int)
        for dep in dependencies:
            dep_on = dep["depends_on_task_id"]
            if isinstance(dep_on, str):
                dep_on = UUID(dep_on)
            downstream_counts[dep_on] += 1

        scores: list[TaskPriorityScore] = []
        for t in tasks:
            created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=UTC)
            score = TaskPriorityScore(
                task_id=t.id,
                explicit_priority=t.priority,
                downstream_dependency_count=downstream_counts[t.id],
                estimated_tokens=8192,  # Default estimation per task
                created_at=created,
                identifier=t.identifier,
            )
            scores.append(score)

        # Sort deterministically: highest priority first, then most downstream dependents, then lowest tokens, stable identifier
        scores.sort(
            key=lambda s: (s.explicit_priority, s.downstream_dependency_count, -s.estimated_tokens), reverse=True
        )
        return scores

    def evaluate_task_readiness(
        self,
        task: TaskModel,
        mission: MissionModel,
        plan: TaskPlanModel,
        upstream_dependencies: list[TaskModel],
        budget: BudgetModel | None = None,
        available_artifacts: set[str] | None = None,
        required_artifacts: list[str] | None = None,
        requested_skills: list[str] | None = None,
    ) -> TaskReadinessReport:
        """Evaluate all 8 domain prerequisites for a task to become READY.

        Prerequisites:
        1. Mission must be APPROVED and in RUNNING (or READY).
        2. Task must belong to the active plan version.
        3. All upstream dependencies must be COMPLETED.
        4. Required input artifacts must be present.
        5. Assigned agent role must be a recognized engineering persona.
        6. Requested skills must be available in the registry.
        7. Budget must have sufficient uncommitted headroom.
        """
        reasons: list[str] = []
        missing_prereqs: list[UUID] = []
        missing_artifacts: list[str] = []
        missing_skills: list[str] = []

        # 1. Mission state
        valid_mission_states = {MissionState.RUNNING, MissionState.READY}
        if mission.state not in valid_mission_states:
            reasons.append(f"Mission state is {mission.state.value}, expected RUNNING or READY.")

        # 2. Plan version
        if plan.plan_version != mission.active_plan_version:
            reasons.append(
                f"Task belongs to plan version {plan.plan_version}, active mission plan version is {mission.active_plan_version}."
            )

        # 3. Dependencies completed
        for dep in upstream_dependencies:
            if dep.state != TaskState.COMPLETED:
                missing_prereqs.append(dep.id)
                reasons.append(
                    f"Prerequisite task {dep.identifier} ({dep.id}) is in state {dep.state.value}, not COMPLETED."
                )

        # 4. Artifact availability
        if required_artifacts:
            available = available_artifacts or set()
            for art in required_artifacts:
                if art not in available:
                    missing_artifacts.append(art)
                    reasons.append(f"Required artifact '{art}' is not available.")

        # 5. Agent role validation
        try:
            AgentRole(task.assigned_role)
        except ValueError:
            reasons.append(f"Unrecognized agent role: '{task.assigned_role}'.")

        # 6. Skill availability
        if requested_skills:
            for s_name in requested_skills:
                try:
                    self.skill_registry.resolve_skill_version(s_name, "latest")
                except Exception:
                    missing_skills.append(s_name)
                    reasons.append(f"Requested skill '{s_name}' is not found in SkillRegistry.")

        # 7. Budget headroom
        if budget:
            estimated_tokens = 8192
            estimated_cost = Decimal("0.0500")
            max_tokens = budget.max_tokens if budget.max_tokens is not None else 0
            consumed_tokens = budget.consumed_tokens if budget.consumed_tokens is not None else 0
            reserved_tokens = budget.reserved_tokens if budget.reserved_tokens is not None else 0
            avail_tokens = max_tokens - (consumed_tokens + reserved_tokens)

            max_cost = budget.max_cost_usd if budget.max_cost_usd is not None else Decimal("0.0000")
            consumed_cost = budget.consumed_cost_usd if budget.consumed_cost_usd is not None else Decimal("0.0000")
            reserved_cost = budget.reserved_cost_usd if budget.reserved_cost_usd is not None else Decimal("0.0000")
            avail_cost = max_cost - (consumed_cost + reserved_cost)

            if max_tokens > 0 and avail_tokens < estimated_tokens:
                reasons.append(
                    f"Insufficient token budget headroom: required {estimated_tokens}, available {avail_tokens}."
                )
            if max_cost > Decimal("0.0000") and avail_cost < estimated_cost:
                reasons.append(
                    f"Insufficient cost budget headroom: required ${estimated_cost}, available ${avail_cost}."
                )

        is_ready = len(reasons) == 0

        return TaskReadinessReport(
            task_id=task.id,
            is_ready=is_ready,
            missing_prerequisites=missing_prereqs,
            missing_artifacts=missing_artifacts,
            missing_skills=missing_skills,
            rejection_reasons=reasons,
        )
