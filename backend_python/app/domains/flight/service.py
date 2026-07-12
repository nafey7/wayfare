"""Flight service - simplified and clean following domain patterns."""

import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends
from pydantic import ValidationError

from app.core.config import settings
from app.database.dependencies import get_database
from app.database.flight_route import departure_iata_from_route_legs
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.exceptions import InvalidTokenError
from app.domains.bookings import BookingService, CreateBookingEventRequest
from app.domains.bookings.constants import TEMP_EXTERNAL_REF
from app.domains.bookings.exceptions import (
    BookingForbiddenError,
    GdsClientReferenceConflictError,
    GdsPendingBookingSyncError,
    MalformedBookingEventDocumentError,
)
from app.domains.bookings.schemas import (
    BookingEventResponse,
    MulticityBookingGroupResponse,
)
from app.domains.bookings.service import booking_document_to_response
from app.domains.bookings.user_id_mongo_filter import booking_events_user_id_filter
from app.domains.common import ErrorDetails
from app.domains.payment.exceptions import PaymentValidationError
from app.domains.revolut_payment.exceptions import RevolutPaymentValidationError
from app.domains.saved_itinerary import ensure_saved_itinerary_owned_by_user
from app.shared.slack_notify import notify_booking_error
from integrations.flightlogic import get_flights_client

from ..user import UserPublic
from ..user.enums import UserRole
from .cache import AirlineListCache, AirportListCache, RevalidateCache
from .enums import JourneyType, TicketStatus
from .events import FlightEventHandler
from .exceptions import (
    FlightBookingError,
    FlightBookingSupplierSyncError,
    FlightSearchError,
    PaymentRequiredError,
)
from .filters import filter_flight_results
from .leg_summaries import (
    flight_leg_summaries_from_segments,
    flight_segment_departure_dates_iso,
)
from .logger import FlightLogger
from .pricing import apply_platform_fee_to_fare_totals
from .revalidation_filters import get_flight_ids_to_remove_after_revalidation
from .route_snapshot import (
    extract_route_and_airline_snapshot,
    extract_route_fields_from_trip_details,
)
from .schemas import (
    AdultPassenger,
    AirlineListRequest,
    AirlineListResponse,
    AirportListRequest,
    AirportListResponse,
    ChildPassenger,
    FlightBookingRequest,
    FlightBookingResponse,
    FlightCancelRequest,
    FlightCancelResponse,
    FlightExtraServicesRequest,
    FlightExtraServicesResponse,
    FlightFareRulesRequest,
    FlightFareRulesResponse,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchFilters,
    FlightSearchRequest,
    FlightSearchResponse,
    InfantPassenger,
    MulticityLegSearchResult,
    PassengerGroups,
    TicketOrderRequest,
    TicketOrderResponse,
    TravelDocuments,
    TripDetailsFlightSegment,
    TripDetailsRequest,
    TripDetailsResponse,
)
from .validation import validate_ticket_time_limit
from .validators import (
    validate_age_requirements,
    validate_infant_adult_pairing,
    validate_required_fields_to_book,
)

logger = logging.getLogger(__name__)

# Strong references for fire-and-forget tasks (prevents GC before completion)
_trip_details_notify_tasks: set[asyncio.Task[None]] = set()


def _filters_for_multicity_leg(
    request: FlightSearchRequest, leg_index: int
) -> FlightSearchFilters | None:
    """Map Circle journey_filters to a single-leg OneWay request (semantic leg 0)."""
    if request.filters is None:
        return None
    base = request.filters
    jlist = base.journey_filters
    if jlist and leg_index < len(jlist):
        leg_jf = jlist[leg_index]
        adjusted = leg_jf.model_copy(update={"leg_index": 0})
        return base.model_copy(update={"journey_filters": [adjusted]})
    return base.model_copy(update={"journey_filters": None})


def _build_multicity_leg_search_request(
    request: FlightSearchRequest, leg_index: int
) -> FlightSearchRequest:
    """Build a OneWay search for one Circle segment (parallel multicity orchestration)."""
    data = request.model_dump()
    data["journey_type"] = JourneyType.ONE_WAY
    data["origin_destination_info"] = [data["origin_destination_info"][leg_index]]
    leg_filters = _filters_for_multicity_leg(request, leg_index)
    data["filters"] = leg_filters.model_dump() if leg_filters else None
    return FlightSearchRequest.model_validate(data)


async def _resolve_saved_passengers(
    request: FlightBookingRequest, user_id: str
) -> FlightBookingRequest:
    """Resolve saved_passenger_id refs: fetch travel_documents from DB, merge, return new request."""
    from app.domains.passenger.repository import get_passenger_by_id
    from app.domains.passenger.schemas import PassengerResponse

    def _build_travel_docs(
        passport_number: str | None,
        passport_expiry: str | None,
        passport_country: str | None,
    ) -> TravelDocuments | None:
        if not passport_number or not passport_expiry or not passport_country:
            return None
        return TravelDocuments(
            passport_number=passport_number,
            passport_expiry=passport_expiry,
            passport_country=passport_country,
        )

    async def _resolve_passenger_list(
        passengers: list[AdultPassenger]
        | list[ChildPassenger]
        | list[InfantPassenger]
        | None,
    ):
        if not passengers:
            return None
        resolved = []
        for p in passengers:
            if p.saved_passenger_id:
                stored = await get_passenger_by_id(
                    p.saved_passenger_id, user_id, include_sensitive=True
                )
                if not stored or not isinstance(stored, PassengerResponse):
                    raise ValueError(
                        f"Saved passenger {p.saved_passenger_id} not found or access denied"
                    )
                td = _build_travel_docs(
                    stored.passport_number,
                    stored.passport_expiry,
                    stored.passport_country,
                )
                if td is None:
                    raise ValueError(
                        f"Saved passenger {p.saved_passenger_id} has incomplete or "
                        "unreadable travel documents"
                    )
                resolved.append(
                    p.model_copy(
                        update={"travel_documents": td, "saved_passenger_id": None}
                    )
                )
            else:
                resolved.append(p)
        return resolved

    adults = await _resolve_passenger_list(request.passenger_groups.adults)
    children = await _resolve_passenger_list(request.passenger_groups.children)
    infants = await _resolve_passenger_list(request.passenger_groups.infants)

    groups = PassengerGroups(adults=adults, children=children, infants=infants)
    return request.model_copy(update={"passenger_groups": groups})


# Simple in-memory cache for cancellation_policy_text by voya_booking_reference
# This is used when tickets are issued automatically after payment
_cancellation_policy_cache: dict[str, str] = {}


def _extract_pnrs_from_trip_details(
    trip_details: TripDetailsResponse | None,
) -> list[str]:
    """Extract unique PNR codes from trip details segments (order preserved).

    Each segment can have a different AirlinePNR; we dedupe while preserving order.
    """
    if not trip_details or not getattr(trip_details, "segments", None):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for seg in trip_details.segments:
        apnr = getattr(seg, "airline_pnr", None)
        code = getattr(apnr, "pnr_code", None) if apnr else None
        if code and code not in seen and code.upper() != "UNKNOWN":
            seen.add(code)
            result.append(code)
    return result


def _enum_or_scalar_str(value: Any) -> str:
    """Normalize enum-like fields from API responses or tests to a string."""
    if isinstance(value, str):
        return value
    inner = getattr(value, "value", None)
    if isinstance(inner, str):
        return inner
    return str(value)


def _is_ticketed_missing_pnr_or_eticket(trip_details: TripDetailsResponse) -> bool:
    """Return True if ticket_status is Ticketed but PNR or e-ticket are missing.

    Triggers a data-quality Slack notification when FlightLogic returns a ticketed
    booking without critical identifiers (PNR or e-ticket numbers).
    """
    if trip_details.ticket_status != TicketStatus.TICKETED:
        return False
    pnrs = _extract_pnrs_from_trip_details(trip_details)
    has_valid_pnr = bool(
        pnrs and any(p and p.upper() not in ("UNKNOWN", "PENDING") for p in pnrs)
    )
    has_eticket = any(
        p.e_ticket_number and str(p.e_ticket_number).strip()
        for p in (trip_details.passengers or [])
    )
    return not (has_valid_pnr and has_eticket)


def _extract_ticket_status_from_trip_details(
    trip_details: TripDetailsResponse | None,
) -> str | None:
    """Extract a normalized ticket status string from trip details."""
    if not trip_details:
        return None
    raw_ticket_status = getattr(trip_details, "ticket_status", None)
    if raw_ticket_status is None:
        return None
    value = getattr(raw_ticket_status, "value", raw_ticket_status)
    ticket_status = str(value).strip() if value is not None else ""
    return ticket_status or None


def _extract_e_ticket_numbers_from_trip_details(
    trip_details: TripDetailsResponse | None,
) -> list[str]:
    """Extract unique passenger e-ticket numbers from trip details."""
    if not trip_details or not getattr(trip_details, "passengers", None):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for passenger in trip_details.passengers:
        raw_number = getattr(passenger, "e_ticket_number", None)
        ticket_number = str(raw_number).strip() if raw_number is not None else ""
        if (
            ticket_number
            and ticket_number.upper() != "UNKNOWN"
            and ticket_number not in seen
        ):
            seen.add(ticket_number)
            result.append(ticket_number)
    return result


def _primary_destination_iata_from_trip_details(trip_details: object) -> str | None:
    """IATA from trip_details.destination (TravelItinerary.Destination); used to split RT legs."""
    dest = getattr(trip_details, "destination", None)
    if dest is None:
        return None
    code = getattr(dest, "iata_code", None)
    if code is None:
        return None
    normalized = str(code).strip().upper()
    return normalized if len(normalized) == 3 else None


def _extract_booking_sync_fields_from_trip_details(
    trip_details: TripDetailsResponse | None,
) -> dict[str, Any]:
    """Build booking fields that should be synchronized from trip details."""
    sync_fields: dict[str, Any] = {}
    pnrs = _extract_pnrs_from_trip_details(trip_details)
    ticket_status = _extract_ticket_status_from_trip_details(trip_details)
    e_ticket_numbers = _extract_e_ticket_numbers_from_trip_details(trip_details)
    if pnrs:
        sync_fields["pnr"] = pnrs
    if ticket_status:
        sync_fields["ticket_status"] = ticket_status
    if e_ticket_numbers:
        sync_fields["e_ticket_numbers"] = e_ticket_numbers
    try:
        sync_fields.update(extract_route_fields_from_trip_details(trip_details))
    except (AttributeError, TypeError, ValidationError) as e:
        logger.warning(
            "Could not derive route/airline snapshot from trip details: %s",
            e,
        )
    except Exception:
        logger.exception(
            "Unexpected error deriving route/airline snapshot from trip details",
        )
    if trip_details and getattr(trip_details, "segments", None):
        segs = list(trip_details.segments)
        if segs and all(isinstance(s, TripDetailsFlightSegment) for s in segs):
            sync_fields["flight_segment_departure_dates"] = (
                flight_segment_departure_dates_iso(segs)
            )
            primary_dest = _primary_destination_iata_from_trip_details(trip_details)
            legs = flight_leg_summaries_from_segments(
                segs, primary_destination_iata=primary_dest
            )
            if legs:
                sync_fields["flight_leg_summaries"] = [
                    leg.model_dump(mode="json") for leg in legs
                ]
    return sync_fields


