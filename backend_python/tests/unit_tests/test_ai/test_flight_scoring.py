"""Tests for flight_scoring module: normalized penalty score and time penalties."""

from app.ai.flight_scoring import (
    TIME_PENALTY_LATE_NIGHT_ARRIVAL,
    TIME_PENALTY_LATE_NIGHT_ARRIVAL_RETURN,
    TIME_PENALTY_RED_EYE_DEPARTURE,
    TIME_PENALTY_RED_EYE_DEPARTURE_RETURN,
    WEIGHT_DURATION,
    WEIGHT_PRICE,
    _score_departure_window,
    _score_max_stops,
    _score_preferred_airlines,
    _time_str_to_minutes,
    compute_penalty_score,
    compute_preference_score,
    hour_from_time_str,
    sort_flights_by_best_value,
)
from app.domains.user_preferences.schemas import FlightsPreferences


class TestWeights:
    """Weights are stored in variables and sum to 1.0."""

    def test_weights_sum_to_one(self):
        assert abs((WEIGHT_PRICE + WEIGHT_DURATION) - 1.0) < 1e-9

    def test_weight_price_is_060(self):
        assert WEIGHT_PRICE == 0.60

    def test_weight_duration_is_040(self):
        assert WEIGHT_DURATION == 0.40

    def test_outbound_time_penalties_are_015(self):
        assert TIME_PENALTY_RED_EYE_DEPARTURE == 0.15
        assert TIME_PENALTY_LATE_NIGHT_ARRIVAL == 0.15

    def test_return_leg_time_penalties_are_010(self):
        assert TIME_PENALTY_RED_EYE_DEPARTURE_RETURN == 0.10
        assert TIME_PENALTY_LATE_NIGHT_ARRIVAL_RETURN == 0.10


class TestNormalization:
    """Normalization: (value - min) / (max - min), 0 if min == max."""

    def test_compute_penalty_score_normalization(self):
        # Same price range, different durations: lower duration => lower duration_norm => lower score
        # min_p=100, max_p=200, min_d=60, max_d=120
        # Flight A: price=100, duration=60 -> price_norm=0, duration_norm=0 -> score=0
        score_a = compute_penalty_score(100, 60, None, None, 100, 200, 60, 120)
        assert score_a == 0.0

        # Flight B: price=200, duration=120 -> price_norm=1, duration_norm=1 -> score=1
        score_b = compute_penalty_score(200, 120, None, None, 100, 200, 60, 120)
        assert abs(score_b - 1.0) < 1e-9

        # Flight C: price=150, duration=90 -> price_norm=0.5, duration_norm=0.5 -> score=0.5
        score_c = compute_penalty_score(150, 90, None, None, 100, 200, 60, 120)
        assert abs(score_c - 0.5) < 1e-9

    def test_min_equals_max_normalization(self):
        # When min == max, normalized value is 0 (avoid division by zero)
        score = compute_penalty_score(100, 60, None, None, 100, 100, 60, 60)
        assert score == 0.0


class TestTimePenalty:
    """Red-eye (23:00–07:00) adds +0.15 for departure and/or arrival."""

    def test_red_eye_departure_adds_penalty(self):
        # Hour 23 or 0,1,2,3,4,5,6 = red-eye / late-night
        score_night = compute_penalty_score(100, 60, 23, 12, 100, 200, 60, 120)
        score_day = compute_penalty_score(100, 60, 10, 12, 100, 200, 60, 120)
        assert abs(score_night - score_day - TIME_PENALTY_RED_EYE_DEPARTURE) < 1e-9

    def test_late_night_arrival_adds_penalty(self):
        score_night = compute_penalty_score(100, 60, 10, 1, 100, 200, 60, 120)
        score_day = compute_penalty_score(100, 60, 10, 12, 100, 200, 60, 120)
        assert abs(score_night - score_day - TIME_PENALTY_LATE_NIGHT_ARRIVAL) < 1e-9

    def test_both_red_eye_adds_both_penalties(self):
        score_both = compute_penalty_score(100, 60, 2, 3, 100, 200, 60, 120)
        score_none = compute_penalty_score(100, 60, 10, 14, 100, 200, 60, 120)
        expected_extra = (
            TIME_PENALTY_RED_EYE_DEPARTURE + TIME_PENALTY_LATE_NIGHT_ARRIVAL
        )
        assert abs(score_both - score_none - expected_extra) < 1e-9

    def test_return_leg_red_eye_adds_010(self):
        """Return leg departure 23:00–07:00 adds +0.10 (not +0.15)."""
        score_with_return_red_eye = compute_penalty_score(
            100,
            60,
            10,
            14,
            100,
            200,
            60,
            120,
            return_departure_hour=2,
            return_arrival_hour=14,
        )
        score_without_return_red_eye = compute_penalty_score(
            100,
            60,
            10,
            14,
            100,
            200,
            60,
            120,
            return_departure_hour=10,
            return_arrival_hour=14,
        )
        assert (
            abs(
                score_with_return_red_eye
                - score_without_return_red_eye
                - TIME_PENALTY_RED_EYE_DEPARTURE_RETURN
            )
            < 1e-9
        )

    def test_return_leg_late_night_arrival_adds_010(self):
        """Return leg arrival 23:00–07:00 adds +0.10 (not +0.15)."""
        score_with_return_late = compute_penalty_score(
            100,
            60,
            10,
            14,
            100,
            200,
            60,
            120,
            return_departure_hour=10,
            return_arrival_hour=1,
        )
        score_without = compute_penalty_score(
            100,
            60,
            10,
            14,
            100,
            200,
            60,
            120,
            return_departure_hour=10,
            return_arrival_hour=14,
        )
        assert (
            abs(
                score_with_return_late
                - score_without
                - TIME_PENALTY_LATE_NIGHT_ARRIVAL_RETURN
            )
            < 1e-9
        )


