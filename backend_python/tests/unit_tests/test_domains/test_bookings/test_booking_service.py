"""Unit tests for BookingService."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bson import ObjectId

from app.domains.bookings import BookingService
from app.domains.bookings.constants import TEMP_EXTERNAL_REF
from app.domains.bookings.exceptions import (
    BookingForbiddenError,
    GdsPendingBookingSyncError,
    MalformedBookingEventDocumentError,
)
from app.domains.bookings.service import (
    MAX_MULTICITY_LEGS,
    booking_document_to_response,
)
from app.domains.payment.enums import PaymentStatus

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_database():
    """Mock database collection."""
    mock_collection = Mock()
    mock_collection.update_one = AsyncMock()
    mock_collection.update_many = AsyncMock()
    mock_collection.find_one = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    return {"booking_events": mock_collection}


# ==============================================================================
# UPDATE PAYMENT INTENT ID TESTS
# ==============================================================================


class TestUpdatePaymentIntentId:
    """Test BookingService.update_payment_intent_id()."""

    @patch("app.domains.bookings.service.get_database")
    async def test_update_payment_intent_id_success(
        self, mock_get_database, mock_database
    ):
        """Test successfully updating payment_intent_id."""
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database

        await BookingService.update_payment_intent_id(
            "VOYA-TEST123", "pi_test_123456789"
        )

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"voya_booking_reference": "VOYA-TEST123"}
        assert call_args[0][1] == {"$set": {"payment_intent_id": "pi_test_123456789"}}

    @patch("app.domains.bookings.service.get_database")
    async def test_update_payment_intent_id_booking_not_found(
        self, mock_get_database, mock_database
    ):
        """Test when booking doesn't exist."""
        mock_collection = mock_database["booking_events"]
        mock_result_one = Mock()
        mock_result_one.matched_count = 0
        mock_result_one.modified_count = 0
        mock_result_many = Mock()
        mock_result_many.matched_count = 0
        mock_result_many.modified_count = 0
        mock_collection.update_one = AsyncMock(return_value=mock_result_one)
        mock_collection.update_many = AsyncMock(return_value=mock_result_many)
        mock_get_database.return_value = mock_database

        with pytest.raises(ValueError) as exc_info:
            await BookingService.update_payment_intent_id(
                "VOYA-NOTFOUND", "pi_test_123456789"
            )

        assert "Booking not found" in str(exc_info.value)
        mock_collection.update_many.assert_called_once()

    @patch("app.domains.bookings.service.get_database")
    async def test_update_payment_intent_id_already_set(
        self, mock_get_database, mock_database
    ):
        """Test when payment_intent_id is already set (no modification)."""
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 0  # Already set
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database

        # Should not raise an error
        await BookingService.update_payment_intent_id(
            "VOYA-TEST123", "pi_test_123456789"
        )

        mock_collection.update_one.assert_called_once()
        mock_collection.update_many.assert_not_called()

    @patch("app.domains.bookings.service.get_database")
    async def test_update_payment_intent_id_multicity_parent_fanout(
        self, mock_get_database, mock_database
    ):
        """Group id updates payment_intent_id on all legs via parent_voya_booking_reference."""
        mock_collection = mock_database["booking_events"]
        mock_result_one = Mock()
        mock_result_one.matched_count = 0
        mock_result_many = Mock()
        mock_result_many.matched_count = 3
        mock_result_many.modified_count = 3
        mock_collection.update_one = AsyncMock(return_value=mock_result_one)
        mock_collection.update_many = AsyncMock(return_value=mock_result_many)
        mock_get_database.return_value = mock_database

        order_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        await BookingService.update_payment_intent_id("VOYA-MC-GROUP-1", order_id)

        mock_collection.update_one.assert_called_once_with(
            {"voya_booking_reference": "VOYA-MC-GROUP-1"},
            {"$set": {"payment_intent_id": order_id}},
        )
        mock_collection.update_many.assert_called_once_with(
            {"parent_voya_booking_reference": "VOYA-MC-GROUP-1"},
            {"$set": {"payment_intent_id": order_id}},
        )


class TestUpdateBookingDatesAndFlagsMulticity:
    """Multicity parent ref fans out date_paid / flags to all leg rows."""

    @patch("app.domains.bookings.service.get_database")
    async def test_update_booking_dates_and_flags_parent_fanout(
        self, mock_get_database, mock_database
    ):
        mock_collection = mock_database["booking_events"]
        mock_one = Mock()
        mock_one.matched_count = 0
        mock_one.modified_count = 0
        mock_many = Mock()
        mock_many.matched_count = 2
        mock_many.modified_count = 2
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.update_one = AsyncMock(return_value=mock_one)
        mock_collection.update_many = AsyncMock(return_value=mock_many)
        mock_get_database.return_value = mock_database

        paid = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        await BookingService.update_booking_dates_and_flags(
            "VOYA-MC-GROUP-1", date_paid=paid, amount=299.0
        )

        mock_collection.find_one.assert_called_once()
        mock_collection.update_many.assert_called_once_with(
            {"parent_voya_booking_reference": "VOYA-MC-GROUP-1"},
            {"$set": {"date_paid": paid, "amount": 299.0}},
        )


