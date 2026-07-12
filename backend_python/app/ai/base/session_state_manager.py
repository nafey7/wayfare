"""Session state manager for MongoDB-backed state management.

This module provides SessionStateManager, which handles all session state
persistence to MongoDB. It replaces the triple-state pattern:

OLD (problematic):
1. Load from MongoDB
2. Merge with in-memory session_store (causes data resurrection)
3. Update in-memory only, persist later

NEW (this module):
1. Always read from MongoDB
2. Always write to MongoDB immediately
3. No in-memory caching of session state

Search results remain in-memory only (acceptable to lose on restart).
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.ai.base.session_state import SessionState, SessionType
from app.domains.booking_sessions.service import BookingSessionService

logger = logging.getLogger(__name__)


class SessionStateManager:
    """MongoDB-only session state management.

    Design principles:
    - Always read from MongoDB (no in-memory cache for state)
    - Write to MongoDB immediately after any change
    - search_results stay in-memory (large, transient data)

    Usage:
        manager = SessionStateManager()

        # Get or create session
        state = await manager.get_or_create_state(
            session_id="chat_123",
            user_id="user_456",
            session_type=SessionType.FLIGHT
        )

        # Update state (writes to MongoDB immediately)
        await manager.update_state(
            session_id="chat_123",
            collected={"origin": "LHR", "destination": "CDG"}
        )

        # Search results (in-memory only)
        manager.store_search_results("chat_123", {"flights": [...]})
        results = manager.get_search_results("chat_123")
    """

    # Default TTL for booking sessions (hours)
    DEFAULT_TTL_HOURS = 2

    def __init__(self) -> None:
        """Initialize the session state manager.

        Only search_results are cached in-memory (large, transient data).
        All session state is stored in MongoDB.
        """
        # ONLY search results stay in memory (acceptable to lose on restart)
        self._search_results: dict[str, Any] = {}

    async def get_state(self, session_id: str) -> SessionState | None:
        """Get session state from MongoDB.

        Args:
            session_id: The session/chat ID

        Returns:
            SessionState if found, None otherwise
        """
        session = await BookingSessionService.get_session(session_id)
        if not session:
            logger.debug(f"No session found for {session_id}")
            return None

        data = session.get("data", {})
        try:
            state = SessionState.from_mongo_dict(data)
            logger.debug(f"Loaded session {session_id} from MongoDB")
            return state
        except Exception as e:
            logger.warning(f"Failed to parse session {session_id}: {e}")
            return None

    async def create_state(
        self,
        session_id: str,
        user_id: str,
        session_type: SessionType,
        ttl_hours: int | None = None,
    ) -> SessionState:
        """Create new session state in MongoDB.

        Args:
            session_id: The session/chat ID
            user_id: The user ID
            session_type: Type of booking (flight/hotel)
            ttl_hours: Time-to-live in hours (default: 2)

        Returns:
            The created SessionState
        """
        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            session_type=session_type,
        )

        await BookingSessionService.store_session(
            session_id=session_id,
            user_id=user_id,
            session_data=state.to_mongo_dict(),
            ttl_hours=ttl_hours or self.DEFAULT_TTL_HOURS,
        )

        logger.info(f"Created new {session_type.value} session {session_id}")
        return state

    async def get_or_create_state(
        self,
        session_id: str,
        user_id: str,
        session_type: SessionType,
        ttl_hours: int | None = None,
    ) -> SessionState:
        """Get existing state or create new one.

        Args:
            session_id: The session/chat ID
            user_id: The user ID
            session_type: Type of booking (flight/hotel)
            ttl_hours: Time-to-live in hours for new sessions

        Returns:
            Existing or newly created SessionState
        """
        state = await self.get_state(session_id)
        if state:
            return state
        return await self.create_state(session_id, user_id, session_type, ttl_hours)

    async def update_state(self, session_id: str, **updates: Any) -> bool:
        """Update specific fields in session state.

        Writes to MongoDB immediately. No in-memory caching.

        Args:
            session_id: The session/chat ID
            **updates: Fields to update (e.g., collected={...}, waiting_for_field="date")

        Returns:
            True if update succeeded, False otherwise
        """
        # Always include updated timestamp
        updates["updated_at"] = datetime.now(UTC).isoformat()

        success = await BookingSessionService.update_session_data(session_id, updates)
        if success:
            logger.debug(f"Updated session {session_id}: {list(updates.keys())}")
        else:
            logger.warning(f"Failed to update session {session_id}")
        return success

    async def update_collected(self, session_id: str, **fields: Any) -> bool:
        """Update collected booking fields.

        Convenience method that merges new fields with existing collected data.

        Args:
            session_id: The session/chat ID
            **fields: Fields to update in collected dict

        Returns:
            True if update succeeded
        """
        # Get current state to merge collected fields
        state = await self.get_state(session_id)
        if not state:
            logger.warning(
                f"Cannot update collected for non-existent session {session_id}"
            )
            return False

        # Merge new fields (filter out None values)
        collected = state.collected.copy()
        for key, value in fields.items():
            if value is not None:
                collected[key] = value

        return await self.update_state(session_id, collected=collected)

    async def delete_state(self, session_id: str) -> bool:
        """Delete session state from MongoDB.

        Also clears any cached search results.

        Args:
            session_id: The session/chat ID

        Returns:
            True if deletion succeeded
        """
        # Clear search results cache
        self.clear_search_results(session_id)

        success = await BookingSessionService.delete_session(session_id)
        if success:
            logger.info(f"Deleted session {session_id}")
        return success

    # =========================================================================
    # Search Results (In-Memory Only)
    # =========================================================================

    def store_search_results(self, session_id: str, results: dict[str, Any]) -> None:
        """Store search results in memory.

        Search results are NOT persisted to MongoDB because:
        - They can be large (50+ flights/hotels)
        - They are transient (user re-searches if lost)
        - Acceptable to lose on server restart

        Args:
            session_id: The session/chat ID
            results: Search results dict (flights, hotels, etc.)
        """
        self._search_results[session_id] = results
        logger.debug(f"Stored search results for {session_id}")

    def get_search_results(self, session_id: str) -> dict[str, Any] | None:
        """Get search results from memory.

        Args:
            session_id: The session/chat ID

        Returns:
            Search results dict if found, None otherwise
        """
        return self._search_results.get(session_id)

    def clear_search_results(self, session_id: str) -> None:
        """Clear search results from memory.

        Args:
            session_id: The session/chat ID
        """
        if session_id in self._search_results:
            del self._search_results[session_id]
            logger.debug(f"Cleared search results for {session_id}")

    def has_search_results(self, session_id: str) -> bool:
        """Check if search results exist for session.

        Args:
            session_id: The session/chat ID

        Returns:
            True if search results exist
        """
        return session_id in self._search_results
