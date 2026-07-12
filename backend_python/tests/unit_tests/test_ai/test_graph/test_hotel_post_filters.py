"""Unit tests for hotel post-filter function.

Tests _apply_hotel_post_filters() in app.ai.graph.tools.hotels.
All hotel filters are post-filters — FlightLogic Hotel API does not support
filter params at the API level.
"""

from app.ai.graph.tools.hotels import _apply_hotel_post_filters


def _make_hotel(
    per_night_price: float | None = 100.0,
    hotel_rating: float | None = 4.0,
    property_type: str | None = "Hotel",
    fare_type: str | None = "Refundable",
    facilities: list[str] | None = None,
    distance_value: float | None = 1.5,
    distance_unit: str = "km",
) -> dict:
    return {
        "per_night_price": per_night_price,
        "hotel_rating": hotel_rating,
        "property_type": property_type,
        "fare_type": fare_type,
        "facilities": ["Swimming Pool", "Gym", "Free WiFi"]
        if facilities is None
        else facilities,
        "distance_value": distance_value,
        "distance_unit": distance_unit,
    }


class TestNoFilters:
    def test_no_filters_returns_all(self):
        hotels = [_make_hotel(), _make_hotel(per_night_price=200)]
        result = _apply_hotel_post_filters(hotels)
        assert result == hotels

    def test_empty_list_returns_empty(self):
        assert _apply_hotel_post_filters([]) == []


class TestPriceFilter:
    def test_price_max_excludes_expensive(self):
        cheap = _make_hotel(per_night_price=80)
        expensive = _make_hotel(per_night_price=200)
        result = _apply_hotel_post_filters([cheap, expensive], price_max=100)
        assert result == [cheap]

    def test_price_min_excludes_cheap(self):
        cheap = _make_hotel(per_night_price=50)
        expensive = _make_hotel(per_night_price=150)
        result = _apply_hotel_post_filters([cheap, expensive], price_min=100)
        assert result == [expensive]

    def test_price_range(self):
        low = _make_hotel(per_night_price=50)
        mid = _make_hotel(per_night_price=120)
        high = _make_hotel(per_night_price=250)
        result = _apply_hotel_post_filters(
            [low, mid, high], price_min=80, price_max=150
        )
        assert result == [mid]

    def test_price_boundary_inclusive(self):
        hotel = _make_hotel(per_night_price=100)
        assert _apply_hotel_post_filters([hotel], price_max=100) == [hotel]
        assert _apply_hotel_post_filters([hotel], price_min=100) == [hotel]

    def test_price_no_match_returns_empty(self):
        hotel = _make_hotel(per_night_price=500)
        assert _apply_hotel_post_filters([hotel], price_max=100) == []

    def test_none_price_excluded_when_filter_active(self):
        """Hotel with None price should be excluded when price filter is active."""
        hotel_no_price = _make_hotel(per_night_price=None)
        hotel_with_price = _make_hotel(per_night_price=80)
        result = _apply_hotel_post_filters(
            [hotel_no_price, hotel_with_price], price_max=150
        )
        assert result == [hotel_with_price]


class TestRatingFilter:
    def test_min_rating_5_filters_lower(self):
        four_star = _make_hotel(hotel_rating=4)
        five_star = _make_hotel(hotel_rating=5)
        result = _apply_hotel_post_filters([four_star, five_star], min_rating=5)
        assert result == [five_star]

    def test_min_rating_3_passes_all(self):
        hotels = [_make_hotel(hotel_rating=r) for r in [3, 4, 5]]
        result = _apply_hotel_post_filters(hotels, min_rating=3)
        assert len(result) == 3

    def test_min_rating_4_passes_4_and_5(self):
        three_star = _make_hotel(hotel_rating=3)
        four_star = _make_hotel(hotel_rating=4)
        five_star = _make_hotel(hotel_rating=5)
        result = _apply_hotel_post_filters(
            [three_star, four_star, five_star], min_rating=4
        )
        assert result == [four_star, five_star]

    def test_none_rating_excluded_when_filter_active(self):
        """Hotel with None rating should be excluded when min_rating is active."""
        no_rating = _make_hotel(hotel_rating=None)
        four_star = _make_hotel(hotel_rating=4)
        result = _apply_hotel_post_filters([no_rating, four_star], min_rating=3)
        assert result == [four_star]


