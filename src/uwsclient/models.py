"""Module containing UWS models for the UWS client."""

from dataclasses import dataclass
from enum import Enum


class UWSPhase(str, Enum):
    """Enumeration of possible UWS job phases.

    Attributes
    ----------
    PENDING : str
        Job is accepted but not yet scheduled
    QUEUED : str
        Job is queued for execution
    EXECUTING : str
        Job is currently running
    COMPLETED : str
        Job has completed successfully
    ERROR : str
        Job terminated with an error
    ABORTED : str
        Job was aborted by user or system
    UNKNOWN : str
        Job state cannot be determined
    HELD : str
        Job is on hold
    """

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"
    HELD = "HELD"


@dataclass
class JobResult:
    """Information about a job result file.

    Attributes
    ----------
    id : str
        Identifier for the result
    href : str
        URL where the result can be downloaded
    mime_type : str
        MIME type of the result file
    """

    id: str
    href: str
    mime_type: str
