"""Backfill admin role for @myvoya.ai users created after migration 002.

Applies the same @myvoya.ai → admin rule as 002_set_myvoya_admin_role.py to any
user still on a non-admin role. Needed because 002 is a one-time run tracked by
name in _migrations; new signups before the service-layer fix were not covered.

Idempotent: safe to run multiple times — only rows with non-admin roles are touched.
"""

import logging
from datetime import UTC, datetime

from app.database.constants import USERS_COLLECTION

# Role strings must match app.domains.user.enums.UserRole — do not import
# app.domains.user.* here; package __init__ chains cause circular imports.
ADMIN_ROLES = {"admin", "super_admin"}
TARGET_ADMIN_ROLE = "admin"

logger = logging.getLogger(__name__)

# One @: exclude invalid multi-@ values that would match …@myvoya\.ai$ alone
MYVOYA_EMAIL_REGEX = r"^[^@]+@myvoya\.ai$"


async def up(db):
    """Set role to admin for @myvoya.ai emails that are not already admin."""
    users = db[USERS_COLLECTION]
    result = await users.update_many(
        {
            "email": {"$regex": MYVOYA_EMAIL_REGEX, "$options": "i"},
            "role": {"$nin": list(ADMIN_ROLES)},
        },
        {"$set": {"role": TARGET_ADMIN_ROLE, "updated_at": datetime.now(UTC)}},
    )
    logger.info(
        "Migration complete: %d user(s) updated to admin", result.modified_count
    )


async def down(db):
    """No-op: role downgrade would require per-user rollback logic."""
    pass
