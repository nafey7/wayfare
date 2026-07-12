"""Booking session service for persistent session storage."""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from app.database.connection import get_connection

logger = logging.getLogger(__name__)


class BookingSessionService:
    """Service for managing booking sessions in MongoDB."""

    @staticmethod
    def _serialize_for_mongo(data: Any) -> Any:
        """Serialize complex objects for MongoDB storage."""
        # Handle primitive types first (most common case)
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        if isinstance(data, Decimal):
            # Decimal - convert to float (before dict check)
            return float(data)
        if isinstance(data, Enum):
            # Enum - store the value (before dict check)
            return data.value
        if isinstance(data, (date, datetime)):
            # Date/datetime - convert to ISO string
            return data.isoformat()
        if hasattr(data, "model_dump"):
            # Pydantic model - serialize to dict first, then recursively serialize
            return BookingSessionService._serialize_for_mongo(data.model_dump())
        if isinstance(data, dict):
            # Dictionary - recursively serialize values
            return {
                k: BookingSessionService._serialize_for_mongo(v)
                for k, v in data.items()
            }
        if isinstance(data, (list, tuple)):
            # List/tuple - recursively serialize items
            return [BookingSessionService._serialize_for_mongo(item) for item in data]
        if hasattr(data, "__dict__"):
            # Object with __dict__ - convert to dict and recursively serialize
            return BookingSessionService._serialize_for_mongo(
                dict(data.__dict__.items())
            )
        # Try to convert to string as fallback
        try:
            result = str(data)
            logger.warning(
                f"Serialized unknown type {type(data)} to string: {result[:100]}"
            )
            return result
        except Exception as e:
            logger.warning(
                f"Could not serialize object of type {type(data)}: {data} - Error: {e}"
            )
            return None

    @staticmethod
    def _get_collection():
        """Get the booking sessions collection."""
        db = get_connection().get_database()
        return db.booking_sessions

    @staticmethod
    async def store_session(
        session_id: str, user_id: str, session_data: dict[str, Any], ttl_hours: int = 3
    ) -> bool:
        """
        Store booking session data with TTL.

        Args:
            session_id: Unique session identifier
            user_id: User ID who owns the session
            session_data: Session data to store
            ttl_hours: Time to live in hours (default 3 hours)

        Returns:
            True if stored successfully
        """
        try:
            collection = BookingSessionService._get_collection()

            # Calculate expiry time (timezone-aware)
            expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

            # Serialize session data for MongoDB
            serialized_data = BookingSessionService._serialize_for_mongo(session_data)

            # Upsert session data
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "data": serialized_data,
                        "updated_at": datetime.now(UTC),
                        "expires_at": expires_at,
                    },
                    "$setOnInsert": {"created_at": datetime.now(UTC)},
                },
                upsert=True,
            )

            logger.info(f"Stored booking session {session_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store booking session {session_id}: {e}")
            return False

    @staticmethod
    async def get_session(session_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve booking session data.

        Args:
            session_id: Session identifier to retrieve

        Returns:
            Session data dict or None if not found/expired
        """
        try:
            collection = BookingSessionService._get_collection()

            # Find non-expired session
            session = await collection.find_one(
                {"session_id": session_id, "expires_at": {"$gt": datetime.now(UTC)}}
            )

            if session:
                logger.info(
                    f"Retrieved booking session {session_id} for user {session.get('user_id')}"
                )
                return {
                    "session_id": session["session_id"],
                    "user_id": session["user_id"],
                    "data": session["data"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                }
            logger.debug(f"Booking session {session_id} not found or expired")
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve booking session {session_id}: {e}")
            return None

    @staticmethod
    async def update_session_data(session_id: str, updates: dict[str, Any]) -> bool:
        """
        Update specific fields in session data.

        Args:
            session_id: Session to update
            updates: Dictionary of fields to update in session.data

        Returns:
            True if updated successfully
        """
        try:
            collection = BookingSessionService._get_collection()

            # Build update query for nested data fields
            update_query = {"updated_at": datetime.now(UTC)}

            for key, value in updates.items():
                serialized_value = BookingSessionService._serialize_for_mongo(value)
                update_query[f"data.{key}"] = serialized_value

            result = await collection.update_one(
                {"session_id": session_id, "expires_at": {"$gt": datetime.now(UTC)}},
                {"$set": update_query},
            )

            if result.modified_count > 0:
                logger.info(
                    f"Updated booking session {session_id} with {len(updates)} fields"
                )
                return True
            logger.warning(f"No session found to update for {session_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to update booking session {session_id}: {e}")
            return False

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """
        Delete booking session.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted successfully
        """
        try:
            collection = BookingSessionService._get_collection()

            result = await collection.delete_one({"session_id": session_id})

            if result.deleted_count > 0:
                logger.info(f"Deleted booking session {session_id}")
                return True
            logger.debug(f"No session found to delete for {session_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete booking session {session_id}: {e}")
            return False

    @staticmethod
    async def get_user_sessions(user_id: str) -> list[dict[str, Any]]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User to get sessions for

        Returns:
            List of session data
        """
        try:
            collection = BookingSessionService._get_collection()

            sessions = []
            async for session in collection.find(
                {"user_id": user_id, "expires_at": {"$gt": datetime.now(UTC)}}
            ).sort("updated_at", -1):
                sessions.append(
                    {
                        "session_id": session["session_id"],
                        "user_id": session["user_id"],
                        "data": session["data"],
                        "created_at": session["created_at"],
                        "updated_at": session["updated_at"],
                    }
                )

            logger.info(f"Retrieved {len(sessions)} active sessions for user {user_id}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to retrieve sessions for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_session_by_external_ref(
        external_booking_reference: str,
    ) -> Optional[dict[str, Any]]:
        """
        Find a booking session by external_booking_reference stored in session data.

        Args:
            external_booking_reference: External booking reference to search for

        Returns:
            Session data dict or None if not found
        """
        try:
            collection = BookingSessionService._get_collection()

            # Search for session with external_booking_reference in data
            session = await collection.find_one(
                {
                    "data.external_booking_reference": external_booking_reference,
                    "expires_at": {"$gt": datetime.now(UTC)},
                }
            )

            if session:
                logger.info(
                    f"Found session {session.get('session_id')} for external ref {external_booking_reference}"
                )
                return {
                    "session_id": session["session_id"],
                    "user_id": session["user_id"],
                    "data": session["data"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                }
            logger.debug(
                f"No session found for external_booking_reference: {external_booking_reference}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Failed to find session by external_booking_reference {external_booking_reference}: {e}"
            )
            return None

    @staticmethod
    async def cleanup_expired_sessions() -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            collection = BookingSessionService._get_collection()

            result = await collection.delete_many(
                {"expires_at": {"$lte": datetime.now(UTC)}}
            )

            if result.deleted_count > 0:
                logger.info(
                    f"Cleaned up {result.deleted_count} expired booking sessions"
                )

            return result.deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

    @staticmethod
    async def get_session_stats() -> dict[str, Any]:
        """
        Get statistics about booking sessions.

        Returns:
            Dict with session statistics
        """
        try:
            collection = BookingSessionService._get_collection()

            total_sessions = await collection.count_documents({})
            active_sessions = await collection.count_documents(
                {"expires_at": {"$gt": datetime.now(UTC)}}
            )

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": total_sessions - active_sessions,
            }

        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"total_sessions": 0, "active_sessions": 0, "expired_sessions": 0}