class TestPropertyTypeFilter:
    def test_single_type(self):
        hotel = _make_hotel(property_type="Hotel")
        resort = _make_hotel(property_type="Resort")
        result = _apply_hotel_post_filters([hotel, resort], property_types=["Hotel"])
        assert result == [hotel]

    def test_multiple_types(self):
        hotel = _make_hotel(property_type="Hotel")
        resort = _make_hotel(property_type="Resort")
        apartment = _make_hotel(property_type="Apartment")
        result = _apply_hotel_post_filters(
            [hotel, resort, apartment], property_types=["Hotel", "Resort"]
        )
        assert result == [hotel, resort]

    def test_case_insensitive(self):
        hotel = _make_hotel(property_type="Hotel")
        result = _apply_hotel_post_filters([hotel], property_types=["hotel"])
        assert result == [hotel]

    def test_none_property_type_excluded_when_filter_active(self):
        """Hotel with None/empty property_type should be excluded when filter is active."""
        no_type = _make_hotel(property_type=None)
        hotel = _make_hotel(property_type="Hotel")
        result = _apply_hotel_post_filters([no_type, hotel], property_types=["Hotel"])
        assert result == [hotel]


class TestRefundableFilter:
    def test_refundable_only_excludes_non_refundable(self):
        refundable = _make_hotel(fare_type="Refundable")
        non_refundable = _make_hotel(fare_type="Non-Refundable")
        result = _apply_hotel_post_filters(
            [refundable, non_refundable], refundable_only=True
        )
        assert result == [refundable]

    def test_refundable_only_false_does_not_filter(self):
        refundable = _make_hotel(fare_type="Refundable")
        non_refundable = _make_hotel(fare_type="Non-Refundable")
        result = _apply_hotel_post_filters(
            [refundable, non_refundable], refundable_only=False
        )
        assert result == [refundable, non_refundable]

    def test_refundable_only_none_does_not_filter(self):
        refundable = _make_hotel(fare_type="Refundable")
        non_refundable = _make_hotel(fare_type="Non-Refundable")
        result = _apply_hotel_post_filters(
            [refundable, non_refundable], refundable_only=None
        )
        assert result == [refundable, non_refundable]

    def test_none_fare_type_excluded_when_refundable_only(self):
        """Hotel with fare_type=None should be excluded when refundable_only=True."""
        unknown = _make_hotel(fare_type=None)
        refundable = _make_hotel(fare_type="Refundable")
        result = _apply_hotel_post_filters([unknown, refundable], refundable_only=True)
        assert result == [refundable]

    def test_empty_fare_type_excluded_when_refundable_only(self):
        """Hotel with empty fare_type should be excluded when refundable_only=True."""
        empty = _make_hotel(fare_type="")
        refundable = _make_hotel(fare_type="Refundable")
        result = _apply_hotel_post_filters([empty, refundable], refundable_only=True)
        assert result == [refundable]


class TestFacilitiesFilter:
    def test_single_facility_substring_match(self):
        with_pool = _make_hotel(facilities=["Swimming Pool", "Gym"])
        without_pool = _make_hotel(facilities=["Gym", "Free WiFi"])
        result = _apply_hotel_post_filters(
            [with_pool, without_pool], required_facilities=["pool"]
        )
        assert result == [with_pool]

    def test_multiple_facilities_and_logic(self):
        """Hotel must have ALL required facilities."""
        both = _make_hotel(facilities=["Swimming Pool", "Spa", "Gym"])
        pool_only = _make_hotel(facilities=["Swimming Pool"])
        spa_only = _make_hotel(facilities=["Spa"])
        result = _apply_hotel_post_filters(
            [both, pool_only, spa_only], required_facilities=["pool", "spa"]
        )
        assert result == [both]

    def test_case_insensitive_facility_match(self):
        hotel = _make_hotel(facilities=["Swimming Pool"])
        result = _apply_hotel_post_filters([hotel], required_facilities=["POOL"])
        assert result == [hotel]

    def test_empty_facilities_excluded_when_filter_active(self):
        no_facilities = _make_hotel(facilities=[])
        with_pool = _make_hotel(facilities=["Swimming Pool"])
        result = _apply_hotel_post_filters(
            [no_facilities, with_pool], required_facilities=["pool"]
        )
        assert result == [with_pool]

    def test_missing_facilities_key_excluded(self):
        hotel = {"per_night_price": 100, "hotel_rating": 4}  # no facilities key
        with_pool = _make_hotel(facilities=["Swimming Pool"])
        result = _apply_hotel_post_filters(
            [hotel, with_pool], required_facilities=["pool"]
        )
        assert result == [with_pool]


