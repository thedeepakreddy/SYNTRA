"""Human approval governance and cryptographic checkpoint resolution endpoints."""

import hashlib
import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import JSONResponse

from syntra.api.auth.dependencies import get_current_user, get_uow, require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.api.v1.schemas import ApprovalDecisionRequest, ApprovalResponse
from syntra.core.config import Settings, get_settings
from syntra.domain.entities import ApprovalActionType, ApprovalDecision, MembershipRole
from syntra.domain.exceptions import DuplicateIdempotencyKeyError, UnauthorizedApprovalError
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    decision: ApprovalDecision | None = None,
    limit: int = 100,
) -> list[ApprovalResponse]:
    """List human approval requests for the caller's organization."""
    approvals = await uow.approvals.list_for_org(org_id=user.org_id, decision=decision, limit=limit)
    return [
        ApprovalResponse(
            id=a.id,
            mission_id=a.mission_id,
            org_id=a.org_id,
            action_type=ApprovalActionType(a.action_type),
            target_resource=a.target_resource,
            mission_version=a.mission_version,
            decision=a.decision,
            action_digest=a.action_digest,
            expires_at=a.expires_at,
            resolved_at=a.resolved_at,
            resolved_by=a.resolved_by,
            reason=a.feedback,
            created_at=a.created_at,
        )
        for a in approvals
    ]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> ApprovalResponse:
    """Retrieve full details for an individual approval request."""
    a = await uow.approvals.get_by_id_for_org(approval_id, user.org_id)
    return ApprovalResponse(
        id=a.id,
        mission_id=a.mission_id,
        org_id=a.org_id,
        action_type=ApprovalActionType(a.action_type),
        target_resource=a.target_resource,
        mission_version=a.mission_version,
        decision=a.decision,
        action_digest=a.action_digest,
        expires_at=a.expires_at,
        resolved_at=a.resolved_at,
        resolved_by=a.resolved_by,
        reason=a.feedback,
        created_at=a.created_at,
    )


def _hash_payload(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
async def submit_approval_decision(
    approval_id: UUID,
    req: ApprovalDecisionRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    """Submit a cryptographic human approval decision for a governance checkpoint.

    Enforces invariants:
    1. Caller authorization (admin or owner only)
    2. Single-use resolution (replay prevention)
    3. Time-limited validity (rejection if expired)
    4. Canonical action digest match (rejection if tampered)
    5. Material modification lock (rejection if mission version changed)
    """
    # 1. RBAC authorization gate: Only Admin or Owner may authorize human gates
    if user.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
        raise UnauthorizedApprovalError(
            f"User with role '{user.role.value}' is not authorized to resolve governance checkpoints. "
            "Requires admin or owner role."
        )

    payload_dict = req.model_dump()
    req_hash = _hash_payload(payload_dict)

    if idempotency_key:
        cached = await uow.idempotency.get(idempotency_key, user.org_id)
        if cached:
            if cached.payload_hash and cached.payload_hash != req_hash:
                raise DuplicateIdempotencyKeyError(
                    f"Idempotency key '{idempotency_key}' already used with different payload."
                )
            return JSONResponse(status_code=cached.response_code, content=cached.response_body)

    # 2. Retrieve approval to inspect bound mission
    approval_entity = await uow.approvals.get_by_id_for_org(approval_id, user.org_id)
    mission = await uow.missions.get_by_id_for_org(approval_entity.mission_id, user.org_id)

    # 3. Resolve decision enforcing all 5 invariants
    resolved = await uow.approvals.resolve_decision(
        approval_id=approval_id,
        org_id=user.org_id,
        user_id=user.user_id,
        decision=req.decision,
        feedback=req.reason,
        secret_key=settings.approval_secret_key,
        current_mission_version=mission.version,
        provided_digest=req.action_digest,
    )

    # 4. Stage transactional outbox event
    uow.publish_event(
        event_type="approval.resolved",
        payload={
            "approval_id": str(resolved.id),
            "mission_id": str(resolved.mission_id),
            "action_type": resolved.action_type,
            "decision": resolved.decision.value,
            "resolved_by": str(user.user_id),
            "reason": req.reason,
        },
    )

    resp_data = ApprovalResponse(
        id=resolved.id,
        mission_id=resolved.mission_id,
        org_id=resolved.org_id,
        action_type=ApprovalActionType(resolved.action_type),
        target_resource=resolved.target_resource,
        mission_version=resolved.mission_version,
        decision=resolved.decision,
        action_digest=resolved.action_digest,
        expires_at=resolved.expires_at,
        resolved_at=resolved.resolved_at,
        resolved_by=resolved.resolved_by,
        reason=resolved.feedback,
        created_at=resolved.created_at,
    ).model_dump(mode="json")

    if idempotency_key:
        await uow.idempotency.record(
            key=idempotency_key,
            org_id=user.org_id,
            response_code=status.HTTP_200_OK,
            response_body=resp_data,
            payload_hash=req_hash,
        )

    await uow.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content=resp_data)
