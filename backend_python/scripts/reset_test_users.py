"""Reset test users - deletes and recreates them with correct passwords."""

import asyncio
import logging

from app.database.connection import (
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
)
from app.database.constants import USERS_COLLECTION
from app.database.seed.seeder import seed_test_users
from app.database.seed.users import TEST_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reset_test_users() -> None:
    """Delete and recreate test users."""
    try:
        # Connect to database
        await connect_to_mongodb()
        db = get_connection().get_database()
        users_collection = db[USERS_COLLECTION]

        # Delete existing test users
        test_emails = [user["email"] for user in TEST_USERS]
        delete_result = await users_collection.delete_many(
            {"email": {"$in": test_emails}}
        )
        logger.info(f"Deleted {delete_result.deleted_count} existing test users")

        # Recreate test users
        result = await seed_test_users()
        logger.info(f"Created {result['created']} test users")

        logger.info("\n✅ Test users reset successfully!")
        logger.info("You can now login with:")
        for user in TEST_USERS:
            logger.info(f"  - {user['email']} / {user['password']}")

    except Exception as e:
        logger.error(f"Error resetting test users: {e}")
        raise
    finally:
        await disconnect_from_mongodb()


if __name__ == "__main__":
    asyncio.run(reset_test_users())
