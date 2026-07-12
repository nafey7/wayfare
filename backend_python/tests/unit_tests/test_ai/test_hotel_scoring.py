"""Unit tests for hotel_scoring module."""

from app.ai.hotel_scoring import (
    _has_meaningful_preferences,
    _score_amenities,
    _score_cancellation,
    _score_room_type,
    _score_star_rating,
    compute_hotel_preference_score,
    sort_hotels_by_best_value,
)

# --- Helpers ---


class _Prefs:
    """Minimal stand-in for HotelsPreferences."""

    def __init__(
        self,
        cancellation: list[str] | None = None,
        amenities: list[str] | None = None,
        room_type: str | None = None,
    ) -> None:
        self.cancellation = cancellation or []
        self.amenities = amenities or []
        self.room_type = room_type


class _TravelStyle:
    """Minimal stand-in for TravelStylePreferences."""

    def __init__(self, accommodation: str | None = None) -> None:
        self.accommodation = accommodation


def _hotel(
    total_price: float = 100.0,
    hotel_rating: float = 3.0,
    fare_type: str = "Refundable",
    facilities: list[str] | None = None,
    property_type: str = "Hotel",
) -> dict:
    return {
        "total_price": total_price,
        "hotel_rating": hotel_rating,
        "fare_type": fare_type,
        "facilities": facilities or [],
        "property_type": property_type,
    }


# --- _has_meaningful_preferences ---


def test_has_prefs_none() -> None:
    assert _has_meaningful_preferences(None) is False


def test_has_prefs_all_empty() -> None:
    assert _has_meaningful_preferences(_Prefs()) is False


def test_has_prefs_cancellation_set() -> None:
    assert _has_meaningful_preferences(_Prefs(cancellation=["refundable"])) is True


def test_has_prefs_amenities_set() -> None:
    assert _has_meaningful_preferences(_Prefs(amenities=["gym"])) is True


def test_has_prefs_room_type_set() -> None:
    assert _has_meaningful_preferences(_Prefs(room_type="hotel")) is True


def test_has_prefs_no_preference_room_type_ignored() -> None:
    assert _has_meaningful_preferences(_Prefs(room_type="noPreference")) is False


def test_has_prefs_accommodation_4_triggers() -> None:
    assert _has_meaningful_preferences(None, _TravelStyle(accommodation="4")) is True


def test_has_prefs_accommodation_5_triggers() -> None:
    assert _has_meaningful_preferences(None, _TravelStyle(accommodation="5")) is True


def test_has_prefs_accommodation_legacy_4star_triggers() -> None:
    assert (
        _has_meaningful_preferences(None, _TravelStyle(accommodation="4star")) is True
    )


def test_has_prefs_accommodation_noPref_ignored() -> None:
    assert (
        _has_meaningful_preferences(None, _TravelStyle(accommodation="noPref")) is False
    )


def test_has_prefs_accommodation_none_ignored() -> None:
    assert _has_meaningful_preferences(None, _TravelStyle(accommodation=None)) is False


def test_has_prefs_both_none() -> None:
    assert _has_meaningful_preferences(None, None) is False


# --- _score_star_rating ---


def test_star_rating_4_matches_4star_hotel() -> None:
    assert _score_star_rating(_hotel(hotel_rating=4.0), "4") == 1


def test_star_rating_4_matches_5star_hotel() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), "4") == 1


def test_star_rating_4_no_match_3star_hotel() -> None:
    assert _score_star_rating(_hotel(hotel_rating=3.0), "4") == 0


def test_star_rating_5_matches_5star_hotel() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), "5") == 1


def test_star_rating_5_no_match_4star_hotel() -> None:
    assert _score_star_rating(_hotel(hotel_rating=4.0), "5") == 0


def test_star_rating_legacy_4star_value() -> None:
    assert _score_star_rating(_hotel(hotel_rating=4.0), "4star") == 1


def test_star_rating_legacy_5star_value() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), "5star") == 1


def test_star_rating_noPref_ignored() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), "noPref") == 0


def test_star_rating_none_ignored() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), None) == 0


def test_star_rating_unique_not_scoreable() -> None:
    assert _score_star_rating(_hotel(hotel_rating=5.0), "unique") == 0


# --- _score_cancellation ---


def test_cancellation_refundable_matches_refundable_fare() -> None:
    h = _hotel(fare_type="Refundable")
    assert _score_cancellation(h, ["refundable"]) == 1


def test_cancellation_refundable_no_match_non_refundable_fare() -> None:
    h = _hotel(fare_type="Non-Refundable")
    assert _score_cancellation(h, ["refundable"]) == 0


