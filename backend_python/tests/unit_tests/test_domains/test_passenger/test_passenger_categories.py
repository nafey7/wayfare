"""Unit tests for passenger categorization and hotel title derivation."""

from datetime import UTC, datetime, timedelta

from app.domains.passenger.categories import (
    derive_hotel_title,
    derive_type_hotel,
    get_passenger_category,
)


class TestDeriveHotelTitle:
    """Tests for derive_hotel_title."""

    def test_adult_male_mr(self):
        """Mr adult stays Mr."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 30)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Mr", dob) == "Mr"

    def test_adult_female_mrs(self):
        """Mrs adult stays Mrs."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 30)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Mrs", dob) == "Mrs"

    def test_adult_female_miss(self):
        """Miss adult stays Miss."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 25)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Miss", dob) == "Miss"

    def test_adult_female_ms(self):
        """Ms adult stays Ms."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 25)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Ms", dob) == "Ms"

    def test_child_male_master(self):
        """Master child stays Master."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 5)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Master", dob) == "Master"

    def test_child_female_miss(self):
        """Miss child stays Miss."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 5)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Miss", dob) == "Miss"

    def test_12_17_stored_mr_becomes_master(self):
        """12-17 stored as Mr (flight adult) → Master for hotel (child)."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 15)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Mr", dob) == "Master"

    def test_12_17_stored_master_stays_master(self):
        """12-17 stored as Master → Master for hotel."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 15)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Master", dob) == "Master"

    def test_invalid_dob_assumes_adult(self):
        """Invalid/missing DOB assumes adult (18+)."""
        assert derive_hotel_title("Mr", None) == "Mr"
        assert derive_hotel_title("Master", None) == "Mr"
        assert derive_hotel_title("Mrs", "invalid") == "Mrs"

    def test_unknown_title_treat_as_female(self):
        """Unknown title → Miss (female)."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 30)).strftime("%Y-%m-%d")
        assert derive_hotel_title("Dr", dob) == "Miss"

    def test_title_stripped(self):
        """Whitespace around title is stripped."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 30)).strftime("%Y-%m-%d")
        assert derive_hotel_title("  Mr  ", dob) == "Mr"


class TestGetPassengerCategory:
    """Tests for get_passenger_category."""

    def test_flight_adult_12_plus(self):
        """Flight: 12+ = adult."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 12)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "flight") == "adult"

    def test_flight_child_2_to_11(self):
        """Flight: 2-11 = child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 5)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "flight") == "child"

    def test_flight_infant_under_2(self):
        """Flight: <2 = infant."""
        today = datetime.now(UTC)
        dob = (today - timedelta(days=100)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "flight") == "infant"

    def test_hotel_adult_18_plus(self):
        """Hotel: 18+ = adult."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 18)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "hotel") == "adult"

    def test_hotel_child_under_18(self):
        """Hotel: 0-17 = child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 17)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "hotel") == "child"

    def test_hotel_12_17_is_child(self):
        """Hotel: 12-17 = child (different from flight)."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 15)).strftime("%Y-%m-%d")
        assert get_passenger_category(dob, "flight") == "adult"
        assert get_passenger_category(dob, "hotel") == "child"

    def test_invalid_dob_returns_none(self):
        """Invalid DOB returns None."""
        assert get_passenger_category(None, "flight") is None
        assert get_passenger_category("invalid", "flight") is None


class TestDeriveTypeHotel:
    """Tests for derive_type_hotel (hotel context: 18+ adult, 0–17 child)."""

    def test_adult_18_plus(self):
        """18+ returns adult."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 25)).strftime("%Y-%m-%d")
        assert derive_type_hotel(dob) == "adult"

    def test_child_under_18(self):
        """0–17 returns child."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 10)).strftime("%Y-%m-%d")
        assert derive_type_hotel(dob) == "child"

    def test_12_17_returns_child(self):
        """12–17 (flight adult) returns child for hotel."""
        today = datetime.now(UTC)
        dob = (today.replace(year=today.year - 15)).strftime("%Y-%m-%d")
        assert derive_type_hotel(dob) == "child"

    def test_invalid_dob_assumes_adult(self):
        """Invalid/missing DOB defaults to adult."""
        assert derive_type_hotel(None) == "adult"
        assert derive_type_hotel("invalid") == "adult"