class TestApplyDatePaidFromCompletedPayment:
    """BookingService.apply_date_paid_from_completed_payment() — Revolut reconcile after webhook."""

    @patch.object(
        BookingService, "update_booking_dates_and_flags", new_callable=AsyncMock
    )
    @patch("app.domains.bookings.service.RevolutPaymentRepository")
    @patch("app.domains.bookings.service.PaymentRepository")
    async def test_revolut_when_stripe_missing(
        self, mock_payment_cls, mock_revolut_cls, mock_update_flags
    ):
        mock_payment_cls.return_value.get_transaction_by_payment_intent = AsyncMock(
            return_value=None
        )
        paid = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        rtxn = SimpleNamespace(
            paid_at=paid, status=PaymentStatus.SUCCEEDED, amount=19900
        )
        mock_revolut_cls.return_value.get_transaction_by_order_id = AsyncMock(
            return_value=rtxn
        )

        await BookingService.apply_date_paid_from_completed_payment(
            "VOYA-LEG-1",
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            flight_amount=None,
        )

        mock_update_flags.assert_called_once()
        kwargs = mock_update_flags.call_args.kwargs
        assert kwargs["date_paid"] == paid
        assert kwargs["amount"] == 199.0

    @patch.object(
        BookingService, "update_booking_dates_and_flags", new_callable=AsyncMock
    )
    @patch("app.domains.bookings.service.RevolutPaymentRepository")
    @patch("app.domains.bookings.service.PaymentRepository")
    async def test_skips_amount_when_flight_amount_set(
        self, mock_payment_cls, mock_revolut_cls, mock_update_flags
    ):
        mock_payment_cls.return_value.get_transaction_by_payment_intent = AsyncMock(
            return_value=None
        )
        paid = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        rtxn = SimpleNamespace(
            paid_at=paid, status=PaymentStatus.SUCCEEDED, amount=19900
        )
        mock_revolut_cls.return_value.get_transaction_by_order_id = AsyncMock(
            return_value=rtxn
        )

        await BookingService.apply_date_paid_from_completed_payment(
            "VOYA-LEG-1",
            "order-id",
            flight_amount=250.0,
        )

        kwargs = mock_update_flags.call_args.kwargs
        assert kwargs["date_paid"] == paid
        assert kwargs["amount"] is None


class TestMulticityPaymentReferenceHelpers:
    """Parent/leg resolution for payment and webhooks."""

    @patch.object(BookingService, "get_event_by_voya_reference", new_callable=AsyncMock)
    async def test_get_parent_for_multicity_leg(self, mock_get_event):
        mock_get_event.return_value = SimpleNamespace(
            parent_voya_booking_reference="VOYA-MC-1"
        )
        parent = await BookingService.get_parent_voya_booking_reference_for_leg(
            "VOYA-LEG-1"
        )
        assert parent == "VOYA-MC-1"

    @patch.object(BookingService, "get_event_by_voya_reference", new_callable=AsyncMock)
    async def test_get_parent_none_when_no_event(self, mock_get_event):
        mock_get_event.return_value = None
        assert (
            await BookingService.get_parent_voya_booking_reference_for_leg("VOYA-X")
            is None
        )

    @patch("app.domains.bookings.service.get_database")
    async def test_get_latest_by_parent_voya_reference(
        self, mock_get_database, mock_database
    ):
        owner_id = ObjectId()
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(
            return_value={
                "_id": ObjectId(),
                "user_id": owner_id,
                "voya_booking_reference": "VOYA-LEG-Z",
                "external_booking_reference": "EXT-Z",
                "action": "BOOKED",
                "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
                "event_type": "FLIGHT",
                "parent_voya_booking_reference": "VOYA-MC-1",
            }
        )
        mock_get_database.return_value = mock_database
        booking = await BookingService.get_latest_booking_by_parent_voya_reference(
            "VOYA-MC-1"
        )
        assert booking is not None
        assert booking.voya_booking_reference == "VOYA-LEG-Z"
        assert booking.parent_voya_booking_reference == "VOYA-MC-1"
        mock_collection.find_one.assert_called_once_with(
            {"parent_voya_booking_reference": "VOYA-MC-1"},
            sort=[("timestamp", -1)],
        )


# ==============================================================================
# GET LATEST BOOKING BY VOYA REFERENCE TESTS (with payment_intent_id)
# ==============================================================================


