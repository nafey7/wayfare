"""Initialize ``users.photo_key`` and create a sparse index on it.

Mongo doesn't enforce schema; the application reads ``photo_key`` as
``Optional[str]``. This migration:

1. Sets ``photo_key=null`` on every existing user missing the field so
   ``$exists`` analytics queries behave predictably.
2. Creates a sparse index on ``photo_key`` to speed lookups by S3 key
   (e.g. orphan-object reconciliation jobs).

Idempotent: only documents missing the field are touched; ``create_index``
is a no-op when the index already exists.
"""

import logging

from app.database.constants import USERS_COLLECTION

logger = logging.getLogger(__name__)


async def up(db) -> None:
    """Set ``photo_key=null`` on every user missing the field and add index."""
    result = await db[USERS_COLLECTION].update_many(
        {"photo_key": {"$exists": False}},
        {"$set": {"photo_key": None}},
    )
    logger.info(
        "Migration 011: set photo_key=null on %s users in %s",
        result.modified_count,
        USERS_COLLECTION,
    )

    index_name = await db[USERS_COLLECTION].create_index(
        "photo_key", sparse=True, name="photo_key_sparse"
    )
    logger.info(
        "Migration 011: ensured sparse index %s on %s.photo_key",
        index_name,
        USERS_COLLECTION,
    )


async def down(db) -> None:
    """Drop the index and unset ``photo_key`` on every user document. Idempotent."""
    try:
        await db[USERS_COLLECTION].drop_index("photo_key_sparse")
    except Exception as e:  # pragma: no cover — defensive
        logger.info("Migration 011 down: drop_index skipped (%s)", e)

    result = await db[USERS_COLLECTION].update_many(
        {"photo_key": {"$exists": True}},
        {"$unset": {"photo_key": ""}},
    )
    logger.info(
        "Migration 011 down: unset photo_key on %s users in %s",
        result.modified_count,
        USERS_COLLECTION,
    )
