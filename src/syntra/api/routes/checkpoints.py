"""Checkpoint governance endpoints for hybrid autonomy."""

from fastapi import APIRouter, HTTPException, Query
from syntra.api.schemas import (
    CheckpointResolveRequest,
    CheckpointResponse,
)
from syntra.checkpoints.engine import get_checkpoint_engine
from syntra.checkpoints.models import CheckpointStatus
from syntra.core.exceptions import CheckpointError

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])


@router.get("", response_model=list[CheckpointResponse])
async def list_checkpoints(
    session_id: str | None = None,
    status: CheckpointStatus | None = None,
) -> list[CheckpointResponse]:
    """List pending or past checkpoints."""
    engine = get_checkpoint_engine()
    cps = engine.list_checkpoints(session_id=session_id, status=status)

    return [
        CheckpointResponse(
            checkpoint_id=cp.checkpoint_id,
            session_id=cp.session_id,
            agent_id=cp.agent_id,
            agent_role=cp.agent_role,
            action_type=cp.action_type.value,
            risk_level=cp.risk_level.value,
            description=cp.description,
            status=cp.status.value,
            proposed_diff=cp.proposed_diff,
            proposed_command=cp.proposed_command,
            target_path=cp.target_path,
            human_feedback=cp.human_feedback,
            created_at=cp.created_at.isoformat(),
        )
        for cp in cps
    ]


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(checkpoint_id: str) -> CheckpointResponse:
    """Retrieve details of a single checkpoint."""
    engine = get_checkpoint_engine()
    cp = engine.get_checkpoint(checkpoint_id)
    if not cp:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found.")

    return CheckpointResponse(
        checkpoint_id=cp.checkpoint_id,
        session_id=cp.session_id,
        agent_id=cp.agent_id,
        agent_role=cp.agent_role,
        action_type=cp.action_type.value,
        risk_level=cp.risk_level.value,
        description=cp.description,
        status=cp.status.value,
        proposed_diff=cp.proposed_diff,
        proposed_command=cp.proposed_command,
        target_path=cp.target_path,
        human_feedback=cp.human_feedback,
        created_at=cp.created_at.isoformat(),
    )


@router.post("/{checkpoint_id}/resolve", response_model=CheckpointResponse)
async def resolve_checkpoint(
    checkpoint_id: str,
    req: CheckpointResolveRequest,
) -> CheckpointResponse:
    """Resolve a pending checkpoint with approve, reject, or modify."""
    engine = get_checkpoint_engine()
    try:
        resolved = await engine.resolve(
            checkpoint_id=checkpoint_id,
            decision=req.decision,
            feedback=req.feedback,
            modified_payload=req.modified_payload,
        )
    except CheckpointError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CheckpointResponse(
        checkpoint_id=resolved.checkpoint_id,
        session_id=resolved.session_id,
        agent_id=resolved.agent_id,
        agent_role=resolved.agent_role,
        action_type=resolved.action_type.value,
        risk_level=resolved.risk_level.value,
        description=resolved.description,
        status=resolved.status.value,
        proposed_diff=resolved.proposed_diff,
        proposed_command=resolved.proposed_command,
        target_path=resolved.target_path,
        human_feedback=resolved.human_feedback,
        created_at=resolved.created_at.isoformat(),
    )
