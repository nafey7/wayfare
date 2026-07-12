"""Flight booking validation logic."""

from datetime import date, datetime, timedelta

from .exceptions import FlightBookingError
from .schemas import FlightBookingRequest, PassengerGroups


class PassengerValidator:
    """Validator for passenger information with age requirements."""

    @staticmethod
    def validate_adult_age(date_of_birth: str | None) -> None:
        """Validate that adult passenger is at least 12 years old.

        Aligns with FlightLogic / industry standard: ADT = 12+ (adult fares).
        Child (CHD) is 2-11, so 12+ must be booked as adult.

        Args:
            date_of_birth: Date of birth in ISO format (YYYY-MM-DD)

        Raises:
            ValueError: If date of birth is invalid or passenger is under 12
        """
        if not date_of_birth:
            # Date of birth is optional for some bookings, so don't raise error here
            # The required field validation will catch this if it's mandatory
            return

        try:
            dob = datetime.fromisoformat(date_of_birth)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid date of birth format. Expected YYYY-MM-DD, got: {date_of_birth}"
            ) from e

        today = datetime.now()

        # Check if date is in the future
        if dob > today:
            raise ValueError("Date of birth cannot be in the future")

        # Calculate 12 years ago from today (ADT = 12+ per FlightLogic)
        # Using 365.25 to account for leap years
        twelve_years_ago = today - timedelta(days=365.25 * 12)

        if dob > twelve_years_ago:
            age_years = (today - dob).days / 365.25
            raise ValueError(
                f"Adult passengers must be at least 12 years old. "
                f"Current age: {age_years:.1f} years"
            )

    @staticmethod
    def validate_child_age_pydantic(date_of_birth: str | None) -> None:
        """Validate that child passenger is between 2 and 11 years old.

        This is for Pydantic field validation. Different from the existing
        validate_age_requirements which is called at booking time.

        Args:
            date_of_birth: Date of birth in ISO format (YYYY-MM-DD)

        Raises:
            ValueError: If date of birth is invalid or not in child age range
        """
        if not date_of_birth:
            # Optional field, skip validation if not provided
            return

        try:
            dob = datetime.fromisoformat(date_of_birth)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid date of birth format. Expected YYYY-MM-DD, got: {date_of_birth}"
            ) from e

        today = datetime.now()

        # Check if date is in the future
        if dob > today:
            raise ValueError("Date of birth cannot be in the future")

        # Convert to date for comparison
        dob_date = dob.date()
        today_date = today.date()

        # Calculate age using standard algorithm
        age = today_date.year - dob_date.year
        if (today_date.month, today_date.day) < (dob_date.month, dob_date.day):
            age -= 1

        if age < 2:
            raise ValueError(
                f"Child passengers must be at least 2 years old. Current age: {age} years. "
                "Passengers under 2 years must be booked as infants."
            )

        if age >= 12:
            raise ValueError(
                f"Child passengers must be under 12 years old. Current age: {age} years. "
                "Passengers 12+ years must be booked as adults."
            )

    @staticmethod
    def validate_infant_age_pydantic(date_of_birth: str | None) -> None:
        """Validate that infant passenger is under 2 years old.

        This is for Pydantic field validation. Different from the existing
        validate_age_requirements which is called at booking time.

        Args:
            date_of_birth: Date of birth in ISO format (YYYY-MM-DD)

        Raises:
            ValueError: If date of birth is invalid or passenger is 2 or older
        """
        if not date_of_birth:
            # Optional field, skip validation if not provided
            return

        try:
            dob = datetime.fromisoformat(date_of_birth)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid date of birth format. Expected YYYY-MM-DD, got: {date_of_birth}"
            ) from e

        today = datetime.now()

        # Check if date is in the future
        if dob > today:
            raise ValueError("Date of birth cannot be in the future")

        # Convert to date for comparison
        dob_date = dob.date()
        today_date = today.date()

        # Calculate age using standard algorithm
        age = today_date.year - dob_date.year
        if (today_date.month, today_date.day) < (dob_date.month, dob_date.day):
            age -= 1

        if age >= 2:
            raise ValueError(
                f"Infant passengers must be under 2 years old. Current age: {age} years. "
                "Passengers 2+ years must be booked as children or adults."
            )


class MissingRequiredFieldError(FlightBookingError):
    """Raised when required booking fields are missing."""

    def __init__(self, field_name: str, passenger_type: str | None = None) -> None:
        if passenger_type:
            message = (
                f"Required field '{field_name}' missing for {passenger_type} passenger"
            )
        else:
            message = f"Required field '{field_name}' is missing"
        super().__init__(message, "MISSING_REQUIRED_FIELD")
        self.field_name = field_name
        self.passenger_type = passenger_type


