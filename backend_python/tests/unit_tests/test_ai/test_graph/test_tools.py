"""Unit tests for LangGraph flight agent tools.

Tests the tool functions directly without invoking the full LangGraph agent.
Note: Imports are done inside test methods to avoid circular import issues
with the full app module graph.
"""

import calendar
import json
from datetime import date, datetime, timedelta
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.common import utc_date


async def _invoke_flight_tool(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a ``response_format='content_and_artifact'`` tool and merge.

    Post #1034 the success-path ``content`` carries only ``status/summary/
    instruction`` (LLM-visible); the full payload — ``flights``,
    ``search_params``, ``session_id``, ``multicity_legs[*].flights``,
    ``dates[*].flights`` — lives on ``ToolMessage.artifact``.

    Tests assert on the combined shape for convenience, so we invoke via a
    ToolCall (which returns a ``ToolMessage`` with both attributes) and
    merge artifact keys onto content (artifact wins on overlap so callers
    see the richer values).
    """
    tool_call = {"name": tool.name, "args": args, "id": "t1", "type": "tool_call"}
    msg = await tool.ainvoke(tool_call)
    content = msg.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            content = {"_raw": content}
    if not isinstance(content, dict):
        return {"_raw": content}
    merged: dict[str, Any] = dict(content)
    artifact = getattr(msg, "artifact", None)
    if isinstance(artifact, dict):
        for k, v in artifact.items():
            # Artifact wins so callers see search_params/flights/session_id/
            # multicity_legs/dates even when content carries a slim copy.
            merged[k] = v
    return merged


def _target_month(months_ahead: int) -> tuple[int, int]:
    """Return (year, month) for a calendar month `months_ahead` from today (UTC)."""
    today = utc_date()
    month = today.month + months_ahead
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return year, month


def _last_weekend_of_future_month(months_ahead: int = 1) -> tuple[str, str]:
    """Return (friday_iso, sunday_iso) of the last weekend in a future month.

    Computes 'last weekend' as the last Friday–Sunday span of the month that is
    `months_ahead` calendar months from today, ensuring dates are always in the future
    so the parse_dates tool does not auto-advance them to the following year.
    """
    year, month = _target_month(months_ahead)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    # Find last Sunday of the month (weekday 6 = Sunday)
    days_since_sunday = (last.weekday() + 1) % 7
    last_sunday = last - timedelta(days=days_since_sunday)
    last_friday = last_sunday - timedelta(days=2)
    return last_friday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")


def _first_weekend_of_future_month(months_ahead: int = 1) -> tuple[str, str]:
    """Return (friday_iso, sunday_iso) of the first weekend in a future month.

    Mirror of `_last_weekend_of_future_month` for tests that assert the
    first-weekend parse path; uses dynamic dates so the test does not break
    once the wall clock crosses the previously-hardcoded reference date.
    """
    year, month = _target_month(months_ahead)
    first = date(year, month, 1)
    # Find first Friday of the month (weekday 4 = Friday)
    days_until_friday = (4 - first.weekday()) % 7
    first_friday = first + timedelta(days=days_until_friday)
    first_sunday = first_friday + timedelta(days=2)
    return first_friday.strftime("%Y-%m-%d"), first_sunday.strftime("%Y-%m-%d")


def _future_month_range(
    months_ahead: int, start_day: int, end_day: int
) -> tuple[str, str]:
    """Return (departure_iso, return_iso) for a same-month date range in a future month.

    Used by tests that assert exact date round-trips through `parse_dates` with a
    mocked LLM. Dynamic dates are required because `parse_dates` post-processing
    rolls past dates forward, breaking any hardcoded date once the wall clock
    crosses it.
    """
    assert start_day <= end_day, (
        f"start_day ({start_day}) must be <= end_day ({end_day})"
    )
    year, month = _target_month(months_ahead)
    return (
        date(year, month, start_day).strftime("%Y-%m-%d"),
        date(year, month, end_day).strftime("%Y-%m-%d"),
    )


def _mock_revalidate_available() -> AsyncMock:
    """Return an async revalidation mock that keeps all fares available."""
    return AsyncMock(return_value=MagicMock(is_fare_available=True))


def _mock_revalidate_unavailable() -> AsyncMock:
    """Return an async revalidation mock that marks all fares unavailable."""
    return AsyncMock(return_value=MagicMock(is_fare_available=False))


class TestParseDatesTool:
    """Tests for the parse_dates tool."""

    @pytest.mark.asyncio
    async def test_parse_relative_date_tomorrow(self) -> None:
        """Test parsing 'tomorrow'."""
        from app.ai.graph.tools.dates import parse_dates

        expected = (utc_date() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Mock the LLM call to avoid needing API keys in CI
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": expected,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "tomorrow",
            }

            result = await parse_dates.ainvoke({"text": "tomorrow"})

            assert "departure_date" in result
            assert result["departure_date"] == expected
            assert result["return_date"] is None
            assert result["is_range"] is False

    @pytest.mark.asyncio
    async def test_parse_relative_date_next_week(self) -> None:
        """Test parsing 'next week'."""
        from app.ai.graph.tools.dates import parse_dates

        expected = (utc_date() + timedelta(days=7)).strftime("%Y-%m-%d")

        # Mock the LLM call to avoid needing API keys in CI
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": expected,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "next week",
            }

            result = await parse_dates.ainvoke({"text": "next week"})

            assert "departure_date" in result
            # next week should be approximately 7 days from now
            dep_date = date.fromisoformat(result["departure_date"])
            assert dep_date >= utc_date()

    @pytest.mark.asyncio
    async def test_parse_date_range(self) -> None:
        """Test parsing date range like 'Dec 15-17' (3 days max)."""
        from app.ai.graph.tools.dates import parse_dates

        # Mock the LLM call to avoid needing API keys in CI
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": "2026-12-15",
                "return_date": "2026-12-17",
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "December 15-17",
            }

            result = await parse_dates.ainvoke({"text": "December 15-17"})

            assert "departure_date" in result
            assert (
                result.get("is_range") is True or result.get("return_date") is not None
            )

    @pytest.mark.asyncio
    async def test_parse_absolute_date(self) -> None:
        """Test parsing absolute date like 'June 15'."""
        from app.ai.graph.tools.dates import parse_dates

        # Use a future date to avoid deterministic past-date validation
        future_date = (utc_date() + timedelta(days=90)).strftime("%Y-%m-%d")

        # Mock the LLM call to avoid needing API keys in CI
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": future_date,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "June 15",
            }

            result = await parse_dates.ainvoke({"text": "June 15"})

            assert "departure_date" in result
            assert result["departure_date"] == future_date

    @pytest.mark.asyncio
    async def test_parse_invalid_date_returns_error(self) -> None:
        """Test that unparseable text returns an error."""
        from app.ai.graph.tools.dates import parse_dates

        # Mock the LLM call to avoid needing API keys in CI
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": "The date expression 'gibberish xyz' is unparseable.",
                "parsed_from": "gibberish xyz",
            }

            result = await parse_dates.ainvoke({"text": "gibberish xyz"})

            assert "error" in result
            assert result["error"] is not None
            assert (
                "unparseable" in result["error"].lower()
                or "could not parse" in result["error"].lower()
            )

    @pytest.mark.asyncio
    async def test_parse_dates_ambiguous_relative_asks_confirmation(self) -> None:
        """Ambiguous relative expressions (e.g. 'next weekend') should trigger the
        _AMBIGUOUS_RELATIVE_PATTERNS branch and return a confirmation instruction.

        Mocks at the LLM level so _parse_dates_with_llm runs its real instruction
        logic, exercising dates.py:272-281.
        """
        from langchain_core.runnables import RunnableLambda

        from app.ai.graph.tools.dates import parse_dates

        mock_llm_result = MagicMock()
        # Use dates far enough in the future so _validate_parsed_dates
        # doesn't reject them as past dates.
        mock_llm_result.model_dump.return_value = {
            "departure_date": "2026-12-19",
            "return_date": "2026-12-20",
            "is_range": True,
            "trip_duration_days": None,
            "error": None,
        }
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _: mock_llm_result
        )

        with patch("app.ai.graph.llm_factory.create_llm", return_value=mock_llm):
            result = await parse_dates.ainvoke({"text": "next weekend"})

        assert "instruction" in result
        assert "Dates parsed successfully" not in result["instruction"]
        assert "does that work" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_parse_dates_departure_only_asks_trip_type(self) -> None:
        """When only a departure date is parsed, the departure-only branch should
        fire and ask one-way or round-trip.

        Mocks at the LLM level so _parse_dates_with_llm runs its real instruction
        logic, exercising dates.py:282-288.
        """
        from langchain_core.runnables import RunnableLambda

        from app.ai.graph.tools.dates import parse_dates

        future = (utc_date() + timedelta(days=30)).strftime("%Y-%m-%d")

        mock_llm_result = MagicMock()
        mock_llm_result.model_dump.return_value = {
            "departure_date": future,
            "return_date": None,
            "is_range": False,
            "trip_duration_days": None,
            "error": None,
        }
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _: mock_llm_result
        )

        with patch("app.ai.graph.llm_factory.create_llm", return_value=mock_llm):
            result = await parse_dates.ainvoke({"text": "June 1"})

        assert "instruction" in result
        instr = result["instruction"].lower()
        assert "one-way" in instr or "round-trip" in instr or "departure" in instr

    @pytest.mark.asyncio
    async def test_no_date_content_returns_error(self) -> None:
        """Text with no date-like tokens should not reach the LLM."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        result = await _parse_dates_with_llm("I want to visit Beijing and Shanghai")
        assert result["error"] == "no_date_found"
        assert result["departure_date"] is None

    @pytest.mark.asyncio
    async def test_date_hint_allows_holidays(self) -> None:
        """Holiday names like 'during Eid' should pass the guard."""
        from app.ai.graph.tools.dates import _DATE_HINT_PATTERN

        for text in ("during Eid", "for Ramadan", "around Diwali", "Chinese New Year"):
            assert _DATE_HINT_PATTERN.search(text), f"Expected match for '{text}'"

    @pytest.mark.asyncio
    async def test_date_hint_allows_full_month_names(self) -> None:
        """Full month names like 'June' should pass the guard (not just 'jun')."""
        from app.ai.graph.tools.dates import _DATE_HINT_PATTERN

        for text in ("anytime in June", "sometime in May", "flights in December"):
            assert _DATE_HINT_PATTERN.search(text), f"Expected match for '{text}'"

    @pytest.mark.asyncio
    async def test_date_hint_allows_flexibility_keywords(self) -> None:
        """Flexibility signals like 'anytime', 'flexible', 'any time' should pass."""
        from app.ai.graph.tools.dates import _DATE_HINT_PATTERN

        for text in (
            "anytime",
            "any time",
            "whenever is cheapest",
            "flexible dates",
            "sometime",
        ):
            assert _DATE_HINT_PATTERN.search(text), f"Expected match for '{text}'"


class TestParseDatesDurationOnly:
    """Tests for duration-only detection — no departure date should be picked."""

    def test_duration_only_5_days(self) -> None:
        """'5 days' → departure_date=None, trip_duration_days=5."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("5 days")
        assert _extract_duration_days("5 days") == 5

    def test_duration_only_a_week(self) -> None:
        """'a week' → departure_date=None, trip_duration_days=7."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("a week")
        assert _extract_duration_days("a week") == 7

    def test_duration_only_with_trip_word(self) -> None:
        """'3 day trip' → departure_date=None, trip_duration_days=3."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("3 day trip")
        assert _extract_duration_days("3 day trip") == 3

    def test_duration_only_word_numbers(self) -> None:
        """'two weeks' → trip_duration_days=14."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("two weeks")
        assert _extract_duration_days("two weeks") == 14

    def test_duration_only_fortnight(self) -> None:
        """'a fortnight' → trip_duration_days=14."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("a fortnight")
        assert _extract_duration_days("a fortnight") == 14

    def test_duration_with_date_not_blocked(self) -> None:
        """'5 days starting next Monday' should NOT match duration-only pattern."""
        from app.ai.graph.tools.dates import _DURATION_ONLY_PATTERN

        assert not _DURATION_ONLY_PATTERN.match("5 days starting next Monday")
        assert not _DURATION_ONLY_PATTERN.match("next Friday for 3 days")
        assert not _DURATION_ONLY_PATTERN.match("May 10 for a week")

    def test_duration_only_nights(self) -> None:
        """'3 nights' → trip_duration_days=3."""
        from app.ai.graph.tools.dates import (
            _DURATION_ONLY_PATTERN,
            _extract_duration_days,
        )

        assert _DURATION_ONLY_PATTERN.match("3 nights")
        assert _extract_duration_days("3 nights") == 3

    def test_duration_only_vacation(self) -> None:
        """'5 day vacation' → matches."""
        from app.ai.graph.tools.dates import _DURATION_ONLY_PATTERN

        assert _DURATION_ONLY_PATTERN.match("5 day vacation")
        assert _DURATION_ONLY_PATTERN.match("10 day holiday")
        assert _DURATION_ONLY_PATTERN.match("3 night getaway")

    @pytest.mark.asyncio
    async def test_parse_dates_duration_only_returns_no_departure(self) -> None:
        """parse_dates('5 days') should return departure_date=None via _parse_dates_with_llm."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        result = await _parse_dates_with_llm("5 days", reference_date="2026-05-01")
        assert result["departure_date"] is None
        assert result["trip_duration_days"] == 5
        assert "departure date" in result["instruction"].lower()


class TestParseDatesBroaderDurationOnly:
    """Tests for broader duration-without-date detection in full sentences."""

    @pytest.mark.asyncio
    async def test_4_day_trip_to_rome(self) -> None:
        """'4-day trip to Rome' has duration but no date anchor → duration-only."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        result = await _parse_dates_with_llm(
            "4-day trip to Rome", reference_date="2026-05-01"
        )
        assert result["departure_date"] is None
        assert result["trip_duration_days"] == 4
        assert "departure date" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_a_week_vacation_to_tokyo(self) -> None:
        """'a week vacation to Tokyo' → duration-only."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        result = await _parse_dates_with_llm(
            "a week vacation to Tokyo", reference_date="2026-05-01"
        )
        assert result["departure_date"] is None
        assert result["trip_duration_days"] == 7

    @pytest.mark.asyncio
    async def test_5_days_starting_next_monday_not_blocked(self) -> None:
        """'5 days starting next Monday' has a date anchor → NOT blocked."""
        from app.ai.graph.tools.dates import (
            _HAS_DURATION,
            _HAS_EXPLICIT_DATE_ANCHOR,
        )

        text = "5 days starting next Monday"
        assert _HAS_DURATION.search(text)
        assert _HAS_EXPLICIT_DATE_ANCHOR.search(text)

    @pytest.mark.asyncio
    async def test_3_day_trip_from_may_10(self) -> None:
        """'3-day trip from May 10' has month name anchor → NOT blocked."""
        from app.ai.graph.tools.dates import (
            _HAS_DURATION,
            _HAS_EXPLICIT_DATE_ANCHOR,
        )

        text = "3-day trip from May 10"
        assert _HAS_DURATION.search(text)
        assert _HAS_EXPLICIT_DATE_ANCHOR.search(text)

    def test_has_duration_pattern_matches(self) -> None:
        """_HAS_DURATION matches duration mentions in various formats."""
        from app.ai.graph.tools.dates import _HAS_DURATION

        assert _HAS_DURATION.search("4-day trip to Rome")
        assert _HAS_DURATION.search("a week vacation to Tokyo")
        assert _HAS_DURATION.search("Plan a 5 day holiday")
        assert _HAS_DURATION.search("two weeks in Barcelona")

    def test_has_duration_no_match(self) -> None:
        """_HAS_DURATION does NOT match text with no duration."""
        from app.ai.graph.tools.dates import _HAS_DURATION

        assert not _HAS_DURATION.search("trip to Rome")
        assert not _HAS_DURATION.search("visit Tokyo next Friday")

    @pytest.mark.parametrize(
        "text",
        [
            # Reproduces the staging bug from issue #1105 — these *are* date
            # anchors but used to be classified as duration-only.
            "departure 30 days from now",
            "30 days from now",
            "2 weeks from now",
            "a month from today",
            "three days from tomorrow",
            "Plan a 7 days trip starting 30 days from now",
            "Going on a trip 2 weeks from today",
        ],
    )
    def test_n_units_from_now_today_tomorrow_recognized_as_anchor(
        self, text: str
    ) -> None:
        """Regression for #1105 — 'N days from now/today/tomorrow' is a date
        anchor (sets departure = reference + offset), not just a duration."""
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        assert _HAS_EXPLICIT_DATE_ANCHOR.search(text), (
            f"expected {text!r} to match the date-anchor regex"
        )

    @pytest.mark.parametrize(
        "text",
        [
            # Pure duration mentions — must NOT match the anchor regex,
            # otherwise the supervisor's duration-without-date guard would
            # never fire for legitimate ambiguous cases.
            "5 days",
            "a week",
            "two weeks",
            "10-day vacation",
            "Plan a 7-day trip to Tokyo",
            "I want a 3 day getaway",
        ],
    )
    def test_pure_duration_still_not_an_anchor(self, text: str) -> None:
        """Negative test: bare durations without 'from now/today/tomorrow'
        or other anchor cues must still NOT match the anchor regex."""
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        assert not _HAS_EXPLICIT_DATE_ANCHOR.search(text), (
            f"expected {text!r} to NOT match the date-anchor regex"
        )


class TestParseDatesAbbreviatedRanges:
    """Tests for abbreviated date range parsing (e.g. 'from May 20 to 25')."""

    @pytest.mark.asyncio
    async def test_parse_abbreviated_range_mid_month(self) -> None:
        """Same-month range mid-month (e.g. 'from 20 to 25') → both dates preserved."""
        from app.ai.graph.tools.dates import parse_dates

        dep, ret = _future_month_range(months_ahead=2, start_day=20, end_day=25)
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "from 20 to 25",
            }
            result = await parse_dates.ainvoke({"text": "from 20 to 25"})

        assert result["departure_date"] == dep
        assert result["return_date"] == ret
        assert result["is_range"] is True

    @pytest.mark.asyncio
    async def test_parse_abbreviated_range_start_of_month(self) -> None:
        """Same-month range at start of month (e.g. '1-7') → both dates preserved."""
        from app.ai.graph.tools.dates import parse_dates

        dep, ret = _future_month_range(months_ahead=3, start_day=1, end_day=7)
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "1-7",
            }
            result = await parse_dates.ainvoke({"text": "1-7"})

        assert result["departure_date"] == dep
        assert result["return_date"] == ret
        assert result["is_range"] is True

    @pytest.mark.asyncio
    async def test_parse_abbreviated_range_early_month(self) -> None:
        """Same-month range early in month (e.g. 'from 3 to 10') → both dates preserved."""
        from app.ai.graph.tools.dates import parse_dates

        dep, ret = _future_month_range(months_ahead=4, start_day=3, end_day=10)
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "from 3 to 10",
            }
            result = await parse_dates.ainvoke({"text": "from 3 to 10"})

        assert result["departure_date"] == dep
        assert result["return_date"] == ret


class TestParseDatesWeekendReferences:
    """Tests for weekend reference date parsing."""

    @pytest.mark.asyncio
    async def test_parse_last_weekend_of_month(self) -> None:
        """'last weekend of this month' → correct Fri-Sun dates."""
        from app.ai.graph.tools.dates import parse_dates

        friday, sunday = _last_weekend_of_future_month(months_ahead=1)

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": friday,
                "return_date": sunday,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "last weekend of this month",
            }
            result = await parse_dates.ainvoke({"text": "last weekend of this month"})

        assert result["departure_date"] == friday
        assert result["return_date"] == sunday
        assert result["is_range"] is True

    @pytest.mark.asyncio
    async def test_parse_first_weekend_of_month(self) -> None:
        """First weekend of a future month → correct Fri-Sun dates."""
        from app.ai.graph.tools.dates import parse_dates

        friday, sunday = _first_weekend_of_future_month(months_ahead=1)

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": friday,
                "return_date": sunday,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "first weekend of next month",
            }
            result = await parse_dates.ainvoke({"text": "first weekend of next month"})

        assert result["departure_date"] == friday
        assert result["return_date"] == sunday
        assert result["is_range"] is True

    @pytest.mark.asyncio
    async def test_parse_next_weekend(self) -> None:
        """'next weekend' → coming Sat-Sun, triggers confirmation instruction."""
        from langchain_core.runnables import RunnableLambda

        from app.ai.graph.tools.dates import parse_dates

        future_sat = utc_date() + timedelta(
            days=(5 - utc_date().weekday() + 7) % 7 or 7
        )
        future_sun = future_sat + timedelta(days=1)

        mock_llm_result = MagicMock()
        mock_llm_result.model_dump.return_value = {
            "departure_date": future_sat.strftime("%Y-%m-%d"),
            "return_date": future_sun.strftime("%Y-%m-%d"),
            "is_range": True,
            "trip_duration_days": None,
            "error": None,
        }
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _: mock_llm_result
        )

        with patch("app.ai.graph.llm_factory.create_llm", return_value=mock_llm):
            result = await parse_dates.ainvoke({"text": "next weekend"})

        assert result["departure_date"] == future_sat.strftime("%Y-%m-%d")
        assert result["return_date"] == future_sun.strftime("%Y-%m-%d")
        assert result["is_range"] is True
        # Should trigger ambiguous confirmation
        assert (
            "confirm" in result["instruction"].lower()
            or "does that work" in result["instruction"].lower()
        )


