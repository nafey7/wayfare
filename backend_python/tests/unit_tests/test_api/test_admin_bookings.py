"""Unit tests for admin booking API endpoints (GET list, GET by-reference, POST retry)."""

import sys
from contextlib import suppress
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Stub sentry_sdk so app.domains.auth.dependencies can load (not in all Docker images)
if "sentry_sdk" not in sys.modules:
    sys.modules["sentry_sdk"] = MagicMock()

from bson import ObjectId
from fastapi import HTTPException, status

from app.database.models.booking_event import BookingEventModel
from app.domains.bookings.schemas import BookingEventResponse
from app.domains.common.enums import AuthProvider
from app.domains.flight.enums import TicketStatus
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

# Ensure patch target exists for get_flights_client (used in retry tests)
with suppress(ImportError):
    import integrations.flightlogic  # noqa: F401

# ==============================================================================
# FIXTURES
# ==============================================================================

# Use future dates in tests (e.g. 2026)
_FUTURE_TS = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_admin() -> UserPublic:
    """Mock admin user for testing."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=_FUTURE_TS,
        updated_at=_FUTURE_TS,
    )


@pytest.fixture
def mock_booking_event_response() -> BookingEventResponse:
    """Minimal booking event response for list endpoint."""
    return BookingEventResponse(
        id="507f1f77bcf86cd799439020",  # pragma: allowlist secret
        user_id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        voya_booking_reference="VOYA-TEST001",
        external_booking_reference="EXT001",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
    )


@pytest.fixture
def mock_booking_event_model() -> BookingEventModel:
    """Booking event model for by-reference and retry (includes payload)."""
    return BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-TEST002",
        external_booking_reference="EXT002",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
        carrier_type="LCC",
        payload={"sessionId": "sess-123", "fareSourceCode": "FSC"},
    )


@pytest.fixture
def mock_user_public() -> UserPublic:
    """User for user_display_name in list response."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=_FUTURE_TS,
        updated_at=_FUTURE_TS,
    )


# ==============================================================================
# GET /admin/bookings
# ==============================================================================


@pytest.mark.asyncio
async def test_get_all_bookings_success(
    mock_admin: UserPublic,
    mock_booking_event_response: BookingEventResponse,
    mock_user_public: UserPublic,
) -> None:
    """GET /admin/bookings returns events with user_display_name and pagination."""
    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "app.domains.user.repository.get_users_by_ids",
            new_callable=AsyncMock,
        ) as mock_get_users,
    ):
        mock_svc_cls.list_all_events = AsyncMock(
            return_value=([mock_booking_event_response], 1)
        )
        mock_get_users.return_value = [mock_user_public]

        from app.api.admin import get_all_bookings

        result = await get_all_bookings(limit=50, offset=0, _admin=mock_admin)

        assert result["total"] == 1
        assert result["limit"] == 50
        assert result["offset"] == 0
        assert len(result["events"]) == 1
        assert result["events"][0]["user_display_name"] == "user@example.com"
        assert result["events"][0]["voya_booking_reference"] == "VOYA-TEST001"
        mock_svc_cls.list_all_events.assert_called_once_with(limit=50, offset=0)
        mock_get_users.assert_called_once_with(
            ["507f1f77bcf86cd799439011"]  # pragma: allowlist secret
        )


@pytest.mark.asyncio
async def test_get_all_bookings_unknown_user_display_name(
    mock_admin: UserPublic,
    mock_booking_event_response: BookingEventResponse,
) -> None:
    """GET /admin/bookings uses 'Unknown' when user not in get_users_by_ids."""
    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "app.domains.user.repository.get_users_by_ids",
            new_callable=AsyncMock,
        ) as mock_get_users,
    ):
        mock_svc_cls.list_all_events = AsyncMock(
            return_value=([mock_booking_event_response], 1)
        )
        mock_get_users.return_value = []  # no user found

        from app.api.admin import get_all_bookings

        result = await get_all_bookings(limit=10, offset=0, _admin=mock_admin)

        assert result["events"][0]["user_display_name"] == "Unknown"


# ==============================================================================
# GET /admin/bookings/by-reference/{voya_booking_reference}
# ==============================================================================


