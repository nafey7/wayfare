"""MongoDB filters for booking_events.user_id (ObjectId or legacy string)."""

from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId


def booking_events_user_id_filter(
    user_id_str: str,
) -> dict[str, list[ObjectId | str]] | str:
    """Match documents where user_id is stored as ObjectId or as the same hex string."""
    try:
        oid = ObjectId(user_id_str)
        return {"$in": [oid, user_id_str]}
    except InvalidId:
        return user_id_str
