"""Hotel domain validators.

Business logic validation functions that complement Pydantic schema validation.
Following the same patterns as the flight domain.
"""

from datetime import date, datetime

from .constants import (
    MAX_ADULTS_PER_ROOM,
    MAX_CHILDREN_PER_ROOM,
    MAX_NIGHTS,
    MAX_ROOMS,
    MIN_ADULTS_PER_ROOM,
    MIN_NIGHTS,
    MIN_ROOMS,
)
from .exceptions import HotelValidationError
from .schemas import HotelSearchRequest, OccupancyRoom


def validate_search_dates(checkin: str, checkout: str) -> None:
    """Validate hotel search dates.

    Args:
        checkin: Check-in date (YYYY-MM-DD)
        checkout: Check-out date (YYYY-MM-DD)

    Raises:
        HotelValidationError: If dates are invalid
    """
    try:
        # Using naive datetime for date-only validation (no timezone needed)
        checkin_date = datetime.strptime(checkin, "%Y-%m-%d").date()  # noqa: DTZ007
        checkout_date = datetime.strptime(checkout, "%Y-%m-%d").date()  # noqa: DTZ007
    except ValueError as e:
        raise HotelValidationError(
            field="dates", reason="Dates must be in YYYY-MM-DD format"
        ) from e

    # Check-out must be after check-in
    if checkout_date <= checkin_date:
        raise HotelValidationError(
            field="checkout", reason="Check-out must be after check-in"
        )

    # Check minimum/maximum nights
    nights = (checkout_date - checkin_date).days
    if nights < MIN_NIGHTS:
        raise HotelValidationError(
            field="dates", reason=f"Minimum {MIN_NIGHTS} night(s) required"
        )
    if nights > MAX_NIGHTS:
        raise HotelValidationError(
            field="dates", reason=f"Maximum {MAX_NIGHTS} nights allowed"
        )

    # Check-in cannot be in the past
    # Using naive date.today() for date comparison (no timezone needed)
    today = date.today()  # noqa: DTZ011
    if checkin_date < today:
        raise HotelValidationError(
            field="checkin", reason="Check-in date cannot be in the past"
        )


def validate_occupancy(occupancy: list[OccupancyRoom] | list[dict]) -> None:
    """Validate occupancy details.

    Args:
        occupancy: List of room occupancy details

    Raises:
        HotelValidationError: If occupancy is invalid
    """
    if not occupancy:
        raise HotelValidationError(
            field="occupancy", reason="At least one room required"
        )

    if len(occupancy) < MIN_ROOMS:
        raise HotelValidationError(
            field="occupancy", reason=f"Minimum {MIN_ROOMS} room(s) required"
        )

    if len(occupancy) > MAX_ROOMS:
        raise HotelValidationError(
            field="occupancy", reason=f"Maximum {MAX_ROOMS} rooms allowed"
        )

    # Validate each room
    for idx, room in enumerate(occupancy):
        room_num = idx + 1

        # Get values (handle both OccupancyRoom objects and dicts)
        if isinstance(room, dict):
            adults = room.get("adult", 0)
            children = room.get("child", 0)
            child_ages = room.get("child_age", [])
        else:
            # Type narrowing: room is OccupancyRoom
            occupancy_room: OccupancyRoom = room  # type: ignore[assignment]
            adults = occupancy_room.adult
            children = occupancy_room.child
            child_ages = occupancy_room.child_age

        # Validate adults
        if adults < MIN_ADULTS_PER_ROOM:
            raise HotelValidationError(
                field=f"occupancy[{idx}].adult",
                reason=f"Room {room_num}: At least {MIN_ADULTS_PER_ROOM} adult(s) required",
            )
        if adults > MAX_ADULTS_PER_ROOM:
            raise HotelValidationError(
                field=f"occupancy[{idx}].adult",
                reason=f"Room {room_num}: Maximum {MAX_ADULTS_PER_ROOM} adults allowed",
            )

        # Validate children
        if children < 0:
            raise HotelValidationError(
                field=f"occupancy[{idx}].child",
                reason=f"Room {room_num}: Children count cannot be negative",
            )
        if children > MAX_CHILDREN_PER_ROOM:
            raise HotelValidationError(
                field=f"occupancy[{idx}].child",
                reason=f"Room {room_num}: Maximum {MAX_CHILDREN_PER_ROOM} children allowed",
            )

        # Validate child ages
        if children > 0:
            if not child_ages or len(child_ages) != children:
                raise HotelValidationError(
                    field=f"occupancy[{idx}].child_age",
                    reason=f"Room {room_num}: Must provide {children} child age(s)",
                )
            for age_idx, age in enumerate(child_ages):
                if age < 0 or age > 17:
                    raise HotelValidationError(
                        field=f"occupancy[{idx}].child_age[{age_idx}]",
                        reason=f"Room {room_num}: Child age must be 0-17",
                    )


