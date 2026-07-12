"""Delete test users from database."""

import asyncio
import logging

from app.database.connection import (
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
)
from app.database.constants import USERS_COLLECTION
from app.database.seed.users import TEST_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def delete_test_users() -> None:
    """Delete all test users."""
    try:
        await connect_to_mongodb()
        db = get_connection().get_database()
        users_collection = db[USERS_COLLECTION]

        # Delete test users
        test_emails = [user["email"] for user in TEST_USERS]
        result = await users_collection.delete_many({"email": {"$in": test_emails}})

        logger.info(f"✅ Deleted {result.deleted_count} test users")
        logger.info("Restart the backend to recreate them with correct passwords")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await disconnect_from_mongodb()


if __name__ == "__main__":
    asyncio.run(delete_test_users())
