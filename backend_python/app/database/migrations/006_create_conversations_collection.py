"""Create ``conversations`` collection for multi-conversation chat.

Adds a metadata collection that tracks per-conversation info (name,
timestamps, message counts) alongside the existing ``chats_python``
messages collection.

Backfills one ``conversations`` document for each distinct
``(user_id, chat_id)`` pair in ``chats_python`` where ``status=10``.

Idempotent: skips documents whose ``chat_id`` already exists in
``conversations``.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

COLLECTION = "conversations"

INDEXES: list[dict[str, Any]] = [
    {
        "keys": [("user_id", 1), ("is_deleted", 1), ("last_message_at", -1)],
        "name": "user_active_conversations",
    },
    {
        "keys": [("chat_id", 1)],
        "name": "chat_id_unique",
        "unique": True,
    },
]


async def up(db: AsyncIOMotorDatabase[Any]) -> None:
    """Create collection, indexes, and backfill from chats_python."""
    coll = db[COLLECTION]

    # 1. Create indexes
    for idx in INDEXES:
        await coll.create_index(
            idx["keys"],
            name=idx["name"],
            unique=idx.get("unique", False),
        )
        logger.info("Created index %s on %s", idx["name"], COLLECTION)

    # 2. Backfill: create a conversations doc for each distinct (user_id, chat_id)
    pipeline = [
        {"$match": {"status": 10, "user_id": {"$ne": None}}},
        {
            "$group": {
                "_id": {"user_id": "$user_id", "chat_id": "$chat_id"},
                "first_message_text": {"$first": "$content.text"},
                "last_message_at": {"$max": "$created_at"},
                "message_count": {"$sum": 1},
                "created_at": {"$min": "$created_at"},
            }
        },
    ]

    chats_coll = db["chats_python"]
    backfilled = 0
    skipped = 0

    async for group in chats_coll.aggregate(pipeline):
        chat_id = group["_id"]["chat_id"]
        user_id = group["_id"]["user_id"]

        # Skip if already backfilled (idempotent)
        existing = await coll.find_one({"chat_id": chat_id})
        if existing:
            skipped += 1
            continue

        preview = ""
        if isinstance(group.get("first_message_text"), str):
            preview = group["first_message_text"][:100]

        doc = {
            "chat_id": chat_id,
            "user_id": user_id,
            "name": "Conversation",
            "is_deleted": False,
            "message_count": group["message_count"],
            "last_message_at": group["last_message_at"] or datetime.now(UTC),
            "last_message_preview": preview,
            "created_at": group["created_at"] or datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await coll.insert_one(doc)
        backfilled += 1

    logger.info(
        "Migration complete: %s collection — %d backfilled, %d skipped",
        COLLECTION,
        backfilled,
        skipped,
    )


async def down(db: AsyncIOMotorDatabase[Any]) -> None:
    """Drop indexes (collection data is preserved)."""
    coll = db[COLLECTION]
    for idx in INDEXES:
        try:
            await coll.drop_index(idx["name"])
        except OperationFailure as exc:
            if (
                getattr(exc, "code", None) != 27
                and "index not found" not in str(exc).lower()
            ):
                raise
            logger.debug("drop_index skipped for %s: %s", idx["name"], exc)
