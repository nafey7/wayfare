"""GDS Pay Now: client_reference must resolve to a PENDING event owned by the caller."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.database.models.booking_event import BookingEventModel
from app.domains.bookings.constants import TEMP_EXTERNAL_REF
from app.domains.bookings.exceptions import (
    BookingForbiddenError,
    GdsClientReferenceConflictError,
    GdsPendingBookingSyncError,
)
from app.domains.common import AuthProvider
from app.domains.flight.enums import FareType
from app.domains.flight.exceptions import FlightBookingSupplierSyncError
from app.domains.flight.schemas import (
    AdultPassenger,
    ContactInformation,
    FlightBookingRequest,
    PassengerGroups,
)
from app.domains.flight.service import FlightService
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


def _adult_passenger() -> AdultPassenger:
    dob = (datetime.now() - timedelta(days=int(365.25 * 25))).strftime("%Y-%m-%d")
    return AdultPassenger(
        personal_info={
            "name": {"first_name": "John", "last_name": "Doe"},
            "date_of_birth": dob,
        }
    )


def _gds_booking_request(client_reference: str) -> FlightBookingRequest:
    return FlightBookingRequest(
        session_id="sess-1",
        fare_source_code="fare-src-1",
        requires_passport=False,
        fare_type=FareType.PUBLIC,
        client_reference=client_reference,
        contact_information=ContactInformation(email="booker@example.com"),
        passenger_groups=PassengerGroups(adults=[_adult_passenger()]),
    )


def _user(user_id: str) -> UserPublic:
    now = datetime.now(UTC)
    return UserPublic(
        id=user_id,
        email="booker@example.com",
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_booking_forbids_client_reference_when_pending_event_owned_by_other() -> (
    None
):
    """IDOR: another user's VOYA-* PENDING reference must not be attachable to this booking."""
    attacker_id = str(ObjectId())
    victim_id = ObjectId()
    voya_ref = "VOYA-PENDING-VICTIM-1"

    pending_event = BookingEventModel(
        user_id=victim_id,
        voya_booking_reference=voya_ref,
        external_booking_reference=TEMP_EXTERNAL_REF,
        action="PENDING",
        timestamp=datetime.now(UTC),
        event_type="FLIGHT",
    )

    service = FlightService(current_user=_user(attacker_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock()
    service.client = mock_client

    with patch(
        "app.domains.flight.service.BookingService.get_event_by_voya_reference",
        new_callable=AsyncMock,
        return_value=pending_event,
    ):
        req = _gds_booking_request(voya_ref)
        with pytest.raises(BookingForbiddenError):
            await service.create_booking(req)

    mock_client.create_booking.assert_not_called()


@pytest.mark.asyncio
async def test_create_booking_conflict_when_event_booked_same_user() -> None:
    """VOYA-* that is already BOOKED must not call FlightLogic (stale UI / duplicate risk)."""
    user_id = str(ObjectId())
    voya_ref = "VOYA-ALREADY-BOOKED-1"

    booked_event = BookingEventModel(
        user_id=ObjectId(user_id),
        voya_booking_reference=voya_ref,
        external_booking_reference="FL-EXT-999",
        action="BOOKED",
        timestamp=datetime.now(UTC),
        event_type="FLIGHT",
    )

    service = FlightService(current_user=_user(user_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock()
    service.client = mock_client

    with patch(
        "app.domains.flight.service.BookingService.get_event_by_voya_reference",
        new_callable=AsyncMock,
        return_value=booked_event,
    ):
        req = _gds_booking_request(voya_ref)
        with pytest.raises(GdsClientReferenceConflictError):
            await service.create_booking(req)

    mock_client.create_booking.assert_not_called()


@pytest.mark.asyncio
async def test_create_booking_conflict_when_pending_but_not_temp_ref() -> None:
    """PENDING row must still use TEMP-REF until Booking API succeeds."""
    user_id = str(ObjectId())
    voya_ref = "VOYA-PENDING-WEIRD-REF"

    weird = BookingEventModel(
        user_id=ObjectId(user_id),
        voya_booking_reference=voya_ref,
        external_booking_reference="NOT-TEMP",
        action="PENDING",
        timestamp=datetime.now(UTC),
        event_type="FLIGHT",
    )

    service = FlightService(current_user=_user(user_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock()
    service.client = mock_client

    with patch(
        "app.domains.flight.service.BookingService.get_event_by_voya_reference",
        new_callable=AsyncMock,
        return_value=weird,
    ):
        req = _gds_booking_request(voya_ref)
        with pytest.raises(GdsClientReferenceConflictError):
            await service.create_booking(req)

    mock_client.create_booking.assert_not_called()


@pytest.mark.asyncio
async def test_create_booking_forbids_client_reference_when_booked_event_owned_by_other() -> (
    None
):
    """IDOR: another user's completed VOYA ref must not reach FlightLogic."""
    attacker_id = str(ObjectId())
    victim_id = ObjectId()
    voya_ref = "VOYA-VICTIM-BOOKED"

    booked_event = BookingEventModel(
        user_id=victim_id,
        voya_booking_reference=voya_ref,
        external_booking_reference="FL-EXT-1",
        action="BOOKED",
        timestamp=datetime.now(UTC),
        event_type="FLIGHT",
    )

    service = FlightService(current_user=_user(attacker_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock()
    service.client = mock_client

    with patch(
        "app.domains.flight.service.BookingService.get_event_by_voya_reference",
        new_callable=AsyncMock,
        return_value=booked_event,
    ):
        req = _gds_booking_request(voya_ref)
        with pytest.raises(BookingForbiddenError):
            await service.create_booking(req)

    mock_client.create_booking.assert_not_called()


@pytest.mark.asyncio
async def test_create_booking_calls_flightlogic_when_voya_ref_has_no_event() -> None:
    """No Mongo row: legacy / unknown refs still reach FlightLogic (logged elsewhere)."""
    user_id = str(ObjectId())
    voya_ref = "VOYA-ORPHAN-REF"

    fail_resp = MagicMock()
    fail_resp.is_successful = False
    fail_resp.errors = [MagicMock(message="supplier error")]

    service = FlightService(current_user=_user(user_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock(return_value=fail_resp)
    service.client = mock_client

    with patch(
        "app.domains.flight.service.BookingService.get_event_by_voya_reference",
        new_callable=AsyncMock,
        return_value=None,
    ):
        req = _gds_booking_request(voya_ref)
        await service.create_booking(req)

    mock_client.create_booking.assert_called_once()


@pytest.mark.asyncio
async def test_create_booking_raises_supplier_sync_error_when_pending_update_fails() -> (
    None
):
    """GDS path: supplier booking OK but Mongo PENDING row update fails → non-retryable domain error."""
    user_id = str(ObjectId())
    voya_ref = "VOYA-GDS-PENDING-SYNC-1"

    pending_event = BookingEventModel(
        user_id=ObjectId(user_id),
        voya_booking_reference=voya_ref,
        external_booking_reference=TEMP_EXTERNAL_REF,
        action="PENDING",
        timestamp=datetime.now(UTC),
        event_type="FLIGHT",
    )

    ok_resp = MagicMock()
    ok_resp.is_successful = True
    ok_resp.external_booking_reference = "FL-SUPPLIER-REF-1"
    ok_resp.booking_status = MagicMock()
    ok_resp.booking_status.value = "CONFIRMED"
    ok_resp.airline_pnr = None
    ok_resp.ticket_time_limit = None
    ok_resp.environment = MagicMock()
    ok_resp.errors = []
    ok_resp.model_dump = MagicMock(return_value={})

    service = FlightService(current_user=_user(user_id))
    mock_client = AsyncMock()
    mock_client.create_booking = AsyncMock(return_value=ok_resp)
    mock_client.adapter = MagicMock()
    mock_client.adapter.booking_request_to_dto = MagicMock(
        side_effect=RuntimeError("skip dto in test")
    )
    service.client = mock_client

    with (
        patch(
            "app.domains.flight.service.BookingService.get_event_by_voya_reference",
            new_callable=AsyncMock,
            return_value=pending_event,
        ),
        patch(
            "app.domains.flight.service.BookingService.update_gds_pending_booking_after_api",
            new_callable=AsyncMock,
            side_effect=GdsPendingBookingSyncError("could not update"),
        ),
        patch(
            "app.domains.flight.service.FlightEventHandler.handle_booking_confirmed",
            new_callable=AsyncMock,
        ),
    ):
        req = _gds_booking_request(voya_ref)
        with pytest.raises(FlightBookingSupplierSyncError) as exc:
            await service.create_booking(req)
        assert "could not update" in str(exc.value).lower()

    mock_client.create_booking.assert_called_once()
