"""Set role to admin for users whose email ends with @myvoya.ai.

This migration updates the users collection so that any user with an email
ending in @myvoya.ai has role "admin", unless they already have an admin role
(admin or super_admin).

Idempotent: safe to run multiple times (update_one with $set).
"""

import logging
from datetime import UTC, datetime

from app.database.constants import USERS_COLLECTION

# Role strings must match app.domains.user.enums.UserRole — do not import
# app.domains.user.* here; package __init__ pulls services and causes circular imports.
ADMIN_ROLES = {"admin", "super_admin"}
TARGET_ADMIN_ROLE = "admin"

logger = logging.getLogger(__name__)

MYVOYA_EMAIL_REGEX = r"@myvoya\.ai$"


async def up(db):
    """Set role to admin for @myvoya.ai emails that are not already admin."""
    users = db[USERS_COLLECTION]
    cursor = users.find(
        {
            "email": {"$regex": MYVOYA_EMAIL_REGEX, "$options": "i"},
            "role": {"$nin": list(ADMIN_ROLES)},
        }
    )
    updated_count = 0
    async for doc in cursor:
        user_id = doc.get("_id")
        email = doc.get("email", "")
        result = await users.update_one(
            {"_id": user_id},
            {"$set": {"role": TARGET_ADMIN_ROLE, "updatedAt": datetime.now(UTC)}},
        )
        if result.modified_count:
            updated_count += 1
            logger.info("Set role=admin for user %s (%s)", email, user_id)
    logger.info("Migration complete: %d user(s) updated to admin", updated_count)


async def down(db):
    """No-op: role downgrade would require per-user rollback logic."""
    pass