class FlightService:
    """Instance-based flight service with user context for environment detection."""

    def __init__(self, current_user: "UserPublic | None" = None) -> None:
        """Initialize flight service with user context."""
        self.current_user = current_user
        self.client = get_flights_client(current_user)
        self._last_revalidate_response: FlightRevalidateResponse | None = None

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _get_base_log_context(self) -> dict[str, str]:
        """Get base logging context shared across all operations.

        Returns:
            Base context with environment and user_id (if authenticated)
        """
        context = {"environment": self.client.environment.value}
        if self.current_user:
            context["user_id"] = str(self.current_user.id)
        return context

    def _truncate_sensitive_code(self, code: str | None, max_len: int = 8) -> str:
        """Truncate sensitive codes for logging (PII/security protection)."""
        if not code:
            return "N/A"
        return code[:max_len] + "..." if len(code) > max_len else code

    async def _sync_booking_from_trip_details(
        self,
        voya_booking_reference: str,
        trip_details: TripDetailsResponse | None,
    ) -> None:
        """Synchronize normalized trip-details fields back into the booking record."""
        sync_fields = _extract_booking_sync_fields_from_trip_details(trip_details)
        if not sync_fields:
            return
        snapshot_time = datetime.now(UTC) if sync_fields.get("ticket_status") else None
        flight_leg_summaries = sync_fields.get("flight_leg_summaries")
        flight_segment_departure_dates = sync_fields.get(
            "flight_segment_departure_dates"
        )
        await BookingService.update_booking_trip_details_sync(
            voya_booking_reference,
            pnr=sync_fields.get("pnr"),
            ticket_status=sync_fields.get("ticket_status"),
            e_ticket_numbers=sync_fields.get("e_ticket_numbers"),
            ticket_status_snapshot_time=snapshot_time,
            route_legs=sync_fields.get("route_legs"),
            flight_trip_type=sync_fields.get("flight_trip_type"),
            departure_airport_iata=sync_fields.get("departure_airport_iata"),
            primary_marketing_airline_name=sync_fields.get(
                "primary_marketing_airline_name"
            ),
            flight_leg_summaries=flight_leg_summaries,
            flight_segment_departure_dates=flight_segment_departure_dates,
        )

    async def _ensure_external_reference(
        self, request: TicketOrderRequest | FlightCancelRequest | TripDetailsRequest
    ) -> str:
        """Ensure external_booking_reference is populated on request.

        If external_booking_reference is already set, returns it.
        Otherwise, converts voya_booking_reference to external reference and populates it.

        Args:
            request: Request object with voya_booking_reference

        Returns:
            External booking reference

        Raises:
            ValueError: If booking not found
        """
        if request.external_booking_reference:
            return request.external_booking_reference

        voya_ref = request.voya_booking_reference
        if not voya_ref:
            raise ValueError(
                "voya_booking_reference is required when external_booking_reference is not set"
            )

        external_ref = await BookingService.get_external_reference(voya_ref)
        request.external_booking_reference = external_ref
        return external_ref

    @staticmethod
    def _should_skip_ticket_order_for_gds(trip_details: TripDetailsResponse) -> bool:
        """Return True if ticket order API should be skipped (GDS already ticketed/cancelled).

        GDS ticket status gate: skip when fare_type.is_gds and ticket_status
        is TICKETED or CANCELLED.

        Note: ``issue_tickets`` returns earlier when ``ticket_status == TICKETED`` for any
        fare type, so this helper usually contributes the skip for **CANCELLED** GDS
        bookings; the TICKETED branch remains for clarity and if call order changes.
        """
        return trip_details.fare_type.is_gds and trip_details.ticket_status in (
            TicketStatus.TICKETED,
            TicketStatus.CANCELLED,
        )

    def _validate_payment_required(
        self,
        fare_type: str,
        payment_id: str | None,
        context_ref: str,
        log: FlightLogger,
    ) -> None:
        """Validate payment requirement based on fare type.

        GDS fares (Public/Private) require payment for ticketing.
        LCC fares (WebFare) require payment at booking time.
        """
        payment_required_fares = {
            "WebFare": "booking",
            "Public": "ticketing",
            "Private": "ticketing",
        }

        if fare_type in payment_required_fares and not payment_id:
            stage = payment_required_fares[fare_type]
            log.warning(
                f"Payment required for {fare_type} at {stage} stage",
                fare_type=fare_type,
                stage=stage,
                context=context_ref,
            )
            raise PaymentRequiredError(fare_type=fare_type)

    async def _enrich_airport_country_codes(
        self, response: TripDetailsResponse
    ) -> None:
        """Enrich airport info with country codes for accurate cross-border detection.

        This method updates the origin and destination airports with country codes
        from the comprehensive airport database, which is required for properly
        detecting international flights. Uses either airport_resolver (mwgg) or
        FlightService (FlightLogic) based on VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS.

        Args:
            response: Trip details response to enrich
        """
        from app.core.config import settings

        # Enrich origin airport
        if response.origin.iata_code:
            if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
                # Use FlightLogic data
                logger.debug(
                    f"Using FlightLogic API for origin airport enrichment: '{response.origin.iata_code}'"
                )
                airport_data = await self.get_airport_info(response.origin.iata_code)
            else:
                # Use mwgg data
                logger.debug(
                    f"Using mwgg/Airports for origin airport enrichment: '{response.origin.iata_code}'"
                )
                from app.domains.airport.airport_resolver import airport_resolver

                airport_data = await airport_resolver.get_airport_info(
                    response.origin.iata_code
                )
            if airport_data and airport_data.get("country"):
                response.origin.country_code = airport_data["country"]

        # Enrich destination airport
        if response.destination.iata_code:
            if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
                # Use FlightLogic data
                logger.debug(
                    f"Using FlightLogic API for destination airport enrichment: '{response.destination.iata_code}'"
                )
                airport_data = await self.get_airport_info(
                    response.destination.iata_code
                )
            else:
                # Use mwgg data
                logger.debug(
                    f"Using mwgg/Airports for destination airport enrichment: '{response.destination.iata_code}'"
                )
                from app.domains.airport.airport_resolver import airport_resolver

                airport_data = await airport_resolver.get_airport_info(
                    response.destination.iata_code
                )
            if airport_data and airport_data.get("country"):
                response.destination.country_code = airport_data["country"]

        # Recalculate cross_border_indicator with enriched country codes
        if response.origin.country_code and response.destination.country_code:
            response.cross_border_indicator = (
                response.origin.country_code != response.destination.country_code
            )

    # ============================================================
    # SEARCH OPERATIONS
    # ============================================================

    async def _finalize_search_response_after_client(
        self,
        request: FlightSearchRequest,
        response: FlightSearchResponse,
        route: str,
        *,
        code_to_logo: dict[str, str] | None = None,
    ) -> FlightSearchResponse:
        """Apply fees, optional logo enrichment, filters, and optional revalidation."""
        for fare_itinerary in response.fare_itineraries:
            if fare_itinerary.pricing and fare_itinerary.pricing.fare_totals:
                apply_platform_fee_to_fare_totals(fare_itinerary.pricing.fare_totals)

        if response.inbound_fare_itineraries:
            for fare_itinerary in response.inbound_fare_itineraries:
                if fare_itinerary.pricing and fare_itinerary.pricing.fare_totals:
                    apply_platform_fee_to_fare_totals(
                        fare_itinerary.pricing.fare_totals
                    )

        if code_to_logo is not None:
            self._enrich_airline_logos(response, code_to_logo)
        else:
            try:
                airline_response = await self.get_airline_list(
                    AirlineListRequest(
                        user_id=None,
                        user_password=None,
                        access=None,
                        ip_address=None,
                    )
                )
                code_to_logo = {
                    a.iata_code: a.logo_url for a in airline_response.airlines
                }
                self._enrich_airline_logos(response, code_to_logo)
            except (FlightSearchError, httpx.HTTPError) as e:
                logger.warning("Could not enrich airline logos: %s", e)

        requested_origin_code = (
            request.origin_destination_info[0].origin_airport.iata_code
            if request.origin_destination_info
            else None
        )
        requested_destination_code = (
            request.origin_destination_info[0].destination_airport.iata_code
            if request.origin_destination_info
            else None
        )

        needs_revalidation = False
        if (
            request.city_wise_search_origin is not None
            or request.city_wise_search_destination is not None
        ) and (
            request.filters is None
            or (
                request.city_wise_search_origin is not None
                and request.filters.city_wise_search_origin
                != request.city_wise_search_origin
            )
            or (
                request.city_wise_search_destination is not None
                and request.filters.city_wise_search_destination
                != request.city_wise_search_destination
            )
        ):
            needs_revalidation = True

        if needs_revalidation:
            request = FlightSearchRequest.model_validate(request.model_dump())

        logger.debug(
            "Applying flight search filters",
            extra={
                "filters_present": request.filters is not None,
                "requested_origin_code": requested_origin_code,
                "requested_destination_code": requested_destination_code,
            },
        )

        response = filter_flight_results(
            response,
            filters=request.filters,
            requested_origin_code=requested_origin_code,
            requested_destination_code=requested_destination_code,
        )

        revalidate_count = getattr(request, "revalidate_flights_count", None)
        if revalidate_count is not None and revalidate_count > 0:
            if settings.FLIGHT_SEARCH_CONCURRENT_REVALIDATION:
                revalidate_start = time.perf_counter()
                ids_to_remove = await get_flight_ids_to_remove_after_revalidation(
                    session_id=response.session_id,
                    flights=response.fare_itineraries,
                    adults=request.adults,
                    children=request.children,
                    infants=request.infants,
                    revalidate_flights_count=revalidate_count,
                    revalidate_fn=self.revalidate_fare,
                )
                revalidate_duration_ms = (time.perf_counter() - revalidate_start) * 1000
                candidates_count = min(len(response.fare_itineraries), revalidate_count)
                removed_count = len(ids_to_remove)
                logger.info(
                    "Flight search revalidation",
                    extra={
                        "requested_count": revalidate_count,
                        "candidates_count": candidates_count,
                        "removed_count": removed_count,
                        "duration_ms": round(revalidate_duration_ms, 1),
                        "route": route,
                        "concurrent": True,
                    },
                )
                if ids_to_remove:
                    response.fare_itineraries = [
                        fi
                        for fi in response.fare_itineraries
                        if (
                            fi.pricing
                            and getattr(fi.pricing, "fare_source_code", None)
                            not in ids_to_remove
                        )
                    ]
            else:
                logger.info(
                    "Flight search revalidation skipped",
                    extra={
                        "requested_count": revalidate_count,
                        "route": route,
                        "reason": "FLIGHT_SEARCH_CONCURRENT_REVALIDATION_disabled",
                    },
                )

        return response

    async def _search_multicity_parallel(
        self,
        request: FlightSearchRequest,
        log: FlightLogger,
    ) -> FlightSearchResponse:
        """Circle with 2+ segments: run N OneWay FlightLogic searches (parallel)."""
        n_segments = len(request.origin_destination_info)
        code_to_logo: dict[str, str] | None = None
        try:
            airline_response = await self.get_airline_list(
                AirlineListRequest(
                    user_id=None,
                    user_password=None,
                    access=None,
                    ip_address=None,
                )
            )
            code_to_logo = {a.iata_code: a.logo_url for a in airline_response.airlines}
        except (FlightSearchError, httpx.HTTPError) as e:
            logger.warning("Multicity search: could not prefetch airline logos: %s", e)

        async def _one_leg(leg_index: int) -> MulticityLegSearchResult:
            seg = request.origin_destination_info[leg_index]
            origin = seg.origin_airport.iata_code
            destination = seg.destination_airport.iata_code
            dep_date = seg.departure_date
            route_i = f"{origin}→{destination}"
            try:
                leg_req = _build_multicity_leg_search_request(request, leg_index)
                leg_response = await self.client.search_flights(leg_req)
                leg_response = await self._finalize_search_response_after_client(
                    leg_req,
                    leg_response,
                    route_i,
                    code_to_logo=code_to_logo,
                )
                return MulticityLegSearchResult(
                    leg_index=leg_index,
                    origin=origin,
                    destination=destination,
                    departure_date=dep_date,
                    session_id=leg_response.session_id,
                    supplier=leg_response.supplier,
                    fare_itineraries=leg_response.fare_itineraries,
                    inbound_fare_itineraries=leg_response.inbound_fare_itineraries,
                    errors=None,
                )
            except FlightSearchError as e:
                logger.warning("Multicity leg %s search failed: %s", leg_index, e)
                return MulticityLegSearchResult(
                    leg_index=leg_index,
                    origin=origin,
                    destination=destination,
                    departure_date=dep_date,
                    session_id="",
                    supplier="",
                    fare_itineraries=[],
                    inbound_fare_itineraries=None,
                    errors=[
                        ErrorDetails(
                            code="MULTICITY_LEG_SEARCH_FAILED",
                            message=str(e),
                            details=None,
                        )
                    ],
                )
            except Exception as e:
                logger.warning("Multicity leg %s unexpected error: %s", leg_index, e)
                return MulticityLegSearchResult(
                    leg_index=leg_index,
                    origin=origin,
                    destination=destination,
                    departure_date=dep_date,
                    session_id="",
                    supplier="",
                    fare_itineraries=[],
                    inbound_fare_itineraries=None,
                    errors=[
                        ErrorDetails(
                            code="MULTICITY_LEG_SEARCH_FAILED",
                            message=str(e),
                            details=None,
                        )
                    ],
                )

        legs = await asyncio.gather(*[_one_leg(i) for i in range(n_segments)])
        supplier = next((lg.supplier for lg in legs if lg.supplier), "FlightLogic")
        total_outbound = sum(len(lg.fare_itineraries) for lg in legs)
        log.success(
            "Multicity parallel search completed",
            legs=len(legs),
            total_outbound_results=total_outbound,
        )
        return FlightSearchResponse(
            session_id="",
            supplier=supplier,
            fare_itineraries=[],
            inbound_fare_itineraries=None,
            errors=None,
            multicity_legs=list(legs),
        )

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for available flights with event handling."""
        ods = request.origin_destination_info
        if request.journey_type == JourneyType.CIRCLE and ods:
            chain = [ods[0].origin_airport.iata_code]
            for seg in ods:
                chain.append(seg.destination_airport.iata_code)
            route = "→".join(chain)
            circle_leg_count = len(ods)
        elif ods:
            origin = ods[0].origin_airport.iata_code
            dest = ods[0].destination_airport.iata_code
            route = f"{origin}→{dest}"
            circle_leg_count = None
        else:
            route = "N/A"
            circle_leg_count = None

        # Extract departure date from first segment
        departure_date = ods[0].departure_date if ods else None

        # Extract return date for Return journeys (second segment departure)
        return_date = None
        if request.journey_type == JourneyType.RETURN and len(ods) > 1:
            return_date = ods[1].departure_date

        log_context: dict[str, Any] = {
            **self._get_base_log_context(),
            "route": route,
            "journey_type": request.journey_type.value,
            "departure_date": str(departure_date) if departure_date else "N/A",
            "passengers": {
                "adults": request.adults,
                "children": request.children,
                "infants": request.infants,
            },
            "cabin_class": request.cabin_class.value,
            "direct_flight_only": request.direct_flight == 1
            if request.direct_flight is not None
            else False,
        }

        if circle_leg_count is not None:
            log_context["circle_leg_count"] = circle_leg_count

        # Add return_date for Return (round trip) searches
        if return_date:
            log_context["return_date"] = str(return_date)

        log = FlightLogger("SEARCH", **log_context)

        log.started()

        try:
            if (
                request.journey_type == JourneyType.CIRCLE
                and len(request.origin_destination_info) >= 2
                and settings.MULTICITY_PARALLEL_SEARCH
            ):
                return await self._search_multicity_parallel(request, log)

            response = await self.client.search_flights(request)
            response = await self._finalize_search_response_after_client(
                request, response, route
            )

            outbound_count = len(response.fare_itineraries)
            inbound_count = len(response.inbound_fare_itineraries or [])
            total_results = outbound_count + inbound_count

            log.success(
                "Flight search completed successfully",
                outbound_results=outbound_count,
                inbound_results=inbound_count,
                total_results=total_results,
            )
            return response

        except FlightSearchError as e:
            log.error("Flight search failed", exc=e)
            raise
        except TimeoutError as e:
            log.error("Flight search timeout", exc=e)
            raise FlightSearchError(f"Flight search timeout: {e}") from e
        except Exception as e:
            log.error("Unexpected error during flight search", exc=e)
            raise FlightSearchError(f"Flight search failed: {e}") from e

    async def revalidate_fare(
        self, request: FlightRevalidateRequest
    ) -> FlightRevalidateResponse:
        """Revalidate selected fare before booking."""
        fare_code = self._truncate_sensitive_code(request.fare_source_code)

        log = FlightLogger(
            "REVALIDATE", **self._get_base_log_context(), fare_code=fare_code
        )

        log.started()

        try:
            response = await self.client.revalidate_fare(request)

            # Apply platform fee to all validated fare itineraries
            for validated_itinerary in response.validated_fare_itineraries:
                if (
                    validated_itinerary.updated_pricing
                    and validated_itinerary.updated_pricing.validated_fare_totals
                ):
                    apply_platform_fee_to_fare_totals(
                        validated_itinerary.updated_pricing.validated_fare_totals
                    )

            # Store revalidate response in cache for booking email (persists across requests)
            if self.current_user and response.is_fare_available:
                RevalidateCache.set(
                    user_id=str(self.current_user.id),
                    fare_source_code=request.fare_source_code,
                    revalidate_response=response,
                )

            if response.is_fare_available:
                # Add price info if available for comparison
                if hasattr(response, "fare_details") and hasattr(
                    response.fare_details, "total_fare_amount"
                ):
                    log.success(
                        "Fare revalidation successful",
                        fare_is_available=True,
                        fare_amount=str(response.fare_details.total_fare_amount)
                        if response.fare_details.total_fare_amount
                        else "N/A",
                    )
                else:
                    log.success("Fare revalidation successful", fare_is_available=True)
            else:
                error_msg = (
                    response.errors[0].message
                    if response.errors
                    else "Fare no longer available"
                )
                log.warning(
                    "Fare no longer available",
                    fare_is_available=False,
                    error_message=error_msg,
                )

            # Log essential revalidate info only (reduced verbosity)
            fare_available = response.is_fare_available
            fare_code = self._truncate_sensitive_code(request.fare_source_code)
            logger.info(
                f"Revalidate response summary - Fare: {fare_code}, Available: {fare_available} | {log.request_id}"
            )

            return response
        except Exception as e:
            log.error("Failed to revalidate fare", exc=e)
            raise

    # ============================================================
    # BOOKING OPERATIONS
    # ============================================================

    async def create_booking(
        self,
        request: FlightBookingRequest,
        required_fields: list[str] | None = None,
        cancellation_policy_text: str | None = None,
    ) -> FlightBookingResponse:
        """Create a flight booking with validation, payment verification, and event handling.

        Args:
            request: The flight booking request
            required_fields: Required fields from revalidate response (optional but recommended)

        Returns:
            FlightBookingResponse with booking details

        Raises:
            PaymentRequiredError: If payment is required but not provided
            MissingRequiredFieldError: If required booking fields are missing
            FlightBookingError: If booking fails

        Note:
            It's recommended to call revalidate_fare() first and pass the
            required_booking_fields from the revalidate response for validation.
        """
        if not self.current_user:
            raise InvalidTokenError("Authentication required for booking")

        user_id = str(self.current_user.id)

        # Resolve saved_passenger_id refs: fetch travel_documents from DB
        request = await _resolve_saved_passengers(request, user_id)

        validated_saved_itinerary_id = await ensure_saved_itinerary_owned_by_user(
            user_id, request.saved_itinerary_id
        )

        fare_code = self._truncate_sensitive_code(request.fare_source_code)
        adults = len(request.passenger_groups.adults or [])
        children = len(request.passenger_groups.children or [])
        infants = len(request.passenger_groups.infants or [])

        log = FlightLogger(
            "BOOK",
            **self._get_base_log_context(),
            fare_code=fare_code,
            passengers={"adults": adults, "children": children, "infants": infants},
            fare_type=request.fare_type.value,
            has_payment=request.payment_id is not None,
        )

        log.started()

        # Validate required booking fields if provided
        if required_fields:
            validate_required_fields_to_book(request, required_fields)

        # Validate passenger ages (children 2-11, infants <2)
        validate_age_requirements(request.passenger_groups)

        # Validate infant-adult pairing (max 1 infant per adult)
        validate_infant_adult_pairing(request.passenger_groups)

        # Payment validation ONLY for LCC bookings (WebFare requires payment upfront)
        # GDS bookings (Public/Private) allow booking without payment (24h payment window)
        if request.fare_type.value == "WebFare":
            self._validate_payment_required(
                request.fare_type.value, request.payment_id, user_id, log
            )

        # LCC: create booking event after payment, before booking API (enables admin retry if API fails)
        voya_booking_reference = None
        if request.fare_type.value == "WebFare":
            try:
                booking_service = BookingService(user_id)
                contact_email = None
                if request.contact_information and request.contact_information.email:
                    contact_email = request.contact_information.email
                lcc_payload: dict[str, Any] = {
                    "external_booking_reference": TEMP_EXTERNAL_REF,
                    "action": "BOOKED",
                    "event_type": "FLIGHT",
                    "carrier_type": "LCC",
                    "contact_email": contact_email,
                    "payment_intent_id": request.payment_id,
                    "parent_voya_booking_reference": request.parent_voya_booking_reference,
                    "multistay_leg_index": request.multistay_leg_index,
                }
                if request.voucher_redemption_id:
                    lcc_payload["voucher_redemption_id"] = request.voucher_redemption_id
                    if request.client_reference:
                        lcc_payload["voya_booking_reference"] = request.client_reference
                lcc_pre_request = CreateBookingEventRequest.model_validate(lcc_payload)
                lcc_pre_response = await booking_service.create_booking(lcc_pre_request)
                voya_booking_reference = lcc_pre_response.voya_booking_reference
                log.info(
                    "Created LCC booking event before booking API",
                    voya_booking_reference=voya_booking_reference,
                )
                # Store payload before API call so admin retry can re-use it if API fails
                try:
                    dto_request = self.client.adapter.booking_request_to_dto(request)
                    payload = dto_request.model_dump(by_alias=True)
                    await BookingService.set_booking_payload(
                        voya_booking_reference, payload
                    )
                except Exception as e:
                    log.warning(
                        "Failed to store LCC booking payload before API",
                        error_message=str(e),
                    )
            except Exception as e:
                log.warning(
                    "Failed to create LCC booking event before API",
                    error_message=str(e),
                )

        # GDS Pay Now: resolve PENDING event (VOYA-*) before FlightLogic — strict client_reference
        gds_pending_voya_ref: str | None = None
        if (
            not voya_booking_reference
            and request.client_reference
            and request.client_reference.startswith("VOYA-")
        ):
            existing = await BookingService.get_event_by_voya_reference(
                request.client_reference
            )
            if existing is not None:
                if str(existing.user_id) != user_id:
                    raise BookingForbiddenError(
                        "You do not have access to this booking reference"
                    )
                if (
                    getattr(existing, "action", None) == "PENDING"
                    and existing.external_booking_reference == TEMP_EXTERNAL_REF
                ):
                    gds_pending_voya_ref = request.client_reference
                    voya_booking_reference = gds_pending_voya_ref
                else:
                    log.warning(
                        "GDS create_booking rejected: VOYA client_reference is not "
                        "PENDING with TEMP-REF",
                        client_reference=request.client_reference,
                        action=getattr(existing, "action", None),
                        external_booking_reference=existing.external_booking_reference,
                    )
                    raise GdsClientReferenceConflictError()
            else:
                log.warning(
                    "VOYA client_reference has no Voya booking event (stale UI or unknown ref)",
                    client_reference=request.client_reference,
                )

        try:
            response = await self.client.create_booking(request)

            if response.is_successful:
                # Add external reference to logger context
                log.base_context["external_booking_reference"] = (
                    response.external_booking_reference
                )

                # Add booking status for visibility
                booking_status = (
                    response.booking_status.value
                    if hasattr(response, "booking_status")
                    else "UNKNOWN"
                )

                log.success(
                    "Booking created successfully", booking_status=booking_status
                )

                # Persist booking event: LCC already has event (TEMP-REF), update it; GDS create now
                try:
                    booking_service = BookingService(user_id)

                    # Extract PNR data if available
                    pnr_code = None
                    pnr_airline_code = None
                    pnr_airline_name = None
                    pnr_status = None

                    if response.airline_pnr:
                        pnr_code = response.airline_pnr.pnr_code
                        if response.airline_pnr.airline:
                            pnr_airline_code = response.airline_pnr.airline.iata_code
                            pnr_airline_name = response.airline_pnr.airline.airline_name
                        if response.airline_pnr.status:
                            pnr_status = response.airline_pnr.status.value

                    # Extract contact email from booking request for email routing
                    contact_email = None
                    if (
                        request.contact_information
                        and request.contact_information.email
                    ):
                        contact_email = request.contact_information.email
                        logger.info(
                            f"🔍 [BookingCreate] Storing contact email: {contact_email}"
                        )
                    else:
                        logger.info(
                            "🔍 [BookingCreate] No contact email in request, will use user email for tickets"
                        )

                    # Get cached revalidate response early (needed for departure airport extraction)
                    cached_revalidate = RevalidateCache.get(
                        user_id, request.fare_source_code
                    )
                    route_snapshot = extract_route_and_airline_snapshot(
                        cached_revalidate,
                        multistay_leg_index=request.multistay_leg_index,
                        pnr_airline_name=pnr_airline_name,
                    )

                    # Extract and convert ticket_time_limit to UTC
                    ticket_time_limit_utc = None
                    departure_airport_iata = (
                        departure_iata_from_route_legs(list(route_snapshot.route_legs))
                        if route_snapshot.route_legs
                        else None
                    )
                    if response.ticket_time_limit and response.ticket_time_limit.value:
                        logger.info(
                            f"🕐 [BookingCreate] TktTimeLimit received from FlightLogic: "
                            f"{response.ticket_time_limit.value} (tzinfo: {response.ticket_time_limit.value.tzinfo})"
                        )
                        # Extract departure airport IATA - try multiple sources
                        # First, try to get from cached revalidate response (most reliable)
                        if (
                            cached_revalidate
                            and cached_revalidate.validated_fare_itineraries
                        ):
                            try:
                                first_itinerary = (
                                    cached_revalidate.validated_fare_itineraries[0]
                                )
                                if (
                                    first_itinerary.flight_legs
                                    and len(first_itinerary.flight_legs) > 0
                                ):
                                    first_leg = first_itinerary.flight_legs[0]
                                    # FlightLeg uses 'flight_segments' not 'segments'
                                    if (
                                        first_leg.flight_segments
                                        and len(first_leg.flight_segments) > 0
                                    ):
                                        first_segment = first_leg.flight_segments[0]
                                        if first_segment.departure_airport:
                                            departure_airport_iata = first_segment.departure_airport.iata_code
                                            logger.info(
                                                f"🕐 [BookingCreate] Found departure airport from cached revalidate: {departure_airport_iata}"
                                            )
                            except (AttributeError, IndexError) as e:
                                logger.warning(
                                    f"🕐 [BookingCreate] Could not extract departure airport from cached revalidate: {e}"
                                )

                        # If not available, try to get from origin_destination_info if available
                        if not departure_airport_iata and (
                            hasattr(request, "origin_destination_info")
                            and request.origin_destination_info
                            and len(request.origin_destination_info) > 0
                            and hasattr(
                                request.origin_destination_info[0], "origin_airport"
                            )
                            and request.origin_destination_info[0].origin_airport
                        ):
                            departure_airport_iata = request.origin_destination_info[
                                0
                            ].origin_airport.iata_code
                            logger.info(
                                f"🕐 [BookingCreate] Found departure airport from request: {departure_airport_iata}"
                            )

                        # If not available, try to fetch from trip details (after booking)
                        if not departure_airport_iata:
                            logger.info(
                                "🕐 [BookingCreate] Departure airport not in request or cache, fetching from trip details..."
                            )
                            try:
                                # external_booking_reference resolves booking; voya ref when known.
                                trip_details_request = TripDetailsRequest.model_validate(
                                    {
                                        "voya_booking_reference": voya_booking_reference
                                        or "",
                                        "external_booking_reference": response.external_booking_reference,
                                    }
                                )
                                trip_details = await self.get_trip_details(
                                    trip_details_request,
                                    skip_logging=True,
                                    skip_validation=True,
                                )
                                if trip_details and trip_details.origin:
                                    departure_airport_iata = (
                                        trip_details.origin.iata_code
                                    )
                                    logger.info(
                                        f"🕐 [BookingCreate] Found departure airport from trip details: {departure_airport_iata}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"🕐 [BookingCreate] Could not fetch trip details to get departure airport: {e}. "
                                    "Will convert ticket_time_limit assuming UTC."
                                )

                        # Convert ticket_time_limit to UTC
                        if departure_airport_iata:
                            from app.domains.flight.timezone_utils import (
                                convert_ticket_time_limit_to_utc,
                            )

                            logger.info(
                                f"🕐 [BookingCreate] Converting TktTimeLimit using airport {departure_airport_iata}"
                            )
                            ticket_time_limit_utc = (
                                await convert_ticket_time_limit_to_utc(
                                    response.ticket_time_limit.value,
                                    departure_airport_iata,
                                )
                            )
                            logger.info(
                                f"🕐 [BookingCreate] ✅ Final converted ticket_time_limit: "
                                f"{response.ticket_time_limit.value} -> {ticket_time_limit_utc} UTC"
                            )
                        else:
                            # Fallback: assume UTC (or use as-is if already timezone-aware)
                            ticket_time_limit_utc = (
                                response.ticket_time_limit.value.replace(tzinfo=UTC)
                                if response.ticket_time_limit.value.tzinfo is None
                                else response.ticket_time_limit.value
                            )
                            logger.warning(
                                f"🕐 [BookingCreate] ⚠️ No departure airport IATA available, "
                                f"storing ticket_time_limit as UTC: {ticket_time_limit_utc}"
                            )

                    now_utc = datetime.now(UTC)
                    flight_amount: float | None = None
                    if cached_revalidate:
                        fare_totals = None
                        if (
                            getattr(
                                cached_revalidate, "validated_fare_itineraries", None
                            )
                            and len(cached_revalidate.validated_fare_itineraries) > 0
                        ):
                            first_it = cached_revalidate.validated_fare_itineraries[0]
                            fare_totals = getattr(
                                getattr(first_it, "pricing", None),
                                "fare_totals",
                                None,
                            )
                        if fare_totals:
                            orig = getattr(fare_totals, "original_total_fare", None)
                            if orig is not None and hasattr(orig, "amount"):
                                with contextlib.suppress(TypeError, ValueError):
                                    flight_amount = float(orig.amount)
                            if flight_amount is None:
                                total = getattr(fare_totals, "total_fare", None)
                                if total is not None and hasattr(total, "amount"):
                                    with contextlib.suppress(TypeError, ValueError):
                                        flight_amount = float(total.amount)
                        if flight_amount is None and hasattr(
                            cached_revalidate, "fare_details"
                        ):
                            fd = cached_revalidate.fare_details
                            if fd is not None and hasattr(fd, "total_fare_amount"):
                                with contextlib.suppress(TypeError, ValueError):
                                    flight_amount = float(fd.total_fare_amount)

                    if voya_booking_reference:
                        if gds_pending_voya_ref:
                            # GDS Pay Now: update PENDING event to BOOKED
                            try:
                                gds_payload = None
                                try:
                                    gds_payload = (
                                        self.client.adapter.booking_request_to_dto(
                                            request
                                        ).model_dump(by_alias=True)
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "Failed to build payload for GDS PENDING update: %s",
                                        e,
                                    )
                                route_legs_dump = (
                                    [
                                        lg.model_dump()
                                        for lg in route_snapshot.route_legs
                                    ]
                                    if route_snapshot.route_legs
                                    else None
                                )
                                await BookingService.update_gds_pending_booking_after_api(
                                    voya_booking_reference,
                                    response.external_booking_reference,
                                    airline_pnr_code=pnr_code,
                                    airline_pnr_airline_code=pnr_airline_code,
                                    airline_pnr_airline_name=pnr_airline_name,
                                    airline_pnr_status=pnr_status,
                                    cancellation_policy_text=cancellation_policy_text,
                                    ticket_time_limit=ticket_time_limit_utc,
                                    departure_airport_iata=departure_airport_iata,
                                    flight_trip_type=route_snapshot.flight_trip_type,
                                    route_legs=route_legs_dump,
                                    primary_marketing_airline_name=route_snapshot.primary_marketing_airline_name,
                                    date_booked=now_utc,
                                    date_tickets_issued=now_utc,
                                    amount=flight_amount,
                                    payload=gds_payload,
                                    saved_itinerary_id=validated_saved_itinerary_id,
                                )
                                log.info(
                                    "Updated GDS PENDING booking to BOOKED",
                                    voya_booking_reference=voya_booking_reference,
                                )
                            except GdsPendingBookingSyncError:
                                raise
                            except Exception as e:
                                log.warning(
                                    "Failed to update GDS PENDING booking",
                                    voya_booking_reference=voya_booking_reference,
                                    error_message=str(e),
                                )
                        else:
                            # LCC: update pre-created event (TEMP-REF) with FlightLogic data
                            rl_dump = (
                                [lg.model_dump() for lg in route_snapshot.route_legs]
                                if route_snapshot.route_legs
                                else None
                            )
                            await BookingService.update_booking_after_flight_confirmation(
                                voya_booking_reference,
                                response.external_booking_reference,
                                airline_pnr_code=pnr_code,
                                airline_pnr_airline_code=pnr_airline_code,
                                airline_pnr_airline_name=pnr_airline_name,
                                airline_pnr_status=pnr_status,
                                cancellation_policy_text=cancellation_policy_text,
                                ticket_time_limit=ticket_time_limit_utc,
                                departure_airport_iata=departure_airport_iata,
                                flight_trip_type=route_snapshot.flight_trip_type,
                                route_legs=rl_dump,
                                primary_marketing_airline_name=route_snapshot.primary_marketing_airline_name,
                                date_booked=now_utc,
                                date_tickets_issued=now_utc,
                                amount=flight_amount,
                                saved_itinerary_id=validated_saved_itinerary_id,
                            )
                        # LCC + Stripe: set date_paid (and amount if missing) from transaction
                        # (Webhook ran with temp ref VOYA-TEMP-* so it could not find the booking)
                        if request.payment_id:
                            try:
                                await BookingService.apply_date_paid_from_completed_payment(
                                    voya_booking_reference,
                                    request.payment_id,
                                    flight_amount=flight_amount,
                                )
                            except Exception as e:
                                log.warning(
                                    "Failed to set date_paid from payment transaction for LCC booking",
                                    voya_booking_reference=voya_booking_reference,
                                    error_message=str(e),
                                )
                    else:
                        # GDS: create booking event now (full data from response); store payload at creation
                        carrier_type: Literal["GDS", "LCC"] = (
                            "LCC" if request.fare_type.value == "WebFare" else "GDS"
                        )
                        gds_payload = None
                        try:
                            dto_request = self.client.adapter.booking_request_to_dto(
                                request
                            )
                            gds_payload = dto_request.model_dump(by_alias=True)
                        except Exception as e:
                            logger.warning(
                                "Failed to build GDS booking payload for storage: %s",
                                e,
                            )
                        gds_new_event: dict[str, Any] = {
                            "external_booking_reference": response.external_booking_reference,
                            "action": "BOOKED",
                            "event_type": "FLIGHT",
                            "airline_pnr_code": pnr_code,
                            "airline_pnr_airline_code": pnr_airline_code,
                            "airline_pnr_airline_name": pnr_airline_name,
                            "airline_pnr_status": pnr_status,
                            "contact_email": contact_email,
                            "cancellation_policy_text": cancellation_policy_text,
                            "ticket_time_limit": ticket_time_limit_utc,
                            "departure_airport_iata": departure_airport_iata,
                            "flight_trip_type": route_snapshot.flight_trip_type,
                            "route_legs": list(route_snapshot.route_legs)
                            if route_snapshot.route_legs
                            else None,
                            "primary_marketing_airline_name": route_snapshot.primary_marketing_airline_name,
                            "carrier_type": carrier_type,
                            "payment_intent_id": request.payment_id,
                            "payload": gds_payload,
                            "amount": flight_amount,
                            "date_booked": now_utc,
                            "saved_itinerary_id": str(validated_saved_itinerary_id)
                            if validated_saved_itinerary_id
                            else None,
                            "parent_voya_booking_reference": request.parent_voya_booking_reference,
                            "multistay_leg_index": request.multistay_leg_index,
                        }
                        if request.voucher_redemption_id:
                            gds_new_event["voucher_redemption_id"] = (
                                request.voucher_redemption_id
                            )
                            if request.client_reference:
                                gds_new_event["voya_booking_reference"] = (
                                    request.client_reference
                                )
                        booking_request = CreateBookingEventRequest.model_validate(
                            gds_new_event
                        )
                        booking_response = await booking_service.create_booking(
                            booking_request
                        )
                        voya_booking_reference = booking_response.voya_booking_reference
                        if request.payment_id and voya_booking_reference:
                            try:
                                await BookingService.apply_date_paid_from_completed_payment(
                                    voya_booking_reference,
                                    request.payment_id,
                                    flight_amount=flight_amount,
                                )
                            except Exception as e:
                                log.warning(
                                    "Failed to set date_paid from payment transaction for GDS booking",
                                    voya_booking_reference=voya_booking_reference,
                                    error_message=str(e),
                                )

                    log.base_context["voya_booking_reference"] = voya_booking_reference

                    # Store cancellation_policy_text in cache for ticket issuance
                    if cancellation_policy_text and voya_booking_reference:
                        _cancellation_policy_cache[voya_booking_reference] = (
                            cancellation_policy_text
                        )
                        logger.info(
                            f"Stored cancellation_policy_text in cache for {voya_booking_reference}"
                        )

                    # Create new response with voya_booking_reference included
                    # Pydantic models are immutable, so we need to create a new instance
                    response = FlightBookingResponse(
                        booking_status=response.booking_status,
                        is_successful=response.is_successful,
                        external_booking_reference=response.external_booking_reference,
                        voya_booking_reference=voya_booking_reference,  # Include VOYA reference
                        airline_pnr=response.airline_pnr,
                        ticket_time_limit=response.ticket_time_limit,
                        environment=response.environment,
                        errors=response.errors,
                    )

                except GdsPendingBookingSyncError:
                    raise
                except Exception as e:
                    log.warning(
                        "Failed to save booking event to database",
                        external_booking_reference=response.external_booking_reference,
                        error_message=str(e),
                    )
                    # Keep voya_booking_reference as None if booking event creation failed

                # For LCC bookings (WebFare), fetch trip details since tickets are already issued
                # GDS bookings skip this - trip details only after ticketing
                trip_details_for_email = None
                if request.fare_type.value == "WebFare" and voya_booking_reference:
                    try:
                        import asyncio

                        # LCC bookings require API sync time - retry with exponential backoff
                        # FlightLogic needs time to sync booking data before trip details become available
                        max_retries = 3
                        for attempt in range(max_retries):
                            delay = 2 * (
                                2**attempt
                            )  # 2s, 4s, 8s (increased from 0.5s, 1s, 2s)
                            await asyncio.sleep(delay)

                            try:
                                trip_details_request = TripDetailsRequest.model_validate(
                                    {
                                        "voya_booking_reference": voya_booking_reference,
                                    }
                                )
                                trip_details_for_email = await self.get_trip_details(
                                    trip_details_request,
                                    skip_logging=True,
                                    skip_validation=True,  # Skip validation - booking just created
                                )

                                # Validate we got segments (required for PDF generation)
                                if (
                                    trip_details_for_email
                                    and trip_details_for_email.segments
                                ):
                                    logger.info(
                                        f"Trip details fetched successfully on attempt {attempt + 1}"
                                    )
                                    break
                                log.warning(
                                    f"Trip details incomplete (no segments) on attempt {attempt + 1}/{max_retries}",
                                    attempt=attempt + 1,
                                    delay_used=delay,
                                )
                                if attempt == max_retries - 1:
                                    # Last attempt failed - email will send without PDF
                                    trip_details_for_email = None
                            except Exception as retry_error:
                                # Get full traceback for debugging
                                import traceback

                                error_traceback = "".join(
                                    traceback.format_exception(
                                        type(retry_error),
                                        retry_error,
                                        retry_error.__traceback__,
                                    )
                                )

                                log.warning(
                                    f"Trip details fetch failed on attempt {attempt + 1}/{max_retries}: {retry_error!s}",
                                    error_type=type(retry_error).__name__,
                                    error_message=str(retry_error)[
                                        :500
                                    ],  # First 500 chars
                                    attempt=attempt + 1,
                                )

                                # Log full traceback to console for debugging
                                logger.debug(f"Full traceback:\n{error_traceback}")

                                if attempt == max_retries - 1:
                                    raise  # Re-raise on final attempt
                    except Exception as e:
                        log.warning(
                            "Failed to fetch trip details for LCC booking email after all retries",
                            error_message=str(e),
                            error_type=type(e).__name__,
                        )

                # LCC: update booking doc with PNR list from trip details when available
                if (
                    voya_booking_reference
                    and trip_details_for_email
                    and getattr(trip_details_for_email, "segments", None)
                ):
                    pnrs = _extract_pnrs_from_trip_details(trip_details_for_email)
                    if pnrs:
                        try:
                            await BookingService.update_booking_pnr(
                                voya_booking_reference, pnrs
                            )
                        except Exception as pnr_err:
                            logger.warning(
                                "Failed to update booking PNR from trip details: %s",
                                pnr_err,
                            )

                # Retrieve revalidate response from cache (persists across requests)
                cached_revalidate = RevalidateCache.get(
                    user_id, request.fare_source_code
                )

                # Log essential cached revalidate info only (reduced verbosity)
                if cached_revalidate:
                    fare_available = getattr(
                        cached_revalidate, "is_fare_available", "Unknown"
                    )
                    fare_details = getattr(cached_revalidate, "fare_details", None)
                    total_fare = (
                        getattr(fare_details, "total_fare_amount", "N/A")
                        if fare_details
                        else "N/A"
                    )
                    logger.info(
                        f"Cached revalidate found - Available: {fare_available}, Total: {total_fare}"
                    )
                else:
                    logger.warning(
                        "⚠️ No cached_revalidate found - PDF may not have pricing data!"
                    )

                # Send booking confirmation email with booking context data
                try:
                    await FlightEventHandler.handle_booking_confirmed(
                        user_id,
                        response.external_booking_reference,
                        response.model_dump(),
                        voya_booking_reference,
                        revalidate_response=cached_revalidate,
                        booking_request=request,
                        trip_details=trip_details_for_email,  # Populated for LCC, None for GDS
                        booking_response_pnr=pnr_code,  # Pass PNR from booking response if available
                        cancellation_policy_text=cancellation_policy_text,  # Cancellation policy from fare rules
                    )
                except Exception as e:
                    log.error("Booking confirmation email handler failed", exc=e)

            else:
                error_msg = (
                    response.errors[0].message if response.errors else "Unknown error"
                )
                log.error(f"Booking unsuccessful: {error_msg}")

            return response

        except GdsPendingBookingSyncError as e:
            log.error(
                "Booking creation failed: supplier booking succeeded but Voya record was not updated",
                exc=e,
            )
            raise FlightBookingSupplierSyncError(str(e)) from e
        except Exception as e:
            log.error("Booking creation failed", exc=e)
            raise FlightBookingError(f"Booking creation failed: {e}") from e

    async def issue_tickets(self, request: TicketOrderRequest) -> TicketOrderResponse:
        """Issue tickets for a confirmed booking using VOYA reference.

        Auto-populates external_booking_reference and validates user ownership.

        When ``trip_details.ticket_status`` from FlightLogic is ``TicketStatus.TICKETED``,
        the FlightLogic ticket-issue API is skipped and success is returned immediately.
        This assumes trip details reflect current supplier state immediately before issuance;
        if the vendor lags, operations may need a support-side retry or forced issue path.
        """
        if not self.current_user:
            raise InvalidTokenError("Authentication required for ticketing")

        user_id = str(self.current_user.id)
        voya_booking_reference = request.voya_booking_reference

        # Security: Validate user owns this booking
        await BookingService.validate_user_owns_booking(voya_booking_reference, user_id)

        # Auto-populate external reference
        external_ref = await self._ensure_external_reference(request)

        if external_ref == TEMP_EXTERNAL_REF:
            raise FlightBookingError(
                "Booking is not linked to a supplier PNR yet (placeholder reference). "
                "Complete the flight booking step so a real booking reference is stored, then issue tickets."
            )

        log = FlightLogger(
            "TICKET",
            **self._get_base_log_context(),
            voya_booking_reference=voya_booking_reference,
            external_booking_reference=external_ref,
            has_payment=request.payment_id is not None,
        )

        log.started()

        # Validate ticket_time_limit before processing
        booking_event = await BookingService.get_latest_booking_by_voya_reference(
            voya_booking_reference
        )
        if booking_event and booking_event.ticket_time_limit:
            is_valid, time_remaining = validate_ticket_time_limit(
                booking_event.ticket_time_limit
            )

            if not is_valid:
                current_time_utc = datetime.now(UTC)
                ticket_time_limit_utc = booking_event.ticket_time_limit
                # Normalize for logging
                if ticket_time_limit_utc.tzinfo is None:
                    ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
                else:
                    ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

                log.error(
                    f"Ticket time limit expired. "
                    f"Current time UTC: {current_time_utc.isoformat()}, "
                    f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}, "
                    f"Voya booking reference: {voya_booking_reference}"
                )
                raise FlightBookingError(
                    f"Booking has expired. The ticket time limit ({ticket_time_limit_utc.isoformat()}) has passed. "
                    "Please start a new search."
                )

            current_time_utc = datetime.now(UTC)
            ticket_time_limit_utc = booking_event.ticket_time_limit
            # Normalize for logging
            if ticket_time_limit_utc.tzinfo is None:
                ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
            else:
                ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

            log.info(
                f"Ticket time limit validation passed. "
                f"Current time UTC: {current_time_utc.isoformat()}, "
                f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}, "
                f"Time remaining: {time_remaining} seconds"
            )

        # Get booking details to check fare_type (GDS requires payment for ticketing)
        try:
            trip_details_request = TripDetailsRequest.model_validate(
                {"voya_booking_reference": voya_booking_reference}
            )
            trip_details = await self.get_trip_details(
                trip_details_request, skip_logging=True
            )

            ticket_status = trip_details.ticket_status
            # Skip payment validation and duplicate issue when already ticketed (see method docstring).
            if ticket_status == TicketStatus.TICKETED:
                log.success(
                    "Skipped FlightLogic ticket issue API; trip details show tickets already issued",
                    ticket_issue_api_skipped=True,
                    ticket_issue_skip_reason="early_trip_details_ticketed",
                    trip_details_ticket_status=_enum_or_scalar_str(ticket_status),
                    fare_type_is_gds=trip_details.fare_type.is_gds,
                )
                return TicketOrderResponse(
                    success=True,
                    external_booking_reference=external_ref,
                    environment=trip_details.environment,
                    errors=[],
                )

            # Payment validation for GDS ticket issuance
            self._validate_payment_required(
                _enum_or_scalar_str(trip_details.fare_type),
                request.payment_id,
                voya_booking_reference,
                log,
            )

            # If payment_id provided, validate it succeeded and belongs to this booking
            if request.payment_id:
                # Detect payment provider: Stripe IDs start with "pi_", Revolut IDs are UUIDs
                is_stripe = request.payment_id.startswith("pi_")
                is_revolut = (
                    not is_stripe
                    and "-" in request.payment_id
                    and len(request.payment_id) == 36
                )

                if is_stripe:
                    from app.domains.payment import PaymentService

                    payment_service = PaymentService(user_id=user_id)

                    try:
                        # 1. Validate payment succeeded with Stripe
                        await payment_service.validate_payment_succeeded(
                            request.payment_id
                        )

                        # 2. Verify payment belongs to this booking (leg ref or multicity parent)
                        transaction = await payment_service.repository.get_transaction_by_voya_reference(
                            voya_booking_reference
                        )
                        if not transaction:
                            parent = await BookingService.get_parent_voya_booking_reference_for_leg(
                                voya_booking_reference
                            )
                            if parent:
                                transaction = await payment_service.repository.get_transaction_by_voya_reference(
                                    parent
                                )

                        if not transaction:
                            log.error(
                                "Payment validation failed: no transaction found for booking",
                                payment_id=request.payment_id,
                                voya_booking_reference=voya_booking_reference,
                            )
                            raise PaymentValidationError(
                                f"No payment transaction found for booking {voya_booking_reference}"
                            )

                        if transaction.stripe_payment_intent_id != request.payment_id:
                            log.error(
                                "Payment validation failed: payment does not belong to this booking",
                                provided_payment_id=request.payment_id,
                                booking_payment_id=transaction.stripe_payment_intent_id,
                            )
                            raise PaymentValidationError(
                                "Payment ID does not match this booking's transaction"
                            )

                        log.info(
                            "✅ Payment validated successfully for ticket issuance",
                            payment_id=request.payment_id,
                            voya_booking_reference=voya_booking_reference,
                        )

                    except PaymentValidationError:
                        raise
                    except Exception as e:
                        log.error(
                            "Payment validation failed",
                            exc=e,
                            payment_id=request.payment_id,
                        )
                        raise PaymentValidationError(
                            f"Payment validation failed: {e!s}"
                        ) from e

                elif is_revolut:
                    from app.domains.revolut_payment import RevolutPaymentService

                    revolut_service = RevolutPaymentService(user_id=user_id)

                    try:
                        # 1. Validate payment succeeded with Revolut
                        await revolut_service.validate_payment_succeeded(
                            request.payment_id
                        )

                        # 2. Verify payment belongs to this booking (leg ref or multicity parent)
                        transaction = await revolut_service.repository.get_transaction_by_voya_reference(
                            voya_booking_reference
                        )
                        if not transaction:
                            parent = await BookingService.get_parent_voya_booking_reference_for_leg(
                                voya_booking_reference
                            )
                            if parent:
                                transaction = await revolut_service.repository.get_transaction_by_voya_reference(
                                    parent
                                )

                        if not transaction:
                            log.error(
                                "Payment validation failed: no transaction found for booking",
                                payment_id=request.payment_id,
                                voya_booking_reference=voya_booking_reference,
                            )
                            raise PaymentValidationError(
                                f"No payment transaction found for booking {voya_booking_reference}"
                            )

                        # Check if payment_id matches revolut_order_id or the temporary mapping format
                        transaction_order_id = None
                        if (
                            hasattr(transaction, "revolut_order_id")
                            and transaction.revolut_order_id
                        ):
                            transaction_order_id = transaction.revolut_order_id
                        elif hasattr(transaction, "stripe_payment_intent_id"):
                            # Handle temporary mapping format: "revolut_<order_id>"
                            pi_id = transaction.stripe_payment_intent_id
                            if pi_id and pi_id.startswith("revolut_"):
                                transaction_order_id = pi_id.replace("revolut_", "", 1)

                        if transaction_order_id != request.payment_id:
                            log.error(
                                "Payment validation failed: payment does not belong to this booking",
                                provided_payment_id=request.payment_id,
                                booking_payment_id=transaction_order_id,
                            )
                            raise PaymentValidationError(
                                "Payment ID does not match this booking's transaction"
                            )

                        log.info(
                            "✅ Revolut payment validated successfully for ticket issuance",
                            payment_id=request.payment_id,
                            voya_booking_reference=voya_booking_reference,
                        )

                    except PaymentValidationError:
                        raise
                    except Exception as e:
                        # Convert RevolutPaymentValidationError to PaymentValidationError for consistency
                        if isinstance(e, RevolutPaymentValidationError):
                            raise PaymentValidationError(str(e)) from e
                        log.error(
                            "Revolut payment validation failed",
                            exc=e,
                            payment_id=request.payment_id,
                        )
                        raise PaymentValidationError(
                            f"Payment validation failed: {e!s}"
                        ) from e
                else:
                    log.error(
                        "Payment validation failed: unrecognized payment ID format",
                        payment_id=request.payment_id,
                    )
                    raise PaymentValidationError(
                        f"Unrecognized payment ID format: {request.payment_id}"
                    )

        except PaymentRequiredError:
            raise
        except Exception as e:
            log.error("Trip details retrieval failed", exc=e)
            raise

        # GDS ticket status gate: skip ticket order API if already ticketed or cancelled
        if self._should_skip_ticket_order_for_gds(trip_details):
            log.info(
                "Skipping ticket order API (_should_skip_ticket_order_for_gds): "
                "GDS fare with terminal ticket status",
                ticket_issue_api_skipped=True,
                ticket_issue_skip_reason="gds_fare_ticket_status_gate",
                trip_details_ticket_status=_enum_or_scalar_str(
                    trip_details.ticket_status
                ),
                fare_type_is_gds=trip_details.fare_type.is_gds,
            )
            return TicketOrderResponse(
                success=True,
                external_booking_reference=external_ref,
                environment=trip_details.environment,
                errors=[],
            )

        log.info(
            "Calling FlightLogic ticket issue API (trip details ticket_status does not indicate issued yet)",
            ticket_issue_api_skipped=False,
            trip_details_ticket_status=_enum_or_scalar_str(ticket_status),
        )

        try:
            # Pass request directly to client (no conversion needed)
            response = await self.client.issue_tickets(request)

            if hasattr(response, "success") and response.success:
                # TODO (2025-01): Extract ticket numbers from response.tickets when schema is finalized
                ticket_numbers: list[str] = []

                # Add fare type from trip details for context
                fare_type = (
                    _enum_or_scalar_str(trip_details.fare_type)
                    if hasattr(trip_details, "fare_type")
                    else "UNKNOWN"
                )

                log.success(
                    "Tickets issued successfully",
                    ticket_count=len(ticket_numbers),
                    fare_type=fare_type,
                )

                # Get cancellation_policy_text from request (if sent from frontend), cache, or DB
                cancellation_policy_text = (
                    request.cancellation_policy_text
                    if hasattr(request, "cancellation_policy_text")
                    and request.cancellation_policy_text
                    else None
                )

                # If not in request, try cache
                if not cancellation_policy_text:
                    cancellation_policy_text = _cancellation_policy_cache.get(
                        voya_booking_reference
                    )

                # If not in cache, try to get from booking event in DB
                if not cancellation_policy_text:
                    try:
                        booking_event = (
                            await BookingService.get_latest_booking_by_voya_reference(
                                voya_booking_reference
                            )
                        )
                        if booking_event and booking_event.cancellation_policy_text:
                            cancellation_policy_text = (
                                booking_event.cancellation_policy_text
                            )
                            log.info(
                                "Retrieved cancellation_policy_text from booking event",
                                policy_length=len(cancellation_policy_text)
                                if cancellation_policy_text
                                else 0,
                            )
                    except Exception as db_error:
                        logger.debug(
                            "Failed to retrieve cancellation_policy_text from booking event: %s",
                            db_error,
                        )

                # If still not available, try to fetch it from fare rules (fallback)
                if not cancellation_policy_text:
                    cancellation_policy_text = (
                        await self._fetch_cancellation_policy_from_fare_rules(
                            external_ref, voya_booking_reference, log
                        )
                    )

                refreshed_trip_details = await self.get_trip_details(
                    TripDetailsRequest.model_validate(
                        {"voya_booking_reference": voya_booking_reference}
                    ),
                    skip_logging=True,
                    skip_validation=True,
                )

                # Send ticket issued email with PDF attachment
                await FlightEventHandler.handle_tickets_issued(
                    user_id,
                    external_ref,
                    ticket_numbers,
                    voya_booking_reference,
                    refreshed_trip_details,
                    cancellation_policy_text=cancellation_policy_text,
                )

                # GDS: set date_tickets_issued when ticket order API succeeded
                await BookingService.update_booking_dates_and_flags(
                    voya_booking_reference,
                    date_tickets_issued=datetime.now(UTC),
                )

                # Clear from cache after tickets are issued (no longer needed)
                if voya_booking_reference in _cancellation_policy_cache:
                    del _cancellation_policy_cache[voya_booking_reference]
                    logger.debug(
                        f"Cleared cancellation_policy_text from cache for {voya_booking_reference}"
                    )
            else:
                errors = response.errors if hasattr(response, "errors") else []
                error_msg = errors[0].message if errors else "Unknown error"
                log.warning("Ticket issuance failed", error_message=error_msg)

            return response

        except Exception as e:
            log.error("Ticket issuance failed", exc=e)
            raise

    async def cancel_booking(
        self, request: FlightCancelRequest
    ) -> FlightCancelResponse:
        """Cancel an existing booking using VOYA reference.

        Auto-populates external_booking_reference and validates user ownership.
        """
        if not self.current_user:
            raise InvalidTokenError("Authentication required for cancellation")

        user_id = str(self.current_user.id)
        voya_booking_reference = request.voya_booking_reference

        # Security: Validate user owns this booking
        await BookingService.validate_user_owns_booking(voya_booking_reference, user_id)

        # Auto-populate external reference
        external_ref = await self._ensure_external_reference(request)

        log = FlightLogger(
            "CANCEL",
            **self._get_base_log_context(),
            voya_booking_reference=voya_booking_reference,
            external_booking_reference=external_ref,
        )

        log.started()

        try:
            # Pass request directly to client (no conversion needed)
            response = await self.client.cancel_booking(request)

            if response.success:
                # Same reference returned for confirmation
                cancelled_ref = (
                    response.external_booking_reference
                    if response.external_booking_reference
                    else external_ref
                )

                log.success(
                    "Booking cancelled successfully", cancelled_reference=cancelled_ref
                )

                # Send cancellation email
                await FlightEventHandler.handle_booking_cancelled(
                    user_id, external_ref, response.external_booking_reference
                )

                # Save simplified cancellation
                try:
                    booking_service = BookingService(user_id)
                    cancellation_request = CreateBookingEventRequest.model_validate(
                        {
                            "external_booking_reference": external_ref,
                            "action": "CANCELLED",
                            "event_type": "FLIGHT",
                        }
                    )
                    await booking_service.create_booking(cancellation_request)

                except Exception as e:
                    log.warning(
                        "Failed to save cancellation event to database",
                        error_message=str(e),
                    )

                try:
                    await BookingService.release_voucher_for_booking_if_any(
                        user_id, voya_booking_reference
                    )
                except Exception as e:
                    log.warning(
                        "Failed to release voucher after cancellation",
                        error_message=str(e),
                    )

            else:
                error_msg = (
                    response.errors[0].message if response.errors else "Unknown error"
                )
                log.warning("Booking cancellation failed", error_message=error_msg)

            return response

        except Exception as e:
            log.error("Booking cancellation failed", exc=e)
            raise

    # ============================================================
    # INFORMATION OPERATIONS
    # ============================================================

    async def get_fare_rules(
        self, request: FlightFareRulesRequest
    ) -> FlightFareRulesResponse:
        """Get fare rules and restrictions."""
        fare_code = self._truncate_sensitive_code(request.fare_source_code)

        log = FlightLogger(
            "GET_FARE_RULES", **self._get_base_log_context(), fare_code=fare_code
        )

        log.started()

        try:
            response = await self.client.get_fare_rules(request)
            log.success("Fare rules retrieved successfully")
            return response
        except Exception as e:
            log.error("Failed to retrieve fare rules", exc=e)
            raise

    async def _fetch_cancellation_policy_from_fare_rules(
        self,
        external_booking_reference: str,
        voya_booking_reference: str,
        log: FlightLogger,
    ) -> str | None:
        """Fetch cancellation policy from fare rules by looking up booking session.

        This method:
        1. Finds the booking session by external_booking_reference
        2. Extracts fare_source_code and session_id from the session
        3. Calls get_fare_rules to fetch the policy
        4. Extracts cancellation_policy_text from the response

        Returns:
            Cancellation policy text or None if not available
        """
        try:
            from app.domains.booking_sessions.service import BookingSessionService

            # Get booking session by external reference
            session = await BookingSessionService.get_session_by_external_ref(
                external_booking_reference
            )

            if not session:
                logger.debug(
                    "No booking session found for fare rules lookup: external=%s",
                    external_booking_reference,
                )
                return None

            session_data = session.get("data", {})
            selected_flight = session_data.get("selected_flight", {})

            # Extract fare_source_code - check multiple possible locations
            fare_source_code = None
            if selected_flight:
                # Priority 1: selected_flight.fare_source_code (api_select_v2 flow)
                fare_source_code = selected_flight.get("fare_source_code")
                if not fare_source_code:
                    # Priority 2: itinerary.updated_pricing.updated_fare_source_code
                    itinerary = selected_flight.get("itinerary", {})
                    updated_pricing = itinerary.get("updated_pricing", {})
                    fare_source_code = updated_pricing.get("updated_fare_source_code")

            # Extract session_id (FlightLogic session)
            fl_session_id = session_data.get("fl_session_id")
            if not fl_session_id:
                # Fallback to session_id from the session
                fl_session_id = session.get("session_id")

            if not fare_source_code or not fl_session_id:
                logger.debug(
                    "Missing fare_source_code or session_id in booking session "
                    "(has_fare=%s has_session=%s)",
                    fare_source_code is not None,
                    fl_session_id is not None,
                )
                return None

            # Check for inbound_fare_code (round trips)
            inbound_fare_code = None
            if selected_flight:
                itinerary = selected_flight.get("itinerary", {})
                updated_pricing = itinerary.get("updated_pricing", {})
                inbound_fare_code = updated_pricing.get(
                    "updated_inbound_fare_source_code"
                )

            # Build fare rules request
            fare_rules_request = FlightFareRulesRequest(
                session_id=fl_session_id,
                fare_source_code=fare_source_code,
                inbound_fare_source_code=inbound_fare_code,
            )

            # Fetch fare rules
            log.info(
                "Fetching cancellation policy from fare rules",
                voya_booking_reference=voya_booking_reference,
            )
            fare_rules_response = await self.get_fare_rules(fare_rules_request)

            # Extract cancellation policy text from fare rules
            cancellation_policy_text = (
                self._extract_cancellation_policy_from_fare_rules(fare_rules_response)
            )

            if cancellation_policy_text:
                log.info(
                    "✅ Successfully fetched cancellation policy from fare rules",
                    policy_length=len(cancellation_policy_text),
                )
            else:
                logger.debug("No cancellation policy found in fare rules response")

            return cancellation_policy_text

        except Exception as e:
            log.warning(
                "Failed to fetch cancellation policy from fare rules",
                exc=e,
                voya_booking_reference=voya_booking_reference,
            )
            # Don't fail ticket issuance if we can't fetch cancellation policy
            return None

    @staticmethod
    def _extract_cancellation_policy_from_fare_rules(
        fare_rules_response: FlightFareRulesResponse,
    ) -> str | None:
        """Extract cancellation policy text from fare rules response.

        Combines all rule_description fields from fare_rules and inbound_fare_data.
        """
        if not fare_rules_response:
            return None

        policy_parts = []

        # Extract from main fare_rules
        if fare_rules_response.fare_rules:
            for rule in fare_rules_response.fare_rules:
                if rule.rule_description and rule.rule_description.strip():
                    policy_parts.append(rule.rule_description.strip())

        # Extract from inbound fare rules (round trips)
        if (
            fare_rules_response.inbound_fare_data
            and fare_rules_response.inbound_fare_data.fare_rules
        ):
            inbound_rules = []
            for rule in fare_rules_response.inbound_fare_data.fare_rules:
                if rule.rule_description and rule.rule_description.strip():
                    inbound_rules.append(rule.rule_description.strip())

            if inbound_rules:
                policy_parts.append("--- Return Flight ---")
                policy_parts.extend(inbound_rules)

        if policy_parts:
            return "\n\n".join(policy_parts)

        return None

    async def get_extra_services(
        self, request: FlightExtraServicesRequest
    ) -> FlightExtraServicesResponse:
        """Get available extra services for a flight."""
        fare_code = self._truncate_sensitive_code(request.fare_source_code)

        log = FlightLogger(
            "GET_EXTRA_SERVICES", **self._get_base_log_context(), fare_code=fare_code
        )

        log.started()

        try:
            response = await self.client.get_extra_services(request)
            log.success("Extra services retrieved successfully")
            return response
        except Exception as e:
            log.error("Failed to retrieve extra services", exc=e)
            raise

    async def get_trip_details(
        self,
        request: TripDetailsRequest,
        skip_logging: bool = False,
        skip_validation: bool = False,
    ) -> TripDetailsResponse:
        """Get complete trip/booking details using VOYA reference.

        Auto-populates external_booking_reference and validates user ownership.

        Args:
            request: Trip details request with VOYA booking reference
            skip_logging: If True, skip logging (for internal calls within other operations)
            skip_validation: If True, skip booking ownership validation (for internal post-booking calls)
        """
        if not self.current_user:
            raise InvalidTokenError("Authentication required")

        user_id = str(self.current_user.id)
        voya_booking_reference = request.voya_booking_reference

        # Skip ownership validation for internal callers or for admin/super_admin
        is_admin = self.current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
        effective_skip_validation = skip_validation or is_admin

        # Security: Validate user owns this booking (unless skipped for internal calls or admin)
        if not effective_skip_validation:
            if not voya_booking_reference:
                raise ValueError(
                    "voya_booking_reference is required when ownership validation applies"
                )
            await BookingService.validate_user_owns_booking(
                voya_booking_reference, user_id
            )

        # Auto-populate external reference
        external_ref = await self._ensure_external_reference(request)

        log = None
        if not skip_logging:
            log = FlightLogger(
                "GET_TRIP_DETAILS",
                **self._get_base_log_context(),
                voya_booking_reference=voya_booking_reference,
                external_booking_reference=external_ref,
            )
            log.started()

        try:
            # Pass request directly to client (no conversion needed)
            response = await self.client.get_trip_details(request)

            # Ensure voya_booking_reference is included in response
            response.voya_booking_reference = voya_booking_reference

            parent_ref: str | None = None
            if voya_booking_reference:
                parent_ref = (
                    await BookingService.get_parent_voya_booking_reference_for_leg(
                        voya_booking_reference
                    )
                )
            response = response.model_copy(
                update={"parent_voya_booking_reference": parent_ref}
            )

            # Apply platform fee to pricing for consistent display (trip details returns original airline price)
            if response.pricing and response.pricing.fare_totals:
                apply_platform_fee_to_fare_totals(response.pricing.fare_totals)

            # Enrich airport info with country codes for accurate cross-border detection
            await self._enrich_airport_country_codes(response)

            # Check for ticketed booking with missing PNR/e-ticket (data quality alert)
            if _is_ticketed_missing_pnr_or_eticket(response):
                task = asyncio.create_task(
                    notify_booking_error(
                        "Trip Details API",
                        "PNR or e-ticket number are missing for ticketed booking",
                        context={
                            "UniqueID": response.external_booking_reference or "unknown"
                        },
                    )
                )
                _trip_details_notify_tasks.add(task)
                task.add_done_callback(_trip_details_notify_tasks.discard)

            if voya_booking_reference:
                try:
                    await self._sync_booking_from_trip_details(
                        voya_booking_reference, response
                    )
                except Exception as sync_error:
                    logger.warning(
                        "Failed to sync booking from trip details for %s: %s",
                        voya_booking_reference,
                        sync_error,
                    )

            if log:
                log.success("Trip details retrieved successfully")
            return response
        except Exception as e:
            if log:
                log.error("Failed to retrieve trip details", exc=e)
            raise

    async def get_multicity_booking_group(
        self, voya_booking_reference: str
    ) -> MulticityBookingGroupResponse:
        """Mongo-backed multicity siblings for a VOYA reference (same user)."""
        if not self.current_user:
            raise InvalidTokenError("Authentication required")
        user_id = str(self.current_user.id)
        return await BookingService.list_multicity_group_for_voya_reference(
            user_id, voya_booking_reference
        )

    async def get_user_bookings(self, limit: int = 10) -> list[BookingEventResponse]:
        """Get user's flight booking events (typed list for profile / my-bookings API)."""

        if not self.current_user:
            raise InvalidTokenError("Authentication required")
        db = await get_database()
        user_id_str = str(self.current_user.id)
        user_id_filter = booking_events_user_id_filter(user_id_str)
        query = {"user_id": user_id_filter, "event_type": "FLIGHT"}

        log = FlightLogger(
            "GET_USER_BOOKINGS", **self._get_base_log_context(), limit=limit
        )

        log.started()

        try:
            raw_bookings = (
                await db["booking_events"]
                .find(query)
                .sort("timestamp", -1)
                .limit(limit)
                .to_list(limit)
            )

            user_bookings: list[BookingEventResponse] = []
            for booking in raw_bookings:
                try:
                    user_bookings.append(booking_document_to_response(dict(booking)))
                except MalformedBookingEventDocumentError as e:
                    logger.warning(
                        "Skipping malformed booking_events row in my-bookings: %s", e
                    )

            log.success(
                "User bookings retrieved successfully", count=len(user_bookings)
            )
            return user_bookings

        except Exception as e:
            log.error("Failed to retrieve user bookings", exc=e)
            raise

    # ============================================================
    # AIRPORT OPERATIONS
    # ============================================================

    async def get_airport_list(
        self, request: AirportListRequest
    ) -> AirportListResponse:
        """Get list of commercial airports from FlightLogic.

        Returns a curated list of commercial airports, excluding private
        and military airports. Uses in-memory cache with 24-hour TTL to
        reduce API calls.

        Args:
            request: Airport list request

        Returns:
            Airport list response with commercial airports
        """
        log = FlightLogger("GET_AIRPORT_LIST", **self._get_base_log_context())

        log.started()

        try:
            # Check cache first
            cached_response = AirportListCache.get()
            if cached_response:
                airport_count = len(cached_response.airports)
                log.success(
                    "Airport list retrieved from cache",
                    airport_count=airport_count,
                )
                return cached_response

            # Cache miss - fetch from FlightLogic API
            response = await self.client.get_airport_list(request)

            # Cache the response for future requests
            AirportListCache.set(response)

            airport_count = len(response.airports)
            log.success(
                "Airport list retrieved successfully and cached",
                airport_count=airport_count,
            )
            return response
        except Exception as e:
            log.error("Failed to retrieve airport list", exc=e)
            raise

    async def get_airline_list(
        self, request: AirlineListRequest
    ) -> AirlineListResponse:
        """Get list of airlines with logos from FlightLogic.

        Returns airlines supported by the API with codes, names, and logo URLs.
        Uses in-memory cache with 24-hour TTL. Used internally to enrich
        flight search results with airline logos.

        Args:
            request: Airline list request

        Returns:
            Airline list response with airlines (iata_code, name, logo_url)
        """
        # Check cache first
        cached_response = AirlineListCache.get()
        if cached_response:
            return cached_response

        # Cache miss - fetch from FlightLogic API
        response = await self.client.get_airline_list(request)

        # Cache the response for future requests
        AirlineListCache.set(response)

        return response

    def _enrich_airline_logos(
        self,
        response: FlightSearchResponse,
        code_to_logo: dict[str, str],
    ) -> None:
        """Enrich marketing_airline and operating_airline with logo_url for each segment.

        Mutates response in place. Looks up logo by iata_code from airline list.
        """
        itineraries = list(response.fare_itineraries)
        if response.inbound_fare_itineraries:
            itineraries = itineraries + list(response.inbound_fare_itineraries)

        for fare_itinerary in itineraries:
            for leg in fare_itinerary.flight_legs:
                for segment in leg.flight_segments:
                    if segment.marketing_airline:
                        logo = code_to_logo.get(segment.marketing_airline.iata_code)
                        if logo:
                            segment.marketing_airline.logo_url = logo
                    if segment.operating_airline:
                        logo = code_to_logo.get(segment.operating_airline.iata_code)
                        if logo:
                            segment.operating_airline.logo_url = logo

    async def _get_airports_data(self) -> list:
        """Get airport list data (helper for airport resolution methods).

        Returns:
            List of AirportListItem objects from FlightLogic
        """
        response = await self.get_airport_list(AirportListRequest.model_validate({}))
        return response.airports

    async def get_airport_info(self, iata_code: str) -> dict[str, Any] | None:
        """Get airport information by IATA code using FlightLogic data.

        Args:
            iata_code: 3-letter IATA code

        Returns:
            Dictionary with airport info (iata_code, airport_name, city, country) or None
        """
        airports = await self._get_airports_data()
        for airport in airports:
            if airport.iata_code.upper() == iata_code.upper():
                return {
                    "iata": airport.iata_code.upper(),
                    "iata_code": airport.iata_code.upper(),
                    "name": airport.airport_name,
                    "airport_name": airport.airport_name,
                    "city": airport.city,
                    "country": airport.country,
                }
        return None

    async def resolve_airport(self, location: str) -> str | None:
        """Resolve location string to IATA airport code using FlightLogic data.

        Supports:
        - City names (e.g., "Calgary", "New York")
        - Airport names (e.g., "John F Kennedy International")
        - IATA codes (e.g., "YYC", "JFK")

        Args:
            location: Location string to resolve

        Returns:
            IATA code if found, None otherwise
        """
        if not location:
            return None

        location = location.strip()
        location_lower = location.lower()
        location_upper = location.upper()

        airports = await self._get_airports_data()

        # Priority city mappings for major cities
        priority_city_mappings = {
            "new york": "JFK",
            "nyc": "JFK",
            "manhattan": "JFK",
            "los angeles": "LAX",
            "la": "LAX",
            "chicago": "ORD",
            "san francisco": "SFO",
            "sf": "SFO",
            "miami": "MIA",
            "boston": "BOS",
            "atlanta": "ATL",
            "seattle": "SEA",
            "dallas": "DFW",
            "denver": "DEN",
            "las vegas": "LAS",
            "vegas": "LAS",
            "orlando": "MCO",
            "washington": "DCA",
            "dc": "DCA",
            "austin": "AUS",
            "london": "LHR",
            "paris": "CDG",
            "madrid": "MAD",
            "barcelona": "BCN",
            "rome": "FCO",
            "milan": "MXP",
            "amsterdam": "AMS",
            "frankfurt": "FRA",
            "munich": "MUC",
            "berlin": "BER",
            "zurich": "ZRH",
            "vienna": "VIE",
            "brussels": "BRU",
            "lisbon": "LIS",
            "athens": "ATH",
            "dublin": "DUB",
            "tokyo": "NRT",
            "dubai": "DXB",
            "singapore": "SIN",
            "hong kong": "HKG",
            "beijing": "PEK",
            "shanghai": "PVG",
            "seoul": "ICN",
            "bangkok": "BKK",
            "delhi": "DEL",
            "mumbai": "BOM",
            "sydney": "SYD",
            "melbourne": "MEL",
            "toronto": "YYZ",
            "vancouver": "YVR",
            "montreal": "YUL",
        }

        # Strategy 1: Direct IATA code (3 letters)
        if len(location) == 3 and location_upper.isalpha():
            for airport in airports:
                if airport.iata_code.upper() == location_upper:
                    return airport.iata_code.upper()

        # Strategy 2: Priority city mappings
        if location_lower in priority_city_mappings:
            priority_code = priority_city_mappings[location_lower]
            for airport in airports:
                if airport.iata_code.upper() == priority_code:
                    return airport.iata_code.upper()

        # Strategy 3: City name lookup (exact match)
        for airport in airports:
            if airport.city.lower() == location_lower:
                return airport.iata_code.upper()

        # Strategy 4: Airport name lookup (exact match)
        for airport in airports:
            if airport.airport_name.lower() == location_lower:
                return airport.iata_code.upper()

        # Strategy 5: Partial matching for city names
        query_words = set(location_lower.split())
        best_match = None
        best_score = 0.0

        for airport in airports:
            city_lower = airport.city.lower()
            city_words = set(city_lower.split())
            overlap = len(query_words & city_words)
            if overlap > 0:
                score = overlap / len(city_words) if city_words else 0
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = airport

        if best_match:
            return best_match.iata_code.upper()

        # Strategy 6: Partial matching for airport names
        best_match = None
        best_score = 0.0

        for airport in airports:
            name_lower = airport.airport_name.lower()
            name_words = set(name_lower.split())
            overlap = len(query_words & name_words)
            if overlap > 0:
                score = overlap / len(name_words) if name_words else 0
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = airport

        if best_match:
            return best_match.iata_code.upper()

        return None

    async def get_city_airports(self, city_name: str) -> list[dict[str, Any]]:
        """Get all airports for a city using FlightLogic.

        This method is used for multi-airport city preference flow (Issue #12).
        Uses FlightService to get airports from FlightLogic data.

        Args:
            city_name: City name to look up (e.g., "London", "New York")

        Returns:
            List of airport dictionaries with iata, name, city, country.
            Empty list if city not found or has no airports.

        Example:
            >>> await service.get_city_airports("London")
            [
                {"iata": "LHR", "name": "London Heathrow", "city": "London", "country": "United Kingdom"},
                {"iata": "LGW", "name": "London Gatwick", "city": "London", "country": "United Kingdom"},
                ...
            ]
        """
        airports = await self._get_airports_data()
        city_lower = city_name.lower().strip()

        matching_airports = []
        for airport in airports:
            if airport.city.lower() == city_lower:
                matching_airports.append(
                    {
                        "iata": airport.iata_code.upper(),
                        "name": airport.airport_name,
                        "city": airport.city,
                        "country": airport.country,
                    }
                )

        return matching_airports


def get_flight_service(
    current_user: Annotated[
        UserPublic | None,
        Depends(get_current_user(required=False)),
    ],
) -> "FlightService":
    """FastAPI dependency: injects the current user when resolving this dependency.

    Do not call with zero arguments outside FastAPI — use ``FlightService(user)`` instead.
    """
    return FlightService(current_user)
