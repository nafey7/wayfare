"""Offline evaluators for ``generate_itinerary`` output (#1053 P0.3).

Each evaluator takes the response payload from a single itinerary turn (the
``ChatResponse.data`` dict on an ``itinerary_results`` response) plus the
declared expectations (destination, day count, etc.) and returns a score +
reason. Scores follow the LangSmith convention: ``1.0`` for full pass,
``0.0`` for full fail, intermediate values for partial pass.

Why pure functions, not LangSmith ``RunEvaluator`` subclasses today:
- LangSmith isn't yet a project dependency. Adding it would mean a new
  account, API key, and runtime cost just to evaluate.
- Pure functions ship today, run inside our existing pytest, and can be
  wrapped as ``RunEvaluator`` instances later with zero logic changes.

Usage:
    from app.ai.evaluation.itinerary_evaluators import (
        evaluate_schema_validity,
        evaluate_day_count_match,
        evaluate_activity_count_per_day,
        evaluate_concrete_details_present,
    )

    payload = response["data"]
    inputs = {"expected_destination": "Paris", "expected_days": 5}
    result = evaluate_schema_validity(payload)
    print(result.score, result.reason)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluatorResult:
    """Mirrors LangSmith's evaluator return shape so port is trivial later."""

    key: str
    score: float
    reason: str


def _resolve_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Tolerate both the flat ``payload`` and the nested ``payload['data']`` shapes.

    Itinerary responses today put ``structured_itinerary`` at the top of
    ``ChatResponse.data``. Some upstream paths (and saved-itinerary records)
    wrap it under ``data['data']``. Probe both.
    """
    if not isinstance(payload, dict):
        return {}
    if "structured_itinerary" in payload:
        return payload
    inner = payload.get("data")
    if isinstance(inner, dict) and "structured_itinerary" in inner:
        return inner
    return payload


def _get_days(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the ``itineraryItems`` list from either nested shape."""
    data = _resolve_data(payload)
    structured = data.get("structured_itinerary")
    if not isinstance(structured, dict):
        return []
    days = structured.get("itineraryItems")
    return days if isinstance(days, list) else []


def evaluate_schema_validity(payload: dict[str, Any]) -> EvaluatorResult:
    """All required top-level fields are present and well-typed.

    Required: ``destination`` (str), ``departure_date`` (str), ``return_date``
    (str), ``adults`` (int), ``structured_itinerary.itineraryItems`` (list).
    Each day must have ``day`` (int), ``title`` (str), ``expandedContent``
    (dict with ``activities`` list).
    """
    data = _resolve_data(payload)
    missing: list[str] = []

    for field, typ in (
        ("destination", str),
        ("departure_date", str),
        ("return_date", str),
        ("adults", int),
    ):
        v = data.get(field)
        if v is None or not isinstance(v, typ):
            missing.append(field)

    days = _get_days(payload)
    if not days:
        missing.append("structured_itinerary.itineraryItems")

    bad_days: list[int] = []
    for idx, d in enumerate(days):
        if not isinstance(d, dict):
            bad_days.append(idx)
            continue
        if not isinstance(d.get("day"), int):
            bad_days.append(idx)
            continue
        if not isinstance(d.get("title"), str):
            bad_days.append(idx)
            continue
        expanded = d.get("expandedContent")
        if not isinstance(expanded, dict) or not isinstance(
            expanded.get("activities"), list
        ):
            bad_days.append(idx)

    if missing or bad_days:
        reason_parts: list[str] = []
        if missing:
            reason_parts.append(f"missing/wrong-type fields: {missing}")
        if bad_days:
            reason_parts.append(f"malformed day indices: {bad_days}")
        return EvaluatorResult(
            key="schema_validity", score=0.0, reason="; ".join(reason_parts)
        )

    return EvaluatorResult(
        key="schema_validity",
        score=1.0,
        reason=f"all required fields present, {len(days)} well-formed days",
    )


def evaluate_day_count_match(
    payload: dict[str, Any], expected_days: int
) -> EvaluatorResult:
    """``len(itineraryItems) == expected_days``. Critical for trip-length contract."""
    days = _get_days(payload)
    actual = len(days)
    if actual == expected_days:
        return EvaluatorResult(
            key="day_count_match",
            score=1.0,
            reason=f"got {actual} days as expected",
        )
    return EvaluatorResult(
        key="day_count_match",
        score=0.0,
        reason=f"expected {expected_days} days, got {actual}",
    )