class TestDistanceFilter:
    def test_max_distance_km(self):
        near = _make_hotel(distance_value=1.0, distance_unit="km")
        far = _make_hotel(distance_value=5.0, distance_unit="km")
        result = _apply_hotel_post_filters([near, far], max_distance_km=2.0)
        assert result == [near]

    def test_miles_converted_to_km(self):
        """1 mile ≈ 1.609 km; a hotel 1 mile away should pass max_distance_km=2.0."""
        hotel_miles = _make_hotel(distance_value=1.0, distance_unit="miles")
        result = _apply_hotel_post_filters([hotel_miles], max_distance_km=2.0)
        assert result == [hotel_miles]  # 1 mile = 1.609 km < 2.0 km

    def test_miles_too_far_excluded(self):
        """2 miles ≈ 3.218 km; should be excluded when max_distance_km=2.0."""
        hotel_miles = _make_hotel(distance_value=2.0, distance_unit="miles")
        result = _apply_hotel_post_filters([hotel_miles], max_distance_km=2.0)
        assert result == []

    def test_none_distance_excluded_when_filter_active(self):
        no_distance = _make_hotel(distance_value=None)
        near = _make_hotel(distance_value=1.0, distance_unit="km")
        result = _apply_hotel_post_filters([no_distance, near], max_distance_km=2.0)
        assert result == [near]

    def test_exact_boundary_inclusive(self):
        hotel = _make_hotel(distance_value=2.0, distance_unit="km")
        assert _apply_hotel_post_filters([hotel], max_distance_km=2.0) == [hotel]


class TestLocalityFilter:
    def _make_hotel_with_locality(self, locality: str | None) -> dict:
        h = _make_hotel()
        h["locality"] = locality
        return h

    def test_locality_match(self):
        montmartre = self._make_hotel_with_locality("Montmartre")
        marais = self._make_hotel_with_locality("Le Marais")
        result = _apply_hotel_post_filters([montmartre, marais], locality="Montmartre")
        assert result == [montmartre]

    def test_locality_case_insensitive(self):
        hotel = self._make_hotel_with_locality("Montmartre")
        result = _apply_hotel_post_filters([hotel], locality="montmartre")
        assert result == [hotel]

    def test_locality_partial_match(self):
        """'Marais' should match 'Le Marais'."""
        hotel = self._make_hotel_with_locality("Le Marais")
        result = _apply_hotel_post_filters([hotel], locality="Marais")
        assert result == [hotel]

    def test_locality_no_match_returns_empty(self):
        hotel = self._make_hotel_with_locality("Montmartre")
        result = _apply_hotel_post_filters([hotel], locality="Saint-Germain")
        assert result == []

    def test_none_locality_excluded_when_filter_active(self):
        no_locality = self._make_hotel_with_locality(None)
        montmartre = self._make_hotel_with_locality("Montmartre")
        result = _apply_hotel_post_filters(
            [no_locality, montmartre], locality="Montmartre"
        )
        assert result == [montmartre]

    def test_empty_locality_excluded_when_filter_active(self):
        empty_locality = self._make_hotel_with_locality("")
        montmartre = self._make_hotel_with_locality("Montmartre")
        result = _apply_hotel_post_filters(
            [empty_locality, montmartre], locality="Montmartre"
        )
        assert result == [montmartre]

    def test_locality_none_does_not_filter(self):
        """No locality filter applied when locality=None."""
        hotels = [
            self._make_hotel_with_locality("Montmartre"),
            self._make_hotel_with_locality(None),
        ]
        result = _apply_hotel_post_filters(hotels, locality=None)
        assert result == hotels


class TestCombinedFilters:
    def test_price_and_rating(self):
        cheap_low = _make_hotel(per_night_price=80, hotel_rating=3)
        cheap_high = _make_hotel(per_night_price=90, hotel_rating=5)
        expensive_high = _make_hotel(per_night_price=300, hotel_rating=5)
        result = _apply_hotel_post_filters(
            [cheap_low, cheap_high, expensive_high],
            price_max=150,
            min_rating=4,
        )
        assert result == [cheap_high]

    def test_all_filters_combined(self):
        match = _make_hotel(
            per_night_price=120,
            hotel_rating=5,
            property_type="Resort",
            fare_type="Refundable",
            facilities=["Swimming Pool", "Spa"],
            distance_value=1.0,
            distance_unit="km",
        )
        match["locality"] = "Beachfront"
        no_match = _make_hotel(
            per_night_price=50,
            hotel_rating=3,
            property_type="Hotel",
            fare_type="Non-Refundable",
            facilities=["Gym"],
            distance_value=10.0,
            distance_unit="km",
        )
        no_match["locality"] = "Downtown"
        result = _apply_hotel_post_filters(
            [match, no_match],
            price_min=100,
            price_max=200,
            min_rating=4,
            property_types=["Resort"],
            refundable_only=True,
            required_facilities=["pool"],
            max_distance_km=2.0,
            locality="Beachfront",
        )
        assert result == [match]
