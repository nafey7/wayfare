"""Structured flight route snapshots for booking_events (API + Mongo).

``flight_trip_type`` is persisted as snake_case strings aligned with product language:
``one_way`` | ``round_trip`` | ``multi_city``.

Mapping from FlightLogic ``journey_type`` at booking time (see ``route_snapshot``):
- ``OneWay`` -> ``one_way``
- ``Return`` -> ``round_trip``
- ``Circle`` or multicity leg selection -> ``multi_city`` (each Mongo row for a paid leg
  typically has one logical leg in ``route_legs``; full-circle single documents may list
  multiple legs).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

FlightTripTypeLiteral = Literal["one_way", "round_trip", "multi_city"]


def _normalize_iata_field(v: object) -> object:
    if isinstance(v, str):
        s = v.strip().upper()
        if len(s) != 3:
            raise ValueError(
                "IATA airport code must be exactly 3 letters (A-Z); "
                f"after trim/upper got {len(s)} character(s), value={v!r}, normalized={s!r}"
            )
        if not s.isalpha():
            raise ValueError(
                "IATA airport code must be 3 letters (A-Z); "
                f"value={v!r}, normalized={s!r}"
            )
        return s
    return v


class RouteSegment(BaseModel):
    """One segment hop (connection) within a leg."""

    departure_iata: str = Field(..., min_length=3, max_length=3)
    arrival_iata: str = Field(..., min_length=3, max_length=3)

    @field_validator("departure_iata", "arrival_iata", mode="before")
    @classmethod
    def _normalize_iata(cls, v: object) -> object:
        return _normalize_iata_field(v)


class RouteLeg(BaseModel):
    """One directional leg: true endpoints match first/last segment IATAs."""

    leg_index: int = Field(..., ge=0)
    departure_iata: str = Field(..., min_length=3, max_length=3)
    arrival_iata: str = Field(..., min_length=3, max_length=3)
    segment_count: int = Field(..., ge=1)
    segments: list[RouteSegment] = Field(default_factory=list)

    @field_validator("departure_iata", "arrival_iata", mode="before")
    @classmethod
    def _normalize_iata(cls, v: object) -> object:
        return _normalize_iata_field(v)


def departure_iata_from_route_legs(route_legs: list[RouteLeg] | None) -> str | None:
    """First segment departure of the first leg — ticket TTL / Slack / legacy field."""
    if not route_legs:
        return None
    leg0 = route_legs[0]
    if leg0.segments:
        return leg0.segments[0].departure_iata
    return leg0.departure_iata


def departure_iata_from_route_legs_raw(route_legs: Any) -> str | None:
    """Parse Mongo/raw list of dicts (post-load); safe for alert jobs on mixed-age docs."""
    if not route_legs or not isinstance(route_legs, list):
        return None
    leg0 = route_legs[0]
    if not isinstance(leg0, dict):
        return None
    segs = leg0.get("segments")
    if isinstance(segs, list) and segs:
        s0 = segs[0]
        if isinstance(s0, dict):
            dep = s0.get("departure_iata")
            if isinstance(dep, str) and len(dep.strip()) == 3:
                return dep.strip().upper()
    dep = leg0.get("departure_iata")
    if isinstance(dep, str) and len(dep.strip()) == 3:
        return dep.strip().upper()
    return None


def parse_route_legs_from_document(
    raw: Any, *, booking_id: str | None = None
) -> list[RouteLeg] | None:
    """Validate Mongo ``route_legs`` into typed models; None if missing/invalid."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        return None
    try:
        return [RouteLeg.model_validate(x) for x in raw]
    except ValidationError as e:
        logger.warning(
            "Invalid route_legs on booking document (booking_id=%s): %s",
            booking_id,
            e,
        )
        return None
