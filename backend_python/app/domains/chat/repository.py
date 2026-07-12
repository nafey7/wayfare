"""Chat repository functions for data persistence"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from bson import ObjectId

from app.database.dependencies import get_database
from app.database.models.chats_python import ChatsPythonModel
from app.database.types import PyObjectId
from app.domains.chat.schemas import ClaimOutcomeStatus
from app.domains.common.types import now_utc

# ---------------------------------------------------------------------------
# Conversation CRUD (multi-conversation support)
# ---------------------------------------------------------------------------

CONVERSATIONS_COLLECTION = "conversations"


async def get_or_create_chat_conversation(user_id: str) -> str:
    """Get the most recent conversation or create a new one.

    Uses the ``conversations`` collection when available, falling back
    to the legacy ``chats_python`` lookup for backward compatibility.
    """
    db = await get_database()
    conv_coll = db[CONVERSATIONS_COLLECTION]

    # Try conversations collection first (new path)
    conversation = await conv_coll.find_one(
        {"user_id": ObjectId(user_id), "is_deleted": False},
        sort=[("last_message_at", -1)],
    )
    if conversation:
        return conversation["chat_id"]

    # Fallback: legacy lookup in chats_python
    chats_coll = db["chats_python"]
    existing = await chats_coll.find_one({"user_id": ObjectId(user_id), "status": 10})
    if existing and existing.get("chat_id"):
        return existing["chat_id"]

    # No conversations at all — create a new one
    doc = await create_conversation(user_id)
    return doc["chat_id"]


async def list_user_conversations(
    user_id: str, limit: int = 50, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    """List user's non-deleted conversations, newest first."""
    db = await get_database()
    coll = db[CONVERSATIONS_COLLECTION]
    query: dict[str, Any] = {
        "user_id": ObjectId(user_id),
        "is_deleted": False,
    }
    total = await coll.count_documents(query)
    cursor = coll.find(query).sort("last_message_at", -1).skip(offset).limit(limit)
    conversations = await cursor.to_list(length=limit)
    return cast("list[dict[str, Any]]", conversations), total


async def create_conversation(
    user_id: str, name: str = "New conversation"
) -> dict[str, Any]:
    """Create a new conversation and return its metadata."""
    db = await get_database()
    coll = db[CONVERSATIONS_COLLECTION]
    chat_id = str(uuid.uuid4())
    now = now_utc()
    doc: dict[str, Any] = {
        "chat_id": chat_id,
        "user_id": ObjectId(user_id),
        "name": name,
        "is_deleted": False,
        "message_count": 0,
        "last_message_at": now,
        "last_message_preview": "",
        "created_at": now,
        "updated_at": now,
    }
    await coll.insert_one(doc)
    return doc


async def rename_conversation(chat_id: str, user_id: str, name: str) -> bool:
    """Rename a conversation. Returns True if updated."""
    db = await get_database()
    coll = db[CONVERSATIONS_COLLECTION]
    result = await coll.update_one(
        {
            "chat_id": chat_id,
            "user_id": ObjectId(user_id),
            "is_deleted": False,
        },
        {"$set": {"name": name[:50], "updated_at": now_utc()}},
    )
    return result.modified_count > 0


async def soft_delete_conversation(chat_id: str, user_id: str) -> bool:
    """Soft delete a conversation. Returns True if deleted."""
    db = await get_database()
    coll = db[CONVERSATIONS_COLLECTION]
    result = await coll.update_one(
        {"chat_id": chat_id, "user_id": ObjectId(user_id)},
        {"$set": {"is_deleted": True, "updated_at": now_utc()}},
    )
    return result.modified_count > 0


async def user_owns_conversation(chat_id: str, user_id: str) -> bool:
    """Return True if ``user_id`` owns ``chat_id``.

    Checks the ``conversations`` collection first (new path) and falls back to
    ``chats_python`` for legacy conversations that never got a conversations
    doc (pre-006 data or guest chats later claimed by a user).
    """
    db = await get_database()

    conv_doc = await db[CONVERSATIONS_COLLECTION].find_one(
        {"chat_id": chat_id, "user_id": ObjectId(user_id), "is_deleted": False},
        projection={"_id": 1},
    )
    if conv_doc is not None:
        return True

    legacy_doc = await db["chats_python"].find_one(
        {"chat_id": chat_id, "user_id": ObjectId(user_id), "status": 10},
        projection={"_id": 1},
    )
    return legacy_doc is not None


