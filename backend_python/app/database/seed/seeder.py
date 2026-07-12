"""Database seeding functions."""

import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.database.connection import get_connection
from app.database.constants import USERS_COLLECTION
from app.domains.auth.service import AuthService

from .users import TEST_USERS

logger = logging.getLogger(__name__)


async def seed_test_users() -> dict[str, int]:
    """Seed test users into database, resetting them to default values on startup."""
    if settings.ENVIRONMENT == "production":
        return {"created": 0, "existing": 0, "reset": 0}

    db = get_connection().get_database()
    users_collection = db[USERS_COLLECTION]

    created = 0
    reset = 0

    for user_data in TEST_USERS:
        email = user_data["email"]

        # Create a copy to avoid mutating the original TEST_USERS
        user_data_copy = user_data.copy()
        password = user_data_copy.pop("password")
        user_doc = {
            **user_data_copy,
            "password_hash": AuthService.hash_password(password),
            "auth_provider": "local",
            "email_verified": True,
            "is_tester": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Check if user exists
        existing_user = await users_collection.find_one({"email": email})

        if existing_user:
            # Check if basic fields need reset first (fast checks)
            basic_fields_wrong = (
                existing_user.get("role") != user_data_copy.get("role")
                or existing_user.get("status") != user_data_copy.get("status")
                or existing_user.get("first_name") != user_data_copy.get("first_name")
                or existing_user.get("last_name") != user_data_copy.get("last_name")
                or existing_user.get("auth_provider") != "local"
                or existing_user.get("email_verified") is not True
                or existing_user.get("is_tester") is not True
                or not existing_user.get("password_hash")  # Missing password hash
            )

            # Only verify password if basic fields are correct (expensive check)
            password_valid = True
            if not basic_fields_wrong and existing_user.get("password_hash"):
                try:
                    password_valid = AuthService.verify_password(
                        password, existing_user.get("password_hash")
                    )
                except Exception:
                    password_valid = False

            needs_reset = basic_fields_wrong or not password_valid

            if needs_reset:
                # Reset existing test user to default seed values
                await users_collection.replace_one(
                    {"email": email},
                    {
                        **user_doc,
                        "_id": existing_user["_id"],
                        "created_at": existing_user.get(
                            "created_at", datetime.now(UTC)
                        ),
                    },
                )
                reset += 1
                logger.info(f"Reset test user to seed defaults: {email}")
            # If user is already correct, do nothing (no log spam)
        else:
            # Create new test user
            result = await users_collection.insert_one(user_doc)
            if result.inserted_id:
                created += 1
                logger.info(f"Created test user: {email}")

    return {"created": created, "existing": 0, "reset": reset}
