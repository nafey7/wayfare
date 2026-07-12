"""Derive leg-level itinerary snapshots from trip-details segments (list/profile UIs).

Connection segments (arrival airport == next departure) form one *leg*. A new leg starts
when that chain breaks (open jaw, multi-city). The leg's departure date is the first
segment's departure (UTC calendar day).

Round trips: the same rule would chain outbound and return when the last outbound arrival
equals the first return departure (e.g. hub JFK). When *primary_destination_iata* is set
(TravelItinerary.Destination from trip_details), we end a leg after any segment that arrives
there so the return journey starts a new leg.
"""

from __future__ import annotations

from datetime import UTC, date
from typing import TYPE_CHECKING

from app.shared.flight_leg_summary import FlightLegSummary

if TYPE_CHECKING:
    from app.domains.flight.schemas import TripDetailsFlightSegment


def _normalize_iata(code: str) -> str:
    return (code or "").strip().upper()


def _segment_departure_date_utc(seg: TripDetailsFlightSegment) -> date:
    dt = seg.departure_datetime.value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).date()


def flight_segment_departure_dates_iso(
    segments: list[TripDetailsFlightSegment],
) -> list[str]:
    """Per-segment departure calendar dates (UTC), trip_details order — for MongoDB / APIs."""
    return [_segment_departure_date_utc(s).isoformat() for s in segments]


def flight_leg_summaries_from_segments(
    segments: list[TripDetailsFlightSegment],
    *,
    primary_destination_iata: str | None = None,
) -> list[FlightLegSummary]:
    """Return ordered leg summaries from trip-details segments (connections collapsed)."""
    if not segments:
        return []

    summaries: list[FlightLegSummary] = []
    leg_start = 0
    dest = _normalize_iata(primary_destination_iata) if primary_destination_iata else ""

    for i in range(len(segments)):
        seg = segments[i]
        last_in_leg = i == len(segments) - 1
        if not last_in_leg:
            nxt = segments[i + 1]
            arr = _normalize_iata(seg.arrival_airport.iata_code)
            nxt_dep = _normalize_iata(nxt.departure_airport.iata_code)
            continues = arr == nxt_dep and bool(arr)
            if dest and arr == dest:
                continues = False
        else:
            continues = False

        if not continues:
            first = segments[leg_start]
            last = segments[i]
            summaries.append(
                FlightLegSummary(
                    departure_date=_segment_departure_date_utc(first),
                    origin_iata=_normalize_iata(first.departure_airport.iata_code),
                    destination_iata=_normalize_iata(last.arrival_airport.iata_code),
                )
            )
            leg_start = i + 1

    return summaries