class TestHourFromTimeStr:
    """Parse 'HH:MM' to hour (0-23)."""

    def test_valid_string(self):
        assert hour_from_time_str("23:45") == 23
        assert hour_from_time_str("00:30") == 0
        assert hour_from_time_str("14:00") == 14

    def test_invalid_returns_none(self):
        assert hour_from_time_str("") is None
        assert hour_from_time_str(None) is None
        assert hour_from_time_str("invalid") is None


class TestSortFlightsByBestValue:
    """sort_flights_by_best_value uses normalized penalty score."""

    def test_sorts_by_penalty_ascending(self):
        # Flights as simple dicts with price, duration_minutes, departure_time, arrival_time
        flights = [
            {
                "price": 200,
                "duration_minutes": 120,
                "departure_time": "10:00",
                "arrival_time": "12:00",
            },
            {
                "price": 100,
                "duration_minutes": 180,
                "departure_time": "10:00",
                "arrival_time": "13:00",
            },
            {
                "price": 150,
                "duration_minutes": 90,
                "departure_time": "10:00",
                "arrival_time": "11:30",
            },
        ]
        sorted_flights = sort_flights_by_best_value(
            flights,
            get_price=lambda f: f["price"],
            get_duration=lambda f: f["duration_minutes"],
            get_departure_hour=lambda f: hour_from_time_str(f.get("departure_time")),
            get_arrival_hour=lambda f: hour_from_time_str(f.get("arrival_time")),
        )
        # Best balance: 150/90 should win (mid price, mid duration). Order by penalty: 150/90, 100/180, 200/120
        assert sorted_flights[0]["price"] == 150
        assert sorted_flights[0]["duration_minutes"] == 90

    def test_empty_list_returns_empty(self):
        assert (
            sort_flights_by_best_value(
                [],
                get_price=lambda f: f["price"],
                get_duration=lambda f: f["duration_minutes"],
                get_departure_hour=lambda f: None,
                get_arrival_hour=lambda f: None,
            )
            == []
        )

    def test_invalid_flights_sort_last(self):
        flights = [
            {
                "price": 100,
                "duration_minutes": 60,
                "departure_time": "10:00",
                "arrival_time": "11:00",
            },
            {
                "price": float("inf"),
                "duration_minutes": 60,
                "departure_time": "10:00",
                "arrival_time": "11:00",
            },
        ]
        sorted_flights = sort_flights_by_best_value(
            flights,
            get_price=lambda f: f["price"],
            get_duration=lambda f: f["duration_minutes"],
            get_departure_hour=lambda f: hour_from_time_str(f.get("departure_time")),
            get_arrival_hour=lambda f: hour_from_time_str(f.get("arrival_time")),
        )
        assert sorted_flights[0]["price"] == 100
        assert len(sorted_flights) == 2


# ---------------------------------------------------------------------------
# Preference scoring tests
# ---------------------------------------------------------------------------


class TestTimeStrToMinutes:
    def test_hhmm(self):
        assert _time_str_to_minutes("08:30") == 8 * 60 + 30

    def test_hhmmss(self):
        assert _time_str_to_minutes("14:45:00") == 14 * 60 + 45

    def test_midnight(self):
        assert _time_str_to_minutes("00:00") == 0

    def test_end_of_day(self):
        assert _time_str_to_minutes("23:59") == 23 * 60 + 59

    def test_hour_wraps_at_24(self):
        # 24 % 24 == 0
        assert _time_str_to_minutes("24:00") == 0

    def test_none_returns_none(self):
        assert _time_str_to_minutes(None) is None

    def test_empty_returns_none(self):
        assert _time_str_to_minutes("") is None

    def test_invalid_format_returns_none(self):
        assert _time_str_to_minutes("not-a-time") is None

    def test_missing_minutes_returns_none(self):
        assert _time_str_to_minutes("10") is None


