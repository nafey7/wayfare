"""Flight scoring utilities.

Single best-value scoring function (penalty-based, lower is better):
    S = (Price_norm * WEIGHT_PRICE) + (Duration_norm * WEIGHT_DURATION)
        + Time_Penalty
        - (preference_score * PREFERENCE_WEIGHT)   # optional bias when user has saved prefs

Preference helpers (additive, 0–3 — used as a soft bias inside best-value):
    pref_score = airline_match (0|1) + stops_match (0|1) + departure_window_match (0|1)

Per issue #1034: ``sort_flights_by_best_value`` is the **only** public sort
function. Preferences become a soft bias inside it (mirrors how
``sort_hotels_by_best_value`` already works) — no separate sort algorithm.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domains.user_preferences.schemas import FlightsPreferences

# Weights for normalized price and duration (must sum to 1.0 for consistent scale)
WEIGHT_PRICE = 0.60
WEIGHT_DURATION = 0.40

# Flat modifiers for undesirable times (local time) – outbound leg
TIME_PENALTY_RED_EYE_DEPARTURE = 0.15  # Outbound departure 23:00–07:00
TIME_PENALTY_LATE_NIGHT_ARRIVAL = 0.15  # Outbound arrival 23:00–07:00
# Return leg (lower weight when present)
TIME_PENALTY_RED_EYE_DEPARTURE_RETURN = 0.10  # Return departure 23:00–07:00
TIME_PENALTY_LATE_NIGHT_ARRIVAL_RETURN = 0.10  # Return arrival 23:00–07:00

# Preference bias: how much each matched preference dimension (0–3 total)
# reduces the penalty score. With base scores in roughly [0, 2.5] range and
# pref_score 0–3, this contributes up to 0.30 of bias — meaningful but not
# dominant. Keeps the "best value" algorithm in charge; preferences merely
# break ties or rerank close candidates.
PREFERENCE_WEIGHT = 0.10


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to [0, 1] range. Returns 0 if min_val == max_val."""
    if min_val == max_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def _is_red_eye_or_late_night(hour: int | None) -> bool:
    """True if hour is in 23:00–07:00 range (23, 0, 1, 2, 3, 4, 5, 6)."""
    if hour is None:
        return False
    return hour >= 23 or hour < 7


def _time_penalty(
    departure_hour: int | None,
    arrival_hour: int | None,
    return_departure_hour: int | None = None,
    return_arrival_hour: int | None = None,
) -> float:
    """Sum of outbound and return red-eye/late-night penalties.

    Outbound: +0.15 each for dep/arr in 23:00–07:00. Return (if present): +0.10 each.
    """
    penalty = 0.0
    if _is_red_eye_or_late_night(departure_hour):
        penalty += TIME_PENALTY_RED_EYE_DEPARTURE
    if _is_red_eye_or_late_night(arrival_hour):
        penalty += TIME_PENALTY_LATE_NIGHT_ARRIVAL
    if return_departure_hour is not None and _is_red_eye_or_late_night(
        return_departure_hour
    ):
        penalty += TIME_PENALTY_RED_EYE_DEPARTURE_RETURN
    if return_arrival_hour is not None and _is_red_eye_or_late_night(
        return_arrival_hour
    ):
        penalty += TIME_PENALTY_LATE_NIGHT_ARRIVAL_RETURN
    return penalty


def hour_from_time_str(time_str: str | None) -> int | None:
    """Parse 'HH:MM' or 'HH:MM:SS' string to hour (0–23). Returns None if invalid."""
    if not time_str or not isinstance(time_str, str):
        return None
    parts = time_str.strip().split(":")
    if not parts:
        return None
    try:
        return int(parts[0]) % 24
    except (ValueError, TypeError):
        return None


def hour_from_datetime(dt: Any) -> int | None:
    """Extract hour (0–23) from datetime-like object (may have .value). Returns None if missing."""
    if dt is None:
        return None
    if hasattr(dt, "value"):
        dt = dt.value
    if hasattr(dt, "hour"):
        return int(dt.hour) % 24
    if isinstance(dt, str):
        try:
            from datetime import datetime as dt_cls

            parsed = dt_cls.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.hour % 24
        except Exception:
            return None
    return None


def compute_penalty_score(
    price: float,
    duration: float,
    departure_hour: int | None,
    arrival_hour: int | None,
    min_price: float,
    max_price: float,
    min_duration: float,
    max_duration: float,
    return_departure_hour: int | None = None,
    return_arrival_hour: int | None = None,
) -> float:
    """Compute best-value penalty score for one flight. Lower is better.

    Uses normalized price and duration plus time penalties (outbound + return if present).
    Returns float('inf') for invalid inputs so they sort last.
    """
    # Treat sentinel values as invalid so they sort last
    if price == float("inf") or price < 0:
        return float("inf")
    if duration == float("inf") or duration < 0 or duration >= 999999:
        return float("inf")
    if min_price == float("inf"):
        return float("inf")

    price_norm = _normalize(price, min_price, max_price)
    duration_norm = _normalize(duration, min_duration, max_duration)
    time_penalty = _time_penalty(
        departure_hour,
        arrival_hour,
        return_departure_hour=return_departure_hour,
        return_arrival_hour=return_arrival_hour,
    )

    return (
        (price_norm * WEIGHT_PRICE) + (duration_norm * WEIGHT_DURATION) + time_penalty
    )