def test_cancellation_nonrefundable_matches_non_refundable_fare() -> None:
    h = _hotel(fare_type="Non-Refundable")
    assert _score_cancellation(h, ["nonrefundable"]) == 1


def test_cancellation_nonrefundable_no_match_refundable_fare() -> None:
    h = _hotel(fare_type="Refundable")
    assert _score_cancellation(h, ["nonrefundable"]) == 0


def test_cancellation_legacy_freeonly_matches_refundable() -> None:
    h = _hotel(fare_type="Refundable")
    assert _score_cancellation(h, ["freeOnly"]) == 1


def test_cancellation_legacy_flexible_matches_refundable() -> None:
    h = _hotel(fare_type="Refundable")
    assert _score_cancellation(h, ["flexiblePreferred"]) == 1


def test_cancellation_legacy_nonrefundableok_no_boost() -> None:
    h = _hotel(fare_type="Refundable")
    assert _score_cancellation(h, ["nonRefundableOk"]) == 0


def test_cancellation_empty_pref() -> None:
    assert _score_cancellation(_hotel(), []) == 0


def test_cancellation_missing_fare_type() -> None:
    h = {"total_price": 100.0, "hotel_rating": 3.0, "facilities": []}
    assert _score_cancellation(h, ["refundable"]) == 0


# --- _score_amenities ---


def test_amenities_exact_match() -> None:
    h = _hotel(facilities=["Breakfast", "Gym", "Pool"])
    assert _score_amenities(h, ["breakfast"]) == 1


def test_amenities_keyword_match() -> None:
    h = _hotel(facilities=["Fitness Center"])
    assert _score_amenities(h, ["gym"]) == 1


def test_amenities_any_match_returns_1() -> None:
    h = _hotel(facilities=["Pool"])
    assert _score_amenities(h, ["gym", "pool"]) == 1


def test_amenities_no_match() -> None:
    h = _hotel(facilities=["Parking"])
    assert _score_amenities(h, ["spa"]) == 0


def test_amenities_empty_facilities() -> None:
    h = _hotel(facilities=[])
    assert _score_amenities(h, ["gym"]) == 0


def test_amenities_empty_pref() -> None:
    h = _hotel(facilities=["Gym"])
    assert _score_amenities(h, []) == 0


def test_amenities_workspace_keywords() -> None:
    h = _hotel(facilities=["Business Centre"])
    assert _score_amenities(h, ["workspace"]) == 1


# --- _score_room_type ---


def test_room_type_hotel_matches() -> None:
    h = _hotel(property_type="Hotel")
    assert _score_room_type(h, "hotel") == 1


def test_room_type_apartment_matches() -> None:
    h = _hotel(property_type="Apartment Hotel")
    assert _score_room_type(h, "apartment") == 1


def test_room_type_legacy_apartmentstyle() -> None:
    h = _hotel(property_type="Serviced Apartment")
    assert _score_room_type(h, "apartmentStyle") == 1


def test_room_type_no_match() -> None:
    h = _hotel(property_type="Hostel")
    assert _score_room_type(h, "hotel") == 0


def test_room_type_none_pref() -> None:
    assert _score_room_type(_hotel(), None) == 0


def test_room_type_no_preference_ignored() -> None:
    assert _score_room_type(_hotel(), "noPreference") == 0


# --- compute_hotel_preference_score ---


def test_full_match_scores_3() -> None:
    h = _hotel(fare_type="Refundable", facilities=["Gym"], property_type="Hotel")
    prefs = _Prefs(cancellation=["refundable"], amenities=["gym"], room_type="hotel")
    assert compute_hotel_preference_score(h, prefs) == 3


def test_partial_match_scores_correctly() -> None:
    h = _hotel(fare_type="Non-Refundable", facilities=["Gym"], property_type="Hotel")
    prefs = _Prefs(cancellation=["refundable"], amenities=["gym"], room_type="hotel")
    # cancellation: 0, amenity: 1, room_type: 1 → 2
    assert compute_hotel_preference_score(h, prefs) == 2


def test_no_prefs_scores_0() -> None:
    h = _hotel(fare_type="Refundable", facilities=["Gym"])
    assert compute_hotel_preference_score(h, None) == 0


def test_full_match_scores_4() -> None:
    h = _hotel(
        fare_type="Refundable",
        facilities=["Gym"],
        property_type="Hotel",
        hotel_rating=5.0,
    )
    prefs = _Prefs(cancellation=["refundable"], amenities=["gym"], room_type="hotel")
    ts = _TravelStyle(accommodation="5")
    assert compute_hotel_preference_score(h, prefs, ts) == 4


