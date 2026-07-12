"""User repository for data access.

Simple, clean functions for essential database operations only.
"""

import asyncio
import logging
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING

from app.database.constants import (
    BOOKING_EVENT_COLLECTION,
    CHATS_COLLECTION,
    SESSIONS_COLLECTION,
    USERS_COLLECTION,
)
from app.database.dependencies import get_database
from app.database.models.user import UserModel
from app.domains.common import UTC, datetime, normalize_email

from .constants import (
    DEFAULT_USER_ROLE,
    MAX_USER_SEARCH_LIMIT,
)
from .enums import UserStatus

logger = logging.getLogger(__name__)


# ============================================================
# SINGLE USER OPERATIONS
# ============================================================

# -------------------------------
# Creation & Basic CRUD
# -------------------------------


async def create_user(user_data: dict[str, Any]) -> UserModel:
    """Create new user in database."""
    db = await get_database()

    # Set defaults
    now = datetime.now(UTC)
    defaults = {
        "status": UserStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
        "email_verified": False,
        "role": DEFAULT_USER_ROLE.value,
    }

    # Merge defaults with provided data
    final_data = {**defaults, **user_data}

    # Normalize email
    if "email" in final_data:
        final_data["email"] = normalize_email(final_data["email"])

    result = await db[USERS_COLLECTION].insert_one(final_data)
    final_data["_id"] = result.inserted_id

    return UserModel(**final_data)


async def get_user_by_id(user_id: str) -> UserModel | None:
    """Get user by ID."""
    try:
        db = await get_database()
        user_dict = await db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
        return UserModel(**user_dict) if user_dict else None
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None


async def get_users_by_ids(user_ids: list[str]) -> list[UserModel]:
    """Get multiple users by IDs. Invalid IDs are skipped. Returns empty list if none valid."""
    if not user_ids:
        return []
    oids: list[ObjectId] = []
    for uid in user_ids:
        try:
            oids.append(ObjectId(uid))
        except Exception as e:
            logger.debug("Skipping invalid user id %s: %s", uid, e)
            continue
    if not oids:
        return []
    try:
        db = await get_database()
        cursor = db[USERS_COLLECTION].find({"_id": {"$in": oids}})
        return [UserModel(**u) async for u in cursor]
    except Exception as e:
        logger.error(f"Error getting users by IDs: {e}")
        return []


async def get_user_by_email(email: str) -> UserModel | None:
    """Get user by email address."""
    try:
        db = await get_database()
        user_dict = await db[USERS_COLLECTION].find_one(
            {"email": normalize_email(email)}
        )
        return UserModel(**user_dict) if user_dict else None
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        return None


async def update_user(user_id: str, update_data: dict[str, Any]) -> UserModel | None:
    """Update user in database."""
    try:
        db = await get_database()

        # Always update timestamp
        update_data["updated_at"] = datetime.now(UTC)

        # Remove protected fields
        for field in ["_id", "id", "created_at"]:
            update_data.pop(field, None)

        result = await db[USERS_COLLECTION].find_one_and_update(
            {"_id": ObjectId(user_id)}, {"$set": update_data}, return_document=True
        )

        return UserModel(**result) if result else None
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return None


async def use_discount_atomic(user_id: str) -> UserModel | None:
    """Atomically mark discount as used (prevents race condition).

    Only updates if discount_eligible is True. Returns the updated user
    or None if user not found or discount already used.
    """
    try:
        db = await get_database()
        result = await db[USERS_COLLECTION].find_one_and_update(
            {"_id": ObjectId(user_id), "discount_eligible": True},
            {"$set": {"discount_eligible": False, "updated_at": datetime.now(UTC)}},
            return_document=True,
        )
        return UserModel(**result) if result else None
    except Exception as e:
        logger.error(f"Error in use_discount_atomic for user {user_id}: {e}")
        return None


