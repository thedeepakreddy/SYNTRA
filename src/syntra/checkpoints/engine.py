"""Checkpoint governance engine: pause, await human decision, and resume execution."""

import asyncio
import logging
from typing import Any

from syntra.checkpoints.models import (
    Checkpoint,
    CheckpointActionType,
    CheckpointStatus,
    RiskLevel,
)
from syntra.checkpoints.policies import CheckpointPolicy
from syntra.core.config import AutonomyMode, get_settings
from syntra.core.events import Event, EventType, get_event_bus
from syntra.core.exceptions import CheckpointError

logger = logging.getLogger(__name__)


class CheckpointEngine:
    """Orchestrates human-in-the-loop checkpoints and workflow suspension."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}
        self._resolution_events: dict[str, asyncio.Event] = {}

    def should_checkpoint(
        self,
        action_type: CheckpointActionType,
        command: str | None = None,
        path: str | None = None,
        custom_mode: AutonomyMode | None = None,
    ) -> tuple[bool, RiskLevel]:
        """Check if an action requires human intervention under current policy."""
        mode = custom_mode or get_settings().autonomy_mode
        risk = CheckpointPolicy.evaluate_risk(action_type=action_type, command=command, path=path)
        required = CheckpointPolicy.should_require_checkpoint(mode=mode, action_type=action_type, risk_level=risk)
        return required, risk

    async def create_checkpoint(
        self,
        session_id: str,
        agent_id: str,
        agent_role: str,
        action_type: CheckpointActionType,
        description: str,
        risk_level: RiskLevel | None = None,
        proposed_diff: str | None = None,
        proposed_command: str | None = None,
        target_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Create and register a new checkpoint, notifying subscribers."""
        calculated_risk = risk_level or CheckpointPolicy.evaluate_risk(
            action_type=action_type,
            command=proposed_command,
            path=target_path,
        )

        cp = Checkpoint(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            action_type=action_type,
            description=description,
            risk_level=calculated_risk,
            proposed_diff=proposed_diff,
            proposed_command=proposed_command,
            target_path=target_path,
            metadata=metadata or {},
        )

        self._checkpoints[cp.checkpoint_id] = cp
        self._resolution_events[cp.checkpoint_id] = asyncio.Event()

        # Publish event
        await get_event_bus().publish(
            Event(
                type=EventType.CHECKPOINT_REQUESTED,
                session_id=session_id,
                agent_id=agent_id,
                agent_role=agent_role,
                data={
                    "checkpoint_id": cp.checkpoint_id,
                    "action_type": cp.action_type.value,
                    "risk_level": cp.risk_level.value,
                    "description": cp.description,
                    "proposed_command": cp.proposed_command,
                    "target_path": cp.target_path,
                },
            )
        )

        return cp

    async def wait_for_resolution(self, checkpoint_id: str, timeout: float | None = None) -> Checkpoint:
        """Block until the checkpoint is resolved by human operator."""
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' not found.")

        if cp.status != CheckpointStatus.PENDING:
            return cp

        event = self._resolution_events.get(checkpoint_id)
        if not event:
            raise CheckpointError(f"No resolution event registered for '{checkpoint_id}'.")

        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()
        except TimeoutError:
            cp.status = CheckpointStatus.CANCELLED
            cp.human_feedback = "Checkpoint resolution timed out."
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' timed out waiting for human resolution.")

        return cp

    async def resolve(
        self,
        checkpoint_id: str,
        decision: str,
        feedback: str | None = None,
        modified_payload: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Resolve a pending checkpoint with APPROVE, REJECT, or MODIFY."""
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' not found.")

        if cp.status != CheckpointStatus.PENDING:
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' has already been resolved as {cp.status.value}.")

        decision_clean = decision.lower()
        if decision_clean in ("approve", "approved"):
            cp.approve(feedback=feedback)
        elif decision_clean in ("reject", "rejected"):
            if not feedback:
                raise CheckpointError("Rejection requires explicit corrective feedback for the agent.")
            cp.reject(feedback=feedback)
        elif decision_clean in ("modify", "modified"):
            cp.modify(modified_payload=modified_payload or {}, feedback=feedback)
        else:
            raise CheckpointError(f"Invalid resolution decision '{decision}'. Use approve, reject, or modify.")

        # Wake up waiting task
        if checkpoint_id in self._resolution_events:
            self._resolution_events[checkpoint_id].set()

        # Publish resolution event
        await get_event_bus().publish(
            Event(
                type=EventType.CHECKPOINT_RESOLVED,
                session_id=cp.session_id,
                agent_id=cp.agent_id,
                agent_role=cp.agent_role,
                data={
                    "checkpoint_id": cp.checkpoint_id,
                    "status": cp.status.value,
                    "feedback": cp.human_feedback,
                },
            )
        )

        return cp

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Get checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(
        self,
        session_id: str | None = None,
        status: CheckpointStatus | None = None,
    ) -> list[Checkpoint]:
        """List checkpoints matching optional filters."""
        cps = list(self._checkpoints.values())
        if session_id:
            cps = [c for c in cps if c.session_id == session_id]
        if status:
            cps = [c for c in cps if c.status == status]
        return sorted(cps, key=lambda c: c.created_at, reverse=True)


# Global singleton
_checkpoint_engine: CheckpointEngine | None = None


def get_checkpoint_engine() -> CheckpointEngine:
    """Retrieve the global CheckpointEngine singleton."""
    global _checkpoint_engine
    if _checkpoint_engine is None:
        _checkpoint_engine = CheckpointEngine()
    return _checkpoint_engine
