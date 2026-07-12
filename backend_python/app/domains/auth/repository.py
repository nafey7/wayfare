"""Auth repository for data access.

Simple, clean functions for essential database operations only.
Handles sessions and auth-specific user operations.
"""

import logging
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING

from app.database.constants import SESSIONS_COLLECTION, USERS_COLLECTION
from app.database.dependencies import get_database
from app.database.models.session import SessionModel
from app.domains.common import datetime, now_utc

logger = logging.getLogger(__name__)


# ============================================================
# SESSION OPERATIONS - CRUD
# ============================================================


async def create_session(session_data: dict[str, Any]) -> SessionModel:
    """Create new session in database."""
    db = await get_database()

    # Set defaults
    now = now_utc()
    defaults = {
        "created_at": now,
        "last_activity": now,
    }

    # Merge defaults with provided data
    final_data = {**defaults, **session_data}

    result = await db[SESSIONS_COLLECTION].insert_one(final_data)
    final_data["_id"] = result.inserted_id

    return SessionModel(**final_data)


async def get_session_by_id(session_id: str) -> SessionModel | None:
    """Get session by ID."""
    try:
        db = await get_database()
        session_dict = await db[SESSIONS_COLLECTION].find_one(
            {"_id": ObjectId(session_id)}
        )
        return SessionModel(**session_dict) if session_dict else None
    except Exception as e:
        logger.error(f"Error getting session by ID {session_id}: {e}")
        return None


async def get_session_by_refresh_token(refresh_token: str) -> SessionModel | None:
    """Get session by refresh token."""
    try:
        db = await get_database()
        session_dict = await db[SESSIONS_COLLECTION].find_one(
            {"refresh_token": refresh_token, "expires_at": {"$gt": now_utc()}}
        )
        return SessionModel(**session_dict) if session_dict else None
    except Exception as e:
        logger.error(f"Error getting session by refresh token: {e}")
        return None


async def update_session(
    session_id: str, update_data: dict[str, Any]
) -> SessionModel | None:
    """Update session in database."""
    try:
        db = await get_database()

        # Always update last activity
        update_data["last_activity"] = now_utc()

        # Remove protected fields
        for field in ["_id", "id", "created_at", "user_id"]:
            update_data.pop(field, None)

        result = await db[SESSIONS_COLLECTION].find_one_and_update(
            {"_id": ObjectId(session_id)}, {"$set": update_data}, return_document=True
        )

        return SessionModel(**result) if result else None
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        return None


async def delete_session(session_id: str) -> bool:
    """Delete session from database."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].delete_one({"_id": ObjectId(session_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return False


# ============================================================
# SESSION OPERATIONS - SPECIFIC
# ============================================================


async def update_session_activity(session_id: str) -> bool:
    """Update session last activity timestamp."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"last_activity": now_utc()}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating session activity {session_id}: {e}")
        return False


async def update_refresh_token(session_id: str, new_token: str) -> bool:
    """Update session refresh token."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"refresh_token": new_token, "last_activity": now_utc()}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating refresh token for session {session_id}: {e}")
        return False


# ============================================================
# SESSION OPERATIONS - USER SPECIFIC
# ============================================================


async def get_user_sessions(
    user_id: str, include_expired: bool = False
) -> list[SessionModel]:
    """Get all sessions for a user."""
    try:
        db = await get_database()

        query: dict[str, Any] = {"user_id": user_id}
        if not include_expired:
            query["expires_at"] = {"$gt": now_utc()}

        cursor = db[SESSIONS_COLLECTION].find(query)
        cursor = cursor.sort("last_activity", DESCENDING)

        sessions = await cursor.to_list(length=None)
        return [SessionModel(**session) for session in sessions]
    except Exception as e:
        logger.error(f"Error getting sessions for user {user_id}: {e}")
        return []


async def delete_user_session(session_id: str, user_id: str) -> bool:
    """Delete a specific session for a user (with ownership check)."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].delete_one(
            {"_id": ObjectId(session_id), "user_id": user_id}
        )
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting user session {session_id}: {e}")
        return False


async def delete_all_user_sessions(user_id: str) -> int:
    """Delete all sessions for a user."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].delete_many({"user_id": user_id})
        return result.deleted_count
    except Exception as e:
        logger.error(f"Error deleting all sessions for user {user_id}: {e}")
        return 0


# ============================================================
# SESSION OPERATIONS - MAINTENANCE
# ============================================================


async def delete_expired_sessions() -> int:
    """Delete all expired sessions (maintenance task)."""
    try:
        db = await get_database()
        result = await db[SESSIONS_COLLECTION].delete_many(
            {"expires_at": {"$lt": now_utc()}}
        )
        return result.deleted_count
    except Exception as e:
        logger.error(f"Error deleting expired sessions: {e}")
        return 0


# ============================================================
# USER AUTH OPERATIONS - REGISTRATION
# ============================================================


async def complete_user_registration(user_id: str, password_hash: str) -> bool:
    """Complete user registration by setting password and verifying email."""
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_hash": password_hash,
                    "email_verified": True,
                    "updated_at": now_utc(),
                },
                "$unset": {"password_reset_token": "", "password_reset_expires": ""},
            },
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error completing registration for user {user_id}: {e}")
        return False


# ============================================================
# USER AUTH OPERATIONS - LOGIN
# ============================================================


async def update_user_last_login(user_id: str) -> bool:
    """Update user last login timestamp."""
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"last_login": now_utc()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating last login for user {user_id}: {e}")
        return False


async def link_google_account(
    user_id: str, google_id: str, update_fields: dict[str, Any] | None = None
) -> bool:
    """Link Google account to existing user."""
    try:
        db = await get_database()

        update_data = {"google_id": google_id, "updated_at": now_utc()}

        # Add any additional fields to update
        if update_fields:
            update_data.update(update_fields)

        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error linking Google account for user {user_id}: {e}")
        return False


# ============================================================
# USER AUTH OPERATIONS - PASSWORD
# ============================================================


async def update_user_password(user_id: str, password_hash: str) -> bool:
    """Update user password hash."""
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": password_hash, "updated_at": now_utc()}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating password for user {user_id}: {e}")
        return False


async def set_password_reset_token(user_id: str, token: str, expiry: datetime) -> bool:
    """Set password reset token for user."""
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_reset_token": token, "password_reset_expires": expiry}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error setting password reset token for user {user_id}: {e}")
        return False


async def get_user_by_reset_token(token: str) -> dict[str, Any] | None:
    """Find user by password reset token."""
    try:
        db = await get_database()
        return await db[USERS_COLLECTION].find_one(
            {
                "password_reset_token": token,
                "password_reset_expires": {"$gt": now_utc()},
            }
        )
    except Exception as e:
        logger.error(f"Error finding user by reset token: {e}")
        return None


async def clear_password_reset_token(user_id: str) -> bool:
    """Clear password reset token after use."""
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"password_reset_token": "", "password_reset_expires": ""}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error clearing password reset token for user {user_id}: {e}")
        return False
