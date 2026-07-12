"""Compound index on booking_events for saved itinerary linkage queries.

Idempotent: create_index with the same name/options is safe to repeat.
"""

import logging

from pymongo.errors import OperationFailure

from app.database.constants import BOOKING_EVENT_COLLECTION

logger = logging.getLogger(__name__)

INDEX_NAME = "user_id_saved_itinerary_id_1"


async def up(db):
    """Create index (user_id, saved_itinerary_id) on booking_events."""
    coll = db[BOOKING_EVENT_COLLECTION]
    await coll.create_index(
        [("user_id", 1), ("saved_itinerary_id", 1)],
        name=INDEX_NAME,
    )
    logger.info(
        "Migration complete: index %s on %s", INDEX_NAME, BOOKING_EVENT_COLLECTION
    )


async def down(db):
    """Drop the index if present."""
    coll = db[BOOKING_EVENT_COLLECTION]
    try:
        await coll.drop_index(INDEX_NAME)
    except OperationFailure as exc:
        if (
            getattr(exc, "code", None) != 27
            and "index not found" not in str(exc).lower()
        ):
            raise
        logger.debug("drop_index skipped for %s: %s", INDEX_NAME, exc)
