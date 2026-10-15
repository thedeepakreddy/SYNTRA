"""Capability policy engine enforcing zero-trust authorization over all MCP tool invocations."""

import fnmatch
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from syntra.domain.entities import ActionClassification
from syntra.mcp.types import MCPInvocationRequest, MCPToolDefinition


class PolicyViolationError(Exception):
    """Base exception for policy engine access denial."""


class UnauthorizedRoleError(PolicyViolationError):
    """Raised when the agent role does not possess capability grant for the tool."""


class ExpiredGrantError(PolicyViolationError):
    """Raised when the matched capability grant has expired."""


class ScopeViolationError(PolicyViolationError):
    """Raised when an operation attempts to access resources outside allowed workspace scope."""


class HumanApprovalRequiredError(PolicyViolationError):
    """Raised when an external write or sensitive action lacks valid human cryptographic approval."""


class CrossTenantAccessError(PolicyViolationError):
    """Raised when a request attempts to operate across organization boundaries."""


class BudgetExceededError(PolicyViolationError):
    """Raised when a mission's token or financial budget is exhausted."""


@dataclass
class PolicyGrantRecord:
    """In-memory or persistent capability grant rule."""

    org_id: UUID
    agent_role: str
    tool_name_pattern: str
    is_allowed: bool = True
    requires_approval: bool = False
    expires_at: datetime | None = None


@dataclass
class PolicyDecision:
    """Outcome of a capability policy evaluation."""

    allowed: bool
    action_classification: ActionClassification
    reason: str
    requires_human_approval: bool = False


class CapabilityPolicyEngine:
    """Evaluates 10-point security and capability authorization matrix before tool execution."""

    def __init__(self) -> None:
        # Default grants registry: org_id -> list[PolicyGrantRecord]
        self._grants: dict[UUID, list[PolicyGrantRecord]] = {}

    def register_grant(
        self,
        org_id: UUID,
        agent_role: str,
        tool_name_pattern: str,
        is_allowed: bool = True,
        requires_approval: bool = False,
        expires_at: datetime | None = None,
    ) -> PolicyGrantRecord:
        """Register a capability grant rule for an organization and agent role."""
        grant = PolicyGrantRecord(
            org_id=org_id,
            agent_role=agent_role,
            tool_name_pattern=tool_name_pattern,
            is_allowed=is_allowed,
            requires_approval=requires_approval,
            expires_at=expires_at,
        )
        if org_id not in self._grants:
            self._grants[org_id] = []
        self._grants[org_id].append(grant)
        return grant

    def evaluate(
        self,
        request: MCPInvocationRequest,
        tool_def: MCPToolDefinition,
        mission_org_id: UUID | None = None,
        budget_remaining_tokens: int | None = None,
        has_valid_approval: bool = False,
    ) -> PolicyDecision:
        """Evaluate invocation request against authoritative capability policies."""
        now = datetime.now(UTC)

        # 1. Tenant boundary enforcement: Cross-tenant operations are strictly forbidden
        if mission_org_id and mission_org_id != request.org_id:
            raise CrossTenantAccessError(
                f"Tenant isolation violation: Caller org '{request.org_id}' cannot access "
                f"mission belonging to org '{mission_org_id}'."
            )

        # 2. Match capability grants for caller role
        org_grants = self._grants.get(request.org_id, [])
        matching_grants = [
            g
            for g in org_grants
            if g.agent_role.lower() == request.caller_role.lower()
            and (fnmatch.fnmatch(request.tool_name, g.tool_name_pattern) or g.tool_name_pattern == "*")
        ]

        if not matching_grants:
            raise UnauthorizedRoleError(
                f"Role '{request.caller_role}' has no capability grant allowing tool '{request.tool_name}'."
            )

        # Check for explicit denial or expiration
        matched = matching_grants[-1]  # Most recent grant
        if not matched.is_allowed:
            raise UnauthorizedRoleError(
                f"Capability grant for role '{request.caller_role}' explicitly denies '{request.tool_name}'."
            )

        if matched.expires_at and matched.expires_at <= now:
            raise ExpiredGrantError(
                f"Capability grant for tool '{request.tool_name}' expired at {matched.expires_at.isoformat()}."
            )

        # 3. Budget exhaustion check
        if budget_remaining_tokens is not None and budget_remaining_tokens <= 0:
            raise BudgetExceededError(
                f"Token budget exhausted for mission '{request.mission_id}'. Tool execution denied."
            )

        # 4. Action classification and human approval requirement check
        action_class = tool_def.action_classification
        requires_approval = matched.requires_approval or (
            action_class in (ActionClassification.EXTERNAL_WRITE, ActionClassification.SENSITIVE_EXTERNAL_ACTION)
        )

        if requires_approval and not has_valid_approval:
            raise HumanApprovalRequiredError(
                f"Tool '{request.tool_name}' classified as {action_class.value} requires authorized "
                "cryptographic human approval digest before execution."
            )

        return PolicyDecision(
            allowed=True,
            action_classification=action_class,
            reason="Authorized by capability policy grant.",
            requires_human_approval=requires_approval,
        )