class TestScorePreferredAirlines:
    def _flight(self, code: str = "", name: str = "") -> dict:
        return {"airline_code": code, "airline": name}

    def test_empty_pref_list_returns_zero(self):
        assert _score_preferred_airlines(self._flight("AA", "American"), []) == 0

    def test_exact_iata_code_match(self):
        assert _score_preferred_airlines(self._flight("AA"), ["AA"]) == 1

    def test_case_insensitive_code_match(self):
        assert _score_preferred_airlines(self._flight("aa"), ["AA"]) == 1

    def test_substring_name_match(self):
        assert (
            _score_preferred_airlines(self._flight("", "British Airways"), ["british"])
            == 1
        )

    def test_no_match_returns_zero(self):
        assert (
            _score_preferred_airlines(self._flight("LH", "Lufthansa"), ["AA", "Delta"])
            == 0
        )

    def test_second_pref_matches(self):
        assert (
            _score_preferred_airlines(self._flight("DL", "Delta"), ["AA", "delta"]) == 1
        )


class TestScoreMaxStops:
    def _flight(self, stops: int) -> dict:
        return {"stops": stops}

    def test_none_pref_returns_zero(self):
        assert _score_max_stops(self._flight(0), None) == 0

    def test_any_pref_returns_zero(self):
        assert _score_max_stops(self._flight(0), "any") == 0

    def test_nonstop_matches_zero_stops(self):
        assert _score_max_stops(self._flight(0), "nonstop") == 1

    def test_nonstop_does_not_match_one_stop(self):
        assert _score_max_stops(self._flight(1), "nonstop") == 0

    def test_1stop_matches_zero_stops(self):
        assert _score_max_stops(self._flight(0), "1stop") == 1

    def test_1stop_matches_one_stop(self):
        assert _score_max_stops(self._flight(1), "1stop") == 1

    def test_1stop_does_not_match_two_stops(self):
        assert _score_max_stops(self._flight(2), "1stop") == 0

    def test_2stops_matches_two_stops(self):
        assert _score_max_stops(self._flight(2), "2stops") == 1

    def test_missing_stops_returns_zero(self):
        assert _score_max_stops({}, "nonstop") == 0


class TestScoreDepartureWindow:
    def _flight(self, dep_time: str) -> dict:
        return {"departure_time": dep_time}

    def test_full_day_window_returns_zero(self):
        assert _score_departure_window(self._flight("10:00"), ["00:00", "23:59"]) == 0

    def test_departure_within_window(self):
        assert _score_departure_window(self._flight("09:00"), ["06:00", "12:00"]) == 1

    def test_departure_outside_window(self):
        assert _score_departure_window(self._flight("15:00"), ["06:00", "12:00"]) == 0

    def test_departure_at_window_boundary(self):
        assert _score_departure_window(self._flight("06:00"), ["06:00", "12:00"]) == 1
        assert _score_departure_window(self._flight("12:00"), ["06:00", "12:00"]) == 1

    def test_midnight_spanning_window_late_night(self):
        # 22:00–06:00 spans midnight; 23:00 should match
        assert _score_departure_window(self._flight("23:00"), ["22:00", "06:00"]) == 1

    def test_midnight_spanning_window_early_morning(self):
        # 22:00–06:00; 05:00 should match
        assert _score_departure_window(self._flight("05:00"), ["22:00", "06:00"]) == 1

    def test_midnight_spanning_window_midday_no_match(self):
        # 22:00–06:00; 14:00 should NOT match
        assert _score_departure_window(self._flight("14:00"), ["22:00", "06:00"]) == 0

    def test_invalid_window_returns_zero(self):
        assert _score_departure_window(self._flight("10:00"), ["bad", "time"]) == 0

    def test_missing_departure_time_returns_zero(self):
        assert _score_departure_window({}, ["06:00", "12:00"]) == 0

    def test_short_window_list_returns_zero(self):
        assert _score_departure_window(self._flight("10:00"), ["06:00"]) == 0


