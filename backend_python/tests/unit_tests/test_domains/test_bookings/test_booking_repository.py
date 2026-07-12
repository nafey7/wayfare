"""Unit tests for BookingRepository."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.domains.bookings.constants import BOOKING_EVENT_COLLECTION, TEMP_EXTERNAL_REF
from app.domains.bookings.repository import BookingRepository


@pytest.mark.asyncio
class TestBookingRepositoryUpdateGdsPending:
    @patch("app.domains.bookings.repository.get_database")
    async def test_update_uses_pending_gds_filter(self, mock_get_database):
        mock_coll = Mock()
        mock_coll.update_one = AsyncMock(
            return_value=Mock(matched_count=1, modified_count=1)
        )
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=mock_coll)
        mock_get_database.return_value = mock_db

        repo = BookingRepository()
        await repo.update_gds_pending_booking_to_booked(
            "VOYA-REPO-1",
            {"external_booking_reference": "EXT-1", "action": "BOOKED"},
        )

        mock_db.__getitem__.assert_called_once_with(BOOKING_EVENT_COLLECTION)
        mock_coll.update_one.assert_called_once()
        flt, upd = mock_coll.update_one.call_args[0]
        assert flt == {
            "voya_booking_reference": "VOYA-REPO-1",
            "external_booking_reference": TEMP_EXTERNAL_REF,
            "action": "PENDING",
            "carrier_type": "GDS",
        }
        assert upd == {
            "$set": {
                "external_booking_reference": "EXT-1",
                "action": "BOOKED",
            },
        }