async def set_photo_key(user_id: str, key: str | None) -> bool:
    """Set or clear the profile photo S3 key for a user.

    Returns True when the document was modified. Pass ``key=None`` to clear.
    """
    try:
        from .enums import UserStatus

        db = await get_database()
        result = await db[USERS_COLLECTION].update_one(
            {
                "_id": ObjectId(user_id),
                "status": {"$ne": UserStatus.DELETED.value},
            },
            {
                "$set": {
                    "photo_key": key,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return result.matched_count > 0
    except Exception as e:
        logger.error(f"Error setting photo_key for user {user_id}: {e}")
        return False


async def get_photo_key(user_id: str) -> str | None:
    """Return the user's current photo_key (or None)."""
    try:
        db = await get_database()
        doc = await db[USERS_COLLECTION].find_one(
            {"_id": ObjectId(user_id)}, {"photo_key": 1}
        )
        return doc.get("photo_key") if doc else None
    except Exception as e:
        logger.error(f"Error getting photo_key for user {user_id}: {e}")
        return None


async def delete_user(user_id: str) -> bool:
    """Soft delete user."""
    try:
        db = await get_database()

        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "status": UserStatus.DELETED,
                    "deleted_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )

        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False


# -------------------------------
# User-Specific Queries
# -------------------------------


async def email_exists(email: str) -> bool:
    """Check if email already exists in database."""
    try:
        db = await get_database()
        # Only check for _id field existence (minimal data transfer)
        result = await db[USERS_COLLECTION].find_one(
            {"email": email.lower()}, {"_id": 1}
        )
        return result is not None
    except Exception as e:
        logger.error(f"Error checking email existence: {e}")
        return False


# -------------------------------
# User-Specific Operations
# -------------------------------


async def verify_email(user_id: str) -> bool:
    """Mark user email as verified with timestamp."""
    try:
        db = await get_database()

        result = await db[USERS_COLLECTION].update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "email_verified": True,
                    "email_verified_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )

        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error verifying email for user {user_id}: {e}")
        return False


async def get_user_statistics(user_id: str) -> dict[str, Any]:
    """Get aggregated user statistics from multiple collections."""
    try:
        db = await get_database()
        oid = ObjectId(user_id)

        # Run all queries in parallel for performance
        # Only use collections that actually exist
        results = await asyncio.gather(
            db[BOOKING_EVENT_COLLECTION].count_documents({"user_id": oid}),
            db[CHATS_COLLECTION].count_documents({"user_id": oid}),
            db[SESSIONS_COLLECTION].count_documents({"user_id": oid}),
            db[USERS_COLLECTION].find_one(
                {"_id": oid},
                {
                    "created_at": 1,
                    "last_activity": 1,
                    "total_spent": 1,
                    "login_streak": 1,
                    "api_calls_today": 1,
                },
            ),
            return_exceptions=True,
        )

        # Handle results safely
        bookings = results[0] if not isinstance(results[0], Exception) else 0
        messages = results[1] if not isinstance(results[1], Exception) else 0
        sessions = results[2] if not isinstance(results[2], Exception) else 0
        user_data_raw = results[3] if not isinstance(results[3], Exception) else {}
        user_data: dict = user_data_raw if isinstance(user_data_raw, dict) else {}

        if not user_data:
            return {}

        # Calculate account age
        created_at = user_data.get("created_at", datetime.now(UTC))
        # Ensure both datetimes are timezone-aware for safe arithmetic
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        account_age_days = (datetime.now(UTC) - created_at).days

        return {
            "bookings": bookings,
            "messages_sent": messages,
            "searches": sessions,
            "trips_created": 0,  # TODO: Implement trips counting
            "account_age_days": account_age_days,
            "last_activity": user_data.get("last_activity"),
            "total_spent": user_data.get("total_spent", 0.0),
            "login_streak": user_data.get("login_streak", 0),
            "api_calls_today": user_data.get("api_calls_today", 0),
        }
    except Exception as e:
        logger.error(f"Error getting statistics for user {user_id}: {e}")
        return {}


# ============================================================
# MULTIPLE USERS OPERATIONS
# ============================================================

# -------------------------------
# Query Helpers
# -------------------------------


def _build_user_query(
    search_term: str | None = None,
    status: UserStatus | None = None,
    role: str | None = None,
    verified_only: bool = False,
) -> dict[str, Any]:
    """Build MongoDB query for user searches.

    Shared query logic for search_users and count_users.
    """
    query: dict[str, Any] = {}

    # Always exclude deleted unless specifically requested
    if status != UserStatus.DELETED:
        query["status"] = {"$ne": UserStatus.DELETED}

    # Add search term (search in name and email)
    if search_term:
        regex = {"$regex": search_term, "$options": "i"}
        query["$or"] = [{"first_name": regex}, {"last_name": regex}, {"email": regex}]

    # Add specific filters
    if status:
        query["status"] = status

    if role:
        query["role"] = role

    if verified_only:
        query["email_verified"] = True

    return query


# -------------------------------
# Search & Filter
# -------------------------------


async def search_users(
    search_term: str | None = None,
    status: UserStatus | None = None,
    role: str | None = None,
    verified_only: bool = False,
    skip: int = 0,
    limit: int = MAX_USER_SEARCH_LIMIT,
) -> list[UserModel]:
    """Search users with optional filters."""
    try:
        db = await get_database()

        # Use shared query builder
        query = _build_user_query(search_term, status, role, verified_only)

        # Execute query with sorting and pagination
        cursor = db[USERS_COLLECTION].find(query)
        cursor = cursor.sort("created_at", DESCENDING)
        cursor = cursor.skip(skip).limit(limit)

        users = await cursor.to_list(length=limit)
        return [UserModel(**user) for user in users]
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return []


# -------------------------------
# Aggregation & Statistics
# -------------------------------


async def count_users(
    status: UserStatus | None = None,
    role: str | None = None,
    verified_only: bool = False,
) -> int:
    """Count users matching filters."""
    try:
        db = await get_database()

        # Use shared query builder (search_term=None for count operation)
        query = _build_user_query(None, status, role, verified_only)

        return await db[USERS_COLLECTION].count_documents(query)
    except Exception as e:
        logger.error(f"Error counting users: {e}")
        return 0
