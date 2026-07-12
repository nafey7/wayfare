"""Journey type normalization and booking-session route params from flight payloads."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from .enums import JourneyType

logger = logging.getLogger(__name__)

# Values accepted from FlightLogic / domain payloads for booking-session route extraction.
_KNOWN_BOOKING_JOURNEY_TYPE_VALUES = frozenset(
    {
        JourneyType.ONE_WAY.value,
        JourneyType.RETURN.value,
        JourneyType.CIRCLE.value,
    }
)


def normalize_fl_api_journey_type(raw: Any) -> str:
    """Normalize FlightLogic / domain journey type for comparison and URLs.

    Maps legacy ``RoundTrip`` to ``Return``. Returns ``""`` if missing.
    """
    if raw is None:
        return ""
    if isinstance(raw, JourneyType):
        return raw.value
    s = str(raw).strip()
    if not s:
        return ""
    if s == "RoundTrip":
        return JourneyType.RETURN.value
    return s


def _journey_type_for_booking_route_extraction(raw: Any) -> str:
    """Like :func:`normalize_fl_api_journey_type` but returns ``\"\"`` for unknown strings.

    Unrecognized values are logged and dropped so multi-leg payloads fall back to
    topology inference instead of being misclassified as Return.
    """
    s = normalize_fl_api_journey_type(raw)
    if not s:
        return ""
    if s not in _KNOWN_BOOKING_JOURNEY_TYPE_VALUES:
        logger.warning(
            "Unknown journey_type %r in flight payload for booking search_params; "
            "treating as missing for topology inference",
            raw,
        )
        return ""
    return s


def normalize_search_redirect_journey_type(
    raw: str | None,
    *,
    has_return_date: bool,
) -> str:
    """Normalize journey type for flight-booker redirect URLs (``search_redirect`` semantics)."""
    s = (raw or "").strip()
    if s == "RoundTrip":
        return JourneyType.RETURN.value
    if s in ("OneWay", "Return", "Circle"):
        return s
    return JourneyType.RETURN.value if has_return_date else JourneyType.ONE_WAY.value


def _segment_to_dict(seg: Any) -> dict[str, Any]:
    if isinstance(seg, dict):
        return seg
    if hasattr(seg, "model_dump"):
        return seg.model_dump()
    raise ValueError(f"Unsupported segment type: {type(seg)!r}")


def coerce_legacy_flight_search_request_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Map deprecated shapes to the current FlightLogic contract.

    - ``journey_type: \"RoundTrip\"`` → ``Return``
    - ``Return`` with a single ``origin_destination_info`` row and ``return_date`` on that row
      → split into two O&D rows (outbound + inbound). Logs a deprecation warning.
    """
    out = dict(data)

    jt_raw = out.get("journey_type")
    if jt_raw == "RoundTrip":
        out["journey_type"] = JourneyType.RETURN.value
        jt_raw = out["journey_type"]

    is_return = jt_raw == JourneyType.RETURN or (
        isinstance(jt_raw, str) and jt_raw.strip() == JourneyType.RETURN.value
    )
    if not is_return:
        return out

    ods = out.get("origin_destination_info")
    if not isinstance(ods, list) or len(ods) != 1:
        return out

    s0 = _segment_to_dict(ods[0])
    rd = s0.get("return_date")
    if rd is None:
        return out

    orig_ap = s0.get("origin_airport")
    dest_ap = s0.get("destination_airport")
    if orig_ap is None or dest_ap is None:
        raise ValueError(
            "Deprecated single-row Return with return_date requires origin_airport and "
            "destination_airport on the segment."
        )
    outbound = deepcopy(s0)
    outbound["return_date"] = None
    inbound = {
        "departure_date": rd,
        "return_date": None,
        "origin_airport": deepcopy(dest_ap),
        "destination_airport": deepcopy(orig_ap),
    }
    out["origin_destination_info"] = [outbound, inbound]
    logger.warning(
        "Deprecated: Return journey sent as one origin_destination_info row with "
        "return_date on that row; split into two legs server-side. "
        "Send two origin_destination_info entries for Return searches."
    )
    return out


def _iata(seg: dict[str, Any], airport_key: str) -> str:
    ap = seg.get(airport_key) or {}
    if hasattr(ap, "model_dump"):
        ap = ap.model_dump()
    return str((ap or {}).get("iata_code", "") or "").upper()


def _date_part_from_dep_datetime(dep: Any) -> str | None:
    if dep is None:
        return None
    if isinstance(dep, str):
        return dep.split("T")[0]
    return str(dep).split("T")[0]


def build_airport_chain_from_flight_legs(
    flight_legs: list[dict[str, Any]],
) -> list[str]:
    """Ordered IATA codes along all segments (multi-leg and multi-segment)."""
    chain: list[str] = []
    first_seg = True
    for leg in flight_legs:
        for seg in leg.get("flight_segments", []) or []:
            dep_a = _iata(seg, "departure_airport")
            arr_a = _iata(seg, "arrival_airport")
            if first_seg and dep_a:
                chain.append(dep_a)
                first_seg = False
            if arr_a:
                chain.append(arr_a)
    return chain