class TestGetLatestBookingByVoyaReference:
    """Test BookingService.get_latest_booking_by_voya_reference() includes payment_intent_id."""

    @patch("app.domains.bookings.service.get_database")
    async def test_get_latest_booking_includes_payment_intent_id(
        self, mock_get_database, mock_database
    ):
        """Test that booking response includes payment_intent_id when present."""
        mock_collection = mock_database["booking_events"]
        mock_booking_doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-TEST123",
            "external_booking_reference": "EXT123",
            "action": "BOOKED",
            "timestamp": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
            "payment_intent_id": "pi_test_123456789",
        }
        mock_collection.find_one = AsyncMock(return_value=mock_booking_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_by_voya_reference(
            "VOYA-TEST123"
        )

        assert result is not None
        assert result.voya_booking_reference == "VOYA-TEST123"
        assert result.payment_intent_id == "pi_test_123456789"

    @patch("app.domains.bookings.service.get_database")
    async def test_get_latest_booking_without_payment_intent_id(
        self, mock_get_database, mock_database
    ):
        """Test that booking response handles missing payment_intent_id."""
        mock_collection = mock_database["booking_events"]
        mock_booking_doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-TEST123",
            "external_booking_reference": "EXT123",
            "action": "BOOKED",
            "timestamp": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
            # payment_intent_id not present
        }
        mock_collection.find_one = AsyncMock(return_value=mock_booking_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_by_voya_reference(
            "VOYA-TEST123"
        )

        assert result is not None
        assert result.voya_booking_reference == "VOYA-TEST123"
        assert result.payment_intent_id is None

    @patch("app.domains.bookings.service.get_database")
    async def test_get_latest_booking_includes_trip_details_sync_fields(
        self, mock_get_database, mock_database
    ):
        """Test that booking response includes synced trip-details fields."""
        mock_collection = mock_database["booking_events"]
        mock_booking_doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-TEST123",
            "external_booking_reference": "EXT123",
            "action": "BOOKED",
            "timestamp": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
            "ticket_status": "TICKETED",
            "e_ticket_numbers": ["0741234567890", "0741234567891"],
            "pnr": ["ABC123"],
            "ticket_status_history": [
                {
                    "status": "TktInProcess",
                    "time": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
                },
                {
                    "status": "TICKETED",
                    "time": datetime(2026, 4, 15, 10, 5, 0, tzinfo=UTC),
                },
            ],
        }
        mock_collection.find_one = AsyncMock(return_value=mock_booking_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_by_voya_reference(
            "VOYA-TEST123"
        )

        assert result is not None
        assert result.ticket_status == "TICKETED"
        assert result.e_ticket_numbers == ["0741234567890", "0741234567891"]
        assert result.pnr == ["ABC123"]
        assert result.ticket_status_history is not None
        assert len(result.ticket_status_history) == 2
        assert result.ticket_status_history[0].status == "TktInProcess"
        assert result.ticket_status_history[1].status == "TICKETED"

    @patch("app.domains.bookings.service.get_database")
    async def test_get_latest_booking_includes_ticket_status_history(
        self, mock_get_database, mock_database
    ):
        """Test that booking response includes ticket_status_history when present."""
        mock_collection = mock_database["booking_events"]
        history = [
            {
                "status": "TktInProcess",
                "time": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            },
            {"status": "TICKETED", "time": datetime(2026, 4, 15, 10, 5, 0, tzinfo=UTC)},
        ]
        mock_booking_doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-TEST123",
            "external_booking_reference": "EXT123",
            "action": "BOOKED",
            "timestamp": datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
            "ticket_status": "TICKETED",
            "ticket_status_history": history,
            "pnr": ["ABC123"],
        }
        mock_collection.find_one = AsyncMock(return_value=mock_booking_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_by_voya_reference(
            "VOYA-TEST123"
        )

        assert result is not None
        assert result.ticket_status == "TICKETED"
        assert result.ticket_status_history is not None
        assert len(result.ticket_status_history) == 2
        assert result.ticket_status_history[0].status == "TktInProcess"
        assert result.ticket_status_history[0].time == history[0]["time"]
        assert result.ticket_status_history[1].status == "TICKETED"
        assert result.ticket_status_history[1].time == history[1]["time"]


# ==============================================================================
# GET EVENT BY VOYA REFERENCE TESTS
# ==============================================================================


class TestGetEventByVoyaReference:
    """Test BookingService.get_event_by_voya_reference() (admin; full model)."""

    @patch("app.domains.bookings.service.get_database")
    async def test_get_event_by_voya_reference_found(
        self, mock_get_database, mock_database
    ):
        """Test returns BookingEventModel when event exists."""
        mock_collection = mock_database["booking_events"]
        mock_doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-REF123",
            "external_booking_reference": "EXT456",
            "action": "BOOKED",
            "timestamp": datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
            "payload": {"sessionId": "sess-1"},
        }
        mock_collection.find_one = AsyncMock(return_value=mock_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_event_by_voya_reference("VOYA-REF123")

        assert result is not None
        assert result.voya_booking_reference == "VOYA-REF123"
        assert result.event_type == "FLIGHT"
        assert result.payload == {"sessionId": "sess-1"}
        mock_collection.find_one.assert_called_once_with(
            {"voya_booking_reference": "VOYA-REF123"}, sort=[("timestamp", -1)]
        )

    @patch("app.domains.bookings.service.get_database")
    async def test_get_event_by_voya_reference_not_found(
        self, mock_get_database, mock_database
    ):
        """Test returns None when no event exists."""
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_event_by_voya_reference("VOYA-MISSING")

        assert result is None


# ==============================================================================
# get_latest_booking_event_with_voucher_for_voya
# ==============================================================================


class TestGetLatestBookingEventWithVoucherForVoya:
    """G2A: must find a row with voucher_redemption_id, not just latest by time."""

    @patch("app.domains.bookings.service.get_database")
    async def test_queries_voucher_and_voya_or_parent(
        self, mock_get_database, mock_database
    ):
        mock_collection = mock_database["booking_events"]
        oid = ObjectId()
        mock_doc = {
            "_id": oid,
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-H-1",
            "external_booking_reference": "TEMP-EXT",
            "voucher_redemption_id": "aaaabbbbccccddddeeeeffff",
            "action": "BOOKED",
            "timestamp": datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC),
            "event_type": "HOTEL",
        }
        mock_collection.find_one = AsyncMock(return_value=mock_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_event_with_voucher_for_voya(
            "VOYA-H-1"
        )

        assert result is not None
        assert result.voucher_redemption_id == "aaaabbbbccccddddeeeeffff"
        mock_collection.find_one.assert_called_once()
        call = mock_collection.find_one.call_args
        filt = call[0][0]
        assert "voucher_redemption_id" in filt
        assert "$or" in filt
        kwargs = mock_collection.find_one.call_args.kwargs
        assert kwargs.get("sort") == [("timestamp", -1)]

    @patch("app.domains.bookings.service.get_database")
    async def test_returns_none_when_no_row_with_voucher(
        self, mock_get_database, mock_database
    ):
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_latest_booking_event_with_voucher_for_voya(
            "VOYA-EMPTY"
        )
        assert result is None


# ==============================================================================
# TRIP DETAILS SYNC UPDATE TESTS
# ==============================================================================


class TestUpdateBookingTripDetailsSync:
    """Test BookingService.update_booking_trip_details_sync()."""

    @patch("app.domains.bookings.service.get_database")
    async def test_updates_all_non_empty_trip_details_fields(
        self, mock_get_database, mock_database
    ):
        """Test syncing pnr, ticket_status, e_ticket_numbers and appends to history."""
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database
        snapshot_time = datetime(2026, 3, 18, 10, 13, 42, tzinfo=UTC)

        await BookingService.update_booking_trip_details_sync(
            "VOYA-TEST123",
            pnr=["ABC123", "XYZ789"],
            ticket_status="TICKETED",
            ticket_status_snapshot_time=snapshot_time,
            e_ticket_numbers=["0741234567890", "0741234567891"],
        )

        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"voya_booking_reference": "VOYA-TEST123"}
        ops = call_args[0][1]
        assert ops["$set"] == {
            "pnr": ["ABC123", "XYZ789"],
            "ticket_status": "TICKETED",
            "e_ticket_numbers": ["0741234567890", "0741234567891"],
        }
        assert ops["$push"]["ticket_status_history"] == {
            "status": "TICKETED",
            "time": snapshot_time,
        }

    @patch("app.domains.bookings.service.get_database")
    async def test_sets_flight_segment_departure_dates_and_leg_summaries(
        self, mock_get_database, mock_database
    ):
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database

        await BookingService.update_booking_trip_details_sync(
            "VOYA-SEG",
            flight_segment_departure_dates=["2026-07-24", "2026-07-28"],
            flight_leg_summaries=[
                {
                    "departure_date": "2026-07-24",
                    "origin_iata": "LCY",
                    "destination_iata": "JFK",
                },
                {
                    "departure_date": "2026-07-28",
                    "origin_iata": "JFK",
                    "destination_iata": "LCY",
                },
            ],
        )

        ops = mock_collection.update_one.call_args[0][1]
        assert ops["$set"]["flight_segment_departure_dates"] == [
            "2026-07-24",
            "2026-07-28",
        ]
        assert len(ops["$set"]["flight_leg_summaries"]) == 2

    @patch("app.domains.bookings.service.get_database")
    async def test_ignores_empty_trip_details_values(
        self, mock_get_database, mock_database
    ):
        """Test empty values do not trigger a database update."""
        mock_get_database.return_value = mock_database

        await BookingService.update_booking_trip_details_sync(
            "VOYA-TEST123",
            pnr=[],
            ticket_status="",
            e_ticket_numbers=[],
        )

        mock_database["booking_events"].update_one.assert_not_called()
        mock_get_database.assert_not_called()

    @patch("app.domains.bookings.service.get_database")
    async def test_pnr_and_e_tickets_only_no_history_push(
        self, mock_get_database, mock_database
    ):
        """Test syncing pnr and e_ticket_numbers without ticket_status does not push history."""
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database

        await BookingService.update_booking_trip_details_sync(
            "VOYA-TEST123",
            pnr=["ABC123"],
            e_ticket_numbers=["0741234567890"],
        )

        call_args = mock_collection.update_one.call_args
        ops = call_args[0][1]
        assert "$set" in ops
        assert ops["$set"] == {
            "pnr": ["ABC123"],
            "e_ticket_numbers": ["0741234567890"],
        }
        assert "$push" not in ops

    @patch("app.domains.bookings.service.get_database")
    async def test_sync_sets_route_and_airline_fields(
        self, mock_get_database, mock_database
    ):
        """Trip-details sync can persist IATA route snapshot + marketing airline name."""
        mock_collection = mock_database["booking_events"]
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)
        mock_get_database.return_value = mock_database

        await BookingService.update_booking_trip_details_sync(
            "VOYA-RT123",
            pnr=["PNR1"],
            departure_airport_iata="JFK",
            flight_trip_type="round_trip",
            route_legs=[
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
            primary_marketing_airline_name="British Airways",
        )

        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"voya_booking_reference": "VOYA-RT123"}
        ops = call_args[0][1]
        assert ops["$set"]["pnr"] == ["PNR1"]
        assert ops["$set"]["departure_airport_iata"] == "JFK"
        assert ops["$set"]["flight_trip_type"] == "round_trip"
        assert ops["$set"]["primary_marketing_airline_name"] == "British Airways"
        assert ops["$unset"]["arrival_airport_iata"] == ""


