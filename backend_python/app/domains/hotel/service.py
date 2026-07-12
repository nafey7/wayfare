"""Hotel service - clean domain service following flight service patterns."""

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from bson import ObjectId  # noqa: TC002
from fastapi import Depends

from app.database.dependencies import get_database
from app.domains.auth.dependencies import get_current_user
from app.domains.bookings.constants import BOOKING_EVENT_COLLECTION
from app.domains.bookings.user_id_mongo_filter import booking_events_user_id_filter
from app.domains.saved_itinerary import ensure_saved_itinerary_owned_by_user
from app.shared.geo import haversine_km

from ..user import UserPublic
from .cache import HotelSessionCache
from .events import HotelEventHandler
from .exceptions import HotelBookingError, HotelSearchError
from .json_float import finite_float_from_hotel_json, first_dict_coord_value
from .logger import HotelLogger
from .pricing import (
    HOTELS_DISCOUNT_PERCENTAGE,
    apply_platform_fee,
    apply_platform_fee_to_hotel_price,
    apply_platform_fee_to_room_option,
)
from .schemas import (
    HotelBookingDetailsRequest,
    HotelBookingDetailsResponse,
    HotelBookingRequest,
    HotelBookingResponse,
    HotelCancelRequest,
    HotelCancelResponse,
    HotelMoreResultsRequest,
    HotelMyBookingListItem,
    HotelRateRulesRequest,
    HotelRateRulesResponse,
    HotelRoomRatesRequest,
    HotelRoomRatesResponse,
    HotelSearchRequest,
    HotelSearchResponse,
    HotelSearchResult,
    HotelTripDetailsRequest,
    HotelTripDetailsResponse,
    NearbyLocation,
)
from .stay_snapshot import hotel_stay_from_booking_details
from .validators import (
    validate_search_request,
    validate_session_id,
    validate_token_id,
)

logger = logging.getLogger(__name__)


class _BookingEventHotelDisplay(Protocol):
    """Structural type: booking_events rows with optional hotel list fields."""

    hotel_name: str | None
    hotel_city: str | None
    hotel_address: str | None
    hotel_image_url: str | None
    hotel_latitude: float | None
    hotel_longitude: float | None


def _booking_details_has_geo_pair(bd: dict[str, Any]) -> bool:
    lat = finite_float_from_hotel_json(
        first_dict_coord_value(bd, "latitude", "hotel_latitude", "lat")
    )
    lng = finite_float_from_hotel_json(
        first_dict_coord_value(bd, "longitude", "hotel_longitude", "lng", "lon")
    )
    return lat is not None and lng is not None


def _overlay_booking_event_display_on_details(
    booking_details: dict[str, Any] | None,
    event: _BookingEventHotelDisplay,
) -> dict[str, Any]:
    """Merge name, city, address, image, and coordinates from booking_events when the supplier omits them.

    FlightLogic booking-details payloads may not repeat marketing fields; Mongo stores
    hotel_name, hotel_city, hotel_address, hotel_image_url, and lat/long at book time for list/profile UIs.
    """
    bd: dict[str, Any] = dict(booking_details or {})

    def _blank(v: Any) -> bool:
        if v is None:
            return True
        return isinstance(v, str) and not v.strip()

    if (
        _blank(bd.get("hotel_name"))
        and event.hotel_name
        and str(event.hotel_name).strip()
    ):
        bd["hotel_name"] = event.hotel_name

    if _blank(bd.get("city")) and event.hotel_city and str(event.hotel_city).strip():
        bd["city"] = event.hotel_city

    ev_addr = getattr(event, "hotel_address", None)
    if _blank(bd.get("address")) and ev_addr and str(ev_addr).strip():
        bd["address"] = str(ev_addr).strip()

    imgs = bd.get("images")
    has_images_list = isinstance(imgs, list) and any(
        isinstance(x, str) and x.strip() for x in imgs
    )
    has_single = not _blank(
        bd.get("image") or bd.get("image_url") or bd.get("thumbnail_url")
    )
    if (
        not has_images_list
        and not has_single
        and event.hotel_image_url
        and str(event.hotel_image_url).strip()
    ):
        bd["image"] = str(event.hotel_image_url).strip()

    if not _booking_details_has_geo_pair(bd):
        elat = finite_float_from_hotel_json(event.hotel_latitude)
        elng = finite_float_from_hotel_json(event.hotel_longitude)
        if elat is not None and elng is not None:
            bd["latitude"] = elat
            bd["longitude"] = elng

    return bd


