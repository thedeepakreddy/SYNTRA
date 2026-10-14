"""Domain exceptions for SYNTRA business invariants and constraints."""


class DomainError(Exception):
    """Base exception for all domain logic violations."""

    pass


class InvalidStateTransitionError(DomainError):
    """Raised when an illegal lifecycle transition is attempted."""

    pass


class UnauthorizedTaskMutationError(DomainError):
    """Raised when an unauthorized actor (e.g. agent) attempts to mutate task state directly."""

    pass


class CyclicDependencyError(DomainError):
    """Raised when a task graph contains circular or self-dependencies."""

    pass


class InvalidTaskGraphError(DomainError):
    """Raised when a task DAG fails structural or relational validation."""

    pass


class CrossMissionDependencyError(InvalidTaskGraphError):
    """Raised when a task dependency spans across different missions."""

    pass


class CrossTenantAccessError(DomainError):
    """Raised when an operation attempts to access or mutate resources of another tenant."""

    pass


class TenantOwnershipError(DomainError):
    """Raised when entity relationships violate tenant ownership invariants."""

    pass


class ArtifactOwnershipError(TenantOwnershipError):
    """Raised when an artifact references a task or mission outside its ownership boundary."""

    pass


class OptimisticLockError(DomainError):
    """Raised when a concurrent modification is detected via version mismatch."""

    pass


class BudgetExceededError(DomainError):
    """Raised when token or spend constraints are exceeded."""

    pass


class DuplicateIdempotencyKeyError(DomainError):
    """Raised when an idempotency key is reused with a conflicting payload."""

    pass
