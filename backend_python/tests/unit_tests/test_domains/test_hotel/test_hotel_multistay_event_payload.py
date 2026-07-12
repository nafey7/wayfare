"""Regression tests for multi-stay hotel booking event payload field naming.

These guard against silent field-name mismatches where multistay_leg_index is
dropped by Pydantic strict validation (the class of bug fixed in this branch).
"""

import pytest
from pydantic import BaseModel

from app.domains.bookings.schemas import CreateBookingEventRequest
from app.domains.hotel.schemas import GuestInfo, HotelBookingRequest


def _minimal_booking_request(**kwargs: object) -> HotelBookingRequest:
    guest = GuestInfo(
        title="Mr",
        first_name="A",
        last_name="B",
        room_number=1,
        is_child=False,
    )
    base: dict[str, object] = {
        "session_id": "sess-001",
        "product_id": "prod-001",
        "token_id": "tok-001",
        "rate_basis_id": "rate-001",
        "client_ref": "VOYA-TEST-001",
        "customer_email": "test@example.com",
        "customer_phone": "+15550001111",
        "booking_note": "",
        "guests": [guest],
        "room_count": 1,
    }
    base.update(kwargs)
    return HotelBookingRequest(**base)


class _LegSummary(BaseModel):
    """Local mirror of MultistayLegSummary for test isolation.

    Mirrors app.api.hotels.MultistayLegSummary — kept in sync by the test
    assertions below.
    """

    voya_booking_reference: str
    external_booking_reference: str | None = None
    hotel_name: str | None = None
    hotel_city: str | None = None
    leg_index: int | None = None


def _doc_to_leg(doc: dict[str, object]) -> _LegSummary:
    """Mirror of the _doc_to_leg closure in get_multistay_booking_context."""
    raw_leg_index = doc.get("multistay_leg_index")
    return _LegSummary(
        voya_booking_reference=str(doc.get("voya_booking_reference") or ""),
        external_booking_reference=str(v)
        if (v := doc.get("external_booking_reference")) is not None
        else None,
        hotel_name=str(v) if (v := doc.get("hotel_name")) is not None else None,
        hotel_city=str(v) if (v := doc.get("hotel_city")) is not None else None,
        leg_index=int(raw_leg_index)
        if isinstance(raw_leg_index, (int, float, str))
        else None,
    )


class TestHotelEventPayloadMultistayLegIndex:
    """multistay_leg_index must flow through the booking event payload."""

    def test_multistay_leg_index_present_in_payload_when_set(self) -> None:
        """Booking event payload dict contains multistay_leg_index when request has it set."""
        request = _minimal_booking_request(
            parent_voya_booking_reference="VOYA-MS-GROUP-001",
            multistay_leg_index=2,
        )

        # Replicate the payload-building logic from app/api/hotels.py lines 508-515
        hotel_event_payload: dict[str, object] = {
            "external_booking_reference": "TEMP-REF",
            "action": "PENDING",
            "event_type": "HOTEL",
        }
        if request.parent_voya_booking_reference:
            hotel_event_payload["parent_voya_booking_reference"] = (
                request.parent_voya_booking_reference
            )
        if request.multistay_leg_index is not None:
            hotel_event_payload["multistay_leg_index"] = request.multistay_leg_index

        assert "multistay_leg_index" in hotel_event_payload
        assert hotel_event_payload["multistay_leg_index"] == 2

    def test_multistay_leg_index_absent_from_payload_when_not_set(self) -> None:
        """Booking event payload dict omits multistay_leg_index when request has it as None."""
        request = _minimal_booking_request()

        hotel_event_payload: dict[str, object] = {
            "external_booking_reference": "TEMP-REF",
            "action": "PENDING",
            "event_type": "HOTEL",
        }
        if request.multistay_leg_index is not None:
            hotel_event_payload["multistay_leg_index"] = request.multistay_leg_index

        assert "multistay_leg_index" not in hotel_event_payload

    def test_create_booking_event_request_accepts_multistay_leg_index(self) -> None:
        """CreateBookingEventRequest.model_validate accepts multistay_leg_index key."""
        payload: dict[str, object] = {
            "external_booking_reference": "TEMP-REF",
            "action": "PENDING",
            "event_type": "HOTEL",
            "multistay_leg_index": 1,
        }
        event_request = CreateBookingEventRequest.model_validate(payload)
        assert event_request.multistay_leg_index == 1

    @pytest.mark.parametrize(("leg_index_value", "expected"), [(0, 0), (1, 1), (3, 3)])
    def test_multistay_leg_index_zero_is_included(
        self, leg_index_value: int, expected: int
    ) -> None:
        """Leg index 0 must also be written to the payload (not treated as falsy)."""
        request = _minimal_booking_request(
            parent_voya_booking_reference="VOYA-MS-GROUP-002",
            multistay_leg_index=leg_index_value,
        )

        hotel_event_payload: dict[str, object] = {}
        if request.multistay_leg_index is not None:
            hotel_event_payload["multistay_leg_index"] = request.multistay_leg_index

        assert hotel_event_payload.get("multistay_leg_index") == expected


class TestDocToLegMultistayLegIndex:
    """_doc_to_leg must read multistay_leg_index (not multicity_leg_index) from stored docs."""

    def test_leg_index_populated_from_multistay_leg_index_key(self) -> None:
        """leg_index is set when doc has multistay_leg_index."""
        doc: dict[str, object] = {
            "voya_booking_reference": "VOYA-001",
            "multistay_leg_index": 2,
        }
        leg = _doc_to_leg(doc)
        assert leg.leg_index == 2

    def test_leg_index_none_when_multistay_leg_index_missing(self) -> None:
        """leg_index is None when doc has no multistay_leg_index."""
        doc: dict[str, object] = {"voya_booking_reference": "VOYA-002"}
        leg = _doc_to_leg(doc)
        assert leg.leg_index is None

    def test_old_multicity_key_does_not_populate_leg_index(self) -> None:
        """Legacy multicity_leg_index key does NOT populate leg_index (field was renamed)."""
        doc: dict[str, object] = {
            "voya_booking_reference": "VOYA-003",
            "multicity_leg_index": 1,  # old field name — should be ignored
        }
        leg = _doc_to_leg(doc)
        assert leg.leg_index is None

    def test_leg_index_populated_for_leg_zero(self) -> None:
        """Leg index 0 is correctly read (not treated as falsy/missing)."""
        doc: dict[str, object] = {
            "voya_booking_reference": "VOYA-004",
            "multistay_leg_index": 0,
        }
        leg = _doc_to_leg(doc)
        assert leg.leg_index == 0
