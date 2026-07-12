"""Booking service - Simplified booking management."""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, cast

from bson import ObjectId
from bson.errors import InvalidId

from app.database.dependencies import get_database
from app.database.flight_route import (
    departure_iata_from_route_legs_raw,
    parse_route_legs_from_document,
)
from app.database.models.booking_event import BookingEventModel
from app.domains.bookings.constants import (
    BOOKING_EVENT_COLLECTION,
    TEMP_EXTERNAL_REF,
)
from app.domains.bookings.exceptions import (
    BookingForbiddenError,
    GdsPendingBookingSyncError,
    MalformedBookingEventDocumentError,
)
from app.domains.bookings.reference_generator import VoyaReferenceGenerator
from app.domains.bookings.repository import BookingRepository
from app.domains.bookings.schemas import (
    BookingEventResponse,
    CreateBookingEventRequest,
    MulticityBookingGroupResponse,
    MulticityLegBookingSummaryItem,
    TicketStatusSnapshotResponse,
)
from app.domains.payment.enums import PaymentStatus
from app.domains.payment.repository import PaymentRepository
from app.domains.revolut_payment.repository import RevolutPaymentRepository
from app.domains.saved_itinerary import ensure_saved_itinerary_owned_by_user

logger = logging.getLogger(__name__)

# Cap for multicity sibling-leg query (booking_events rows per group); adjustable if product allows larger groups.
MAX_MULTICITY_LEGS = 50


def _flight_trip_type_from_value(
    raw: object,
) -> Literal["one_way", "round_trip", "multi_city"] | None:
    if raw in ("one_way", "round_trip", "multi_city"):
        return raw  # type: ignore[return-value]
    return None


def _booking_event_model_to_response(model: BookingEventModel) -> BookingEventResponse:
    """Map BookingEventModel to API response (delegates to :meth:`BookingService.booking_event_model_to_response`)."""
    return BookingService.booking_event_model_to_response(model)


def _multistay_leg_sort_key(doc: Mapping[str, Any]) -> tuple:
    """Sort multi-stay legs by itinerary index when present, else by booking time, then ref."""
    raw_idx = doc.get("multistay_leg_index")
    if isinstance(raw_idx, int):
        return (0, raw_idx, 0.0, "")
    ts = doc.get("timestamp")
    if isinstance(ts, datetime):
        return (1, 0, ts.timestamp(), str(doc.get("voya_booking_reference") or ""))
    return (2, 0, 0.0, str(doc.get("voya_booking_reference") or ""))


def booking_document_to_response(doc: dict[str, Any]) -> BookingEventResponse:
    """Map a raw Mongo booking_events document to API response (my-bookings, admin list).

    Raises:
        MalformedBookingEventDocumentError: If ``_id``, ``user_id``, or ``timestamp`` is missing.
    """
    oid = doc.get("_id")
    uid = doc.get("user_id")
    ts = doc.get("timestamp")
    if oid is None or uid is None or ts is None:
        raise MalformedBookingEventDocumentError(
            "booking_events document missing required field(s): "
            f"_id={oid!r}, user_id={uid!r}, timestamp={ts!r}"
        )
    raw_event_type = doc.get("event_type") or "FLIGHT"
    event_type = cast(
        "Literal['FLIGHT', 'HOTEL']",
        raw_event_type if raw_event_type in ("FLIGHT", "HOTEL") else "FLIGHT",
    )
    raw_action = doc.get("action") or "BOOKED"
    if raw_action not in ("BOOKED", "CANCELLED", "PENDING"):
        raw_action = "BOOKED"
    action = cast("Literal['BOOKED', 'CANCELLED', 'PENDING']", raw_action)
    saved_raw = doc.get("saved_itinerary_id")
    return BookingEventResponse(
        id=str(oid),
        user_id=str(uid),
        voya_booking_reference=doc.get("voya_booking_reference") or "",
        external_booking_reference=doc.get("external_booking_reference", ""),
        action=action,
        timestamp=ts,
        event_type=event_type,
        airline_pnr_code=doc.get("airline_pnr_code"),
        airline_pnr_airline_code=doc.get("airline_pnr_airline_code"),
        airline_pnr_airline_name=doc.get("airline_pnr_airline_name"),
        airline_pnr_status=doc.get("airline_pnr_status"),
        contact_email=doc.get("contact_email"),
        cancellation_policy_text=doc.get("cancellation_policy_text"),
        ticket_time_limit=doc.get("ticket_time_limit"),
        departure_airport_iata=doc.get("departure_airport_iata"),
        flight_trip_type=_flight_trip_type_from_value(doc.get("flight_trip_type")),
        route_legs=parse_route_legs_from_document(
            doc.get("route_legs"), booking_id=str(oid)
        ),
        primary_marketing_airline_name=doc.get("primary_marketing_airline_name"),
        payment_intent_id=doc.get("payment_intent_id"),
        carrier_type=doc.get("carrier_type"),
        date_booked=doc.get("date_booked"),
        date_paid=doc.get("date_paid"),
        date_tickets_issued=doc.get("date_tickets_issued"),
        amount=doc.get("amount"),
        confirmation_email_sent=doc.get("confirmation_email_sent"),
        pnr=doc.get("pnr"),
        ticket_status=doc.get("ticket_status"),
        e_ticket_numbers=doc.get("e_ticket_numbers"),
        flight_leg_summaries=doc.get("flight_leg_summaries"),
        flight_segment_departure_dates=doc.get("flight_segment_departure_dates"),
        ticket_status_history=_to_ticket_status_history_response(
            doc.get("ticket_status_history")
        ),
        hotel_reference_number=doc.get("hotel_reference_number"),
        hotel_image_url=doc.get("hotel_image_url"),
        hotel_name=doc.get("hotel_name"),
        hotel_city=doc.get("hotel_city"),
        hotel_address=doc.get("hotel_address"),
        hotel_latitude=doc.get("hotel_latitude"),
        hotel_longitude=doc.get("hotel_longitude"),
        hotel_check_in_date=doc.get("hotel_check_in_date"),
        hotel_check_out_date=doc.get("hotel_check_out_date"),
        hotel_nights=doc.get("hotel_nights"),
        saved_itinerary_id=str(saved_raw) if saved_raw else None,
        parent_voya_booking_reference=doc.get("parent_voya_booking_reference"),
        multistay_leg_index=doc.get("multistay_leg_index"),
        voucher_redemption_id=doc.get("voucher_redemption_id"),
        voucher_discount_amount=doc.get("voucher_discount_amount"),
    )


