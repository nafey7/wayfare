"""Unified date parsing utilities for AI handlers.

This module consolidates date parsing logic previously duplicated across
flight_field_collector.py and hotel_field_collector.py.
"""

import logging
import re
from datetime import date, timedelta
from typing import Any, ClassVar

from app.domains.common import utc_date

logger = logging.getLogger(__name__)


class DateParser:
    """Unified date parsing for AI handlers.

    Provides static methods for parsing various date formats:
    - Relative time expressions ("tomorrow", "2 weeks later", "following Friday")
    - Absolute dates with smart year selection ("Feb 14", "November 5th")
    - Date ranges ("between Nov 11 and 15", "anytime Dec 5-10")
    """

    # Word-to-number mapping for relative time parsing
    WORD_TO_NUM: ClassVar[dict[str, int]] = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "a": 1,
        "an": 1,
    }

    # Weekday name-to-number mapping
    WEEKDAY_MAP: ClassVar[dict[str, int]] = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    @staticmethod
    def convert_word_to_number(word: str) -> int | None:
        """Convert number words to digits for time expressions.

        Args:
            word: Number word like 'two', 'three', 'a', 'an'

        Returns:
            Integer value or None if not a recognized number word
        """
        return DateParser.WORD_TO_NUM.get(word.lower())

    @staticmethod
    def parse_relative_time(
        message: str,
        reference_date: date | None = None,
        include_weekday_patterns: bool = True,
    ) -> date | None:
        """Parse relative time expressions.

        Supports patterns like:
        - 'tomorrow', 'today', 'tonight'
        - '1 week later', 'two weeks later', 'a week later'
        - 'returning 2 weeks', 'back in two weeks'
        - 'in 3 days', 'after 2 weeks'
        - 'next week', 'next month', 'next weekend'
        - 'following Friday', 'following weekend'
        - Bare weekday names (when include_weekday_patterns=True)

        Args:
            message: The message containing time expression
            reference_date: Base date to calculate from (default: today)
            include_weekday_patterns: Include weekday matching (default: True)

        Returns:
            Parsed date or None if no valid time expression found
        """
        if reference_date is None:
            reference_date = utc_date()
        message_lower = message.lower().strip()

        # Handle simple cases first
        if message_lower == "tomorrow":
            return reference_date + timedelta(days=1)
        if message_lower in ["today", "tonight"]:
            return reference_date

        # Handle relative time patterns with numbers (digits or words) and units
        number_pattern = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an)"
        unit_pattern = r"(day|days|week|weeks|month|months|year|years|night|nights)"

        relative_patterns = [
            # "2 weeks later", "two weeks later", "a week later"
            rf"{number_pattern}\s+{unit_pattern}\s+later",
            # "returning 2 weeks", "returning two weeks" (flight-specific)
            rf"returning?\s+{number_pattern}\s+{unit_pattern}",
            # "back 2 weeks", "back in two weeks"
            rf"back\s+(?:in\s+)?{number_pattern}\s+{unit_pattern}",
            # "in 2 weeks", "in two weeks"
            rf"in\s+{number_pattern}\s+{unit_pattern}",
            # "2 weeks", "two weeks" (when standing alone)
            rf"^{number_pattern}\s+{unit_pattern}$",
            # "after 2 weeks", "after two weeks"
            rf"after\s+{number_pattern}\s+{unit_pattern}",
        ]

        for pattern in relative_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    number_str = match.group(1)
                    unit = match.group(2).lower()

                    # Convert number (digit or word) to int
                    if number_str.isdigit():
                        number = int(number_str)
                    else:
                        converted = DateParser.convert_word_to_number(number_str)
                        if converted is None:
                            continue
                        number = converted

                    # Convert to days
                    if unit in ["day", "days", "night", "nights"]:
                        days = number
                    elif unit in ["week", "weeks"]:
                        days = number * 7
                    elif unit in ["month", "months"]:
                        days = number * 30  # Approximate
                    elif unit in ["year", "years"]:
                        days = number * 365  # Approximate
                    else:
                        continue

                    return reference_date + timedelta(days=days)
                except (ValueError, IndexError):
                    continue

        # Handle "following [weekday]" patterns
        if include_weekday_patterns:
            following_match = re.search(
                r"following\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                message_lower,
            )
            if following_match:
                day_name = following_match.group(1)
                target_weekday = DateParser.WEEKDAY_MAP.get(day_name)

                if target_weekday is not None:
                    current_weekday = reference_date.weekday()
                    days_ahead = target_weekday - current_weekday

                    # "Following" means the NEXT occurrence
                    if days_ahead <= 0:
                        days_ahead += 7

                    return reference_date + timedelta(days=days_ahead)

        # Handle "next weekend" BEFORE "next week" to avoid incorrect matching
        if "next weekend" in message_lower:
            current_weekday = reference_date.weekday()
            days_to_saturday = (5 - current_weekday) % 7
            # If today IS Saturday, go to next Saturday
            if days_to_saturday == 0:
                days_to_saturday = 7
            return reference_date + timedelta(days=days_to_saturday)

        # Handle "next week" patterns
        if "next week" in message_lower:
            next_week_start = reference_date + timedelta(
                days=(7 - reference_date.weekday())
            )
            # Check for specific day: "next week friday", "next week monday"
            if include_weekday_patterns:
                day_match = re.search(
                    r"next week\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                    message_lower,
                )
                if day_match:
                    day_name = day_match.group(1)
                    day_offset = DateParser.WEEKDAY_MAP.get(day_name, 0)
                    return next_week_start + timedelta(days=day_offset)
            # Just "next week" - assume Monday
            return next_week_start

        # Handle "next month"
        if "next month" in message_lower:
            return reference_date + timedelta(days=30)

        # Handle "following weekend" BEFORE "following week"
        if "following weekend" in message_lower:
            current_weekday = reference_date.weekday()
            days_to_saturday = (5 - current_weekday) % 7
            if days_to_saturday == 0:
                return reference_date  # Already Saturday
            return reference_date + timedelta(days=days_to_saturday)

        # Handle "week after" or "following week" - means 7 days later
        if "week after" in message_lower or "following week" in message_lower:
            return reference_date + timedelta(days=7)

        # Handle specific weekday names (this week or next)
        # BUT only if there's no explicit date (e.g., "Monday 26th January" should
        # parse as Jan 26, not "next Monday")
        if include_weekday_patterns:
            # Check for explicit date: day number + month name
            has_explicit_date = bool(
                re.search(
                    r"\b\d{1,2}(?:st|nd|rd|th)?\s+"
                    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
                    message_lower,
                )
                or re.search(
                    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}",
                    message_lower,
                )
            )

            # Only use bare weekday pattern if no explicit date is present
            if not has_explicit_date:
                weekday_match = re.search(
                    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                    message_lower,
                )
                if weekday_match:
                    day_name = weekday_match.group(1)
                    target_weekday = DateParser.WEEKDAY_MAP.get(day_name)

                    if target_weekday is not None:
                        current_weekday = reference_date.weekday()
                        days_ahead = target_weekday - current_weekday

                        # If the day has already passed this week, get next week's
                        if days_ahead <= 0:
                            days_ahead += 7

                        return reference_date + timedelta(days=days_ahead)

        return None

    @staticmethod
    def parse_absolute_date(
        value: str | date,
        check_explicit_year: bool = True,
    ) -> date:
        """Parse absolute date with smart year selection.

        Smart year selection logic:
        - If no year is explicitly provided and parsed date is in the past,
          automatically increment year by 1 to get next occurrence
        - Preserves explicitly provided years
        - Handles relative dates ("tomorrow", "next week") without modification

        Args:
            value: Date string or date object to parse
            check_explicit_year: If True, check for explicit year in input
                                 before applying smart year selection

        Returns:
            Parsed date object with smart year selection applied

        Raises:
            ValueError: If date cannot be parsed

        Examples:
            "Feb 14" (when today is Oct 7, 2025) -> 2026-02-14
            "Nov 15" (when today is Oct 7, 2025) -> 2025-11-15
            "Feb 14 2027" -> 2027-02-14 (explicit year preserved)
        """
        from dateutil import parser

        # If already a date object, return it
        if isinstance(value, date):
            return value

        value_lower = str(value).lower().strip()
        today = utc_date()

        # Handle relative dates
        if value_lower == "today":
            return today
        if value_lower == "tomorrow":
            return today + timedelta(days=1)
        if "next" in value_lower:
            for day_name, day_num in DateParser.WEEKDAY_MAP.items():
                if day_name in value_lower:
                    days_ahead = (day_num - today.weekday() + 7) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    return today + timedelta(days=days_ahead)

        # Handle "in X days" pattern
        days_match = re.search(r"in\s+(\d+)\s+days?", value_lower)
        if days_match:
            return today + timedelta(days=int(days_match.group(1)))

        # Clean up ordinal numbers (5th -> 5, 1st -> 1, etc.)
        cleaned_value = re.sub(
            r"(\d+)(?:st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE
        )

        # Remove "of" if present (e.g., "5th of november" -> "5 november")
        cleaned_value = cleaned_value.replace(" of ", " ")

        # Try standard date parsing
        try:
            parsed = parser.parse(cleaned_value, fuzzy=True)
            parsed_date = parsed.date()

            # Smart year selection
            year_explicitly_provided = False
            if check_explicit_year:
                year_explicitly_provided = bool(re.search(r"\b(19|20)\d{2}\b", value))

            if not year_explicitly_provided and parsed_date < today:
                # No year provided + date is in the past -> use next year
                original_year = parsed_date.year
                try:
                    parsed_date = parsed_date.replace(year=today.year + 1)
                except ValueError:
                    # Handle leap year edge case (Feb 29)
                    parsed_date = parsed_date.replace(year=today.year + 1, day=28)
                logger.info(
                    f"Smart date parsing: '{value}' -> {parsed_date} "
                    f"(auto-incremented year from {original_year} to {today.year + 1})"
                )
            else:
                logger.debug(f"Successfully parsed date '{value}' as {parsed_date}")

            return parsed_date

        except Exception as e:
            logger.error(f"Failed to parse date '{value}': {e}")
            raise ValueError(f"Could not parse date: {value}") from e

    @staticmethod
    def parse_date_range(value: str, max_range_days: int = 2) -> dict[str, Any]:
        """Parse date range expressions (flight-specific).

        Supports patterns like:
        - 'between November 11 and 15'
        - 'anytime between 11 and 15 Oct'
        - 'from 5 to 10 December'
        - 'December 5-10'
        - 'anytime Dec 5-10'

        Args:
            value: Date range expression
            max_range_days: Maximum allowed range (default: 2 = 3 days total)

        Returns:
            Dictionary with keys:
            - start_date, end_date, is_range=True, requires_confirmation=True (success)
            - error (string), suggestion (optional) (failure)
            - is_range=False (no range pattern found)
        """
        from dateutil import parser

        value_lower = str(value).lower().strip()
        today = utc_date()
        current_year = today.year

        # Comprehensive pattern matching for date ranges
        patterns = [
            # "between Month X and Y" variations
            r"between\s+([a-z]+)\s+(\d+)\s+and\s+(\d+)",
            r"anytime\s+between\s+([a-z]+)\s+(\d+)\s+and\s+(\d+)",
            # "between X and Y Month" variations
            r"between\s+(\d+)\s+and\s+(\d+)\s+([a-z]+)",
            r"between\s+(\d+)-(\d+)\s+([a-z]+)",
            # "anytime between X and Y Month" variations
            r"anytime\s+between\s+(\d+)\s+and\s+(\d+)\s+([a-z]+)",
            r"anytime\s+between\s+(\d+)\s*-\s*(\d+)\s+([a-z]+)",
            # "anytime Month X-Y" variations
            r"anytime\s+([a-z]+)\s+(\d+)-(\d+)",
            r"anytime\s+([a-z]+)\s+(\d+)\s*-\s*(\d+)",
            # "from X to Y Month" variations
            r"(?:anytime\s+)?from\s+(\d+)\s+to\s+(\d+)\s+([a-z]+)",
            r"(?:anytime\s+)?from\s+(\d+)-(\d+)\s+([a-z]+)",
            # "X to Y Month" variations
            r"(\d+)\s+to\s+(\d+)\s+([a-z]+)",
            r"(\d+)-(\d+)\s+([a-z]+)",
            # "Month X-Y" variations
            r"([a-z]+)\s+(\d+)-(\d+)",
            r"([a-z]+)\s+(\d+)\s*-\s*(\d+)",
        ]

        between_match = None
        for pattern in patterns:
            between_match = re.search(pattern, value_lower)
            if between_match:
                break

        if between_match:
            groups = between_match.groups()
            if len(groups) == 3:
                # Check if first group is a month (letters) or day (digits)
                if groups[0].isdigit():
                    # Pattern: X-Y Month (start_day, end_day, month)
                    start_day = int(groups[0])
                    end_day = int(groups[1])
                    month_str = groups[2]
                else:
                    # Pattern: Month X-Y (month, start_day, end_day)
                    month_str = groups[0]
                    start_day = int(groups[1])
                    end_day = int(groups[2])
            else:
                # Fallback
                start_day = int(between_match.group(1))
                end_day = int(between_match.group(2))
                month_str = between_match.group(3)

            # Parse month
            try:
                month_date = parser.parse(f"{month_str} 1 {current_year}")
                month = month_date.month
                year = current_year

                # If parsed month is before current month, assume next year
                if month < today.month or (
                    month == today.month and start_day < today.day
                ):
                    year = current_year + 1

                start_date = date(year, month, start_day)
                end_date = date(year, month, end_day)

                # Validate dates
                if start_date >= end_date:
                    return {
                        "error": f"Start date {start_date} must be before end date {end_date}"
                    }

                # Check if date range is too long
                if (end_date - start_date).days > max_range_days:
                    return {
                        "error": f"Date range is {(end_date - start_date).days + 1} days. "
                        f"Maximum allowed is {max_range_days + 1} days.",
                        "suggestion": f"Please narrow down to a {max_range_days + 1}-day window.",
                    }

                return {
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_range": True,
                    "requires_confirmation": True,
                }

            except Exception as e:
                logger.warning(f"Could not parse month '{month_str}': {e}")
                return {"error": f"Could not parse month '{month_str}'"}

        return {"is_range": False}

    @staticmethod
    def assign_relative_date(
        extracted: dict[str, Any],
        relative_date: date,
        message: str = "",
        journey_type: str | None = None,
    ) -> dict[str, Any]:
        """Smart assignment of relative dates based on journey type.

        For round-trip flights, ensures return dates are calculated relative
        to departure date, not from today.

        Args:
            extracted: Current extracted data dictionary
            relative_date: The parsed relative date
            message: Original message for context-aware recalculation
            journey_type: Journey type (one_way, return, round_trip)

        Returns:
            Updated extracted data with date assigned appropriately
        """
        has_departure = "departure_date" in extracted and extracted["departure_date"]
        has_return = "return_date" in extracted and extracted["return_date"]

        # Normalize journey type string
        journey_type_str = None
        if journey_type:
            if hasattr(journey_type, "value"):
                journey_type_str = journey_type.value
            elif hasattr(journey_type, "name"):
                journey_type_str = journey_type.name
            else:
                journey_type_str = str(journey_type).lower()

        # For one-way trips, only assign to departure_date
        if journey_type_str and journey_type_str.lower() in ("one_way", "oneway"):
            if not has_departure:
                extracted["departure_date"] = relative_date

        # For round-trip/return trips
        elif journey_type_str and journey_type_str.lower() in (
            "return",
            "round_trip",
            "roundtrip",
            "round-trip",
        ):
            if not has_departure:
                extracted["departure_date"] = relative_date
            elif not has_return:
                # Have departure, calculate return relative to departure_date
                departure_date = extracted["departure_date"]

                # Recalculate relative date from departure_date
                recalculated_return = DateParser.parse_relative_time(
                    message, reference_date=departure_date
                )

                if recalculated_return:
                    logger.info(
                        f"Return date calculated from departure ({departure_date}): "
                        f"'{message}' -> {recalculated_return}"
                    )
                    extracted["return_date"] = recalculated_return
                elif relative_date > departure_date:
                    # Fallback: use relative_date if after departure
                    extracted["return_date"] = relative_date
                    logger.info(
                        f"Using absolute return date: {relative_date} "
                        f"(after departure {departure_date})"
                    )
                else:
                    # Last resort: default 7-day offset
                    logger.warning(
                        f"Could not parse return date from '{message}'. "
                        f"Using default 7-day offset from departure {departure_date}"
                    )
                    extracted["return_date"] = departure_date + timedelta(days=7)

                # Validate: return must be after departure
                if extracted["return_date"] <= departure_date:
                    logger.error(
                        f"Invalid return date {extracted['return_date']} "
                        f"<= departure {departure_date}. Adding 1 day."
                    )
                    extracted["return_date"] = departure_date + timedelta(days=1)

        # Unknown journey type - default to departure_date
        elif not has_departure:
            extracted["departure_date"] = relative_date

        return extracted