def is_return_two_leg_topology(flight_legs: list[dict[str, Any]]) -> bool:
    """True if the first two legs look like outbound + return (A→B, B→A)."""
    if len(flight_legs) < 2:
        return False
    segs0 = flight_legs[0].get("flight_segments") or []
    segs1 = flight_legs[1].get("flight_segments") or []
    if not segs0 or not segs1:
        return False
    first_dep = _iata(segs0[0], "departure_airport")
    first_arr = _iata(segs0[-1], "arrival_airport")
    second_dep = _iata(segs1[0], "departure_airport")
    second_arr = _iata(segs1[-1], "arrival_airport")
    if not all((first_dep, first_arr, second_dep, second_arr)):
        return False
    return first_dep == second_arr and first_arr == second_dep


def infer_journey_type_when_missing(
    flight_legs: list[dict[str, Any]],
) -> str | None:
    """Infer ``Return`` or ``Circle`` when ``journey_type`` is absent from the payload."""
    if len(flight_legs) < 2:
        return None
    if is_return_two_leg_topology(flight_legs):
        return JourneyType.RETURN.value
    logger.debug(
        "Inferred journey_type=%s from multi-leg itinerary (journey_type missing in payload)",
        JourneyType.CIRCLE.value,
    )
    return JourneyType.CIRCLE.value


def build_booking_search_route_params_from_flight_dict(
    flight_dict: dict[str, Any],
) -> dict[str, Any]:
    """Extract origin/destination/dates/journey_type/airport_codes_chain for booking session storage.

    Uses :func:`normalize_fl_api_journey_type` for ``RoundTrip`` → ``Return``.
    Unknown ``journey_type`` strings are ignored (with a warning) so multi-leg payloads
    use topology inference instead of being treated as Return.
    When ``journey_type`` is missing, infers ``Return`` vs ``Circle`` from leg topology
    (two legs forming A→B / B→A vs multi-leg open jaw).
    """
    search_params: dict[str, Any] = {}
    flight_legs = flight_dict.get("flight_legs") or []
    jt_str = _journey_type_for_booking_route_extraction(flight_dict.get("journey_type"))

    if not flight_legs:
        if jt_str:
            search_params["journey_type"] = jt_str
        return search_params

    first_leg = flight_legs[0]
    segments = first_leg.get("flight_segments") or []
    if not segments:
        if jt_str:
            search_params["journey_type"] = jt_str
        return search_params

    first_segment = segments[0]
    last_segment = segments[-1]

    dep_airport = first_segment.get("departure_airport", {})
    if hasattr(dep_airport, "model_dump"):
        dep_airport = dep_airport.model_dump()
    if dep_airport:
        search_params["origin"] = dep_airport.get("iata_code", "")

    arr_airport = last_segment.get("arrival_airport", {})
    if hasattr(arr_airport, "model_dump"):
        arr_airport = arr_airport.model_dump()
    if arr_airport:
        search_params["destination"] = arr_airport.get("iata_code", "")

    dep_datetime = first_segment.get("departure_datetime")
    if dep_datetime:
        dp = _date_part_from_dep_datetime(dep_datetime)
        if dp:
            search_params["departure_date"] = dp

    effective_jt = jt_str
    if not effective_jt:
        inferred = infer_journey_type_when_missing(flight_legs)
        if inferred:
            effective_jt = inferred

    if effective_jt == JourneyType.CIRCLE.value:
        search_params["journey_type"] = JourneyType.CIRCLE.value
        airport_chain = build_airport_chain_from_flight_legs(flight_legs)
        if airport_chain:
            search_params["airport_codes_chain"] = airport_chain
        return search_params

    if len(flight_legs) > 1:
        if effective_jt == JourneyType.ONE_WAY.value:
            search_params["journey_type"] = JourneyType.ONE_WAY.value
            return search_params
        return_leg = flight_legs[1]
        return_segments = return_leg.get("flight_segments") or []
        if return_segments:
            return_first = return_segments[0]
            return_dep_datetime = return_first.get("departure_datetime")
            if return_dep_datetime:
                rd = _date_part_from_dep_datetime(return_dep_datetime)
                if rd:
                    search_params["return_date"] = rd
            search_params["journey_type"] = JourneyType.RETURN.value
        else:
            search_params["journey_type"] = (
                JourneyType.RETURN.value
                if effective_jt == JourneyType.RETURN.value
                else JourneyType.ONE_WAY.value
            )
        return search_params

    if effective_jt == JourneyType.RETURN.value:
        search_params["journey_type"] = JourneyType.RETURN.value
        return search_params

    search_params["journey_type"] = JourneyType.ONE_WAY.value
    return search_params
