"""Unit tests for flight search filter schemas.

Tests schema validation, backward compatibility, and data structure validation
for FlightSearchFilters, LegFilter, TimeWindow, and FlightSearchRequest.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domains.flight.enums import CabinClass, JourneyType
from app.domains.flight.schemas import (
    FlightSearchFilters,
    FlightSearchRequest,
    LegFilter,
    OriginDestinationSegment,
    TimeWindow,
)

# Reuse helper function
from tests.unit_tests.test_domains.test_flight.test_city_wise_filtering import (
    create_mock_airport,
)

# ==============================================================================
# BACKWARD COMPATIBILITY TESTS
# ==============================================================================


class TestBackwardCompatibility:
    """Test backward compatibility for legacy city_wise_search fields."""

    def test_merge_legacy_filters_creates_filters_if_none(self):
        """Test that filters object is created when legacy fields are provided."""
        request = FlightSearchRequest(
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=datetime.now(UTC).date(),
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                )
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            filters=None,  # No filters object
            city_wise_search_origin=True,  # Legacy field
        )

        # After validation, filters should be created
        assert request.filters is not None
        assert request.filters.city_wise_search_origin is True

    def test_merge_legacy_filters_top_level_precedence(self):
        """Test that top-level legacy fields take precedence over filters object."""
        request = FlightSearchRequest(
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=datetime.now(UTC).date(),
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                )
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            filters=FlightSearchFilters(
                city_wise_search_origin=False
            ),  # Filters says False
            city_wise_search_origin=True,  # Top-level says True (should win)
        )

        # Top-level should take precedence
        assert request.filters.city_wise_search_origin is True

    def test_merge_legacy_filters_both_origin_and_destination(self):
        """Test that both legacy fields are merged into filters."""
        request = FlightSearchRequest(
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=datetime.now(UTC).date(),
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                )
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            city_wise_search_origin=True,
            city_wise_search_destination=False,
        )

        assert request.filters is not None
        assert request.filters.city_wise_search_origin is True
        assert request.filters.city_wise_search_destination is False

    def test_merge_legacy_filters_existing_filters_preserved(self):
        """Test that existing filter fields are preserved when merging legacy fields."""
        request = FlightSearchRequest(
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=datetime.now(UTC).date(),
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                )
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            filters=FlightSearchFilters(min_price=100.0),  # Existing filter
            city_wise_search_origin=True,  # Legacy field to merge
        )

        # Existing filter should be preserved
        assert request.filters.min_price == 100.0
        # Legacy field should be merged
        assert request.filters.city_wise_search_origin is True

    def test_legacy_single_row_return_missing_airports_raises_validation_error(self):
        """Deprecated Return+return_date without airports raises a clear error, not KeyError."""
        with pytest.raises(ValidationError) as exc_info:
            FlightSearchRequest.model_validate(
                {
                    "journey_type": "Return",
                    "origin_destination_info": [
                        {
                            "departure_date": "2025-06-01",
                            "return_date": "2025-06-15",
                        }
                    ],
                    "cabin_class": "Economy",
                    "adults": 1,
                    "children": 0,
                    "infants": 0,
                }
            )
        assert "origin_airport" in str(exc_info.value).lower()


# ==============================================================================
# SCHEMA VALIDATION TESTS
# ==============================================================================


class TestFlightSearchFiltersSchema:
    """Test FlightSearchFilters schema validation."""

    def test_filters_schema_all_fields_optional(self):
        """Test that all fields in FlightSearchFilters are optional."""
        filters = FlightSearchFilters()
        assert filters is not None
        assert filters.min_price is None
        assert filters.max_price is None
        assert filters.is_refundable is None
        assert filters.carrier is None
        assert filters.max_stops is None
        assert filters.operating_airlines is None
        assert filters.journey_filters is None

    def test_filters_schema_with_all_fields(self):
        """Test that filters can be created with all fields."""
        filters = FlightSearchFilters(
            min_price=100.0,
            max_price=1000.0,
            is_refundable=True,
            carrier="GDS",
            max_stops=1,
            operating_airlines=["Emirates"],
            journey_filters=[LegFilter(leg_index=0)],
        )
        assert filters.min_price == 100.0
        assert filters.max_price == 1000.0
        assert filters.is_refundable is True
        assert filters.carrier == "GDS"
        assert filters.max_stops == 1
        assert filters.operating_airlines == ["Emirates"]
        assert len(filters.journey_filters) == 1


class TestLegFilterSchema:
    """Test LegFilter schema validation."""

    def test_leg_filter_leg_index_required(self):
        """Test that leg_index is required in LegFilter."""
        with pytest.raises(ValidationError):
            LegFilter()  # Missing required leg_index

    def test_leg_filter_all_optional_fields(self):
        """Test that all fields except leg_index are optional."""
        leg_filter = LegFilter(leg_index=0)
        assert leg_filter.leg_index == 0
        assert leg_filter.description is None
        assert leg_filter.city_wise_search is None
        assert leg_filter.departure_window is None
        assert leg_filter.arrival_window is None
        assert leg_filter.max_duration_minutes is None
        assert leg_filter.excluded_layover_airports is None
        assert leg_filter.allowed_layover_airports is None

    def test_leg_filter_with_all_fields(self):
        """Test that LegFilter can be created with all fields."""
        leg_filter = LegFilter(
            leg_index=0,
            description="Outbound leg",
            city_wise_search=True,
            departure_window=TimeWindow(min="06:00", max="12:00"),
            arrival_window=TimeWindow(min="14:00", max="20:00"),
            max_duration_minutes=600,
            excluded_layover_airports=["DXB"],
            allowed_layover_airports=["IST", "DOH"],
        )
        assert leg_filter.leg_index == 0
        assert leg_filter.description == "Outbound leg"
        assert leg_filter.city_wise_search is True
        assert leg_filter.departure_window is not None
        assert leg_filter.arrival_window is not None
        assert leg_filter.max_duration_minutes == 600
        assert leg_filter.excluded_layover_airports == ["DXB"]
        assert leg_filter.allowed_layover_airports == ["IST", "DOH"]


class TestTimeWindowSchema:
    """Test TimeWindow schema validation."""

    def test_time_window_min_required(self):
        """Test that min is required in TimeWindow."""
        with pytest.raises(ValidationError):
            TimeWindow(max="12:00")  # Missing required min

    def test_time_window_max_required(self):
        """Test that max is required in TimeWindow."""
        with pytest.raises(ValidationError):
            TimeWindow(min="06:00")  # Missing required max

    def test_time_window_valid_format(self):
        """Test that TimeWindow accepts valid HH:mm format."""
        time_window = TimeWindow(min="06:00", max="12:00")
        assert time_window.min == "06:00"
        assert time_window.max == "12:00"

    def test_time_window_edge_times(self):
        """Test that TimeWindow accepts edge case valid times."""
        # Midnight
        time_window1 = TimeWindow(min="00:00", max="23:59")
        assert time_window1.min == "00:00"
        assert time_window1.max == "23:59"

        # Noon
        time_window2 = TimeWindow(min="12:00", max="12:00")
        assert time_window2.min == "12:00"
        assert time_window2.max == "12:00"

    def test_time_window_rejects_invalid_hour(self):
        """Test that TimeWindow rejects invalid hour values."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindow(min="25:00", max="12:00")  # Hour > 23
        assert "Time must be in HH:mm format" in str(exc_info.value)

    def test_time_window_rejects_invalid_minute(self):
        """Test that TimeWindow rejects invalid minute values."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindow(min="12:60", max="14:00")  # Minute > 59
        assert "Time must be in HH:mm format" in str(exc_info.value)

    def test_time_window_rejects_single_digit_hour(self):
        """Test that TimeWindow rejects single digit hour (requires HH:mm)."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindow(min="6:00", max="12:00")  # Single digit hour
        assert "Time must be in HH:mm format" in str(exc_info.value)

    def test_time_window_rejects_invalid_format(self):
        """Test that TimeWindow rejects invalid time formats."""
        # Missing leading zero on minute
        with pytest.raises(ValidationError):
            TimeWindow(min="06:0", max="12:00")

        # Extra characters
        with pytest.raises(ValidationError):
            TimeWindow(min="06:00:00", max="12:00")

        # Wrong separator
        with pytest.raises(ValidationError):
            TimeWindow(min="06-00", max="12:00")


