"""Unit tests for flight passenger age validators."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domains.flight.exceptions import FlightBookingError
from app.domains.flight.schemas import (
    AdultPassenger,
    ChildPassenger,
    InfantPassenger,
    PassengerGroups,
    PersonalInfo,
)
from app.domains.flight.validators import (
    PassengerValidator,
    calculate_age,
    validate_age_requirements,
)


class TestPassengerValidatorAdults:
    """Test PassengerValidator.validate_adult_age method."""

    def test_valid_adult_age(self):
        """Test that 12+ year old passes validation."""
        # 25 years old
        dob = (datetime.now() - timedelta(days=365.25 * 25)).strftime("%Y-%m-%d")
        PassengerValidator.validate_adult_age(dob)  # Should not raise

    def test_exactly_12_years_old(self):
        """Test that exactly 12 years old passes validation (FlightLogic ADT = 12+)."""
        # Exactly 12 years ago
        dob = (datetime.now() - timedelta(days=365.25 * 12)).strftime("%Y-%m-%d")
        PassengerValidator.validate_adult_age(dob)  # Should not raise

    def test_under_12_fails(self):
        """Test that under 12 years old fails validation."""
        # 11 years old
        dob = (datetime.now() - timedelta(days=365.25 * 11)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValueError, match="Adult passengers must be at least 12 years old"
        ):
            PassengerValidator.validate_adult_age(dob)

    def test_future_date_fails(self):
        """Test that future date of birth fails validation."""
        # 1 year in the future
        dob = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="Date of birth cannot be in the future"):
            PassengerValidator.validate_adult_age(dob)

    def test_invalid_format_fails(self):
        """Test that invalid date format fails validation."""
        with pytest.raises(ValueError, match="Invalid date of birth format"):
            PassengerValidator.validate_adult_age("not-a-date")

    def test_none_date_of_birth_passes(self):
        """Test that None date of birth passes (optional field)."""
        PassengerValidator.validate_adult_age(None)  # Should not raise


class TestPassengerValidatorChildren:
    """Test PassengerValidator.validate_child_age_pydantic method."""

    def test_valid_child_age(self):
        """Test that 2-11 year old passes validation."""
        # 5 years old
        dob = (datetime.now() - timedelta(days=365.25 * 5)).strftime("%Y-%m-%d")
        PassengerValidator.validate_child_age_pydantic(dob)  # Should not raise

    def test_exactly_2_years_old(self):
        """Test that exactly 2 years old passes validation."""
        # Exactly 2 years ago (same month and day, 2 years earlier)
        today = datetime.now()
        dob = today.replace(year=today.year - 2).strftime("%Y-%m-%d")
        PassengerValidator.validate_child_age_pydantic(dob)  # Should not raise

    def test_exactly_11_years_old(self):
        """Test that 11 years old passes validation."""
        # 11 years old (still under 12)
        dob = (datetime.now() - timedelta(days=365.25 * 11)).strftime("%Y-%m-%d")
        PassengerValidator.validate_child_age_pydantic(dob)  # Should not raise

    def test_under_2_fails(self):
        """Test that under 2 years old fails validation."""
        # 1 year old
        dob = (datetime.now() - timedelta(days=365.25 * 1)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValueError, match="Child passengers must be at least 2 years old"
        ):
            PassengerValidator.validate_child_age_pydantic(dob)

    def test_12_or_older_fails(self):
        """Test that 12+ years old fails validation."""
        # 12 years old
        dob = (datetime.now() - timedelta(days=365.25 * 12)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValueError, match="Child passengers must be under 12 years old"
        ):
            PassengerValidator.validate_child_age_pydantic(dob)

    def test_future_date_fails(self):
        """Test that future date of birth fails validation."""
        dob = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="Date of birth cannot be in the future"):
            PassengerValidator.validate_child_age_pydantic(dob)

    def test_none_date_of_birth_passes(self):
        """Test that None date of birth passes (optional field)."""
        PassengerValidator.validate_child_age_pydantic(None)  # Should not raise


class TestPassengerValidatorInfants:
    """Test PassengerValidator.validate_infant_age_pydantic method."""

    def test_valid_infant_age(self):
        """Test that under 2 years old passes validation."""
        # 1 year old
        dob = (datetime.now() - timedelta(days=365.25 * 1)).strftime("%Y-%m-%d")
        PassengerValidator.validate_infant_age_pydantic(dob)  # Should not raise

    def test_newborn_passes(self):
        """Test that newborn (< 1 month) passes validation."""
        # 2 weeks old
        dob = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        PassengerValidator.validate_infant_age_pydantic(dob)  # Should not raise

    def test_2_years_or_older_fails(self):
        """Test that 2+ years old fails validation."""
        # Exactly 2 years old (same month and day, 2 years earlier)
        today = datetime.now()
        dob = today.replace(year=today.year - 2).strftime("%Y-%m-%d")
        with pytest.raises(
            ValueError, match="Infant passengers must be under 2 years old"
        ):
            PassengerValidator.validate_infant_age_pydantic(dob)

    def test_future_date_fails(self):
        """Test that future date of birth fails validation."""
        dob = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        with pytest.raises(ValueError, match="Date of birth cannot be in the future"):
            PassengerValidator.validate_infant_age_pydantic(dob)

    def test_none_date_of_birth_passes(self):
        """Test that None date of birth passes (optional field)."""
        PassengerValidator.validate_infant_age_pydantic(None)  # Should not raise


class TestPydanticModelValidation:
    """Test that Pydantic models call validators automatically."""

    def test_adult_passenger_validation_passes_for_valid_age(self):
        """Test that AdultPassenger validates age on instantiation."""
        dob = (datetime.now() - timedelta(days=365.25 * 25)).strftime("%Y-%m-%d")
        adult = AdultPassenger(
            personal_info={
                "name": {"first_name": "John", "last_name": "Doe"},
                "date_of_birth": dob,
            }
        )
        assert adult.personal_info.date_of_birth == dob

    def test_adult_passenger_validation_fails_for_under_12(self):
        """Test that AdultPassenger rejects under 12 age."""
        dob = (datetime.now() - timedelta(days=365.25 * 11)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValidationError, match="Adult passengers must be at least 12 years old"
        ):
            AdultPassenger(
                personal_info={
                    "name": {"first_name": "John", "last_name": "Doe"},
                    "date_of_birth": dob,
                }
            )

    def test_child_passenger_validation_passes_for_valid_age(self):
        """Test that ChildPassenger validates age on instantiation."""
        dob = (datetime.now() - timedelta(days=365.25 * 5)).strftime("%Y-%m-%d")
        child = ChildPassenger(
            personal_info={
                "name": {"first_name": "Jane", "last_name": "Doe"},
                "date_of_birth": dob,
            }
        )
        assert child.personal_info.date_of_birth == dob

    def test_child_passenger_validation_fails_for_under_2(self):
        """Test that ChildPassenger rejects under 2 age."""
        dob = (datetime.now() - timedelta(days=365.25 * 1)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValidationError, match="Child passengers must be at least 2 years old"
        ):
            ChildPassenger(
                personal_info={
                    "name": {"first_name": "Jane", "last_name": "Doe"},
                    "date_of_birth": dob,
                }
            )

    def test_child_passenger_validation_fails_for_12_or_older(self):
        """Test that ChildPassenger rejects 12+ age."""
        dob = (datetime.now() - timedelta(days=365.25 * 12)).strftime("%Y-%m-%d")
        with pytest.raises(
            ValidationError, match="Child passengers must be under 12 years old"
        ):
            ChildPassenger(
                personal_info={
                    "name": {"first_name": "Jane", "last_name": "Doe"},
                    "date_of_birth": dob,
                }
            )

    def test_infant_passenger_validation_passes_for_valid_age(self):
        """Test that InfantPassenger validates age on instantiation."""
        dob = (datetime.now() - timedelta(days=365.25 * 1)).strftime("%Y-%m-%d")
        infant = InfantPassenger(
            personal_info={
                "name": {"first_name": "Baby", "last_name": "Doe"},
                "date_of_birth": dob,
            }
        )
        assert infant.personal_info.date_of_birth == dob

    def test_infant_passenger_validation_fails_for_2_or_older(self):
        """Test that InfantPassenger rejects 2+ age."""
        # Exactly 2 years old (same month and day, 2 years earlier)
        today = datetime.now()
        dob = today.replace(year=today.year - 2).strftime("%Y-%m-%d")
        with pytest.raises(
            ValidationError, match="Infant passengers must be under 2 years old"
        ):
            InfantPassenger(
                personal_info={
                    "name": {"first_name": "Baby", "last_name": "Doe"},
                    "date_of_birth": dob,
                }
            )

    def test_adult_passenger_allows_none_date_of_birth(self):
        """Test that AdultPassenger allows None date of birth (optional field)."""
        adult = AdultPassenger(
            personal_info={
                "name": {"first_name": "John", "last_name": "Doe"},
                "date_of_birth": None,
            }
        )
        assert adult.personal_info.date_of_birth is None


class TestValidateAgeRequirements:
    """Test validate_age_requirements function (booking-time validation)."""

    def test_adult_under_12_raises(self):
        """Adult with DOB yielding age < 12 should raise INVALID_ADULT_AGE."""
        today = datetime.now(UTC).date()
        dob_11_years_ago = (today.replace(year=today.year - 11)).strftime("%Y-%m-%d")
        personal_info = PersonalInfo.model_construct(
            name={"first_name": "Child", "last_name": "AsAdult"},
            date_of_birth=dob_11_years_ago,
            nationality="US",
        )
        adult = AdultPassenger.model_construct(personal_info=personal_info)
        groups = PassengerGroups.model_construct(
            adults=[adult], children=None, infants=None
        )

        with pytest.raises(FlightBookingError) as exc_info:
            validate_age_requirements(groups)
        assert exc_info.value.code == "INVALID_ADULT_AGE"
        assert "at least 12 years old" in exc_info.value.message

    def test_adult_12_or_older_passes(self):
        """Adult with DOB yielding age >= 12 should pass."""
        today = datetime.now(UTC).date()
        dob_12_years_ago = (today.replace(year=today.year - 12)).strftime("%Y-%m-%d")
        personal_info = PersonalInfo.model_construct(
            name={"first_name": "Adult", "last_name": "Valid"},
            date_of_birth=dob_12_years_ago,
            nationality="US",
        )
        adult = AdultPassenger.model_construct(personal_info=personal_info)
        groups = PassengerGroups.model_construct(
            adults=[adult], children=None, infants=None
        )

        validate_age_requirements(groups)  # Should not raise


class TestCalculateAge:
    """Test calculate_age function for age calculation edge cases."""

    def test_calculate_age_none_returns_none(self):
        """Test that None date of birth returns None."""
        assert calculate_age(None) is None

    def test_calculate_age_empty_string_returns_none(self):
        """Test that empty string returns None."""
        assert calculate_age("") is None

    def test_calculate_age_valid_date_format(self):
        """Test that valid ISO date format calculates age correctly."""
        # 25 years old
        dob = (datetime.now(UTC) - timedelta(days=365.25 * 25)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 25

    def test_calculate_age_exactly_2_years_old(self):
        """Test boundary case: exactly 2 years old."""
        today = datetime.now(UTC)
        # Exactly 2 years ago, same month and day
        dob = (today - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
        age = calculate_age(dob)
        # Should be 2 (or close to 2 depending on leap years)
        assert age in (1, 2)  # Account for leap year variations

    def test_calculate_age_exactly_2_years_old_same_date(self):
        """Test boundary case: exactly 2 years ago today."""
        today = datetime.now(UTC)
        dob_date = today.replace(year=today.year - 2)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 2

    def test_calculate_age_exactly_12_years_old(self):
        """Test boundary case: exactly 12 years old."""
        today = datetime.now(UTC)
        dob_date = today.replace(year=today.year - 12)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 12

    def test_calculate_age_one_day_before_2nd_birthday(self):
        """Test edge case: one day before 2nd birthday (should be 1)."""
        today = datetime.now(UTC)
        # 1 year and 364 days ago
        dob_date = today - timedelta(days=365 * 2 - 1)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 1

    def test_calculate_age_one_day_before_12th_birthday(self):
        """Test edge case: one day before 12th birthday (should be 11)."""
        today = datetime.now(UTC)
        # 11 years and 364 days ago
        dob_date = today - timedelta(days=365 * 12 - 1)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 11

    def test_calculate_age_birthday_today(self):
        """Test edge case: birthday is today (should count as that age)."""
        today = datetime.now(UTC)
        dob = today.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 0

    def test_calculate_age_birthday_yesterday(self):
        """Test edge case: birthday was yesterday (should be 1 year older than today)."""
        today = datetime.now(UTC)
        yesterday = today - timedelta(days=1)
        # If yesterday was their birthday, they turned 1 year old yesterday
        dob = yesterday.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        # Should be 0 (born yesterday) or 1 (if it was their 1st birthday)
        # Actually, if born yesterday, age should be 0
        assert age == 0

    def test_calculate_age_one_year_ago_today(self):
        """Test edge case: born exactly one year ago today."""
        today = datetime.now(UTC)
        one_year_ago = today.replace(year=today.year - 1)
        dob = one_year_ago.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 1

    def test_calculate_age_one_year_ago_yesterday(self):
        """Test edge case: born one year and one day ago."""
        today = datetime.now(UTC)
        one_year_one_day_ago = today.replace(year=today.year - 1) - timedelta(days=1)
        dob = one_year_one_day_ago.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 1

    def test_calculate_age_iso_datetime_with_timezone(self):
        """Test that ISO datetime with timezone works correctly."""
        today = datetime.now(UTC)
        five_years_ago = today.replace(year=today.year - 5)
        dob = five_years_ago.isoformat()
        age = calculate_age(dob)
        assert age == 5

    def test_calculate_age_iso_datetime_with_z_timezone(self):
        """Test that ISO datetime with 'Z' timezone indicator works."""
        today = datetime.now(UTC)
        five_years_ago = today.replace(year=today.year - 5)
        dob = five_years_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        age = calculate_age(dob)
        assert age == 5

    def test_calculate_age_invalid_format_returns_none(self):
        """Test that invalid date format returns None."""
        assert calculate_age("not-a-date") is None
        assert calculate_age("2024-13-45") is None  # Invalid month/day
        assert calculate_age("abcd-ef-gh") is None

    def test_calculate_age_future_date(self):
        """Test that future date still calculates (no validation in calculate_age)."""
        future_date = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%d")
        age = calculate_age(future_date)
        # Should return negative age or 0, but function doesn't validate
        assert age is not None
        assert age <= 0

    def test_calculate_age_timezone_naive_assumes_utc(self):
        """Test that timezone-naive datetime strings are treated as UTC."""
        today = datetime.now(UTC)
        three_years_ago = today.replace(year=today.year - 3)
        # Create timezone-naive string
        dob = three_years_ago.replace(tzinfo=None).isoformat()
        age = calculate_age(dob)
        assert age == 3

    def test_calculate_age_11_years_364_days(self):
        """Test edge case: 11 years and 364 days old (should be 11, not 12)."""
        today = datetime.now(UTC)
        dob_date = today.replace(year=today.year - 11) - timedelta(days=1)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 11

    def test_calculate_age_1_year_364_days(self):
        """Test edge case: 1 year and 364 days old (should be 1, not 2)."""
        today = datetime.now(UTC)
        dob_date = today.replace(year=today.year - 1) - timedelta(days=1)
        dob = dob_date.strftime("%Y-%m-%d")
        age = calculate_age(dob)
        assert age == 1