def evaluate_activity_count_per_day(
    payload: dict[str, Any],
    *,
    min_per_day: int = 2,
    max_per_day: int = 4,
) -> EvaluatorResult:
    """Each day has between ``min_per_day`` and ``max_per_day`` activities.

    Default bounds match the itinerary prompt's "ACTIVITY COUNTS: Day 1: 2-3,
    middle: 3, last: 2" rule (``prompts/itinerary_agent.py``).
    """
    days = _get_days(payload)
    if not days:
        return EvaluatorResult(
            key="activity_count_per_day",
            score=0.0,
            reason="no days to evaluate",
        )
    out_of_bounds: list[tuple[int, int]] = []
    for d in days:
        if not isinstance(d, dict):
            continue
        expanded = d.get("expandedContent") or {}
        activities = expanded.get("activities") or []
        # Stitched flight/hotel entries (#1038) carry kind != "activity" — only
        # count actual activity entries when scoring against the LLM's
        # promised range.
        actual_activities = [
            a
            for a in activities
            if not isinstance(a, dict) or a.get("kind", "activity") == "activity"
        ]
        n = len(actual_activities)
        if n < min_per_day or n > max_per_day:
            day_num = d.get("day", "?")
            out_of_bounds.append((day_num, n))

    if out_of_bounds:
        return EvaluatorResult(
            key="activity_count_per_day",
            score=max(0.0, 1.0 - len(out_of_bounds) / len(days)),
            reason=(
                f"{len(out_of_bounds)}/{len(days)} days out of [{min_per_day}, "
                f"{max_per_day}] range: {out_of_bounds}"
            ),
        )
    return EvaluatorResult(
        key="activity_count_per_day",
        score=1.0,
        reason=f"all {len(days)} days within [{min_per_day}, {max_per_day}] activities",
    )


def evaluate_concrete_details_present(
    payload: dict[str, Any],
    *,
    expected_destination: str,
    expected_departure_date: str | None = None,
) -> EvaluatorResult:
    """The plan references the user's actual destination + dates somewhere in titles/descriptions.

    Guards against the LLM producing a "valid-but-generic" itinerary that
    forgets which city it's planning. Matches case-insensitive against day
    titles + activity descriptions.
    """
    days = _get_days(payload)
    if not days:
        return EvaluatorResult(
            key="concrete_details_present",
            score=0.0,
            reason="no days to evaluate",
        )

    needle_dest = expected_destination.lower()
    haystack_parts: list[str] = []
    for d in days:
        if not isinstance(d, dict):
            continue
        title = d.get("title")
        if isinstance(title, str):
            haystack_parts.append(title)
        expanded = d.get("expandedContent") or {}
        for a in expanded.get("activities") or []:
            if not isinstance(a, dict):
                continue
            for field in ("location", "description"):
                v = a.get(field)
                if isinstance(v, str):
                    haystack_parts.append(v)
    haystack = " ".join(haystack_parts).lower()

    dest_present = needle_dest in haystack
    date_present = True
    date_note = ""
    if expected_departure_date:
        # Tolerate either ISO date or month-day format ("2026-06-13" or "June 13")
        date_present = expected_departure_date.lower() in haystack
        if not date_present:
            # Try month name from ISO
            try:
                from datetime import date as date_cls

                parsed_date = date_cls.fromisoformat(expected_departure_date)
                month_name = parsed_date.strftime("%B").lower()
                date_present = month_name in haystack
                date_note = f" (matched on month name '{month_name}')"
            except (ValueError, TypeError):
                date_note = ""

    if dest_present and date_present:
        return EvaluatorResult(
            key="concrete_details_present",
            score=1.0,
            reason=(
                f"destination '{expected_destination}' present in plan"
                + (
                    f"; departure date '{expected_departure_date}' referenced{date_note}"
                    if expected_departure_date
                    else ""
                )
            ),
        )

    missing = []
    if not dest_present:
        missing.append(f"destination '{expected_destination}'")
    if not date_present:
        missing.append(f"departure date '{expected_departure_date}'")
    return EvaluatorResult(
        key="concrete_details_present",
        score=0.0 if not dest_present else 0.5,
        reason=f"not referenced in titles/descriptions: {', '.join(missing)}",
    )


def evaluate_all(
    payload: dict[str, Any],
    *,
    expected_destination: str,
    expected_days: int,
    expected_departure_date: str | None = None,
    activity_bounds: tuple[int, int] = (2, 4),
) -> list[EvaluatorResult]:
    """Run all four evaluators and return their results in order."""
    return [
        evaluate_schema_validity(payload),
        evaluate_day_count_match(payload, expected_days),
        evaluate_activity_count_per_day(
            payload, min_per_day=activity_bounds[0], max_per_day=activity_bounds[1]
        ),
        evaluate_concrete_details_present(
            payload,
            expected_destination=expected_destination,
            expected_departure_date=expected_departure_date,
        ),
    ]


__all__ = [
    "EvaluatorResult",
    "evaluate_activity_count_per_day",
    "evaluate_all",
    "evaluate_concrete_details_present",
    "evaluate_day_count_match",
    "evaluate_schema_validity",
]
