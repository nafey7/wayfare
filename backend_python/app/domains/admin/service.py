"""Admin service for administrative operations.

This module provides admin functionality including user management,
system statistics, and administrative operations.
"""

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.database.dependencies import get_database
from app.database.models.user import UserModel
from app.domains.user.enums import UserRole, UserStatus

logger = logging.getLogger(__name__)


async def check_is_admin(user_id: str | None) -> bool:
    """Check if a user has admin role.

    Args:
        user_id: The user ID to check

    Returns:
        True if user is admin, False otherwise
    """
    if not user_id:
        return False

    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return False

    try:
        db = await get_database()
        user_data = await db.users.find_one({"_id": user_oid}, {"role": 1})

        if not user_data:
            return False

        return user_data.get("role") == UserRole.ADMIN.value

    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}")
        return False


async def get_all_users(
    limit: int = 100, offset: int = 0, include_deleted: bool = False
) -> list[UserModel]:
    """Get all users with pagination.

    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        include_deleted: Whether to include deleted users

    Returns:
        List of UserModel instances
    """
    try:
        db = await get_database()

        # Build query - exclude deleted users by default
        query: dict[str, Any] = {}
        if not include_deleted:
            query["status"] = {"$ne": UserStatus.DELETED.value}

        cursor = db.users.find(query).skip(offset).limit(limit).sort("createdAt", -1)

        users = []
        async for user_data in cursor:
            try:
                user = UserModel(**user_data)
                users.append(user)
            except Exception as e:
                logger.warning(f"Failed to parse user data: {e}")
                continue

        return users

    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


async def update_user_status(user_id: str | None, status: int) -> bool:
    """Update user status.

    Args:
        user_id: The user ID to update
        status: New status value

    Returns:
        True if updated successfully, False otherwise
    """
    if not user_id:
        return False

    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return False

    try:
        db = await get_database()
        result = await db.users.update_one(
            {"_id": user_oid},
            {"$set": {"status": status, "updatedAt": datetime.utcnow()}},
        )

        return result.modified_count > 0

    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return False


async def update_user_role(user_id: str | None, role: str) -> bool:
    """Update user role.

    Args:
        user_id: The user ID to update
        role: New role ('admin' or 'user')

    Returns:
        True if updated successfully, False otherwise
    """
    if not user_id:
        return False

    # Validate role
    if role == "admin":
        role_value = UserRole.ADMIN.value
    elif role == "user":
        role_value = UserRole.USER.value
    else:
        logger.warning(f"Invalid role: {role}")
        return False

    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return False

    try:
        db = await get_database()
        result = await db.users.update_one(
            {"_id": user_oid},
            {"$set": {"role": role_value, "updatedAt": datetime.utcnow()}},
        )

        return result.modified_count > 0

    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return False


async def _get_user_growth_stats(db: Any) -> dict[str, int]:
    """Get user growth statistics by month."""
    try:
        pipeline = [
            {"$match": {"status": {"$ne": UserStatus.DELETED.value}}},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$createdAt"},
                        "month": {"$month": "$createdAt"},
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.year": -1, "_id.month": -1}},
            {"$limit": 12},
        ]

        cursor = db.users.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        # Format as YYYY-MM: count
        growth_stats = {}
        for result in results:
            year = result["_id"]["year"]
            month = result["_id"]["month"]
            key = f"{year:04d}-{month:02d}"
            growth_stats[key] = result["count"]

        return growth_stats

    except Exception as e:
        logger.error(f"Error getting user growth stats: {e}")
        return {}


async def _get_usage_by_hour(db: Any) -> dict[str, int]:
    """Get usage statistics by hour of day."""
    try:
        pipeline = [
            {"$match": {"status": UserStatus.ACTIVE.value}},
            {"$group": {"_id": {"$hour": "$createdAt"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]

        cursor = db.chats_python.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        # Format as HH:00: count
        usage_stats = {}
        for result in results:
            hour = result["_id"]
            key = f"{hour:02d}:00"
            usage_stats[key] = result["count"]

        return usage_stats

    except Exception as e:
        logger.error(f"Error getting usage by hour stats: {e}")
        return {}


async def get_system_stats() -> dict[str, Any]:
    """Get comprehensive system statistics."""
    try:
        db = await get_database()

        # Get basic counts
        active_users = await db.users.count_documents(
            {"status": {"$ne": UserStatus.DELETED.value}}
        )
        deleted_users = await db.users.count_documents(
            {"status": UserStatus.DELETED.value}
        )
        total_messages = await db.chats_python.count_documents({})
        active_sessions = await db.sessions.count_documents({})

        # Get detailed analytics
        user_growth = await _get_user_growth_stats(db)
        usage_by_hour = await _get_usage_by_hour(db)

        return {
            "active_users": active_users,
            "deleted_users": deleted_users,
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "user_growth": user_growth,
            "usage_by_hour": usage_by_hour,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        # Return basic fallback stats
        return {
            "active_users": 0,
            "deleted_users": 0,
            "total_messages": 0,
            "active_sessions": 0,
            "user_growth": {},
            "usage_by_hour": {},
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }


class AdminService:
    """Service for admin operations.

    This service provides administrative functionality including user management,
    system statistics, and other admin-only operations.
    """

    def __init__(self) -> None:
        """Initialize admin service."""
        pass

    async def get_system_stats(self) -> dict[str, Any]:
        """Get system-wide statistics."""
        return await get_system_stats()


# Create singleton instance
_admin_service_instance = AdminService()


def get_admin_service() -> AdminService:
    """Get admin service instance."""
    return _admin_service_instance