def _to_ticket_status_history_response(
    history: list | None,
) -> list[TicketStatusSnapshotResponse] | None:
    """Convert ticket_status_history from model or raw doc to response format."""
    if not history:
        return None
    result: list[TicketStatusSnapshotResponse] = []
    for s in history:
        if hasattr(s, "status"):
            result.append(TicketStatusSnapshotResponse(status=s.status, time=s.time))
        else:
            result.append(
                TicketStatusSnapshotResponse(status=s["status"], time=s["time"])
            )
    return result


class BookingService:
    """Service for managing bookings."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    async def create_booking(
        self, request: CreateBookingEventRequest
    ) -> BookingEventResponse:
        """Create a new simplified booking event.

        Only stores:
        - external_booking_reference
        - action (BOOKED/CANCELLED)
        - timestamp
        - user_id
        - event_type (FLIGHT)
        """
        logger.info(
            f"Creating {request.action} event for booking {request.external_booking_reference}"
        )

        voucher_redemption_id: str | None = None
        voucher_discount_amount: int | None = None
        if request.voucher_redemption_id:
            from app.domains.discount.service import discount_service

            voucher_redemption_id = request.voucher_redemption_id
            try:
                voucher_discount_amount = await discount_service.validate_voucher_reservation_for_booking_event(
                    user_id=self.user_id,
                    redemption_id=request.voucher_redemption_id,
                )
            except Exception as e:
                logger.exception(
                    "Voucher validation failed; persisting booking event with "
                    "voucher_redemption_id only (discount may be reconciled later): %s",
                    e,
                )

        saved_itinerary_oid: ObjectId | None = None
        if request.saved_itinerary_id:
            saved_itinerary_oid = await ensure_saved_itinerary_owned_by_user(
                self.user_id, request.saved_itinerary_id
            )
            if saved_itinerary_oid is None:
                logger.warning(
                    "Ignoring saved_itinerary_id on create_booking (invalid or not owned): %s",
                    request.saved_itinerary_id,
                )

        # Get database connection
        db = await get_database()

        if request.voya_booking_reference:
            voya_booking_reference = request.voya_booking_reference
            logger.info("Using provided VOYA reference: %s", voya_booking_reference)
        else:
            voya_booking_reference = await VoyaReferenceGenerator.generate_unique(
                db[BOOKING_EVENT_COLLECTION]
            )
            logger.info("Generated VOYA reference: %s", voya_booking_reference)

        # Create simplified database model
        event_model = BookingEventModel(
            user_id=ObjectId(self.user_id),
            saved_itinerary_id=saved_itinerary_oid,
            voya_booking_reference=voya_booking_reference,
            external_booking_reference=request.external_booking_reference,
            action=request.action,
            timestamp=datetime.now(UTC),
            event_type=request.event_type,
            parent_voya_booking_reference=request.parent_voya_booking_reference,
            multistay_leg_index=request.multistay_leg_index,
            airline_pnr_code=request.airline_pnr_code,
            airline_pnr_airline_code=request.airline_pnr_airline_code,
            airline_pnr_airline_name=request.airline_pnr_airline_name,
            airline_pnr_status=request.airline_pnr_status,
            contact_email=request.contact_email,
            cancellation_policy_text=request.cancellation_policy_text,
            ticket_time_limit=request.ticket_time_limit,  # Store UTC time limit
            departure_airport_iata=request.departure_airport_iata,  # Store departure airport IATA
            flight_trip_type=request.flight_trip_type,
            route_legs=request.route_legs,
            primary_marketing_airline_name=request.primary_marketing_airline_name,
            carrier_type=request.carrier_type,  # GDS or LCC for flight bookings
            payment_intent_id=request.payment_intent_id,  # LCC: set at creation; GDS: may be set later
            payload=request.payload,  # GDS: store at creation; LCC: set later via set_booking_payload
            amount=request.amount,
            date_booked=request.date_booked,
            date_paid=request.date_paid,
            pnr=request.pnr,
            ticket_status=request.ticket_status,
            e_ticket_numbers=request.e_ticket_numbers,
            flight_leg_summaries=request.flight_leg_summaries,
            flight_segment_departure_dates=request.flight_segment_departure_dates,
            hotel_image_url=request.hotel_image_url,
            hotel_name=request.hotel_name,
            hotel_city=request.hotel_city,
            hotel_address=request.hotel_address,
            hotel_latitude=request.hotel_latitude,
            hotel_longitude=request.hotel_longitude,
            hotel_check_in_date=request.hotel_check_in_date,
            hotel_check_out_date=request.hotel_check_out_date,
            hotel_nights=request.hotel_nights,
            voucher_redemption_id=voucher_redemption_id,
            voucher_discount_amount=voucher_discount_amount,
        )
        document_to_save = event_model.model_dump(by_alias=True, exclude_none=True)

        # Log cancellation policy status for debugging
        if request.cancellation_policy_text:
            logger.info(
                f"Storing cancellation_policy_text for {voya_booking_reference} "
                f"(length: {len(request.cancellation_policy_text)})"
            )
        else:
            logger.debug(
                f"No cancellation_policy_text provided for {voya_booking_reference}"
            )

        logger.info(
            f"Saving {request.action} event for {request.external_booking_reference}"
        )

        result = await db[BOOKING_EVENT_COLLECTION].insert_one(document_to_save)
        event_model.id = result.inserted_id

        logger.info(f"Booking saved with ID: {result.inserted_id}")

        # Convert back to response
        return BookingService.booking_event_model_to_response(event_model)

    @staticmethod
    def booking_event_model_to_response(
        model: BookingEventModel,
    ) -> BookingEventResponse:
        """Map persisted booking event model to API response (single source of truth)."""
        return BookingEventResponse(
            id=str(model.id) if model.id else "",
            user_id=str(model.user_id),
            voya_booking_reference=model.voya_booking_reference or "",
            external_booking_reference=model.external_booking_reference,
            action=model.action,
            timestamp=model.timestamp,
            event_type=model.event_type,
            airline_pnr_code=model.airline_pnr_code,
            airline_pnr_airline_code=model.airline_pnr_airline_code,
            airline_pnr_airline_name=model.airline_pnr_airline_name,
            airline_pnr_status=model.airline_pnr_status,
            contact_email=model.contact_email,
            cancellation_policy_text=model.cancellation_policy_text,
            ticket_time_limit=model.ticket_time_limit,
            departure_airport_iata=model.departure_airport_iata,
            flight_trip_type=_flight_trip_type_from_value(model.flight_trip_type),
            route_legs=model.route_legs,
            primary_marketing_airline_name=model.primary_marketing_airline_name,
            carrier_type=model.carrier_type,
            payment_intent_id=model.payment_intent_id,
            date_booked=model.date_booked,
            date_paid=model.date_paid,
            date_tickets_issued=model.date_tickets_issued,
            amount=model.amount,
            confirmation_email_sent=model.confirmation_email_sent,
            pnr=model.pnr,
            ticket_status=model.ticket_status,
            e_ticket_numbers=model.e_ticket_numbers,
            flight_leg_summaries=model.flight_leg_summaries,
            flight_segment_departure_dates=model.flight_segment_departure_dates,
            ticket_status_history=_to_ticket_status_history_response(
                model.ticket_status_history
            ),
            hotel_reference_number=model.hotel_reference_number,
            hotel_image_url=model.hotel_image_url,
            hotel_name=model.hotel_name,
            hotel_city=model.hotel_city,
            hotel_address=model.hotel_address,
            hotel_latitude=model.hotel_latitude,
            hotel_longitude=model.hotel_longitude,
            hotel_check_in_date=model.hotel_check_in_date,
            hotel_check_out_date=model.hotel_check_out_date,
            hotel_nights=model.hotel_nights,
            saved_itinerary_id=str(model.saved_itinerary_id)
            if model.saved_itinerary_id is not None
            else None,
            parent_voya_booking_reference=model.parent_voya_booking_reference,
            multistay_leg_index=model.multistay_leg_index,
            voucher_redemption_id=model.voucher_redemption_id,
            voucher_discount_amount=model.voucher_discount_amount,
        )

    @staticmethod
    async def set_booking_payload(voya_booking_reference: str, payload: dict) -> None:
        """Store FlightLogic booking API payload on an existing event (LCC: before calling API).

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            payload: Exact dict sent to FlightLogic booking endpoint (DTO model_dump(by_alias=True))

        Raises:
            ValueError: If booking not found
        """
        db = await get_database()
        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {"voya_booking_reference": voya_booking_reference},
            {"$set": {"payload": payload}},
        )
        if result.matched_count == 0:
            raise ValueError(f"Booking not found: {voya_booking_reference}")
        logger.info(
            f"Stored booking payload for {voya_booking_reference} ({len(str(payload))} chars)"
        )

    @staticmethod
    async def update_external_reference(
        voya_booking_reference: str, external_booking_reference: str
    ) -> None:
        """Update external_booking_reference on an existing event (e.g. hotel: after book API succeeds).

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            external_booking_reference: New value (e.g. supplier_confirmation_num for hotel)

        Raises:
            ValueError: If booking not found
        """
        db = await get_database()
        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {"voya_booking_reference": voya_booking_reference},
            {"$set": {"external_booking_reference": external_booking_reference}},
        )
        if result.matched_count == 0:
            raise ValueError(f"Booking not found: {voya_booking_reference}")
        logger.info(
            f"Updated external_booking_reference for {voya_booking_reference} → {external_booking_reference[:20]}..."
        )

    @staticmethod
    async def update_hotel_reference_number(
        voya_booking_reference: str, hotel_reference_number: str
    ) -> None:
        """Update hotel_reference_number on an existing hotel booking event.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            hotel_reference_number: referenceNum from hotel book API response

        Raises:
            ValueError: If booking not found
        """
        db = await get_database()
        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {"voya_booking_reference": voya_booking_reference},
            {"$set": {"hotel_reference_number": hotel_reference_number}},
        )
        if result.matched_count == 0:
            raise ValueError(f"Booking not found: {voya_booking_reference}")
        logger.info(
            f"Updated hotel_reference_number for {voya_booking_reference} → {hotel_reference_number[:20]}..."
        )

    @staticmethod
    async def get_event_by_id(booking_event_id: str) -> BookingEventModel | None:
        """Get a booking event by MongoDB _id (internal use e.g. admin retry). Includes payload."""
        db = await get_database()
        try:
            doc = await db[BOOKING_EVENT_COLLECTION].find_one(
                {"_id": ObjectId(booking_event_id)}
            )
        except Exception:
            return None
        if not doc:
            return None
        return BookingEventModel(**doc)

    @staticmethod
    async def get_latest_booking(
        external_booking_reference: str,
    ) -> BookingEventResponse | None:
        """Get the latest booking by external reference."""
        db = await get_database()

        # Find the most recent booking for this external reference
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"external_booking_reference": external_booking_reference},
            sort=[("timestamp", -1)],
        )

        if not booking_doc:
            return None

        model = BookingEventModel(**booking_doc)
        return _booking_event_model_to_response(model)

    @staticmethod
    async def get_event_by_voya_reference(
        voya_booking_reference: str,
    ) -> BookingEventModel | None:
        """Get the latest booking event by VOYA reference (full model including payload, for admin)."""
        db = await get_database()
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voya_booking_reference": voya_booking_reference},
            sort=[("timestamp", -1)],
        )
        if not booking_doc:
            return None
        return BookingEventModel(**booking_doc)

    @staticmethod
    async def get_latest_booking_event_with_voucher_for_voya(
        voya_booking_reference: str,
    ) -> BookingEventModel | None:
        """Latest booking row that carries a G2A voucher, for a VOYA or multicity group ref.

        ``get_event_by_voya_reference`` only sorts by time; a newer row for the same VOYA
        (e.g. HOTEL follow-up) may omit ``voucher_redemption_id`` and would block redemption.
        This query only matches events that have a non-empty ``voucher_redemption_id``,
        and also checks ``parent_voya_booking_reference`` so a payment webhook carrying the
        group VOYA still finds a leg row with the voucher.
        """
        db = await get_database()
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {
                "voucher_redemption_id": {"$exists": True, "$nin": [None, ""]},
                "$or": [
                    {"voya_booking_reference": voya_booking_reference},
                    {"parent_voya_booking_reference": voya_booking_reference},
                ],
            },
            sort=[("timestamp", -1)],
        )
        if not booking_doc:
            return None
        return BookingEventModel(**booking_doc)

    @staticmethod
    async def get_latest_booking_event_by_voucher_redemption_id(
        voucher_redemption_id: str,
    ) -> BookingEventModel | None:
        """Latest booking row that references this G2A redemption id (apply idempotency vs booking)."""
        db = await get_database()
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voucher_redemption_id": voucher_redemption_id},
            sort=[("timestamp", -1)],
        )
        if not booking_doc:
            return None
        return BookingEventModel(**booking_doc)

    @staticmethod
    async def get_parent_voya_booking_reference_for_leg(
        voya_booking_reference: str,
    ) -> str | None:
        """Return multicity group reference when ``voya_booking_reference`` is a leg row."""
        event = await BookingService.get_event_by_voya_reference(voya_booking_reference)
        if not event or not event.parent_voya_booking_reference:
            return None
        return event.parent_voya_booking_reference

    @staticmethod
    async def release_voucher_for_booking_if_any(
        user_id: str,
        voya_booking_reference: str,
    ) -> None:
        """Release a reserved G2A voucher when payment fails or booking is cancelled."""
        from app.domains.discount.service import discount_service

        await discount_service.release_voucher_for_booking_reference(
            user_id=user_id,
            voya_booking_reference=voya_booking_reference,
        )

    @staticmethod
    async def get_latest_booking_by_voya_reference(
        voya_booking_reference: str,
    ) -> BookingEventResponse | None:
        """Get the latest booking by VOYA reference."""
        db = await get_database()

        # Find the most recent booking for this VOYA reference
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voya_booking_reference": voya_booking_reference},
            sort=[("timestamp", -1)],
        )

        if not booking_doc:
            return None

        model = BookingEventModel(**booking_doc)
        return _booking_event_model_to_response(model)

    @staticmethod
    async def get_latest_booking_by_parent_voya_reference(
        parent_voya_booking_reference: str,
    ) -> BookingEventResponse | None:
        """Latest flight leg booking whose ``parent_voya_booking_reference`` matches (multicity group id)."""
        db = await get_database()
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"parent_voya_booking_reference": parent_voya_booking_reference},
            sort=[("timestamp", -1)],
        )
        if not booking_doc:
            return None
        model = BookingEventModel(**booking_doc)
        return _booking_event_model_to_response(model)

    @staticmethod
    async def get_external_reference(voya_booking_reference: str) -> str:
        """Convert VOYA reference to FlightLogic external reference.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format

        Returns:
            FlightLogic external_booking_reference (UniqueID)

        Raises:
            ValueError: If booking not found
        """
        db = await get_database()

        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voya_booking_reference": voya_booking_reference}, sort=[("timestamp", -1)]
        )

        if not booking_doc:
            logger.error(
                f"Booking not found for VOYA reference: {voya_booking_reference}"
            )
            raise ValueError(f"Booking not found: {voya_booking_reference}")

        external_ref = booking_doc.get("external_booking_reference")
        if not external_ref:
            logger.error(
                f"Missing external_booking_reference for {voya_booking_reference}"
            )
            raise ValueError(f"Invalid booking data for {voya_booking_reference}")

        logger.debug(f"Converted {voya_booking_reference} → {external_ref}")
        return external_ref

    @staticmethod
    async def update_booking_after_flight_confirmation(
        voya_booking_reference: str,
        external_booking_reference: str,
        *,
        airline_pnr_code: str | None = None,
        airline_pnr_airline_code: str | None = None,
        airline_pnr_airline_name: str | None = None,
        airline_pnr_status: str | None = None,
        cancellation_policy_text: str | None = None,
        ticket_time_limit: datetime | None = None,
        departure_airport_iata: str | None = None,
        flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = None,
        route_legs: list[Any] | None = None,
        primary_marketing_airline_name: str | None = None,
        date_booked: datetime | None = None,
        date_tickets_issued: datetime | None = None,
        amount: float | None = None,
        saved_itinerary_id: ObjectId | None = None,
    ) -> None:
        """Update an LCC booking event with FlightLogic data after booking API succeeds.

        Only updates the document when external_booking_reference is TEMP-REF
        (created after payment, before booking API).

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            external_booking_reference: Real FlightLogic UniqueID from booking response
            airline_pnr_code: PNR code from booking response
            airline_pnr_airline_code: Airline IATA code
            airline_pnr_airline_name: Airline name
            airline_pnr_status: PNR status
            cancellation_policy_text: From fare rules
            ticket_time_limit: UTC ticket time limit
            departure_airport_iata: Departure airport IATA for timezone conversion
            date_booked: UTC when booking API succeeded (LCC)
            date_tickets_issued: UTC when tickets issued (LCC = same as booking)
            amount: Total original amount
            saved_itinerary_id: Set when booking succeeds and client linked a saved itinerary (LCC)
        """
        db = await get_database()
        update: dict = {"external_booking_reference": external_booking_reference}
        if airline_pnr_code is not None:
            update["airline_pnr_code"] = airline_pnr_code
        if airline_pnr_airline_code is not None:
            update["airline_pnr_airline_code"] = airline_pnr_airline_code
        if airline_pnr_airline_name is not None:
            update["airline_pnr_airline_name"] = airline_pnr_airline_name
        if airline_pnr_status is not None:
            update["airline_pnr_status"] = airline_pnr_status
        if cancellation_policy_text is not None:
            update["cancellation_policy_text"] = cancellation_policy_text
        if ticket_time_limit is not None:
            update["ticket_time_limit"] = ticket_time_limit
        if departure_airport_iata is not None:
            update["departure_airport_iata"] = departure_airport_iata
        if flight_trip_type is not None:
            update["flight_trip_type"] = flight_trip_type
        if route_legs is not None:
            update["route_legs"] = route_legs
        if primary_marketing_airline_name is not None:
            update["primary_marketing_airline_name"] = primary_marketing_airline_name
        if date_booked is not None:
            update["date_booked"] = date_booked
        if date_tickets_issued is not None:
            update["date_tickets_issued"] = date_tickets_issued
        if amount is not None:
            update["amount"] = amount
        if saved_itinerary_id is not None:
            update["saved_itinerary_id"] = saved_itinerary_id

        mongo_ops: dict[str, Any] = {"$set": update}
        if route_legs is not None:
            mongo_ops["$unset"] = {
                "arrival_airport_iata": "",
                "return_departure_airport_iata": "",
                "return_arrival_airport_iata": "",
            }

        # Require LCC + BOOKED so we never patch a stray PENDING GDS row that also matched TEMP-REF
        # (voucher LCC used to create both).
        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {
                "voya_booking_reference": voya_booking_reference,
                "external_booking_reference": TEMP_EXTERNAL_REF,
                "carrier_type": "LCC",
                "action": "BOOKED",
            },
            mongo_ops,
        )
        if result.modified_count > 0:
            logger.info(
                f"Updated LCC booking {voya_booking_reference} with external ref {external_booking_reference}"
            )
        else:
            logger.debug(
                f"No update for {voya_booking_reference} (not LCC BOOKED + TEMP-REF or not found)"
            )

    @staticmethod
    async def create_pending_gds_event(
        user_id: str,
        voya_booking_reference: str,
        payment_intent_id: str,
        *,
        contact_email: str | None = None,
        amount: float | None = None,
        voucher_redemption_id: str | None = None,
    ) -> BookingEventResponse:
        """Create a PENDING GDS booking event after Revolut order creation.

        Used when user clicks "Continue to Payment" on Review page (before Booking API).
        Event has external_booking_reference=TEMP-REF; updated to BOOKED when
        Booking API succeeds on Pay Now.

        Args:
            user_id: User ID who owns the booking
            voya_booking_reference: VOYA-XXXXXXXXXX (generated before create-order)
            payment_intent_id: Revolut order ID (order_id from create_order response)
            contact_email: Contact email for email routing
            amount: Total amount (optional)

        Returns:
            BookingEventResponse for the created event
        """
        payload: dict[str, Any] = {
            "external_booking_reference": TEMP_EXTERNAL_REF,
            "action": "PENDING",
            "event_type": "FLIGHT",
            "carrier_type": "GDS",
            "payment_intent_id": payment_intent_id,
            "voya_booking_reference": voya_booking_reference,
            "contact_email": contact_email,
            "amount": amount,
        }
        if voucher_redemption_id:
            payload["voucher_redemption_id"] = voucher_redemption_id
        request = CreateBookingEventRequest.model_validate(payload)
        service = BookingService(user_id)
        return await service.create_booking(request)

    @staticmethod
    async def update_gds_pending_booking_after_api(
        voya_booking_reference: str,
        external_booking_reference: str,
        *,
        airline_pnr_code: str | None = None,
        airline_pnr_airline_code: str | None = None,
        airline_pnr_airline_name: str | None = None,
        airline_pnr_status: str | None = None,
        cancellation_policy_text: str | None = None,
        ticket_time_limit: datetime | None = None,
        departure_airport_iata: str | None = None,
        flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = None,
        route_legs: list[Any] | None = None,
        primary_marketing_airline_name: str | None = None,
        payload: dict | None = None,
        date_booked: datetime | None = None,
        date_tickets_issued: datetime | None = None,
        amount: float | None = None,
        saved_itinerary_id: ObjectId | None = None,
    ) -> None:
        """Update a GDS PENDING booking event with FlightLogic data after Booking API succeeds.

        Called when user clicks "Pay Now" on Payment page and FlightLogic create_booking
        succeeds. Updates TEMP-REF event to real external_ref and action=BOOKED.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            external_booking_reference: Real FlightLogic UniqueID from booking response
            airline_pnr_code: PNR code from booking response
            airline_pnr_airline_code: Airline IATA code
            airline_pnr_airline_name: Airline name
            airline_pnr_status: PNR status
            cancellation_policy_text: From fare rules
            ticket_time_limit: UTC ticket time limit
            departure_airport_iata: Departure airport IATA for timezone conversion
            payload: FlightLogic booking API payload (for admin retry)
            date_booked: UTC when booking API succeeded
            date_tickets_issued: UTC aligned with LCC path when booking API records issuance time
            amount: Total original amount
            saved_itinerary_id: Optional link to saved itinerary when client provided it

        Raises:
            GdsPendingBookingSyncError: If no document matched the filter (nothing to update).

        Idempotency: A second call after a successful update will usually match ``matched_count == 0``
        (row is already ``BOOKED`` with a real external ref). If Mongo applies an update that
        matches but leaves the document bitwise unchanged, ``matched_count > 0`` and
        ``modified_count == 0`` — we still treat that as success.
        """
        update: dict = {
            "external_booking_reference": external_booking_reference,
            "action": "BOOKED",
        }
        if airline_pnr_code is not None:
            update["airline_pnr_code"] = airline_pnr_code
        if airline_pnr_airline_code is not None:
            update["airline_pnr_airline_code"] = airline_pnr_airline_code
        if airline_pnr_airline_name is not None:
            update["airline_pnr_airline_name"] = airline_pnr_airline_name
        if airline_pnr_status is not None:
            update["airline_pnr_status"] = airline_pnr_status
        if cancellation_policy_text is not None:
            update["cancellation_policy_text"] = cancellation_policy_text
        if ticket_time_limit is not None:
            update["ticket_time_limit"] = ticket_time_limit
        if departure_airport_iata is not None:
            update["departure_airport_iata"] = departure_airport_iata
        if flight_trip_type is not None:
            update["flight_trip_type"] = flight_trip_type
        if route_legs is not None:
            update["route_legs"] = route_legs
        if primary_marketing_airline_name is not None:
            update["primary_marketing_airline_name"] = primary_marketing_airline_name
        if payload is not None:
            update["payload"] = payload
        if date_booked is not None:
            update["date_booked"] = date_booked
        if date_tickets_issued is not None:
            update["date_tickets_issued"] = date_tickets_issued
        elif date_booked is not None:
            update["date_tickets_issued"] = date_booked
        if amount is not None:
            update["amount"] = amount
        if saved_itinerary_id is not None:
            update["saved_itinerary_id"] = saved_itinerary_id

        unset_legacy: dict[str, str] | None = None
        if route_legs is not None:
            unset_legacy = {
                "arrival_airport_iata": "",
                "return_departure_airport_iata": "",
                "return_arrival_airport_iata": "",
            }

        repo = BookingRepository()
        result = await repo.update_gds_pending_booking_to_booked(
            voya_booking_reference, update, unset_legacy
        )
        if result.matched_count == 0:
            logger.error(
                f"GDS PENDING booking update failed for {voya_booking_reference} "
                f"(not PENDING/TEMP-REF/GDS or not found); supplier booking may exist without Voya sync"
            )
            raise GdsPendingBookingSyncError(
                "Could not update your booking record after the supplier confirmed the reservation. "
                "Please contact support and do not retry payment until the issue is resolved."
            )
        if result.modified_count > 0:
            logger.info(
                f"Updated GDS PENDING booking {voya_booking_reference} to BOOKED "
                f"with external ref {external_booking_reference}"
            )
        else:
            logger.info(
                f"GDS PENDING booking {voya_booking_reference} update matched but made no field "
                f"changes (idempotent or duplicate apply); external ref {external_booking_reference}"
            )

    @staticmethod
    async def validate_user_owns_booking(
        voya_booking_reference: str, user_id: str
    ) -> None:
        """Security check: Verify user owns this booking.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            user_id: User ID to validate

        Raises:
            ValueError: If booking not found
            BookingForbiddenError: If user doesn't own the booking
        """
        db = await get_database()

        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voya_booking_reference": voya_booking_reference}, sort=[("timestamp", -1)]
        )

        if not booking_doc:
            logger.warning(f"Booking not found: {voya_booking_reference}")
            raise ValueError(f"Booking not found: {voya_booking_reference}")

        # Convert ObjectId to string for comparison
        booking_user_id = str(booking_doc.get("user_id"))
        if booking_user_id != user_id:
            logger.warning(
                f"Unauthorized access attempt: user {user_id} tried to access "
                f"booking {voya_booking_reference} owned by {booking_user_id}"
            )
            raise BookingForbiddenError("You do not have access to this booking")

        logger.debug(f"User {user_id} authorized for booking {voya_booking_reference}")

    @staticmethod
    def _doc_to_multicity_leg(doc: Mapping[str, Any]) -> MulticityLegBookingSummaryItem:
        ref = doc.get("voya_booking_reference")
        if not ref:
            logger.warning(
                "Multicity leg document missing voya_booking_reference (id=%s)",
                doc.get("_id"),
            )
            raise ValueError("Booking event document missing voya_booking_reference")
        dep_raw = doc.get("departure_airport_iata")
        dep = (
            departure_iata_from_route_legs_raw(doc.get("route_legs"))
            if doc.get("route_legs")
            else None
        )
        if dep is None and isinstance(dep_raw, str):
            dep = dep_raw.strip().upper() if len(dep_raw.strip()) == 3 else None
        return MulticityLegBookingSummaryItem(
            voya_booking_reference=ref,
            external_booking_reference=doc.get("external_booking_reference"),
            ticket_status=doc.get("ticket_status"),
            departure_airport_iata=dep,
            flight_trip_type=_flight_trip_type_from_value(doc.get("flight_trip_type")),
            route_legs=parse_route_legs_from_document(
                doc.get("route_legs"),
                booking_id=str(doc.get("_id")) if doc.get("_id") is not None else None,
            ),
        )

    @staticmethod
    async def list_multicity_group_for_voya_reference(
        user_id: str,
        voya_booking_reference: str,
    ) -> MulticityBookingGroupResponse:
        """Return this booking plus sibling legs when part of a multicity group.

        Caller must have already validated JWT; enforces ownership via
        ``validate_user_owns_booking``.
        """
        await BookingService.validate_user_owns_booking(voya_booking_reference, user_id)
        db = await get_database()
        coll = db[BOOKING_EVENT_COLLECTION]
        base_doc = await coll.find_one(
            {"voya_booking_reference": voya_booking_reference},
            sort=[("timestamp", -1)],
        )
        if not base_doc:
            raise ValueError(f"Booking not found: {voya_booking_reference}")

        parent = base_doc.get("parent_voya_booking_reference")
        if not parent:
            return MulticityBookingGroupResponse(
                parent_voya_booking_reference=None,
                legs=[BookingService._doc_to_multicity_leg(base_doc)],
            )

        try:
            oid = ObjectId(user_id)
        except InvalidId as e:
            raise ValueError(
                f"Invalid user id for multicity group query: {user_id!r}"
            ) from e
        cursor = coll.find(
            {
                "user_id": oid,
                "event_type": "FLIGHT",
                "parent_voya_booking_reference": parent,
            }
        ).sort("timestamp", 1)
        raw_legs = await cursor.to_list(length=MAX_MULTICITY_LEGS)
        by_ref: dict[str, Mapping[str, Any]] = {}
        for doc in raw_legs:
            ref = doc.get("voya_booking_reference") or ""
            if not ref:
                continue
            prev = by_ref.get(ref)
            ts = doc.get("timestamp")
            if prev is None:
                by_ref[ref] = doc
                continue
            prev_ts = prev.get("timestamp")
            if (ts and prev_ts and ts >= prev_ts) or (ts and not prev_ts):
                by_ref[ref] = doc
        leg_docs = sorted(by_ref.values(), key=_multistay_leg_sort_key)
        return MulticityBookingGroupResponse(
            parent_voya_booking_reference=parent,
            legs=[BookingService._doc_to_multicity_leg(d) for d in leg_docs],
        )

    @staticmethod
    async def get_voya_reference_by_payment_intent_id(
        payment_intent_id: str,
    ) -> str | None:
        """Return voya_booking_reference for the booking with this payment_intent_id (Stripe pi_xxx or Revolut order id).

        Used by payment webhooks when metadata is missing (e.g. Revolut may not return metadata in webhook payload).
        """
        db = await get_database()
        doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"payment_intent_id": payment_intent_id},
            sort=[("timestamp", -1)],
            projection={"voya_booking_reference": 1},
        )
        return doc.get("voya_booking_reference") if doc else None

    @staticmethod
    async def update_payment_intent_id(
        voya_booking_reference: str, payment_intent_id: str
    ) -> None:
        """Update payment_intent_id for a booking event.

        Used when a payment intent is created for a booking, so it can be reused
        if the user returns via email link.

        Args:
            voya_booking_reference: VOYA-XXXXXXXXXX format
            payment_intent_id: Stripe payment intent ID (pi_xxx)

        Raises:
            ValueError: If booking not found
        """
        db = await get_database()

        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {"voya_booking_reference": voya_booking_reference},
            {"$set": {"payment_intent_id": payment_intent_id}},
        )

        if result.matched_count == 0:
            result = await db[BOOKING_EVENT_COLLECTION].update_many(
                {"parent_voya_booking_reference": voya_booking_reference},
                {"$set": {"payment_intent_id": payment_intent_id}},
            )
            if result.matched_count == 0:
                logger.warning(
                    f"Booking not found for payment intent update: {voya_booking_reference}"
                )
                raise ValueError(f"Booking not found: {voya_booking_reference}")
            if result.modified_count > 0:
                logger.info(
                    f"Updated payment_intent_id for multicity group {voya_booking_reference} "
                    f"({result.modified_count} leg(s)) → {payment_intent_id}"
                )
            else:
                logger.debug(
                    f"Payment intent ID already set for multicity group {voya_booking_reference}"
                )
            return

        if result.modified_count > 0:
            logger.info(
                f"Updated payment_intent_id for {voya_booking_reference} → {payment_intent_id}"
            )
        else:
            logger.debug(f"Payment intent ID already set for {voya_booking_reference}")

    @staticmethod
    async def apply_date_paid_from_completed_payment(
        voya_booking_reference: str,
        payment_id: str,
        *,
        flight_amount: float | None = None,
    ) -> None:
        """Set ``date_paid`` on a leg when payment already succeeded in Mongo.

        Stripe webhooks key on ``payment_intent_id``; Revolut webhooks may run before
        multicity leg rows exist, so parent fan-out can no-op. This reconciles when the
        leg booking event is persisted (LCC after confirmation, GDS after insert).
        """
        date_paid: datetime | None = None
        amount_minor: int | None = None

        try:
            payment_repo = PaymentRepository()
            txn = await payment_repo.get_transaction_by_payment_intent(payment_id)
            if (
                txn
                and getattr(txn, "paid_at", None)
                and getattr(txn, "status", None) == PaymentStatus.SUCCEEDED
            ):
                date_paid = txn.paid_at
                amount_minor = txn.amount
        except Exception as e:
            logger.warning(
                "Stripe transaction lookup failed for date_paid reconcile: %s",
                e,
            )

        if date_paid is None:
            try:
                revolut_repo = RevolutPaymentRepository()
                rtxn = await revolut_repo.get_transaction_by_order_id(payment_id)
                if (
                    rtxn
                    and getattr(rtxn, "paid_at", None)
                    and getattr(rtxn, "status", None) == PaymentStatus.SUCCEEDED
                ):
                    date_paid = rtxn.paid_at
                    amount_minor = rtxn.amount
            except Exception as e:
                logger.warning(
                    "Revolut transaction lookup failed for date_paid reconcile: %s",
                    e,
                )

        if date_paid is None:
            return

        await BookingService.update_booking_dates_and_flags(
            voya_booking_reference,
            date_paid=date_paid,
            amount=(
                (amount_minor / 100.0)
                if flight_amount is None and amount_minor is not None
                else None
            ),
        )

    @staticmethod
    async def update_booking_dates_and_flags(
        voya_booking_reference: str,
        *,
        date_booked: datetime | None = None,
        date_paid: datetime | None = None,
        date_tickets_issued: datetime | None = None,
        amount: float | None = None,
        confirmation_email_sent: bool | None = None,
        hotel_check_in_date: str | None = None,
        hotel_check_out_date: str | None = None,
        hotel_nights: int | None = None,
        saved_itinerary_id: ObjectId | None = None,
    ) -> None:
        """Update date and flag fields on a booking event (by VOYA reference).

        Only updates fields that are passed as non-None. Used for date_paid (payment
        webhook), date_tickets_issued (GDS after issue_tickets), amount, and
        confirmation_email_sent (after email sent). HOTEL stay fields are set from
        book response or refreshed from get_booking_details.
        """
        db = await get_database()
        update: dict = {}
        if date_booked is not None:
            update["date_booked"] = date_booked
        if date_paid is not None:
            update["date_paid"] = date_paid
        if date_tickets_issued is not None:
            update["date_tickets_issued"] = date_tickets_issued
        if amount is not None:
            update["amount"] = amount
        if confirmation_email_sent is not None:
            update["confirmation_email_sent"] = confirmation_email_sent
        if hotel_check_in_date is not None:
            update["hotel_check_in_date"] = hotel_check_in_date
        if hotel_check_out_date is not None:
            update["hotel_check_out_date"] = hotel_check_out_date
        if hotel_nights is not None and hotel_nights > 0:
            update["hotel_nights"] = hotel_nights
        if saved_itinerary_id is not None:
            update["saved_itinerary_id"] = saved_itinerary_id
        if not update:
            return
        # Prefer the latest event for this VOYA ref so payment webhooks align with get_latest /
        # get_external_reference when duplicate rows ever exist.
        booking_doc = await db[BOOKING_EVENT_COLLECTION].find_one(
            {"voya_booking_reference": voya_booking_reference},
            sort=[("timestamp", -1)],
        )
        if booking_doc:
            result = await db[BOOKING_EVENT_COLLECTION].update_one(
                {"_id": booking_doc["_id"]},
                {"$set": update},
            )
            if result.matched_count == 0:
                logger.warning(
                    f"Booking not found for dates/flags update: {voya_booking_reference}"
                )
            return

        result = await db[BOOKING_EVENT_COLLECTION].update_many(
            {"parent_voya_booking_reference": voya_booking_reference},
            {"$set": update},
        )
        if result.matched_count == 0:
            logger.warning(
                f"Booking not found for dates/flags update: {voya_booking_reference}"
            )

    @staticmethod
    async def update_booking_pnr(voya_booking_reference: str, pnr: list[str]) -> None:
        """Update PNR list on a booking event from trip details API (flights only).

        Called when trip details are received: LCC after booking API + trip details;
        GDS after ticket issue API + trip details.
        """
        await BookingService.update_booking_trip_details_sync(
            voya_booking_reference, pnr=pnr
        )

    @staticmethod
    async def update_booking_trip_details_sync(
        voya_booking_reference: str,
        *,
        pnr: list[str] | None = None,
        ticket_status: str | None = None,
        ticket_status_snapshot_time: datetime | None = None,
        e_ticket_numbers: list[str] | None = None,
        departure_airport_iata: str | None = None,
        flight_trip_type: str | None = None,
        route_legs: list[Any] | None = None,
        primary_marketing_airline_name: str | None = None,
        flight_leg_summaries: list[dict[str, Any]] | None = None,
        flight_segment_departure_dates: list[str] | None = None,
    ) -> None:
        """Persist the latest non-empty trip-details-derived booking fields.

        When ticket_status is present, appends a snapshot to ticket_status_history
        (using ticket_status_snapshot_time or now) and updates the scalar ticket_status.

        Route and airline snapshot fields from trip details overwrite prior Mongo values when
        provided (authoritative refresh after a successful trip-details fetch).
        """
        set_update: dict[str, Any] = {}
        if pnr:
            set_update["pnr"] = pnr
        if ticket_status:
            set_update["ticket_status"] = ticket_status
        if e_ticket_numbers:
            set_update["e_ticket_numbers"] = e_ticket_numbers
        if departure_airport_iata:
            set_update["departure_airport_iata"] = departure_airport_iata
        if flight_trip_type:
            set_update["flight_trip_type"] = flight_trip_type
        if route_legs is not None:
            set_update["route_legs"] = route_legs
        if primary_marketing_airline_name:
            set_update["primary_marketing_airline_name"] = (
                primary_marketing_airline_name
            )
        if flight_leg_summaries:
            set_update["flight_leg_summaries"] = flight_leg_summaries
        if flight_segment_departure_dates:
            set_update["flight_segment_departure_dates"] = (
                flight_segment_departure_dates
            )

        push_update: dict[str, dict[str, str | datetime]] = {}
        if ticket_status:
            snapshot_time = ticket_status_snapshot_time or datetime.now(UTC)
            push_update["ticket_status_history"] = {
                "status": ticket_status,
                "time": snapshot_time,
            }

        if not set_update and not push_update:
            return

        ops: dict[str, Any] = {}
        if set_update:
            ops["$set"] = set_update
        if push_update:
            ops["$push"] = push_update
        if route_legs is not None:
            ops["$unset"] = {
                "arrival_airport_iata": "",
                "return_departure_airport_iata": "",
                "return_arrival_airport_iata": "",
            }

        db = await get_database()
        result = await db[BOOKING_EVENT_COLLECTION].update_one(
            {"voya_booking_reference": voya_booking_reference},
            ops,
        )
        if result.matched_count == 0:
            logger.warning(
                f"Booking not found for trip-details sync: {voya_booking_reference}"
            )
        else:
            updated_keys = list(set_update.keys()) + list(push_update.keys())
            logger.info(
                "Updated trip-details sync fields for %s: %s",
                voya_booking_reference,
                ", ".join(updated_keys),
            )

    @staticmethod
    async def list_all_events(
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BookingEventResponse], int]:
        """List all booking events (admin only). Sorted by timestamp descending.

        Returns:
            Tuple of (list of booking event responses, total count).
        """
        db = await get_database()
        coll = db[BOOKING_EVENT_COLLECTION]
        total = await coll.count_documents({})
        cursor = coll.find({}).sort("timestamp", -1).skip(offset).limit(limit)
        events: list[BookingEventResponse] = []
        async for doc in cursor:
            try:
                events.append(booking_document_to_response(dict(doc)))
            except MalformedBookingEventDocumentError as e:
                logger.warning("Skipping booking event row in admin list: %s", e)
        return events, total

    def _model_to_response(self, model: BookingEventModel) -> BookingEventResponse:
        """Convert simplified database model to response."""
        return _booking_event_model_to_response(model)
