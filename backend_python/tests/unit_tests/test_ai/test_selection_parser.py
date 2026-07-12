"""Unit tests for SelectionParser utility.

Tests the selection parsing functionality extracted from:
- flight_booking_handler.py
- hotel_booking_handler.py
- enhanced_flight_handler.py
"""

import pytest

from app.ai.utils.selection_parser import (
    SelectionDomain,
    SelectionParser,
    parse_selection,
)


class TestSelectionParserOptionPattern:
    """Test Pattern 1: 'book option 1', 'select option 2'"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("book option 1", 1),
            ("select option 2", 2),
            ("choose option 3", 3),
            ("pick option 4", 4),
            ("take option 5", 5),
            ("Book Option 1", 1),  # Case insensitive
            ("I would like to book option 1 please", 1),
            ("select option 10", 10),  # Double digit
        ],
    )
    def test_option_pattern(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected


class TestSelectionParserOrdinalPattern:
    """Test Pattern 2: 'book the first one', 'take the second'"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("book the first one", 1),
            ("select the second one", 2),
            ("choose the third", 3),
            ("take the fourth option", 4),
            ("want the fifth flight", 5),
            ("I'll book the first", 1),
            ("pick the second", 2),
        ],
    )
    def test_ordinal_words(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("book the 1st one", 1),
            ("select the 2nd", 2),
            ("choose the 3rd option", 3),
            ("take the 4th", 4),
            ("want the 5th", 5),
        ],
    )
    def test_ordinal_abbreviations(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected


class TestSelectionParserActionNumberPattern:
    """Test Pattern 3: 'book 1', 'select 2'"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("book 1", 1),
            ("select 2", 2),
            ("choose 3", 3),
            ("take 4", 4),
            ("want 5", 5),
            ("I'll take 1", 1),
        ],
    )
    def test_action_number(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected


class TestSelectionParserLabelPatternFlight:
    """Test Pattern 4: Label-based selection for flights"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            # Option 1: Best Value
            ("book best value", 1),
            ("select the best option", 1),
            ("choose recommended", 1),
            # Option 2: Cheapest
            ("book cheapest", 2),
            ("select the cheapest one", 2),
            ("want lowest price", 2),
            ("pick budget", 2),
            # Option 3: Most Convenient
            ("book convenient", 3),
            ("select direct flight", 3),
            ("choose fastest", 3),
            ("take nonstop", 3),
            ("want non-stop", 3),
        ],
    )
    def test_flight_labels(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message, SelectionDomain.FLIGHT) == expected