def validate_required_fields_to_book(
    booking_request: FlightBookingRequest,
    required_fields: list[str] | None,
) -> None:
    """Validate that all required fields from revalidate response are present.

    Args:
        booking_request: The flight booking request to validate
        required_fields: List of required field names from revalidate response

    Raises:
        MissingRequiredFieldError: If any required field is missing
    """
    if not required_fields:
        return

    # Normalize field names to lowercase for comparison
    required_fields_lower = [field.lower() for field in required_fields]

    # Validate each required field
    for field in required_fields_lower:
        if field == "passport":
            _validate_passport_fields(booking_request)
        elif field == "dob":
            _validate_dob_fields(booking_request)
        elif field == "nationality":
            _validate_nationality_fields(booking_request)
        elif field in {"postcode", "zip"}:
            _validate_postal_code(booking_request)
        elif field == "city":
            _validate_city(booking_request)
        elif field == "state":
            _validate_state(booking_request)
        elif field == "firstname":
            _validate_first_name(booking_request)
        elif field == "lastname":
            _validate_last_name(booking_request)
        elif field == "title":
            _validate_title(booking_request)
        # Add more field validations as needed


def _validate_passport_fields(booking_request: FlightBookingRequest) -> None:
    """Validate passport fields are present and valid."""
    passenger_groups = booking_request.passenger_groups

    # Check adults
    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if (
                not adult.travel_documents
                or not adult.travel_documents.passport_number
                or not adult.travel_documents.passport_number.strip()
            ):
                raise MissingRequiredFieldError("passport_number", f"adult {i + 1}")
            if not adult.travel_documents.passport_expiry:
                raise MissingRequiredFieldError("passport_expiry", f"adult {i + 1}")
            if (
                not adult.travel_documents.passport_country
                or not adult.travel_documents.passport_country.strip()
            ):
                raise MissingRequiredFieldError("passport_country", f"adult {i + 1}")

            # Validate passport expiry date is in the future
            expiry_raw = adult.travel_documents.passport_expiry
            if isinstance(expiry_raw, str):
                expiry_date = datetime.fromisoformat(expiry_raw).date()
            elif isinstance(expiry_raw, datetime):
                expiry_date = expiry_raw.date()
            else:
                expiry_date = expiry_raw  # Already a date object

            # Compare with UTC today for timezone-aware validation
            from datetime import UTC

            if expiry_date <= datetime.now(UTC).date():
                raise FlightBookingError(
                    f"Passport expired for adult {i + 1}. Expiry date: {expiry_date}",
                    "PASSPORT_EXPIRED",
                )

    # Check children
    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if (
                not child.travel_documents
                or not child.travel_documents.passport_number
                or not child.travel_documents.passport_number.strip()
            ):
                raise MissingRequiredFieldError("passport_number", f"child {i + 1}")
            if not child.travel_documents.passport_expiry:
                raise MissingRequiredFieldError("passport_expiry", f"child {i + 1}")
            if (
                not child.travel_documents.passport_country
                or not child.travel_documents.passport_country.strip()
            ):
                raise MissingRequiredFieldError("passport_country", f"child {i + 1}")

    # Check infants
    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if (
                not infant.travel_documents
                or not infant.travel_documents.passport_number
                or not infant.travel_documents.passport_number.strip()
            ):
                raise MissingRequiredFieldError("passport_number", f"infant {i + 1}")
            if not infant.travel_documents.passport_expiry:
                raise MissingRequiredFieldError("passport_expiry", f"infant {i + 1}")
            if (
                not infant.travel_documents.passport_country
                or not infant.travel_documents.passport_country.strip()
            ):
                raise MissingRequiredFieldError("passport_country", f"infant {i + 1}")


def _validate_dob_fields(booking_request: FlightBookingRequest) -> None:
    """Validate date of birth fields are present."""
    passenger_groups = booking_request.passenger_groups

    # Check adults
    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if not adult.personal_info.date_of_birth:
                raise MissingRequiredFieldError("date_of_birth", f"adult {i + 1}")

    # Children and infants ALWAYS need DOB
    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if not child.personal_info.date_of_birth:
                raise MissingRequiredFieldError("date_of_birth", f"child {i + 1}")

    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if not infant.personal_info.date_of_birth:
                raise MissingRequiredFieldError("date_of_birth", f"infant {i + 1}")