# ==============================================================================
# GET EVENT BY ID TESTS
# ==============================================================================


class TestGetEventById:
    """Test BookingService.get_event_by_id() (admin retry; includes payload)."""

    @patch("app.domains.bookings.service.get_database")
    async def test_get_event_by_id_found(self, mock_get_database, mock_database):
        """Test returns BookingEventModel when event exists (includes payload)."""
        oid = ObjectId()
        mock_collection = mock_database["booking_events"]
        mock_doc = {
            "_id": oid,
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-REF789",
            "external_booking_reference": "EXT789",
            "action": "BOOKED",
            "timestamp": datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC),
            "event_type": "HOTEL",
            "payload": {"hotel": "book-payload"},
        }
        mock_collection.find_one = AsyncMock(return_value=mock_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_event_by_id(str(oid))

        assert result is not None
        assert result.voya_booking_reference == "VOYA-REF789"
        assert result.event_type == "HOTEL"
        assert result.payload == {"hotel": "book-payload"}
        mock_collection.find_one.assert_called_once_with({"_id": oid})

    @patch("app.domains.bookings.service.get_database")
    async def test_get_event_by_id_not_found(self, mock_get_database, mock_database):
        """Test returns None when event does not exist."""
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_get_database.return_value = mock_database

        result = await BookingService.get_event_by_id(str(ObjectId()))

        assert result is None

    @patch("app.domains.bookings.service.get_database")
    async def test_get_event_by_id_invalid_objectid_returns_none(
        self, mock_get_database, mock_database
    ):
        """Test returns None for invalid ObjectId (exception path)."""
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(side_effect=Exception("bad id"))
        mock_get_database.return_value = mock_database

        result = await BookingService.get_event_by_id("not-a-valid-oid")

        assert result is None


# ==============================================================================
# VALIDATE USER OWNS BOOKING TESTS
# ==============================================================================


class TestValidateUserOwnsBooking:
    """Test BookingService.validate_user_owns_booking() (ownership and not-found)."""

    @patch("app.domains.bookings.service.get_database")
    async def test_raises_booking_forbidden_error_when_user_does_not_own_booking(
        self, mock_get_database, mock_database
    ):
        """When booking belongs to another user, raises BookingForbiddenError."""
        mock_collection = mock_database["booking_events"]
        owner_id = ObjectId()
        # Use a date ~2 months ahead of current time
        ts = datetime.now(UTC) + timedelta(days=60)
        booking_doc = {
            "_id": ObjectId(),
            "user_id": owner_id,
            "voya_booking_reference": "VOYA-REF123",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
        }
        mock_collection.find_one = AsyncMock(return_value=booking_doc)
        mock_get_database.return_value = mock_database

        with pytest.raises(BookingForbiddenError) as exc_info:
            await BookingService.validate_user_owns_booking(
                "VOYA-REF123", "different_user_id"
            )

        assert "do not have access" in str(exc_info.value).lower()
        mock_collection.find_one.assert_called_once_with(
            {"voya_booking_reference": "VOYA-REF123"},
            sort=[("timestamp", -1)],
        )

    @patch("app.domains.bookings.service.get_database")
    async def test_does_not_raise_when_user_owns_booking(
        self, mock_get_database, mock_database
    ):
        """When user_id matches booking owner, does not raise."""
        owner_id = ObjectId()
        mock_collection = mock_database["booking_events"]
        ts = datetime.now(UTC) + timedelta(days=60)
        booking_doc = {
            "_id": ObjectId(),
            "user_id": owner_id,
            "voya_booking_reference": "VOYA-OWNED",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
        }
        mock_collection.find_one = AsyncMock(return_value=booking_doc)
        mock_get_database.return_value = mock_database

        await BookingService.validate_user_owns_booking("VOYA-OWNED", str(owner_id))

        mock_collection.find_one.assert_called_once()

    @patch("app.domains.bookings.service.get_database")
    async def test_raises_value_error_when_booking_not_found(
        self, mock_get_database, mock_database
    ):
        """When no booking exists for reference, raises ValueError."""
        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_get_database.return_value = mock_database

        with pytest.raises(ValueError) as exc_info:
            await BookingService.validate_user_owns_booking(
                "VOYA-NOTFOUND", "any_user_id"
            )

        assert "Booking not found" in str(exc_info.value)
        assert "VOYA-NOTFOUND" in str(exc_info.value)


# ==============================================================================
# MULTICITY GROUP CONTEXT
# ==============================================================================


class TestListMulticityGroupForVoyaReference:
    """BookingService.list_multicity_group_for_voya_reference() — Mongo group aggregation."""

    @patch("app.domains.bookings.service.get_database")
    async def test_no_parent_returns_single_leg(self, mock_get_database, mock_database):
        owner_id = ObjectId()
        mock_collection = mock_database["booking_events"]
        ts = datetime.now(UTC) + timedelta(days=60)
        booking_doc = {
            "_id": ObjectId(),
            "user_id": owner_id,
            "voya_booking_reference": "VOYA-SOLO",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
            "parent_voya_booking_reference": None,
            "external_booking_reference": "EXT-1",
            "ticket_status": "ticketed",
            "departure_airport_iata": "LHR",
        }
        mock_collection.find_one = AsyncMock(return_value=booking_doc)
        mock_get_database.return_value = mock_database

        from app.domains.bookings.service import BookingService

        result = await BookingService.list_multicity_group_for_voya_reference(
            str(owner_id), "VOYA-SOLO"
        )

        assert result.parent_voya_booking_reference is None
        assert len(result.legs) == 1
        assert result.legs[0].voya_booking_reference == "VOYA-SOLO"
        assert result.legs[0].ticket_status == "ticketed"

    @patch("app.domains.bookings.service.get_database")
    async def test_with_parent_returns_all_sibling_legs(
        self, mock_get_database, mock_database
    ):
        owner_id = ObjectId()
        parent = "VOYA-MC-GROUP-1"
        ts = datetime.now(UTC) + timedelta(days=60)
        # Leg 0 has lexicographically later VOYA ref than leg 1 — order must follow multistay_leg_index
        doc_leg0 = {
            "_id": ObjectId(),
            "user_id": owner_id,
            "voya_booking_reference": "VOYA-LEG-ZZZ",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
            "parent_voya_booking_reference": parent,
            "multistay_leg_index": 0,
            "ticket_status": "ticketed",
        }
        doc_leg1 = {
            "_id": ObjectId(),
            "user_id": owner_id,
            "voya_booking_reference": "VOYA-LEG-AAA",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
            "parent_voya_booking_reference": parent,
            "multistay_leg_index": 1,
            "ticket_status": "pending",
        }

        mock_collection = mock_database["booking_events"]
        mock_collection.find_one = AsyncMock(return_value=doc_leg0)

        class _FakeCursor:
            def sort(self, *_a, **_kw):
                return self

            async def to_list(self, length: int | None = None):
                return [doc_leg1, doc_leg0]

        mock_collection.find = MagicMock(return_value=_FakeCursor())
        mock_get_database.return_value = mock_database

        from app.domains.bookings.service import BookingService

        result = await BookingService.list_multicity_group_for_voya_reference(
            str(owner_id), "VOYA-LEG-ZZZ"
        )

        assert result.parent_voya_booking_reference == parent
        assert len(result.legs) == 2
        assert [leg.voya_booking_reference for leg in result.legs] == [
            "VOYA-LEG-ZZZ",
            "VOYA-LEG-AAA",
        ]


# ==============================================================================
# LIST ALL EVENTS TESTS (admin)
# ==============================================================================


class _AsyncIterator:
    """Helper to make a list async-iterable for Motor cursor emulation."""

    def __init__(self, items: list):
        self._items = list(items)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._items):
            raise StopAsyncIteration
        val = self._items[self._i]
        self._i += 1
        return val