async def update_conversation_on_message(chat_id: str, message_preview: str) -> None:
    """Increment message count and update last_message timestamp."""
    db = await get_database()
    coll = db[CONVERSATIONS_COLLECTION]
    await coll.update_one(
        {"chat_id": chat_id},
        {
            "$inc": {"message_count": 1},
            "$set": {
                "last_message_at": now_utc(),
                "last_message_preview": message_preview[:100],
                "updated_at": now_utc(),
            },
        },
    )


async def create_message(
    content: dict[str, Any],
    chat_id: str,
    sender: str,
    user_id: str | None = None,
    intent_name: str | None = None,
    action: str | None = None,
    action_data: Any | None = None,
    *,
    guest_fingerprint: str | None = None,
) -> ChatsPythonModel:
    """Store a chat message using ChatsPythonModel.

    For authenticated users pass ``user_id``. For guest (public) chat pass
    ``user_id=None`` and ``guest_fingerprint`` (e.g. browser session UUID).
    """
    if (user_id is None) == (guest_fingerprint is None):
        raise ValueError("Exactly one of user_id or guest_fingerprint is required")

    db = await get_database()
    collection = db["chats_python"]

    # Create model instance - note: 'from' is aliased to 'from_' in the model
    message_data: dict[str, Any] = {
        "chat_id": chat_id,
        "content": content,
        "from": sender,  # Use 'from' key for MongoDB, model will handle alias
        "intent_name": intent_name,
        "action": action,
        "action_data": action_data,
        "status": 10,
        "created_at": now_utc(),
    }
    if user_id is not None:
        message_data["user_id"] = PyObjectId(user_id)
    else:
        message_data["fingerprint"] = guest_fingerprint

    # Create model from dict
    message = ChatsPythonModel(**message_data)

    # Convert to dict for MongoDB
    message_dict = message.model_dump(by_alias=True, exclude_none=True)

    # Insert into database
    result = await collection.insert_one(message_dict)
    message.id = PyObjectId(result.inserted_id)

    return message


async def guest_session_may_use_chat_id(chat_id: str, guest_fingerprint: str) -> bool:
    """Return whether this guest session may post to ``chat_id``.

    - If there are no messages for ``chat_id``, allow (new conversation).
    - If messages exist for an authenticated user, deny (guest cannot hijack).
    - Otherwise require ``fingerprint`` on stored messages to match ``guest_fingerprint``.
    """
    db = await get_database()
    collection = db["chats_python"]
    doc = await collection.find_one({"chat_id": chat_id, "status": 10})
    if doc is None:
        return True
    if doc.get("user_id") is not None:
        return False
    return doc.get("fingerprint") == guest_fingerprint


@dataclass
class ClaimOutcome:
    """Result of ``claim_messages_for_user``."""

    status: ClaimOutcomeStatus
    message_count: int = 0
    chat_id: str | None = None


