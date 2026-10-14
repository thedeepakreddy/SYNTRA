"""FastAPI authentication and authorization dependencies with strict multi-tenancy and RBAC."""

from collections.abc import AsyncGenerator, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status

from syntra.api.auth.jwt import parse_authenticated_user_from_claims, verify_and_decode_jwt
from syntra.api.auth.models import AuthenticatedUser, has_sufficient_role
from syntra.core.config import Settings, get_settings
from syntra.domain.entities import MembershipRole
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import get_db_manager


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user_id: Annotated[str | None, Header()] = None,
    x_dev_org_id: Annotated[str | None, Header()] = None,
    x_dev_role: Annotated[str | None, Header()] = None,
    x_dev_email: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> AuthenticatedUser:
    """Extract and authenticate the calling user.

    Supports:
    1. Local development headers, strictly forbidden outside 'development' environment.
    2. Cryptographically verified Bearer OIDC/JWT token.
    """
    if settings is None:
        settings = get_settings()

    # 1. Dev Auth Path
    if x_dev_user_id or x_dev_org_id or x_dev_role:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Development authentication headers are strictly prohibited outside development environment.",
            )
        try:
            user_id = UUID(x_dev_user_id) if x_dev_user_id else UUID("00000000-0000-0000-0000-000000000001")
            org_id = UUID(x_dev_org_id) if x_dev_org_id else UUID("00000000-0000-0000-0000-000000000002")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID in dev auth headers: {exc}",
            ) from exc

        role_str = (x_dev_role or "developer").lower()
        try:
            role = MembershipRole(role_str)
        except ValueError:
            role = MembershipRole.DEVELOPER

        return AuthenticatedUser(
            user_id=user_id,
            email=x_dev_email or f"{user_id}@syntra.local",
            org_id=org_id,
            role=role,
            is_service_account=False,
            claims={"auth_provider": "dev_headers"},
        )

    # 2. Production OIDC / Bearer JWT Path
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
        claims = verify_and_decode_jwt(token, settings)
        return parse_authenticated_user_from_claims(claims)

    # 3. Missing Credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials missing. Provide 'Authorization: Bearer <token>'.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(min_role: MembershipRole) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Dependency factory checking that the authenticated user possesses at least min_role privileges."""

    def role_checker(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if not has_sufficient_role(user.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: role '{user.role.value}' does not have sufficient permissions. "
                    f"Minimum required role is '{min_role.value}'."
                ),
            )
        return user

    return role_checker


# Shortcuts
require_viewer_or_above = require_role(MembershipRole.VIEWER)
require_developer_or_above = require_role(MembershipRole.DEVELOPER)
require_admin_or_above = require_role(MembershipRole.ADMIN)
require_owner = require_role(MembershipRole.OWNER)


async def get_uow() -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    """Provide scoped Unit of Work instance per request."""
    session_factory = get_db_manager().get_session_factory()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        yield uow
