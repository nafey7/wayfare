"""FastAPI dependency functions for database access."""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.database.connection import get_connection


async def get_database() -> AsyncIOMotorDatabase[Any]:
    """FastAPI dependency for database access.

    Usage in routes:
        @router.get("/users")
        async def get_users(db = Depends(get_database)):
            collection = db[USERS_COLLECTION]
            ...
    """
    return get_connection().get_database()


async def get_collection(collection_name: str) -> AsyncIOMotorCollection[Any]:
    """Get a specific collection.

    Usage:
        collection = await get_collection(USERS_COLLECTION)
    """
    return get_connection().get_collection(collection_name)
