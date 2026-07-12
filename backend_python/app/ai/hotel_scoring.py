"""Best-value hotel scoring with optional preference-aware sort.

Default (no meaningful preferences):
    S = (price_norm * WEIGHT_PRICE) + ((1 - rating_norm) * WEIGHT_RATING)
    Lower S = better. Returns hotels sorted ascending by S.

With preferences (cancellation, amenities, room_type, or accommodation star rating set):
    preference_score = 0–4 (one point per matched attribute).
    Returns hotels sorted descending by preference_score, then ascending by price.
"""

from typing import Any

WEIGHT_PRICE = 0.60
WEIGHT_RATING = 0.40

# Maps preference key → substrings found in hotel facility strings (case-insensitive)
AMENITY_KEYWORD_MAP: dict[str, list[str]] = {
    "breakfast": ["breakfast"],
    "gym": ["gym", "fitness"],
    "spa": ["spa", "wellness"],
    "pool": ["pool", "swimming"],
    "workspace": ["business center", "business centre", "work desk", "workspace"],
    "familyFriendly": ["family room", "family friendly", "family-friendly"],
    "petFriendly": ["pet friendly", "pets allowed", "pets welcome", "pet-friendly"],
    "airportShuttle": ["airport shuttle", "airport transfer", "shuttle"],
}


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to [0, 1] range. Returns 0 if min_val == max_val."""
    if min_val == max_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def _has_meaningful_preferences(prefs: Any, travel_style: Any = None) -> bool:
    """True if prefs or travel_style has at least one scoreable hotel preference set.

    Scoreable from hotel search data: cancellation, amenities, room_type, accommodation.
    hotel_style, location_preference, and bed_type are not returned by the search API.
    """
    if prefs is not None:
        has_cancellation = bool(getattr(prefs, "cancellation", None))
        has_amenities = bool(getattr(prefs, "amenities", None))
        room_type = getattr(prefs, "room_type", None)
        has_room_type = bool(room_type) and room_type != "noPreference"
    else:
        has_cancellation = has_amenities = has_room_type = False
    accommodation = (
        getattr(travel_style, "accommodation", None) if travel_style else None
    )
    has_accommodation = bool(accommodation) and accommodation != "noPref"
    return has_cancellation or has_amenities or has_room_type or has_accommodation


def _score_cancellation(hotel: dict[str, Any], cancellation_pref: list[str]) -> int:
    """Return 1 if fare_type matches the cancellation preference, else 0.

    Handles both current values (refundable, nonrefundable) and legacy values
    (freeOnly, flexiblePreferred, nonRefundableOk).
    """
    if not cancellation_pref:
        return 0
    pref = cancellation_pref[0].lower()
    fare = (hotel.get("fare_type") or "").lower()

    is_refundable = "refundable" in fare and "non" not in fare
    is_non_refundable = "non-refundable" in fare or "non refundable" in fare

    if pref in ("refundable", "freeonly", "flexiblepreferred"):
        return 1 if is_refundable else 0
    if pref == "nonrefundable":
        return 1 if is_non_refundable else 0
    # nonRefundableOk = tolerance, not preference — no boost
    return 0


def _score_amenities(hotel: dict[str, Any], amenities_pref: list[str]) -> int:
    """Return 1 if the hotel offers any preferred amenity, else 0."""
    if not amenities_pref:
        return 0
    hotel_facilities = [f.lower() for f in (hotel.get("facilities") or [])]
    for pref in amenities_pref:
        keywords = AMENITY_KEYWORD_MAP.get(pref, [pref.lower()])
        if any(any(kw in fac for kw in keywords) for fac in hotel_facilities):
            return 1
    return 0


def _score_star_rating(hotel: dict[str, Any], accommodation_pref: str | None) -> int:
    """Return 1 if hotel_rating matches the accommodation preference, else 0.

    Handles current values ('4', '5') and legacy values ('4star', '5star').
    '4'/'4star': matches hotels with hotel_rating >= 4.
    '5'/'5star': matches hotels with hotel_rating >= 5.
    'unique' is not scoreable from star rating data.
    """
    if not accommodation_pref or accommodation_pref == "noPref":
        return 0
    rating = float(hotel.get("hotel_rating", 0) or 0)
    pref = accommodation_pref.lower()
    if pref in ("5", "5star"):
        return 1 if rating >= 5 else 0
    if pref in ("4", "4star"):
        return 1 if rating >= 4 else 0
    return 0


def _score_room_type(hotel: dict[str, Any], room_type_pref: str | None) -> int:
    """Return 1 if property_type matches the room type preference, else 0.

    Handles both current values (hotel, apartment) and legacy value (apartmentStyle).
    """
    if not room_type_pref or room_type_pref == "noPreference":
        return 0
    property_type = (hotel.get("property_type") or "").lower()
    pref = room_type_pref.lower()
    if pref == "hotel":
        return 1 if "hotel" in property_type else 0
    if pref in ("apartment", "apartmentstyle"):
        return 1 if "apartment" in property_type else 0
    return 0


def compute_hotel_preference_score(
    hotel: dict[str, Any], prefs: Any, travel_style: Any = None
) -> int:
    """Compute preference match score (0–4) for a hotel against user preferences.

    One point each for: cancellation match, amenity match, room type match, star rating match.
    Returns 0 when both prefs and travel_style are None.
    """
    if prefs is None and travel_style is None:
        return 0
    hotels_score = 0
    if prefs is not None:
        hotels_score = (
            _score_cancellation(hotel, getattr(prefs, "cancellation", []) or [])
            + _score_amenities(hotel, getattr(prefs, "amenities", []) or [])
            + _score_room_type(hotel, getattr(prefs, "room_type", None))
        )
    accommodation = (
        getattr(travel_style, "accommodation", None) if travel_style else None
    )
    return hotels_score + _score_star_rating(hotel, accommodation)


def _default_penalty(
    hotel: dict[str, Any],
    min_price: float,
    max_price: float,
    min_rating: float,
    max_rating: float,
) -> float:
    """Normalized penalty for default best-value sort. Lower = better.

    Returns float('inf') for hotels with invalid/zero price so they sort last.
    """
    price = float(hotel.get("total_price", 0) or 0)
    rating = float(hotel.get("hotel_rating", 0) or 0)
    if price <= 0:
        return float("inf")
    price_norm = _normalize(price, min_price, max_price)
    rating_norm = _normalize(rating, min_rating, max_rating)
    return (price_norm * WEIGHT_PRICE) + ((1 - rating_norm) * WEIGHT_RATING)


def sort_hotels_by_best_value(
    hotels: list[dict[str, Any]],
    user_preferences: Any = None,
    travel_style: Any = None,
) -> list[dict[str, Any]]:
    """Sort hotels for the best_value category. Returns a new list.

    With meaningful preferences (cancellation / amenities / room_type / accommodation set):
      Sort descending by preference_score (0–4), then ascending by price.

    Without preferences (or unauthenticated):
      Normalized penalty sort — lower price and higher rating rank first.
    """
    if not hotels:
        return []

    if _has_meaningful_preferences(user_preferences, travel_style):
        scores = {
            id(h): compute_hotel_preference_score(h, user_preferences, travel_style)
            for h in hotels
        }
        return sorted(
            hotels,
            key=lambda h: (-scores[id(h)], float(h.get("total_price", 0) or 0)),
        )

    valid_prices = [
        float(h.get("total_price", 0) or 0)
        for h in hotels
        if float(h.get("total_price", 0) or 0) > 0
    ]
    if not valid_prices:
        return hotels[:]

    min_price, max_price = min(valid_prices), max(valid_prices)
    ratings = [float(h.get("hotel_rating", 0) or 0) for h in hotels]
    min_rating, max_rating = min(ratings), max(ratings)

    return sorted(
        hotels,
        key=lambda h: _default_penalty(h, min_price, max_price, min_rating, max_rating),
    )