class TestListAllEvents:
    """Test BookingService.list_all_events() (admin list)."""

    @patch("app.domains.bookings.service.get_database")
    async def test_list_all_events_returns_events_and_total(
        self, mock_get_database, mock_database
    ):
        """Test returns paginated events and total count."""
        mock_coll = mock_database["booking_events"]
        mock_coll.count_documents = AsyncMock(return_value=2)
        doc1 = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-A",
            "external_booking_reference": "EXT-A",
            "action": "BOOKED",
            "timestamp": datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
        }
        doc2 = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-B",
            "external_booking_reference": "EXT-B",
            "action": "BOOKED",
            "timestamp": datetime(2026, 8, 14, 9, 0, 0, tzinfo=UTC),
            "event_type": "HOTEL",
        }
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc1, doc2])
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        events, total = await BookingService.list_all_events(limit=10, offset=0)

        assert total == 2
        assert len(events) == 2
        assert events[0].voya_booking_reference == "VOYA-A"
        assert events[0].event_type == "FLIGHT"
        assert events[1].voya_booking_reference == "VOYA-B"
        assert events[1].event_type == "HOTEL"
        mock_coll.count_documents.assert_called_once_with({})
        mock_coll.find.assert_called_once_with({})
        mock_cursor.sort.assert_called_once_with("timestamp", -1)
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(10)

    @patch("app.domains.bookings.service.get_database")
    async def test_list_all_events_pagination(self, mock_get_database, mock_database):
        """Test limit and offset are applied."""
        mock_coll = mock_database["booking_events"]
        mock_coll.count_documents = AsyncMock(return_value=100)
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: _AsyncIterator([])
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        await BookingService.list_all_events(limit=20, offset=40)

        mock_cursor.skip.assert_called_once_with(40)
        mock_cursor.limit.assert_called_once_with(20)

    @patch("app.domains.bookings.service.get_database")
    async def test_list_all_events_empty(self, mock_get_database, mock_database):
        """Test returns empty list when no events."""
        mock_coll = mock_database["booking_events"]
        mock_coll.count_documents = AsyncMock(return_value=0)
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: _AsyncIterator([])
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        events, total = await BookingService.list_all_events()

        assert events == []
        assert total == 0

    @patch("app.domains.bookings.service.get_database")
    async def test_list_all_events_unknown_event_type_defaults_to_flight(
        self, mock_get_database, mock_database
    ):
        """Test unknown event_type in document defaults to FLIGHT."""
        mock_coll = mock_database["booking_events"]
        mock_coll.count_documents = AsyncMock(return_value=1)
        doc = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-X",
            "external_booking_reference": "EXT-X",
            "action": "BOOKED",
            "timestamp": datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC),
            "event_type": "OTHER",  # not FLIGHT or HOTEL
        }
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        events, total = await BookingService.list_all_events(limit=50, offset=0)

        assert total == 1
        assert len(events) == 1
        assert events[0].event_type == "FLIGHT"

    @patch("app.domains.bookings.service.get_database")
    async def test_list_all_events_skips_malformed_documents(
        self, mock_get_database, mock_database
    ):
        """Admin list skips rows missing required fields; total count is still full."""
        mock_coll = mock_database["booking_events"]
        mock_coll.count_documents = AsyncMock(return_value=2)
        good = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-OK",
            "external_booking_reference": "EXT-OK",
            "action": "BOOKED",
            "timestamp": datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC),
            "event_type": "FLIGHT",
        }
        bad = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "voya_booking_reference": "VOYA-BAD",
            "external_booking_reference": "EXT-BAD",
            "action": "BOOKED",
            # missing timestamp
            "event_type": "FLIGHT",
        }
        mock_cursor = Mock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: _AsyncIterator([good, bad])
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        events, total = await BookingService.list_all_events(limit=10, offset=0)

        assert total == 2
        assert len(events) == 1
        assert events[0].voya_booking_reference == "VOYA-OK"


