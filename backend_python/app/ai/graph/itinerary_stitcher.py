"""Stitcher: fold flight + hotel cards into the LLM-produced itinerary.

The flight + hotel agents run in parallel with ``generate_itinerary`` so the
LLM never sees their payloads (issue #1034). This module merges the three
streams into a single FE-ready response in pure Python — no LLM, no I/O.

Architecture (see ``docs/PERSONALIZED_ITINERARY_PLAN.md``):

- Day 1 of every itinerary opens with an outbound flight card + hotel
  check-in card above the LLM-generated activities.
- Last day ends with a hotel check-out card + return flight card (if
  the trip is a round-trip).
- ``flights[1:]`` and ``hotels[1:]`` attach at the top level of the
  response payload for the FE's "Recommended" rails.

Each inserted entry carries a ``kind`` field
(``"flight" | "hotel-checkin" | "hotel-checkout"``) so the FE renderer
picks the right compact card. Activities the LLM produced get
``kind="activity"`` by default (the FE renderer treats missing ``kind``
as ``"activity"`` too — back-compat with pre-feature saved itineraries).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _make_flight_entry(flight: dict[str, Any], leg: str) -> dict[str, Any]:
    """Build a flight itinerary entry from a flight dict.

    ``leg`` is ``"outbound"`` or ``"inbound"`` — recorded on the entry so the
    FE can label the card without scanning origin/destination.
    """
    return {
        "kind": "flight",
        "leg": leg,
        "flight": flight,
    }


def _make_hotel_entry(hotel: dict[str, Any], phase: str) -> dict[str, Any]:
    """Build a hotel itinerary entry.

    ``phase`` is ``"check-in"`` or ``"check-out"``.
    """
    return {
        "kind": "hotel-checkin" if phase == "check-in" else "hotel-checkout",
        "hotel": hotel,
    }


def _ensure_day_activities(day: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the activities list for ``day``, creating ``expandedContent`` if missing."""
    expanded = day.get("expandedContent")
    if not isinstance(expanded, dict):
        expanded = {}
        day["expandedContent"] = expanded
    activities = expanded.get("activities")
    if not isinstance(activities, list):
        activities = []
        expanded["activities"] = activities
    return activities


def stitch_itinerary(
    structured_itinerary: dict[str, Any],
    flights: list[dict[str, Any]] | None,
    hotels: list[dict[str, Any]] | None,
    *,
    is_round_trip: bool,
) -> dict[str, Any]:
    """Insert flight + hotel cards into the LLM-produced itinerary.

    Mutates ``structured_itinerary`` in place AND returns it so callers can
    chain. No-ops gracefully when either list is empty / None — the doc's
    "graceful degradation" requirement.

    Insertion policy (matches Q9 in the working doc):
    - Cards land at the TOP of the day's ``expandedContent.activities`` (Day 1)
      or BOTTOM (Day N, return flight) regardless of activity times. They
      render with a distinct ``kind`` so users don't read them as
      time-conflicting activity entries. The LLM's pacing is not reshuffled.

    Args:
        structured_itinerary: The dict from ``generate_itinerary`` (with
            ``itineraryItems: [...]``).
        flights: Flat best-value-sorted flight list from ``_do_flight_search``
            (``flights[0]`` becomes the inline card; rest attach at the top
            level by the caller).
        hotels: Flat best-value-sorted hotel list from ``_do_hotel_search``.
        is_round_trip: When ``True``, the same ``flights[0]`` is reused as the
            return-leg card on the last day. When ``False`` (one-way), the
            check-out / return cards are skipped — faithful to the user's
            stated intent (Q5 in the doc).

    Returns:
        The (mutated) ``structured_itinerary`` dict.
    """
    items = structured_itinerary.get("itineraryItems") or []
    if not items:
        logger.debug("stitch_itinerary: no itineraryItems — nothing to stitch")
        return structured_itinerary

    top_flight = flights[0] if flights else None
    top_hotel = hotels[0] if hotels else None

    first_day = items[0]
    last_day = items[-1] if len(items) > 1 else None

    first_day_activities = _ensure_day_activities(first_day)
    inserts_day1: list[dict[str, Any]] = []
    if top_flight is not None:
        inserts_day1.append(_make_flight_entry(top_flight, leg="outbound"))
    if top_hotel is not None:
        inserts_day1.append(_make_hotel_entry(top_hotel, phase="check-in"))
    # Prepend so flight + hotel cards lead Day 1, ahead of LLM activities.
    if inserts_day1:
        first_day_activities[:0] = inserts_day1

    if last_day is not None:
        last_day_activities = _ensure_day_activities(last_day)
        # Hotel check-out first (morning), then return flight at the end.
        if top_hotel is not None:
            last_day_activities.insert(
                0, _make_hotel_entry(top_hotel, phase="check-out")
            )
        if top_flight is not None and is_round_trip:
            last_day_activities.append(_make_flight_entry(top_flight, leg="inbound"))

    return structured_itinerary


__all__ = ["stitch_itinerary"]
