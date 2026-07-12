"""Tests for GET /flights/my-bookings mapping (booking_events → FlightMyBookingListItem)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.bookings.service import booking_document_to_response
from app.domains.common.enums import AuthProvider
from app.domains.flight.service import FlightService
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

_TS = datetime(2026, 8, 1, 14, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="u@example.com",
        first_name="U",
        last_name="Ser",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=_TS,
        updated_at=_TS,
    )


def test_booking_document_to_response_maps_my_bookings_fields() -> None:
    oid = ObjectId()
    uid = ObjectId()
    doc = {
        "_id": oid,
        "user_id": uid,
        "voya_booking_reference": "VOYA-F1",
        "external_booking_reference": "EXT",
        "action": "BOOKED",
        "timestamp": _TS,
        "event_type": "FLIGHT",
        "departure_airport_iata": "JFK",
        "amount": 199.5,
        "ticket_status": "Ticketed",
    }
    item = booking_document_to_response(doc)
    assert item.voya_booking_reference == "VOYA-F1"
    assert item.action == "BOOKED"
    assert item.departure_airport_iata == "JFK"
    assert item.amount == 199.5
    assert item.ticket_status == "Ticketed"


@pytest.mark.asyncio
@patch("app.domains.flight.service.get_database")
async def test_get_user_bookings_queries_unified_user_id_and_maps(
    mock_get_database, sample_user: UserPublic
) -> None:
    mock_coll = Mock()
    mock_cursor = Mock()
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_cursor.sort = Mock(return_value=mock_cursor)
    mock_cursor.limit = Mock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "_id": ObjectId(),
                "user_id": ObjectId(sample_user.id),
                "voya_booking_reference": "VOYA-X",
                "external_booking_reference": "E1",
                "action": "BOOKED",
                "timestamp": _TS,
                "event_type": "FLIGHT",
                "departure_airport_iata": "JFK",
                "flight_trip_type": "round_trip",
                "primary_marketing_airline_name": "Ocean Air",
                "route_legs": [
                    {
                        "leg_index": 0,
                        "departure_iata": "JFK",
                        "arrival_iata": "LHR",
                        "segment_count": 1,
                        "segments": [
                            {"departure_iata": "JFK", "arrival_iata": "LHR"},
                        ],
                    },
                    {
                        "leg_index": 1,
                        "departure_iata": "LHR",
                        "arrival_iata": "JFK",
                        "segment_count": 1,
                        "segments": [
                            {"departure_iata": "LHR", "arrival_iata": "JFK"},
                        ],
                    },
                ],
            }
        ]
    )
    mock_db = {"booking_events": mock_coll}
    mock_get_database.return_value = mock_db

    service = FlightService(current_user=sample_user)
    out = await service.get_user_bookings(limit=5)

    assert len(out) == 1
    assert out[0].voya_booking_reference == "VOYA-X"
    assert out[0].departure_airport_iata == "JFK"
    assert out[0].flight_trip_type == "round_trip"
    assert out[0].primary_marketing_airline_name == "Ocean Air"
    assert out[0].route_legs is not None
    assert len(out[0].route_legs) == 2
    assert out[0].route_legs[0].departure_iata == "JFK"
    assert out[0].route_legs[0].arrival_iata == "LHR"
    mock_coll.find.assert_called_once()
    call_query = mock_coll.find.call_args[0][0]
    assert call_query["event_type"] == "FLIGHT"
    assert call_query["user_id"] == {"$in": [ObjectId(sample_user.id), sample_user.id]}


@pytest.mark.asyncio
@patch("app.domains.flight.service.get_database")
async def test_get_user_bookings_skips_malformed_row(
    mock_get_database, sample_user: UserPublic
) -> None:
    """Malformed Mongo rows are skipped so one bad document does not break the list."""
    good_id = ObjectId()
    bad_id = ObjectId()
    mock_coll = Mock()
    mock_cursor = Mock()
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_cursor.sort = Mock(return_value=mock_cursor)
    mock_cursor.limit = Mock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "_id": good_id,
                "user_id": ObjectId(sample_user.id),
                "voya_booking_reference": "VOYA-OK",
                "external_booking_reference": "E0",
                "action": "BOOKED",
                "timestamp": _TS,
                "event_type": "FLIGHT",
            },
            {
                "_id": bad_id,
                "user_id": ObjectId(sample_user.id),
                "voya_booking_reference": "VOYA-BAD",
                "external_booking_reference": "E1",
                "action": "BOOKED",
                # missing timestamp — booking_document_to_response raises
                "event_type": "FLIGHT",
            },
        ]
    )
    mock_db = {"booking_events": mock_coll}
    mock_get_database.return_value = mock_db

    service = FlightService(current_user=sample_user)
    out = await service.get_user_bookings(limit=10)

    assert len(out) == 1
    assert out[0].voya_booking_reference == "VOYA-OK"
