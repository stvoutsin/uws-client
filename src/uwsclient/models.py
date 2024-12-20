from enum import Enum

__all__ = ["UWSPhase"]


class UWSPhase(Enum):
    """Universal Worker Service (UWS) job execution phases."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"
    HELD = "HELD"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"
