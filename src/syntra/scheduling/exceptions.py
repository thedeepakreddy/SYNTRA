"""Domain and infrastructure exceptions for task scheduling and agent coordination."""


class SchedulerError(Exception):
    """Base exception for all scheduler domain and runtime errors."""


class DAGValidationError(SchedulerError):
    """Raised when a task dependency graph violates acyclicity, containment, or integrity."""


class TaskNotReadyError(SchedulerError):
    """Raised when an operation attempts to schedule or claim a task whose prerequisites are unverified."""


class CapacityExceededError(SchedulerError):
    """Raised when scheduling exceeds mission concurrency limits or worker capacity reservations."""


class StaleLeaseError(SchedulerError):
    """Raised when a superseded worker attempts to submit results or extend a replaced lease."""


class LeaseExpiredError(SchedulerError):
    """Raised when an operation is attempted on an expired worker lease."""


class WorkerHeartbeatLostError(SchedulerError):
    """Raised when a worker fails to send heartbeats within the configured liveness interval."""


class DuplicateDispatchError(SchedulerError):
    """Raised when duplicate dispatch notifications are detected."""


class RedisStreamError(SchedulerError):
    """Raised when Redis Streams publish, read, or acknowledgment operations fail."""