# ==============================================================================
# MULTICITY GROUP + PAYMENT INTENT LOOKUP
# ==============================================================================


class TestGetVoyaReferenceByPaymentIntentId:
    """BookingService.get_voya_reference_by_payment_intent_id — webhook fallback lookup."""

    @patch("app.domains.bookings.service.get_database")
    async def test_returns_reference_when_booking_exists(
        self, mock_get_database, mock_database
    ):
        mock_coll = mock_database["booking_events"]
        mock_coll.find_one = AsyncMock(
            return_value={"voya_booking_reference": "VOYA-PI-1"}
        )
        mock_get_database.return_value = mock_database

        ref = await BookingService.get_voya_reference_by_payment_intent_id(
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        )
        assert ref == "VOYA-PI-1"
        mock_coll.find_one.assert_called_once()
        assert mock_coll.find_one.call_args[0][0] == {
            "payment_intent_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        }

    @patch("app.domains.bookings.service.get_database")
    async def test_returns_none_when_not_found(self, mock_get_database, mock_database):
        mock_coll = mock_database["booking_events"]
        mock_coll.find_one = AsyncMock(return_value=None)
        mock_get_database.return_value = mock_database

        ref = await BookingService.get_voya_reference_by_payment_intent_id("missing")
        assert ref is None

    @patch("app.domains.bookings.service.get_database")
    async def test_returns_none_when_doc_has_no_reference(
        self, mock_get_database, mock_database
    ):
        mock_coll = mock_database["booking_events"]
        mock_coll.find_one = AsyncMock(return_value={"_id": ObjectId()})
        mock_get_database.return_value = mock_database

        ref = await BookingService.get_voya_reference_by_payment_intent_id("pi_x")
        assert ref is None


class TestListMulticityGroupForVoyaReferenceDedup:
    """BookingService.list_multicity_group_for_voya_reference — dedup + sibling cursor."""

    @patch.object(BookingService, "validate_user_owns_booking", new_callable=AsyncMock)
    @patch("app.domains.bookings.service.get_database")
    async def test_single_booking_without_parent_returns_one_leg(
        self, mock_get_database, mock_validate_owns, mock_database
    ):
        user_id = str(ObjectId())
        oid = ObjectId(user_id)
        mock_coll = mock_database["booking_events"]
        base_doc = {
            "_id": ObjectId(),
            "user_id": oid,
            "voya_booking_reference": "VOYA-SOLO",
            "parent_voya_booking_reference": None,
            "event_type": "FLIGHT",
            "timestamp": datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
            "departure_airport_iata": "JFK",
        }
        mock_coll.find_one = AsyncMock(return_value=base_doc)
        mock_get_database.return_value = mock_database

        result = await BookingService.list_multicity_group_for_voya_reference(
            user_id, "VOYA-SOLO"
        )

        assert result.parent_voya_booking_reference is None
        assert len(result.legs) == 1
        assert result.legs[0].voya_booking_reference == "VOYA-SOLO"
        assert result.legs[0].departure_airport_iata == "JFK"
        mock_validate_owns.assert_called_once_with("VOYA-SOLO", user_id)
        mock_coll.find.assert_not_called()

    @patch.object(BookingService, "validate_user_owns_booking", new_callable=AsyncMock)
    @patch("app.domains.bookings.service.get_database")
    async def test_multicity_parent_dedupes_by_ref_keeps_newer_timestamp(
        self, mock_get_database, mock_validate_owns, mock_database
    ):
        user_id = str(ObjectId())
        oid = ObjectId(user_id)
        parent = "VOYA-MC-PARENT"
        t_old = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        t_new = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)

        leg_a_old = {
            "user_id": oid,
            "voya_booking_reference": "VOYA-LEG-A",
            "parent_voya_booking_reference": parent,
            "event_type": "FLIGHT",
            "timestamp": t_old,
            "ticket_status": "old",
        }
        base_doc = {**leg_a_old, "timestamp": t_new, "ticket_status": "current"}

        mock_coll = mock_database["booking_events"]
        mock_coll.find_one = AsyncMock(return_value=base_doc)

        mock_cursor = MagicMock()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        raw_legs = [
            leg_a_old,
            {
                **leg_a_old,
                "timestamp": t_new,
                "ticket_status": "current",
            },
            {
                "user_id": oid,
                "voya_booking_reference": "VOYA-LEG-B",
                "parent_voya_booking_reference": parent,
                "event_type": "FLIGHT",
                "timestamp": t_old,
            },
        ]
        mock_cursor.to_list = AsyncMock(return_value=raw_legs)
        mock_coll.find = Mock(return_value=mock_cursor)
        mock_get_database.return_value = mock_database

        result = await BookingService.list_multicity_group_for_voya_reference(
            user_id, "VOYA-LEG-A"
        )

        assert result.parent_voya_booking_reference == parent
        assert len(result.legs) == 2
        leg_a = next(
            leg for leg in result.legs if leg.voya_booking_reference == "VOYA-LEG-A"
        )
        assert leg_a.ticket_status == "current"
        mock_cursor.to_list.assert_called_once_with(length=MAX_MULTICITY_LEGS)

    @patch.object(BookingService, "validate_user_owns_booking", new_callable=AsyncMock)
    @patch("app.domains.bookings.service.get_database")
    async def test_invalid_user_id_raises_value_error(
        self, mock_get_database, mock_validate_owns, mock_database
    ):
        """ObjectId(user_id) must not surface as 500 for malformed ids."""
        user_id = "not-a-valid-objectid"
        oid = ObjectId()
        base_doc = {
            "_id": ObjectId(),
            "user_id": oid,
            "voya_booking_reference": "VOYA-LEG",
            "parent_voya_booking_reference": "VOYA-MC-P",
            "event_type": "FLIGHT",
            "timestamp": datetime.now(UTC),
        }
        mock_coll = mock_database["booking_events"]
        mock_coll.find_one = AsyncMock(return_value=base_doc)
        mock_get_database.return_value = mock_database

        with pytest.raises(ValueError, match="Invalid user id"):
            await BookingService.list_multicity_group_for_voya_reference(
                user_id, "VOYA-LEG"
            )


