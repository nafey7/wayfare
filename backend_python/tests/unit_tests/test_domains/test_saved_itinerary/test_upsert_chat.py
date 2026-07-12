"""Tests for upsert_saved_itinerary_for_chat."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.domains.saved_itinerary.repository import upsert_saved_itinerary_for_chat
from app.domains.saved_itinerary.schemas import SavedItineraryCreate

USER_ID = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
CHAT_ID = "chat-abc"
ITIN_ID = "507f1f77bcf86cd799439022"  # pragma: allowlist secret


@pytest.mark.asyncio
class TestUpsertSavedItineraryForChat:
    """One document per (user, chat); stable id across regenerations."""

    @patch(
        "app.domains.saved_itinerary.repository.get_database", new_callable=AsyncMock
    )
    async def test_upsert_returns_response_with_id(self, mock_get_db):
        oid = ObjectId(ITIN_ID)
        now = datetime.now(UTC)
        doc = {
            "_id": oid,
            "user_id": ObjectId(USER_ID),
            "chat_id": CHAT_ID,
            "structured_itinerary": {"days": []},
            "trip_meta": None,
            "created_at": now,
            "updated_at": now,
        }
        coll = AsyncMock()
        coll.find_one_and_update = AsyncMock(return_value=doc)
        mock_get_db.return_value = {"saved_itineraries": coll}

        result = await upsert_saved_itinerary_for_chat(
            USER_ID,
            CHAT_ID,
            SavedItineraryCreate(structured_itinerary={"days": []}),
        )

        assert result.id == ITIN_ID
        assert coll.find_one_and_update.await_count == 1
        assert coll.find_one_and_update.call_args[1]["upsert"] is True

    @patch(
        "app.domains.saved_itinerary.repository.get_database", new_callable=AsyncMock
    )
    async def test_duplicate_key_retries_update_without_upsert(self, mock_get_db):
        oid = ObjectId(ITIN_ID)
        now = datetime.now(UTC)
        doc = {
            "_id": oid,
            "user_id": ObjectId(USER_ID),
            "chat_id": CHAT_ID,
            "structured_itinerary": {"x": 1},
            "trip_meta": None,
            "created_at": now,
            "updated_at": now,
        }
        coll = AsyncMock()
        coll.find_one_and_update = AsyncMock(
            side_effect=[DuplicateKeyError("dup"), doc],
        )
        mock_get_db.return_value = {"saved_itineraries": coll}

        result = await upsert_saved_itinerary_for_chat(
            USER_ID,
            CHAT_ID,
            SavedItineraryCreate(structured_itinerary={"x": 1}),
        )

        assert result.id == ITIN_ID
        assert coll.find_one_and_update.await_count == 2
        assert coll.find_one_and_update.call_args_list[1][1]["upsert"] is False