def _validate_nationality_fields(booking_request: FlightBookingRequest) -> None:
    """Validate nationality fields are present."""
    passenger_groups = booking_request.passenger_groups

    # Check all passenger types
    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if (
                not adult.personal_info.nationality
                or not adult.personal_info.nationality.strip()
            ):
                raise MissingRequiredFieldError("nationality", f"adult {i + 1}")

    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if (
                not child.personal_info.nationality
                or not child.personal_info.nationality.strip()
            ):
                raise MissingRequiredFieldError("nationality", f"child {i + 1}")

    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if (
                not infant.personal_info.nationality
                or not infant.personal_info.nationality.strip()
            ):
                raise MissingRequiredFieldError("nationality", f"infant {i + 1}")


def _validate_postal_code(booking_request: FlightBookingRequest) -> None:
    """Validate postal code is present."""
    if not booking_request.postal_code or not booking_request.postal_code.code.strip():
        raise MissingRequiredFieldError("postal_code")


def _validate_city(booking_request: FlightBookingRequest) -> None:
    """Validate city is present (would need to add city field to schema)."""
    # TODO: Add city field to ContactInformation schema if needed
    pass


def _validate_state(booking_request: FlightBookingRequest) -> None:
    """Validate state is present (would need to add state field to schema)."""
    # TODO: Add state field to ContactInformation schema if needed
    pass


def _validate_first_name(booking_request: FlightBookingRequest) -> None:
    """Validate first name is present for all passengers."""
    passenger_groups = booking_request.passenger_groups

    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if (
                not adult.personal_info.name.first_name
                or not adult.personal_info.name.first_name.strip()
            ):
                raise MissingRequiredFieldError("first_name", f"adult {i + 1}")

    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if (
                not child.personal_info.name.first_name
                or not child.personal_info.name.first_name.strip()
            ):
                raise MissingRequiredFieldError("first_name", f"child {i + 1}")

    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if (
                not infant.personal_info.name.first_name
                or not infant.personal_info.name.first_name.strip()
            ):
                raise MissingRequiredFieldError("first_name", f"infant {i + 1}")


def _validate_last_name(booking_request: FlightBookingRequest) -> None:
    """Validate last name is present for all passengers."""
    passenger_groups = booking_request.passenger_groups

    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if (
                not adult.personal_info.name.last_name
                or not adult.personal_info.name.last_name.strip()
            ):
                raise MissingRequiredFieldError("last_name", f"adult {i + 1}")

    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if (
                not child.personal_info.name.last_name
                or not child.personal_info.name.last_name.strip()
            ):
                raise MissingRequiredFieldError("last_name", f"child {i + 1}")

    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if (
                not infant.personal_info.name.last_name
                or not infant.personal_info.name.last_name.strip()
            ):
                raise MissingRequiredFieldError("last_name", f"infant {i + 1}")


def _validate_title(booking_request: FlightBookingRequest) -> None:
    """Validate title is present for all passengers."""
    passenger_groups = booking_request.passenger_groups

    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            if (
                not adult.personal_info.name.title
                or not adult.personal_info.name.title.strip()
            ):
                raise MissingRequiredFieldError("title", f"adult {i + 1}")

    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            if (
                not child.personal_info.name.title
                or not child.personal_info.name.title.strip()
            ):
                raise MissingRequiredFieldError("title", f"child {i + 1}")

    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            if (
                not infant.personal_info.name.title
                or not infant.personal_info.name.title.strip()
            ):
                raise MissingRequiredFieldError("title", f"infant {i + 1}")


def calculate_age(date_of_birth: str | None) -> int | None:
    """Calculate age in years from date of birth.

    Args:
        date_of_birth: Date of birth in ISO format (YYYY-MM-DD or ISO datetime with timezone)

    Returns:
        Age in years, or None if date_of_birth is None or cannot be parsed
    """
    if not date_of_birth:
        return None
    try:
        from datetime import UTC

        # Handle ISO datetime strings with 'Z' timezone indicator
        dob_str = date_of_birth.replace("Z", "+00:00")
        dob = datetime.fromisoformat(dob_str)
        # If timezone-naive, assume UTC; otherwise convert to UTC for consistent comparison
        dob = dob.replace(tzinfo=UTC) if dob.tzinfo is None else dob.astimezone(UTC)

        today = datetime.now(UTC)
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return None