class TestDocToMulticityLeg:
    """BookingService._doc_to_multicity_leg — required voya_booking_reference."""

    def test_raises_when_voya_booking_reference_missing(self):
        with pytest.raises(ValueError, match="missing voya_booking_reference"):
            BookingService._doc_to_multicity_leg({"_id": ObjectId()})


# ==============================================================================
# GDS PENDING → BOOKED UPDATE (after FlightLogic booking API)
# ==============================================================================


class TestUpdateGdsPendingBookingAfterApi:
    """BookingService.update_gds_pending_booking_after_api() — Mongo sync vs supplier success."""

    @patch("app.domains.bookings.service.BookingRepository")
    async def test_raises_when_no_document_updated(self, mock_repo_cls):
        """Hard failure when TEMP-REF/PENDING row is missing (split-brain vs FlightLogic)."""
        mock_repo = mock_repo_cls.return_value
        mock_result = Mock()
        mock_result.matched_count = 0
        mock_result.modified_count = 0
        mock_repo.update_gds_pending_booking_to_booked = AsyncMock(
            return_value=mock_result
        )

        with pytest.raises(GdsPendingBookingSyncError) as exc_info:
            await BookingService.update_gds_pending_booking_after_api(
                "VOYA-GDS-PENDING-1",
                "FL-EXT-REF-999",
                date_booked=datetime.now(UTC),
            )

        assert "could not update" in str(exc_info.value).lower()

    @patch("app.domains.bookings.service.BookingRepository")
    async def test_sets_date_tickets_issued_when_booking_succeeds(self, mock_repo_cls):
        """Parity with LCC: date_tickets_issued set when booking API succeeds."""
        mock_repo = mock_repo_cls.return_value
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_repo.update_gds_pending_booking_to_booked = AsyncMock(
            return_value=mock_result
        )

        booked = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        await BookingService.update_gds_pending_booking_after_api(
            "VOYA-GDS-PENDING-2",
            "FL-EXT-REF-888",
            date_booked=booked,
        )

        mock_repo.update_gds_pending_booking_to_booked.assert_called_once()
        call_args = mock_repo.update_gds_pending_booking_to_booked.call_args
        assert call_args[0][0] == "VOYA-GDS-PENDING-2"
        set_doc = call_args[0][1]
        assert set_doc["date_booked"] == booked
        assert set_doc["date_tickets_issued"] == booked

    @patch("app.domains.bookings.service.BookingRepository")
    async def test_success_when_modified(self, mock_repo_cls):
        """Does not raise when one document matched and was updated."""
        mock_repo = mock_repo_cls.return_value
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_repo.update_gds_pending_booking_to_booked = AsyncMock(
            return_value=mock_result
        )

        await BookingService.update_gds_pending_booking_after_api(
            "VOYA-OK",
            "EXT-1",
            date_booked=datetime.now(UTC),
        )

        mock_repo.update_gds_pending_booking_to_booked.assert_called_once()

    @patch("app.domains.bookings.service.BookingRepository")
    async def test_success_when_matched_but_unchanged_idempotent(self, mock_repo_cls):
        """matched_count > 0 with modified_count == 0 still succeeds (idempotent apply)."""
        mock_repo = mock_repo_cls.return_value
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 0
        mock_repo.update_gds_pending_booking_to_booked = AsyncMock(
            return_value=mock_result
        )

        await BookingService.update_gds_pending_booking_after_api(
            "VOYA-IDEMPOTENT",
            "EXT-2",
            date_booked=datetime.now(UTC),
        )

        mock_repo.update_gds_pending_booking_to_booked.assert_called_once()

    @patch("app.domains.bookings.service.BookingRepository")
    async def test_passes_route_snapshot_and_unsets_legacy_flat_iata_fields(
        self, mock_repo_cls
    ):
        """Route legs + airline snapshot are written and legacy flat IATA keys unset."""
        mock_repo = mock_repo_cls.return_value
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mock_repo.update_gds_pending_booking_to_booked = AsyncMock(
            return_value=mock_result
        )
        route_legs = [
            {
                "leg_index": 0,
                "departure_iata": "JFK",
                "arrival_iata": "LHR",
                "segment_count": 1,
                "segments": [
                    {"departure_iata": "JFK", "arrival_iata": "LHR"},
                ],
            }
        ]
        booked = datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC)
        await BookingService.update_gds_pending_booking_after_api(
            "VOYA-GDS-ROUTE",
            "FL-EXT-ROUTE",
            date_booked=booked,
            departure_airport_iata="JFK",
            flight_trip_type="one_way",
            route_legs=route_legs,
            primary_marketing_airline_name="Ocean Air",
        )

        mock_repo.update_gds_pending_booking_to_booked.assert_called_once()
        _voya, set_doc, unset_legacy = (
            mock_repo.update_gds_pending_booking_to_booked.call_args[0]
        )
        assert set_doc["route_legs"] == route_legs
        assert set_doc["departure_airport_iata"] == "JFK"
        assert set_doc["flight_trip_type"] == "one_way"
        assert set_doc["primary_marketing_airline_name"] == "Ocean Air"
        assert unset_legacy == {
            "arrival_airport_iata": "",
            "return_departure_airport_iata": "",
            "return_arrival_airport_iata": "",
        }