async def claim_messages_for_user(
    chat_id: str,
    fingerprint: str,
    user_id: str,
    *,
    max_age_minutes: int,
    message_cap: int,
) -> ClaimOutcome:
    """Re-own guest messages on ``chat_id`` for ``user_id``.

    Idempotent: re-running on an already-claimed thread returns
    ``already_claimed`` without writes.
    """
    db = await get_database()
    chats = db["chats_python"]
    user_oid = ObjectId(user_id)

    # Unsorted find: relies on the invariant that if more than `message_cap`
    # eligible docs exist we always reject as TOO_LARGE before age matters, so
    # natural Mongo order can't change the outcome (newest-doc selection only
    # runs once we know the set fits under the cap).
    cursor = chats.find({"chat_id": chat_id, "status": 10})
    docs: list[dict[str, Any]] = cast(
        "list[dict[str, Any]]", await cursor.to_list(length=message_cap + 1)
    )

    if not docs:
        return ClaimOutcome(status=ClaimOutcomeStatus.NOTHING_TO_CLAIM, chat_id=chat_id)

    # Inspect ownership and fingerprint state.
    guest_msgs: list[dict[str, Any]] = []
    other_user_msgs = 0
    self_owned_msgs = 0
    newest: datetime | None = None
    for doc in docs:
        owner = doc.get("user_id")
        fp = doc.get("fingerprint")
        ts = doc.get("created_at")
        if isinstance(ts, datetime) and (newest is None or ts > newest):
            newest = ts
        if owner is not None:
            if owner == user_oid:
                self_owned_msgs += 1
            else:
                other_user_msgs += 1
            continue
        if fp != fingerprint:
            return ClaimOutcome(
                status=ClaimOutcomeStatus.REJECTED_FINGERPRINT_MISMATCH,
                chat_id=chat_id,
            )
        guest_msgs.append(doc)

    if other_user_msgs > 0:
        return ClaimOutcome(
            status=ClaimOutcomeStatus.REJECTED_OWNED_BY_OTHER_USER, chat_id=chat_id
        )

    if not guest_msgs:
        # All non-deleted messages already owned by this user.
        if self_owned_msgs > 0:
            return ClaimOutcome(
                status=ClaimOutcomeStatus.ALREADY_CLAIMED,
                message_count=self_owned_msgs,
                chat_id=chat_id,
            )
        return ClaimOutcome(status=ClaimOutcomeStatus.NOTHING_TO_CLAIM, chat_id=chat_id)

    total_count = len(guest_msgs) + self_owned_msgs
    if total_count > message_cap:
        return ClaimOutcome(
            status=ClaimOutcomeStatus.REJECTED_TOO_LARGE, chat_id=chat_id
        )

    if newest is not None:
        # Compare in UTC; ``newest`` may be naive (legacy) — treat as UTC.
        from datetime import UTC

        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=UTC)
        cutoff = now_utc() - timedelta(minutes=max_age_minutes)
        if newest < cutoff:
            return ClaimOutcome(
                status=ClaimOutcomeStatus.REJECTED_TOO_OLD, chat_id=chat_id
            )

    # Re-own messages.
    update_result = await chats.update_many(
        {"chat_id": chat_id, "fingerprint": fingerprint, "user_id": None},
        {"$set": {"user_id": user_oid}, "$unset": {"fingerprint": ""}},
    )

    # Upsert conversations doc (idempotent).
    conv = db[CONVERSATIONS_COLLECTION]
    last_preview = ""
    last_doc = await chats.find_one(
        {"chat_id": chat_id, "user_id": user_oid, "status": 10},
        sort=[("created_at", -1)],
    )
    last_at = newest or now_utc()
    if last_doc:
        content = last_doc.get("content")
        if isinstance(content, dict):
            txt = content.get("text") or ""
            last_preview = str(txt)[:100]
        elif isinstance(content, str):
            last_preview = content[:100]
        if isinstance(last_doc.get("created_at"), datetime):
            last_at = last_doc["created_at"]
    now = now_utc()
    await conv.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "user_id": user_oid,
                "is_deleted": False,
                "message_count": total_count,
                "last_message_at": last_at,
                "last_message_preview": last_preview,
                "updated_at": now,
            },
            "$setOnInsert": {
                "chat_id": chat_id,
                "name": "New conversation",
                "created_at": now,
            },
        },
        upsert=True,
    )

    return ClaimOutcome(
        status=ClaimOutcomeStatus.CLAIMED,
        message_count=int(update_result.modified_count) + self_owned_msgs,
        chat_id=chat_id,
    )


# Trip-meta keys persisted at the top level of an itinerary_results message's
# ``action_data``. Shared with ``_try_auto_save_itinerary_and_enrich`` in
# service.py so the auth auto-save and guest claim-time backfill can't drift.
ITINERARY_TRIP_META_KEYS: tuple[str, ...] = (
    "origin",
    "destination",
    "departure_date",
    "return_date",
    "adults",
    "children",
    "infants",
    "trip_type",
    "origin_location",
    "destination_location",
)