def validate_currency_code(currency: str) -> None:
    """Validate currency code format.

    Args:
        currency: ISO 4217 currency code

    Raises:
        HotelValidationError: If currency code is invalid
    """
    if not currency:
        raise HotelValidationError(field="currency", reason="Currency code is required")

    if len(currency) != 3:
        raise HotelValidationError(
            field="currency", reason="Currency code must be 3 characters (ISO 4217)"
        )

    if not currency.isalpha():
        raise HotelValidationError(
            field="currency", reason="Currency code must contain only letters"
        )

    if not currency.isupper():
        raise HotelValidationError(
            field="currency", reason="Currency code must be uppercase"
        )


def validate_search_request(request: HotelSearchRequest) -> None:
    """Validate complete hotel search request.

    Performs business logic validation beyond Pydantic schema validation.

    Args:
        request: Hotel search request

    Raises:
        HotelValidationError: If request is invalid
    """
    # Validate dates
    validate_search_dates(request.checkin, request.checkout)

    # Validate occupancy
    validate_occupancy(request.occupancy)

    # Validate currency
    validate_currency_code(request.required_currency)

    # Validate search criteria
    has_city = bool(request.city_name and request.country_name)
    has_geo = bool(request.latitude is not None and request.longitude is not None)
    has_codes = bool(request.hotel_codes)

    if not (has_city or has_geo or has_codes):
        raise HotelValidationError(
            field="search_criteria",
            reason="Must provide either (city + country), (lat + lng), or hotel codes",
        )

    # Validate geolocation if provided
    if has_geo:
        if request.latitude is not None and (
            request.latitude < -90 or request.latitude > 90
        ):
            raise HotelValidationError(
                field="latitude", reason="Latitude must be between -90 and 90"
            )
        if request.longitude is not None and (
            request.longitude < -180 or request.longitude > 180
        ):
            raise HotelValidationError(
                field="longitude", reason="Longitude must be between -180 and 180"
            )

    # Validate radius if provided
    if request.radius is not None and request.radius < 1:
        raise HotelValidationError(
            field="radius", reason="Radius must be at least 1 KM"
        )

    # Validate nationality if provided
    if request.nationality and len(request.nationality) != 2:
        raise HotelValidationError(
            field="nationality",
            reason="Nationality must be 2-character ISO 3166-1 alpha-2 code",
        )


def validate_session_id(session_id: str) -> None:
    """Validate session ID format.

    Args:
        session_id: FlightLogic session ID

    Raises:
        HotelValidationError: If session ID is invalid
    """
    if not session_id:
        raise HotelValidationError(field="session_id", reason="Session ID is required")

    if not session_id.strip():
        raise HotelValidationError(
            field="session_id", reason="Session ID cannot be empty"
        )


def validate_token_id(token_id: str) -> None:
    """Validate hotel token ID format.

    Args:
        token_id: Hotel token from search results

    Raises:
        HotelValidationError: If token ID is invalid
    """
    if not token_id:
        raise HotelValidationError(field="token_id", reason="Token ID is required")

    if not token_id.strip():
        raise HotelValidationError(field="token_id", reason="Token ID cannot be empty")
