"""linked_bookings aggregation from booking_events."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.database.constants import BOOKING_EVENT_COLLECTION
from app.database.flight_route import RouteLeg, RouteSegment
from app.domains.saved_itinerary.repository import (
    _booking_doc_to_summary,
    fetch_linked_bookings_for_itinerary_ids,
)
from app.domains.saved_itinerary.schemas import (
    LinkedBookingEventSummary,
    LinkedBookings,
)

USER_ID = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
ITIN_A = "507f1f77bcf86cd7994390aa"  # pragma: allowlist secret
ITIN_B = "507f1f77bcf86cd7994390bb"  # pragma: allowlist secret


def test_booking_doc_to_summary_maps_route_and_marketing_airline() -> None:
    ts = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
    doc = {
        "voya_booking_reference": "VOYA-RT-1",
        "event_type": "FLIGHT",
        "timestamp": ts,
        "departure_airport_iata": "JFK",
        "flight_trip_type": "round_trip",
        "route_legs": [
            {
                "leg_index": 0,
                "departure_iata": "JFK",
                "arrival_iata": "LHR",
                "segment_count": 1,
                "segments": [{"departure_iata": "JFK", "arrival_iata": "LHR"}],
            },
            {
                "leg_index": 1,
                "departure_iata": "LHR",
                "arrival_iata": "JFK",
                "segment_count": 1,
                "segments": [{"departure_iata": "LHR", "arrival_iata": "JFK"}],
            },
        ],
        "primary_marketing_airline_name": "British Airways",
        "airline_pnr_airline_name": "American Airlines",
    }
    summary = _booking_doc_to_summary(doc)
    assert summary is not None
    assert summary.voya_booking_reference == "VOYA-RT-1"
    assert summary.departure_airport_iata == "JFK"
    assert summary.flight_trip_type == "round_trip"
    assert summary.route_legs == [
        RouteLeg(
            leg_index=0,
            departure_iata="JFK",
            arrival_iata="LHR",
            segment_count=1,
            segments=[RouteSegment(departure_iata="JFK", arrival_iata="LHR")],
        ),
        RouteLeg(
            leg_index=1,
            departure_iata="LHR",
            arrival_iata="JFK",
            segment_count=1,
            segments=[RouteSegment(departure_iata="LHR", arrival_iata="JFK")],
        ),
    ]
    assert summary.primary_marketing_airline_name == "British Airways"
    assert summary.airline_pnr_airline_name == "American Airlines"


@pytest.mark.asyncio
async def test_fetch_groups_flight_and_hotel_by_itinerary() -> None:
    oid_a = ObjectId(ITIN_A)
    oid_b = ObjectId(ITIN_B)
    ts = datetime.now(UTC)
    docs = [
        {
            "_id": ObjectId(),
            "user_id": ObjectId(USER_ID),
            "saved_itinerary_id": oid_a,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-F1",
            "timestamp": ts,
        },
        {
            "_id": ObjectId(),
            "user_id": ObjectId(USER_ID),
            "saved_itinerary_id": oid_a,
            "action": "BOOKED",
            "event_type": "HOTEL",
            "voya_booking_reference": "VOYA-H1",
            "timestamp": ts,
        },
        {
            "_id": ObjectId(),
            "user_id": ObjectId(USER_ID),
            "saved_itinerary_id": oid_b,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-F2",
            "timestamp": ts,
        },
    ]

    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_coll.find.return_value = mock_cursor

    mock_db = {BOOKING_EVENT_COLLECTION: mock_coll}

    async def fake_get_database() -> dict:
        return mock_db  # type: ignore[return-value]

    with patch(
        "app.domains.saved_itinerary.repository.get_database",
        new_callable=AsyncMock,
        side_effect=fake_get_database,
    ):
        result = await fetch_linked_bookings_for_itinerary_ids(
            USER_ID, [ITIN_A, ITIN_B]
        )

    assert result[ITIN_A] == LinkedBookings(
        flight_voya_references=["VOYA-F1"],
        hotel_voya_references=["VOYA-H1"],
        flight_events=[
            LinkedBookingEventSummary(
                voya_booking_reference="VOYA-F1",
                event_type="FLIGHT",
                timestamp=ts,
            )
        ],
        hotel_events=[
            LinkedBookingEventSummary(
                voya_booking_reference="VOYA-H1",
                event_type="HOTEL",
                timestamp=ts,
            )
        ],
    )
    assert result[ITIN_B] == LinkedBookings(
        flight_voya_references=["VOYA-F2"],
        hotel_voya_references=[],
        flight_events=[
            LinkedBookingEventSummary(
                voya_booking_reference="VOYA-F2",
                event_type="FLIGHT",
                timestamp=ts,
            )
        ],
    )


@pytest.mark.asyncio
async def test_fetch_caps_at_five_flights_per_itinerary() -> None:
    """Newest-first order; at most 5 unique flight refs per itinerary."""
    oid_a = ObjectId(ITIN_A)
    base = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    docs = []
    for i in range(6):
        docs.append(
            {
                "_id": ObjectId(),
                "user_id": ObjectId(USER_ID),
                "saved_itinerary_id": oid_a,
                "action": "BOOKED",
                "event_type": "FLIGHT",
                "voya_booking_reference": f"VOYA-F{i}",
                "timestamp": base.replace(second=i),
            }
        )
    # Real Mongo returns newest first; mock cursor does not run sort — emulate that order.
    docs_newest_first = list(reversed(docs))
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=docs_newest_first)
    mock_coll.find.return_value = mock_cursor

    async def fake_get_database() -> dict:
        return {BOOKING_EVENT_COLLECTION: mock_coll}

    with patch(
        "app.domains.saved_itinerary.repository.get_database",
        new_callable=AsyncMock,
        side_effect=fake_get_database,
    ):
        result = await fetch_linked_bookings_for_itinerary_ids(USER_ID, [ITIN_A])

    assert result[ITIN_A].flight_voya_references == [
        "VOYA-F5",
        "VOYA-F4",
        "VOYA-F3",
        "VOYA-F2",
        "VOYA-F1",
    ]
    assert len(result[ITIN_A].flight_events) == 5
    assert [e.voya_booking_reference for e in result[ITIN_A].flight_events] == [
        "VOYA-F5",
        "VOYA-F4",
        "VOYA-F3",
        "VOYA-F2",
        "VOYA-F1",
    ]


@pytest.mark.asyncio
async def test_fetch_skips_duplicate_voya_refs() -> None:
    oid_a = ObjectId(ITIN_A)
    ts = datetime.now(UTC)
    docs = [
        {
            "_id": ObjectId(),
            "user_id": ObjectId(USER_ID),
            "saved_itinerary_id": oid_a,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-DUP",
            "timestamp": ts,
        },
        {
            "_id": ObjectId(),
            "user_id": ObjectId(USER_ID),
            "saved_itinerary_id": oid_a,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-DUP",
            "timestamp": ts,
        },
    ]
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_coll.find.return_value = mock_cursor

    async def fake_get_database() -> dict:
        return {BOOKING_EVENT_COLLECTION: mock_coll}

    with patch(
        "app.domains.saved_itinerary.repository.get_database",
        new_callable=AsyncMock,
        side_effect=fake_get_database,
    ):
        result = await fetch_linked_bookings_for_itinerary_ids(USER_ID, [ITIN_A])

    assert result[ITIN_A].flight_voya_references == ["VOYA-DUP"]


@pytest.mark.asyncio
async def test_fetch_matches_booking_when_user_id_stored_as_string() -> None:
    """Legacy or exported docs may have user_id as string; still link to itinerary."""
    oid_a = ObjectId(ITIN_A)
    ts = datetime.now(UTC)
    docs = [
        {
            "_id": ObjectId(),
            "user_id": USER_ID,
            "saved_itinerary_id": oid_a,
            "action": "BOOKED",
            "event_type": "FLIGHT",
            "voya_booking_reference": "VOYA-STR-UID",
            "timestamp": ts,
        },
    ]
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_coll.find.return_value = mock_cursor

    async def fake_get_database() -> dict:
        return {BOOKING_EVENT_COLLECTION: mock_coll}

    with patch(
        "app.domains.saved_itinerary.repository.get_database",
        new_callable=AsyncMock,
        side_effect=fake_get_database,
    ):
        result = await fetch_linked_bookings_for_itinerary_ids(USER_ID, [ITIN_A])

    assert result[ITIN_A].flight_voya_references == ["VOYA-STR-UID"]


@pytest.mark.asyncio
async def test_fetch_empty_when_no_docs() -> None:
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_coll.find.return_value = mock_cursor

    async def fake_get_database() -> dict:
        return {BOOKING_EVENT_COLLECTION: mock_coll}

    with patch(
        "app.domains.saved_itinerary.repository.get_database",
        new_callable=AsyncMock,
        side_effect=fake_get_database,
    ):
        result = await fetch_linked_bookings_for_itinerary_ids(USER_ID, [ITIN_A])

    assert result[ITIN_A] == LinkedBookings()
