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


class ApprovalError(DomainError):
    """Base exception for approval governance failures."""

    pass


class ApprovalExpiredError(ApprovalError):
    """Raised when resolving an approval request that has passed its expiration time."""

    pass


class ApprovalReplayError(ApprovalError):
    """Raised when attempting to re-resolve an already finalized approval request."""

    pass


class ApprovalTamperedError(ApprovalError):
    """Raised when an approval request target or mission state has been modified after request creation."""

    pass


class DigestMismatchError(ApprovalError):
    """Raised when the cryptographic HMAC action digest fails validation."""

    pass


class UnauthorizedApprovalError(ApprovalError):
    """Raised when a user lacks required organizational permissions to resolve an approval."""

    pass


class SecretRedactionError(DomainError):
    """Raised when secret redaction fails or encounters unredactable sensitive data."""

    pass


class MemoryValidationError(DomainError):
    """Raised when memory record attributes violate domain constraints or scopes."""

    pass


class VerificationError(DomainError):
    """Base exception for independent verification and security assurance failures."""

    pass


class ProtectedTestViolationError(VerificationError):
    """Raised when an untrusted patch attempts to mutate, delete, or bypass protected test suites."""

    pass


class VerificationFailedError(VerificationError):
    """Raised when independent verification execution produces non-zero exit codes or defects."""

    pass


class VerificationTamperedError(VerificationError):
    """Raised when a verification record digest or signature fails cryptographic integrity verification."""

    pass


class HermeticExecutionError(VerificationError):
    """Raised when hermetic sandbox preparation, patching, or test runner fails to execute safely."""

    pass


class DeliveryBlockedError(VerificationError):
    """Raised when release/delivery gate is blocked due to missing, failed, or mismatched verification evidence."""

    pass


class AuditLoggingError(DomainError):
    """Raised when structured security audit event emission fails (fail-closed requirement)."""

    pass
