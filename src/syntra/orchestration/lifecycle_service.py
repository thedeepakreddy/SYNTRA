"""Lifecycle operations: pause, resume, cancel, recover, and reconcile missions.

Maintains strict consistency between LangGraph execution checkpoints and authoritative
PostgreSQL domain state records, transactional outbox events, and task states.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from syntra.domain.entities import MissionState, TaskState
from syntra.domain.exceptions import InvalidStateTransitionError
from syntra.domain.state_machines import transition_mission_state
from syntra.orchestration.checkpointer import build_mission_thread_id
from syntra.persistence.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


async def pause_mission(
    mission_id: UUID,
    org_id: UUID,
    reason: str,
    uow: UnitOfWork | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Halt active mission scheduling and persist PAUSED state."""
    thread_id = build_mission_thread_id(mission_id)
    current_state_val = MissionState.RUNNING.value

    if uow:
        mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
        current_state_val = mission.state.value if hasattr(mission.state, "value") else str(mission.state)
        curr = MissionState(current_state_val)
        target = transition_mission_state(curr, MissionState.PAUSED)
        mission.state = target

        # Emit outbox event
        uow.publish_event(
            event_type="MISSION_PAUSED",
            payload={
                "aggregate_type": "mission",
                "aggregate_id": str(mission_id),
                "mission_id": str(mission_id),
                "org_id": str(org_id),
                "reason": reason,
                "previous_state": current_state_val,
            },
        )
        await uow.commit()

    if checkpointer:
        config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            current_checkpoint_state = dict(checkpoint_tuple.checkpoint.get("channel_values", {}))
            current_checkpoint_state["control_signal"] = "PAUSE"
            current_checkpoint_state["domain_state"] = MissionState.PAUSED.value
            current_checkpoint_state["current_phase"] = "PAUSED"

    logger.info("Mission %s paused successfully (reason: %s)", mission_id, reason)
    return {
        "mission_id": str(mission_id),
        "status": MissionState.PAUSED.value,
        "previous_state": current_state_val,
        "reason": reason,
    }


