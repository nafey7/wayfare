"""Phase 3: hotel booking links saved_itinerary_id on successful book only."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.common.enums import AuthProvider
from app.domains.hotel.schemas import (
    GuestInfo,
    HotelBookingRequest,
    HotelBookingResponse,
)
from app.domains.hotel.service import HotelService
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


def _minimal_hotel_book_request(
    *,
    client_ref: str = "VOYA-HOTEL01",
    saved_itinerary_id: str | None = None,
) -> HotelBookingRequest:
    return HotelBookingRequest(
        session_id="sess-fl-123456789012",
        product_id="prod-1",
        token_id="tok-1",
        rate_basis_id="rate-basis-1",
        client_ref=client_ref,
        customer_email="guest@example.com",
        customer_phone="+31600000000",
        booking_note="",
        guests=[
            GuestInfo(
                title="Mr",
                first_name="Test",
                last_name="User",
                room_number=1,
                is_child=False,
            )
        ],
        room_count=1,
        saved_itinerary_id=saved_itinerary_id,
    )


@pytest.fixture
def hotel_user() -> UserPublic:
    now = datetime.now(UTC)
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="T",
        last_name="U",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


class TestHotelCreateBookingSavedItinerary:
    """HotelService.create_booking sets saved_itinerary on success path only."""

    @pytest.mark.asyncio
    @patch("integrations.flightlogic.get_flights_client")
    @patch(
        "app.domains.hotel.service.HotelEventHandler.handle_booking_confirmed",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.hotel.service.ensure_saved_itinerary_owned_by_user",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.BookingService.update_booking_dates_and_flags",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.BookingService.update_hotel_reference_number",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.BookingService.update_external_reference",
        new_callable=AsyncMock,
    )
    async def test_success_passes_validated_oid_to_update_dates(
        self,
        mock_update_ext,
        mock_update_hotel_ref,
        mock_update_dates,
        mock_ensure_owned,
        mock_email,
        mock_get_client,
        hotel_user: UserPublic,
    ):
        itinerary_oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret
        mock_ensure_owned.return_value = itinerary_oid

        mock_client = Mock()
        mock_client.environment = Mock(value="test")
        mock_client.book_hotel = AsyncMock(
            return_value=HotelBookingResponse(
                status="Success",
                supplier_confirmation_num="SUP-CONF-1",
                reference_num="REF-NUM-1",
                booking_details={"total_price": 100.0},
            )
        )
        mock_get_client.return_value = mock_client

        req = _minimal_hotel_book_request(
            saved_itinerary_id=str(itinerary_oid),
        )
        svc = HotelService(current_user=hotel_user)
        await svc.create_booking(req)

        mock_ensure_owned.assert_called_once_with(
            str(hotel_user.id), str(itinerary_oid)
        )
        mock_update_dates.assert_called_once()
        kwargs = mock_update_dates.call_args[1]
        assert kwargs.get("saved_itinerary_id") == itinerary_oid

    @pytest.mark.asyncio
    @patch("integrations.flightlogic.get_flights_client")
    @patch(
        "app.domains.hotel.service.HotelEventHandler.handle_booking_failed",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.hotel.service.ensure_saved_itinerary_owned_by_user",
        new_callable=AsyncMock,
    )
    @patch(
        "app.domains.bookings.BookingService.update_booking_dates_and_flags",
        new_callable=AsyncMock,
    )
    async def test_failed_booking_does_not_call_update_dates_with_link(
        self,
        mock_update_dates,
        mock_ensure_owned,
        mock_failed_email,
        mock_get_client,
        hotel_user: UserPublic,
    ):
        itinerary_oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret
        mock_ensure_owned.return_value = itinerary_oid

        mock_client = Mock()
        mock_client.environment = Mock(value="test")
        mock_client.book_hotel = AsyncMock(
            return_value=HotelBookingResponse(
                status="Failed",
                errors={"message": "no rooms"},
            )
        )
        mock_get_client.return_value = mock_client

        req = _minimal_hotel_book_request(
            saved_itinerary_id=str(itinerary_oid),
        )
        svc = HotelService(current_user=hotel_user)

        with pytest.raises(Exception) as exc:
            await svc.create_booking(req)
        assert exc.value.__class__.__name__ == "HotelBookingError"

        mock_update_dates.assert_not_called()


class TestUpdateBookingDatesAndFlagsHotelSavedItinerary:
    """BookingService.update_booking_dates_and_flags persists saved_itinerary_id."""

    @pytest.mark.asyncio
    @patch("app.domains.bookings.service.get_database")
    async def test_includes_saved_itinerary_in_set(self, mock_get_database):
        mock_collection = Mock()
        mock_collection.find_one = AsyncMock(
            return_value={
                "_id": ObjectId("507f1f77bcf86cd799439011")
            }  # pragma: allowlist secret
        )
        mock_collection.update_one = AsyncMock(
            return_value=Mock(modified_count=1, matched_count=1)
        )
        mock_get_database.return_value = {"booking_events": mock_collection}
        oid = ObjectId("507f1f77bcf86cd799439022")  # pragma: allowlist secret

        from app.domains.bookings import BookingService

        await BookingService.update_booking_dates_and_flags(
            "VOYA-H-1",
            date_booked=None,
            saved_itinerary_id=oid,
        )

        filt, update_op = mock_collection.update_one.call_args[0]
        assert "_id" in filt
        assert update_op["$set"]["saved_itinerary_id"] == oid