class TestSelectionParserLabelPatternHotel:
    """Test Pattern 4: Label-based selection for hotels"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            # Option 1: Best Value
            ("book best value", 1),
            ("select the best", 1),
            # Option 2: Lowest Price
            ("book cheapest", 2),
            ("select lowest price", 2),
            # Option 3: Highest Rated
            ("book highest rated", 3),
            ("choose top rated", 3),
            # Note: "best rated" and "best reviews" contain "best" which matches option 1 first
            # This is expected behavior - more specific patterns not supported
        ],
    )
    def test_hotel_labels(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message, SelectionDomain.HOTEL) == expected

    def test_ambiguous_patterns_match_first(self) -> None:
        """Verify that ambiguous patterns like 'best rated' match 'best' (option 1) first.

        This is expected behavior - the parser checks patterns in option order,
        so 'best' in option 1 matches before 'best rated' in option 3.
        """
        # "best rated" contains "best" which is in option 1's labels
        assert SelectionParser.parse("select best rated", SelectionDomain.HOTEL) == 1
        # "best reviews" contains "best" which is in option 1's labels
        assert SelectionParser.parse("want best reviews", SelectionDomain.HOTEL) == 1


class TestSelectionParserBareNumber:
    """Test Pattern 5: Just a number by itself"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("1", 1),
            ("2", 2),
            ("3", 3),
            (" 1 ", 1),  # With whitespace
            ("1.", 1),  # Trailing period (bug fix)
            ("2,", 2),  # Trailing comma
            ("3!", 3),  # Trailing exclamation
            ("4?", 4),  # Trailing question mark
        ],
    )
    def test_bare_number(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected


class TestSelectionParserNoMatch:
    """Test messages that should NOT match"""

    @pytest.mark.parametrize(
        "message",
        [
            "hello",
            "what are my options?",
            "show me more",
            "the first one is nice",  # No action word
            "option 1 looks good",  # No action word
            "how much is 1",  # No action word
            "",
            "   ",
        ],
    )
    def test_no_match(self, message: str) -> None:
        assert SelectionParser.parse(message) is None


class TestSelectionParserPriority:
    """Test pattern matching priority"""

    def test_option_pattern_takes_priority(self) -> None:
        """Option pattern should be checked before ordinal"""
        # "book option 1" has both option pattern and "first" could match
        assert SelectionParser.parse("book option 1 the first") == 1

    def test_label_not_matched_without_action(self) -> None:
        """Labels without action words should not match"""
        assert SelectionParser.parse("cheapest is nice") is None
        assert SelectionParser.parse("best value looks good") is None


class TestSelectionParserDomainDifferences:
    """Test domain-specific behavior differences"""

    def test_convenient_only_for_flight(self) -> None:
        """'convenient' should map to option 3 for flights but not hotels"""
        assert SelectionParser.parse("book convenient", SelectionDomain.FLIGHT) == 3
        # For hotels, "convenient" isn't in the label patterns
        assert SelectionParser.parse("book convenient", SelectionDomain.HOTEL) is None

    def test_highest_rated_only_for_hotel(self) -> None:
        """'highest rated' should map to option 3 for hotels but not flights"""
        assert SelectionParser.parse("book highest rated", SelectionDomain.HOTEL) == 3
        # For flights, "highest rated" isn't in the label patterns
        assert (
            SelectionParser.parse("book highest rated", SelectionDomain.FLIGHT) is None
        )


class TestSelectionParserValidation:
    """Test validate_selection helper"""

    def test_valid_selection(self) -> None:
        is_valid, error = SelectionParser.validate_selection(2, max_options=3)
        assert is_valid is True
        assert error is None

    def test_none_selection(self) -> None:
        is_valid, error = SelectionParser.validate_selection(None, max_options=3)
        assert is_valid is False
        assert "Could not parse" in error

    def test_below_min(self) -> None:
        is_valid, error = SelectionParser.validate_selection(
            0, max_options=3, min_options=1
        )
        assert is_valid is False
        assert "at least 1" in error

    def test_above_max(self) -> None:
        is_valid, error = SelectionParser.validate_selection(5, max_options=3)
        assert is_valid is False
        assert "out of range" in error
        assert "5" in error


class TestSelectionParserHelpers:
    """Test helper methods"""

    def test_has_selection_intent_true(self) -> None:
        assert SelectionParser.has_selection_intent("I want to book") is True
        assert SelectionParser.has_selection_intent("select the best") is True
        assert SelectionParser.has_selection_intent("choose one") is True
        assert SelectionParser.has_selection_intent("pick this") is True

    def test_has_selection_intent_false(self) -> None:
        assert SelectionParser.has_selection_intent("show me options") is False
        assert SelectionParser.has_selection_intent("what's available") is False

    def test_extract_all_numbers(self) -> None:
        assert SelectionParser.extract_all_numbers("book options 1 and 3") == [1, 3]
        assert SelectionParser.extract_all_numbers("flight 123 on dec 25") == [123, 25]
        assert SelectionParser.extract_all_numbers("no numbers here") == []


class TestParseSelectionConvenienceFunction:
    """Test the module-level convenience function"""

    def test_with_string_domain(self) -> None:
        assert parse_selection("book option 1", domain="flight") == 1
        assert parse_selection("book option 1", domain="hotel") == 1
        assert parse_selection("book option 1", domain="generic") == 1

    def test_with_enum_domain(self) -> None:
        assert parse_selection("book option 1", domain=SelectionDomain.FLIGHT) == 1

    def test_without_labels(self) -> None:
        """Test include_labels=False skips label patterns"""
        # "book best" would match option 1 via labels
        assert parse_selection("book best", include_labels=True) == 1
        # With labels disabled, it should not match
        assert parse_selection("book best", include_labels=False) is None


class TestSelectionParserExtendedOrdinals:
    """Test extended ordinal support (6th-10th)"""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("book the sixth", 6),
            ("select seventh", 7),
            ("choose eighth", 8),
            ("take ninth", 9),
            ("want tenth", 10),
            ("book the 6th", 6),
            ("select 7th", 7),
            ("choose 8th", 8),
            ("take 9th", 9),
            ("want 10th", 10),
        ],
    )
    def test_extended_ordinals(self, message: str, expected: int) -> None:
        assert SelectionParser.parse(message) == expected