async def resume_mission(
    mission_id: UUID,
    org_id: UUID,
    uow: UnitOfWork | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Resume execution of a paused mission."""
    thread_id = build_mission_thread_id(mission_id)
    current_state_val = MissionState.PAUSED.value

    if uow:
        mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
        current_state_val = mission.state.value if hasattr(mission.state, "value") else str(mission.state)
        curr = MissionState(current_state_val)
        target = transition_mission_state(curr, MissionState.RUNNING)
        mission.state = target

        uow.publish_event(
            event_type="MISSION_RESUMED",
            payload={
                "aggregate_type": "mission",
                "aggregate_id": str(mission_id),
                "mission_id": str(mission_id),
                "org_id": str(org_id),
                "previous_state": current_state_val,
            },
        )
        await uow.commit()

    if checkpointer:
        config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            current_checkpoint_state = dict(checkpoint_tuple.checkpoint.get("channel_values", {}))
            current_checkpoint_state["control_signal"] = None
            current_checkpoint_state["domain_state"] = MissionState.RUNNING.value

    logger.info("Mission %s resumed successfully", mission_id)
    return {
        "mission_id": str(mission_id),
        "status": MissionState.RUNNING.value,
        "previous_state": current_state_val,
    }


async def cancel_mission(
    mission_id: UUID,
    org_id: UUID,
    reason: str,
    uow: UnitOfWork | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Permanently abort mission execution and cancel pending tasks."""
    thread_id = build_mission_thread_id(mission_id)
    current_state_val = MissionState.RUNNING.value

    if uow:
        mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
        current_state_val = mission.state.value if hasattr(mission.state, "value") else str(mission.state)
        curr = MissionState(current_state_val)

        if curr in {MissionState.COMPLETED, MissionState.FAILED, MissionState.CANCELLED}:
            raise InvalidStateTransitionError(
                f"Cannot cancel mission {mission_id} in terminal state {current_state_val}."
            )

        target = transition_mission_state(curr, MissionState.CANCELLED)
        mission.state = target

        # Cancel all pending tasks for mission in DB
        tasks, _, _ = await uow.tasks.list_for_mission(mission_id=mission_id, org_id=org_id)
        for t in tasks:
            if t.state in {TaskState.PENDING, TaskState.READY, TaskState.ASSIGNED, TaskState.BLOCKED}:
                t.state = TaskState.CANCELLED

        uow.publish_event(
            event_type="MISSION_CANCELLED",
            payload={
                "aggregate_type": "mission",
                "aggregate_id": str(mission_id),
                "mission_id": str(mission_id),
                "org_id": str(org_id),
                "reason": reason,
                "previous_state": current_state_val,
            },
        )
        await uow.commit()

    if checkpointer:
        config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            current_checkpoint_state = dict(checkpoint_tuple.checkpoint.get("channel_values", {}))
            current_checkpoint_state["control_signal"] = "CANCEL"
            current_checkpoint_state["domain_state"] = MissionState.CANCELLED.value
            current_checkpoint_state["current_phase"] = "CANCELLED"

    logger.info("Mission %s cancelled successfully (reason: %s)", mission_id, reason)
    return {
        "mission_id": str(mission_id),
        "status": MissionState.CANCELLED.value,
        "previous_state": current_state_val,
        "reason": reason,
    }


async def recover_mission(
    mission_id: UUID,
    org_id: UUID,
    uow: UnitOfWork | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Reconstruct execution state after process crash from DB and checkpoint."""
    thread_id = build_mission_thread_id(mission_id)
    recovered_from = "DATABASE"

    domain_state = MissionState.DRAFT.value
    mission_version = 1
    objective = ""

    if uow:
        mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
        domain_state = mission.state.value if hasattr(mission.state, "value") else str(mission.state)
        mission_version = getattr(mission, "version", 1)
        objective = getattr(mission, "objective", "")

    checkpoint_state: dict[str, Any] = {}
    if checkpointer:
        config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            recovered_from = "CHECKPOINT_AND_DATABASE"
            checkpoint_state = dict(checkpoint_tuple.checkpoint.get("channel_values", {}))

    return {
        "mission_id": str(mission_id),
        "org_id": str(org_id),
        "thread_id": thread_id,
        "domain_state": domain_state,
        "mission_version": mission_version,
        "objective": objective,
        "recovered_from": recovered_from,
        "checkpoint_state": checkpoint_state,
    }


async def reconcile_mission(
    mission_id: UUID,
    org_id: UUID,
    uow: UnitOfWork | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Reconcile discrepancies between ephemeral LangGraph checkpoints and PostgreSQL.

    PostgreSQL domain state remains absolute and authoritative.
    """
    thread_id = build_mission_thread_id(mission_id)

    if not uow:
        return {"reconciled": False, "reason": "No authoritative database UnitOfWork provided."}

    mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
    authoritative_state = mission.state.value if hasattr(mission.state, "value") else str(mission.state)

    graph_state: str | None = None
    desynchronized = False

    if checkpointer:
        config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
            graph_state = channel_values.get("domain_state")
            if graph_state and graph_state != authoritative_state:
                desynchronized = True
                # Reconcile graph state to authoritative DB state
                channel_values["domain_state"] = authoritative_state
                channel_values["current_phase"] = authoritative_state

    if desynchronized:
        logger.warning(
            "Reconciled desynchronized graph state '%s' to DB authoritative state '%s' for mission %s",
            graph_state,
            authoritative_state,
            mission_id,
        )

    return {
        "mission_id": str(mission_id),
        "authoritative_state": authoritative_state,
        "graph_state": graph_state or authoritative_state,
        "desynchronized": desynchronized,
        "reconciled": True,
    }
