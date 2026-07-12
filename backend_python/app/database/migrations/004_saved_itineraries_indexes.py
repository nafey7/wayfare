"""Indexes on saved_itineraries for list queries and chat-scoped auto-save dedupe.

Idempotent: create_index with the same name/options is safe to repeat.

Index names and options are duplicated from ``ensure_saved_itinerary_indexes`` in
``app.domains.saved_itinerary.repository`` — keep them in sync. Do not import
that module here: ``app.domains.saved_itinerary`` package ``__init__`` pulls the
full repository graph at migrate load time.
"""

import logging

from pymongo.errors import OperationFailure

from app.database.constants import SAVED_ITINERARIES_COLLECTION

logger = logging.getLogger(__name__)

# Must match app.domains.saved_itinerary.repository (startup uses the same names).
INDEX_NAME_USER_CREATED = "idx_saved_itineraries_user_created"
INDEX_NAME_USER_CHAT_UNIQUE = "uniq_saved_itineraries_user_chat"


async def up(db):
    """Create list index (user_id, created_at) and partial unique (user_id, chat_id)."""
    coll = db[SAVED_ITINERARIES_COLLECTION]
    await coll.create_index(
        [("user_id", 1), ("created_at", -1)],
        name=INDEX_NAME_USER_CREATED,
    )
    await coll.create_index(
        [("user_id", 1), ("chat_id", 1)],
        name=INDEX_NAME_USER_CHAT_UNIQUE,
        unique=True,
        partialFilterExpression={"chat_id": {"$type": "string"}},
    )
    logger.info(
        "Migration complete: indexes %s, %s on %s",
        INDEX_NAME_USER_CREATED,
        INDEX_NAME_USER_CHAT_UNIQUE,
        SAVED_ITINERARIES_COLLECTION,
    )


async def down(db):
    """Drop indexes if present."""
    coll = db[SAVED_ITINERARIES_COLLECTION]
    for name in (INDEX_NAME_USER_CHAT_UNIQUE, INDEX_NAME_USER_CREATED):
        try:
            await coll.drop_index(name)
        except OperationFailure as exc:
            # IndexNotFound (27) or equivalent — idempotent down()
            if (
                getattr(exc, "code", None) != 27
                and "index not found" not in str(exc).lower()
            ):
                raise
            logger.debug("drop_index skipped for %s: %s", name, exc)