def test_accommodation_adds_to_score_when_prefs_none() -> None:
    h = _hotel(hotel_rating=4.0)
    ts = _TravelStyle(accommodation="4")
    assert compute_hotel_preference_score(h, None, ts) == 1


def test_no_prefs_and_no_travel_style_scores_0() -> None:
    assert compute_hotel_preference_score(_hotel(hotel_rating=5.0), None, None) == 0


# --- sort_hotels_by_best_value ---


def test_sort_no_prefs_lower_price_and_higher_rating_wins() -> None:
    expensive_low_rated = _hotel(total_price=500.0, hotel_rating=2.0)
    cheap_high_rated = _hotel(total_price=100.0, hotel_rating=5.0)
    mid = _hotel(total_price=250.0, hotel_rating=3.5)

    result = sort_hotels_by_best_value([expensive_low_rated, mid, cheap_high_rated])
    assert result[0] is cheap_high_rated


def test_sort_no_prefs_returns_new_list() -> None:
    hotels = [_hotel(100.0), _hotel(200.0)]
    result = sort_hotels_by_best_value(hotels)
    assert result is not hotels


def test_sort_empty_list() -> None:
    assert sort_hotels_by_best_value([]) == []


def test_sort_with_prefs_orders_by_score_descending() -> None:
    h_no_match = _hotel(
        fare_type="Non-Refundable",
        facilities=[],
        property_type="Hostel",
        total_price=80.0,
    )
    h_partial = _hotel(
        fare_type="Refundable", facilities=[], property_type="Hostel", total_price=120.0
    )
    h_full = _hotel(
        fare_type="Refundable",
        facilities=["Gym"],
        property_type="Hotel",
        total_price=200.0,
    )

    prefs = _Prefs(cancellation=["refundable"], amenities=["gym"], room_type="hotel")
    result = sort_hotels_by_best_value([h_no_match, h_full, h_partial], prefs)

    assert result[0] is h_full  # score 3
    assert result[1] is h_partial  # score 1
    assert result[2] is h_no_match  # score 0


def test_sort_with_prefs_price_tiebreaker() -> None:
    h_cheap = _hotel(
        fare_type="Non-Refundable",
        facilities=[],
        property_type="Hostel",
        total_price=80.0,
    )
    h_expensive = _hotel(
        fare_type="Non-Refundable",
        facilities=[],
        property_type="Hostel",
        total_price=200.0,
    )

    prefs = _Prefs(cancellation=["refundable"])  # both score 0 → sort by price
    result = sort_hotels_by_best_value([h_expensive, h_cheap], prefs)
    assert result[0] is h_cheap


def test_sort_falls_back_to_default_when_prefs_all_empty() -> None:
    h_cheap = _hotel(total_price=100.0, hotel_rating=3.0)
    h_expensive = _hotel(total_price=500.0, hotel_rating=5.0)

    prefs = _Prefs()  # no preferences set → use default scoring
    result = sort_hotels_by_best_value([h_expensive, h_cheap], prefs)
    # With normalized scoring: cheap + decent rating should beat expensive + high rating
    assert result[0] is h_cheap


def test_sort_single_hotel() -> None:
    h = _hotel()
    assert sort_hotels_by_best_value([h]) == [h]


def test_sort_no_prefs_handles_zero_price() -> None:
    h_valid = _hotel(total_price=100.0)
    h_zero = _hotel(total_price=0.0)
    result = sort_hotels_by_best_value([h_zero, h_valid])
    assert result[0] is h_valid


def test_sort_with_travel_style_5star_preference() -> None:
    h_5star = _hotel(total_price=300.0, hotel_rating=5.0)
    h_4star = _hotel(total_price=200.0, hotel_rating=4.0)
    h_3star = _hotel(total_price=100.0, hotel_rating=3.0)
    ts = _TravelStyle(accommodation="5")
    result = sort_hotels_by_best_value([h_3star, h_4star, h_5star], travel_style=ts)
    assert result[0] is h_5star  # only 5-star scores 1; others score 0, sorted by price


def test_sort_with_travel_style_4star_matches_4_and_5() -> None:
    h_5star = _hotel(total_price=300.0, hotel_rating=5.0)
    h_4star = _hotel(total_price=200.0, hotel_rating=4.0)
    h_3star = _hotel(total_price=100.0, hotel_rating=3.0)
    ts = _TravelStyle(accommodation="4")
    result = sort_hotels_by_best_value([h_3star, h_4star, h_5star], travel_style=ts)
    # Both 4-star and 5-star score 1; price tiebreaker: 4-star (200) before 5-star (300)
    assert result[0] is h_4star
    assert result[1] is h_5star
    assert result[2] is h_3star