class TestUpdateBookingAfterFlightConfirmationRouteSnapshot:
    """LCC update_booking_after_flight_confirmation — route snapshot fields on $set/$unset."""

    @patch("app.domains.bookings.service.get_database")
    async def test_sets_route_legs_and_unsets_legacy_iata_when_confirming(
        self, mock_get_database, mock_database
    ):
        mock_coll = mock_database["booking_events"]
        mock_coll.update_one = AsyncMock(return_value=Mock(modified_count=1))
        mock_get_database.return_value = mock_database
        route_legs = [
            {
                "leg_index": 0,
                "departure_iata": "SFO",
                "arrival_iata": "NRT",
                "segment_count": 1,
                "segments": [
                    {"departure_iata": "SFO", "arrival_iata": "NRT"},
                ],
            }
        ]
        await BookingService.update_booking_after_flight_confirmation(
            "VOYA-LCC-ROUTE",
            "FL-EXT-LCC",
            departure_airport_iata="SFO",
            flight_trip_type="one_way",
            route_legs=route_legs,
            primary_marketing_airline_name="ANA",
        )

        mock_coll.update_one.assert_called_once()
        filt, update_op = mock_coll.update_one.call_args[0]
        assert filt["external_booking_reference"] == TEMP_EXTERNAL_REF
        assert filt["carrier_type"] == "LCC"
        assert filt["action"] == "BOOKED"
        assert update_op["$set"]["route_legs"] == route_legs
        assert update_op["$set"]["primary_marketing_airline_name"] == "ANA"
        assert update_op["$unset"] == {
            "arrival_airport_iata": "",
            "return_departure_airport_iata": "",
            "return_arrival_airport_iata": "",
        }


class TestBookingDocumentToResponse:
    """booking_document_to_response (my-bookings / admin list mapping)."""

    def test_maps_route_airline_and_multicity_leg(self):
        oid = ObjectId()
        uid = ObjectId()
        ts = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        doc = {
            "_id": oid,
            "user_id": uid,
            "voya_booking_reference": "VOYA-LEG",
            "external_booking_reference": "EXT-X",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
            "departure_airport_iata": "JFK",
            "flight_trip_type": "one_way",
            "route_legs": [
                {
                    "leg_index": 0,
                    "departure_iata": "JFK",
                    "arrival_iata": "LHR",
                    "segment_count": 1,
                    "segments": [
                        {"departure_iata": "JFK", "arrival_iata": "LHR"},
                    ],
                }
            ],
            "primary_marketing_airline_name": "Ocean Air",
            "parent_voya_booking_reference": "VOYA-MC-PARENT",
            "multistay_leg_index": 1,
        }
        r = booking_document_to_response(doc)
        assert r.id == str(oid)
        assert r.user_id == str(uid)
        assert r.departure_airport_iata == "JFK"
        assert r.flight_trip_type == "one_way"
        assert r.route_legs is not None
        assert len(r.route_legs) == 1
        assert r.primary_marketing_airline_name == "Ocean Air"
        assert r.parent_voya_booking_reference == "VOYA-MC-PARENT"
        assert r.multistay_leg_index == 1

    def test_corrupt_route_legs_in_document_maps_to_none(self):
        """Bad Mongo data is dropped by parse_route_legs_from_document (no 500 on list)."""
        oid = ObjectId()
        uid = ObjectId()
        ts = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)
        doc = {
            "_id": oid,
            "user_id": uid,
            "voya_booking_reference": "VOYA-BAD-LEG",
            "external_booking_reference": "EXT-B",
            "action": "BOOKED",
            "timestamp": ts,
            "event_type": "FLIGHT",
            "route_legs": [{"not": "a valid leg"}],
        }
        r = booking_document_to_response(doc)
        assert r.route_legs is None

    def test_invalid_action_defaults_to_booked(self):
        oid = ObjectId()
        uid = ObjectId()
        ts = datetime(2026, 1, 3, 12, 0, 0, tzinfo=UTC)
        doc = {
            "_id": oid,
            "user_id": uid,
            "voya_booking_reference": "VOYA-A",
            "external_booking_reference": "EXT-A",
            "action": "not-a-valid-action",
            "timestamp": ts,
            "event_type": "FLIGHT",
        }
        r = booking_document_to_response(doc)
        assert r.action == "BOOKED"

    def test_raises_when_missing_required_id_or_timestamp(self):
        oid = ObjectId()
        uid = ObjectId()
        ts = datetime(2026, 1, 4, 12, 0, 0, tzinfo=UTC)
        with pytest.raises(MalformedBookingEventDocumentError):
            booking_document_to_response(
                {
                    "user_id": uid,
                    "timestamp": ts,
                    "voya_booking_reference": "VOYA-Z",
                    "external_booking_reference": "EXT-Z",
                }
            )
        with pytest.raises(MalformedBookingEventDocumentError):
            booking_document_to_response(
                {
                    "_id": oid,
                    "timestamp": ts,
                    "voya_booking_reference": "VOYA-Z",
                    "external_booking_reference": "EXT-Z",
                }
            )