class TestCarrierFilterValidation:
    """Test carrier filter Literal type validation."""

    def test_carrier_gds_valid(self):
        """Test that GDS is a valid carrier value."""
        filters = FlightSearchFilters(carrier="GDS")
        assert filters.carrier == "GDS"

    def test_carrier_lcc_valid(self):
        """Test that LCC is a valid carrier value."""
        filters = FlightSearchFilters(carrier="LCC")
        assert filters.carrier == "LCC"

    def test_carrier_none_valid(self):
        """Test that None is a valid carrier value (no filter)."""
        filters = FlightSearchFilters(carrier=None)
        assert filters.carrier is None

    def test_carrier_invalid_value_rejected(self):
        """Test that invalid carrier values are rejected at schema level."""
        with pytest.raises(ValidationError) as exc_info:
            FlightSearchFilters(carrier="INVALID")
        error_str = str(exc_info.value)
        # Pydantic Literal validation error
        assert "carrier" in error_str.lower()

    def test_carrier_lowercase_rejected(self):
        """Test that lowercase carrier values are rejected (case-sensitive)."""
        with pytest.raises(ValidationError):
            FlightSearchFilters(carrier="gds")  # Should be "GDS"

    def test_carrier_typo_rejected(self):
        """Test that common typos in carrier values are rejected."""
        with pytest.raises(ValidationError):
            FlightSearchFilters(carrier="gds ")  # Trailing space

        with pytest.raises(ValidationError):
            FlightSearchFilters(carrier="AIRLINE")  # Wrong value
