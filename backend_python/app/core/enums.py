"""Core enums used across the application.

These enums are infrastructure-level and not specific to any domain.
"""

from enum import StrEnum


class LogLevel(StrEnum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