class TestComputePreferenceScore:
    def _prefs(
        self, airlines=None, max_stops=None, departure_window=None
    ) -> FlightsPreferences:
        return FlightsPreferences(
            preferred_airlines=airlines or [],
            max_stops=max_stops,
            departure_window=departure_window or ["00:00", "23:59"],
        )

    def _flight(self, code="AA", name="American", stops=0, dep="10:00") -> dict:
        return {
            "airline_code": code,
            "airline": name,
            "stops": stops,
            "departure_time": dep,
        }

    def test_none_prefs_returns_zero(self):
        assert compute_preference_score(self._flight(), None) == 0

    def test_all_dimensions_match_returns_three(self):
        prefs = self._prefs(
            airlines=["AA"], max_stops="nonstop", departure_window=["08:00", "12:00"]
        )
        assert compute_preference_score(self._flight(dep="10:00"), prefs) == 3

    def test_no_dimension_matches_returns_zero(self):
        prefs = self._prefs(
            airlines=["LH"], max_stops="nonstop", departure_window=["22:00", "23:00"]
        )
        flight = self._flight(code="AA", stops=2, dep="14:00")
        assert compute_preference_score(flight, prefs) == 0

    def test_partial_match_returns_one(self):
        prefs = self._prefs(airlines=["AA"])
        assert compute_preference_score(self._flight(), prefs) == 1

    def test_empty_prefs_returns_zero(self):
        # no airlines, no max_stops preference, full-day window
        prefs = self._prefs()
        assert compute_preference_score(self._flight(), prefs) == 0


class TestSortFlightsByBestValueWithPreferences:
    """Preference bias in ``sort_flights_by_best_value`` (#1034).

    Replaces the deleted ``sort_flights_by_preference`` — preferences are now a
    soft input to best-value scoring (each matched dimension subtracts
    ``PREFERENCE_WEIGHT`` from the penalty score).
    """

    def _prefs(
        self, airlines=None, max_stops=None, departure_window=None
    ) -> FlightsPreferences:
        return FlightsPreferences(
            preferred_airlines=airlines or [],
            max_stops=max_stops,
            departure_window=departure_window or ["00:00", "23:59"],
        )

    def _sort(self, flights, prefs=None):
        return sort_flights_by_best_value(
            flights,
            get_price=lambda f: f["price"],
            get_duration=lambda f: f["duration_minutes"],
            get_departure_hour=lambda f: int(f["departure_time"].split(":")[0]),
            get_arrival_hour=lambda f: int(f["arrival_time"].split(":")[0]),
            user_preferences=prefs,
        )

    def test_preference_match_breaks_tie_between_similar_candidates(self):
        # Two flights with identical price/duration → preferences pick winner
        flights = [
            {
                "airline_code": "LH",
                "airline": "Lufthansa",
                "stops": 2,
                "departure_time": "14:00",
                "arrival_time": "16:00",
                "price": 200,
                "duration_minutes": 120,
            },
            {
                "airline_code": "AA",
                "airline": "American",
                "stops": 0,
                "departure_time": "09:00",
                "arrival_time": "11:00",
                "price": 200,
                "duration_minutes": 120,
            },
        ]
        prefs = self._prefs(
            airlines=["AA"], max_stops="nonstop", departure_window=["06:00", "12:00"]
        )
        result = self._sort(flights, prefs)
        # AA matches all 3 prefs → preference bias reduces its penalty → ranks first
        assert result[0]["airline_code"] == "AA"

    def test_preference_bias_is_soft_not_dominant(self):
        # When one flight is dramatically cheaper, preferences should NOT override.
        # Cheap LH at $50 vs preferred AA at $500 → cheaper LH still wins.
        flights = [
            {
                "airline_code": "LH",
                "stops": 2,
                "departure_time": "14:00",
                "arrival_time": "16:00",
                "price": 50,
                "duration_minutes": 120,
            },
            {
                "airline_code": "AA",
                "stops": 0,
                "departure_time": "09:00",
                "arrival_time": "11:00",
                "price": 500,
                "duration_minutes": 120,
            },
        ]
        prefs = self._prefs(
            airlines=["AA"], max_stops="nonstop", departure_window=["06:00", "12:00"]
        )
        result = self._sort(flights, prefs)
        assert result[0]["airline_code"] == "LH"

    def test_none_prefs_behaves_like_plain_best_value(self):
        flights = [
            {
                "airline_code": "AA",
                "stops": 0,
                "departure_time": "10:00",
                "arrival_time": "12:00",
                "price": 500,
                "duration_minutes": 120,
            },
            {
                "airline_code": "LH",
                "stops": 0,
                "departure_time": "10:00",
                "arrival_time": "12:00",
                "price": 200,
                "duration_minutes": 120,
            },
        ]
        result = self._sort(flights, prefs=None)
        # No prefs, same duration/times → cheaper wins on price weight
        assert result[0]["price"] == 200

    def test_empty_list_returns_empty(self):
        assert self._sort([], self._prefs()) == []