def validate_passenger_counts(
    booking_request: FlightBookingRequest,
    expected_adults: int,
    expected_children: int,
    expected_infants: int,
) -> None:
    """Validate passenger counts match search criteria.

    Args:
        booking_request: The flight booking request to validate
        expected_adults: Number of adults from search
        expected_children: Number of children from search
        expected_infants: Number of infants from search

    Raises:
        FlightBookingError: If passenger counts don't match
    """
    actual_adults = len(booking_request.passenger_groups.adults or [])
    actual_children = len(booking_request.passenger_groups.children or [])
    actual_infants = len(booking_request.passenger_groups.infants or [])

    if actual_adults != expected_adults:
        raise FlightBookingError(
            f"Passenger count mismatch: expected {expected_adults} adults, got {actual_adults}",
            "PASSENGER_COUNT_MISMATCH",
        )

    if actual_children != expected_children:
        raise FlightBookingError(
            f"Passenger count mismatch: expected {expected_children} children, got {actual_children}",
            "PASSENGER_COUNT_MISMATCH",
        )

    if actual_infants != expected_infants:
        raise FlightBookingError(
            f"Passenger count mismatch: expected {expected_infants} infants, got {actual_infants}",
            "PASSENGER_COUNT_MISMATCH",
        )


def _parse_dob(dob_raw: str | datetime | date | None) -> date | None:
    """Parse DOB from str/datetime/date to date. Returns None if invalid/missing."""
    if dob_raw is None:
        return None
    if isinstance(dob_raw, str):
        return datetime.fromisoformat(dob_raw).date()
    if isinstance(dob_raw, datetime):
        return dob_raw.date()
    return dob_raw


def _age_years(dob: date, today: date) -> int:
    """Compute age in full years."""
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def validate_age_requirements(passenger_groups: PassengerGroups) -> None:
    """Validate passenger ages meet requirements.

    Business rules:
    - Children: 2-11 years old
    - Infants: 0-1 years old (under 2)
    - Adults: 12+ years old

    Args:
        passenger_groups: Passenger groups to validate

    Raises:
        FlightBookingError: If age requirements not met
    """
    from datetime import UTC

    today = datetime.now(UTC).date()

    # Validate adults (must be >= 12 years)
    if passenger_groups.adults:
        for i, adult in enumerate(passenger_groups.adults):
            dob_date = _parse_dob(adult.personal_info.date_of_birth)
            if dob_date is not None:
                age = _age_years(dob_date, today)
                if age < 12:
                    raise FlightBookingError(
                        f"Adult {i + 1} is too young (age: {age} years). "
                        "Adult passengers must be at least 12 years old. "
                        "Passengers under 12 must be booked as children or infants.",
                        "INVALID_ADULT_AGE",
                    )

    # Validate children (must be >= 2 and < 12 years)
    if passenger_groups.children:
        for i, child in enumerate(passenger_groups.children):
            dob_date = _parse_dob(child.personal_info.date_of_birth)
            if dob_date is not None:
                age = _age_years(dob_date, today)
                if age < 2:
                    raise FlightBookingError(
                        f"Child {i + 1} is too young (age: {age} years). Passengers under 2 years must be booked as infants.",
                        "INVALID_CHILD_AGE",
                    )
                if age >= 12:
                    raise FlightBookingError(
                        f"Child {i + 1} is too old (age: {age} years). Passengers 12+ years must be booked as adults.",
                        "INVALID_CHILD_AGE",
                    )

    # Validate infants (must be < 2 years)
    if passenger_groups.infants:
        for i, infant in enumerate(passenger_groups.infants):
            dob_date = _parse_dob(infant.personal_info.date_of_birth)
            if dob_date is not None:
                age = _age_years(dob_date, today)
                if age >= 2:
                    raise FlightBookingError(
                        f"Infant {i + 1} is too old (age: {age} years). Passengers 2+ years must be booked as children or adults.",
                        "INVALID_INFANT_AGE",
                    )


def validate_infant_adult_pairing(passenger_groups: PassengerGroups) -> None:
    """Validate infant-adult pairing requirements.

    Business rule: Each infant must travel with an adult (max 1 infant per adult).

    Args:
        passenger_groups: Passenger groups to validate

    Raises:
        FlightBookingError: If infant-adult pairing rules are violated
    """
    num_adults = len(passenger_groups.adults or [])
    num_infants = len(passenger_groups.infants or [])

    if num_infants == 0:
        return  # No infants, validation passes

    if num_adults == 0:
        raise FlightBookingError(
            "Infants cannot travel without an accompanying adult.",
            "INFANT_REQUIRES_ADULT",
        )

    if num_infants > num_adults:
        raise FlightBookingError(
            f"Too many infants for the number of adults. {num_infants} infant(s) require at least {num_infants} adult(s), but only {num_adults} adult(s) booked. Each infant must be accompanied by one adult.",
            "INFANT_ADULT_RATIO_EXCEEDED",
        )