class TestResolveAirportTool:
    """Tests for the resolve_airport tool."""

    @pytest.mark.asyncio
    async def test_resolve_iata_code(self) -> None:
        """Test resolving a valid IATA code."""
        from app.ai.graph.tools.airport import resolve_airport
        from app.core.config import settings

        # Use mwgg + mocked service (when FlightLogic airports is on, mocks are bypassed).
        with (
            patch.object(
                settings,
                "VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS",
                False,
            ),
            patch("app.domains.airport.get_airport_service") as mock_get,
        ):
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "resolved"
            mock_airport = MagicMock()
            mock_airport.iata = "LHR"
            mock_airport.name = "London Heathrow"
            mock_airport.city = "London"
            mock_airport.country = "United Kingdom"
            mock_result.airport = mock_airport
            mock_result.needs_airport_preference = False
            mock_result.all_airports = None

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await resolve_airport.ainvoke({"query": "LHR"})

            assert result["status"] == "resolved"
            assert result["iata"] == "LHR"
            assert result["name"] == "London Heathrow"
            assert result["city"] == "London"

    @pytest.mark.asyncio
    async def test_resolve_needs_disambiguation(self) -> None:
        """Test disambiguation when multiple airports match."""
        from app.ai.graph.tools.airport import resolve_airport
        from app.core.config import settings

        with (
            patch.object(
                settings,
                "VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS",
                False,
            ),
            patch("app.domains.airport.get_airport_service") as mock_get,
        ):
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "needs_disambiguation"
            mock_result.disambiguation_type = MagicMock(value="multi_airport_city")
            mock_result.suggested_prompt = "Which London airport?"
            mock_result.options = [
                MagicMock(
                    display_name="London Heathrow",
                    airports=[MagicMock(iata="LHR")],
                ),
                MagicMock(
                    display_name="London Gatwick",
                    airports=[MagicMock(iata="LGW")],
                ),
            ]

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await resolve_airport.ainvoke({"query": "London"})

            assert result["status"] == "needs_disambiguation"
            assert result["type"] == "multi_airport_city"
            assert "instruction" in result
            assert len(result["options"]) == 2

    @pytest.mark.asyncio
    async def test_resolve_not_found(self) -> None:
        """Test when no airport is found."""
        from app.ai.graph.tools.airport import resolve_airport
        from app.core.config import settings

        with (
            patch.object(
                settings,
                "VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS",
                False,
            ),
            patch("app.domains.airport.get_airport_service") as mock_get,
        ):
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "not_found"

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await resolve_airport.ainvoke({"query": "xyznotreal"})

            assert result["status"] == "not_found"
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_rejects_bare_digit(self) -> None:
        """Bare digits like '2' are too short to be locations."""
        from app.ai.graph.tools.airport import resolve_airport

        result = await resolve_airport.ainvoke({"query": "2"})
        assert result["status"] == "not_found"
        assert "not a valid location" in result["instruction"]

    @pytest.mark.asyncio
    async def test_rejects_passenger_count_pattern(self) -> None:
        """'1adult', '3adults' etc. are passenger counts, not locations."""
        from app.ai.graph.tools.airport import resolve_airport

        for query in ("1adult", "3adults", "2children"):
            result = await resolve_airport.ainvoke({"query": query})
            assert result["status"] == "not_found", f"Expected not_found for '{query}'"
            assert "passenger count" in result["instruction"]

    @pytest.mark.asyncio
    async def test_rejects_short_query(self) -> None:
        """Single-character or empty queries are rejected."""
        from app.ai.graph.tools.airport import resolve_airport

        result = await resolve_airport.ainvoke({"query": "X"})
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_mwgg_exclude_iatas_filters_nearby(self) -> None:
        """exclude_iatas removes matching airports from nearby fallback list."""
        from app.ai.graph.tools.airport import _resolve_via_mwgg

        with patch("app.domains.airport.get_airport_service") as mock_get:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "resolved"
            mock_result.is_nearby_fallback = True
            mock_airport = MagicMock(
                iata="AMS",
                name="Amsterdam Schiphol",
                city="Amsterdam",
                country="Netherlands",
            )
            mock_result.airport = mock_airport
            nearby_1 = MagicMock(
                iata="AMS",
                name="Amsterdam Schiphol",
                city="Amsterdam",
                country="Netherlands",
            )
            nearby_2 = MagicMock(
                iata="RTM",
                name="Rotterdam The Hague",
                city="Rotterdam",
                country="Netherlands",
            )
            mock_result.all_airports = [nearby_1, nearby_2]

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await _resolve_via_mwgg("Utrecht", exclude_iatas={"AMS"})

            # After excluding AMS only RTM remains — single nearby airport
            # auto-resolves to "resolved" (issue #814).
            assert result["status"] == "resolved"
            assert result["iata"] == "RTM"

    @pytest.mark.asyncio
    async def test_mwgg_multiple_nearby_airports_returns_no_own_airport(self) -> None:
        """Two+ nearby airports return no_own_airport so user can choose."""
        from app.ai.graph.tools.airport import _resolve_via_mwgg

        with patch("app.domains.airport.get_airport_service") as mock_get:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "resolved"
            mock_result.is_nearby_fallback = True
            mock_result.airport = MagicMock(iata="AMS")
            nearby_1 = MagicMock(
                iata="AMS",
                name="Amsterdam Schiphol",
                city="Amsterdam",
                country="Netherlands",
            )
            nearby_2 = MagicMock(
                iata="RTM",
                name="Rotterdam The Hague",
                city="Rotterdam",
                country="Netherlands",
            )
            mock_result.all_airports = [nearby_1, nearby_2]

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await _resolve_via_mwgg("Utrecht")

            assert result["status"] == "no_own_airport"
            assert len(result["nearby_airports"]) == 2

    @pytest.mark.asyncio
    async def test_mwgg_all_nearby_filtered_returns_not_found(self) -> None:
        """When exclude_iatas removes all nearby airports, return not_found."""
        from app.ai.graph.tools.airport import _resolve_via_mwgg

        with patch("app.domains.airport.get_airport_service") as mock_get:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "resolved"
            mock_result.is_nearby_fallback = True
            mock_result.airport = MagicMock(iata="AMS")
            nearby_1 = MagicMock(
                iata="AMS",
                name="Amsterdam Schiphol",
                city="Amsterdam",
                country="Netherlands",
            )
            mock_result.all_airports = [nearby_1]

            mock_service.resolve = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_service

            result = await _resolve_via_mwgg("Utrecht", exclude_iatas={"AMS"})

            assert result["status"] == "not_found"
            assert "already in use" in result["instruction"]

    @pytest.mark.asyncio
    async def test_flightlogic_exclude_iatas_returns_not_found(self) -> None:
        """FlightLogic path returns not_found when resolved IATA is in exclude set."""
        from app.ai.graph.tools.airport import _resolve_via_flightlogic

        with patch("app.domains.flight.service.FlightService") as MockFS:
            mock_service = MockFS.return_value
            mock_service.resolve_airport = AsyncMock(return_value="LHR")

            result = await _resolve_via_flightlogic("London", exclude_iatas={"LHR"})

            assert result["status"] == "not_found"
            assert "already used" in result["instruction"]


