"""Tests for the offline itinerary evaluators (#1053 P0.3).

These are pure-function evaluators that score ``generate_itinerary`` outputs.
The tests feed synthetic payloads (no LLM calls) so they're fast + offline,
matching the LangSmith offline-eval pattern that this code can be ported to
later without logic changes.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.evaluation.itinerary_evaluators import (
    evaluate_activity_count_per_day,
    evaluate_all,
    evaluate_concrete_details_present,
    evaluate_day_count_match,
    evaluate_schema_validity,
)


def _make_payload(
    *,
    destination: str = "Paris",
    departure_date: str = "2026-06-20",
    return_date: str = "2026-06-24",
    adults: int = 2,
    days: int = 5,
    activities_per_day: int = 3,
    skip_destination_in_text: bool = False,
) -> dict[str, Any]:
    """Synthesize a well-formed itinerary-results payload."""
    itinerary_items: list[dict[str, Any]] = []
    for i in range(days):
        title = (
            f"Day {i + 1} — relaxed start"
            if skip_destination_in_text
            else f"Day {i + 1} — {destination} highlights"
        )
        activities = [
            {
                "kind": "activity",
                "location": f"Activity {j + 1} {'spot' if skip_destination_in_text else destination}",
                "description": f"Visit something fun in {'town' if skip_destination_in_text else destination}",
            }
            for j in range(activities_per_day)
        ]
        itinerary_items.append(
            {
                "day": i + 1,
                "title": title,
                "expandedContent": {"activities": activities},
            }
        )
    return {
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "adults": adults,
        "structured_itinerary": {"itineraryItems": itinerary_items},
    }


# ----------------------------------------------------------------------------
# evaluate_schema_validity
# ----------------------------------------------------------------------------


class TestSchemaValidity:
    def test_pass_when_all_required_fields_present(self) -> None:
        result = evaluate_schema_validity(_make_payload())
        assert result.score == 1.0
        assert "5 well-formed days" in result.reason

    def test_fail_when_destination_missing(self) -> None:
        payload = _make_payload()
        del payload["destination"]
        result = evaluate_schema_validity(payload)
        assert result.score == 0.0
        assert "destination" in result.reason

    def test_fail_when_no_days(self) -> None:
        payload = _make_payload()
        payload["structured_itinerary"]["itineraryItems"] = []
        result = evaluate_schema_validity(payload)
        assert result.score == 0.0
        assert "itineraryItems" in result.reason

    def test_fail_when_day_missing_expanded_content(self) -> None:
        payload = _make_payload()
        del payload["structured_itinerary"]["itineraryItems"][2]["expandedContent"]
        result = evaluate_schema_validity(payload)
        assert result.score == 0.0
        assert "2" in result.reason  # malformed day at index 2

    def test_tolerates_nested_data_shape(self) -> None:
        """``payload['data']['structured_itinerary']`` is also valid (saved-itinerary records use this)."""
        inner = _make_payload()
        wrapped = {"data": inner}
        result = evaluate_schema_validity(wrapped)
        assert result.score == 1.0


# ----------------------------------------------------------------------------
# evaluate_day_count_match
# ----------------------------------------------------------------------------


class TestDayCountMatch:
    def test_pass_when_count_matches(self) -> None:
        result = evaluate_day_count_match(_make_payload(days=5), expected_days=5)
        assert result.score == 1.0

    def test_fail_when_too_few(self) -> None:
        result = evaluate_day_count_match(_make_payload(days=4), expected_days=5)
        assert result.score == 0.0
        assert "got 4" in result.reason

    def test_fail_when_too_many(self) -> None:
        result = evaluate_day_count_match(_make_payload(days=6), expected_days=5)
        assert result.score == 0.0
        assert "got 6" in result.reason


# ----------------------------------------------------------------------------
# evaluate_activity_count_per_day
# ----------------------------------------------------------------------------


class TestActivityCountPerDay:
    def test_pass_when_all_within_bounds(self) -> None:
        result = evaluate_activity_count_per_day(_make_payload(activities_per_day=3))
        assert result.score == 1.0

    def test_partial_score_when_some_out_of_bounds(self) -> None:
        payload = _make_payload(days=5, activities_per_day=3)
        # Drop activities on day 1 below the floor
        payload["structured_itinerary"]["itineraryItems"][0]["expandedContent"][
            "activities"
        ] = []
        result = evaluate_activity_count_per_day(payload)
        assert 0.0 < result.score < 1.0  # partial credit
        assert "1/5 days" in result.reason

    def test_fail_when_no_days(self) -> None:
        payload = _make_payload()
        payload["structured_itinerary"]["itineraryItems"] = []
        result = evaluate_activity_count_per_day(payload)
        assert result.score == 0.0

    def test_excludes_stitched_flight_hotel_entries(self) -> None:
        """#1038 stitcher inserts entries with kind != 'activity'; those must
        not count against the activity-bounds check."""
        payload = _make_payload(days=3, activities_per_day=3)
        # Add 2 stitched cards to day 1
        payload["structured_itinerary"]["itineraryItems"][0]["expandedContent"][
            "activities"
        ].insert(0, {"kind": "flight", "flight": {}})
        payload["structured_itinerary"]["itineraryItems"][0]["expandedContent"][
            "activities"
        ].insert(1, {"kind": "hotel-checkin", "hotel": {}})
        # Day 1 now has 5 entries total but only 3 actual activities — should still pass
        result = evaluate_activity_count_per_day(payload)
        assert result.score == 1.0


# ----------------------------------------------------------------------------
# evaluate_concrete_details_present
# ----------------------------------------------------------------------------


class TestConcreteDetailsPresent:
    def test_pass_when_destination_referenced(self) -> None:
        result = evaluate_concrete_details_present(
            _make_payload(destination="Paris"), expected_destination="Paris"
        )
        assert result.score == 1.0

    def test_fail_when_destination_never_mentioned(self) -> None:
        result = evaluate_concrete_details_present(
            _make_payload(destination="Tokyo", skip_destination_in_text=True),
            expected_destination="Tokyo",
        )
        assert result.score == 0.0
        assert "Tokyo" in result.reason

    def test_matches_destination_case_insensitive(self) -> None:
        payload = _make_payload(destination="PARIS")
        result = evaluate_concrete_details_present(
            payload, expected_destination="paris"
        )
        assert result.score == 1.0

    def test_partial_when_destination_present_but_date_missing(self) -> None:
        payload = _make_payload(destination="Paris")
        result = evaluate_concrete_details_present(
            payload,
            expected_destination="Paris",
            expected_departure_date="1999-01-01",
        )
        assert result.score == 0.5
        assert "1999-01-01" in result.reason


# ----------------------------------------------------------------------------
# evaluate_all wrapper
# ----------------------------------------------------------------------------


class TestEvaluateAll:
    def test_returns_all_four_evaluators_in_order(self) -> None:
        results = evaluate_all(
            _make_payload(),
            expected_destination="Paris",
            expected_days=5,
        )
        assert len(results) == 4
        assert [r.key for r in results] == [
            "schema_validity",
            "day_count_match",
            "activity_count_per_day",
            "concrete_details_present",
        ]

    def test_pass_path_all_score_1(self) -> None:
        results = evaluate_all(
            _make_payload(destination="Paris", days=5, activities_per_day=3),
            expected_destination="Paris",
            expected_days=5,
        )
        assert all(r.score == 1.0 for r in results), [
            (r.key, r.score, r.reason) for r in results
        ]


# Note for future LangSmith adoption: each ``EvaluatorResult`` already carries
# (key, score, reason) — the exact shape LangSmith's ``EvaluationResult``
# requires. Wrapping these in a ``langsmith.evaluation.RunEvaluator`` is a
# 5-line shim when we adopt LangSmith.

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
