"""Extract persisted route + marketing-airline snapshots for flight booking_events.

Used at booking confirmation (revalidate + request context) and when syncing from
trip-details responses. Parsing is defensive: missing vendor fields leave snapshots empty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.database.flight_route import (
    FlightTripTypeLiteral,
    RouteLeg,
    RouteSegment,
    departure_iata_from_route_legs,
)

logger = logging.getLogger(__name__)


def _journey_type_str(itin: Any) -> str | None:
    """Normalize journey_type from ValidatedFareItinerary (enum or string mock)."""
    jt = getattr(itin, "journey_type", None)
    if jt is None:
        return None
    return str(getattr(jt, "value", jt))


def _norm_iata(code: str | None) -> str | None:
    if not code or not str(code).strip():
        return None
    s = str(code).strip().upper()
    return s if len(s) == 3 else None


def _marketing_name_from_segment(seg: Any) -> str | None:
    if seg is None:
        return None
    ma = getattr(seg, "marketing_airline", None)
    if ma is None:
        return None
    name = getattr(ma, "airline_name", None)
    if name and str(name).strip():
        return str(name).strip()
    return None


def _route_segments_from_vendor_segments(
    vendor_segments: list[Any],
) -> list[RouteSegment] | None:
    out: list[RouteSegment] = []
    for seg in vendor_segments:
        dep = _norm_iata(
            getattr(getattr(seg, "departure_airport", None), "iata_code", None)
        )
        arr = _norm_iata(
            getattr(getattr(seg, "arrival_airport", None), "iata_code", None)
        )
        if dep and arr:
            out.append(RouteSegment(departure_iata=dep, arrival_iata=arr))
    return out or None


def _leg_from_vendor_segments(
    vendor_segments: list[Any],
    leg_index: int,
) -> RouteLeg | None:
    segs = _route_segments_from_vendor_segments(vendor_segments)
    if not segs:
        return None
    return RouteLeg(
        leg_index=leg_index,
        departure_iata=segs[0].departure_iata,
        arrival_iata=segs[-1].arrival_iata,
        segment_count=len(segs),
        segments=segs,
    )


def _seg_dep_arr(seg: Any) -> tuple[str | None, str | None]:
    dep = _norm_iata(
        getattr(getattr(seg, "departure_airport", None), "iata_code", None)
    )
    arr = _norm_iata(getattr(getattr(seg, "arrival_airport", None), "iata_code", None))
    return dep, arr


def _rt_partition_valid(a: list[Any], b: list[Any], orig: str) -> bool:
    """True if ``a`` then ``b`` form a connected round trip closing at ``orig``."""
    if not a or not b:
        return False
    chain_ok = True
    for i in range(len(a) - 1):
        _, ar = _seg_dep_arr(a[i])
        d2, _ = _seg_dep_arr(a[i + 1])
        if not ar or not d2 or ar != d2:
            chain_ok = False
            break
    if not chain_ok:
        return False
    _, hub = _seg_dep_arr(a[-1])
    d_ret, _ = _seg_dep_arr(b[0])
    if not hub or not d_ret or hub != d_ret:
        return False
    for i in range(len(b) - 1):
        _, ar = _seg_dep_arr(b[i])
        d2, _ = _seg_dep_arr(b[i + 1])
        if not ar or not d2 or ar != d2:
            return False
    _, b_last_arr = _seg_dep_arr(b[-1])
    return b_last_arr == orig


def _find_round_trip_split_equal_halves(vendor_segments: list[Any]) -> int | None:
    """Split after first half of segments when length is even and partition is a valid RT."""
    n = len(vendor_segments)
    if n < 2 or n % 2 != 0:
        return None
    orig, _ = _seg_dep_arr(vendor_segments[0])
    _, last_arr = _seg_dep_arr(vendor_segments[-1])
    if not orig or not last_arr or last_arr != orig:
        return None
    mid = n // 2
    a = vendor_segments[:mid]
    b = vendor_segments[mid:]
    if _rt_partition_valid(a, b, orig):
        return mid
    return None


def _find_round_trip_split_index(vendor_segments: list[Any]) -> int | None:
    """First index of return leg: partition connects and last arrival equals origin."""
    n = len(vendor_segments)
    if n < 2:
        return None
    orig, _ = _seg_dep_arr(vendor_segments[0])
    _, last_arr = _seg_dep_arr(vendor_segments[-1])
    if not orig or not last_arr or last_arr != orig:
        return None
    for k in range(1, n):
        a = vendor_segments[:k]
        b = vendor_segments[k:]
        if _rt_partition_valid(a, b, orig):
            return k
    return None


def _find_round_trip_split_at_destination_arrival(
    vendor_segments: list[Any],
    primary_destination_iata: str | None,
) -> int | None:
    """Split after the first segment whose arrival is the primary destination (far end)."""
    if not primary_destination_iata or not vendor_segments:
        return None
    dest = _norm_iata(primary_destination_iata)
    if not dest:
        return None
    orig, _ = _seg_dep_arr(vendor_segments[0])
    _, last_arr = _seg_dep_arr(vendor_segments[-1])
    if not orig or not last_arr or last_arr != orig:
        return None
    for i, seg in enumerate(vendor_segments):
        _, arr = _seg_dep_arr(seg)
        if arr == dest:
            k = i + 1
            if 0 < k < len(vendor_segments):
                a = vendor_segments[:k]
                b = vendor_segments[k:]
                if _rt_partition_valid(a, b, orig):
                    return k
    return None


def build_route_legs_from_revalidate(
    cached_revalidate: Any,
    *,
    multistay_leg_index: int | None = None,
) -> tuple[list[RouteLeg], FlightTripTypeLiteral | None]:
    """Walk validated fare itinerary legs/segments into structured route legs + trip type."""
    if not cached_revalidate or not getattr(
        cached_revalidate, "validated_fare_itineraries", None
    ):
        return [], None
    itin = cached_revalidate.validated_fare_itineraries[0]
    legs = getattr(itin, "flight_legs", None) or []
    jt = _journey_type_str(itin)

    if multistay_leg_index is not None and 0 <= multistay_leg_index < len(legs):
        leg = legs[multistay_leg_index]
        segs = getattr(leg, "flight_segments", None) or []
        built = _leg_from_vendor_segments(list(segs), 0)
        if built:
            return [built], "multi_city"
        return [], None

    if not legs:
        return [], None

    if jt == "OneWay":
        segs0 = getattr(legs[0], "flight_segments", None) or []
        built = _leg_from_vendor_segments(list(segs0), 0)
        if built:
            return [built], "one_way"
        return [], None

    if jt == "Return":
        if len(legs) >= 2:
            if len(legs) == 2:
                out: list[RouteLeg] = []
                for idx, lg in enumerate(legs):
                    segs = getattr(lg, "flight_segments", None) or []
                    blt = _leg_from_vendor_segments(list(segs), idx)
                    if blt:
                        out.append(blt)
                if len(out) == 2:
                    return out, "round_trip"
            else:
                if len(legs) % 2 == 0:
                    mid = len(legs) // 2
                    flat_o: list[Any] = []
                    for lg in legs[:mid]:
                        flat_o.extend(list(getattr(lg, "flight_segments", None) or []))
                    flat_r: list[Any] = []
                    for lg in legs[mid:]:
                        flat_r.extend(list(getattr(lg, "flight_segments", None) or []))
                    ao = _leg_from_vendor_segments(flat_o, 0)
                    br = _leg_from_vendor_segments(flat_r, 1)
                    if ao and br:
                        return [ao, br], "round_trip"
                flat: list[Any] = []
                for lg in legs:
                    flat.extend(list(getattr(lg, "flight_segments", None) or []))
                split = _find_round_trip_split_equal_halves(flat)
                if split is None:
                    split = _find_round_trip_split_index(flat)
                if split is not None:
                    a = _leg_from_vendor_segments(flat[:split], 0)
                    b = _leg_from_vendor_segments(flat[split:], 1)
                    if a and b:
                        return [a, b], "round_trip"
        if len(legs) == 1:
            segs = list(getattr(legs[0], "flight_segments", None) or [])
            if len(segs) == 2:
                a = _leg_from_vendor_segments([segs[0]], 0)
                b = _leg_from_vendor_segments([segs[1]], 1)
                if a and b:
                    return [a, b], "round_trip"
            if len(segs) >= 2:
                split = _find_round_trip_split_equal_halves(segs)
                if split is None:
                    split = _find_round_trip_split_index(segs)
                if split is not None:
                    a = _leg_from_vendor_segments(segs[:split], 0)
                    b = _leg_from_vendor_segments(segs[split:], 1)
                    if a and b:
                        return [a, b], "round_trip"
            built = _leg_from_vendor_segments(segs, 0)
            if built:
                # Unsplittable Return (e.g. open-jaw): one leg only — label as one_way so UIs
                # that expect two legs for round_trip are not misled.
                return [built], "one_way"
        return [], None

    if jt == "Circle":
        out_mc: list[RouteLeg] = []
        for idx, lg in enumerate(legs):
            segs = getattr(lg, "flight_segments", None) or []
            blt = _leg_from_vendor_segments(list(segs), idx)
            if blt:
                out_mc.append(blt)
        if out_mc:
            return out_mc, "multi_city"
        return [], None

    # Unknown journey type: best-effort single leg
    segs0 = getattr(legs[0], "flight_segments", None) or []
    built = _leg_from_vendor_segments(list(segs0), 0)
    if built:
        return [built], "one_way"
    return [], None


@dataclass(frozen=True)
class RouteBookingSnapshot:
    """Persisted flight route + marketing carrier for booking_events list UIs."""

    flight_trip_type: FlightTripTypeLiteral | None = None
    route_legs: tuple[RouteLeg, ...] = ()
    primary_marketing_airline_name: str | None = None


def extract_route_and_airline_snapshot(
    cached_revalidate: Any,
    *,
    multistay_leg_index: int | None = None,
    pnr_airline_name: str | None = None,
) -> RouteBookingSnapshot:
    """Derive structured route + marketing airline from revalidate cache at booking time."""
    route_legs_list, trip_type = build_route_legs_from_revalidate(
        cached_revalidate,
        multistay_leg_index=multistay_leg_index,
    )
    marketing: str | None = None
    if cached_revalidate and getattr(
        cached_revalidate, "validated_fare_itineraries", None
    ):
        itin = cached_revalidate.validated_fare_itineraries[0]
        legs = getattr(itin, "flight_legs", None) or []
        pick_leg_idx = (
            multistay_leg_index
            if multistay_leg_index is not None
            and legs
            and multistay_leg_index < len(legs)
            else 0
        )
        if legs and pick_leg_idx < len(legs):
            segs = getattr(legs[pick_leg_idx], "flight_segments", None) or []
            if segs:
                marketing = _marketing_name_from_segment(segs[0])
    if not marketing and pnr_airline_name and pnr_airline_name.strip():
        marketing = pnr_airline_name.strip()
    if not route_legs_list:
        logger.debug(
            "Route snapshot: no route legs from revalidate (fare cache empty or missing legs)"
        )
        return RouteBookingSnapshot(
            primary_marketing_airline_name=marketing,
        )
    return RouteBookingSnapshot(
        flight_trip_type=trip_type,
        route_legs=tuple(route_legs_list),
        primary_marketing_airline_name=marketing,
    )


def _trip_details_pick_rt_split(
    vendor_segs: list[Any], trip_details: Any
) -> int | None:
    """Prefer primary-destination arrival, then equal halves, then first graph-valid split."""
    dest = getattr(getattr(trip_details, "destination", None), "iata_code", None)
    sp = _find_round_trip_split_at_destination_arrival(vendor_segs, dest)
    if sp is not None:
        return sp
    sp = _find_round_trip_split_equal_halves(vendor_segs)
    if sp is not None:
        return sp
    return _find_round_trip_split_index(vendor_segs)


def _td_segment_airline_name(seg: Any) -> str | None:
    ma = getattr(seg, "marketing_airline", None)
    if ma is None:
        return None
    name = getattr(ma, "airline_name", None)
    if name and str(name).strip():
        return str(name).strip()
    return None


def extract_route_fields_from_trip_details(
    trip_details: Any,
) -> dict[str, Any]:
    """Build Mongo $set fields from trip-details (overwrite when parsing succeeds).

    Does not populate removed flat arrival/return IATA keys; uses ``route_legs`` +
    ``flight_trip_type`` + ``departure_airport_iata`` (first hop, for TTL legacy readers).
    """
    if trip_details is None:
        return {}
    out: dict[str, Any] = {}

    segs_raw = getattr(trip_details, "segments", None) or []
    if not segs_raw:
        origin_obj = getattr(trip_details, "origin", None)
        origin = (
            getattr(origin_obj, "iata_code", None) if origin_obj is not None else None
        )
        dep_iata = _norm_iata(origin)
        if dep_iata:
            out["departure_airport_iata"] = dep_iata
        return out

    vendor_segs = list(segs_raw)
    route_segs = _route_segments_from_vendor_segments(vendor_segs)
    if not route_segs:
        return out

    first = vendor_segs[0]
    trip_type: FlightTripTypeLiteral | None = None
    legs: list[RouteLeg] = []

    if len(route_segs) == 1:
        legs = [
            RouteLeg(
                leg_index=0,
                departure_iata=route_segs[0].departure_iata,
                arrival_iata=route_segs[0].arrival_iata,
                segment_count=1,
                segments=route_segs,
            )
        ]
        trip_type = "one_way"
    elif len(route_segs) == 2:
        a, b = route_segs[0], route_segs[1]
        if a.departure_iata == b.arrival_iata and a.arrival_iata == b.departure_iata:
            legs = [
                RouteLeg(
                    leg_index=0,
                    departure_iata=a.departure_iata,
                    arrival_iata=a.arrival_iata,
                    segment_count=1,
                    segments=[a],
                ),
                RouteLeg(
                    leg_index=1,
                    departure_iata=b.departure_iata,
                    arrival_iata=b.arrival_iata,
                    segment_count=1,
                    segments=[b],
                ),
            ]
            trip_type = "round_trip"
        else:
            split = _trip_details_pick_rt_split(vendor_segs, trip_details)
            if split is not None:
                rs_a = _route_segments_from_vendor_segments(vendor_segs[:split])
                rs_b = _route_segments_from_vendor_segments(vendor_segs[split:])
                if rs_a and rs_b:
                    legs = [
                        RouteLeg(
                            leg_index=0,
                            departure_iata=rs_a[0].departure_iata,
                            arrival_iata=rs_a[-1].arrival_iata,
                            segment_count=len(rs_a),
                            segments=rs_a,
                        ),
                        RouteLeg(
                            leg_index=1,
                            departure_iata=rs_b[0].departure_iata,
                            arrival_iata=rs_b[-1].arrival_iata,
                            segment_count=len(rs_b),
                            segments=rs_b,
                        ),
                    ]
                    trip_type = "round_trip"
            if not legs:
                legs = [
                    RouteLeg(
                        leg_index=0,
                        departure_iata=route_segs[0].departure_iata,
                        arrival_iata=route_segs[-1].arrival_iata,
                        segment_count=len(route_segs),
                        segments=route_segs,
                    )
                ]
                trip_type = "one_way"
    else:
        split = _trip_details_pick_rt_split(vendor_segs, trip_details)
        if split is not None:
            rs_a = _route_segments_from_vendor_segments(vendor_segs[:split])
            rs_b = _route_segments_from_vendor_segments(vendor_segs[split:])
            if rs_a and rs_b:
                legs = [
                    RouteLeg(
                        leg_index=0,
                        departure_iata=rs_a[0].departure_iata,
                        arrival_iata=rs_a[-1].arrival_iata,
                        segment_count=len(rs_a),
                        segments=rs_a,
                    ),
                    RouteLeg(
                        leg_index=1,
                        departure_iata=rs_b[0].departure_iata,
                        arrival_iata=rs_b[-1].arrival_iata,
                        segment_count=len(rs_b),
                        segments=rs_b,
                    ),
                ]
                trip_type = "round_trip"
        if not legs:
            legs = [
                RouteLeg(
                    leg_index=0,
                    departure_iata=route_segs[0].departure_iata,
                    arrival_iata=route_segs[-1].arrival_iata,
                    segment_count=len(route_segs),
                    segments=route_segs,
                )
            ]
            trip_type = "one_way"

    out["route_legs"] = [lg.model_dump() for lg in legs]
    if trip_type:
        out["flight_trip_type"] = trip_type

    dep_ttl = departure_iata_from_route_legs(legs)
    if dep_ttl:
        out["departure_airport_iata"] = dep_ttl

    airline_name = _td_segment_airline_name(first)
    if not airline_name and getattr(first, "airline_pnr", None) is not None:
        al = getattr(first.airline_pnr, "airline", None)
        if al is not None:
            nm = getattr(al, "airline_name", None)
            if nm and str(nm).strip():
                airline_name = str(nm).strip()
    if airline_name:
        out["primary_marketing_airline_name"] = airline_name

    return out