class TestSearchFlightsTool:
    """Tests for the search_flights tool."""

    @pytest.mark.asyncio
    async def test_search_flights_invalid_iata(self) -> None:
        """Test that invalid IATA codes return error."""
        from app.ai.graph.tools.flights import search_flights

        # Invalid origin (not 3 chars)
        result = await search_flights.ainvoke(
            {
                "origin": "LO",  # Invalid - only 2 chars
                "destination": "CDG",
                "departure_date": "2025-01-15",
                "adults": 1,
                "trip_type": "one-way",
            }
        )

        assert "error" in result
        assert "IATA" in result["error"]

    @pytest.mark.asyncio
    async def test_search_flights_invalid_date_format(self) -> None:
        """Test that invalid date format returns error."""
        from app.ai.graph.tools.flights import search_flights

        result = await search_flights.ainvoke(
            {
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "15-01-2025",  # Wrong format
                "adults": 1,
                "trip_type": "one-way",
            }
        )

        assert "error" in result
        assert "date" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_search_flights_invalid_trip_type(self) -> None:
        """Test that an unrecognised trip_type value returns an error."""
        from app.ai.graph.tools.flights import search_flights

        result = await search_flights.ainvoke(
            {
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "2026-06-01",
                "adults": 1,
                "trip_type": "maybe",
            }
        )

        assert result["status"] == "error"
        assert "one-way" in result["error"] or "round-trip" in result["error"]

    @pytest.mark.asyncio
    async def test_search_flights_round_trip_missing_return_date(self) -> None:
        """Test that round-trip without return_date returns an error."""
        from app.ai.graph.tools.flights import search_flights

        result = await search_flights.ainvoke(
            {
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "2026-06-01",
                "adults": 1,
                "trip_type": "round-trip",
            }
        )

        assert result["status"] == "error"
        assert "return_date" in result["error"]

    @pytest.mark.asyncio
    async def test_search_flights_success(self) -> None:
        """Test successful flight search with mocked API."""
        from app.ai.graph.tools.flights import search_flights
        from app.core.config import settings

        # Mock the FlightService
        with (
            patch("app.domains.flight.service.FlightService") as mock_service_class,
            patch.object(settings, "FLIGHT_SEARCH_CONCURRENT_REVALIDATION", True),
        ):
            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create mock itinerary using the current FareItinerary shape.
            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                airline_name="British Airways", iata_code="BA"
            )
            mock_segment.operating_flight_number = MagicMock(formatted_number="BA123")
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "10:00" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "12:30" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=150)
            mock_segment.departure_airport = MagicMock(iata_code="LHR")
            mock_segment.arrival_airport = MagicMock(iata_code="CDG")

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0

            mock_itinerary = MagicMock()
            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "LHRCDG_SUCCESS"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = 250.0
            mock_total_fare.currency = "GBP"
            mock_fare_totals.total_fare = mock_total_fare
            mock_pricing.fare_totals = mock_fare_totals
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.errors = []
            # Non-empty session enables per-category revalidation (8→4→3) in the tool.
            mock_response.session_id = "fl-test-session-revalidate"

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-15",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            # Issue #1034: categories are gone — `flights` is a flat
            # best-value-sorted list on the artifact. session_id is on the
            # artifact too.
            assert result["status"] == "success"
            assert "summary" in result
            assert result["summary"]["total_found"] >= 1
            assert isinstance(result.get("flights"), list)
            assert result.get("session_id") == "fl-test-session-revalidate"
            mock_service.revalidate_fare.assert_awaited()

    @pytest.mark.asyncio
    async def test_search_flights_multi_airport_city_names(self) -> None:
        """Test multi-airport search when user specifies city names (not airport codes)."""
        from app.ai.graph.tools.flights import search_flights

        # Mock the FlightService
        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create multiple mock itineraries for different airport combinations
            mock_itineraries = []
            airports = [
                ("LHR", "CDG", "250.00"),  # London Heathrow -> Paris CDG
                ("LGW", "CDG", "180.00"),  # London Gatwick -> Paris CDG (cheaper)
                ("STN", "ORY", "220.00"),  # London Stansted -> Paris Orly
            ]

            for origin, dest, price in airports:
                mock_segment = MagicMock()
                mock_segment.operating_airline = MagicMock(
                    name="British Airways", iata_code="BA"
                )
                mock_segment.operating_flight_number = f"{origin}{dest}123"
                mock_segment.departure_datetime = MagicMock()
                mock_segment.departure_datetime.strftime = lambda fmt: (
                    "2026-01-17T10:00:00" if ":" in fmt else "2026-01-17"
                )
                mock_segment.arrival_datetime = MagicMock()
                mock_segment.arrival_datetime.strftime = lambda fmt: (
                    "2026-01-17T12:00:00" if ":" in fmt else "2026-01-17"
                )
                mock_segment.flight_duration = MagicMock(total_minutes=120)

                mock_leg = MagicMock()
                mock_leg.flight_segments = [mock_segment]
                mock_leg.total_stops = 0
                mock_leg.total_time_seconds = 7200  # 2 hours

                # Use correct pricing structure (FlightService sets these fields)
                original_price = float(price)
                # Platform fee: price_with_fee = original_price / 0.95
                price_with_fee = round(original_price / 0.95, 2)

                mock_pricing = MagicMock()
                mock_pricing.fare_source_code = f"{origin}{dest}_FARE"
                mock_fare_totals = MagicMock()
                # total_fare = price WITH platform fee
                mock_total_fare = MagicMock()
                mock_total_fare.amount = price_with_fee
                mock_total_fare.currency = "EUR"
                mock_fare_totals.total_fare = mock_total_fare
                # original_total_fare = price WITHOUT platform fee
                mock_original_fare = MagicMock()
                mock_original_fare.amount = original_price
                mock_original_fare.currency = "EUR"
                mock_fare_totals.original_total_fare = mock_original_fare
                # platform_fee_percentage = 5.0
                mock_fare_totals.platform_fee_percentage = 5.0
                mock_pricing.fare_totals = mock_fare_totals

                mock_itinerary = MagicMock()
                mock_itinerary.pricing = mock_pricing
                mock_itinerary.flight_legs = [mock_leg]
                mock_itinerary.sequence_number = len(mock_itineraries) + 1

                mock_itineraries.append(mock_itinerary)

            mock_response.fare_itineraries = mock_itineraries
            mock_response.session_id = "MOCK_SESSION_123"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            # Call with city flags set to True
            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-17",
                    "adults": 1,
                    "trip_type": "one-way",
                    "origin_is_city": True,
                    "destination_is_city": True,
                },
            )

            # Verify the service was called
            mock_service.search_flights.assert_called_once()
            call_args = mock_service.search_flights.call_args[0][0]

            # Verify city_wise_search flags were passed correctly
            assert call_args.city_wise_search_origin is True
            assert call_args.city_wise_search_destination is True

            # Verify results — flat best-value-sorted list (#1034).
            assert result["status"] == "success"
            assert "summary" in result
            assert "flights" in result
            assert result["summary"]["total_found"] == 3

            # Cheapest flight is from LGW (180 EUR original, 189.47 with platform fee).
            # With the flat list sorted by best_value, the LGW fare is no longer
            # guaranteed at index 0 — look it up by price.
            prices = [f["price"] for f in result["flights"]]
            assert 189.47 in prices  # 180.00 / 0.95 = 189.47 (5% platform fee)
            lgw_flight = next(f for f in result["flights"] if f["price"] == 189.47)
            assert lgw_flight["original_total_fare"] == 180.0

    @pytest.mark.asyncio
    async def test_search_flights_single_airport_codes(self) -> None:
        """Test single-airport search when user specifies airport codes (not city names)."""
        from app.ai.graph.tools.flights import search_flights

        # Mock the FlightService
        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create mock itinerary for single route
            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                name="British Airways", iata_code="BA"
            )
            mock_segment.operating_flight_number = "BA123"
            mock_segment.origin_iata_code = "LHR"  # Required for filtering
            mock_segment.destination_iata_code = "CDG"  # Required for filtering
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "2026-01-17T10:00:00" if ":" in fmt else "2026-01-17"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "2026-01-17T12:00:00" if ":" in fmt else "2026-01-17"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=120)

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0
            mock_leg.total_time_seconds = 7200  # 2 hours

            # Use correct pricing structure
            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "LHRCDG_FARE"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = 250.0
            mock_total_fare.currency = "EUR"
            mock_fare_totals.total_fare = mock_total_fare
            mock_pricing.fare_totals = mock_fare_totals

            mock_itinerary = MagicMock()
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.session_id = "MOCK_SESSION_456"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            # Call with city flags set to False (airport codes)
            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-17",
                    "adults": 1,
                    "trip_type": "one-way",
                    "origin_is_city": False,
                    "destination_is_city": False,
                }
            )

            # Verify the service was called
            mock_service.search_flights.assert_called_once()
            call_args = mock_service.search_flights.call_args[0][0]

            # Verify city_wise_search flags were passed correctly
            assert call_args.city_wise_search_origin is False
            assert call_args.city_wise_search_destination is False

            # Verify results
            assert result["status"] == "success"
            assert result["summary"]["total_found"] == 1

    @pytest.mark.asyncio
    async def test_search_flights_processes_all_results_for_categorization(
        self,
    ) -> None:
        """Regression test: Verify all flights (>50) are processed for accurate categorization.

        This test ensures that cheapest/fastest/best_value categories are calculated
        from ALL flights, not just the first 50. The cheapest, fastest, and best_value
        flights are intentionally placed after position 50 to catch regressions.
        """
        from app.ai.graph.tools.flights import search_flights

        # Mock the FlightService
        with (
            patch("app.domains.flight.service.FlightService") as mock_service_class,
            patch(
                "app.ai.graph.tools.flights._get_airport_names",
                new_callable=AsyncMock,
            ) as mock_get_airport_names,
        ):
            # Mock airport name lookup to prevent real async calls
            mock_get_airport_names.return_value = {
                "city": "Test City",
                "name": "Test Airport",
            }

            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create 60 mock itineraries to test >50 limit
            # Strategy: Place cheapest, fastest, and best_value flights AFTER position 50
            mock_itineraries = []

            # First 50 flights: Higher prices and longer durations
            for i in range(50):
                mock_segment = MagicMock()
                mock_segment.operating_airline = MagicMock(
                    name="Airline", iata_code="XX"
                )
                mock_segment.operating_flight_number = f"XX{i:03d}"
                mock_segment.departure_datetime = MagicMock()
                mock_segment.departure_datetime.strftime = lambda fmt: (
                    "2026-04-17T10:00:00" if ":" in fmt else "2026-04-17"
                )
                mock_segment.arrival_datetime = MagicMock()
                mock_segment.arrival_datetime.strftime = lambda fmt: (
                    "2026-04-17T14:00:00" if ":" in fmt else "2026-04-17"
                )
                mock_segment.flight_duration = MagicMock(total_minutes=240)  # 4 hours
                # Add airport mocks
                mock_segment.departure_airport = MagicMock(iata_code="LHR")
                mock_segment.arrival_airport = MagicMock(iata_code="CDG")

                mock_leg = MagicMock()
                mock_leg.flight_segments = [mock_segment]
                mock_leg.total_stops = 0
                mock_leg.total_time_seconds = 14400  # 4 hours

                # Use correct pricing structure
                original_price = 500.0 + (i * 10)  # Prices from 500-990
                price_with_fee = round(original_price / 0.95, 2)

                mock_pricing = MagicMock()
                mock_pricing.fare_source_code = f"FARE_{i}"
                mock_fare_totals = MagicMock()
                mock_total_fare = MagicMock()
                mock_total_fare.amount = price_with_fee
                mock_total_fare.currency = "EUR"
                mock_fare_totals.total_fare = mock_total_fare
                mock_original_fare = MagicMock()
                mock_original_fare.amount = original_price
                mock_original_fare.currency = "EUR"
                mock_fare_totals.original_total_fare = mock_original_fare
                mock_fare_totals.platform_fee_percentage = 5.0
                mock_pricing.fare_totals = mock_fare_totals

                mock_itinerary = MagicMock()
                mock_itinerary.pricing = mock_pricing
                mock_itinerary.flight_legs = [mock_leg]
                mock_itinerary.sequence_number = i + 1

                mock_itineraries.append(mock_itinerary)

            # Flight 51: CHEAPEST (100 EUR original) - should be found
            cheapest_segment = MagicMock()
            cheapest_segment.operating_airline = MagicMock(
                name="Budget Air", iata_code="BA"
            )
            cheapest_segment.operating_flight_number = "BA999"
            cheapest_segment.departure_datetime = MagicMock()
            cheapest_segment.departure_datetime.strftime = lambda fmt: (
                "2026-04-17T10:00:00" if ":" in fmt else "2026-04-17"
            )
            cheapest_segment.arrival_datetime = MagicMock()
            cheapest_segment.arrival_datetime.strftime = lambda fmt: (
                "2026-04-17T14:00:00" if ":" in fmt else "2026-04-17"
            )
            cheapest_segment.flight_duration = MagicMock(total_minutes=240)
            cheapest_segment.departure_airport = MagicMock(iata_code="LHR")
            cheapest_segment.arrival_airport = MagicMock(iata_code="CDG")
            cheapest_leg = MagicMock()
            cheapest_leg.flight_segments = [cheapest_segment]
            cheapest_leg.total_stops = 0
            cheapest_leg.total_time_seconds = 14400

            cheapest_original_price = 100.0
            cheapest_price_with_fee = round(cheapest_original_price / 0.95, 2)

            cheapest_pricing = MagicMock()
            cheapest_pricing.fare_source_code = "CHEAPEST_FARE"
            cheapest_fare_totals = MagicMock()
            cheapest_total_fare = MagicMock()
            cheapest_total_fare.amount = cheapest_price_with_fee
            cheapest_total_fare.currency = "EUR"
            cheapest_fare_totals.total_fare = cheapest_total_fare
            cheapest_original_fare = MagicMock()
            cheapest_original_fare.amount = cheapest_original_price
            cheapest_original_fare.currency = "EUR"
            cheapest_fare_totals.original_total_fare = cheapest_original_fare
            cheapest_fare_totals.platform_fee_percentage = 5.0
            cheapest_pricing.fare_totals = cheapest_fare_totals
            cheapest_itinerary = MagicMock()
            cheapest_itinerary.pricing = cheapest_pricing
            cheapest_itinerary.flight_legs = [cheapest_leg]
            cheapest_itinerary.sequence_number = 51
            mock_itineraries.append(cheapest_itinerary)

            # Flight 52: FASTEST (60 minutes) - should be found
            fastest_segment = MagicMock()
            fastest_segment.operating_airline = MagicMock(
                name="Speed Air", iata_code="SA"
            )
            fastest_segment.operating_flight_number = "SA888"
            fastest_segment.departure_datetime = MagicMock()
            fastest_segment.departure_datetime.strftime = lambda fmt: (
                "2026-04-17T10:00:00" if ":" in fmt else "2026-04-17"
            )
            fastest_segment.arrival_datetime = MagicMock()
            fastest_segment.arrival_datetime.strftime = lambda fmt: (
                "2026-04-17T11:00:00" if ":" in fmt else "2026-04-17"
            )
            fastest_segment.flight_duration = MagicMock(total_minutes=60)  # 1 hour
            fastest_segment.departure_airport = MagicMock(iata_code="LHR")
            fastest_segment.arrival_airport = MagicMock(iata_code="CDG")
            fastest_leg = MagicMock()
            fastest_leg.flight_segments = [fastest_segment]
            fastest_leg.total_stops = 0
            fastest_leg.total_time_seconds = 3600  # 1 hour

            fastest_original_price = 600.0
            fastest_price_with_fee = round(fastest_original_price / 0.95, 2)

            fastest_pricing = MagicMock()
            fastest_pricing.fare_source_code = "FASTEST_FARE"
            fastest_fare_totals = MagicMock()
            fastest_total_fare = MagicMock()
            fastest_total_fare.amount = fastest_price_with_fee
            fastest_total_fare.currency = "EUR"
            fastest_fare_totals.total_fare = fastest_total_fare
            fastest_original_fare = MagicMock()
            fastest_original_fare.amount = fastest_original_price
            fastest_original_fare.currency = "EUR"
            fastest_fare_totals.original_total_fare = fastest_original_fare
            fastest_fare_totals.platform_fee_percentage = 5.0
            fastest_pricing.fare_totals = fastest_fare_totals
            fastest_itinerary = MagicMock()
            fastest_itinerary.pricing = fastest_pricing
            fastest_itinerary.flight_legs = [fastest_leg]
            fastest_itinerary.sequence_number = 52
            mock_itineraries.append(fastest_itinerary)

            # Flight 53: BEST VALUE (low price + low duration combo) - should be found
            best_value_segment = MagicMock()
            best_value_segment.operating_airline = MagicMock(
                name="Value Air", iata_code="VA"
            )
            best_value_segment.operating_flight_number = "VA777"
            best_value_segment.departure_datetime = MagicMock()
            best_value_segment.departure_datetime.strftime = lambda fmt: (
                "2026-04-17T10:00:00" if ":" in fmt else "2026-04-17"
            )
            best_value_segment.arrival_datetime = MagicMock()
            best_value_segment.arrival_datetime.strftime = lambda fmt: (
                "2026-04-17T11:30:00" if ":" in fmt else "2026-04-17"
            )
            best_value_segment.flight_duration = MagicMock(
                total_minutes=90
            )  # 1.5 hours
            best_value_segment.departure_airport = MagicMock(iata_code="LHR")
            best_value_segment.arrival_airport = MagicMock(iata_code="CDG")
            best_value_leg = MagicMock()
            best_value_leg.flight_segments = [best_value_segment]
            best_value_leg.total_stops = 0
            best_value_leg.total_time_seconds = 5400  # 1.5 hours

            best_value_original_price = 150.0
            best_value_price_with_fee = round(best_value_original_price / 0.95, 2)

            best_value_pricing = MagicMock()
            best_value_pricing.fare_source_code = "BEST_VALUE_FARE"
            best_value_fare_totals = MagicMock()
            best_value_total_fare = MagicMock()
            best_value_total_fare.amount = best_value_price_with_fee
            best_value_total_fare.currency = "EUR"
            best_value_fare_totals.total_fare = best_value_total_fare
            best_value_original_fare = MagicMock()
            best_value_original_fare.amount = best_value_original_price
            best_value_original_fare.currency = "EUR"
            best_value_fare_totals.original_total_fare = best_value_original_fare
            best_value_fare_totals.platform_fee_percentage = 5.0
            best_value_pricing.fare_totals = best_value_fare_totals
            best_value_itinerary = MagicMock()
            best_value_itinerary.pricing = best_value_pricing
            best_value_itinerary.flight_legs = [best_value_leg]
            best_value_itinerary.sequence_number = 53
            mock_itineraries.append(best_value_itinerary)

            # Add 7 more flights to make it 60 total
            for i in range(54, 61):
                mock_segment = MagicMock()
                mock_segment.operating_airline = MagicMock(
                    name="Airline", iata_code="XX"
                )
                mock_segment.operating_flight_number = f"XX{i:03d}"
                mock_segment.departure_datetime = MagicMock()
                mock_segment.departure_datetime.strftime = lambda fmt: (
                    "2026-04-17T10:00:00" if ":" in fmt else "2026-04-17"
                )
                mock_segment.arrival_datetime = MagicMock()
                mock_segment.arrival_datetime.strftime = lambda fmt: (
                    "2026-04-17T14:00:00" if ":" in fmt else "2026-04-17"
                )
                mock_segment.flight_duration = MagicMock(total_minutes=240)
                mock_segment.departure_airport = MagicMock(iata_code="LHR")
                mock_segment.arrival_airport = MagicMock(iata_code="CDG")
                mock_leg = MagicMock()
                mock_leg.flight_segments = [mock_segment]
                mock_leg.total_stops = 0
                mock_leg.total_time_seconds = 14400

                original_price = 500.0
                price_with_fee = round(original_price / 0.95, 2)

                mock_pricing = MagicMock()
                mock_pricing.fare_source_code = f"FARE_{i}"
                mock_fare_totals = MagicMock()
                mock_total_fare = MagicMock()
                mock_total_fare.amount = price_with_fee
                mock_total_fare.currency = "EUR"
                mock_fare_totals.total_fare = mock_total_fare
                mock_original_fare = MagicMock()
                mock_original_fare.amount = original_price
                mock_original_fare.currency = "EUR"
                mock_fare_totals.original_total_fare = mock_original_fare
                mock_fare_totals.platform_fee_percentage = 5.0
                mock_pricing.fare_totals = mock_fare_totals
                mock_itinerary = MagicMock()
                mock_itinerary.pricing = mock_pricing
                mock_itinerary.flight_legs = [mock_leg]
                mock_itinerary.sequence_number = i
                mock_itineraries.append(mock_itinerary)

            mock_response.fare_itineraries = mock_itineraries
            mock_response.session_id = "MOCK_SESSION_REGRESSION"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-04-17",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            # Verify all flights were processed
            assert result["status"] == "success"
            assert result["summary"]["total_found"] == 60

            # Issue #1034: no more cheapest/fastest/best_value buckets.
            # All flights ship on the flat artifact `flights` list, sorted by
            # best_value. The original cheapest (105.26), fastest (60 min) and
            # best_value (157.89 / 90 min) winners must still all be present
            # somewhere in that list — the test asserts presence, not order.
            all_flights = result["flights"]
            assert len(all_flights) == 60
            prices = [f["price"] for f in all_flights]
            durations = [f.get("duration_minutes") for f in all_flights]

            assert 105.26 in prices, "Cheapest fare (105.26 EUR) must be present"
            cheap = next(f for f in all_flights if f["price"] == 105.26)
            assert cheap["original_total_fare"] == 100.0

            assert 60 in durations, "Fastest flight (60 min) must be present"

            # Best-value winner from the old test: 157.89 / 90 min.
            bv = next(
                (
                    f
                    for f in all_flights
                    if f["price"] == 157.89 and f.get("duration_minutes") == 90
                ),
                None,
            )
            assert bv is not None, "Best-value winner (157.89, 90 min) must be present"
            # And it should sort high (top half) because best_value is the sort key.
            bv_idx = all_flights.index(bv)
            assert bv_idx < 30, (
                f"Best-value winner expected near the top of the sorted list, got index {bv_idx}"
            )

    @pytest.mark.asyncio
    async def test_search_flights_includes_price_breakdown_fields(self) -> None:
        """Test that all flights include original_total_fare and platform_fee_percentage fields."""
        from app.ai.graph.tools.flights import search_flights

        # Mock the FlightService
        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create a simple mock itinerary
            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                name="Test Airline", iata_code="TA"
            )
            mock_segment.operating_flight_number = "TA123"
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "2026-01-17T10:00:00" if ":" in fmt else "2026-01-17"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "2026-01-17T12:00:00" if ":" in fmt else "2026-01-17"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=120)
            mock_segment.departure_airport = MagicMock(iata_code="LHR")
            mock_segment.arrival_airport = MagicMock(iata_code="CDG")

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0
            mock_leg.total_time_seconds = 7200

            original_price = 200.0
            price_with_fee = round(original_price / 0.95, 2)

            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "TEST_FARE"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = price_with_fee
            mock_total_fare.currency = "USD"
            mock_fare_totals.total_fare = mock_total_fare
            mock_original_fare = MagicMock()
            mock_original_fare.amount = original_price
            mock_original_fare.currency = "USD"
            mock_fare_totals.original_total_fare = mock_original_fare
            mock_fare_totals.platform_fee_percentage = 5.0
            mock_pricing.fare_totals = mock_fare_totals

            mock_itinerary = MagicMock()
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.session_id = "MOCK_SESSION_TEST"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-17",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            # Verify all flights have the new price breakdown fields.
            # Issue #1034: flights are now a flat list on the artifact.
            assert result["status"] == "success"
            all_flights = result["flights"]

            for flight in all_flights:
                assert "original_total_fare" in flight, (
                    f"Flight missing original_total_fare field: {flight}"
                )
                assert "platform_fee_percentage" in flight, (
                    f"Flight missing platform_fee_percentage field: {flight}"
                )
                assert flight["platform_fee_percentage"] == 5.0, (
                    f"Platform fee percentage should be 5.0, got {flight['platform_fee_percentage']}"
                )
                assert flight["original_total_fare"] == original_price, (
                    f"Original total fare should be {original_price}, got {flight['original_total_fare']}"
                )

    @pytest.mark.asyncio
    async def test_search_flights_price_consistency(self) -> None:
        """Test that price field equals apply_platform_fee(original_total_fare) for all flights."""
        from app.ai.graph.tools.flights import search_flights
        from app.domains.flight.pricing import apply_platform_fee

        # Mock the FlightService
        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()

            # Create multiple mock itineraries with different prices
            mock_itineraries = []
            test_prices = [100.0, 200.0, 300.0, 500.0]

            for i, original_price in enumerate(test_prices):
                mock_segment = MagicMock()
                mock_segment.operating_airline = MagicMock(
                    name=f"Airline {i}", iata_code=f"AL{i}"
                )
                mock_segment.operating_flight_number = f"AL{i}123"
                mock_segment.departure_datetime = MagicMock()
                mock_segment.departure_datetime.strftime = lambda fmt: (
                    "2026-01-17T10:00:00" if ":" in fmt else "2026-01-17"
                )
                mock_segment.arrival_datetime = MagicMock()
                mock_segment.arrival_datetime.strftime = lambda fmt: (
                    "2026-01-17T12:00:00" if ":" in fmt else "2026-01-17"
                )
                mock_segment.flight_duration = MagicMock(total_minutes=120)
                mock_segment.departure_airport = MagicMock(iata_code="LHR")
                mock_segment.arrival_airport = MagicMock(iata_code="CDG")

                mock_leg = MagicMock()
                mock_leg.flight_segments = [mock_segment]
                mock_leg.total_stops = 0
                mock_leg.total_time_seconds = 7200

                price_with_fee = round(original_price / 0.95, 2)

                mock_pricing = MagicMock()
                mock_pricing.fare_source_code = f"FARE_{i}"
                mock_fare_totals = MagicMock()
                mock_total_fare = MagicMock()
                mock_total_fare.amount = price_with_fee
                mock_total_fare.currency = "USD"
                mock_fare_totals.total_fare = mock_total_fare
                mock_original_fare = MagicMock()
                mock_original_fare.amount = original_price
                mock_original_fare.currency = "USD"
                mock_fare_totals.original_total_fare = mock_original_fare
                mock_fare_totals.platform_fee_percentage = 5.0
                mock_pricing.fare_totals = mock_fare_totals

                mock_itinerary = MagicMock()
                mock_itinerary.pricing = mock_pricing
                mock_itinerary.flight_legs = [mock_leg]
                mock_itinerary.sequence_number = i + 1

                mock_itineraries.append(mock_itinerary)

            mock_response.fare_itineraries = mock_itineraries
            mock_response.session_id = "MOCK_SESSION_CONSISTENCY"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-17",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            # Verify price consistency for all flights — flat list (#1034).
            assert result["status"] == "success"
            all_flights = result["flights"]

            for flight in all_flights:
                original_price = flight["original_total_fare"]
                expected_price = float(apply_platform_fee(original_price))
                actual_price = flight["price"]
                assert abs(actual_price - expected_price) < 0.01, (
                    f"Price inconsistency: expected {expected_price} (from apply_platform_fee({original_price})), "
                    f"got {actual_price} for flight {flight.get('id', 'unknown')}"
                )

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_morning(self) -> None:
        """Test mapping morning preference to TimeWindow."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window = _map_time_preference_to_window("morning")
        assert window is not None
        assert window.min == "06:00"
        assert window.max == "12:00"

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_afternoon(self) -> None:
        """Test mapping afternoon preference to TimeWindow."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window = _map_time_preference_to_window("afternoon")
        assert window is not None
        assert window.min == "12:00"
        assert window.max == "18:00"

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_evening(self) -> None:
        """Test mapping evening preference to TimeWindow."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window = _map_time_preference_to_window("evening")
        assert window is not None
        assert window.min == "18:00"
        assert window.max == "23:00"

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_case_insensitive(self) -> None:
        """Test time preference mapping is case-insensitive."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window_lower = _map_time_preference_to_window("morning")
        window_upper = _map_time_preference_to_window("MORNING")
        window_mixed = _map_time_preference_to_window("Morning")

        assert window_lower.min == window_upper.min == window_mixed.min
        assert window_lower.max == window_upper.max == window_mixed.max

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_invalid(self) -> None:
        """Test invalid time preference returns None."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window = _map_time_preference_to_window("invalid_time")
        assert window is None

    @pytest.mark.asyncio
    async def test_map_time_preference_to_window_none(self) -> None:
        """Test None preference returns None."""
        from app.ai.graph.tools.flights import _map_time_preference_to_window

        window = _map_time_preference_to_window(None)
        assert window is None

    @pytest.mark.asyncio
    async def test_search_flights_with_morning_preference(self) -> None:
        """Test search_flights accepts departure_time_preference parameter."""
        from app.ai.graph.tools.flights import search_flights

        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()
            mock_response.fare_itineraries = []
            mock_response.session_id = "test_session"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service_class.return_value = mock_service

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-03-15",
                    "adults": 1,
                    "trip_type": "one-way",
                    "departure_time_preference": "morning",
                }
            )

            # Should not error even with no results
            assert result["status"] == "no_results" or result["status"] == "success"

    @pytest.mark.asyncio
    async def test_search_flights_with_both_time_preferences(self) -> None:
        """Test search_flights accepts both departure and arrival time preferences."""
        from app.ai.graph.tools.flights import search_flights

        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()
            mock_response.fare_itineraries = []
            mock_response.session_id = "test_session"
            mock_response.errors = []

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service_class.return_value = mock_service

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-03-15",
                    "adults": 1,
                    "trip_type": "one-way",
                    "departure_time_preference": "afternoon",
                    "arrival_time_preference": "evening",
                }
            )

            # Should not error
            assert result["status"] in ["no_results", "success"]

    @pytest.mark.asyncio
    async def test_time_preference_windows_configuration(self) -> None:
        """Test TIME_PREFERENCE_WINDOWS has all required preferences."""
        from app.ai.graph.tools.flights import TIME_PREFERENCE_WINDOWS

        assert "morning" in TIME_PREFERENCE_WINDOWS
        assert "afternoon" in TIME_PREFERENCE_WINDOWS
        assert "evening" in TIME_PREFERENCE_WINDOWS
        assert "early_morning" in TIME_PREFERENCE_WINDOWS
        assert "night" in TIME_PREFERENCE_WINDOWS

        # Verify structure
        for _pref, window in TIME_PREFERENCE_WINDOWS.items():
            assert "min" in window
            assert "max" in window

    @pytest.mark.asyncio
    async def test_search_flights_all_revalidation_fails_returns_no_results(
        self,
    ) -> None:
        """When revalidation marks all flights unavailable, tool returns no_results."""
        from app.ai.graph.tools.flights import search_flights
        from app.core.config import settings

        with (
            patch("app.domains.flight.service.FlightService") as mock_service_class,
            patch.object(settings, "FLIGHT_SEARCH_CONCURRENT_REVALIDATION", True),
        ):
            mock_service = MagicMock()
            mock_response = MagicMock()

            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                airline_name="British Airways", iata_code="BA"
            )
            mock_segment.operating_flight_number = MagicMock(formatted_number="BA123")
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "10:00" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "12:30" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=150)
            mock_segment.departure_airport = MagicMock(iata_code="LHR")
            mock_segment.arrival_airport = MagicMock(iata_code="CDG")

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0

            mock_itinerary = MagicMock()
            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "LHRCDG_REVAL_FAIL"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = 250.0
            mock_total_fare.currency = "GBP"
            mock_fare_totals.total_fare = mock_total_fare
            mock_pricing.fare_totals = mock_fare_totals
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.errors = []
            mock_response.session_id = "fl-test-session-all-fail"

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_unavailable()
            mock_service_class.return_value = mock_service

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-15",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

            assert result["status"] == "no_results"
            assert "message" in result
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_search_flights_skips_revalidation_when_flag_disabled(self) -> None:
        """When FLIGHT_SEARCH_CONCURRENT_REVALIDATION=False, revalidate_fare must not be called."""
        from app.ai.graph.tools.flights import search_flights
        from app.core.config import settings

        with (
            patch("app.domains.flight.service.FlightService") as mock_service_class,
            patch.object(settings, "FLIGHT_SEARCH_CONCURRENT_REVALIDATION", False),
        ):
            mock_service = MagicMock()
            mock_response = MagicMock()

            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                airline_name="British Airways", iata_code="BA"
            )
            mock_segment.operating_flight_number = MagicMock(formatted_number="BA123")
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "10:00" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "12:30" if fmt == "%H:%M" else "2026-01-15"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=150)
            mock_segment.departure_airport = MagicMock(iata_code="LHR")
            mock_segment.arrival_airport = MagicMock(iata_code="CDG")

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0

            mock_itinerary = MagicMock()
            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "LHRCDG_FLAG_OFF"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = 250.0
            mock_total_fare.currency = "GBP"
            mock_fare_totals.total_fare = mock_total_fare
            mock_pricing.fare_totals = mock_fare_totals
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.errors = []
            # Non-empty session_id triggers the revalidation gate in _do_flight_search.
            mock_response.session_id = "fl-test-session-flag-off"

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = AsyncMock()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-01-15",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            assert result["status"] == "success"
            mock_service.revalidate_fare.assert_not_awaited()


class TestFlightState:
    """Tests for FlightState TypedDict."""

    def test_flight_state_structure(self) -> None:
        """Test that FlightState has correct structure."""
        from app.ai.graph.state import FlightParams, FlightState

        # Verify FlightParams fields
        params: FlightParams = {
            "origin": "LHR",
            "destination": "CDG",
            "departure_date": "2025-01-15",
        }
        assert params["origin"] == "LHR"

        # FlightState should be a TypedDict (just verify import works)
        assert FlightState is not None
        assert FlightParams is not None


class TestFlightGraphModule:
    """Tests for the flight graph module."""

    def test_prompt_exports(self) -> None:
        """Test that prompt module exports system prompt."""
        from app.ai.graph.prompts import FLIGHT_SYSTEM_PROMPT

        assert isinstance(FLIGHT_SYSTEM_PROMPT, str)
        assert "Voya" in FLIGHT_SYSTEM_PROMPT
        assert "flight" in FLIGHT_SYSTEM_PROMPT.lower()


class TestExtractFlightInfo:
    """Tests for _extract_flight_info function and duration calculation with layovers."""

    def _create_mock_segment(
        self,
        flight_duration_minutes: int = 120,
        departure_datetime: datetime | str | None = None,
        arrival_datetime: datetime | str | None = None,
        departure_datetime_wrapper: bool = False,
        arrival_datetime_wrapper: bool = False,
    ) -> MagicMock:
        """Create a mock flight segment with configurable datetime formats."""
        segment = MagicMock()

        # Flight duration
        duration_mock = MagicMock()
        duration_mock.total_minutes = flight_duration_minutes
        segment.flight_duration = duration_mock

        # Departure datetime - handle different formats
        if departure_datetime:
            if departure_datetime_wrapper:
                # DateTime wrapper object with .value
                wrapper = MagicMock()
                wrapper.value = departure_datetime
                segment.departure_datetime = wrapper
            else:
                segment.departure_datetime = departure_datetime
        else:
            segment.departure_datetime = None

        # Arrival datetime - handle different formats
        if arrival_datetime:
            if arrival_datetime_wrapper:
                # DateTime wrapper object with .value
                wrapper = MagicMock()
                wrapper.value = arrival_datetime
                segment.arrival_datetime = wrapper
            else:
                segment.arrival_datetime = arrival_datetime
        else:
            segment.arrival_datetime = None

        # Basic segment info
        segment.operating_airline = MagicMock(
            airline_name="Test Airline", iata_code="TA"
        )
        segment.departure_airport = MagicMock(iata_code="LHR", city_name="London")
        segment.arrival_airport = MagicMock(iata_code="CDG", city_name="Paris")

        return segment

    def _create_mock_itinerary(
        self,
        segments: list[MagicMock],
        price: float = 250.0,
        currency: str = "USD",
        total_stops: int = 0,
    ) -> MagicMock:
        """Create a mock itinerary with given segments."""
        itinerary = MagicMock()

        # Pricing
        pricing = MagicMock()
        pricing.fare_source_code = "TEST123"
        total_fare = MagicMock()
        total_fare.amount = price
        total_fare.currency = currency
        fare_totals = MagicMock()
        fare_totals.total_fare = total_fare
        pricing.fare_totals = fare_totals
        itinerary.pricing = pricing

        # Flight legs
        leg = MagicMock()
        leg.flight_segments = segments
        leg.total_stops = total_stops
        itinerary.flight_legs = [leg]

        return itinerary

    def test_duration_single_segment_no_layover(self) -> None:
        """Test duration calculation for single segment flight (no layover)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        # Single segment: 120 minutes flight time, no layover
        segment = self._create_mock_segment(flight_duration_minutes=120)
        itinerary = self._create_mock_itinerary([segment])

        result = _extract_flight_info(itinerary)

        assert result is not None
        assert result["duration_minutes"] == 120  # Only flight time, no layover

    def test_duration_multiple_segments_with_layover(self) -> None:
        """Test duration calculation for multiple segments with layover time."""
        from app.ai.graph.tools.flights import _extract_flight_info

        # Two segments with 60 minute layover
        # Segment 1: 10:00 - 12:00 (120 min flight)
        # Layover: 12:00 - 13:00 (60 min)
        # Segment 2: 13:00 - 14:30 (90 min flight)
        # Total: 120 + 60 + 90 = 270 minutes
        base_time = datetime(2026, 4, 15, 10, 0, 0)

        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=base_time + timedelta(minutes=180),  # 60 min layover
            arrival_datetime=base_time + timedelta(minutes=270),
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Total = 120 (flight) + 60 (layover) + 90 (flight) = 270
        assert result["duration_minutes"] == 270

    def test_duration_with_datetime_wrapper_objects(self) -> None:
        """Test duration calculation with DateTime wrapper objects (.value attribute)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        # Use wrapper objects (simulating FlightLogic DateTime wrapper)
        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
            arrival_datetime_wrapper=True,  # Wrap arrival in .value
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=base_time + timedelta(minutes=180),
            departure_datetime_wrapper=True,  # Wrap departure in .value
            arrival_datetime=base_time + timedelta(minutes=270),
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should still calculate correctly: 120 + 60 + 90 = 270
        assert result["duration_minutes"] == 270

    def test_duration_with_string_datetime_formats(self) -> None:
        """Test duration calculation with string datetime formats (ISO and common formats)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        # Use ISO format strings
        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time.isoformat(),
            arrival_datetime=(base_time + timedelta(minutes=120)).isoformat(),
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=(base_time + timedelta(minutes=180)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            arrival_datetime=(base_time + timedelta(minutes=270)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should parse strings correctly: 120 + 60 + 90 = 270
        assert result["duration_minutes"] == 270

    def test_duration_with_missing_datetimes(self) -> None:
        """Test duration calculation when some datetimes are missing (should skip layover)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        # Segment 1 has datetimes, segment 2 missing arrival
        base_time = datetime(2026, 4, 15, 10, 0, 0)

        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=None,  # Missing departure
            arrival_datetime=None,  # Missing arrival
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should only count flight times (no layover calculated): 120 + 90 = 210
        assert result["duration_minutes"] == 210

    def test_duration_with_negative_layover_ignored(self) -> None:
        """Test that negative layover times are ignored (should not subtract time)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        # Segment 2 departs before segment 1 arrives (invalid, but should handle gracefully)
        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=base_time
            + timedelta(minutes=60),  # Before seg1 arrives!
            arrival_datetime=base_time + timedelta(minutes=150),
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should only count flight times (negative layover ignored): 120 + 90 = 210
        assert result["duration_minutes"] == 210

    def test_duration_with_invalid_datetime_format(self) -> None:
        """Test duration calculation with invalid datetime format (should skip layover)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime="invalid-date-format",  # Invalid format
            arrival_datetime=base_time + timedelta(minutes=270),
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should only count flight times (invalid datetime skipped): 120 + 90 = 210
        assert result["duration_minutes"] == 210

    def test_duration_round_trip_with_multiple_legs(self) -> None:
        """Test duration calculation for round trip (multiple legs)."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        # Outbound leg: 2 segments with layover
        outbound_seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=120),
        )
        outbound_seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime=base_time + timedelta(minutes=180),
            arrival_datetime=base_time + timedelta(minutes=270),
        )

        # Return leg: 1 segment (direct)
        return_seg = self._create_mock_segment(
            flight_duration_minutes=150,
            departure_datetime=base_time + timedelta(days=7),
            arrival_datetime=base_time + timedelta(days=7, minutes=150),
        )

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "TEST123"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=500.0, currency="USD")
        itinerary.pricing.fare_totals = fare_totals

        outbound_leg = MagicMock()
        outbound_leg.flight_segments = [outbound_seg1, outbound_seg2]
        outbound_leg.total_stops = 1

        return_leg = MagicMock()
        return_leg.flight_segments = [return_seg]
        return_leg.total_stops = 0

        itinerary.flight_legs = [outbound_leg, return_leg]

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Total = outbound (120 + 60 + 90) + return (150) = 270 + 150 = 420
        assert result["duration_minutes"] == 420

    def test_duration_with_iso_string_with_z_suffix(self) -> None:
        """Test duration calculation with ISO string format with Z suffix."""
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 4, 15, 10, 0, 0)

        # Use ISO format with Z suffix
        seg1 = self._create_mock_segment(
            flight_duration_minutes=120,
            departure_datetime="2026-04-15T10:00:00Z",
            arrival_datetime="2026-04-15T12:00:00Z",
        )
        seg2 = self._create_mock_segment(
            flight_duration_minutes=90,
            departure_datetime="2026-04-15T13:00:00Z",
            arrival_datetime="2026-04-15T14:30:00Z",
        )

        itinerary = self._create_mock_itinerary([seg1, seg2], total_stops=1)

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should parse Z suffix correctly: 120 + 60 + 90 = 270
        assert result["duration_minutes"] == 270

    def test_duration_empty_segments_skipped(self) -> None:
        """Test that legs with empty segments are skipped."""
        from app.ai.graph.tools.flights import _extract_flight_info

        # Leg with segments
        seg = self._create_mock_segment(flight_duration_minutes=120)
        leg1 = MagicMock()
        leg1.flight_segments = [seg]
        leg1.total_stops = 0

        # Leg with empty segments
        leg2 = MagicMock()
        leg2.flight_segments = []
        leg2.total_stops = 0

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "TEST123"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=250.0, currency="USD")
        itinerary.pricing.fare_totals = fare_totals
        itinerary.flight_legs = [leg1, leg2]

        result = _extract_flight_info(itinerary)

        assert result is not None
        # Should only count leg1: 120 minutes
        assert result["duration_minutes"] == 120

    def test_duration_no_segments_returns_none(self) -> None:
        """Test that itinerary with no segments returns None."""
        from app.ai.graph.tools.flights import _extract_flight_info

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "TEST123"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=250.0, currency="USD")
        itinerary.pricing.fare_totals = fare_totals

        leg = MagicMock()
        leg.flight_segments = []  # Empty segments
        itinerary.flight_legs = [leg]

        result = _extract_flight_info(itinerary)

        assert result is None

    def test_duration_no_legs_returns_none(self) -> None:
        """Test that itinerary with no legs returns None."""
        from app.ai.graph.tools.flights import _extract_flight_info

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "TEST123"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=250.0, currency="USD")
        itinerary.pricing.fare_totals = fare_totals
        itinerary.flight_legs = []  # No legs

        result = _extract_flight_info(itinerary)

        assert result is None

    def test_round_trip_segments_include_leg_index(self) -> None:
        """Segments produced for a round-trip itinerary must carry leg_index.

        The frontend reconstructs separate outbound/return legs from this field
        (hydrateChatFlightResultsToSearchCache.ts hasLegIndex branch).  If
        leg_index is dropped, the frontend silently treats round-trips as one-way.
        """
        from app.ai.graph.tools.flights import _extract_flight_info

        base_time = datetime(2026, 6, 1, 10, 0, 0)

        outbound_seg = self._create_mock_segment(
            flight_duration_minutes=210,
            departure_datetime=base_time,
            arrival_datetime=base_time + timedelta(minutes=210),
        )
        outbound_seg.departure_airport = MagicMock(
            iata_code="AMS", city_name="Amsterdam"
        )
        outbound_seg.arrival_airport = MagicMock(iata_code="BCN", city_name="Barcelona")

        return_seg = self._create_mock_segment(
            flight_duration_minutes=210,
            departure_datetime=base_time + timedelta(days=7),
            arrival_datetime=base_time + timedelta(days=7, minutes=210),
        )
        return_seg.departure_airport = MagicMock(iata_code="BCN", city_name="Barcelona")
        return_seg.arrival_airport = MagicMock(iata_code="AMS", city_name="Amsterdam")

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "RT-001"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=300.0, currency="EUR")
        itinerary.pricing.fare_totals = fare_totals

        outbound_leg = MagicMock()
        outbound_leg.flight_segments = [outbound_seg]
        outbound_leg.total_stops = 0

        return_leg = MagicMock()
        return_leg.flight_segments = [return_seg]
        return_leg.total_stops = 0

        itinerary.flight_legs = [outbound_leg, return_leg]

        result = _extract_flight_info(itinerary)

        assert result is not None
        segments = result.get("segments", [])
        assert len(segments) == 2, "expected one segment per leg"
        assert segments[0].get("leg_index") == 0, (
            "outbound segment must have leg_index=0"
        )
        assert segments[1].get("leg_index") == 1, "return segment must have leg_index=1"