@pytest.mark.asyncio
async def test_get_booking_event_by_reference_success(
    mock_admin: UserPublic,
    mock_booking_event_model: BookingEventModel,
) -> None:
    """GET by-reference returns event dict when found."""
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_voya_reference = AsyncMock(
            return_value=mock_booking_event_model
        )

        from app.api.admin import get_booking_event_by_reference

        result = await get_booking_event_by_reference("VOYA-TEST002", _admin=mock_admin)

        assert result["voya_booking_reference"] == "VOYA-TEST002"
        assert result["event_type"] == "FLIGHT"
        mock_svc_cls.get_event_by_voya_reference.assert_called_once_with("VOYA-TEST002")


@pytest.mark.asyncio
async def test_get_booking_event_by_reference_not_found(
    mock_admin: UserPublic,
) -> None:
    """GET by-reference returns 404 when booking not found."""
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_voya_reference = AsyncMock(return_value=None)

        from app.api.admin import get_booking_event_by_reference

        with pytest.raises(HTTPException) as exc_info:
            await get_booking_event_by_reference("VOYA-MISSING", _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Booking not found" in str(exc_info.value.detail)


# ==============================================================================
# POST /admin/bookings/retry
# ==============================================================================


@pytest.mark.asyncio
async def test_admin_retry_booking_event_not_found(
    mock_admin: UserPublic,
) -> None:
    """POST retry returns 404 when booking event not found."""
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=None)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id="507f1f77bcf86cd799439099")

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Booking event not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_admin_retry_booking_action_not_booked(
    mock_admin: UserPublic,
) -> None:
    """POST retry returns 400 when event action is not BOOKED."""
    cancelled_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-CANC",
        external_booking_reference="EXT-CANC",
        action="CANCELLED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
    )
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=cancelled_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(cancelled_event.id))

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "only supported for BOOKED" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_admin_retry_booking_hotel_missing_payload(
    mock_admin: UserPublic,
) -> None:
    """POST retry returns 400 for HOTEL when payload is missing."""
    hotel_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-HOTEL",
        external_booking_reference="EXT-HOTEL",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="HOTEL",
        payload=None,  # missing
    )
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=hotel_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(hotel_event.id))

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Hotel retry requires stored payload" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_admin_retry_booking_lcc_missing_payload(
    mock_admin: UserPublic,
) -> None:
    """POST retry returns 400 for FLIGHT LCC when payload is missing."""
    lcc_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-LCC",
        external_booking_reference="EXT-LCC",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
        carrier_type="LCC",
        payload=None,  # missing
    )
    with patch(
        "app.domains.bookings.service.BookingService",
    ) as mock_svc_cls:
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=lcc_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(lcc_event.id))

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "LCC retry requires stored payload" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_admin_retry_booking_gds_missing_external_reference(
    mock_admin: UserPublic,
) -> None:
    """POST retry returns 400 for FLIGHT GDS when external_booking_reference missing."""
    gds_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-GDS",
        external_booking_reference="",  # missing
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
        carrier_type="GDS",
    )
    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "integrations.flightlogic.get_flights_client",
            return_value=Mock(),  # not called for this error path
        ),
    ):
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=gds_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(gds_event.id))

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "GDS retry requires external_booking_reference" in str(
            exc_info.value.detail
        )


@pytest.mark.asyncio
async def test_admin_retry_booking_hotel_success(
    mock_admin: UserPublic,
) -> None:
    """POST retry HOTEL succeeds and returns success with references."""
    hotel_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-HOTEL2",
        external_booking_reference="EXT-HOTEL2",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="HOTEL",
        payload={"hotel": "book-payload"},
    )
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status = "Success"
    mock_response.supplier_confirmation_num = "SUPPLIER-123"
    mock_response.reference_num = "REF456"
    mock_response.errors = None
    mock_client.book_hotel_with_payload = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "integrations.flightlogic.get_flights_client",
            return_value=mock_client,
        ),
    ):
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=hotel_event)
        mock_svc_cls.update_external_reference = AsyncMock()
        mock_svc_cls.update_hotel_reference_number = AsyncMock()
        mock_response.booking_details = {}

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(hotel_event.id))

        with patch(
            "app.domains.hotel.events.HotelEventHandler.handle_booking_confirmed",
            new_callable=AsyncMock,
        ):
            result = await admin_retry_booking(body=body, _admin=mock_admin)

        assert result["success"] is True
        assert result["voya_booking_reference"] == "VOYA-HOTEL2"
        assert result["external_booking_reference"] == "SUPPLIER-123"
        mock_client.book_hotel_with_payload.assert_called_once_with(
            {"hotel": "book-payload"}
        )


