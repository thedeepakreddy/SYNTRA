"""Session management and autonomous execution endpoints."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Query

from syntra.api.schemas import (
    CreateSessionRequest,
    RunTaskRequest,
    SessionResponse,
)
from syntra.storage.database import get_db_manager
from syntra.storage.repositories import SessionRepository
from syntra.swarm.engine import SwarmEngine

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Active running swarms cache: session_id -> SwarmEngine
_active_swarms: dict[str, SwarmEngine] = {}


def get_active_swarm(session_id: str) -> SwarmEngine | None:
    return _active_swarms.get(session_id)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(req: CreateSessionRequest) -> SessionResponse:
    """Create a new autonomous engineering session."""
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    db_manager = get_db_manager()

    async with db_manager.session() as db:
        repo = SessionRepository(db)
        model = await repo.create(
            session_id=session_id,
            objective=req.objective,
            autonomy_mode=req.autonomy_mode.value,
            metadata={"workspace_dir": req.workspace_dir},
        )
        created_at_str = model.created_at.isoformat()

    # Pre-warm SwarmEngine
    swarm = SwarmEngine(
        workspace_dir=req.workspace_dir,
        session_id=session_id,
        autonomy_mode=req.autonomy_mode,
    )
    _active_swarms[session_id] = swarm

    return SessionResponse(
        session_id=session_id,
        objective=req.objective,
        status="created",
        autonomy_mode=req.autonomy_mode.value,
        created_at=created_at_str,
    )


@router.get("", response_model=list[SessionResponse])
async def list_sessions(limit: int = Query(default=50, ge=1, le=100)) -> list[SessionResponse]:
    """List recent sessions."""
    db_manager = get_db_manager()
    async with db_manager.session() as db:
        repo = SessionRepository(db)
        records = await repo.list_recent(limit=limit)

        return [
            SessionResponse(
                session_id=r.id,
                objective=r.objective,
                status=r.status,
                autonomy_mode=r.autonomy_mode,
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Retrieve details for a specific session."""
    db_manager = get_db_manager()
    async with db_manager.session() as db:
        repo = SessionRepository(db)
        record = await repo.get_by_id(session_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        return SessionResponse(
            session_id=record.id,
            objective=record.objective,
            status=record.status,
            autonomy_mode=record.autonomy_mode,
            created_at=record.created_at.isoformat(),
        )


@router.post("/{session_id}/run")
async def run_session(session_id: str, req: RunTaskRequest) -> dict:
    """Trigger multi-agent swarm execution for a session."""
    db_manager = get_db_manager()
    async with db_manager.session() as db:
        repo = SessionRepository(db)
        record = await repo.get_by_id(session_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
        objective = req.objective or record.objective
        await repo.update_status(session_id, "running")

    swarm = _active_swarms.get(session_id)
    if not swarm:
        swarm = SwarmEngine(session_id=session_id, autonomy_mode=req.autonomy_mode)
        _active_swarms[session_id] = swarm

    # Run execution in background task to avoid blocking HTTP worker
    async def _execute_swarm():
        try:
            state = await swarm.execute_task(
                objective=objective,
                max_iterations=req.max_iterations,
                autonomy_mode=req.autonomy_mode,
            )
            new_status = "completed" if state.is_completed and not state.error else "failed"
        except Exception:
            new_status = "failed"

        async with db_manager.session() as sess_db:
            repo_inner = SessionRepository(sess_db)
            await repo_inner.update_status(session_id, new_status)

    asyncio.create_task(_execute_swarm())

    return {
        "status": "started",
        "session_id": session_id,
        "objective": objective,
        "message": "Swarm workflow started in background. Monitor progress via /ws/events or GET /api/sessions/{session_id}.",
    }