class TestExtractSegmentInfo:
    """Tests for _extract_segment_info function, particularly flight number extraction."""

    def _create_mock_segment(
        self,
        marketing_flight_number: MagicMock | None = None,
        operating_flight_number: MagicMock | None = None,
        departure_code: str = "LHR",
        arrival_code: str = "CDG",
        marketing_airline: MagicMock | None = None,
        operating_airline: MagicMock | None = None,
    ) -> MagicMock:
        """Create a mock flight segment with configurable flight numbers and airlines."""
        segment = MagicMock()

        # Airport info
        segment.departure_airport = MagicMock(
            iata_code=departure_code, city_name="London"
        )
        segment.arrival_airport = MagicMock(iata_code=arrival_code, city_name="Paris")

        # Flight numbers
        # Explicitly set to None to prevent MagicMock from auto-creating attributes
        if marketing_flight_number is not None:
            segment.marketing_flight_number = marketing_flight_number
        else:
            segment.marketing_flight_number = None
        if operating_flight_number is not None:
            segment.operating_flight_number = operating_flight_number
        else:
            segment.operating_flight_number = None

        # Airlines — explicitly set to None so auto-attribute generation doesn't
        # produce truthy mock objects that break airline extraction logic.
        segment.marketing_airline = marketing_airline
        segment.operating_airline = operating_airline

        # Duration
        duration_mock = MagicMock()
        duration_mock.total_minutes = 120
        segment.flight_duration = duration_mock

        return segment

    def test_extract_marketing_flight_number_with_formatted_number(self) -> None:
        """Test extraction when marketing_flight_number has formatted_number."""
        from app.ai.graph.tools.flights import _extract_segment_info

        # Create mock with formatted_number
        marketing_fn = MagicMock()
        marketing_fn.formatted_number = "BA123"
        marketing_fn.flight_number = "123"
        marketing_fn.carrier_code = "BA"

        segment = self._create_mock_segment(marketing_flight_number=marketing_fn)
        result = _extract_segment_info(segment)

        assert result["flight_number"] == "BA123"
        assert result["flight_number_info"] is not None
        assert result["flight_number_info"]["formatted_number"] == "BA123"
        assert result["flight_number_info"]["number"] == "123"
        assert result["flight_number_info"]["airline_prefix"] == "BA"

    def test_extract_marketing_flight_number_without_formatted_number(self) -> None:
        """Test extraction when marketing_flight_number lacks formatted_number (manual construction)."""
        from app.ai.graph.tools.flights import _extract_segment_info

        # Create mock without formatted_number
        marketing_fn = MagicMock()
        marketing_fn.formatted_number = None
        marketing_fn.flight_number = "456"
        marketing_fn.carrier_code = "AF"

        segment = self._create_mock_segment(marketing_flight_number=marketing_fn)
        result = _extract_segment_info(segment)

        assert result["flight_number"] == "AF456"
        assert result["flight_number_info"] is not None
        assert result["flight_number_info"]["formatted_number"] == "AF456"
        assert result["flight_number_info"]["number"] == "456"
        assert result["flight_number_info"]["airline_prefix"] == "AF"

    def test_extract_operating_flight_number_fallback_with_formatted_number(
        self,
    ) -> None:
        """Test fallback to operating_flight_number when marketing_flight_number is missing."""
        from app.ai.graph.tools.flights import _extract_segment_info

        # Create mock with only operating_flight_number
        operating_fn = MagicMock()
        operating_fn.formatted_number = "LH789"
        operating_fn.flight_number = "789"
        operating_fn.carrier_code = "LH"

        segment = self._create_mock_segment(operating_flight_number=operating_fn)
        result = _extract_segment_info(segment)

        assert result["flight_number"] == "LH789"
        assert result["flight_number_info"] is not None
        assert result["flight_number_info"]["formatted_number"] == "LH789"
        assert result["flight_number_info"]["number"] == "789"
        assert result["flight_number_info"]["airline_prefix"] == "LH"

    def test_extract_operating_flight_number_fallback_without_formatted_number(
        self,
    ) -> None:
        """Test fallback to operating_flight_number without formatted_number (manual construction).

        Symmetric fallback: operating_flight_number now has the same fallback logic
        as marketing_flight_number - constructs from carrier_code + flight_number.
        """
        from app.ai.graph.tools.flights import _extract_segment_info

        # Create mock with operating_flight_number but no formatted_number
        operating_fn = MagicMock()
        operating_fn.formatted_number = None
        operating_fn.flight_number = "321"
        operating_fn.carrier_code = "KL"

        segment = self._create_mock_segment(operating_flight_number=operating_fn)
        result = _extract_segment_info(segment)

        # Symmetric fallback: operating_flight_number without formatted_number
        # now gets manual construction (same as marketing_flight_number)
        assert result["flight_number"] == "KL321"
        assert result["flight_number_info"] is not None
        assert result["flight_number_info"]["formatted_number"] == "KL321"
        assert result["flight_number_info"]["number"] == "321"
        assert result["flight_number_info"]["airline_prefix"] == "KL"

    def test_extract_duration_minutes_is_returned(self) -> None:
        """duration_minutes must be in the return dict so segmentInfoToSegmentCamel can set flightDuration.totalMinutes."""
        from app.ai.graph.tools.flights import _extract_segment_info

        # _create_mock_segment sets flight_duration.total_minutes = 120
        segment = self._create_mock_segment()
        result = _extract_segment_info(segment)

        assert result["duration_minutes"] == 120
        assert result["duration"] == "2h 0m"

    def test_extract_duration_minutes_zero_when_no_flight_duration(self) -> None:
        """duration_minutes is 0 when flight_duration is absent."""
        from app.ai.graph.tools.flights import _extract_segment_info

        segment = self._create_mock_segment()
        segment.flight_duration = None
        result = _extract_segment_info(segment)

        assert result["duration_minutes"] == 0
        assert result["duration"] == "0h 0m"

    def test_extract_flight_number_missing_all(self) -> None:
        """Test extraction when both marketing and operating flight numbers are missing."""
        from app.ai.graph.tools.flights import _extract_segment_info

        segment = self._create_mock_segment()
        result = _extract_segment_info(segment)

        assert result["flight_number"] == ""
        assert result["flight_number_info"] is None

    def test_extract_flight_number_marketing_takes_precedence(self) -> None:
        """Test that marketing_flight_number takes precedence over operating_flight_number."""
        from app.ai.graph.tools.flights import _extract_segment_info

        # Both present, marketing should be used
        marketing_fn = MagicMock()
        marketing_fn.formatted_number = "BA999"
        marketing_fn.flight_number = "999"
        marketing_fn.carrier_code = "BA"

        operating_fn = MagicMock()
        operating_fn.formatted_number = "LH888"
        operating_fn.flight_number = "888"
        operating_fn.carrier_code = "LH"

        segment = self._create_mock_segment(
            marketing_flight_number=marketing_fn, operating_flight_number=operating_fn
        )
        result = _extract_segment_info(segment)

        assert result["flight_number"] == "BA999"
        assert result["flight_number_info"]["formatted_number"] == "BA999"
        assert result["flight_number_info"]["airline_prefix"] == "BA"

    def test_extract_airline_info_from_marketing_airline(self) -> None:
        """Test that airline_code, airline, and logo_url are extracted from marketing_airline."""
        from app.ai.graph.tools.flights import _extract_segment_info

        marketing_airline = MagicMock()
        marketing_airline.iata_code = "BA"
        marketing_airline.airline_name = "British Airways"
        marketing_airline.logo_url = "https://example.com/ba.gif"

        segment = self._create_mock_segment(marketing_airline=marketing_airline)
        result = _extract_segment_info(segment)

        assert result["airline_code"] == "BA"
        assert result["airline"] == "British Airways"
        assert result["logo_url"] == "https://example.com/ba.gif"

    def test_extract_airline_info_falls_back_to_operating_airline(self) -> None:
        """Test that airline info falls back to operating_airline when marketing_airline is absent."""
        from app.ai.graph.tools.flights import _extract_segment_info

        operating_airline = MagicMock()
        operating_airline.iata_code = "LH"
        operating_airline.airline_name = "Lufthansa"
        operating_airline.logo_url = "https://example.com/lh.gif"

        segment = self._create_mock_segment(operating_airline=operating_airline)
        result = _extract_segment_info(segment)

        assert result["airline_code"] == "LH"
        assert result["airline"] == "Lufthansa"
        assert result["logo_url"] == "https://example.com/lh.gif"

    def test_extract_airline_info_empty_when_no_airline(self) -> None:
        """Test that airline fields are empty/None when no airline objects are present."""
        from app.ai.graph.tools.flights import _extract_segment_info

        segment = self._create_mock_segment()
        result = _extract_segment_info(segment)

        assert result["airline_code"] == ""
        assert result["airline"] == ""
        assert result["logo_url"] is None

    def test_segments_array_includes_flight_number_fields(self) -> None:
        """Test that _extract_flight_info includes flight_number fields in segments array."""
        from app.ai.graph.tools.flights import _extract_flight_info

        # Create segment with marketing flight number using helper method
        marketing_fn = MagicMock()
        marketing_fn.formatted_number = "BA123"
        marketing_fn.flight_number = "123"
        marketing_fn.carrier_code = "BA"

        segment = self._create_mock_segment(marketing_flight_number=marketing_fn)

        # Add operating_airline and datetimes for _extract_flight_info (needed for full extraction)
        segment.operating_airline = MagicMock(
            airline_name="British Airways", iata_code="BA"
        )
        base_time = datetime(2026, 4, 15, 10, 0, 0)
        segment.departure_datetime = base_time
        segment.arrival_datetime = base_time + timedelta(minutes=120)

        # Create itinerary
        leg = MagicMock()
        leg.flight_segments = [segment]
        leg.total_stops = 0

        itinerary = MagicMock()
        itinerary.pricing = MagicMock()
        itinerary.pricing.fare_source_code = "TEST123"
        fare_totals = MagicMock()
        fare_totals.total_fare = MagicMock(amount=250.0, currency="USD")
        itinerary.pricing.fare_totals = fare_totals
        itinerary.flight_legs = [leg]

        result = _extract_flight_info(itinerary)

        assert result is not None
        assert "segments" in result
        assert len(result["segments"]) == 1
        assert "flight_number" in result["segments"][0]
        assert "flight_number_info" in result["segments"][0]
        assert result["segments"][0]["flight_number"] == "BA123"
        assert result["segments"][0]["flight_number_info"] is not None
        assert (
            result["segments"][0]["flight_number_info"]["formatted_number"] == "BA123"
        )


class TestValidateFlightResults:
    """Tests for _validate_flight_results output validation."""

    def _make_flight(self, **overrides: object) -> dict:
        """Create a valid flight dict with optional overrides."""
        future_date = (utc_date() + timedelta(days=7)).strftime("%Y-%m-%d")
        base: dict = {
            "id": "TEST1",
            "price": 250.0,
            "duration_minutes": 120,
            "airline": "Test Air",
            "segments": [{"origin_code": "LHR", "destination_code": "CDG"}],
            "origin_code": "LHR",
            "destination_code": "CDG",
            "departure_date": future_date,
        }
        base.update(overrides)
        return base

    def test_valid_flights_pass_through(self) -> None:
        """Valid flights are not filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [self._make_flight(), self._make_flight(id="TEST2", price=500.0)]
        result = _validate_flight_results(flights)
        assert len(result) == 2

    def test_zero_price_filtered(self) -> None:
        """Flights with price=0 are filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [self._make_flight(price=0)]
        result = _validate_flight_results(flights)
        assert len(result) == 0

    def test_negative_price_filtered(self) -> None:
        """Flights with negative price are filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [self._make_flight(price=-100)]
        result = _validate_flight_results(flights)
        assert len(result) == 0

    def test_excessive_price_filtered(self) -> None:
        """Flights with price > 50,000 are filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [self._make_flight(price=60_000)]
        result = _validate_flight_results(flights)
        assert len(result) == 0

    def test_past_departure_date_filtered(self) -> None:
        """Flights departing in the past are filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        past_date = (utc_date() - timedelta(days=1)).strftime("%Y-%m-%d")
        flights = [self._make_flight(departure_date=past_date)]
        result = _validate_flight_results(flights)
        assert len(result) == 0

    def test_missing_required_fields_filtered(self) -> None:
        """Flights missing required fields are filtered out."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [self._make_flight(airline=None)]
        result = _validate_flight_results(flights)
        assert len(result) == 0

    def test_mixed_valid_invalid(self) -> None:
        """Only invalid flights are filtered; valid ones remain."""
        from app.ai.graph.tools.flights import _validate_flight_results

        flights = [
            self._make_flight(id="VALID", price=200),
            self._make_flight(id="BAD_PRICE", price=0),
            self._make_flight(id="NO_AIRLINE", airline=None),
        ]
        result = _validate_flight_results(flights)
        assert len(result) == 1
        assert result[0]["id"] == "VALID"


class TestValidateHotelResults:
    """Tests for _validate_hotel_results output validation."""

    def _make_hotel(self, **overrides: object) -> dict:
        """Create a valid hotel dict with optional overrides."""
        base: dict = {
            "hotel_name": "Test Hotel",
            "total_price": 150.0,
            "hotel_rating": 4,
            "address": "123 Test St",
            "currency": "GBP",
        }
        base.update(overrides)
        return base

    def test_valid_hotels_pass_through(self) -> None:
        """Valid hotels are not filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(), self._make_hotel(hotel_name="Hotel B")]
        result = _validate_hotel_results(hotels)
        assert len(result) == 2

    def test_zero_price_filtered(self) -> None:
        """Hotels with price=0 are filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(total_price=0)]
        result = _validate_hotel_results(hotels)
        assert len(result) == 0

    def test_negative_price_filtered(self) -> None:
        """Hotels with negative price are filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(total_price=-50)]
        result = _validate_hotel_results(hotels)
        assert len(result) == 0

    def test_missing_hotel_name_filtered(self) -> None:
        """Hotels missing hotel_name are filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(hotel_name=None)]
        result = _validate_hotel_results(hotels)
        assert len(result) == 0

    def test_missing_address_filtered(self) -> None:
        """Hotels missing address are filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(address=None)]
        result = _validate_hotel_results(hotels)
        assert len(result) == 0

    def test_non_numeric_price_filtered(self) -> None:
        """Hotels with non-numeric price are filtered out."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [self._make_hotel(total_price="not_a_number")]
        result = _validate_hotel_results(hotels)
        assert len(result) == 0

    def test_mixed_valid_invalid(self) -> None:
        """Only invalid hotels are filtered; valid ones remain."""
        from app.ai.graph.tools.hotels import _validate_hotel_results

        hotels = [
            self._make_hotel(hotel_name="Good Hotel"),
            self._make_hotel(hotel_name=None),
            self._make_hotel(total_price=0),
        ]
        result = _validate_hotel_results(hotels)
        assert len(result) == 1
        assert result[0]["hotel_name"] == "Good Hotel"


