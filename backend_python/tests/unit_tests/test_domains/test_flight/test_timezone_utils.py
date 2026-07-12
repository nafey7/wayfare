"""Unit tests for timezone conversion utilities for flight bookings.

Tests cover:
- Known airports (JFK, LHR) with timezone conversion
- Unknown airports (fallback behavior)
- DST transitions
- Edge cases (naive/aware datetimes)
- pytz vs zoneinfo fallback
- Missing timezone field in airport data
- Exception handling
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.flight.timezone_utils import (
    convert_ticket_time_limit_to_utc,
)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def get_test_date(month: int, day: int, year_offset: int = 0) -> datetime:
    """Generate a test date dynamically based on current date.

    Calculates a date by taking current date, adding 3-4 months, then adjusting
    to the specified month and day. This ensures tests use future dates that
    remain valid as time passes.

    Args:
        month: Target month (1-12)
        day: Target day (1-31)
        year_offset: Optional year offset to add (e.g., for leap year tests)

    Returns:
        datetime object with the specified month and day in a future year
    """
    # Calculate base date: current date + 3-4 months
    base_date = datetime.now(tz=UTC).date()
    # Add 3-4 months (approximately 100 days)
    future_date = base_date + timedelta(days=100)

    # Use the year from the future date, or add offset if specified
    target_year = future_date.year + year_offset

    # Adjust to target month and day
    try:
        return datetime(target_year, month, day)
    except ValueError:
        # Handle invalid dates (e.g., Feb 29 in non-leap year)
        # Fall back to Feb 28 or adjust to valid date
        if month == 2 and day == 29:
            # Try to find next leap year
            for y in range(target_year, target_year + 4):
                try:
                    return datetime(y, 2, 29)
                except ValueError:
                    continue
            # If no leap year found, use Feb 28
            return datetime(target_year, 2, 28)
        raise


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_airport_resolver():
    """Mock airport resolver for testing."""
    with patch("app.domains.flight.timezone_utils.airport_resolver") as mock_resolver:
        yield mock_resolver


# ==============================================================================
# KNOWN AIRPORTS - JFK (America/New_York)
# ==============================================================================


class TestKnownAirportJFK:
    """Test timezone conversion for JFK (America/New_York)."""

    @pytest.mark.asyncio
    async def test_jfk_naive_datetime_winter(self, mock_airport_resolver):
        """Test JFK naive datetime conversion during EST (UTC-5)."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # January 15, future year 10:00 AM EST (UTC-5) = 15:00 UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should convert to UTC: 10:00 EST + 5 hours = 15:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_jfk_naive_datetime_summer(self, mock_airport_resolver):
        """Test JFK naive datetime conversion during EDT (UTC-4)."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # July 15, future year 10:00 AM EDT (UTC-4) = 14:00 UTC
        test_date = get_test_date(7, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should convert to UTC: 10:00 EDT + 4 hours = 14:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 14, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_jfk_aware_datetime_stripped(self, mock_airport_resolver):
        """Test JFK aware datetime (incorrectly marked as UTC) is stripped and converted."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # January 15, future year 10:00 AM (incorrectly marked as UTC, but should be EST)
        # This simulates the bug where _parse_datetime_string() marks it as UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should strip UTC timezone, treat as EST, then convert to UTC
        # 10:00 EST = 15:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_jfk_case_insensitive(self, mock_airport_resolver):
        """Test that IATA code is case-insensitive."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "jfk")  # lowercase

        # Should still work
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert mock_airport_resolver.get_airport_info.called
        # Should be called with uppercase
        assert mock_airport_resolver.get_airport_info.call_args[0][0] == "JFK"


# ==============================================================================
# KNOWN AIRPORTS - LHR (Europe/London)
# ==============================================================================


class TestKnownAirportLHR:
    """Test timezone conversion for LHR (Europe/London)."""

    @pytest.mark.asyncio
    async def test_lhr_naive_datetime_winter(self, mock_airport_resolver):
        """Test LHR naive datetime conversion during GMT (UTC+0)."""
        # Mock airport info for LHR
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "LHR",
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "United Kingdom",
                "tz": "Europe/London",
            }
        )

        # January 15, future year 10:00 AM GMT (UTC+0) = 10:00 UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "LHR")

        # Should convert to UTC: 10:00 GMT = 10:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_lhr_naive_datetime_summer(self, mock_airport_resolver):
        """Test LHR naive datetime conversion during BST (UTC+1)."""
        # Mock airport info for LHR
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "LHR",
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "United Kingdom",
                "tz": "Europe/London",
            }
        )

        # July 15, future year 10:00 AM BST (UTC+1) = 09:00 UTC
        test_date = get_test_date(7, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "LHR")

        # Should convert to UTC: 10:00 BST - 1 hour = 09:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 9, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_lhr_dst_transition_spring(self, mock_airport_resolver):
        """Test LHR DST transition in spring (GMT -> BST)."""
        # Mock airport info for LHR
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "LHR",
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "United Kingdom",
                "tz": "Europe/London",
            }
        )

        # March 31, future year 1:00 AM GMT (before DST) = 01:00 UTC
        # March 31, future year 2:00 AM BST (after DST) = 01:00 UTC (clock jumps forward)
        # Testing at 2:00 AM local time (should be 01:00 UTC)
        test_date = get_test_date(3, 31)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 2, 0, 0
        )  # After DST transition
        result = await convert_ticket_time_limit_to_utc(local_time, "LHR")

        # Should convert to UTC: 2:00 BST = 01:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 1, 0, 0, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_lhr_dst_transition_fall(self, mock_airport_resolver):
        """Test LHR DST transition in fall (BST -> GMT)."""
        # Mock airport info for LHR
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "LHR",
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "United Kingdom",
                "tz": "Europe/London",
            }
        )

        # October 27, future year 2:00 AM BST (before DST ends) = 01:00 UTC
        # October 27, future year 2:00 AM GMT (after DST ends) = 02:00 UTC (clock jumps back)
        # Testing at 2:00 AM local time (should be 02:00 UTC after transition)
        test_date = get_test_date(10, 27)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 2, 0, 0
        )  # After DST ends
        result = await convert_ticket_time_limit_to_utc(local_time, "LHR")

        # Should convert to UTC: 2:00 GMT = 02:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 2, 0, 0, tzinfo=UTC
        )
        assert result == expected


# ==============================================================================
# UNKNOWN AIRPORTS - FALLBACK BEHAVIOR
# ==============================================================================


class TestUnknownAirport:
    """Test fallback behavior for unknown airports."""

    @pytest.mark.asyncio
    async def test_unknown_airport_returns_none(self, mock_airport_resolver):
        """Test that unknown airport returns None and falls back to UTC."""
        # Mock airport resolver to return None (airport not found)
        mock_airport_resolver.get_airport_info = AsyncMock(return_value=None)

        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "XXX")

        # Should fallback to UTC: naive datetime gets UTC timezone
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_unknown_airport_aware_datetime(self, mock_airport_resolver):
        """Test that unknown airport with aware datetime returns as-is."""
        # Mock airport resolver to return None (airport not found)
        mock_airport_resolver.get_airport_info = AsyncMock(return_value=None)

        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        result = await convert_ticket_time_limit_to_utc(local_time, "XXX")

        # Should return as-is (already has timezone)
        assert result == local_time
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_empty_airport_code(self, mock_airport_resolver):
        """Test that empty airport code falls back to UTC."""
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "")

        # Should fallback to UTC: naive datetime gets UTC timezone
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

        # Should not call airport resolver
        mock_airport_resolver.get_airport_info.assert_not_called()


# ==============================================================================
# MISSING TIMEZONE FIELD
# ==============================================================================


class TestMissingTimezoneField:
    """Test behavior when airport found but timezone field is missing."""

    @pytest.mark.asyncio
    async def test_airport_found_no_tz_field(self, mock_airport_resolver):
        """Test that airport without 'tz' field falls back to UTC."""
        # Mock airport info without timezone field
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                # Missing "tz" field
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should fallback to UTC: naive datetime gets UTC timezone
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_airport_found_empty_tz_field(self, mock_airport_resolver):
        """Test that airport with empty 'tz' field falls back to UTC."""
        # Mock airport info with empty timezone field
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "",  # Empty timezone
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should fallback to UTC: naive datetime gets UTC timezone
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC


# ==============================================================================
# PYTZ VS ZONEINFO FALLBACK
# ==============================================================================


class TestTimezoneLibraryFallback:
    """Test pytz vs zoneinfo fallback behavior.

    Note: Testing the actual fallback mechanism is complex because zoneinfo
    is imported inside the function. These tests verify that the function
    works correctly with the available timezone library (zoneinfo on Python 3.9+).
    """

    @pytest.mark.asyncio
    async def test_zoneinfo_available(self, mock_airport_resolver):
        """Test that zoneinfo is used when available (Python 3.9+)."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should work with zoneinfo (Python 3.9+)
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_timezone_conversion_works(self, mock_airport_resolver):
        """Test that timezone conversion works correctly (verifies library integration)."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Verify conversion is correct (5 hour offset for EST)
        # This confirms the timezone library (zoneinfo or pytz) is working
        assert result.hour == 15  # 10:00 EST + 5 hours = 15:00 UTC
        assert result.tzinfo == UTC


# ==============================================================================
# EXCEPTION HANDLING
# ==============================================================================


class TestExceptionHandling:
    """Test exception handling and fallback behavior."""

    @pytest.mark.asyncio
    async def test_airport_resolver_exception(self, mock_airport_resolver):
        """Test that exception in airport resolver falls back to UTC."""
        # Mock airport resolver to raise exception
        mock_airport_resolver.get_airport_info = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0
        )  # Naive datetime
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should fallback to UTC: naive datetime gets UTC timezone
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
        assert result.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_invalid_timezone_exception(self, mock_airport_resolver):
        """Test that invalid timezone string falls back gracefully."""
        # Mock airport info with invalid timezone
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "Invalid/Timezone",  # Invalid timezone
            }
        )

        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)

        # Should handle exception and fallback to UTC
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should fallback to UTC
        assert result.tzinfo == UTC


# ==============================================================================
# EDGE CASES
# ==============================================================================


class TestEdgeCases:
    """Test edge cases for datetime handling."""

    @pytest.mark.asyncio
    async def test_midnight_local_time(self, mock_airport_resolver):
        """Test conversion at midnight local time."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # January 15, future year 00:00:00 EST = 05:00 UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 0, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        expected = datetime(
            test_date.year, test_date.month, test_date.day, 5, 0, 0, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_end_of_day_local_time(self, mock_airport_resolver):
        """Test conversion at end of day local time."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # January 15, future year 23:59:59 EST = 04:59:59 UTC (next day)
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 23, 59, 59
        )
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Calculate next day using timedelta to handle month boundaries
        next_day = test_date + timedelta(days=1)
        expected = datetime(
            next_day.year, next_day.month, next_day.day, 4, 59, 59, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_leap_year_date(self, mock_airport_resolver):
        """Test conversion on leap year date."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # February 29, future leap year 10:00 AM EST = 15:00 UTC
        # get_test_date will find the next leap year
        test_date = get_test_date(2, 29)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_aware_datetime_different_timezone(self, mock_airport_resolver):
        """Test that aware datetime with different timezone is stripped and converted."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # Create a datetime with Europe/London timezone (incorrectly marked)
        # This simulates the bug where datetime is marked with wrong timezone
        from zoneinfo import ZoneInfo

        test_date = get_test_date(1, 15)
        london_tz = ZoneInfo("Europe/London")
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=london_tz
        )

        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should strip London timezone, treat as EST, then convert to UTC
        # 10:00 EST = 15:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_naive_datetime_with_microseconds(self, mock_airport_resolver):
        """Test conversion preserves microseconds."""
        # Mock airport info for JFK
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "JFK",
                "name": "John F Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "tz": "America/New_York",
            }
        )

        # January 15, future year 10:00:00.123456 EST
        test_date = get_test_date(1, 15)
        local_time = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, 123456
        )
        result = await convert_ticket_time_limit_to_utc(local_time, "JFK")

        # Should preserve microseconds
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 15, 0, 0, 123456, tzinfo=UTC
        )
        assert result == expected
        assert result.microsecond == 123456

    @pytest.mark.asyncio
    async def test_different_timezone_offsets(self, mock_airport_resolver):
        """Test conversion with airports in different timezone offsets."""
        # Test Tokyo (UTC+9) - no DST
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "NRT",
                "name": "Narita International Airport",
                "city": "Tokyo",
                "country": "Japan",
                "tz": "Asia/Tokyo",
            }
        )

        # January 15, future year 10:00 AM JST = 01:00 UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "NRT")

        # Should convert: 10:00 JST - 9 hours = 01:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 1, 0, 0, tzinfo=UTC
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_utc_timezone_airport(self, mock_airport_resolver):
        """Test conversion with airport already in UTC timezone."""
        # Test Accra, Ghana (UTC+0, no DST)
        mock_airport_resolver.get_airport_info = AsyncMock(
            return_value={
                "iata": "ACC",
                "name": "Kotoka International Airport",
                "city": "Accra",
                "country": "Ghana",
                "tz": "Africa/Accra",
            }
        )

        # January 15, future year 10:00 AM GMT = 10:00 UTC
        test_date = get_test_date(1, 15)
        local_time = datetime(test_date.year, test_date.month, test_date.day, 10, 0, 0)
        result = await convert_ticket_time_limit_to_utc(local_time, "ACC")

        # Should convert: 10:00 GMT = 10:00 UTC
        expected = datetime(
            test_date.year, test_date.month, test_date.day, 10, 0, 0, tzinfo=UTC
        )
        assert result == expected
