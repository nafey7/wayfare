"""Unit tests for FlightSearchRequest passenger validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domains.flight.enums import CabinClass, JourneyType
from app.domains.flight.schemas import (
    AirportInfo,
    FlightSearchRequest,
    OriginDestinationSegment,
)

# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def valid_base_data():
    """Base valid data for FlightSearchRequest tests."""
    return {
        "journey_type": JourneyType.ONE_WAY,
        "origin_destination_info": [
            OriginDestinationSegment(
                departure_date=datetime.now(UTC).date(),
                origin_airport=AirportInfo(iata_code="LAX"),
                destination_airport=AirportInfo(iata_code="JFK"),
            )
        ],
        "cabin_class": CabinClass.ECONOMY,
    }


# ==============================================================================
# VALID PASSENGER COUNT COMBINATIONS
# ==============================================================================


def test_valid_passenger_combinations(valid_base_data):
    """Test all valid passenger combinations from business requirements."""
    valid_combinations = [
        # All the example combinations from requirements
        {"adults": 5, "children": 3, "infants": 1},  # Total: 9
        {"adults": 4, "children": 4, "infants": 1},  # Total: 9
        {"adults": 6, "children": 2, "infants": 1},  # Total: 9
        {"adults": 3, "children": 3, "infants": 3},  # Total: 9
        {"adults": 7, "children": 1, "infants": 1},  # Total: 9
        {"adults": 2, "children": 4, "infants": 3},  # Total: 9
        {"adults": 4, "children": 2, "infants": 3},  # Total: 9
        {"adults": 3, "children": 5, "infants": 1},  # Total: 9
        {"adults": 8, "children": 0, "infants": 1},  # Total: 9
        {"adults": 1, "children": 7, "infants": 1},  # Total: 9
        {"adults": 9, "children": 0, "infants": 0},  # Total: 9, max adults only
        # Additional valid combinations
        {"adults": 1, "children": 0, "infants": 0},  # Total: 1, minimum
        {"adults": 2, "children": 1, "infants": 0},  # Total: 3, no infants
        {"adults": 5, "children": 4, "infants": 0},  # Total: 9, no infants
        {
            "adults": 1,
            "children": 2,
            "infants": 1,
        },  # Total: 4, infants <= adults+children
    ]

    for combination in valid_combinations:
        data = {**valid_base_data, **combination}
        request = FlightSearchRequest(**data)

        assert request.adults == combination["adults"]
        assert request.children == combination["children"]
        assert request.infants == combination["infants"]

        total = request.adults + request.children + request.infants
        assert total <= 9, f"Total passengers {total} should be <= 9"
        assert request.infants <= (request.adults + request.children), (
            f"Infants {request.infants} should be <= Adults+Children {request.adults + request.children}"
        )


# ==============================================================================
# INVALID PASSENGER COUNT COMBINATIONS - TOTAL EXCEEDS 9
# ==============================================================================


def test_invalid_total_exceeds_9(valid_base_data):
    """Test that total passengers > 9 raises validation error."""
    invalid_combinations = [
        {"adults": 6, "children": 3, "infants": 2},  # Total: 11
        {"adults": 10, "children": 0, "infants": 0},  # Total: 10
        {"adults": 5, "children": 5, "infants": 1},  # Total: 11
        {"adults": 4, "children": 4, "infants": 4},  # Total: 12
        {"adults": 3, "children": 3, "infants": 5},  # Total: 11
    ]

    for combination in invalid_combinations:
        data = {**valid_base_data, **combination}
        total = combination["adults"] + combination["children"] + combination["infants"]

        with pytest.raises(ValidationError) as exc_info:
            FlightSearchRequest(**data)

        error = exc_info.value.errors()[0]
        assert "Total passenger count cannot exceed 9" in error["msg"]
        assert f"Current: {total}" in error["msg"]


# ==============================================================================
# INVALID PASSENGER COUNT COMBINATIONS - INFANT RULES
# ==============================================================================


def test_invalid_infants_exceed_adults_plus_children(valid_base_data):
    """Test that infants > (adults + children) raises validation error."""
    invalid_combinations = [
        {"adults": 2, "children": 1, "infants": 4},  # Infants 4 > Adults+Children 3
        {"adults": 1, "children": 0, "infants": 2},  # Infants 2 > Adults+Children 1
        {"adults": 0, "children": 2, "infants": 3},  # Infants 3 > Adults+Children 2
        {
            "adults": 3,
            "children": 2,
            "infants": 6,
        },  # Infants 6 > Adults+Children 5 (also exceeds total)
    ]

    for combination in invalid_combinations:
        data = {**valid_base_data, **combination}
        adults_plus_children = combination["adults"] + combination["children"]
        infants = combination["infants"]

        with pytest.raises(ValidationError) as exc_info:
            FlightSearchRequest(**data)

        error = exc_info.value.errors()[0]
        # Could fail on either rule (total > 9 or infants > adults+children)
        # Check for the specific infant rule if total <= 9
        total = combination["adults"] + combination["children"] + combination["infants"]
        if total <= 9:
            assert (
                f"Infant count ({infants}) cannot exceed combined Adults + Children count ({adults_plus_children})"
                in error["msg"]
            )


def test_invalid_infants_without_adults(valid_base_data):
    """Test that infants without adults raises validation error."""
    invalid_combinations = [
        {"adults": 0, "children": 5, "infants": 1},  # Infants without adults
        {"adults": 0, "children": 2, "infants": 2},  # Multiple infants without adults
        {"adults": 0, "children": 1, "infants": 1},  # Single infant without adults
    ]

    for combination in invalid_combinations:
        data = {**valid_base_data, **combination}

        with pytest.raises(ValidationError) as exc_info:
            FlightSearchRequest(**data)

        error = exc_info.value.errors()[0]
        assert "cannot travel without an accompanying adult" in error["msg"]
        assert "At least 1 adult is required" in error["msg"]


# ==============================================================================
# BOUNDARY TESTS
# ==============================================================================


def test_minimum_passengers(valid_base_data):
    """Test minimum passenger requirement."""
    # Zero passengers should fail
    data = {**valid_base_data, "adults": 0, "children": 0, "infants": 0}

    with pytest.raises(ValidationError) as exc_info:
        FlightSearchRequest(**data)

    error = exc_info.value.errors()[0]
    assert "At least 1 passenger is required for flight search" in error["msg"]


def test_maximum_valid_passengers(valid_base_data):
    """Test maximum valid passenger combinations (total = 9)."""
    max_combinations = [
        {"adults": 9, "children": 0, "infants": 0},  # All adults
        {
            "adults": 0,
            "children": 9,
            "infants": 0,
        },  # All children (no infants = no adult requirement)
        {"adults": 4, "children": 4, "infants": 1},  # Mixed with infants
        {"adults": 1, "children": 7, "infants": 1},  # Minimum adults with infants
    ]

    for combination in max_combinations:
        data = {**valid_base_data, **combination}
        request = FlightSearchRequest(**data)  # Should not raise
        total = request.adults + request.children + request.infants
        assert total == 9


def test_negative_passenger_counts_rejected(valid_base_data):
    """Test that negative passenger counts are rejected by Field validation."""
    invalid_combinations = [
        {"adults": -1, "children": 0, "infants": 0},
        {"adults": 1, "children": -1, "infants": 0},
        {"adults": 1, "children": 0, "infants": -1},
    ]

    for combination in invalid_combinations:
        data = {**valid_base_data, **combination}

        with pytest.raises(ValidationError) as exc_info:
            FlightSearchRequest(**data)

        # Should fail on the Field ge=0 constraint, not our custom validator
        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in error["msg"] for error in errors)


# ==============================================================================
# EDGE CASES AND ERROR MESSAGE VALIDATION
# ==============================================================================


def test_error_messages_include_passenger_breakdown(valid_base_data):
    """Test that error messages include clear passenger count breakdown."""
    data = {**valid_base_data, "adults": 6, "children": 3, "infants": 2}  # Total: 11

    with pytest.raises(ValidationError) as exc_info:
        FlightSearchRequest(**data)

    error = exc_info.value.errors()[0]
    assert "Adults: 6" in error["msg"]
    assert "Children: 3" in error["msg"]
    assert "Infants: 2" in error["msg"]
    assert "Current: 11" in error["msg"]


def test_multiple_validation_errors_first_failure_wins(valid_base_data):
    """Test that validation stops at first error (total > 9 vs infant rules)."""
    # This combination violates both rules:
    # 1. Total > 9 (3+3+5=11)
    # 2. Infants > Adults+Children (5 > 6)
    data = {**valid_base_data, "adults": 3, "children": 3, "infants": 5}

    with pytest.raises(ValidationError) as exc_info:
        FlightSearchRequest(**data)

    # Should get exactly one error (first validation that fails)
    errors = exc_info.value.errors()
    assert len(errors) == 1

    # Should be the total > 9 error since it's checked first
    error = errors[0]
    assert "Total passenger count cannot exceed 9" in error["msg"]


def test_valid_infant_adult_pairing_edge_cases(valid_base_data):
    """Test edge cases for infant-adult pairing that should be valid."""
    valid_cases = [
        {"adults": 1, "children": 0, "infants": 1},  # 1:1 ratio
        {"adults": 3, "children": 0, "infants": 3},  # 1:1 ratio, multiple
        {"adults": 2, "children": 1, "infants": 3},  # Infants = Adults+Children
        {"adults": 5, "children": 4, "infants": 0},  # No infants (no restriction)
    ]

    for combination in valid_cases:
        data = {**valid_base_data, **combination}
        request = FlightSearchRequest(**data)  # Should not raise

        # Verify the business logic
        if request.infants > 0:
            assert request.adults > 0, "Should have adults when infants present"
            assert request.infants <= (request.adults + request.children), (
                "Infants should not exceed adults + children"
            )


# ==============================================================================
# INTEGRATION WITH OTHER FIELDS
# ==============================================================================


def test_passenger_validation_with_other_required_fields(valid_base_data):
    """Test that passenger validation works with all other required fields."""
    # Test with full valid data
    data = {
        **valid_base_data,
        "adults": 2,
        "children": 1,
        "infants": 1,
        "required_currency_code": "USD",
        "preferred_airline": AirportInfo(
            iata_code="BA"
        ),  # This will fail but tests interaction
        "direct_flight": 1,
    }

    # The passenger validation should pass, other fields might have their own validation
    try:
        request = FlightSearchRequest(**data)
        # If we get here, passenger validation passed
        assert request.adults == 2
        assert request.children == 1
        assert request.infants == 1
    except ValidationError as e:
        # If there's an error, make sure it's not from passenger validation
        for error in e.errors():
            assert "passenger count" not in error["msg"].lower()
            assert "infant" not in error["msg"].lower()


def test_revalidate_flights_count_accepts_valid_values(valid_base_data):
    """Test revalidate_flights_count accepts 0, 5, and max 10."""
    for count in [0, 5, 10]:
        data = {
            **valid_base_data,
            "adults": 1,
            "children": 0,
            "infants": 0,
            "revalidate_flights_count": count,
        }
        request = FlightSearchRequest(**data)
        assert request.revalidate_flights_count == count


def test_revalidate_flights_count_optional_none(valid_base_data):
    """Test revalidate_flights_count can be omitted (None)."""
    data = {**valid_base_data, "adults": 1, "children": 0, "infants": 0}
    request = FlightSearchRequest(**data)
    assert request.revalidate_flights_count is None


def test_revalidate_flights_count_rejects_negative(valid_base_data):
    """Test revalidate_flights_count rejects negative values."""
    data = {
        **valid_base_data,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "revalidate_flights_count": -1,
    }
    with pytest.raises(ValidationError):
        FlightSearchRequest(**data)


def test_revalidate_flights_count_enforces_max_cap(valid_base_data):
    """Test revalidate_flights_count enforces max cap of 10."""
    data = {
        **valid_base_data,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "revalidate_flights_count": 11,
    }
    with pytest.raises(ValidationError):
        FlightSearchRequest(**data)


def test_passenger_validation_preserves_other_validations():
    """Test that adding passenger validation doesn't break other field validations."""
    # Test with invalid journey_type but valid passengers
    with pytest.raises(ValidationError) as exc_info:
        FlightSearchRequest(
            journey_type="INVALID_TYPE",  # Invalid enum
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=datetime.now(UTC).date(),
                    origin_airport=AirportInfo(iata_code="LAX"),
                    destination_airport=AirportInfo(iata_code="JFK"),
                )
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=2,
            children=1,
            infants=0,  # Valid passenger counts
        )

    # Should fail on journey_type, not passenger validation
    errors = exc_info.value.errors()
    assert any("journey_type" in error["loc"] for error in errors)