class TestDeterministicDateParse:
    """Tests for _try_deterministic_parse — bypass LLM for trivial keywords."""

    def test_now_returns_today(self) -> None:
        """'now' resolves to today's date deterministically."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("now", today)
        assert result is not None
        assert result["departure_date"] == today
        assert result["error"] is None

    def test_today_returns_today(self) -> None:
        """'today' resolves to today's date deterministically."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("Today", today)
        assert result is not None
        assert result["departure_date"] == today

    def test_tonight_returns_today(self) -> None:
        """'tonight' resolves to today's date deterministically."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("tonight", today)
        assert result is not None
        assert result["departure_date"] == today

    def test_tomorrow_returns_next_day(self) -> None:
        """'tomorrow' resolves to reference_date + 1."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        expected = (utc_date() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = _try_deterministic_parse("tomorrow", today)
        assert result is not None
        assert result["departure_date"] == expected

    def test_now_for_1_night(self) -> None:
        """'Now for 1 night' — 1 night = 2 calendar days inclusive (today + checkout tomorrow)."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        tomorrow = (utc_date() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = _try_deterministic_parse("Now for 1 night", today)
        assert result is not None
        assert result["departure_date"] == today
        assert result["return_date"] == tomorrow
        assert result["is_range"] is True
        # 1 night stay → 2 calendar days inclusive (depart day + checkout day).
        # See duration convention in dates.py prompt.
        assert result["trip_duration_days"] == 2
        assert result["error"] is None

    def test_today_for_3_nights(self) -> None:
        """'today for 3 nights' = 4 calendar days inclusive."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        # 3 nights → checkout on day +3 → 4 calendar days inclusive.
        expected_return = (utc_date() + timedelta(days=3)).strftime("%Y-%m-%d")
        result = _try_deterministic_parse("today for 3 nights", today)
        assert result is not None
        assert result["departure_date"] == today
        assert result["return_date"] == expected_return
        assert result["trip_duration_days"] == 4

    def test_now_for_1_week(self) -> None:
        """'now for 1 week' = 7 calendar days inclusive (return = depart + 6)."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        # 1 week = 7 calendar days inclusive → return = depart + 6.
        expected_return = (utc_date() + timedelta(days=6)).strftime("%Y-%m-%d")
        result = _try_deterministic_parse("now for 1 week", today)
        assert result is not None
        assert result["return_date"] == expected_return
        assert result["trip_duration_days"] == 7

    def test_today_for_5_days(self) -> None:
        """Convention regression for #1105 — 'N days' = N calendar days inclusive."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        # 5 days inclusive → return = depart + 4 (today, +1, +2, +3, +4).
        expected_return = (utc_date() + timedelta(days=4)).strftime("%Y-%m-%d")
        result = _try_deterministic_parse("today for 5 days", today)
        assert result is not None
        assert result["return_date"] == expected_return
        assert result["trip_duration_days"] == 5

    def test_complex_expression_returns_none(self) -> None:
        """Complex expressions fall through to LLM (returns None)."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        assert _try_deterministic_parse("next Tuesday for a week", today) is None
        assert _try_deterministic_parse("December 15 to 20", today) is None
        assert _try_deterministic_parse("cherry blossom season", today) is None

    def test_now_without_duration(self) -> None:
        """'now' without duration has no return_date."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("now", today)
        assert result is not None
        assert result["return_date"] is None
        assert result["is_range"] is False
        assert result["trip_duration_days"] is None

    def test_iso_date_fast_path(self) -> None:
        """Already-parsed ISO date (YYYY-MM-DD) returns immediately, no LLM."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("2026-04-10", today)
        assert result is not None
        assert result["departure_date"] == "2026-04-10"
        assert result["return_date"] is None
        assert result["is_range"] is False
        assert result["trip_duration_days"] is None
        assert result["error"] is None
        assert "instruction" in result

    def test_iso_date_fast_path_with_whitespace(self) -> None:
        """ISO date with leading/trailing whitespace is still fast-pathed."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        result = _try_deterministic_parse("  2026-12-25  ", today)
        assert result is not None
        assert result["departure_date"] == "2026-12-25"

    def test_iso_like_partial_not_fast_pathed(self) -> None:
        """Date-like strings that aren't full ISO (e.g. 'Dec 25') fall through."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        today = utc_date().strftime("%Y-%m-%d")
        # Not ISO format — should return None (falls through to LLM)
        assert _try_deterministic_parse("2026-04", today) is None
        assert _try_deterministic_parse("04-10", today) is None


class TestDeterministicQuarterParse:
    """Tests for quarter parsing in _try_deterministic_parse."""

    def test_q3_mid_quarter_uses_current_year(self) -> None:
        from app.ai.graph.tools.dates import _try_deterministic_parse

        result = _try_deterministic_parse("Q3", "2026-08-15")
        assert result is not None
        assert result["departure_date"] is None
        assert result["return_date"] is None
        assert "July-September" in result["instruction"]
        assert "Q3 2026" in result["instruction"]

    def test_q1_in_q4_uses_next_year(self) -> None:
        from app.ai.graph.tools.dates import _try_deterministic_parse

        result = _try_deterministic_parse("Q1", "2026-11-01")
        assert result is not None
        assert "Q1 2027" in result["instruction"]
        assert "January-March" in result["instruction"]

    def test_q3_explicit_year(self) -> None:
        from app.ai.graph.tools.dates import _try_deterministic_parse

        result = _try_deterministic_parse("Q3 2027", "2026-04-23")
        assert result is not None
        assert "Q3 2027" in result["instruction"]
        assert "July-September" in result["instruction"]

    def test_q1_lowercase(self) -> None:
        from app.ai.graph.tools.dates import _try_deterministic_parse

        result = _try_deterministic_parse("q1", "2026-01-15")
        assert result is not None
        assert "Q1 2026" in result["instruction"]

    def test_q3_review_falls_through(self) -> None:
        """'Q3 review' is not a pure quarter expression — should return None."""
        from app.ai.graph.tools.dates import _try_deterministic_parse

        result = _try_deterministic_parse("Q3 review", "2026-04-23")
        assert result is None


class TestValidateParsedDates:
    """Tests for _validate_parsed_dates deterministic validation."""

    def test_past_departure_date_auto_rolls(self) -> None:
        """Past departure dates are auto-rolled to next year."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        past_date = (utc_date() - timedelta(days=5)).strftime("%Y-%m-%d")
        result = _validate_parsed_dates(
            {
                "departure_date": past_date,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
            }
        )
        # Validator auto-rolls past dates to next year
        assert result["departure_date"] is not None
        rolled = datetime.strptime(result["departure_date"], "%Y-%m-%d").date()
        assert rolled >= utc_date()

    def test_return_before_departure_returns_error(self) -> None:
        """Return date before departure (same month) is caught and error is set."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        # Use explicit same-month dates to avoid year-spanning auto-roll
        dep = "2027-06-20"
        ret = "2027-06-15"
        result = _validate_parsed_dates(
            {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
            }
        )
        assert result["return_date"] is None
        assert result["error"] is not None
        assert "before" in result["error"].lower()
        assert result["departure_date"] == dep  # departure preserved

    def test_year_spanning_range_auto_rolls_return_year(self) -> None:
        """Year-spanning season (Nov-Apr) auto-rolls return to next year."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-11-01",
                "return_date": "2026-04-30",
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "_reference_date": "2026-04-20",
            }
        )
        assert result["return_date"] == "2027-04-30"
        assert result["departure_date"] == "2026-11-01"
        assert result["error"] is None

    def test_multi_year_past_date_rolling(self) -> None:
        """Past date that needs multiple rolls (2025 → 2026 still past → 2027)."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2025-01-05",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "_reference_date": "2026-04-20",
            }
        )
        assert result["departure_date"] == "2027-01-05"
        assert result["error"] is None

    def test_adjacent_month_reversal_not_auto_rolled(self) -> None:
        """Adjacent-month reversal (Nov→Oct) should error, not auto-roll."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-11-15",
                "return_date": "2026-10-01",
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "_reference_date": "2026-04-20",
            }
        )
        assert result["return_date"] is None
        assert result["error"] is not None
        assert "before" in result["error"].lower()

    def test_valid_dates_pass_through(self) -> None:
        """Valid future dates pass through without modification."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        dep = (utc_date() + timedelta(days=5)).strftime("%Y-%m-%d")
        ret = (utc_date() + timedelta(days=12)).strftime("%Y-%m-%d")
        result = _validate_parsed_dates(
            {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": 7,
                "error": None,
            }
        )
        assert result["departure_date"] == dep
        assert result["return_date"] == ret
        assert result["error"] is None

    def test_today_departure_passes(self) -> None:
        """Today's date as departure is allowed (not past)."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        today = utc_date().strftime("%Y-%m-%d")
        result = _validate_parsed_dates(
            {
                "departure_date": today,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
            }
        )
        assert result["departure_date"] == today
        assert result["error"] is None

    def test_yesterday_departure_today_return_shifts_to_today(self) -> None:
        """Yesterday departure + today return should shift departure to today (>= fix)."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        yesterday = (utc_date() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = utc_date().strftime("%Y-%m-%d")
        result = _validate_parsed_dates(
            {
                "departure_date": yesterday,
                "return_date": today,
                "is_range": True,
                "trip_duration_days": 1,
                "error": None,
            }
        )
        # Should auto-correct departure to today, NOT return an error
        assert result["departure_date"] == today
        assert result["error"] is None


class TestValidateParsedDatesStateAware:
    """Regression tests for state-aware swap/preserve/no-op branches (#1014).

    `_existing_departure` is a hidden context key set by `parse_dates` when the
    caller passes `departure_date`. The validator interprets a single parsed
    date relative to the existing departure:
      * strictly after  → swap to return (user provided a return date)
      * strictly before → preserve existing (likely an ambiguous LLM hallucination)
      * equal           → no-op (user restated existing date)
    """

    def test_swap_to_return_when_new_strictly_after_existing(self) -> None:
        """existing=May 18 + new=May 22 (no return) → swap to dep=May 18, ret=May 22."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-05-22",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "_existing_departure": "2026-05-18",
                "_reference_date": "2026-05-12",
            }
        )
        assert result["departure_date"] == "2026-05-18"
        assert result["return_date"] == "2026-05-22"
        assert result["is_range"] is True
        assert result["trip_duration_days"] == 4
        assert result["error"] is None
        assert "_existing_departure" not in result, "context key must be popped"

    def test_preserve_existing_when_new_before_existing(self) -> None:
        """existing=May 18 + new=May 15 (no return) → preserve existing + ambiguous error."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-05-15",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "_existing_departure": "2026-05-18",
                "_reference_date": "2026-05-12",
            }
        )
        assert result["departure_date"] == "2026-05-18", (
            "existing departure must be preserved"
        )
        assert result["return_date"] is None
        assert result["error"] is not None
        assert "before" in result["error"].lower()
        assert "departure" in result["instruction"].lower()
        assert "2026-05-18" in result["instruction"], "instruction quotes existing"
        assert "_existing_departure" not in result

    def test_no_op_when_new_equals_existing(self) -> None:
        """existing=May 18 + new=May 18 → no swap, no error (user restating)."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-05-18",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "_existing_departure": "2026-05-18",
                "_reference_date": "2026-05-12",
            }
        )
        assert result["departure_date"] == "2026-05-18"
        assert result["return_date"] is None
        assert result["error"] is None

    def test_swap_skipped_when_parsed_already_has_return(self) -> None:
        """If LLM already returned both dep+ret (a range), swap logic must not fire."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": "2026-05-15",
                "return_date": "2026-06-05",
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "_existing_departure": "2026-05-18",
                "_reference_date": "2026-05-12",
            }
        )
        # Both dates must pass through unchanged — this is "15 may to 5 june"
        # after agent had proposed May 18: user is replacing the range entirely.
        assert result["departure_date"] == "2026-05-15"
        assert result["return_date"] == "2026-06-05"
        assert result["error"] is None

    def test_context_aware_error_when_parse_fails_with_existing(self) -> None:
        """error AND no departure AND existing_dep set → instruction quotes existing."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": "Could not parse 'qwerty'",
                "_existing_departure": "2026-05-18",
                "_reference_date": "2026-05-12",
            }
        )
        instr = result["instruction"]
        assert "2026-05-18" in instr, "instruction must quote existing departure"
        assert "before" in instr.lower(), "instruction must forbid earlier suggestions"

    def test_generic_error_when_no_existing_context(self) -> None:
        """error without existing_dep → keep original generic instruction."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": "Could not parse 'qwerty'",
                "_reference_date": "2026-05-12",
            }
        )
        # No _existing_departure → context-aware branch should be skipped
        # (the result["instruction"] is set by the caller, not the validator,
        # in this code path — just confirm validator didn't override it)
        assert result.get("error") is not None


class TestParseDatesAfterXDaysReferenceShift:
    """Regression test for the reference_date narrowing behavior (#1014).

    `parse_dates(text, departure_date)` historically used `departure_date` as
    the LLM `reference_date`, which caused "May 15" said after an existing
    May 18 departure to auto-roll to 2027-05-15 (a 361-day trip). The fix
    reserves that behavior strictly for the "after X days/weeks/months"
    idiom — everything else uses today as the reference.
    """

    @pytest.mark.asyncio
    async def test_after_n_days_still_uses_existing_as_reference(self) -> None:
        """'after 3 days' MUST pass existing_dep as ref so LLM computes dep+3."""
        from app.ai.graph.tools.dates import parse_dates

        existing = "2026-05-18"
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": "2026-05-21",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "after 3 days",
            }
            await parse_dates.ainvoke(
                {"text": "after 3 days", "departure_date": existing}
            )
            # Inspect the reference_date that parse_dates passed to the LLM helper
            _, args, _ = mock.mock_calls[0]
            ref_arg = (
                args[1]
                if len(args) > 1
                else mock.call_args.kwargs.get("reference_date")
            )
            assert ref_arg == existing, (
                "after-X idiom must anchor LLM to existing departure"
            )

    @pytest.mark.asyncio
    async def test_plain_date_does_not_use_existing_as_reference(self) -> None:
        """A bare 'May 15' must NOT use existing_dep as ref — otherwise the LLM
        auto-rolls 2026-05-15 to 2027-05-15 when existing=2026-05-18."""
        from app.ai.graph.tools.dates import parse_dates

        existing = "2026-05-18"
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": "2026-05-15",
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "May 15",
            }
            await parse_dates.ainvoke({"text": "May 15", "departure_date": existing})
            _, args, _ = mock.mock_calls[0]
            ref_arg = (
                args[1]
                if len(args) > 1
                else mock.call_args.kwargs.get("reference_date")
            )
            assert ref_arg is None, "plain dates must anchor to today, not existing_dep"


class TestHasExplicitDateAnchorInNUnits:
    """Regression for the 'in N units' regex anchor (#1014)."""

    def test_in_n_weeks_matches(self) -> None:
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in 2 weeks")
        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in a week")
        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in two weeks")

    def test_in_n_days_matches(self) -> None:
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in 3 days")
        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in ten days")

    def test_in_n_months_matches(self) -> None:
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in a month")
        assert _HAS_EXPLICIT_DATE_ANCHOR.search("in 2 months")

    def test_does_not_match_unrelated_in_phrases(self) -> None:
        """Pure-duration phrases without 'in' must NOT match this anchor."""
        from app.ai.graph.tools.dates import _HAS_EXPLICIT_DATE_ANCHOR

        # "for 2 weeks" is duration only — should not be a date anchor
        assert not _HAS_EXPLICIT_DATE_ANCHOR.search("for 2 weeks")
        # "5 days" is bare duration
        assert not _HAS_EXPLICIT_DATE_ANCHOR.search("5 days")
        # Non-time units after "in" should not match
        assert not _HAS_EXPLICIT_DATE_ANCHOR.search("in 3 hotels")


class TestParseDatesLLMResponseFormats:
    """Tests for parse_dates handling different LLM response content formats.

    Covers the use_responses_api=True fix where gpt-5.x returns non-empty
    structured output correctly instead of empty/null values.
    """

    @pytest.mark.asyncio
    async def test_date_range_without_year_resolves_correctly(self) -> None:
        """'April 1 to 10' without year should resolve using current/next year.

        Use future dates derived from ``utc_date()`` so ``_validate_parsed_dates`` does not
        shift a past departure to today (hardcoded April dates fail when CI runs after that
        window in the same month).
        """
        from app.ai.graph.tools.dates import parse_dates

        dep_date = utc_date() + timedelta(days=30)
        ret_date = dep_date + timedelta(days=9)  # same span as 1st–10th of a month
        dep = dep_date.strftime("%Y-%m-%d")
        ret = ret_date.strftime("%Y-%m-%d")

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": dep,
                "return_date": ret,
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "May 1 to 10",
                "instruction": "Dates parsed successfully. Proceed with the search.",
            }
            result = await parse_dates.ainvoke({"text": "April 1 to 10"})
            assert result["departure_date"] == dep
            assert result["return_date"] == ret
            assert result["error"] is None
            assert (
                result["instruction"]
                == "Dates parsed successfully. Proceed with the search."
            )

    @pytest.mark.asyncio
    async def test_empty_text_returns_error_not_exception(self) -> None:
        """Empty text should return a graceful error dict, not raise."""
        from app.ai.graph.tools.dates import parse_dates

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": "No date expression provided to parse.",
                "parsed_from": "",
                "instruction": "Inform the user about the date parsing error and ask for clarification.",
            }
            result = await parse_dates.ainvoke({"text": ""})
            assert result["departure_date"] is None
            assert result["error"] is not None
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_llm_returning_null_values_propagates_error(self) -> None:
        """If LLM returns all nulls (empty content bug), error is set and instruction is present."""
        from app.ai.graph.tools.dates import parse_dates

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            # Simulates what happens without use_responses_api=True — all nulls
            mock.return_value = {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": "No date expression was provided to parse.",
                "parsed_from": "April 1 to 10",
                "instruction": "Inform the user about the date parsing error and ask for clarification.",
            }
            result = await parse_dates.ainvoke({"text": "April 1 to 10"})
            # Should propagate error, not crash
            assert result["departure_date"] is None
            assert result["error"] is not None
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_destination_passed_to_llm(self) -> None:
        """Destination parameter is forwarded to _parse_dates_with_llm."""
        from app.ai.graph.tools.dates import parse_dates

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": "2026-04-01",
                "return_date": "2026-04-10",
                "is_range": True,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "April 1 to 10",
                "instruction": "Dates parsed successfully. Proceed with the search.",
            }
            await parse_dates.ainvoke(
                {"text": "cherry blossom season", "destination": "Tokyo"}
            )
            call_kwargs = mock.call_args
            assert call_kwargs[1].get("destination") == "Tokyo"


