"""Workspace inspection endpoints."""

from fastapi import APIRouter, HTTPException, Query

from syntra.api.routes.sessions import get_active_swarm
from syntra.api.schemas import WorkspaceFileResponse

router = APIRouter(prefix="/api/sessions/{session_id}/files", tags=["workspace"])


@router.get("")
async def list_workspace_files(session_id: str, tree: bool = Query(default=False)) -> dict:
    """List all files or directory tree of the session workspace."""
    swarm = get_active_swarm(session_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"No active workspace found for session '{session_id}'.")

    if tree:
        return {"tree": swarm.workspace.get_tree()}
    else:
        return {"files": swarm.workspace.list_files()}


@router.get("/{file_path:path}", response_model=WorkspaceFileResponse)
async def read_workspace_file(session_id: str, file_path: str) -> WorkspaceFileResponse:
    """Read a specific file from the session's isolated workspace."""
    swarm = get_active_swarm(session_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"No active workspace found for session '{session_id}'.")

    if not swarm.workspace.file_exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{file_path}' does not exist in workspace.")

    content = swarm.workspace.read_file(file_path)
    return WorkspaceFileResponse(
        path=file_path,
        content=content,
        size_bytes=len(content.encode("utf-8")),
    )
