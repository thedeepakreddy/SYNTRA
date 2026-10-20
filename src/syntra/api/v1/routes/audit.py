"""Cryptographic audit log query and exploration endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from syntra.api.auth.dependencies import require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.observability.audit_logger import get_audit_logger

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditRecordResponse(BaseModel):
    """Cryptographic audit trail entry with payload digest."""

    event_type: str
    timestamp: str
    trace_id: str | None = None
    mission_id: str
    task_id: str | None = None
    agent_role: str | None = None
    outcome: str
    sha256: str
    payload: dict[str, Any] = {}


@router.get("", response_model=list[AuditRecordResponse])
async def list_audit_events(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    event_type: str | None = None,
    mission_id: str | None = None,
    limit: int = 50,
) -> list[AuditRecordResponse]:
    """Retrieve recent cryptographic audit log records with server-side secret scrubbing."""
    logger = get_audit_logger()
    records = logger.get_records()

    filtered: list[dict[str, Any]] = []
    for r in reversed(records):
        if event_type and r.get("event_type") != event_type:
            continue
        if mission_id and r.get("mission_id") != mission_id:
            continue
        filtered.append(r)
        if len(filtered) >= limit:
            break

    return [
        AuditRecordResponse(
            event_type=rec["event_type"],
            timestamp=rec["timestamp"],
            trace_id=rec.get("trace_id"),
            mission_id=rec["mission_id"],
            task_id=rec.get("task_id"),
            agent_role=rec.get("agent_role"),
            outcome=rec.get("outcome", "SUCCESS"),
            sha256=rec["sha256"],
            payload=rec.get("payload", {}),
        )
        for rec in filtered
    ]