class TestInstructionFieldPresence:
    """Tests that all tool returns include the instruction field."""

    @pytest.mark.asyncio
    async def test_parse_dates_success_has_instruction(self) -> None:
        """parse_dates success result includes instruction."""
        from app.ai.graph.tools.dates import parse_dates

        future = (utc_date() + timedelta(days=3)).strftime("%Y-%m-%d")
        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock:
            mock.return_value = {
                "departure_date": future,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "parsed_from": "in 3 days",
                "instruction": "Dates parsed successfully. Proceed with the search.",
            }
            result = await parse_dates.ainvoke({"text": "in 3 days"})
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_resolve_airport_resolved_has_instruction(self) -> None:
        """resolve_airport resolved result includes instruction."""
        from app.ai.graph.tools.airport import resolve_airport

        resolved_result = {
            "status": "resolved",
            "iata": "LHR",
            "name": "Heathrow",
            "city": "London",
            "country": "UK",
            "query_is_city_name": False,
            "instruction": "Airport resolved: LHR (Heathrow). Proceed with this airport code.",
        }

        with (
            patch(
                "app.ai.graph.tools.airport._resolve_via_mwgg",
                return_value=resolved_result,
            ),
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS = False
            result = await resolve_airport.ainvoke({"query": "LHR"})
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_resolve_via_flightlogic_fetches_coordinates_from_mwgg(self) -> None:
        """_resolve_via_flightlogic falls back to mwgg resolver for coordinates.

        FlightLogic API does not return lat/lon, so the function must use
        airport_resolver.get_airport_info to populate coordinates.
        This test would have caught the AttributeError bug where get_airport_service()
        (which returns AirportService) was used instead of airport_resolver.
        """
        from app.ai.graph.tools.airport import _resolve_via_flightlogic

        mock_mwgg_info = {"lat": 51.4775, "lon": -0.4614}

        mock_flight_service = MagicMock()
        mock_flight_service.resolve_airport = AsyncMock(return_value="LHR")
        mock_flight_service.get_airport_info = AsyncMock(
            return_value={
                "name": "London Heathrow Airport",
                "city": "London",
                "country": "GB",
            }
        )

        mock_resolver = MagicMock()
        mock_resolver.ensure_loaded = AsyncMock()
        mock_resolver.get_airport_info = AsyncMock(return_value=mock_mwgg_info)

        with (
            patch(
                "app.domains.flight.service.FlightService",
                return_value=mock_flight_service,
            ),
            patch(
                "app.domains.airport.airport_resolver.airport_resolver",
                mock_resolver,
            ),
        ):
            result = await _resolve_via_flightlogic("LHR")

        assert result["status"] == "resolved"
        assert result["iata"] == "LHR"
        assert result["lat"] == 51.4775
        assert result["lon"] == -0.4614
        # Verify mwgg resolver was used (not AirportService)
        mock_resolver.ensure_loaded.assert_awaited_once()
        mock_resolver.get_airport_info.assert_awaited_once_with("LHR")

    @pytest.mark.asyncio
    async def test_resolve_city_resolved_has_instruction(self) -> None:
        """resolve_city resolved result includes instruction."""
        from app.ai.graph.tools.city import resolve_city

        mock_geo_result = MagicMock(
            city="Paris",
            country="France",
            country_code="FR",
            lat=48.8566,
            lng=2.3522,
            formatted_address="Paris, France",
        )
        with patch("app.shared.geocoding.GeocodingService") as mock_svc:
            mock_svc.return_value.geocode_city = AsyncMock(
                return_value=[mock_geo_result]
            )
            result = await resolve_city.ainvoke({"query": "Paris"})
            assert "instruction" in result
            assert result["status"] == "resolved"


class TestNormalizeCityName:
    """Tests for _normalize_city_name: country stripping + diacritics removal."""

    def test_strips_diacritics(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("Cancún") == "Cancun"

    def test_strips_multiple_diacritics(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("São Paulo") == "Sao Paulo"

    def test_plain_ascii_unchanged(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("Tokyo") == "Tokyo"

    def test_strips_country_suffix(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("Cancún, Mexico") == "Cancun"

    def test_strips_country_and_diacritics(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("São Paulo, Brazil") == "Sao Paulo"

    def test_city_only_no_comma(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("Barcelona") == "Barcelona"

    def test_whitespace_handling(self) -> None:
        from app.ai.graph.tools.trip_info import _normalize_city_name

        assert _normalize_city_name("  Zürich , Switzerland  ") == "Zurich"


class TestUpdateTripInfoProceedCondition:
    """Tests for the destination + dates proceed signal in update_trip_info."""

    @pytest.mark.asyncio
    async def test_complete_when_destination_and_both_dates_present(self) -> None:
        """Status=complete when destination + departure_date + return_date are all present."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {"departure_date": "2026-04-01", "is_range": False},
                    {"departure_date": "2026-04-05", "is_range": False},
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "Tokyo",
                    "departure_date": "April 1",
                    "return_date": "April 5",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "complete"
            assert (
                "proceed" in result["instruction"].lower()
                or "generate" in result["instruction"].lower()
            )

    @pytest.mark.asyncio
    async def test_complete_without_iata_codes(self) -> None:
        """Status=complete even when IATA codes are absent — only destination + dates needed."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            # side_effect: distinct return per call so departure and return
            # parse to different dates (the post-#1014 guard rejects
            # return_date <= departure_date).
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {"departure_date": "2026-05-10", "is_range": False},
                    {"departure_date": "2026-05-15", "is_range": False},
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "Barcelona",
                    "departure_date": "May 10",
                    "return_date": "May 15",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "complete"
            assert "origin_iata" not in result

    @pytest.mark.asyncio
    async def test_success_when_destination_missing(self) -> None:
        """Status=success (not complete) when destination is missing."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {"departure_date": "2026-04-01", "is_range": False},
                    {"departure_date": "2026-04-05", "is_range": False},
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "departure_date": "April 1",
                    "return_date": "April 5",
                    "origin": "London",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "success"
            assert "missing" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_success_when_date_missing(self) -> None:
        """Status=success (not complete) when departure_date is missing."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        raw = await update_trip_info.ainvoke({"destination": "Paris"})
        result = json.loads(raw)
        assert result["status"] == "success"
        assert "missing" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_not_complete_with_departure_only(self) -> None:
        """Status=success (not complete) when only departure_date present, no return_date."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                return_value={"departure_date": "2026-06-01", "return_date": None}
            )
            raw = await update_trip_info.ainvoke(
                {"destination": "Tokyo", "departure_date": "June 1"}
            )
            result = json.loads(raw)
            assert result["status"] == "success"
            assert "return date or trip duration" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_complete_with_range_from_departure(self) -> None:
        """Status=complete when parse_dates returns both dates from a range expression."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                return_value={
                    "departure_date": "2026-05-10",
                    "return_date": "2026-05-17",
                    "is_range": True,
                }
            )
            raw = await update_trip_info.ainvoke(
                {"destination": "Rome", "departure_date": "May 10 for a week"}
            )
            result = json.loads(raw)
            assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_auto_derive_return_from_departure_plus_duration(self) -> None:
        """departure_date + trip_duration_days auto-derives return_date → status=complete."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                return_value={"departure_date": "2026-05-04", "return_date": None}
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "Bali",
                    "departure_date": "next Monday",
                    "trip_duration_days": 5,
                }
            )
            result = json.loads(raw)
            assert result["status"] == "complete"
            # Inclusive counting: 5-day trip from May 4 → May 4,5,6,7,8 → return May 8
            assert result["return_date"] == "2026-05-08"
            assert result["trip_duration_days"] == 5

    @pytest.mark.asyncio
    async def test_no_auto_derive_without_duration(self) -> None:
        """departure_date without trip_duration_days does NOT auto-derive return_date."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                return_value={"departure_date": "2026-05-04", "return_date": None}
            )
            raw = await update_trip_info.ainvoke(
                {"destination": "Bali", "departure_date": "next Monday"}
            )
            result = json.loads(raw)
            assert result["status"] == "success"
            assert "return date or trip duration" in result["instruction"].lower()


class TestUpdateTripInfoStateAware:
    """Regression tests for the state-aware update_trip_info paths (#1014)."""

    @pytest.mark.asyncio
    async def test_ambiguous_date_preserves_existing_departure(self) -> None:
        """parse_dates returns ambiguous error → status='ambiguous_date', dep preserved."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            # Simulate the state-aware validator's "preserve existing" response
            mock_parse.ainvoke = AsyncMock(
                return_value={
                    "departure_date": "2026-05-18",  # existing, preserved
                    "return_date": None,
                    "error": "Could not unambiguously parse '2026-05-15' lands "
                    "before the existing departure (2026-05-18).",
                    "instruction": "Ask the user explicitly: did you mean to "
                    "change the departure, or were you giving me the return?",
                }
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "New York City",
                    "departure_date": "15-5",
                    "existing_departure_date": "2026-05-18",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "ambiguous_date"
            assert result["departure_date"] == "2026-05-18", "existing preserved"
            assert "depart" in result["instruction"].lower()

    @pytest.mark.asyncio
    async def test_invalid_return_date_when_before_departure(self) -> None:
        """return_date <= departure_date → status='invalid_return_date', not stored."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            # First call processes departure_date="2026-05-18" (already ISO)
            # Second call processes return_date="2026-05-15" (the rescued-rejected date)
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {
                        "departure_date": "2026-05-18",
                        "return_date": None,
                        "is_range": False,
                    },
                    {
                        "departure_date": "2026-05-15",
                        "return_date": None,
                        "is_range": False,
                    },
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "New York City",
                    "departure_date": "2026-05-18",
                    "return_date": "2026-05-15",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "invalid_return_date"
            assert "after departure" in result["instruction"].lower()
            assert "2026-05-15" in result["instruction"]
            assert "2026-05-18" in result["instruction"]

    @pytest.mark.asyncio
    async def test_invalid_return_date_when_equal_to_departure(self) -> None:
        """return_date == departure_date is also invalid (zero-day trip)."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {
                        "departure_date": "2026-06-01",
                        "return_date": None,
                        "is_range": False,
                    },
                    {
                        "departure_date": "2026-06-01",
                        "return_date": None,
                        "is_range": False,
                    },
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "Paris",
                    "departure_date": "June 1",
                    "return_date": "June 1",
                }
            )
            result = json.loads(raw)
            assert result["status"] == "invalid_return_date"

    @pytest.mark.asyncio
    async def test_replacing_full_range_bypasses_existing_context(self) -> None:
        """Passing both new dep AND new return = explicit "change whole trip" — \
        existing_departure_date must NOT be forwarded to parse_dates for the dep parse,
        otherwise legitimate range changes ("15 may to 5 june") get rejected."""
        import json

        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                side_effect=[
                    {
                        "departure_date": "2026-05-15",
                        "return_date": None,
                        "is_range": False,
                    },
                    {
                        "departure_date": "2026-06-05",
                        "return_date": None,
                        "is_range": False,
                    },
                ]
            )
            raw = await update_trip_info.ainvoke(
                {
                    "destination": "New York City",
                    "departure_date": "2026-05-15",
                    "return_date": "2026-06-05",
                    "existing_departure_date": "2026-05-18",  # would normally reject!
                }
            )
            result = json.loads(raw)
            # Both new dates accepted — the dep parse must NOT have received the
            # existing context. Verify the first parse_dates call args:
            first_call_args = mock_parse.ainvoke.await_args_list[0].args[0]
            assert "departure_date" not in first_call_args, (
                "When return_date is also being set, existing_departure_date "
                "must NOT be forwarded to parse_dates for the dep parse"
            )
            assert result["status"] == "complete"
            assert result["departure_date"] == "2026-05-15"
            assert result["return_date"] == "2026-06-05"

    @pytest.mark.asyncio
    async def test_single_departure_uses_existing_context(self) -> None:
        """Passing departure_date alone (no return) DOES forward existing context."""
        from app.ai.graph.tools.trip_info import update_trip_info

        with patch("app.ai.graph.tools.dates.parse_dates") as mock_parse:
            mock_parse.ainvoke = AsyncMock(
                return_value={"departure_date": "2026-05-22", "return_date": None}
            )
            await update_trip_info.ainvoke(
                {
                    "destination": "New York City",
                    "departure_date": "May 22",
                    "existing_departure_date": "2026-05-18",
                }
            )
            # Verify existing context was forwarded
            call_args = mock_parse.ainvoke.await_args_list[0].args[0]
            assert call_args.get("departure_date") == "2026-05-18", (
                "Single-date update must forward existing_departure_date for "
                "state-aware swap/preserve to fire"
            )


class TestMulticityFlightSearch:
    """Tests for multicity (Circle) flight search via search_flights segments parameter."""

    def _make_leg_itinerary(
        self,
        seq: int,
        price: float,
        duration_min: int,
        origin_iata: str,
        dest_iata: str,
        airline_code: str = "BA",
        airline_name: str = "British Airways",
        flight_number: str = "BA100",
    ) -> MagicMock:
        """Build a minimal FareItinerary mock for multicity leg tests."""
        segment = MagicMock()
        segment.operating_airline = MagicMock(name=airline_name, iata_code=airline_code)
        segment.operating_flight_number = flight_number
        dep_str = "2026-06-01T08:00:00"
        arr_str = "2026-06-01T10:00:00"
        segment.departure_datetime = MagicMock()
        segment.departure_datetime.strftime = lambda fmt: (
            dep_str if ":" in fmt else "2026-06-01"
        )
        segment.arrival_datetime = MagicMock()
        segment.arrival_datetime.strftime = lambda fmt: (
            arr_str if ":" in fmt else "2026-06-01"
        )
        segment.flight_duration = MagicMock(total_minutes=duration_min)
        segment.departure_airport = MagicMock(iata_code=origin_iata)
        segment.arrival_airport = MagicMock(iata_code=dest_iata)

        leg = MagicMock()
        leg.flight_segments = [segment]
        leg.total_stops = 0
        leg.total_time_seconds = duration_min * 60

        original_price = price / (1 + 5 / 100)
        pricing = MagicMock()
        pricing.fare_source_code = f"FARE_{seq}"
        fare_totals = MagicMock()
        total_fare = MagicMock()
        total_fare.amount = price
        total_fare.currency = "GBP"
        fare_totals.total_fare = total_fare
        original_fare = MagicMock()
        original_fare.amount = original_price
        original_fare.currency = "GBP"
        fare_totals.original_total_fare = original_fare
        fare_totals.platform_fee_percentage = 5.0
        pricing.fare_totals = fare_totals

        itinerary = MagicMock()
        itinerary.pricing = pricing
        itinerary.flight_legs = [leg]
        itinerary.sequence_number = seq
        return itinerary

    @pytest.mark.asyncio
    async def test_multicity_happy_path_two_legs(self) -> None:
        """Multi-city search with 2 legs returns multicity_results with per-leg categories."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.ai.graph.tools.flights import _search_multicity

        leg0_itinerary = self._make_leg_itinerary(1, 200.0, 90, "LHR", "CDG")
        leg1_itinerary = self._make_leg_itinerary(2, 180.0, 120, "CDG", "FCO")

        mock_leg0 = MagicMock()
        mock_leg0.leg_index = 0
        mock_leg0.origin = "LHR"
        mock_leg0.destination = "CDG"
        mock_leg0.departure_date = date(2026, 6, 1)
        mock_leg0.session_id = "session_leg0"
        mock_leg0.fare_itineraries = [leg0_itinerary]
        mock_leg0.errors = None

        mock_leg1 = MagicMock()
        mock_leg1.leg_index = 1
        mock_leg1.origin = "CDG"
        mock_leg1.destination = "FCO"
        mock_leg1.departure_date = date(2026, 6, 8)
        mock_leg1.session_id = "session_leg1"
        mock_leg1.fare_itineraries = [leg1_itinerary]
        mock_leg1.errors = None

        mock_response = MagicMock()
        mock_response.multicity_legs = [mock_leg0, mock_leg1]

        mock_service = MagicMock()
        mock_service.search_flights = AsyncMock(return_value=mock_response)
        mock_service.revalidate_fare = _mock_revalidate_available()

        with patch(
            "app.domains.flight.service.FlightService", return_value=mock_service
        ):
            result = await _search_multicity(
                segments_input=[
                    {
                        "origin": "LHR",
                        "destination": "CDG",
                        "departure_date": "2026-06-01",
                    },
                    {
                        "origin": "CDG",
                        "destination": "FCO",
                        "departure_date": "2026-06-08",
                    },
                ],
                adults=1,
                children=0,
                infants=0,
                cabin_class=None,
            )

        assert result["status"] == "multicity_results"
        legs = result["multicity_legs"]
        assert len(legs) == 2
        assert legs[0]["origin"] == "LHR"
        assert legs[0]["destination"] == "CDG"
        assert legs[1]["origin"] == "CDG"
        assert legs[1]["destination"] == "FCO"
        # Issue #1034: per-leg categories are gone — each leg ships a flat
        # `flights` list (best-value-sorted) instead.
        for leg in legs:
            assert "categories" not in leg
            assert "flights" in leg
            assert isinstance(leg["flights"], list)
            assert len(leg["flights"]) >= 1
        assert "instruction" in result

    @pytest.mark.asyncio
    async def test_multicity_invalid_iata_returns_error(self) -> None:
        """Invalid IATA code in segment returns error status without calling service."""
        from app.ai.graph.tools.flights import _search_multicity

        result = await _search_multicity(
            segments_input=[
                {
                    "origin": "INVALID",
                    "destination": "CDG",
                    "departure_date": "2026-06-01",
                },
                {
                    "origin": "CDG",
                    "destination": "LHR",
                    "departure_date": "2026-06-08",
                },
            ],
            adults=1,
            children=0,
            infants=0,
            cabin_class=None,
        )

        assert result["status"] == "error"
        assert "IATA" in result["error"] or "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_multicity_bad_date_format_returns_error(self) -> None:
        """Bad departure_date format in segment returns error status."""
        from app.ai.graph.tools.flights import _search_multicity

        result = await _search_multicity(
            segments_input=[
                {"origin": "LHR", "destination": "CDG", "departure_date": "01/06/2026"},
                {"origin": "CDG", "destination": "FCO", "departure_date": "2026-06-08"},
            ],
            adults=1,
            children=0,
            infants=0,
            cabin_class=None,
        )

        assert result["status"] == "error"
        assert "departure_date" in result["error"] or "YYYY-MM-DD" in result["error"]

    @pytest.mark.asyncio
    async def test_multicity_no_flights_leg_included_with_empty_categories(
        self,
    ) -> None:
        """A leg with no fare_itineraries is included with empty categories, not dropped."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.ai.graph.tools.flights import _search_multicity

        leg0_itinerary = self._make_leg_itinerary(1, 200.0, 90, "LHR", "CDG")

        mock_leg0 = MagicMock()
        mock_leg0.leg_index = 0
        mock_leg0.origin = "LHR"
        mock_leg0.destination = "CDG"
        mock_leg0.departure_date = date(2026, 6, 1)
        mock_leg0.session_id = "session_leg0"
        mock_leg0.fare_itineraries = [leg0_itinerary]
        mock_leg0.errors = None

        mock_leg1 = MagicMock()  # Empty leg
        mock_leg1.leg_index = 1
        mock_leg1.origin = "CDG"
        mock_leg1.destination = "FCO"
        mock_leg1.departure_date = date(2026, 6, 8)
        mock_leg1.session_id = ""
        mock_leg1.fare_itineraries = []
        mock_leg1.errors = None

        mock_response = MagicMock()
        mock_response.multicity_legs = [mock_leg0, mock_leg1]

        mock_service = MagicMock()
        mock_service.search_flights = AsyncMock(return_value=mock_response)
        mock_service.revalidate_fare = _mock_revalidate_available()

        with patch(
            "app.domains.flight.service.FlightService", return_value=mock_service
        ):
            result = await _search_multicity(
                segments_input=[
                    {
                        "origin": "LHR",
                        "destination": "CDG",
                        "departure_date": "2026-06-01",
                    },
                    {
                        "origin": "CDG",
                        "destination": "FCO",
                        "departure_date": "2026-06-08",
                    },
                ],
                adults=1,
                children=0,
                infants=0,
                cabin_class=None,
            )

        # Leg 0 has results, so overall status is not no_results
        assert result["status"] == "multicity_results"
        legs = result["multicity_legs"]
        assert len(legs) == 2
        # Issue #1034: leg 1 has an empty `flights` list (no more categories),
        # but the leg dict is still present so the FE can render an empty state.
        leg1 = next(lg for lg in legs if lg["leg_index"] == 1)
        assert leg1.get("flights", []) == []
        assert leg1["summary"]["total_flights"] == 0

    @pytest.mark.asyncio
    async def test_multicity_search_params_shape(self) -> None:
        """Returned search_params contains journey_type=Circle and passenger counts."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.ai.graph.tools.flights import _search_multicity

        leg0_itinerary = self._make_leg_itinerary(1, 200.0, 90, "LHR", "CDG")

        mock_leg0 = MagicMock()
        mock_leg0.leg_index = 0
        mock_leg0.origin = "LHR"
        mock_leg0.destination = "CDG"
        mock_leg0.departure_date = date(2026, 6, 1)
        mock_leg0.session_id = "s0"
        mock_leg0.fare_itineraries = [leg0_itinerary]
        mock_leg0.errors = None

        leg1_itinerary = self._make_leg_itinerary(2, 150.0, 120, "CDG", "FCO")
        mock_leg1 = MagicMock()
        mock_leg1.leg_index = 1
        mock_leg1.origin = "CDG"
        mock_leg1.destination = "FCO"
        mock_leg1.departure_date = date(2026, 6, 8)
        mock_leg1.session_id = "s1"
        mock_leg1.fare_itineraries = [leg1_itinerary]
        mock_leg1.errors = None

        mock_response = MagicMock()
        mock_response.multicity_legs = [mock_leg0, mock_leg1]

        mock_service = MagicMock()
        mock_service.search_flights = AsyncMock(return_value=mock_response)
        mock_service.revalidate_fare = _mock_revalidate_available()

        with patch(
            "app.domains.flight.service.FlightService", return_value=mock_service
        ):
            result = await _search_multicity(
                segments_input=[
                    {
                        "origin": "LHR",
                        "destination": "CDG",
                        "departure_date": "2026-06-01",
                    },
                    {
                        "origin": "CDG",
                        "destination": "FCO",
                        "departure_date": "2026-06-08",
                    },
                ],
                adults=2,
                children=1,
                infants=0,
                cabin_class=None,
            )

        assert result["status"] == "multicity_results"
        sp = result["search_params"]
        assert sp["journey_type"] == "Circle"
        assert sp["adults"] == 2
        assert sp["children"] == 1
        assert sp["infants"] == 0
        assert sp["cabin_class"] == "Economy"

    def test_extract_multicity_flight_search_results_happy_path(self) -> None:
        """Extractor returns data dict with multicity_parallel=True and legs.

        Issue #1034: the extractor reads from ``msg.artifact``, so fixtures
        must set ``artifact=`` with the full payload (search_params +
        multicity_legs[*].flights). ``content`` is slim summary-only.
        """
        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_multicity_flight_search_results

        artifact_payload = {
            "status": "multicity_results",
            "search_params": {
                "journey_type": "Circle",
                "adults": 1,
                "children": 0,
                "infants": 0,
                "cabin_class": "Economy",
            },
            "multicity_legs": [
                {
                    "leg_index": 0,
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-06-01",
                    "session_id": "s0",
                    "summary": {"total_found": 5},
                    "flights": [],
                }
            ],
        }
        slim_content = {
            "status": "multicity_results",
            "instruction": "Present the multi-city options to the user.",
        }
        msg = ToolMessage(
            content=json.dumps(slim_content),
            name="search_flights",
            tool_call_id="tc1",
            artifact=artifact_payload,
        )
        result = _extract_multicity_flight_search_results([msg])

        assert result is not None
        assert result["data"]["multicity_parallel"] is True
        assert len(result["data"]["multicity_legs"]) == 1
        assert result["data"]["multicity_legs"][0]["origin"] == "LHR"
        assert result["data"]["search_params"]["journey_type"] == "Circle"

    def test_extract_multicity_skips_non_multicity_status(self) -> None:
        """Extractor returns None when search_flights status is 'success' (OW/RT)."""
        import json

        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_multicity_flight_search_results

        tool_result = {"status": "success", "categories": {}, "session_id": "s1"}
        msg = ToolMessage(
            content=json.dumps(tool_result), name="search_flights", tool_call_id="tc2"
        )
        result = _extract_multicity_flight_search_results([msg])

        assert result is None


class TestDateRangeFlightSearch:
    """Tests for date-range flight search (Issue #634).

    Covers: _split_into_chunks, parallel date-range search,
    _aggregate_date_range_results, and single-date regression.
    """

    # ── _split_into_chunks tests ───────────────────────────────────────

    def test_split_into_chunks_small_range(self) -> None:
        """A 4-day window fits in one chunk."""
        from app.ai.graph.tools.dates import _split_into_chunks

        chunks = _split_into_chunks("2026-04-21", "2026-04-24", chunk_size=6)
        assert len(chunks) == 1
        assert chunks[0] == [
            "2026-04-21",
            "2026-04-22",
            "2026-04-23",
            "2026-04-24",
        ]

    def test_split_into_chunks_large_range(self) -> None:
        """A 20-day window splits into chunks of 6, 6, 6, 2."""
        from app.ai.graph.tools.dates import _split_into_chunks

        # Apr 15 to May 4 = 20 days
        chunks = _split_into_chunks("2026-04-15", "2026-05-04", chunk_size=6)
        assert len(chunks) == 4
        assert len(chunks[0]) == 6  # Apr 15-20
        assert len(chunks[1]) == 6  # Apr 21-26
        assert len(chunks[2]) == 6  # Apr 27 - May 2
        assert len(chunks[3]) == 2  # May 3-4
        assert chunks[0][0] == "2026-04-15"
        assert chunks[-1][-1] == "2026-05-04"

    def test_split_into_chunks_exact_six(self) -> None:
        """Exactly 6 days → single chunk."""
        from app.ai.graph.tools.dates import _split_into_chunks

        chunks = _split_into_chunks("2026-04-15", "2026-04-20", chunk_size=6)
        assert len(chunks) == 1
        assert len(chunks[0]) == 6

    def test_split_into_chunks_single_day(self) -> None:
        """Single day → single chunk with 1 date."""
        from app.ai.graph.tools.dates import _split_into_chunks

        chunks = _split_into_chunks("2026-04-15", "2026-04-15", chunk_size=6)
        assert len(chunks) == 1
        assert chunks[0] == ["2026-04-15"]

    # ── parse_dates departure window test ──────────────────────────────

    @pytest.mark.asyncio
    async def test_parse_dates_returns_departure_window(self) -> None:
        """LLM returns is_departure_window=True for 'after Dec 10, before Dec 16'."""
        from app.ai.graph.tools.dates import parse_dates

        with patch("app.ai.graph.tools.dates._parse_dates_with_llm") as mock_parse:
            mock_parse.return_value = {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": "2026-12-11",
                "departure_window_end": "2026-12-15",
                "is_departure_window": True,
                "parsed_from": "after December 10, before December 16",
            }

            result = await parse_dates.ainvoke(
                {"text": "after December 10, before December 16"}
            )

            assert result["is_departure_window"] is True
            assert result["departure_window_start"] == "2026-12-11"
            assert result["departure_window_end"] == "2026-12-15"
            assert result["departure_date"] is None
            assert "instruction" in result

    # ── _aggregate_date_range_results tests ────────────────────────────

    def _make_date_result(
        self,
        date_str: str,
        price: float,
        duration_minutes: int,
        airline: str = "BA",
        session_id: str = "sess-1",
    ) -> dict:
        """Build a per-date result dict matching _search_single_date output.

        Issue #1034: per-date result carries a flat best-value-sorted
        ``flights`` list (not categories). The aggregator picks the lowest
        ``best_value_score`` across each date's first flight as the
        overall winner.
        """
        flight = {
            "price": price,
            "duration_minutes": duration_minutes,
            "airline": airline,
            "best_value_score": price * 0.6 + duration_minutes * 0.4,
        }
        return {
            "date": date_str,
            "available": True,
            "session_id": session_id,
            "flights": [flight],
            "summary": {},
        }

    def test_aggregate_highlights_overall_cheapest(self) -> None:
        """overall_best is the single flight with the lowest best_value_score.

        Issue #1034: aggregator returns ``overall_best`` (single dict) rather
        than ``overall.{cheapest,fastest,best_value}`` buckets.
        """
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        results = [
            self._make_date_result("2026-04-21", price=300, duration_minutes=150),
            self._make_date_result("2026-04-22", price=200, duration_minutes=180),
            self._make_date_result("2026-04-23", price=250, duration_minutes=120),
        ]
        dates = ["2026-04-21", "2026-04-22", "2026-04-23"]

        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-23")

        assert agg["status"] == "date_range_results"
        # best_value_score: 300*0.6+150*0.4=240, 200*0.6+180*0.4=192,
        # 250*0.6+120*0.4=198 → April 22 wins.
        assert agg["overall_best"]["price"] == 200
        assert agg["overall_best"]["date"] == "2026-04-22"

    def test_aggregate_handles_partial_failure(self) -> None:
        """Some dates unavailable → those marked available=False, rest shown.

        Only the surviving date contributes to ``overall_best``.
        """
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        results: list[dict | BaseException] = [
            self._make_date_result("2026-04-21", price=300, duration_minutes=150),
            {"date": "2026-04-22", "available": False},
            RuntimeError("API timeout"),
        ]
        dates = ["2026-04-21", "2026-04-22", "2026-04-23"]

        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-23")

        assert agg["status"] == "date_range_results"
        available = [d for d in agg["dates"] if d.get("available")]
        unavailable = [d for d in agg["dates"] if not d.get("available")]
        assert len(available) == 1
        assert len(unavailable) == 2
        assert agg["overall_best"]["price"] == 300
        assert agg["overall_best"]["date"] == "2026-04-21"

    def test_aggregate_all_unavailable(self) -> None:
        """All dates fail → date_range_no_results status."""
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        results: list[dict | BaseException] = [
            {"date": "2026-04-21", "available": False},
            {"date": "2026-04-22", "available": False},
        ]
        dates = ["2026-04-21", "2026-04-22"]

        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-22")

        assert agg["status"] == "date_range_no_results"
        assert agg["has_more"] is False

    def test_no_more_chunks_when_window_fits(self) -> None:
        """Window ≤ 6 days → has_more=False."""
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        results = [
            self._make_date_result("2026-04-21", price=300, duration_minutes=150),
        ]
        dates = ["2026-04-21"]

        # window_end == last searched date → no more
        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-21")

        assert agg["has_more"] is False
        assert agg["next_chunk_start"] is None

    def test_has_more_chunks_when_window_extends(self) -> None:
        """departure_window_end beyond current chunk → has_more=True, next_chunk set."""
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        dates = ["2026-04-15", "2026-04-16", "2026-04-17"]
        results = [
            self._make_date_result(d, price=300, duration_minutes=150) for d in dates
        ]

        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-30")

        assert agg["has_more"] is True
        assert agg["next_chunk_start"] == "2026-04-18"
        assert agg["next_chunk_end"] is not None
        # Next chunk should not exceed window_end
        assert agg["next_chunk_end"] <= "2026-04-30"

    def test_all_unavailable_with_more_chunks(self) -> None:
        """All dates fail but window extends → has_more=True."""
        from app.ai.graph.tools.flights import _aggregate_date_range_results

        dates = ["2026-04-15", "2026-04-16"]
        results: list[dict | BaseException] = [
            {"date": "2026-04-15", "available": False},
            {"date": "2026-04-16", "available": False},
        ]

        agg = _aggregate_date_range_results(dates, results, window_end="2026-04-30")

        assert agg["status"] == "date_range_no_results"
        assert agg["has_more"] is True
        assert agg["next_chunk_start"] == "2026-04-17"

    # ── Parallel search via search_flights ─────────────────────────────

    @pytest.mark.asyncio
    async def test_search_flights_date_range_runs_parallel(self) -> None:
        """departure_dates=[4 dates] triggers parallel search via _search_date_range.

        Issue #1034: ``_search_single_date`` calls ``_do_flight_search``
        directly (the internal helper that returns the full unsplit dict).
        Mock that, returning the new flat-list shape.
        """
        mock_single_result = {
            "status": "success",
            "session_id": "sess-1",
            "flights": [
                {
                    "price": 200,
                    "duration_minutes": 120,
                    "airline": "BA",
                    "best_value_score": 168,
                }
            ],
            "summary": {},
        }

        with patch(
            "app.ai.graph.tools.flights._do_flight_search",
            new=AsyncMock(return_value=mock_single_result),
        ) as mock_do:
            from app.ai.graph.tools.flights import _search_date_range

            result = await _search_date_range(
                origin="LHR",
                destination="CDG",
                departure_dates=[
                    "2026-04-21",
                    "2026-04-22",
                    "2026-04-23",
                    "2026-04-24",
                ],
                departure_window_end="2026-04-24",
                adults=2,
                children=0,
                infants=0,
                origin_is_city=True,
                destination_is_city=True,
                departure_time_preference=None,
                arrival_time_preference=None,
                cabin_class=None,
                max_stops=None,
                price_min=None,
                price_max=None,
                preferred_airline=None,
                max_outbound_duration=None,
                max_inbound_duration=None,
            )

            assert result["status"] == "date_range_results"
            assert len(result["dates"]) == 4
            assert all(d["available"] for d in result["dates"])
            assert mock_do.await_count == 4

    # ── Regression: trip_type passed to _search_single_date ─────────────

    @pytest.mark.asyncio
    async def test_search_date_range_passes_trip_type_to_single_date(self) -> None:
        """Regression: _search_date_range must pass trip_type to _search_single_date.

        Bug: PR #633 made trip_type required on search_flights, but
        _search_date_range (PR #637) never passed it, causing silent failures.
        """
        with patch(
            "app.ai.graph.tools.flights._search_single_date",
            new_callable=AsyncMock,
        ) as mock_single:
            mock_single.return_value = {"date": "2026-05-01", "available": False}

            from app.ai.graph.tools.flights import _search_date_range

            await _search_date_range(
                origin="AMS",
                destination="FCO",
                departure_dates=["2026-05-01"],
                departure_window_end="2026-05-07",
                adults=2,
                children=0,
                infants=0,
                origin_is_city=True,
                destination_is_city=True,
                departure_time_preference=None,
                arrival_time_preference=None,
                cabin_class=None,
                max_stops=None,
                price_min=None,
                price_max=None,
                preferred_airline=None,
                max_outbound_duration=None,
                max_inbound_duration=None,
            )

            mock_single.assert_called_once()
            _, kwargs = mock_single.call_args
            assert kwargs["trip_type"] == "one-way"

    # ── Single-date regression ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_flights_single_date_unchanged(self) -> None:
        """Existing departure_date path still works (no regression)."""
        from app.ai.graph.tools.flights import search_flights

        with patch("app.domains.flight.service.FlightService") as mock_service_class:
            mock_service = MagicMock()
            mock_response = MagicMock()

            mock_segment = MagicMock()
            mock_segment.operating_airline = MagicMock(
                airline_name="Lufthansa", iata_code="LH"
            )
            mock_segment.operating_flight_number = MagicMock(formatted_number="LH456")
            mock_segment.departure_datetime = MagicMock()
            mock_segment.departure_datetime.strftime = lambda fmt: (
                "10:00" if fmt == "%H:%M" else "2026-06-15"
            )
            mock_segment.arrival_datetime = MagicMock()
            mock_segment.arrival_datetime.strftime = lambda fmt: (
                "12:30" if fmt == "%H:%M" else "2026-06-15"
            )
            mock_segment.flight_duration = MagicMock(total_minutes=150)
            mock_segment.departure_airport = MagicMock(iata_code="LHR")
            mock_segment.arrival_airport = MagicMock(iata_code="CDG")

            mock_leg = MagicMock()
            mock_leg.flight_segments = [mock_segment]
            mock_leg.total_stops = 0

            mock_itinerary = MagicMock()
            mock_pricing = MagicMock()
            mock_pricing.fare_source_code = "LHRCDG_SINGLE"
            mock_fare_totals = MagicMock()
            mock_total_fare = MagicMock()
            mock_total_fare.amount = 280.0
            mock_total_fare.currency = "GBP"
            mock_fare_totals.total_fare = mock_total_fare
            mock_pricing.fare_totals = mock_fare_totals
            mock_itinerary.pricing = mock_pricing
            mock_itinerary.flight_legs = [mock_leg]
            mock_itinerary.sequence_number = 1

            mock_response.fare_itineraries = [mock_itinerary]
            mock_response.errors = []
            mock_response.session_id = "fl-single-date-test"

            mock_service.search_flights = AsyncMock(return_value=mock_response)
            mock_service.revalidate_fare = _mock_revalidate_available()
            mock_service_class.return_value = mock_service

            result = await _invoke_flight_tool(
                search_flights,
                {
                    "origin": "LHR",
                    "destination": "CDG",
                    "departure_date": "2026-06-15",
                    "adults": 1,
                    "trip_type": "one-way",
                },
            )

            # Issue #1034: flat best-value-sorted list, no categories.
            assert result["status"] == "success"
            assert isinstance(result.get("flights"), list)
            assert result.get("session_id") == "fl-single-date-test"

    @pytest.mark.asyncio
    async def test_search_flights_rejects_both_date_params(self) -> None:
        """Providing both departure_date and departure_dates returns error."""
        from app.ai.graph.tools.flights import search_flights

        result = await search_flights.ainvoke(
            {
                "origin": "LHR",
                "destination": "CDG",
                "departure_date": "2026-04-21",
                "departure_dates": ["2026-04-21", "2026-04-22"],
                "adults": 1,
                "trip_type": "one-way",
            }
        )

        assert result.get("status") == "error"
        assert "not both" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_search_flights_rejects_no_date_params(self) -> None:
        """Providing neither departure_date nor departure_dates returns error."""
        from app.ai.graph.tools.flights import search_flights

        result = await search_flights.ainvoke(
            {
                "origin": "LHR",
                "destination": "CDG",
                "adults": 1,
                "trip_type": "one-way",
            }
        )

        assert result.get("status") == "error"
        assert "departure_date" in result["error"].lower()

    # ── _extract_flight_date_range_results tests ───────────────────────

    def test_extract_flight_date_range_results_happy_path(self) -> None:
        """ToolMessage with date_range_results status → returns correct dict.

        Issue #1034: the heavy payload lives on ``msg.artifact``;
        ``overall`` was replaced by a single ``overall_best`` flight.
        """
        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_flight_date_range_results

        artifact = {
            "status": "date_range_results",
            "dates": [
                {
                    "date": "2026-04-21",
                    "available": True,
                    "session_id": "s1",
                    "flights": [],
                },
                {"date": "2026-04-22", "available": False},
            ],
            "overall_best": {"price": 200, "date": "2026-04-21", "airline": "BA"},
            "searched_from": "2026-04-21",
            "searched_to": "2026-04-22",
            "has_more": False,
            "next_chunk_start": None,
            "next_chunk_end": None,
        }
        slim_content = {
            "status": "date_range_results",
            "instruction": "Present overall_best to the user.",
        }
        msg = ToolMessage(
            content=json.dumps(slim_content),
            tool_call_id="tc-1",
            name="search_flights",
            artifact=artifact,
        )

        result = _extract_flight_date_range_results([msg])

        assert result is not None
        assert result["searched_from"] == "2026-04-21"
        assert result["searched_to"] == "2026-04-22"
        assert len(result["dates"]) == 2
        # Extractor surfaces overall_best at the top level.
        assert result["overall_best"]["price"] == 200
        assert result["has_more"] is False
        assert result["next_chunk_start"] is None

    def test_extract_flight_date_range_results_wrong_status(self) -> None:
        """ToolMessage with 'success' status (not date_range_results) → returns None."""
        import json

        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_flight_date_range_results

        payload = {"status": "success", "categories": {}}
        msg = ToolMessage(
            content=json.dumps(payload), tool_call_id="tc-1", name="search_flights"
        )

        result = _extract_flight_date_range_results([msg])

        assert result is None

    def test_extract_flight_date_range_results_wrong_tool_name(self) -> None:
        """ToolMessage named 'parse_dates' → ignored, returns None."""
        import json

        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_flight_date_range_results

        payload = {
            "status": "date_range_results",
            "dates": [],
            "overall": {},
            "searched_from": "2026-04-21",
            "searched_to": "2026-04-24",
            "has_more": False,
        }
        msg = ToolMessage(
            content=json.dumps(payload), tool_call_id="tc-1", name="parse_dates"
        )

        result = _extract_flight_date_range_results([msg])

        assert result is None

    def test_extract_flight_date_range_results_uses_latest(self) -> None:
        """When multiple search_flights messages exist, uses the most recent one.

        Issue #1034: payload lives on ``msg.artifact``.
        """
        from langchain_core.messages import ToolMessage

        from app.ai.graph.flight_graph import _extract_flight_date_range_results

        slim_content = json.dumps(
            {
                "status": "date_range_results",
                "instruction": "Present overall_best.",
            }
        )
        old_msg = ToolMessage(
            content=slim_content,
            tool_call_id="tc-1",
            name="search_flights",
            artifact={
                "status": "date_range_results",
                "dates": [],
                "overall_best": None,
                "searched_from": "2026-04-10",
                "searched_to": "2026-04-15",
                "has_more": True,
            },
        )
        new_msg = ToolMessage(
            content=slim_content,
            tool_call_id="tc-2",
            name="search_flights",
            artifact={
                "status": "date_range_results",
                "dates": [],
                "overall_best": None,
                "searched_from": "2026-04-21",
                "searched_to": "2026-04-24",
                "has_more": False,
            },
        )

        # Reversed scan → new_msg is checked first
        result = _extract_flight_date_range_results([old_msg, new_msg])

        assert result is not None
        assert result["searched_from"] == "2026-04-21"
        assert result["has_more"] is False

    # ── _validate_parsed_dates departure window tests ──────────────────

    def test_validate_parsed_dates_window_fully_past(self) -> None:
        """Window entirely in the past → error returned, fields cleared."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": "2020-01-01",
                "departure_window_end": "2020-01-07",
                "is_departure_window": True,
                "parsed_from": "some old week",
            }
        )

        assert result["error"] is not None
        assert "past" in result["error"].lower()
        assert result["departure_window_start"] is None
        assert result["departure_window_end"] is None
        assert result["is_departure_window"] is False

    def test_validate_parsed_dates_window_end_before_start(self) -> None:
        """Window end before start → error returned."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": "2027-05-10",
                "departure_window_end": "2027-05-05",  # end before start
                "is_departure_window": True,
                "parsed_from": "invalid range",
            }
        )

        assert result["error"] is not None
        assert result["is_departure_window"] is False

    def test_validate_parsed_dates_valid_window_builds_instruction(self) -> None:
        """Valid future window → instruction contains first-chunk dates and departure_dates."""
        from app.ai.graph.tools.dates import _validate_parsed_dates

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": "2027-06-01",
                "departure_window_end": "2027-06-04",
                "is_departure_window": True,
                "parsed_from": "between June 1 and June 4",
            }
        )

        assert result.get("error") is None
        assert result["is_departure_window"] is True
        instruction = result["instruction"]
        # Instruction must reference departure dates and window bounds
        assert "departure" in instruction.lower()
        assert "2027-06-01" in instruction
        assert "2027-06-04" in instruction

    def test_validate_parsed_dates_window_clips_past_start(self) -> None:
        """Window start in past but end future → start clipped to today."""
        from datetime import timedelta

        from app.ai.graph.tools.dates import _validate_parsed_dates

        today = utc_date()
        past_start = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        future_end = (today + timedelta(days=4)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": past_start,
                "departure_window_end": future_end,
                "is_departure_window": True,
                "parsed_from": "partially past window",
            }
        )

        assert result.get("error") is None
        assert result["is_departure_window"] is True
        # Start should have been clipped to today
        assert result["departure_window_start"] == today_str

    def test_validate_parsed_dates_open_ended_window_auto_fills_end(self) -> None:
        """Open-ended window ('April 28 or after') auto-fills end to start + MAX - 1 days."""
        from app.ai.graph.tools.dates import (
            MAX_DEPARTURE_WINDOW_DAYS,
            _validate_parsed_dates,
        )

        today = utc_date()
        start_date = today + timedelta(days=30)
        start = start_date.strftime("%Y-%m-%d")
        expected_end = (
            start_date + timedelta(days=MAX_DEPARTURE_WINDOW_DAYS - 1)
        ).strftime("%Y-%m-%d")

        result = _validate_parsed_dates(
            {
                "departure_date": None,
                "return_date": None,
                "is_range": False,
                "trip_duration_days": None,
                "error": None,
                "departure_window_start": start,
                "departure_window_end": None,  # Open-ended — no end date given
                "is_departure_window": True,
                "parsed_from": "April 28 or after",
            }
        )

        assert result.get("error") is None
        assert result["is_departure_window"] is True
        assert result["departure_window_start"] == start
        assert result["departure_window_end"] == expected_end


