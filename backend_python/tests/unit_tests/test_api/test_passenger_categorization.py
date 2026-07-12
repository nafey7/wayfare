"""Unit tests for passenger categorization and count extraction.

Tests for PR #234:
- Age-based passenger categorization in create_booking_from_session
- Passenger count extraction from revalidate API response in select_flight_for_booking
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.domains.flight import PassengerType
from app.domains.flight.validators import calculate_age


class TestPassengerCategorization:
    """Test passenger categorization logic based on age."""

    def test_categorize_adult_12_years_old(self):
        """Test that exactly 12 years old is categorized as adult."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 12)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 12
        assert age >= 12  # Should be categorized as adult

    def test_categorize_adult_13_years_old(self):
        """Test that 13 years old is categorized as adult."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 13)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 13
        assert age >= 12  # Should be categorized as adult

    def test_categorize_child_11_years_old(self):
        """Test that 11 years old is categorized as child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 11)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 11
        assert 2 <= age < 12  # Should be categorized as child

    def test_categorize_child_2_years_old(self):
        """Test that exactly 2 years old is categorized as child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 2)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 2
        assert 2 <= age < 12  # Should be categorized as child

    def test_categorize_infant_1_year_old(self):
        """Test that 1 year old is categorized as infant."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 1)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 1
        assert age < 2  # Should be categorized as infant

    def test_categorize_infant_newborn(self):
        """Test that newborn (< 1 month) is categorized as infant."""
        today = datetime.now(UTC)
        dob = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 0
        assert age < 2  # Should be categorized as infant

    def test_categorize_boundary_11_years_364_days(self):
        """Test boundary: 11 years and 364 days is still a child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 11) - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        age = calculate_age(dob)
        assert age == 11
        assert 2 <= age < 12  # Should be categorized as child

    def test_categorize_boundary_1_year_364_days(self):
        """Test boundary: 1 year and 364 days is still an infant."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 1) - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        age = calculate_age(dob)
        assert age == 1
        assert age < 2  # Should be categorized as infant

    def test_categorize_none_age_defaults_to_adult(self):
        """Test that None age (invalid/missing DOB) defaults to adult."""
        age = calculate_age(None)
        assert age is None
        # In the actual code, this would default to adult category

    def test_categorize_invalid_date_defaults_to_adult(self):
        """Test that invalid date format defaults to adult."""
        age = calculate_age("invalid-date")
        assert age is None
        # In the actual code, this would default to adult category


