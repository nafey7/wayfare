"""Tests for ``backfill_guest_itinerary_for_chat`` (claim-time itinerary backfill).

Covers the gap where guest-era ``itinerary_results`` messages keep
``structured_itinerary`` in ``action_data`` but never get a
``saved_itinerary_id`` (auto-save is auth-gated). Without backfill, after the
guest signs in and revisits the chat, "View itinerary" falls through to
``/itinerary?destination=...`` and renders nothing.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.chat.repository import backfill_guest_itinerary_for_chat

USER_ID = "507f1f77bcf86cd799439011"
USER_OID = ObjectId(USER_ID)
CHAT_ID = "550e8400-e29b-41d4-a716-446655440000"


def _itin_msg(
    *,
    has_structured: bool = True,
    saved_id: str | None = None,
    created_at: datetime | None = None,
    destination: str = "Lisbon",
) -> dict:
    action_data: dict = {
        "destination": destination,
        "origin": "London",
        "departure_date": "2026-06-01",
        "adults": 2,
    }
    if has_structured:
        action_data["structured_itinerary"] = {
            "itineraryItems": [{"day": 1}],
        }
    if saved_id is not None:
        action_data["saved_itinerary_id"] = saved_id
    return {
        "_id": ObjectId(),
        "chat_id": CHAT_ID,
        "user_id": USER_OID,
        "status": 10,
        "action": "itinerary_results",
        "action_data": action_data,
        "created_at": created_at or datetime.now(UTC),
    }


def _mock_db(latest_doc: dict | None, modified_count: int = 0):
    chats_coll = MagicMock()
    chats_coll.find_one = AsyncMock(return_value=latest_doc)
    chats_coll.update_many = AsyncMock(
        return_value=MagicMock(modified_count=modified_count)
    )
    db = MagicMock()
    type(db).__getitem__ = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda name: chats_coll if name == "chats_python" else MagicMock()
    )
    return db, chats_coll


@pytest.mark.asyncio
async def test_backfill_creates_saved_itinerary_and_stamps_id() -> None:
    latest = _itin_msg(created_at=datetime.now(UTC))
    db, chats_coll = _mock_db(latest_doc=latest, modified_count=1)

    saved_response = MagicMock(id="saved-it-123")
    with (
        patch(
            "app.domains.chat.repository.get_database",
            new=AsyncMock(return_value=db),
        ),
        patch(
            "app.domains.saved_itinerary.repository.upsert_saved_itinerary_for_chat",
            new=AsyncMock(return_value=saved_response),
        ) as mock_upsert,
    ):
        stamped = await backfill_guest_itinerary_for_chat(
            chat_id=CHAT_ID, user_id=USER_ID
        )

    assert stamped == 1
    mock_upsert.assert_awaited_once()
    args, _ = mock_upsert.await_args
    assert args[0] == USER_ID
    assert args[1] == CHAT_ID
    payload = args[2]
    assert payload.structured_itinerary == {"itineraryItems": [{"day": 1}]}
    assert payload.trip_meta == {
        "origin": "London",
        "destination": "Lisbon",
        "departure_date": "2026-06-01",
        "adults": 2,
    }
    chats_coll.update_many.assert_awaited_once()
    update_call = chats_coll.update_many.await_args
    assert update_call.args[1] == {
        "$set": {"action_data.saved_itinerary_id": "saved-it-123"}
    }


@pytest.mark.asyncio
async def test_backfill_noop_when_no_guest_itinerary_messages() -> None:
    db, chats_coll = _mock_db(latest_doc=None)

    with (
        patch(
            "app.domains.chat.repository.get_database",
            new=AsyncMock(return_value=db),
        ),
        patch(
            "app.domains.saved_itinerary.repository.upsert_saved_itinerary_for_chat",
            new=AsyncMock(),
        ) as mock_upsert,
    ):
        stamped = await backfill_guest_itinerary_for_chat(
            chat_id=CHAT_ID, user_id=USER_ID
        )

    assert stamped == 0
    mock_upsert.assert_not_awaited()
    chats_coll.update_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_skips_when_structured_itinerary_invalid() -> None:
    bad = _itin_msg()
    bad["action_data"]["structured_itinerary"] = {}  # empty dict — nothing to save
    db, _chats_coll = _mock_db(latest_doc=bad)

    with (
        patch(
            "app.domains.chat.repository.get_database",
            new=AsyncMock(return_value=db),
        ),
        patch(
            "app.domains.saved_itinerary.repository.upsert_saved_itinerary_for_chat",
            new=AsyncMock(),
        ) as mock_upsert,
    ):
        stamped = await backfill_guest_itinerary_for_chat(
            chat_id=CHAT_ID, user_id=USER_ID
        )

    assert stamped == 0
    mock_upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_filter_targets_missing_or_null_saved_itinerary_id() -> None:
    """Filter must exclude messages already stamped (idempotency)."""
    latest = _itin_msg()
    db, chats_coll = _mock_db(latest_doc=latest, modified_count=2)

    saved_response = MagicMock(id="saved-it-xyz")
    with (
        patch(
            "app.domains.chat.repository.get_database",
            new=AsyncMock(return_value=db),
        ),
        patch(
            "app.domains.saved_itinerary.repository.upsert_saved_itinerary_for_chat",
            new=AsyncMock(return_value=saved_response),
        ),
    ):
        await backfill_guest_itinerary_for_chat(chat_id=CHAT_ID, user_id=USER_ID)

    find_filter = chats_coll.find_one.await_args.args[0]
    assert find_filter["chat_id"] == CHAT_ID
    assert find_filter["user_id"] == USER_OID
    assert find_filter["action"] == "itinerary_results"
    assert find_filter["action_data.structured_itinerary"] == {
        "$exists": True,
        "$ne": None,
    }
    assert {"action_data.saved_itinerary_id": {"$exists": False}} in find_filter["$or"]
    assert {"action_data.saved_itinerary_id": None} in find_filter["$or"]
    assert {"action_data.saved_itinerary_id": ""} in find_filter["$or"]


@pytest.mark.asyncio
async def test_backfill_picks_latest_when_multiple() -> None:
    """find_one with sort=created_at desc returns the latest itinerary message."""
    latest = _itin_msg(
        destination="Porto", created_at=datetime.now(UTC)
    )  # newer message
    db, chats_coll = _mock_db(latest_doc=latest, modified_count=3)

    saved_response = MagicMock(id="saved-it-newest")
    with (
        patch(
            "app.domains.chat.repository.get_database",
            new=AsyncMock(return_value=db),
        ),
        patch(
            "app.domains.saved_itinerary.repository.upsert_saved_itinerary_for_chat",
            new=AsyncMock(return_value=saved_response),
        ) as mock_upsert,
    ):
        stamped = await backfill_guest_itinerary_for_chat(
            chat_id=CHAT_ID, user_id=USER_ID
        )

    assert stamped == 3
    payload = mock_upsert.await_args.args[2]
    assert payload.trip_meta["destination"] == "Porto"
    # Ensure sort directive was provided
    assert chats_coll.find_one.await_args.kwargs.get("sort") == [("created_at", -1)]