# ========================
# TestFlSupportedAirportsCache
# ========================


class TestFlSupportedAirportsCache:
    """Tests for _get_fl_supported_airports() caching behaviour."""

    @pytest.mark.asyncio
    async def test_returns_set_of_iata_codes(self) -> None:
        """Successful fetch returns a non-empty set of uppercase IATA codes."""
        import app.ai.graph.tools.flights as flights_module
        from app.ai.graph.tools.flights import _get_fl_supported_airports

        mock_item = MagicMock()
        mock_item.iata_code = "lhr"  # lowercase — should be uppercased
        mock_response = MagicMock()
        mock_response.airports = [mock_item]

        # Reset cache so the fetch actually runs
        flights_module._fl_supported_airports_cache = set()
        flights_module._fl_supported_airports_fetched_at = 0.0

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_airport_list = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            codes = await _get_fl_supported_airports()

        assert isinstance(codes, set)
        assert "LHR" in codes

    @pytest.mark.asyncio
    async def test_caches_result_skips_second_fetch(self) -> None:
        """Second call within TTL returns cached set without calling FL again."""
        import time

        import app.ai.graph.tools.flights as flights_module
        from app.ai.graph.tools.flights import _get_fl_supported_airports

        # Pre-populate cache as if already fetched
        flights_module._fl_supported_airports_cache = {"ROC", "LHR"}
        flights_module._fl_supported_airports_fetched_at = time.monotonic()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_cls:
            codes = await _get_fl_supported_airports()
            mock_client_cls.assert_not_called()

        assert codes == {"ROC", "LHR"}

    @pytest.mark.asyncio
    async def test_returns_empty_set_on_fl_error(self) -> None:
        """When FL airport_list call fails, returns empty set (graceful fallback)."""
        import app.ai.graph.tools.flights as flights_module
        from app.ai.graph.tools.flights import _get_fl_supported_airports

        flights_module._fl_supported_airports_cache = set()
        flights_module._fl_supported_airports_fetched_at = 0.0

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_airport_list = AsyncMock(side_effect=Exception("FL down"))
            mock_client_cls.return_value = mock_client

            codes = await _get_fl_supported_airports()

        assert codes == set()


# ========================
# TestUnsupportedAirportHandler
# ========================


