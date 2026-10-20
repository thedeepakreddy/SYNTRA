"""Deterministic domain state machines and lifecycle transition functions."""

from syntra.domain.entities import (
    ApprovalDecision,
    AttemptState,
    MissionState,
    TaskState,
)
from syntra.domain.exceptions import (
    InvalidStateTransitionError,
    UnauthorizedTaskMutationError,
)

# ==============================================================================
# Mission Transition Rules
# ==============================================================================
MISSION_TRANSITIONS: dict[MissionState, set[MissionState]] = {
    MissionState.DRAFT: {MissionState.PLANNING, MissionState.CANCELLED},
    MissionState.PLANNING: {
        MissionState.AWAITING_APPROVAL,
        MissionState.READY,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.AWAITING_APPROVAL: {
        MissionState.READY,
        MissionState.PLANNING,
        MissionState.COMPLETED,
        MissionState.CANCELLED,
    },
    MissionState.READY: {
        MissionState.RUNNING,
        MissionState.PAUSED,
        MissionState.CANCELLED,
    },
    MissionState.RUNNING: {
        MissionState.PAUSED,
        MissionState.REPLANNING,
        MissionState.VERIFYING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.PAUSED: {
        MissionState.RUNNING,
        MissionState.CANCELLED,
    },
    MissionState.REPLANNING: {
        MissionState.AWAITING_APPROVAL,
        MissionState.READY,
        MissionState.RUNNING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.VERIFYING: {
        MissionState.AWAITING_DELIVERY_APPROVAL,
        MissionState.REPLANNING,
        MissionState.RUNNING,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.AWAITING_DELIVERY_APPROVAL: {
        MissionState.COMPLETED,
        MissionState.REPLANNING,
        MissionState.CANCELLED,
    },
    MissionState.COMPLETED: set(),
    MissionState.FAILED: set(),
    MissionState.CANCELLED: set(),
}


def transition_mission_state(
    current_state: MissionState,
    target_state: MissionState,
    decision_context: ApprovalDecision | None = None,
) -> MissionState:
    """Validate and execute a deterministic state transition for a Mission."""
    allowed_targets = MISSION_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            f"Illegal mission transition from {current_state.value} to {target_state.value}."
        )

    # Authorization context checks
    if current_state == MissionState.AWAITING_APPROVAL and target_state in (MissionState.READY, MissionState.COMPLETED):
        if decision_context != ApprovalDecision.APPROVED:
            raise InvalidStateTransitionError(
                f"Transition from {current_state.value} to {target_state.value} requires APPROVED decision context, got {decision_context}."
            )

    if current_state == MissionState.AWAITING_DELIVERY_APPROVAL and target_state == MissionState.COMPLETED:
        if decision_context != ApprovalDecision.APPROVED:
            raise InvalidStateTransitionError(
                f"Transition from {current_state.value} to {target_state.value} requires APPROVED decision context, got {decision_context}."
            )

    return target_state


# ==============================================================================
# Task Transition Rules
# ==============================================================================
TASK_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.READY, TaskState.CANCELLED},
    TaskState.READY: {TaskState.ASSIGNED, TaskState.CANCELLED},
    TaskState.ASSIGNED: {TaskState.IN_PROGRESS, TaskState.READY, TaskState.CANCELLED},
    TaskState.IN_PROGRESS: {
        TaskState.BLOCKED,
        TaskState.REVIEW,
        TaskState.VERIFYING,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.BLOCKED: {TaskState.READY, TaskState.CANCELLED},
    TaskState.REVIEW: {
        TaskState.VERIFYING,
        TaskState.IN_PROGRESS,
        TaskState.FAILED,
    },
    TaskState.VERIFYING: {
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.IN_PROGRESS,
    },
    TaskState.COMPLETED: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}


def transition_task_state(
    current_state: TaskState,
    target_state: TaskState,
    actor_type: str = "orchestrator",
) -> TaskState:
    """Validate and execute a deterministic state transition for a Task.

    Invariants:
    - Agents cannot mutate task status directly. Only the scheduler, orchestrator, or verifier can.
    """
    if actor_type == "agent":
        raise UnauthorizedTaskMutationError(
            "Agents cannot mutate task status directly; task transitions are strictly governed by the scheduler and verifier."
        )

    allowed_targets = TASK_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            f"Illegal task transition from {current_state.value} to {target_state.value}."
        )

    return target_state


# ==============================================================================
# Attempt Transition Rules
# ==============================================================================
ATTEMPT_TRANSITIONS: dict[AttemptState, set[AttemptState]] = {
    AttemptState.INITIALIZING: {AttemptState.RUNNING, AttemptState.FAILED},
    AttemptState.RUNNING: {
        AttemptState.AWAITING_TOOL,
        AttemptState.EVALUATING,
        AttemptState.SUCCEEDED,
        AttemptState.FAILED,
        AttemptState.TIMED_OUT,
    },
    AttemptState.AWAITING_TOOL: {
        AttemptState.RUNNING,
        AttemptState.FAILED,
        AttemptState.TIMED_OUT,
    },
    AttemptState.EVALUATING: {
        AttemptState.SUCCEEDED,
        AttemptState.FAILED,
    },
    AttemptState.SUCCEEDED: set(),
    AttemptState.FAILED: set(),
    AttemptState.TIMED_OUT: set(),
}


def transition_attempt_state(
    current_state: AttemptState,
    target_state: AttemptState,
) -> AttemptState:
    """Validate and execute a deterministic state transition for a Task Attempt."""
    allowed_targets = ATTEMPT_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidStateTransitionError(
            f"Illegal task attempt transition from {current_state.value} to {target_state.value}."
        )

    return target_state
