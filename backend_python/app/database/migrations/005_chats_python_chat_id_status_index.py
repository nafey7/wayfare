"""Compound index on chats_python for guest_session_may_use_chat_id lookup.

``find_one({"chat_id": ..., "status": 10})`` runs on every public chat message.
Idempotent: create_index with the same name/options is safe to repeat.
"""

import logging

from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

CHATS_PYTHON_COLLECTION = "chats_python"
INDEX_NAME = "chat_id_1_status_1"


async def up(db):
    """Create index (chat_id, status) on chats_python."""
    coll = db[CHATS_PYTHON_COLLECTION]
    await coll.create_index(
        [("chat_id", 1), ("status", 1)],
        name=INDEX_NAME,
    )
    logger.info(
        "Migration complete: index %s on %s",
        INDEX_NAME,
        CHATS_PYTHON_COLLECTION,
    )


async def down(db):
    """Drop the index if present."""
    coll = db[CHATS_PYTHON_COLLECTION]
    try:
        await coll.drop_index(INDEX_NAME)
    except OperationFailure as exc:
        if (
            getattr(exc, "code", None) != 27
            and "index not found" not in str(exc).lower()
        ):
            raise
        logger.debug("drop_index skipped for %s: %s", INDEX_NAME, exc)