async def backfill_guest_itinerary_for_chat(chat_id: str, user_id: str) -> int:
    """Persist a ``saved_itineraries`` row for guest-era itinerary messages on a
    claimed chat, and stamp ``saved_itinerary_id`` back onto every matching
    message's ``action_data`` so reload routes to ``/itinerary/:id``.

    Guest auto-save is gated on authentication, so itinerary_results generated
    before sign-in keep ``structured_itinerary`` in ``action_data`` but never get
    a ``saved_itinerary_id``. Without this, ``ItineraryResultMessage`` falls
    through to the ``/itinerary?destination=...`` path which renders nothing.

    Idempotent: filters on missing/null ``saved_itinerary_id``, so re-running on
    an already-backfilled chat is a no-op.

    Returns the number of messages stamped (0 if nothing to backfill).
    """
    from app.domains.saved_itinerary.repository import upsert_saved_itinerary_for_chat
    from app.domains.saved_itinerary.schemas import SavedItineraryCreate

    db = await get_database()
    chats = db["chats_python"]
    cid = str(chat_id).strip()
    uid_oid = ObjectId(user_id)

    base_filter: dict[str, Any] = {
        "chat_id": cid,
        "user_id": uid_oid,
        "status": 10,
        "action": "itinerary_results",
        "action_data.structured_itinerary": {"$exists": True, "$ne": None},
        "$or": [
            {"action_data.saved_itinerary_id": {"$exists": False}},
            {"action_data.saved_itinerary_id": None},
            {"action_data.saved_itinerary_id": ""},
        ],
    }

    latest = await chats.find_one(base_filter, sort=[("created_at", -1)])
    if not latest:
        return 0

    action_data = latest.get("action_data") or {}
    if not isinstance(action_data, dict):
        return 0
    structured_itinerary = action_data.get("structured_itinerary")
    if not isinstance(structured_itinerary, dict) or not structured_itinerary:
        return 0

    trip_meta: dict[str, Any] = {
        k: action_data[k]
        for k in ITINERARY_TRIP_META_KEYS
        if action_data.get(k) is not None
    }

    saved = await upsert_saved_itinerary_for_chat(
        user_id,
        cid,
        SavedItineraryCreate(
            structured_itinerary=structured_itinerary,
            trip_meta=trip_meta or None,
        ),
    )

    # If the guest produced multiple distinct itineraries in this chat, every
    # un-stamped itinerary_results message gets the same saved_itinerary_id —
    # the latest itinerary wins because upsert_saved_itinerary_for_chat is
    # one-per-chat. This mirrors the auth-flow auto-save in service.py
    # (``_try_auto_save_itinerary_and_enrich``); kept intentional so reload
    # routes to a real /itinerary/:id instead of the empty fallback.
    stamp_result = await chats.update_many(
        base_filter,
        {"$set": {"action_data.saved_itinerary_id": saved.id}},
    )
    return int(stamp_result.modified_count)


async def get_chat_messages(chat_id: str, limit: int = 50) -> list[ChatsPythonModel]:
    """Get messages for a chat session"""
    db = await get_database()
    collection = db["chats_python"]

    cursor = (
        collection.find({"chat_id": chat_id, "status": 10})
        .sort("created_at", -1)
        .limit(limit)
    )

    messages = []
    async for doc in cursor:
        messages.append(ChatsPythonModel(**doc))

    # Return in chronological order
    return list(reversed(messages))


async def get_user_sessions(user_id: str, limit: int = 10) -> list[str]:
    """Get unique chat sessions for a user"""
    db = await get_database()
    collection = db["chats_python"]

    # Get distinct chat_ids for user
    chat_ids = await collection.distinct(
        "chat_id", {"user_id": ObjectId(user_id), "status": 10}
    )

    return chat_ids[:limit] if chat_ids else []


async def clear_chat_messages(chat_id: str) -> int:
    """Clear all messages in a chat conversation"""
    db = await get_database()
    collection = db["chats_python"]

    # Mark messages as deleted (status = 0) instead of actual deletion
    result = await collection.update_many(
        {"chat_id": chat_id, "status": 10}, {"$set": {"status": 0}}
    )

    return result.modified_count
