"""Phase 1–2: booking_events saved_itinerary_id persistence (avoids test_bookings/conftest patch)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.bookings import BookingService
from app.domains.bookings.constants import TEMP_EXTERNAL_REF
from app.domains.bookings.schemas import CreateBookingEventRequest


class TestCreateBookingSavedItineraryId:
    """BookingService.create_booking persists optional saved_itinerary_id."""

    @pytest.mark.asyncio
    @patch(
        "app.domains.bookings.service.ensure_saved_itinerary_owned_by_user",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.service.VoyaReferenceGenerator.generate_unique",
        new_callable=AsyncMock,
    )
    @patch("app.domains.bookings.service.get_database")
    async def test_inserts_saved_itinerary_id_when_provided(
        self, mock_get_database, mock_gen_unique, mock_ensure_owned
    ):
        """Document includes saved_itinerary_id (PyObjectId serializes to str in model_dump)."""
        inserted = ObjectId()
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=inserted))
        mock_get_database.return_value = {"booking_events": mock_collection}
        mock_gen_unique.return_value = "VOYA-LINK01"

        itinerary_oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret
        mock_ensure_owned.return_value = itinerary_oid
        svc = BookingService("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        await svc.create_booking(
            CreateBookingEventRequest(
                external_booking_reference="EXT-LINK",
                action="BOOKED",
                saved_itinerary_id=str(itinerary_oid),
            )
        )

        mock_ensure_owned.assert_called_once_with(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            str(itinerary_oid),
        )
        saved = mock_collection.insert_one.call_args[0][0]
        assert saved.get("saved_itinerary_id") == str(itinerary_oid)

    @pytest.mark.asyncio
    @patch(
        "app.domains.bookings.service.ensure_saved_itinerary_owned_by_user",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.service.VoyaReferenceGenerator.generate_unique",
        new_callable=AsyncMock,
    )
    @patch("app.domains.bookings.service.get_database")
    async def test_omits_saved_itinerary_id_when_invalid_string(
        self, mock_get_database, mock_gen_unique, mock_ensure_owned
    ):
        """Invalid ObjectId string is ignored (no field or None)."""
        inserted = ObjectId()
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=inserted))
        mock_get_database.return_value = {"booking_events": mock_collection}
        mock_gen_unique.return_value = "VOYA-LINK02"

        mock_ensure_owned.return_value = None
        svc = BookingService("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        await svc.create_booking(
            CreateBookingEventRequest(
                external_booking_reference="EXT-LINK2",
                action="BOOKED",
                saved_itinerary_id="bad-id",
            )
        )

        saved = mock_collection.insert_one.call_args[0][0]
        assert saved.get("saved_itinerary_id") is None

    @pytest.mark.asyncio
    @patch(
        "app.domains.bookings.service.ensure_saved_itinerary_owned_by_user",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.service.VoyaReferenceGenerator.generate_unique",
        new_callable=AsyncMock,
    )
    @patch("app.domains.bookings.service.get_database")
    async def test_omits_saved_itinerary_id_when_not_owned(
        self, mock_get_database, mock_gen_unique, mock_ensure_owned
    ):
        """Valid ObjectId but not owned by user is not persisted."""
        inserted = ObjectId()
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=inserted))
        mock_get_database.return_value = {"booking_events": mock_collection}
        mock_gen_unique.return_value = "VOYA-LINK03"

        mock_ensure_owned.return_value = None
        other_oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret
        svc = BookingService("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        await svc.create_booking(
            CreateBookingEventRequest(
                external_booking_reference="EXT-LINK3",
                action="BOOKED",
                saved_itinerary_id=str(other_oid),
            )
        )

        saved = mock_collection.insert_one.call_args[0][0]
        assert saved.get("saved_itinerary_id") is None


class TestUpdateBookingAfterFlightConfirmationSavedItinerary:
    """LCC success path can set saved_itinerary_id (Phase 2)."""

    @pytest.mark.asyncio
    @patch("app.domains.bookings.service.get_database")
    async def test_sets_saved_itinerary_id_on_lcc_update(self, mock_get_database):
        mock_collection = Mock()
        mock_collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
        mock_get_database.return_value = {"booking_events": mock_collection}
        oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret

        await BookingService.update_booking_after_flight_confirmation(
            "VOYA-LCC-X",
            "FL-EXT-REAL-REF",
            saved_itinerary_id=oid,
        )

        mock_collection.update_one.assert_called_once()
        filter_q, update_op = mock_collection.update_one.call_args[0]
        assert filter_q["voya_booking_reference"] == "VOYA-LCC-X"
        assert filter_q["external_booking_reference"] == TEMP_EXTERNAL_REF
        assert filter_q["carrier_type"] == "LCC"
        assert filter_q["action"] == "BOOKED"
        assert update_op["$set"]["saved_itinerary_id"] == oid