class TestUnsupportedAirportHandler:
    """Tests for the unsupported airport error path in search_flights."""

    _BUF_AIRPORTS_DATA: ClassVar[dict] = {
        "buf": {
            "iata": "BUF",
            "city": "Buffalo",
            "name": "Buffalo Niagara International Airport",
        }
    }

    def _make_error_response(self, message: str) -> MagicMock:
        mock_error = MagicMock()
        mock_error.message = message
        mock_error.code = "INVALID_AIRPORT"
        mock_response = MagicMock()
        mock_response.errors = [mock_error]
        mock_response.itineraries = []
        return mock_response

    def _make_mock_resolver(self, nearby: list[dict], airports_data: dict) -> MagicMock:
        """Build a mock AirportResolver with preset nearby + airports_data."""
        mock_resolver = MagicMock()
        mock_resolver.ensure_loaded = AsyncMock()
        mock_resolver.find_nearby_airports = AsyncMock(return_value=nearby)
        mock_resolver.airports_data = airports_data
        return mock_resolver

    @pytest.mark.asyncio
    async def test_shows_city_name_not_iata_code(self) -> None:
        """Error message uses city name (Buffalo) not raw IATA code (BUF)."""
        from app.ai.graph.tools.flights import search_flights

        mock_response = self._make_error_response(
            "Airport BUF is not supported by our search system."
        )
        mock_nearby = [{"iata": "ROC", "city": "Rochester", "distance_km": 88}]
        mock_resolver = self._make_mock_resolver(mock_nearby, self._BUF_AIRPORTS_DATA)

        with (
            patch("app.domains.flight.service.FlightService") as mock_svc_cls,
            patch(
                "app.ai.graph.tools.flights._get_fl_supported_airports",
                new=AsyncMock(return_value={"ROC", "LHR"}),
            ),
            patch(
                "app.domains.airport.airport_resolver.AirportResolver",
                return_value=mock_resolver,
            ),
        ):
            mock_svc = AsyncMock()
            mock_svc.search_flights = AsyncMock(return_value=mock_response)
            mock_svc_cls.return_value = mock_svc

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

        assert result["status"] == "unsupported_airport"
        instruction = result["instruction"]
        assert "Buffalo" in instruction  # city name shown
        assert "Rochester" in instruction  # alternative shown

    @pytest.mark.asyncio
    async def test_filters_nearby_by_fl_supported(self) -> None:
        """Nearby airports not in FL supported set are excluded from suggestions."""
        from app.ai.graph.tools.flights import search_flights

        mock_response = self._make_error_response("Airport BUF is not supported.")
        # Haversine returns IAG and ROC; FL only supports ROC
        mock_nearby = [
            {"iata": "IAG", "city": "Niagara Falls", "distance_km": 25},
            {"iata": "ROC", "city": "Rochester", "distance_km": 88},
        ]
        mock_resolver = self._make_mock_resolver(mock_nearby, self._BUF_AIRPORTS_DATA)

        with (
            patch("app.domains.flight.service.FlightService") as mock_svc_cls,
            patch(
                "app.ai.graph.tools.flights._get_fl_supported_airports",
                new=AsyncMock(return_value={"ROC", "LHR"}),  # IAG excluded
            ),
            patch(
                "app.domains.airport.airport_resolver.AirportResolver",
                return_value=mock_resolver,
            ),
        ):
            mock_svc = AsyncMock()
            mock_svc.search_flights = AsyncMock(return_value=mock_response)
            mock_svc_cls.return_value = mock_svc

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

        assert result["status"] == "unsupported_airport"
        instruction = result["instruction"]
        assert "Rochester" in instruction  # ROC kept
        assert "Niagara" not in instruction  # IAG filtered out

    @pytest.mark.asyncio
    async def test_shows_all_nearby_when_fl_list_unavailable(self) -> None:
        """When FL airport list fetch fails (empty set), all nearby airports shown."""
        from app.ai.graph.tools.flights import search_flights

        mock_response = self._make_error_response("Airport BUF is not supported.")
        mock_nearby = [
            {"iata": "IAG", "city": "Niagara Falls", "distance_km": 25},
            {"iata": "ROC", "city": "Rochester", "distance_km": 88},
        ]
        mock_resolver = self._make_mock_resolver(mock_nearby, self._BUF_AIRPORTS_DATA)

        with (
            patch("app.domains.flight.service.FlightService") as mock_svc_cls,
            patch(
                "app.ai.graph.tools.flights._get_fl_supported_airports",
                new=AsyncMock(return_value=set()),  # empty = FL unavailable
            ),
            patch(
                "app.domains.airport.airport_resolver.AirportResolver",
                return_value=mock_resolver,
            ),
        ):
            mock_svc = AsyncMock()
            mock_svc.search_flights = AsyncMock(return_value=mock_response)
            mock_svc_cls.return_value = mock_svc

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

        assert result["status"] == "unsupported_airport"
        instruction = result["instruction"]
        # Both shown — no filtering when FL list unavailable
        assert "Niagara" in instruction
        assert "Rochester" in instruction


class TestFindNearbyAirportsResolver:
    """Tests for AirportResolver.find_nearby_airports with known coordinates.

    Uses real haversine math (no mocking) to verify that distance-based
    filtering and sorting work correctly for well-known airports.
    """

    # Real-world coordinates (degrees)
    # BUF  Buffalo Niagara International: 42.9405 N, -78.7322 W
    # IAG  Niagara Falls International:   43.1073 N, -79.1058 W  (~28 km from BUF)
    # ROC  Rochester International:       43.1189 N, -77.6725 W  (~96 km from BUF)
    # JFK  John F. Kennedy International: 40.6441 N, -73.7824 W (~536 km from BUF)

    _AIRPORTS_DATA: ClassVar[dict] = {
        "buf": {
            "iata": "BUF",
            "name": "Buffalo Niagara International Airport",
            "city": "Buffalo",
            "state": "NY",
            "country": "US",
            "lat": 42.9405,
            "lon": -78.7322,
        },
        "iag": {
            "iata": "IAG",
            "name": "Niagara Falls International Airport",
            "city": "Niagara Falls",
            "state": "NY",
            "country": "US",
            "lat": 43.1073,
            "lon": -79.1058,
        },
        "roc": {
            "iata": "ROC",
            "name": "Greater Rochester International Airport",
            "city": "Rochester",
            "state": "NY",
            "country": "US",
            "lat": 43.1189,
            "lon": -77.6725,
        },
        "jfk": {
            "iata": "JFK",
            "name": "John F. Kennedy International Airport",
            "city": "New York",
            "state": "NY",
            "country": "US",
            "lat": 40.6441,
            "lon": -73.7824,
        },
    }

    def _make_resolver(self) -> MagicMock:
        from app.domains.airport.airport_resolver import AirportResolver

        resolver = AirportResolver.__new__(AirportResolver)
        resolver.airports_data = self._AIRPORTS_DATA
        resolver._loaded = True
        resolver.ensure_loaded = AsyncMock()
        return resolver

    @pytest.mark.asyncio
    async def test_nearby_within_radius_returned_sorted_by_distance(self) -> None:
        """IAG (~28 km) and ROC (~96 km) are within 200 km; JFK (~536 km) is not."""

        resolver = self._make_resolver()
        results = await resolver.find_nearby_airports("BUF", radius_km=200, limit=10)

        iata_codes = [r["iata"] for r in results]
        assert "IAG" in iata_codes, "IAG (~28 km) should be within 200 km radius"
        assert "ROC" in iata_codes, "ROC (~96 km) should be within 200 km radius"
        assert "JFK" not in iata_codes, "JFK (~536 km) should be outside 200 km radius"
        assert "BUF" not in iata_codes, "Reference airport must not appear in results"

    @pytest.mark.asyncio
    async def test_results_sorted_ascending_by_distance(self) -> None:
        """Closer airport (IAG ~28 km) must appear before farther one (ROC ~96 km)."""

        resolver = self._make_resolver()
        results = await resolver.find_nearby_airports("BUF", radius_km=200, limit=10)

        iata_codes = [r["iata"] for r in results]
        assert iata_codes.index("IAG") < iata_codes.index("ROC")

    @pytest.mark.asyncio
    async def test_limit_respected(self) -> None:
        """Only `limit` results are returned even if more are within radius."""

        resolver = self._make_resolver()
        results = await resolver.find_nearby_airports("BUF", radius_km=200, limit=1)

        assert len(results) == 1
        assert results[0]["iata"] == "IAG"  # closest first

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_iata(self) -> None:
        """IATA code not in airports_data → empty list, no exception."""

        resolver = self._make_resolver()
        results = await resolver.find_nearby_airports("ZZZ", radius_km=200)

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_coordinates(self) -> None:
        """Airport entry missing lat/lon coordinates → empty list."""

        resolver = self._make_resolver()
        # Inject an airport with no coordinates as the reference
        resolver.airports_data = {
            **self._AIRPORTS_DATA,
            "noc": {"iata": "NOC", "name": "No Coords Airport", "city": "Nowhere"},
        }
        results = await resolver.find_nearby_airports("NOC", radius_km=200)

        assert results == []

    @pytest.mark.asyncio
    async def test_distance_km_field_present_and_reasonable(self) -> None:
        """Each result dict includes distance_km within expected range."""

        resolver = self._make_resolver()
        results = await resolver.find_nearby_airports("BUF", radius_km=200, limit=10)

        iag = next(r for r in results if r["iata"] == "IAG")
        roc = next(r for r in results if r["iata"] == "ROC")

        # Real-world distances — allow ±20 km tolerance for rounding
        assert 10 <= iag["distance_km"] <= 50, (
            f"IAG distance unexpected: {iag['distance_km']}"
        )
        assert 70 <= roc["distance_km"] <= 120, (
            f"ROC distance unexpected: {roc['distance_km']}"
        )


class TestFindNearbyAirportsFullFlow:
    """Integration-style tests for the find_nearby_airports resolution flow inside search_flights.

    Unlike TestUnsupportedAirportHandler (which mocks find_nearby_airports), these tests
    use a real AirportResolver populated with known coordinates to verify the full path
    from unsupported-airport error → haversine resolution → result instruction.
    """

    _AIRPORTS_DATA: ClassVar[dict] = {
        "buf": {
            "iata": "BUF",
            "name": "Buffalo Niagara International Airport",
            "city": "Buffalo",
            "state": "NY",
            "country": "US",
            "lat": 42.9405,
            "lon": -78.7322,
        },
        "iag": {
            "iata": "IAG",
            "name": "Niagara Falls International Airport",
            "city": "Niagara Falls",
            "state": "NY",
            "country": "US",
            "lat": 43.1073,
            "lon": -79.1058,
        },
        "roc": {
            "iata": "ROC",
            "name": "Greater Rochester International Airport",
            "city": "Rochester",
            "state": "NY",
            "country": "US",
            "lat": 43.1189,
            "lon": -77.6725,
        },
    }

    def _make_error_response(self, code: str = "INVALID_AIRPORT") -> MagicMock:
        mock_error = MagicMock()
        mock_error.message = "Airport BUF is not supported."
        mock_error.code = code
        mock_response = MagicMock()
        mock_response.errors = [mock_error]
        mock_response.itineraries = []
        return mock_response

    def _make_resolver_with_real_data(self) -> MagicMock:
        """Return a mock AirportResolver whose find_nearby_airports delegates to real impl."""
        from app.domains.airport.airport_resolver import AirportResolver

        real_resolver = AirportResolver.__new__(AirportResolver)
        real_resolver.airports_data = self._AIRPORTS_DATA
        real_resolver._loaded = True
        real_resolver.ensure_loaded = AsyncMock()
        return real_resolver

    @pytest.mark.asyncio
    async def test_full_flow_returns_nearby_from_real_haversine(self) -> None:
        """search_flights unsupported-airport path uses real haversine to find IAG and ROC."""
        from app.ai.graph.tools.flights import search_flights

        mock_response = self._make_error_response()
        real_resolver = self._make_resolver_with_real_data()

        with (
            patch("app.domains.flight.service.FlightService") as mock_svc_cls,
            patch(
                "app.ai.graph.tools.flights._get_fl_supported_airports",
                new=AsyncMock(return_value={"IAG", "ROC", "LHR"}),
            ),
            patch(
                "app.domains.airport.airport_resolver.AirportResolver",
                return_value=real_resolver,
            ),
        ):
            mock_svc = AsyncMock()
            mock_svc.search_flights = AsyncMock(return_value=mock_response)
            mock_svc_cls.return_value = mock_svc

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

        assert result["status"] == "unsupported_airport"
        instruction = result["instruction"]
        # Real haversine finds IAG first (~28 km), then ROC (~96 km)
        assert "Niagara" in instruction
        assert "Rochester" in instruction

    @pytest.mark.asyncio
    async def test_full_flow_fl_filter_excludes_unsupported_nearby(self) -> None:
        """FL filtering applied to real haversine results: only supported airports shown."""
        from app.ai.graph.tools.flights import search_flights

        mock_response = self._make_error_response()
        real_resolver = self._make_resolver_with_real_data()

        with (
            patch("app.domains.flight.service.FlightService") as mock_svc_cls,
            patch(
                "app.ai.graph.tools.flights._get_fl_supported_airports",
                new=AsyncMock(return_value={"ROC", "LHR"}),  # IAG excluded from FL
            ),
            patch(
                "app.domains.airport.airport_resolver.AirportResolver",
                return_value=real_resolver,
            ),
        ):
            mock_svc = AsyncMock()
            mock_svc.search_flights = AsyncMock(return_value=mock_response)
            mock_svc_cls.return_value = mock_svc

            result = await search_flights.ainvoke(
                {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 1,
                    "trip_type": "one-way",
                }
            )

        assert result["status"] == "unsupported_airport"
        instruction = result["instruction"]
        assert "Rochester" in instruction  # ROC kept (FL-supported)
        assert "Niagara" not in instruction  # IAG filtered out (not FL-supported)


# ---------------------------------------------------------------------------
# Tests for supervisor_v2 message pre-classification helpers
# ---------------------------------------------------------------------------


class TestIsMode2Acknowledgement:
    """Tests for _is_mode2_acknowledgement helper."""

    @pytest.mark.parametrize(
        "msg",
        [
            "Looks great, thanks!",
            "thanks",
            "Perfect",
            "love it",
            "Amazing!",
            "That's awesome",
            "nice",
            "Cool!",
        ],
    )
    def test_positive(self, msg: str) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_acknowledgement

        assert _is_mode2_acknowledgement(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "looks great, add food tours",
            "thanks, book flights",
            "nice, change day 2 to museums",
            "awesome, find me hotels",
            "perfect, swap day 1 and 3",
        ],
    )
    def test_negative_has_action(self, msg: str) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_acknowledgement

        assert _is_mode2_acknowledgement(msg) is False

    def test_too_long(self) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_acknowledgement

        long_msg = (
            "This is a really great message that goes on and on about how awesome everything is"
            * 2
        )
        assert _is_mode2_acknowledgement(long_msg) is False

    def test_no_ack_word(self) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_acknowledgement

        assert _is_mode2_acknowledgement("Plan a trip to Paris") is False

    @pytest.mark.parametrize(
        "msg",
        [
            "thanksgiving dinner",
            "nicely done, but wrong",
            "cooling down now",
        ],
    )
    def test_negative_substring_not_word_boundary(self, msg: str) -> None:
        """Ensure substring matches like 'thank' in 'thanksgiving' don't trigger."""
        from app.ai.graph.supervisor_v2 import _is_mode2_acknowledgement

        assert _is_mode2_acknowledgement(msg) is False


class TestIsMode2PlanQuestion:
    """Tests for _is_mode2_plan_question helper."""

    @pytest.mark.parametrize(
        "msg",
        [
            "What's the best thing on day 2?",
            "Tell me about day 3",
            "What restaurant is on day 1?",
            "Which activity do you recommend?",
            "What is planned for day 4?",
        ],
    )
    def test_positive(self, msg: str) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_plan_question

        assert _is_mode2_plan_question(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "What if we add museums?",
            "Change day 2 to food tours",
            "Remove the hiking activity",
            "Can you swap day 1 and 3?",
        ],
    )
    def test_negative_has_action(self, msg: str) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_plan_question

        assert _is_mode2_plan_question(msg) is False

    def test_too_long(self) -> None:
        from app.ai.graph.supervisor_v2 import _is_mode2_plan_question

        long_msg = "a" * 130
        assert _is_mode2_plan_question(long_msg) is False


class TestDurationWithoutDateHint:
    """Test that _format_context_for_agent injects duration-without-date hint."""

    def test_duration_no_date_injects_hint(self) -> None:
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {"trip": {}, "flight": {}, "hotel": {}, "general": {}}
        result, _ = _format_context_for_agent(
            ctx, "itinerary", latest_message="Plan a 4-day trip to Rome"
        )
        assert "Contains trip duration but NO departure date" in result

    def test_duration_with_date_no_hint(self) -> None:
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {"trip": {}, "flight": {}, "hotel": {}, "general": {}}
        result, _ = _format_context_for_agent(
            ctx,
            "itinerary",
            latest_message="Plan a 4-day trip to Rome starting May 10",
        )
        assert "Contains trip duration but NO departure date" not in result

    def test_may_auxiliary_not_treated_as_date(self) -> None:
        """'may' as auxiliary verb should NOT suppress the duration guard."""
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {"trip": {}, "flight": {}, "hotel": {}, "general": {}}
        result, _ = _format_context_for_agent(
            ctx,
            "itinerary",
            latest_message="I may travel for 4 days in Europe",
        )
        assert "Contains trip duration but NO departure date" in result


class TestIsOriginCountryOnly:
    """``_is_origin_country_only`` uses the geocoder's top-level ``types``
    array (via ``GeocodingService.get_location_types``) to deterministically
    detect country-only origins (#1105).

    Note: must use ``get_location_types`` and NOT ``geocode_city``, because
    the latter filters out results without a ``locality`` component —
    exactly the case (country queries) we need to detect.
    """

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService")
    async def test_country_types_returns_true(
        self, mock_service_cls: MagicMock
    ) -> None:
        """``types=["country", "political"]`` → country-only."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        mock_service_cls.return_value.get_location_types = AsyncMock(
            return_value=["country", "political"]
        )

        assert await _is_origin_country_only("the US") is True
        mock_service_cls.return_value.get_location_types.assert_awaited_once_with(
            "the US"
        )

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService")
    async def test_locality_types_returns_false(
        self, mock_service_cls: MagicMock
    ) -> None:
        """``types=["locality", "political"]`` → real city, not country."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        mock_service_cls.return_value.get_location_types = AsyncMock(
            return_value=["locality", "political"]
        )

        assert await _is_origin_country_only("Los Angeles") is False

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService")
    async def test_country_and_locality_both_present_returns_false(
        self, mock_service_cls: MagicMock
    ) -> None:
        """Defensive: if Google ever returns both ``country`` + ``locality``
        (e.g. a city-state like Monaco), trust the locality signal."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        mock_service_cls.return_value.get_location_types = AsyncMock(
            return_value=["country", "locality", "political"]
        )

        assert await _is_origin_country_only("Monaco") is False

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService")
    async def test_geocoder_returns_empty_returns_false(
        self, mock_service_cls: MagicMock
    ) -> None:
        """No geocode results → safe default of False (don't block)."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        mock_service_cls.return_value.get_location_types = AsyncMock(return_value=[])

        assert await _is_origin_country_only("Nowheresville") is False

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService")
    async def test_geocoder_raises_returns_false(
        self, mock_service_cls: MagicMock
    ) -> None:
        """Network / quota errors must not raise — safe default of False."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        mock_service_cls.return_value.get_location_types = AsyncMock(
            side_effect=RuntimeError("quota exceeded")
        )

        assert await _is_origin_country_only("Tokyo") is False

    @pytest.mark.asyncio
    async def test_empty_input_short_circuits(self) -> None:
        """Empty / whitespace inputs return False without hitting the geocoder."""
        from app.ai.graph.itinerary_trip_extractor import _is_origin_country_only

        assert await _is_origin_country_only("") is False
        assert await _is_origin_country_only("   ") is False


class TestCountryOnlyOriginInjection:
    """``_format_context_for_agent`` injects a BLOCKING ask when
    ``trip.origin_is_country=True`` and itinerary hasn't been generated yet
    (#1105 Bug 2). The flag is computed during ``extract_and_resolve`` via
    the geocoder and cached on shared_context."""

    def test_country_origin_injects_blocking_ask(self) -> None:
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {
            "trip": {
                "origin": "the US",
                "origin_is_country": True,
                "destination": "Tokyo",
                "departure_date": "2026-06-19",
                "return_date": "2026-06-25",
                "trip_duration_days": 7,
            },
            "flight": {},
            "hotel": {},
            "general": {},
        }
        result, _ = _format_context_for_agent(
            ctx,
            "itinerary",
            latest_message="Plan a 7-day Tokyo trip from the US starting 30 days from now",
        )
        assert "BLOCKING" in result
        # Dynamic country-aware ask: should mention the origin verbatim and
        # nudge the LLM to suggest cities-of-that-country with IATAs.
        assert "the US" in result
        assert "city of the US" in result
        assert "IATA" in result

    def test_specific_city_origin_no_block(self) -> None:
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {
            "trip": {
                "origin": "Los Angeles",
                "origin_iata": "LAX",
                "origin_is_country": False,
                "destination": "Tokyo",
                "departure_date": "2026-06-19",
                "return_date": "2026-06-25",
                "trip_duration_days": 7,
            },
            "flight": {},
            "hotel": {},
            "general": {},
        }
        result, _ = _format_context_for_agent(
            ctx, "itinerary", latest_message="anything"
        )
        assert "BLOCKING" not in result

    def test_country_origin_with_iata_already_resolved_no_block(self) -> None:
        """If origin_iata is already set, treat as resolved even if the
        origin label is country-only (defensive)."""
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {
            "trip": {
                "origin": "the US",
                "origin_iata": "LAX",  # already resolved upstream
                "origin_is_country": True,
                "destination": "Tokyo",
                "departure_date": "2026-06-19",
                "return_date": "2026-06-25",
            },
            "flight": {},
            "hotel": {},
            "general": {},
        }
        result, _ = _format_context_for_agent(
            ctx, "itinerary", latest_message="anything"
        )
        assert "BLOCKING" not in result

    def test_country_origin_after_itinerary_generated_no_block(self) -> None:
        """Once the itinerary exists, the block doesn't fire (Mode 2)."""
        from app.ai.graph.supervisor_v2 import _format_context_for_agent

        ctx: dict = {
            "trip": {
                "origin": "the US",
                "origin_is_country": True,
                "destination": "Tokyo",
                "departure_date": "2026-06-19",
                "return_date": "2026-06-25",
                "itinerary_generated": True,
            },
            "flight": {},
            "hotel": {},
            "general": {},
        }
        result, _ = _format_context_for_agent(
            ctx, "itinerary", latest_message="anything"
        )
        assert "BLOCKING" not in result
