"""Base classes for AI session management.

This module provides the foundation for MongoDB-backed session state management,
eliminating the triple-state problem (in-memory handler + in-memory collector + MongoDB).
"""

from app.ai.base.session_state import SessionState, SessionType
from app.ai.base.session_state_manager import SessionStateManager

__all__ = [
    "SessionState",
    "SessionStateManager",
    "SessionType",
]
