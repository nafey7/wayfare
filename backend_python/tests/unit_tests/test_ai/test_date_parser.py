"""Unit tests for DateParser utility."""

from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from app.ai.utils.date_parser import DateParser


class TestConvertWordToNumber:
    """Tests for convert_word_to_number method."""

    @pytest.mark.parametrize(
        ("word", "expected"),
        [
            ("one", 1),
            ("two", 2),
            ("three", 3),
            ("four", 4),
            ("five", 5),
            ("six", 6),
            ("seven", 7),
            ("eight", 8),
            ("nine", 9),
            ("ten", 10),
            ("a", 1),
            ("an", 1),
            ("ONE", 1),  # case insensitive
            ("Two", 2),
            ("invalid", None),
            ("eleven", None),
        ],
    )
    def test_word_conversion(self, word: str, expected: int | None) -> None:
        assert DateParser.convert_word_to_number(word) == expected


class TestParseRelativeTime:
    """Tests for parse_relative_time method."""

    @pytest.fixture
    def reference_date(self) -> date:
        """Fixed reference date for testing."""
        return date(2025, 12, 8)  # Monday (weekday=0)

    def test_tomorrow(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("tomorrow", reference_date)
        assert result == reference_date + timedelta(days=1)

    def test_today(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("today", reference_date)
        assert result == reference_date

    def test_tonight(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("tonight", reference_date)
        assert result == reference_date

    @pytest.mark.parametrize(
        ("message", "expected_days"),
        [
            ("2 weeks later", 14),
            ("two weeks later", 14),
            ("a week later", 7),
            ("1 week later", 7),
            ("3 days later", 3),
            ("three days later", 3),
        ],
    )
    def test_n_units_later(
        self, reference_date: date, message: str, expected_days: int
    ) -> None:
        result = DateParser.parse_relative_time(message, reference_date)
        assert result == reference_date + timedelta(days=expected_days)

    @pytest.mark.parametrize(
        ("message", "expected_days"),
        [
            ("in 2 weeks", 14),
            ("in two weeks", 14),
            ("in 3 days", 3),
            ("in a week", 7),
        ],
    )
    def test_in_n_units(
        self, reference_date: date, message: str, expected_days: int
    ) -> None:
        result = DateParser.parse_relative_time(message, reference_date)
        assert result == reference_date + timedelta(days=expected_days)

    @pytest.mark.parametrize(
        ("message", "expected_days"),
        [
            ("after 2 weeks", 14),
            ("after 3 days", 3),
        ],
    )
    def test_after_n_units(
        self, reference_date: date, message: str, expected_days: int
    ) -> None:
        result = DateParser.parse_relative_time(message, reference_date)
        assert result == reference_date + timedelta(days=expected_days)

    def test_standalone_units(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("2 weeks", reference_date)
        assert result == reference_date + timedelta(days=14)

    def test_returning_pattern(self, reference_date: date) -> None:
        """Flight-specific pattern: returning 2 weeks."""
        result = DateParser.parse_relative_time("returning 2 weeks", reference_date)
        assert result == reference_date + timedelta(days=14)

    def test_next_week(self, reference_date: date) -> None:
        """next week returns the following Monday."""
        result = DateParser.parse_relative_time("next week", reference_date)
        # reference_date is Sunday (weekday 6), so next Monday is 1 day away
        expected = reference_date + timedelta(days=(7 - reference_date.weekday()))
        assert result == expected

    def test_next_month(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("next month", reference_date)
        assert result == reference_date + timedelta(days=30)

    def test_next_weekend(self, reference_date: date) -> None:
        """next weekend returns next Saturday."""
        result = DateParser.parse_relative_time("next weekend", reference_date)
        # reference_date is Sunday (weekday 6), next Saturday (weekday 5) is 6 days away
        current_weekday = reference_date.weekday()
        days_to_saturday = (5 - current_weekday) % 7
        if days_to_saturday == 0:
            days_to_saturday = 7
        assert result == reference_date + timedelta(days=days_to_saturday)

    def test_following_friday(self, reference_date: date) -> None:
        """following Friday returns the next Friday from reference date."""
        result = DateParser.parse_relative_time("following Friday", reference_date)
        # reference_date is Monday (weekday 0), Friday is weekday 4
        # days_ahead = 4 - 0 = 4
        expected = reference_date + timedelta(days=4)
        assert result == expected
        assert expected.weekday() == 4  # Verify it's a Friday

    def test_bare_weekday(self, reference_date: date) -> None:
        """Just 'Friday' returns next Friday."""
        result = DateParser.parse_relative_time("Friday", reference_date)
        # reference_date is Monday (weekday 0), Friday is weekday 4
        expected = reference_date + timedelta(days=4)  # Monday -> Friday = 4 days
        assert result == expected
        assert expected.weekday() == 4

    def test_no_match_returns_none(self, reference_date: date) -> None:
        result = DateParser.parse_relative_time("random text", reference_date)
        assert result is None

    def test_weekday_patterns_disabled(self, reference_date: date) -> None:
        """When include_weekday_patterns=False, weekdays are not parsed."""
        result = DateParser.parse_relative_time(
            "Friday", reference_date, include_weekday_patterns=False
        )
        assert result is None

    def test_weekday_with_explicit_date_defers_to_absolute(
        self, reference_date: date
    ) -> None:
        """Weekday + explicit date should NOT match relative pattern.

        'Monday 26th January' should parse as Jan 26, not 'next Monday'.
        The weekday is just context/confirmation, not the primary date.
        """
        # These should return None from parse_relative_time (no relative match)
        # because they contain explicit dates that should be handled by
        # parse_absolute_date instead
        test_cases = [
            "Monday 26th January",
            "26th January Monday",
            "Friday December 5th",
            "December 5th Friday",
        ]
        for case in test_cases:
            result = DateParser.parse_relative_time(case, reference_date)
            assert result is None, f"'{case}' should not match relative pattern"

    def test_nights_unit(self, reference_date: date) -> None:
        """Hotel-specific: 3 nights should work like 3 days."""
        result = DateParser.parse_relative_time("3 nights later", reference_date)
        assert result == reference_date + timedelta(days=3)


class TestParseAbsoluteDate:
    """Tests for parse_absolute_date method."""

    @pytest.fixture
    def mock_today(self) -> date:
        """Fixed today for testing."""
        return date(2025, 10, 7)

    def test_date_object_passthrough(self) -> None:
        """Date objects are returned as-is."""
        input_date = date(2025, 12, 25)
        result = DateParser.parse_absolute_date(input_date)
        assert result == input_date

    def test_today_keyword(self) -> None:
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_absolute_date("today")
            assert result == date(2025, 10, 7)

    def test_tomorrow_keyword(self) -> None:
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_absolute_date("tomorrow")
            assert result == date(2025, 10, 8)

    def test_smart_year_selection_past_date(self) -> None:
        """Past dates without year get bumped to next year."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2026, 10, 7)
            result = DateParser.parse_absolute_date("Feb 14")
            assert result == date(2027, 2, 14)

    def test_future_date_same_year(self) -> None:
        """Future dates stay in current year."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2026, 10, 7)
            result = DateParser.parse_absolute_date("Nov 15")
            assert result == date(2026, 11, 15)

    def test_explicit_year_preserved(self) -> None:
        """Explicit years are not modified."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_absolute_date("Feb 14 2027")
            assert result == date(2027, 2, 14)

    def test_ordinal_numbers_cleaned(self) -> None:
        """5th, 1st, etc. are handled correctly."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2026, 10, 7)
            result = DateParser.parse_absolute_date("November 5th")
            assert result == date(2026, 11, 5)

    def test_of_removed(self) -> None:
        """'5th of November' handled correctly."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2026, 10, 7)
            result = DateParser.parse_absolute_date("5th of November")
            assert result == date(2026, 11, 5)

    def test_in_x_days(self) -> None:
        """'in 5 days' works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_absolute_date("in 5 days")
            assert result == date(2025, 10, 12)

    def test_next_weekday(self) -> None:
        """'next Monday' works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)  # Tuesday
            result = DateParser.parse_absolute_date("next Monday")
            # Tuesday (1) -> Monday (0): (0 - 1 + 7) % 7 = 6, but we want next week
            # Since days_ahead = 0 means same day, we add 7
            assert result == date(2025, 10, 13)

    def test_weekday_with_explicit_date(self) -> None:
        """'Monday 26th January' should parse as Jan 26, not next Monday.

        Regression test for bug where weekday name was prioritized over
        explicit date components.
        """
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 12, 31)
            # All should parse to January 26, 2026
            test_cases = [
                "Monday 26th January",
                "26th January Monday",
                "Monday January 26",
                "January 26 Monday",
            ]
            for case in test_cases:
                result = DateParser.parse_absolute_date(case)
                assert result == date(2026, 1, 26), f"'{case}' should be 2026-01-26"

    def test_explicit_leap_year_feb_29(self) -> None:
        """Feb 29 with explicit leap year works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2024, 1, 1)
            result = DateParser.parse_absolute_date("February 29 2024")
            assert result == date(2024, 2, 29)

    def test_invalid_feb_29_raises(self) -> None:
        """Feb 29 in non-leap year raises ValueError."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 3, 1)  # 2025 is not a leap year
            with pytest.raises(ValueError):
                # Without explicit year, dateutil uses current year
                # In 2025 (non-leap year), Feb 29 is invalid
                DateParser.parse_absolute_date("February 29")


class TestParseDateRange:
    """Tests for parse_date_range method."""

    @pytest.fixture
    def mock_today(self) -> date:
        return date(2025, 10, 7)

    def test_between_month_x_and_y(self) -> None:
        """'between November 11 and 13' works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_date_range("between November 11 and 13")
            assert result["is_range"] is True
            assert result["start_date"] == date(2025, 11, 11)
            assert result["end_date"] == date(2025, 11, 13)

    def test_month_x_y_format(self) -> None:
        """'Dec 5-7' works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_date_range("Dec 5-7")
            assert result["is_range"] is True
            assert result["start_date"] == date(2025, 12, 5)
            assert result["end_date"] == date(2025, 12, 7)

    def test_anytime_pattern(self) -> None:
        """'anytime Dec 5-7' works."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_date_range("anytime Dec 5-7")
            assert result["is_range"] is True

    def test_range_too_long(self) -> None:
        """Ranges > 3 days return error."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_date_range("between Nov 10 and 20")
            assert "error" in result

    def test_no_range_pattern(self) -> None:
        """Non-range input returns is_range=False."""
        result = DateParser.parse_date_range("November 15")
        assert result == {"is_range": False}

    def test_smart_year_selection_past_month(self) -> None:
        """Past months bump to next year."""
        with patch("app.ai.utils.date_parser.utc_date") as mock_utc:
            mock_utc.return_value = date(2025, 10, 7)
            result = DateParser.parse_date_range("between Feb 10 and 12")
            assert result["start_date"].year == 2026


class TestAssignRelativeDate:
    """Tests for assign_relative_date method."""

    def test_one_way_assigns_departure(self) -> None:
        """One-way trips assign to departure_date."""
        extracted: dict[str, Any] = {}
        result = DateParser.assign_relative_date(
            extracted,
            date(2025, 12, 15),
            message="next week",
            journey_type="one_way",
        )
        assert result["departure_date"] == date(2025, 12, 15)
        assert "return_date" not in result

    def test_return_trip_assigns_departure_first(self) -> None:
        """Return trips assign to departure_date first."""
        extracted: dict[str, Any] = {}
        result = DateParser.assign_relative_date(
            extracted,
            date(2025, 12, 15),
            message="next week",
            journey_type="return",
        )
        assert result["departure_date"] == date(2025, 12, 15)

    def test_return_trip_assigns_return_when_departure_exists(self) -> None:
        """Return trips assign to return_date when departure exists."""
        extracted: dict[str, Any] = {"departure_date": date(2025, 12, 15)}
        result = DateParser.assign_relative_date(
            extracted,
            date(2025, 12, 29),  # 2 weeks from departure
            message="2 weeks later",
            journey_type="return",
        )
        assert result["departure_date"] == date(2025, 12, 15)
        # Return should be recalculated from departure
        assert result["return_date"] == date(2025, 12, 29)

    def test_return_date_validation(self) -> None:
        """Return date must be after departure."""
        extracted: dict[str, Any] = {"departure_date": date(2025, 12, 15)}
        result = DateParser.assign_relative_date(
            extracted,
            date(2025, 12, 10),  # Before departure
            message="yesterday",
            journey_type="return",
        )
        # Should get default offset since date is before departure
        assert result["return_date"] > result["departure_date"]

    def test_unknown_journey_type(self) -> None:
        """Unknown journey type assigns to departure_date."""
        extracted: dict[str, Any] = {}
        result = DateParser.assign_relative_date(
            extracted, date(2025, 12, 15), message="next week"
        )
        assert result["departure_date"] == date(2025, 12, 15)