def sort_flights_by_best_value(
    flights: list[Any],
    get_price: Callable[[Any], float],
    get_duration: Callable[[Any], float],
    get_departure_hour: Callable[[Any], int | None],
    get_arrival_hour: Callable[[Any], int | None],
    get_return_departure_hour: Callable[[Any], int | None] | None = None,
    get_return_arrival_hour: Callable[[Any], int | None] | None = None,
    user_preferences: "FlightsPreferences | None" = None,
) -> list[Any]:
    """Sort flights by ascending penalty score (best first). Returns new list.

    If get_return_departure_hour/get_return_arrival_hour are provided, return-leg
    time penalties (+0.10 each) are applied when present.

    If ``user_preferences`` is provided, each preference dimension that matches
    (preferred airline, max stops, departure window) reduces the penalty score
    by ``PREFERENCE_WEIGHT`` — see module docstring. Mirrors the
    preference-aware behavior of ``sort_hotels_by_best_value``.
    """
    if not flights:
        return []

    prices = [get_price(f) for f in flights]
    durations = [get_duration(f) for f in flights]

    min_price = min(prices)
    max_price = max(prices)
    min_duration = min(durations)
    max_duration = max(durations)

    def _return_dep(f: Any) -> int | None:
        return get_return_departure_hour(f) if get_return_departure_hour else None

    def _return_arr(f: Any) -> int | None:
        return get_return_arrival_hour(f) if get_return_arrival_hour else None

    def score(flight: Any) -> float:
        base = compute_penalty_score(
            get_price(flight),
            get_duration(flight),
            get_departure_hour(flight),
            get_arrival_hour(flight),
            min_price,
            max_price,
            min_duration,
            max_duration,
            return_departure_hour=_return_dep(flight),
            return_arrival_hour=_return_arr(flight),
        )
        if user_preferences is not None and isinstance(flight, dict):
            pref = compute_preference_score(flight, user_preferences)
            base -= pref * PREFERENCE_WEIGHT
        return base

    return sorted(flights, key=score)


# ---------------------------------------------------------------------------
# Preference scoring (0–3 additive, higher = better match)
# ---------------------------------------------------------------------------


def _time_str_to_minutes(time_str: str | None) -> int | None:
    """Parse 'HH:MM' or 'HH:MM:SS' to minutes since midnight. Hour is taken mod 24. Returns None if invalid."""
    if not time_str or not isinstance(time_str, str):
        return None
    parts = time_str.strip().split(":")
    if len(parts) < 2:
        return None
    try:
        h = int(parts[0]) % 24
        m = int(parts[1])
        return h * 60 + m
    except (ValueError, TypeError):
        return None


def _score_preferred_airlines(
    flight: dict[str, Any], preferred_airlines: list[str]
) -> int:
    """Return 1 if the flight's airline matches any preference, else 0."""
    if not preferred_airlines:
        return 0
    airline_code = (flight.get("airline_code") or "").lower()
    airline_name = (flight.get("airline") or "").lower()
    for pref in preferred_airlines:
        pref_lower = pref.lower()
        if airline_code and airline_code == pref_lower:
            return 1
        if airline_name and pref_lower in airline_name:
            return 1
    return 0


def _score_max_stops(flight: dict[str, Any], max_stops: str | None) -> int:
    """Return 1 if the flight's stop count meets the max_stops preference, else 0."""
    if not max_stops or max_stops == "any":
        return 0
    stops = flight.get("stops")
    if stops is None:
        return 0
    if max_stops == "nonstop" and stops == 0:
        return 1
    if max_stops == "1stop" and stops <= 1:
        return 1
    if max_stops == "2stops" and stops <= 2:
        return 1
    return 0


def _score_departure_window(flight: dict[str, Any], departure_window: list[str]) -> int:
    """Return 1 if the first-leg departure time falls within the preferred window, else 0.

    Handles midnight-spanning windows (e.g. ["22:00", "06:00"]).
    Returns 0 if the window covers the full day (no meaningful preference).
    """
    if len(departure_window) < 2:
        return 0
    min_minutes = _time_str_to_minutes(departure_window[0])
    max_minutes = _time_str_to_minutes(departure_window[1])
    if min_minutes is None or max_minutes is None:
        return 0
    # Full-day window — no real preference expressed
    if min_minutes == 0 and max_minutes == 23 * 60 + 59:
        return 0
    dep_minutes = _time_str_to_minutes(flight.get("departure_time"))
    if dep_minutes is None:
        return 0
    # Midnight-spanning window (e.g. 22:00–06:00)
    if min_minutes > max_minutes:
        return 1 if (dep_minutes >= min_minutes or dep_minutes <= max_minutes) else 0
    return 1 if (min_minutes <= dep_minutes <= max_minutes) else 0


def compute_preference_score(
    flight: dict[str, Any],
    prefs: "FlightsPreferences | None",
) -> int:
    """Compute preference score (0–3) for a flight dict.

    Each of the three dimensions (airline, stops, departure window) contributes 0 or 1.
    Returns 0 when prefs is None (unauthenticated or no saved preferences).
    """
    if prefs is None:
        return 0
    return (
        _score_preferred_airlines(flight, prefs.preferred_airlines or [])
        + _score_max_stops(flight, prefs.max_stops)
        + _score_departure_window(flight, prefs.departure_window or ["00:00", "23:59"])
    )


# NOTE (issue #1034): ``sort_flights_by_preference`` was removed. Preference
# bias is now a soft input to ``sort_flights_by_best_value`` (see the
# ``user_preferences`` parameter) — mirrors the unified scoring shape of
# ``sort_hotels_by_best_value``. ``compute_preference_score`` and its helpers
# (``_score_preferred_airlines``, ``_score_max_stops``, ``_score_departure_window``,
# ``_time_str_to_minutes``) are still used **internally** by best-value.
