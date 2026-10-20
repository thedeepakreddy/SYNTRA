"""RFC 7807 Problem Details for HTTP APIs error representation and handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from syntra.core.logging import correlation_id_ctx
from syntra.core.redactor import SecretRedactor
from syntra.domain.exceptions import (
    ApprovalExpiredError,
    ApprovalReplayError,
    ApprovalTamperedError,
    ArtifactOwnershipError,
    BudgetExceededError,
    CrossTenantAccessError,
    DigestMismatchError,
    DomainError,
    DuplicateIdempotencyKeyError,
    OptimisticLockError,
    UnauthorizedApprovalError,
)

logger = logging.getLogger(__name__)


def create_problem_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    problem_type: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Construct an RFC 7807 compliant JSONResponse with fail-closed secret redaction."""
    clean_title = SecretRedactor.redact(title) if isinstance(title, str) else str(title)
    clean_detail = SecretRedactor.redact_deep_json_or_text(detail) if isinstance(detail, str) else str(detail)
    payload: dict[str, Any] = {
        "type": problem_type,
        "title": clean_title,
        "status": status_code,
        "detail": clean_detail,
        "instance": instance,
        "correlation_id": correlation_id_ctx.get(),
    }
    if extra:
        redacted_extra = SecretRedactor.redact_sensitive_data(extra)
        if isinstance(redacted_extra, dict):
            payload.update(redacted_extra)

    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain and framework exception handlers to output RFC 7807 problem details."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
        return create_problem_response(
            status_code=exc.status_code,
            title=title,
            detail=str(exc.detail),
            instance=request.url.path,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Validation Error",
            detail="The request body or parameters failed schema validation.",
            instance=request.url.path,
            extra={"invalid_params": exc.errors()},
        )

    @app.exception_handler(CrossTenantAccessError)
    async def cross_tenant_handler(request: Request, exc: CrossTenantAccessError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Cross-Tenant Access Prohibited",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/cross-tenant-access",
        )

    @app.exception_handler(DigestMismatchError)
    async def digest_mismatch_handler(request: Request, exc: DigestMismatchError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Action Digest Mismatch",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/digest-mismatch",
        )

    @app.exception_handler(ApprovalExpiredError)
    async def approval_expired_handler(request: Request, exc: ApprovalExpiredError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_410_GONE,
            title="Approval Expired",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/approval-expired",
        )

    @app.exception_handler(ApprovalReplayError)
    async def approval_replay_handler(request: Request, exc: ApprovalReplayError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Approval Replay Prohibited",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/approval-replay",
        )

    @app.exception_handler(ApprovalTamperedError)
    async def approval_tampered_handler(request: Request, exc: ApprovalTamperedError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Approval Tampered",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/approval-tampered",
        )

    @app.exception_handler(UnauthorizedApprovalError)
    async def unauthorized_approval_handler(request: Request, exc: UnauthorizedApprovalError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Unauthorized Approval",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/unauthorized-approval",
        )

    @app.exception_handler(BudgetExceededError)
    async def budget_exceeded_handler(request: Request, exc: BudgetExceededError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            title="Budget Exceeded",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/budget-exceeded",
        )

    @app.exception_handler(DuplicateIdempotencyKeyError)
    async def idempotency_conflict_handler(request: Request, exc: DuplicateIdempotencyKeyError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Idempotency Key Conflict",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/duplicate-idempotency-key",
        )

    @app.exception_handler(OptimisticLockError)
    async def optimistic_lock_handler(request: Request, exc: OptimisticLockError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Concurrent Modification Conflict",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/optimistic-lock-conflict",
        )

    @app.exception_handler(ArtifactOwnershipError)
    async def artifact_ownership_handler(request: Request, exc: ArtifactOwnershipError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Artifact Ownership Violation",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/artifact-ownership",
        )

    @app.exception_handler(DomainError)
    async def general_domain_handler(request: Request, exc: DomainError) -> JSONResponse:
        return create_problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Domain Rule Violation",
            detail=str(exc),
            instance=request.url.path,
            problem_type="https://api.syntra.io/errors/domain-violation",
        )