@pytest.mark.asyncio
async def test_admin_retry_booking_flight_lcc_success(
    mock_admin: UserPublic,
    mock_booking_event_model: BookingEventModel,
) -> None:
    """POST retry FLIGHT LCC succeeds and returns success."""
    mock_client = Mock()
    mock_booking_response = Mock()
    mock_booking_response.is_successful = True
    mock_booking_response.external_booking_reference = "EXT-NEW"
    mock_booking_response.airline_pnr = None
    mock_booking_response.ticket_time_limit = None
    mock_booking_response.errors = None
    mock_client.create_booking_with_payload = AsyncMock(
        return_value=mock_booking_response
    )
    mock_client.get_trip_details = AsyncMock(return_value=None)

    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "integrations.flightlogic.get_flights_client",
            return_value=mock_client,
        ),
    ):
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=mock_booking_event_model)
        mock_svc_cls.update_booking_after_flight_confirmation = AsyncMock()

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(
            booking_event_id=str(mock_booking_event_model.id)
        )

        with patch(
            "app.domains.flight.events.FlightEventHandler.handle_booking_confirmed",
            new_callable=AsyncMock,
        ):
            result = await admin_retry_booking(body=body, _admin=mock_admin)

        assert result["success"] is True
        assert result["voya_booking_reference"] == "VOYA-TEST002"
        assert result["external_booking_reference"] == "EXT-NEW"
        mock_client.create_booking_with_payload.assert_called_once_with(
            mock_booking_event_model.payload
        )


@pytest.mark.asyncio
async def test_admin_retry_booking_gds_skips_when_ticketed(
    mock_admin: UserPublic,
) -> None:
    """POST retry FLIGHT GDS skips ticket order when booking is already ticketed."""
    from app.domains.flight.schemas import TripDetailsResponse

    gds_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-GDS-TKT",
        external_booking_reference="EXT-GDS-123",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
        carrier_type="GDS",
    )
    mock_trip_details = Mock(spec=TripDetailsResponse)
    mock_trip_details.ticket_status = TicketStatus.TICKETED

    mock_client = Mock()
    mock_client.get_trip_details = AsyncMock(return_value=mock_trip_details)
    mock_client.issue_tickets = AsyncMock()  # Should NOT be called

    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "integrations.flightlogic.get_flights_client",
            return_value=mock_client,
        ),
    ):
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=gds_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(gds_event.id))

        result = await admin_retry_booking(body=body, _admin=mock_admin)

        assert result["success"] is True
        assert result["voya_booking_reference"] == "VOYA-GDS-TKT"
        assert result["external_booking_reference"] == "EXT-GDS-123"
        mock_client.get_trip_details.assert_called_once()
        mock_client.issue_tickets.assert_not_called()


@pytest.mark.asyncio
async def test_admin_retry_booking_gds_trip_details_failure_raises_502(
    mock_admin: UserPublic,
) -> None:
    """POST retry FLIGHT GDS returns 502 when trip details fails before ticket order."""
    gds_event = BookingEventModel(
        id=ObjectId(),
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        voya_booking_reference="VOYA-GDS-FAIL",
        external_booking_reference="EXT-GDS-123",
        action="BOOKED",
        timestamp=_FUTURE_TS,
        event_type="FLIGHT",
        carrier_type="GDS",
    )
    mock_client = Mock()
    mock_client.get_trip_details = AsyncMock(side_effect=RuntimeError("upstream down"))

    with (
        patch(
            "app.domains.bookings.service.BookingService",
        ) as mock_svc_cls,
        patch(
            "integrations.flightlogic.get_flights_client",
            return_value=mock_client,
        ),
    ):
        mock_svc_cls.get_event_by_id = AsyncMock(return_value=gds_event)

        from app.api.admin import AdminBookingRetryRequest, admin_retry_booking

        body = AdminBookingRetryRequest(booking_event_id=str(gds_event.id))

        with pytest.raises(HTTPException) as exc_info:
            await admin_retry_booking(body=body, _admin=mock_admin)

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Trip details failed" in (exc_info.value.detail or "")
        mock_client.issue_tickets.assert_not_called()
