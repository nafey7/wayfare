"""Unit tests for datetime parsing in FlightLogic adapters.

Tests ensure that datetime parsing preserves time components exactly as provided
without timezone conversion. Flight times should be displayed as local airport time.
"""

import pytest

from integrations.flightlogic.adapter import (
    FlightLogicSchemaAdapter,
    _parse_datetime_string,
)
from integrations.flightlogic.trip_details_adapter import _parse_datetime


class TestParseDatetimeString:
    """Test _parse_datetime_string function."""

    def test_returns_naive_datetime(self):
        """Verify _parse_datetime_string returns naive datetime (no timezone)."""
        result = _parse_datetime_string("2025-01-15T10:30:00")

        assert result.tzinfo is None  # Must be naive
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_strips_timezone_info_from_utc(self):
        """When input has UTC timezone (Z), result should be naive with same time."""
        result = _parse_datetime_string("2025-01-15T10:30:00Z")

        assert result.tzinfo is None  # Must be naive
        assert result.hour == 10
        assert result.minute == 30
        # Time should be preserved exactly, not converted

    def test_strips_timezone_info_from_offset(self):
        """When input has timezone offset, result should be naive with same time."""
        # Input with +05:00 offset
        result = _parse_datetime_string("2025-01-15T10:30:00+05:00")

        assert result.tzinfo is None  # Must be naive
        assert result.hour == 10  # Should preserve hour, not convert
        assert result.minute == 30

    def test_preserves_time_components_exactly(self):
        """Time components should be preserved exactly, no conversion."""
        # Even if input has timezone, output should preserve the time as-is
        result = _parse_datetime_string("2025-01-15T14:45:00Z")

        # Should be 14:45, not converted to local time
        assert result.hour == 14
        assert result.minute == 45
        assert result.tzinfo is None

    def test_handles_space_separated_format(self):
        """Should handle space-separated datetime format."""
        result = _parse_datetime_string("2025-01-15 10:30:00")

        assert result.tzinfo is None
        assert result.hour == 10
        assert result.minute == 30

    def test_handles_microseconds(self):
        """Should handle datetime with microseconds."""
        result = _parse_datetime_string("2025-01-15T10:30:00.123456")

        assert result.tzinfo is None
        assert result.hour == 10
        assert result.minute == 30
        assert result.microsecond == 123456

    def test_handles_date_only(self):
        """Should handle date-only format."""
        result = _parse_datetime_string("2025-01-15")

        assert result.tzinfo is None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0

    def test_raises_error_for_empty_string(self):
        """Should raise ValueError for empty string."""
        with pytest.raises(ValueError, match="Empty datetime string"):
            _parse_datetime_string("")

    def test_raises_error_for_invalid_format(self):
        """Should raise ValueError for invalid format."""
        with pytest.raises(ValueError, match="Unable to parse"):
            _parse_datetime_string("invalid-datetime")


class TestParseDatetimeInAdapter:
    """Test FlightLogicSchemaAdapter._parse_datetime method."""

    @pytest.fixture
    def adapter(self):
        """Create FlightLogicSchemaAdapter instance for testing."""
        return FlightLogicSchemaAdapter()

    def test_returns_datetime_wrapper_with_naive_datetime(self, adapter):
        """Verify _parse_datetime returns DateTime wrapper with naive datetime."""
        result = adapter._parse_datetime("2025-01-15T10:30:00")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_strips_timezone_info_from_utc(self, adapter):
        """When input has UTC timezone (Z), result should be naive with same time."""
        result = adapter._parse_datetime("2025-01-15T10:30:00Z")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_strips_timezone_info_from_offset(self, adapter):
        """When input has timezone offset, result should be naive with same time."""
        result = adapter._parse_datetime("2025-01-15T10:30:00+05:00")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10  # Should preserve hour, not convert
        assert result.value.minute == 30

    def test_preserves_time_components_exactly(self, adapter):
        """Time components should be preserved exactly, no conversion."""
        result = adapter._parse_datetime("2025-01-15T14:45:00Z")

        # Should be 14:45, not converted to local time
        assert result.value.hour == 14
        assert result.value.minute == 45
        assert result.value.tzinfo is None

    def test_handles_iso_format(self, adapter):
        """Should handle ISO format datetime."""
        result = adapter._parse_datetime("2025-01-15T10:30:00")

        assert result.value.tzinfo is None
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_raises_error_for_empty_string(self, adapter):
        """Should raise ConversionError for empty string."""
        from integrations.flightlogic.adapter import ConversionError

        with pytest.raises(ConversionError, match="Missing datetime string"):
            adapter._parse_datetime("")

    def test_raises_error_for_invalid_format(self, adapter):
        """Should raise ConversionError for invalid format."""
        from integrations.flightlogic.adapter import ConversionError

        with pytest.raises(ConversionError, match="Invalid datetime format"):
            adapter._parse_datetime("invalid-datetime")


