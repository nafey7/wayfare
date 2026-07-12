"""Tests for ensure_saved_itinerary_owned_by_user."""

from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from app.domains.saved_itinerary import ensure_saved_itinerary_owned_by_user

USER_ID = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
ITIN_ID = "507f1f77bcf86cd799439022"  # pragma: allowlist secret


@pytest.mark.asyncio
class TestEnsureSavedItineraryOwnedByUser:
    """Ownership validation for booking linkage."""

    async def test_none_and_empty_return_none(self):
        assert await ensure_saved_itinerary_owned_by_user(USER_ID, None) is None
        assert await ensure_saved_itinerary_owned_by_user(USER_ID, "") is None
        assert await ensure_saved_itinerary_owned_by_user(USER_ID, "   ") is None

    async def test_invalid_object_id_returns_none(self):
        with patch(
            "app.domains.saved_itinerary.repository.get_database",
            new_callable=AsyncMock,
        ):
            assert (
                await ensure_saved_itinerary_owned_by_user(USER_ID, "not-an-oid")
                is None
            )

    @patch(
        "app.domains.saved_itinerary.repository.get_database", new_callable=AsyncMock
    )
    async def test_returns_oid_when_doc_exists_for_user(self, mock_get_db):
        coll = AsyncMock()
        coll.find_one = AsyncMock(
            return_value={"_id": ObjectId(ITIN_ID), "user_id": ObjectId(USER_ID)}
        )
        mock_get_db.return_value = {"saved_itineraries": coll}

        result = await ensure_saved_itinerary_owned_by_user(USER_ID, ITIN_ID)

        assert result == ObjectId(ITIN_ID)
        coll.find_one.assert_called_once_with(
            {"_id": ObjectId(ITIN_ID), "user_id": ObjectId(USER_ID)}
        )

    @patch(
        "app.domains.saved_itinerary.repository.get_database", new_callable=AsyncMock
    )
    async def test_returns_none_when_not_found(self, mock_get_db):
        coll = AsyncMock()
        coll.find_one = AsyncMock(return_value=None)
        mock_get_db.return_value = {"saved_itineraries": coll}

        assert await ensure_saved_itinerary_owned_by_user(USER_ID, ITIN_ID) is None