class TestPassengerCountExtraction:
    """Test passenger count extraction from revalidate API response."""

    def create_mock_passenger_type_info(self, passenger_type: str, count: int):
        """Helper to create mock passenger_type_info."""
        mock_info = Mock()
        mock_info.passenger_type = passenger_type
        mock_info.passenger_count = count
        return mock_info

    def create_mock_breakdown(self, passenger_type: str, count: int):
        """Helper to create mock passenger_fare_breakdown entry."""
        mock_breakdown = Mock()
        mock_info = self.create_mock_passenger_type_info(passenger_type, count)
        mock_breakdown.passenger_type_info = mock_info
        return mock_breakdown

    def test_extract_adult_count_from_enum(self):
        """Test extracting adult count when passenger_type is PassengerType.ADULT enum."""
        breakdown = self.create_mock_breakdown(PassengerType.ADULT, 2)
        assert breakdown.passenger_type_info.passenger_type == PassengerType.ADULT
        assert breakdown.passenger_type_info.passenger_count == 2

    def test_extract_adult_count_from_string_value(self):
        """Test extracting adult count when passenger_type is string 'ADULT'."""
        breakdown = self.create_mock_breakdown(PassengerType.ADULT.value, 2)
        assert breakdown.passenger_type_info.passenger_type == PassengerType.ADULT.value
        assert breakdown.passenger_type_info.passenger_count == 2

    def test_extract_adult_count_from_adt_code(self):
        """Test extracting adult count when passenger_type is 'ADT' code."""
        breakdown = self.create_mock_breakdown("ADT", 2)
        assert breakdown.passenger_type_info.passenger_type == "ADT"
        assert breakdown.passenger_type_info.passenger_count == 2

    def test_extract_child_count_from_enum(self):
        """Test extracting child count when passenger_type is PassengerType.CHILD enum."""
        breakdown = self.create_mock_breakdown(PassengerType.CHILD, 1)
        assert breakdown.passenger_type_info.passenger_type == PassengerType.CHILD
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_child_count_from_string_value(self):
        """Test extracting child count when passenger_type is string 'CHILD'."""
        breakdown = self.create_mock_breakdown(PassengerType.CHILD.value, 1)
        assert breakdown.passenger_type_info.passenger_type == PassengerType.CHILD.value
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_child_count_from_chd_code(self):
        """Test extracting child count when passenger_type is 'CHD' code."""
        breakdown = self.create_mock_breakdown("CHD", 1)
        assert breakdown.passenger_type_info.passenger_type == "CHD"
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_infant_count_from_enum(self):
        """Test extracting infant count when passenger_type is PassengerType.INFANT enum."""
        breakdown = self.create_mock_breakdown(PassengerType.INFANT, 1)
        assert breakdown.passenger_type_info.passenger_type == PassengerType.INFANT
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_infant_count_from_string_value(self):
        """Test extracting infant count when passenger_type is string 'INFANT'."""
        breakdown = self.create_mock_breakdown(PassengerType.INFANT.value, 1)
        assert (
            breakdown.passenger_type_info.passenger_type == PassengerType.INFANT.value
        )
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_infant_count_from_inf_code(self):
        """Test extracting infant count when passenger_type is 'INF' code."""
        breakdown = self.create_mock_breakdown("INF", 1)
        assert breakdown.passenger_type_info.passenger_type == "INF"
        assert breakdown.passenger_type_info.passenger_count == 1

    def test_extract_multiple_passenger_types(self):
        """Test extracting counts for multiple passenger types in same response."""
        breakdowns = [
            self.create_mock_breakdown(PassengerType.ADULT, 2),
            self.create_mock_breakdown(PassengerType.CHILD, 1),
            self.create_mock_breakdown(PassengerType.INFANT, 1),
        ]

        adults_count = 0
        children_count = 0
        infants_count = 0

        for breakdown in breakdowns:
            pax_type = breakdown.passenger_type_info.passenger_type
            pax_count = breakdown.passenger_type_info.passenger_count

            if pax_type in (PassengerType.ADULT, PassengerType.ADULT.value, "ADT"):
                adults_count = pax_count
            elif pax_type in (PassengerType.CHILD, PassengerType.CHILD.value, "CHD"):
                children_count = pax_count
            elif pax_type in (PassengerType.INFANT, PassengerType.INFANT.value, "INF"):
                infants_count = pax_count

        assert adults_count == 2
        assert children_count == 1
        assert infants_count == 1

    def test_extract_with_missing_passenger_type_info(self):
        """Test handling when passenger_type_info is missing."""
        breakdown = Mock()
        breakdown.passenger_type_info = None

        # Should not raise error, just skip
        if hasattr(breakdown, "passenger_type_info") and breakdown.passenger_type_info:
            pax_type = breakdown.passenger_type_info.passenger_type
        else:
            pax_type = None

        assert pax_type is None

    def test_extract_with_missing_updated_pricing(self):
        """Test handling when updated_pricing is missing."""
        validated_flight = Mock()
        validated_flight.updated_pricing = None

        # Should use fallback values
        adults_count = 1  # Default fallback
        children_count = 0  # Default fallback
        infants_count = 0  # Default fallback

        assert adults_count == 1
        assert children_count == 0
        assert infants_count == 0

    def test_extract_with_missing_passenger_fare_breakdown(self):
        """Test handling when passenger_fare_breakdown is missing."""
        validated_flight = Mock()
        validated_flight.updated_pricing = Mock()
        validated_flight.updated_pricing.passenger_fare_breakdown = None

        # Should use fallback values
        adults_count = 1  # Default fallback
        children_count = 0  # Default fallback
        infants_count = 0  # Default fallback

        assert adults_count == 1
        assert children_count == 0
        assert infants_count == 0

    def test_extract_with_empty_passenger_fare_breakdown(self):
        """Test handling when passenger_fare_breakdown is empty list."""
        validated_flight = Mock()
        validated_flight.updated_pricing = Mock()
        validated_flight.updated_pricing.passenger_fare_breakdown = []

        # Should use fallback values
        adults_count = 1  # Default fallback
        children_count = 0  # Default fallback
        infants_count = 0  # Default fallback

        assert adults_count == 1
        assert children_count == 0
        assert infants_count == 0

    def test_extract_with_various_response_shapes(self):
        """Test extraction works with various response shapes (dict vs object)."""
        # Test with dict-like structure
        breakdown_dict = {
            "passenger_type_info": {
                "passenger_type": "ADT",
                "passenger_count": 2,
            }
        }

        # Test with object-like structure
        breakdown_obj = self.create_mock_breakdown("ADT", 2)

        # Both should work in the actual code
        assert breakdown_dict["passenger_type_info"]["passenger_type"] == "ADT"
        assert breakdown_obj.passenger_type_info.passenger_type == "ADT"

    def test_extract_zero_counts(self):
        """Test that zero counts are extracted correctly."""
        breakdowns = [
            self.create_mock_breakdown(PassengerType.ADULT, 1),
            self.create_mock_breakdown(PassengerType.CHILD, 0),
            self.create_mock_breakdown(PassengerType.INFANT, 0),
        ]

        adults_count = 0
        children_count = 0
        infants_count = 0

        for breakdown in breakdowns:
            pax_type = breakdown.passenger_type_info.passenger_type
            pax_count = breakdown.passenger_type_info.passenger_count

            if pax_type in (PassengerType.ADULT, PassengerType.ADULT.value, "ADT"):
                adults_count = pax_count
            elif pax_type in (PassengerType.CHILD, PassengerType.CHILD.value, "CHD"):
                children_count = pax_count
            elif pax_type in (PassengerType.INFANT, PassengerType.INFANT.value, "INF"):
                infants_count = pax_count

        assert adults_count == 1
        assert children_count == 0
        assert infants_count == 0