class TestParseDatetimeInTripDetailsAdapter:
    """Test trip_details_adapter._parse_datetime function."""

    def test_returns_datetime_wrapper_with_naive_datetime(self):
        """Verify _parse_datetime returns DateTime wrapper with naive datetime."""
        result = _parse_datetime("2025-01-15T10:30:00")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_strips_timezone_info_from_utc(self):
        """When input has UTC timezone (Z), result should be naive with same time."""
        result = _parse_datetime("2025-01-15T10:30:00Z")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_strips_timezone_info_from_offset(self):
        """When input has timezone offset, result should be naive with same time."""
        result = _parse_datetime("2025-01-15T10:30:00+05:00")

        assert result.value.tzinfo is None  # Must be naive
        assert result.value.hour == 10  # Should preserve hour, not convert
        assert result.value.minute == 30

    def test_preserves_time_components_exactly(self):
        """Time components should be preserved exactly, no conversion."""
        result = _parse_datetime("2025-01-15T14:45:00Z")

        # Should be 14:45, not converted to local time
        assert result.value.hour == 14
        assert result.value.minute == 45
        assert result.value.tzinfo is None

    def test_handles_iso_format(self):
        """Should handle ISO format datetime."""
        result = _parse_datetime("2025-01-15T10:30:00")

        assert result.value.tzinfo is None
        assert result.value.hour == 10
        assert result.value.minute == 30

    def test_returns_current_time_for_empty_string(self):
        """Should return current time for empty string (fallback behavior)."""
        result = _parse_datetime("")

        assert result.value.tzinfo is None  # Should still be naive
        # Just verify it's a datetime object
        assert hasattr(result.value, "year")

    def test_handles_invalid_format_with_fallback(self):
        """Should fallback to current time for invalid format."""
        result = _parse_datetime("invalid-datetime")

        assert result.value.tzinfo is None  # Should still be naive
        # Just verify it's a datetime object (fallback to current time)
        assert hasattr(result.value, "year")


class TestTimePreservationAcrossFormats:
    """Test that same time is preserved across different timezone formats."""

    def test_same_time_different_timezones_produce_same_naive_datetime(self):
        """Same time string in different timezone formats should produce same naive datetime."""
        # All these should produce the same naive datetime (10:30)
        result1 = _parse_datetime_string("2025-01-15T10:30:00")
        result2 = _parse_datetime_string("2025-01-15T10:30:00Z")
        result3 = _parse_datetime_string("2025-01-15T10:30:00+00:00")

        # All should have same time components
        assert result1.hour == result2.hour == result3.hour == 10
        assert result1.minute == result2.minute == result3.minute == 30
        # All should be naive
        assert result1.tzinfo is None
        assert result2.tzinfo is None
        assert result3.tzinfo is None

    def test_time_with_offset_preserves_time_not_converts(self):
        """Time with offset should preserve the time value, not convert it."""
        # Input: 10:30 with +05:00 offset
        # Output should be naive 10:30, NOT 05:30 (which would be conversion)
        result = _parse_datetime_string("2025-01-15T10:30:00+05:00")

        assert result.hour == 10  # Preserved, not converted
        assert result.minute == 30
        assert result.tzinfo is None
