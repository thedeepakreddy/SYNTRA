"""Authentication and authorization data models."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from syntra.domain.entities import MembershipRole

ROLE_HIERARCHY: dict[MembershipRole, int] = {
    MembershipRole.VIEWER: 1,
    MembershipRole.DEVELOPER: 2,
    MembershipRole.ENGINEER: 2,
    MembershipRole.ADMIN: 3,
    MembershipRole.OWNER: 4,
}


def has_sufficient_role(current_role: MembershipRole, required_role: MembershipRole) -> bool:
    """Evaluate whether current_role meets or exceeds required_role in the SYNTRA hierarchy."""
    current_level = ROLE_HIERARCHY.get(current_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return current_level >= required_level


class AuthenticatedUser(BaseModel):
    """Cryptographically verified or strictly gated development identity."""

    user_id: UUID
    email: str
    org_id: UUID
    role: MembershipRole = MembershipRole.DEVELOPER
    is_service_account: bool = False
    claims: dict[str, Any] = Field(default_factory=dict)