def _mongo_doc_to_hotel_my_booking(doc: dict) -> HotelMyBookingListItem:
    """Map raw booking_events document to hotel my-bookings list item."""
    stored = doc.get("action")
    if stored in ("BOOKED", "CANCELLED", "PENDING"):
        action: str = stored
    elif not stored:
        action = "BOOKED"
    else:
        logger.debug(
            "Unknown booking action %r; defaulting to BOOKED (hotel my-bookings list)",
            stored,
        )
        action = "BOOKED"
    return HotelMyBookingListItem(
        voya_booking_reference=doc.get("voya_booking_reference"),
        action=action,  # type: ignore[arg-type]
        timestamp=doc["timestamp"],
        date_booked=doc.get("date_booked"),
        amount=doc.get("amount"),
        hotel_image_url=doc.get("hotel_image_url"),
        hotel_name=doc.get("hotel_name"),
        hotel_city=doc.get("hotel_city"),
        hotel_check_in_date=doc.get("hotel_check_in_date"),
        hotel_check_out_date=doc.get("hotel_check_out_date"),
        hotel_nights=doc.get("hotel_nights"),
    )


class HotelService:
    """Instance-based hotel service with user context for environment detection."""

    def __init__(self, current_user: "UserPublic | None" = None) -> None:
        """Initialize hotel service with user context."""
        # Lazy import to avoid circular dependency
        from integrations.flightlogic import get_flights_client

        self.current_user = current_user
        self.client = get_flights_client(current_user)  # Uses same client for now

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

    def _truncate_session_id(self, session_id: str | None, max_len: int = 12) -> str:
        """Truncate session IDs for logging."""
        if not session_id:
            return "N/A"
        return session_id[:max_len] + "..." if len(session_id) > max_len else session_id

    # ============================================================
    # SORT HELPER
    # ============================================================

    @staticmethod
    def _apply_nearby_sort(
        itineraries: list[HotelSearchResult],
        nearby_location: NearbyLocation,
    ) -> None:
        """Compute Haversine distance from nearby_location to each hotel and sort ascending.

        Hotels with missing coordinates get nearby_distance_km = None and are
        appended at the end using float('inf') as a sort sentinel.
        Mutates itineraries in place.
        """
        for hotel in itineraries:
            try:
                coords = hotel.get_lat_lng()
            except (ValueError, TypeError):
                coords = None

            if coords is not None:
                dist = haversine_km(
                    nearby_location.lat,
                    nearby_location.lng,
                    coords[0],
                    coords[1],
                )
                hotel.nearby_distance_km = round(dist, 3)
            else:
                hotel.nearby_distance_km = None

        itineraries.sort(
            key=lambda h: h.nearby_distance_km
            if h.nearby_distance_km is not None
            else float("inf")
        )

    # ============================================================
    # SEARCH OPERATIONS
    # ============================================================

    async def search_hotels(self, request: HotelSearchRequest) -> HotelSearchResponse:
        """Search for available hotels with event handling."""
        # Build location string for logging
        location = "N/A"
        if request.city_name and request.country_name:
            location = f"{request.city_name}, {request.country_name}"
        elif request.latitude and request.longitude:
            location = f"{request.latitude:.4f}, {request.longitude:.4f}"
        elif request.hotel_codes:
            location = f"{len(request.hotel_codes)} specific hotels"

        # Calculate nights
        from datetime import datetime

        # Using naive datetime for date-only parsing (no timezone needed)
        checkin_date = datetime.strptime(request.checkin, "%Y-%m-%d").date()  # noqa: DTZ007
        checkout_date = datetime.strptime(request.checkout, "%Y-%m-%d").date()  # noqa: DTZ007
        nights = (checkout_date - checkin_date).days

        # Calculate total guests
        total_rooms = len(request.occupancy)
        total_guests = sum(room.adult + room.child for room in request.occupancy)

        log_context = {
            **self._get_base_log_context(),
            "location": location,
            "checkin": request.checkin,
            "checkout": request.checkout,
            "nights": str(nights),
            "occupancy": {"rooms": total_rooms, "guests": total_guests},
        }

        log = HotelLogger("SEARCH", **log_context)
        log.started(f"location={location}")

        try:
            # Validate request
            validate_search_request(request)

            # Make API call via FlightLogic client
            response = await self.client.search_hotels(request)

            # Apply platform fee (10.5%) to all hotel prices
            for hotel in response.itineraries:
                apply_platform_fee_to_hotel_price(hotel)

            # Sort by distance from nearby_location when provided (after fee so values are final)
            if request.nearby_location is not None:
                self._apply_nearby_sort(response.itineraries, request.nearby_location)

            # Cache search response for room rates and booking
            if self.current_user and response.session_id:
                HotelSessionCache.set(
                    user_id=str(self.current_user.id),
                    session_id=response.session_id,
                    search_response=response,
                )

            log.success(
                f"hotels={response.total_results}",
                hotels=response.total_results,
                session_id=self._truncate_session_id(response.session_id),
            )
            return response

        except Exception as e:
            log.error(f"Hotel search failed: {e!s}", exc=e)
            # If it's already a HotelSearchError, just re-raise it to avoid double-wrapping
            from app.domains.hotel.exceptions import HotelSearchError

            if isinstance(e, HotelSearchError):
                raise
            raise HotelSearchError(reason=str(e)) from e

    async def get_more_results(
        self, request: "HotelMoreResultsRequest"
    ) -> "HotelSearchResponse":
        """Get additional hotel search results using pagination token.

        This should be called when moreResults is true in the search response
        to fetch additional hotels using the nextToken.

        Args:
            request: More results request with session ID and next token

        Returns:
            Hotel search response with additional results

        Raises:
            HotelSearchError: If fetching more results fails
        """
        log_context = {
            **self._get_base_log_context(),
            "session_id": self._truncate_session_id(request.session_id),
            "next_token": request.next_token[:12] + "..."
            if len(request.next_token) > 12
            else request.next_token,
        }

        log = HotelLogger("MORE_RESULTS", **log_context)
        log.started(f"max_result={request.max_result}")

        try:
            # Validate session ID
            validate_session_id(request.session_id)

            # Make API call via FlightLogic client
            response = await self.client.get_more_results(request)

            # Apply platform fee (10.5%) to all hotel prices
            for hotel in response.itineraries:
                apply_platform_fee_to_hotel_price(hotel)

            # Sort by distance from nearby_location when provided (after fee so values are final)
            if request.nearby_location is not None:
                self._apply_nearby_sort(response.itineraries, request.nearby_location)

            log.success(
                f"hotels={len(response.itineraries)}",
                hotels=len(response.itineraries),
                total_results=response.total_results,
                more_results=response.more_results,
                session_id=self._truncate_session_id(response.session_id),
            )
            return response

        except Exception as e:
            log.error(f"Failed to get more results: {e!s}", exc=e)
            raise HotelSearchError(reason=str(e)) from e

    # ============================================================
    # ROOM RATES OPERATIONS
    # ============================================================

    async def get_room_rates(
        self, request: HotelRoomRatesRequest
    ) -> HotelRoomRatesResponse:
        """Get detailed room rates for a specific hotel."""
        log_context = {
            **self._get_base_log_context(),
            "session_id": self._truncate_session_id(request.session_id),
            "token_id": request.token_id[:12] + "..." if request.token_id else "N/A",
        }

        log = HotelLogger("RATES", **log_context)
        log.started()

        try:
            # Validate session ID and token
            validate_session_id(request.session_id)
            validate_token_id(request.token_id)

            # Make API call
            response = await self.client.get_room_rates(request)

            # Apply platform fee (10.5%) to all room prices
            for room in response.rooms:
                apply_platform_fee_to_room_option(room)

            log.success(
                f"rooms={len(response.rooms)}", room_options=len(response.rooms)
            )
            return response

        except Exception as e:
            log.error(f"Failed to get room rates: {e!s}", exc=e)
            raise HotelSearchError(reason=f"Room rates error: {e!s}") from e

    async def check_rate_rules(
        self, request: "HotelRateRulesRequest"
    ) -> "HotelRateRulesResponse":
        """Validate hotel rate rules before booking.

        This should be called before booking to ensure rates are still valid
        and get detailed cancellation policies and room information.

        Args:
            request: Rate rules request with session and rate identifiers

        Returns:
            Validated rate information with pricing and policies

        Raises:
            HotelSearchError: If rate validation fails
        """

        log_context = {
            **self._get_base_log_context(),
            "session_id": self._truncate_session_id(request.session_id),
            "rate_basis_id": request.rate_basis_id[:12] + "..."
            if request.rate_basis_id
            else "N/A",
        }

        log = HotelLogger("RATE_RULES", **log_context)
        log.started()

        try:
            # Validate session ID
            validate_session_id(request.session_id)

            # Make API call
            response = await self.client.check_rate_rules(request)

            # Apply platform fee (10.5%) to net_price
            original_net_price = response.net_price
            response.net_price = apply_platform_fee(original_net_price)
            response.original_net_price = original_net_price
            response.platform_fee_percentage = float(HOTELS_DISCOUNT_PERCENTAGE)

            log.success(
                "validated=True",
                room_type=response.room_type,
                net_price=float(response.net_price),
                currency=response.currency,
            )
            return response

        except Exception as e:
            log.error(f"Failed to validate rate rules: {e!s}", exc=e)
            raise HotelSearchError(reason=f"Rate validation error: {e!s}") from e

    # ============================================================
    # BOOKING OPERATIONS
    # ============================================================

    async def create_booking(
        self, request: HotelBookingRequest
    ) -> HotelBookingResponse:
        """Create a hotel booking with payment and event handling."""
        log_context = {
            **self._get_base_log_context(),
            "session_id": self._truncate_session_id(request.session_id),
            "guest_email": request.customer_email,
        }

        log = HotelLogger("BOOK", **log_context)
        log.started()

        try:
            # Validate session ID and rate basis ID
            validate_session_id(request.session_id)
            if not request.rate_basis_id:
                raise HotelBookingError(reason="Rate basis ID is required for booking")

            validated_saved_itinerary_id: ObjectId | None = None
            if self.current_user and request.saved_itinerary_id:
                validated_saved_itinerary_id = (
                    await ensure_saved_itinerary_owned_by_user(
                        str(self.current_user.id), request.saved_itinerary_id
                    )
                )

            # Make API call
            response = await self.client.book_hotel(request)

            # Handle booking result
            if response.status == "Success":
                # Update booking event with supplier confirmation (event was created before API call)
                voya_ref = request.client_ref if request.client_ref else None
                if (
                    voya_ref
                    and voya_ref.startswith("VOYA-")
                    and response.supplier_confirmation_num
                ):
                    try:
                        from app.domains.bookings import BookingService

                        await BookingService.update_external_reference(
                            voya_ref, response.supplier_confirmation_num
                        )
                        if response.reference_num:
                            await BookingService.update_hotel_reference_number(
                                voya_ref, response.reference_num
                            )
                        now_utc = datetime.now(UTC)
                        hotel_amount: float | None = None
                        if response.booking_details:
                            bd = response.booking_details
                            raw = bd.get("original_total_price") or bd.get(
                                "total_price"
                            )
                            if raw is not None:
                                with contextlib.suppress(TypeError, ValueError):
                                    hotel_amount = float(raw)
                        cin, cout, nights = hotel_stay_from_booking_details(
                            response.booking_details or None
                        )
                        await BookingService.update_booking_dates_and_flags(
                            voya_ref,
                            date_booked=now_utc,
                            date_tickets_issued=now_utc,
                            amount=hotel_amount,
                            hotel_check_in_date=cin,
                            hotel_check_out_date=cout,
                            hotel_nights=nights,
                            saved_itinerary_id=validated_saved_itinerary_id,
                        )
                    except Exception as update_err:
                        logger.warning(
                            "Failed to update hotel booking event external reference: %s",
                            update_err,
                        )

                # Display reference for email: VOYA ref if we have it, else external
                booking_reference = (
                    voya_ref
                    or response.reference_num
                    or response.supplier_confirmation_num
                )

                if self.current_user:
                    try:
                        # Send confirmation email
                        await HotelEventHandler.handle_booking_confirmed(
                            user_id=str(self.current_user.id),
                            external_booking_reference=response.supplier_confirmation_num
                            or "PENDING",
                            reference_num=response.reference_num,
                            booking_details=response.booking_details,
                            voya_booking_reference=booking_reference,
                            booking_request=request,
                        )

                    except Exception as event_error:
                        # Log but don't fail the booking
                        logger.warning(
                            f"Failed to handle booking events: {event_error}"
                        )

                log.success(
                    f"confirmation={response.supplier_confirmation_num[:15]}..."
                    if response.supplier_confirmation_num
                    else "booking_created",
                    confirmation=response.supplier_confirmation_num or "N/A",
                )

            else:
                # Booking failed
                error_msg = (
                    response.errors.get("message", "Unknown error")
                    if response.errors
                    else "Booking failed"
                )

                if self.current_user:
                    from contextlib import suppress

                    with suppress(Exception):
                        # Don't fail on email errors
                        await HotelEventHandler.handle_booking_failed(
                            user_id=str(self.current_user.id),
                            error_message=error_msg,
                            booking_request=request,
                        )

                log.error(f"Booking failed: {error_msg}")
                raise HotelBookingError(reason=error_msg)

            # Add VOYA reference to response (from client_ref in request)
            return response.model_copy(
                update={"voya_booking_reference": request.client_ref}
            )

        except HotelBookingError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            log.error(f"Unexpected booking error: {e!s}", exc=e)
            raise HotelBookingError(reason=f"Booking failed: {e!s}") from e

    # ============================================================
    # CANCELLATION OPERATIONS
    # ============================================================

    async def cancel_booking(self, request: HotelCancelRequest) -> HotelCancelResponse:
        """Cancel a hotel booking.

        Args:
            request: Cancel request with supplier confirmation and reference numbers

        Returns:
            Cancellation confirmation or error details

        Raises:
            HotelBookingError: If cancellation fails
        """
        log_context = {
            **self._get_base_log_context(),
            "supplier_confirmation": request.supplier_confirmation_num[:15] + "..."
            if request.supplier_confirmation_num
            else "N/A",
            "reference_num": request.reference_num[:15] + "..."
            if request.reference_num
            else "N/A",
        }

        log = HotelLogger("CANCEL", **log_context)
        log.started()

        try:
            # Validate required fields
            if not request.supplier_confirmation_num:
                raise HotelBookingError(
                    reason="Supplier confirmation number is required for cancellation"
                )
            if not request.reference_num:
                raise HotelBookingError(
                    reason="Reference number is required for cancellation"
                )

            # Make API call
            response = await self.client.cancel_hotel_booking(request)

            # Handle cancellation result
            if response.status == "CANCELLED":
                log.success(
                    f"cancel_ref={response.cancel_reference_num[:15]}..."
                    if response.cancel_reference_num
                    else "cancelled",
                    cancel_reference=response.cancel_reference_num or "N/A",
                )
            else:
                # Cancellation failed
                error_msg = (
                    response.errors.get("message", "Unknown error")
                    if response.errors
                    else response.message or "Cancellation failed"
                )

                log.error(f"Cancellation failed: {error_msg}")
                raise HotelBookingError(reason=error_msg)

            return response

        except HotelBookingError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            log.error(f"Unexpected cancellation error: {e!s}", exc=e)
            raise HotelBookingError(reason=f"Cancellation failed: {e!s}") from e

    # ============================================================
    # BOOKING DETAILS OPERATIONS
    # ============================================================

    async def get_booking_details(
        self, request: HotelBookingDetailsRequest
    ) -> HotelBookingDetailsResponse:
        """Get complete hotel booking details.

        Args:
            request: Booking details request with supplier confirmation and reference numbers

        Returns:
            Complete booking details or error information

        Raises:
            HotelBookingError: If booking details retrieval fails
        """
        log_context = {
            **self._get_base_log_context(),
            "supplier_confirmation": request.supplier_confirmation_num[:15] + "..."
            if request.supplier_confirmation_num
            else "N/A",
            "reference_num": request.reference_num[:15] + "..."
            if request.reference_num
            else "N/A",
        }

        log = HotelLogger("BOOKING_DETAILS", **log_context)
        log.started()

        try:
            # Make API call via FlightLogic client
            response = await self.client.get_booking_details(request)

            # Apply platform fee to booking details (same as other hotel APIs): add
            # original_net_price and set total_price to price with platform fee
            if response.booking_details:
                details = response.booking_details
                raw_price = (
                    details.get("total_price")
                    or details.get("NetPrice")
                    or details.get("netPrice")
                )
                if raw_price is not None:
                    try:
                        from decimal import Decimal

                        original = (
                            Decimal(str(raw_price))
                            if not isinstance(raw_price, Decimal)
                            else raw_price
                        )
                        if original > 0:
                            with_fee = apply_platform_fee(original)
                            details["original_net_price"] = float(original)
                            details["original_total_price"] = float(original)
                            details["total_price"] = float(with_fee)
                            details["NetPrice"] = float(with_fee)
                            details["platform_fee_percentage"] = float(
                                HOTELS_DISCOUNT_PERCENTAGE
                            )
                    except (TypeError, ValueError) as e:
                        log.warning(
                            "Could not apply platform fee to booking details price",
                            error_message=str(e),
                        )

            log.success(
                "details_retrieved=True",
                has_details=bool(response.booking_details),
            )
            return response

        except Exception as e:
            log.error(f"Booking details retrieval failed: {e!s}", exc=e)
            raise HotelBookingError(
                reason=f"Booking details retrieval failed: {e!s}"
            ) from e

    # ============================================================
    # TRIP DETAILS BY VOYA REFERENCE (for email link / booking details page)
    # ============================================================

    @staticmethod
    def _decode_booking_auth_token_user_id(auth_token: str) -> str | None:
        """Decode JWT auth_token and return user_id. Returns None if invalid/expired."""
        import jwt

        from app.core.config import settings

        try:
            payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None
        if payload.get("type") != "booking_auth":  # nosec B105 - token type
            return None
        user_id = payload.get("user_id")
        return str(user_id) if user_id is not None else None

    async def get_trip_details(
        self, request: HotelTripDetailsRequest
    ) -> HotelTripDetailsResponse:
        """Get hotel booking details by VOYA reference.

        Resolves supplier_confirmation_num and reference_num from the booking
        event, validates user ownership, then delegates to get_booking_details.

        When auth_token is provided (email link), decodes it and verifies
        the token's user_id matches the booking event's user_id; otherwise 403.

        Args:
            request: Contains voya_booking_reference and optional auth_token

        Returns:
            HotelTripDetailsResponse with booking details

        Raises:
            InvalidTokenError: If user is not authenticated (when no auth_token)
            ValueError: If booking not found or missing supplier references
            BookingForbiddenError: If user doesn't own the booking or token user_id != booking owner
            HotelBookingError: If supplier API call fails
        """
        from app.domains.bookings.exceptions import BookingForbiddenError
        from app.domains.bookings.service import BookingService

        voya_ref = request.voya_booking_reference
        auth_token = request.auth_token

        if auth_token:
            token_user_id = self._decode_booking_auth_token_user_id(auth_token)
            if token_user_id is None:
                from app.domains.auth.exceptions import InvalidTokenError

                raise InvalidTokenError(
                    "Invalid or expired booking link. Please request a new link."
                )
            event = await BookingService.get_event_by_voya_reference(voya_ref)
            if not event:
                raise ValueError(f"Booking not found: {voya_ref}")
            booking_user_id = str(event.user_id)
            if str(token_user_id) != booking_user_id:
                logger.warning(
                    "Auth token user mismatch: token user_id=%s, booking user_id=%s",
                    token_user_id,
                    booking_user_id,
                )
                raise BookingForbiddenError(
                    "This link is for a different account. Sign out and open the link again."
                )
            user_id = token_user_id
        else:
            if not self.current_user:
                from app.domains.auth.exceptions import InvalidTokenError

                raise InvalidTokenError("Authentication required")
            user_id = str(self.current_user.id)
            await BookingService.validate_user_owns_booking(voya_ref, user_id)
            event = await BookingService.get_event_by_voya_reference(voya_ref)
            if not event:
                raise ValueError(f"Booking not found: {voya_ref}")

        supplier_confirmation_num = event.external_booking_reference
        hotel_reference_number = event.hotel_reference_number

        if not supplier_confirmation_num or not hotel_reference_number:
            return HotelTripDetailsResponse(
                success=False,
                voya_booking_reference=voya_ref,
                booking_status=event.action,
                errors=["Missing supplier references — booking details unavailable."],
            )

        details_request = HotelBookingDetailsRequest(
            supplier_confirmation_num=supplier_confirmation_num,
            reference_num=hotel_reference_number,
            user_id=None,
            user_password=None,
            access=None,
            ip_address=None,
        )

        details_response = await self.get_booking_details(details_request)

        merged_booking_details = _overlay_booking_event_display_on_details(
            details_response.booking_details,
            event,
        )

        cin, cout, nights = hotel_stay_from_booking_details(
            merged_booking_details or None
        )
        if cin is not None or cout is not None or nights is not None:
            try:
                await BookingService.update_booking_dates_and_flags(
                    voya_ref,
                    hotel_check_in_date=cin,
                    hotel_check_out_date=cout,
                    hotel_nights=nights,
                )
            except Exception as e:
                logger.warning(
                    "Failed to update hotel stay dates for %s: %s",
                    voya_ref,
                    e,
                )

        return HotelTripDetailsResponse(
            success=True,
            voya_booking_reference=voya_ref,
            booking_status=event.action,
            booking_details=merged_booking_details,
            errors=None,
        )

    async def get_user_bookings(self, limit: int = 10) -> list[HotelMyBookingListItem]:
        """List current user's hotel booking_events (newest first)."""
        if not self.current_user:
            raise ValueError("Authentication required")

        db = await get_database()
        user_id_str = str(self.current_user.id)
        user_id_filter = booking_events_user_id_filter(user_id_str)
        hotel_query = {"user_id": user_id_filter, "event_type": "HOTEL"}

        log = HotelLogger(
            "GET_USER_BOOKINGS", **self._get_base_log_context(), limit=limit
        )
        log.started()

        try:
            rows = (
                await db[BOOKING_EVENT_COLLECTION]
                .find(hotel_query)
                .sort("timestamp", -1)
                .limit(limit)
                .to_list(limit)
            )
            mapped = [_mongo_doc_to_hotel_my_booking(dict(doc)) for doc in rows]
            log.success("User bookings retrieved successfully", count=len(mapped))
            return mapped
        except Exception as e:
            log.error("Failed to retrieve user bookings", exc=e)
            raise


# ============================================================
# DEPENDENCY INJECTION
# ============================================================


def get_hotel_service(
    current_user: UserPublic | None = Depends(get_current_user(required=False)),
) -> HotelService:
    """Get hotel service instance with user context.

    Args:
        current_user: Current authenticated user (optional for public endpoints)

    Returns:
        Configured HotelService instance
    """
    return HotelService(current_user=current_user)
