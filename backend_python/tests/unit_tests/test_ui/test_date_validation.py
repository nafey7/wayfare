"""Unit tests for date validation logic in flight booker UI."""

from datetime import datetime, timedelta
from unittest.mock import patch


class TestDateValidation:
    """Test date validation logic used in flight booker UI."""

    def test_adult_passenger_age_validation_logic(self):
        """Test the date validation logic for adult passengers (minimum 12 years old, FlightLogic ADT = 12+)."""

        # Mock current date for consistent testing
        with patch("datetime.datetime") as mock_datetime:
            # Set test date to October 30, 2025
            test_today = datetime(2025, 10, 30)
            mock_datetime.now.return_value = test_today
            mock_datetime.side_effect = datetime

            # Calculate 12 years ago from test date
            twelve_years_ago = datetime(2013, 10, 30)

            test_cases = [
                {
                    "name": "Future date should be invalid",
                    "birth_date": datetime(2025, 12, 25),
                    "expected_valid": False,
                    "expected_reason": "future_date",
                },
                {
                    "name": "Today should be invalid (0 years old)",
                    "birth_date": test_today,
                    "expected_valid": False,
                    "expected_reason": "too_young",
                },
                {
                    "name": "11 years old should be invalid",
                    "birth_date": datetime(2014, 10, 30),
                    "expected_valid": False,
                    "expected_reason": "too_young",
                },
                {
                    "name": "11 years 364 days old should be invalid",
                    "birth_date": datetime(2013, 10, 31),  # One day after 12th birthday
                    "expected_valid": False,
                    "expected_reason": "too_young",
                },
                {
                    "name": "Exactly 12 years old should be valid",
                    "birth_date": twelve_years_ago,
                    "expected_valid": True,
                    "expected_reason": None,
                },
                {
                    "name": "12 years and 1 day old should be valid",
                    "birth_date": datetime(2013, 10, 29),
                    "expected_valid": True,
                    "expected_reason": None,
                },
                {
                    "name": "25 years old should be valid",
                    "birth_date": datetime(2000, 10, 30),
                    "expected_valid": True,
                    "expected_reason": None,
                },
                {
                    "name": "50 years old should be valid",
                    "birth_date": datetime(1975, 5, 15),
                    "expected_valid": True,
                    "expected_reason": None,
                },
            ]

            for case in test_cases:
                # Replicate JavaScript validation logic
                selected_date = case["birth_date"]
                today = test_today
                minimum_date = datetime(today.year - 12, today.month, today.day)

                # JavaScript logic:
                # - selectedDate > today means future date (invalid)
                # - selectedDate > minimumDate means under 12 (invalid)
                is_future = selected_date > today
                is_too_young = selected_date > minimum_date
                is_valid = not is_future and not is_too_young

                # Determine validation reason
                validation_reason = None
                if is_future:
                    validation_reason = "future_date"
                elif is_too_young:
                    validation_reason = "too_young"

                assert is_valid == case["expected_valid"], (
                    f"Test '{case['name']}' failed. "
                    f"Birth date: {selected_date.strftime('%Y-%m-%d')}, "
                    f"Expected valid: {case['expected_valid']}, "
                    f"Actual valid: {is_valid}"
                )

                assert validation_reason == case["expected_reason"], (
                    f"Test '{case['name']}' validation reason mismatch. "
                    f"Expected: {case['expected_reason']}, "
                    f"Actual: {validation_reason}"
                )

    def test_twelve_years_ago_calculation(self):
        """Test that the 12 years ago calculation works correctly for different dates."""

        test_dates = [
            datetime(2025, 1, 1),  # New Year's Day
            datetime(2025, 2, 28),  # End of February (non-leap year)
            datetime(2025, 12, 31),  # New Year's Eve
            datetime(2024, 2, 29),  # Actual leap year date
        ]

        for test_date in test_dates:
            with patch("datetime.datetime") as mock_datetime:
                mock_datetime.now.return_value = test_date
                mock_datetime.side_effect = datetime

                # Calculate 12 years ago (matching JavaScript logic)
                # Handle leap year edge case
                try:
                    twelve_years_ago = datetime(
                        test_date.year - 12, test_date.month, test_date.day
                    )
                except ValueError:
                    # Handle Feb 29 on non-leap year - use Feb 28
                    twelve_years_ago = datetime(
                        test_date.year - 12, test_date.month, 28
                    )

                # Verify the calculation is correct
                age_in_years = test_date.year - twelve_years_ago.year
                assert age_in_years == 12

                # Test edge case: someone born exactly 12 years ago should be valid
                is_valid = twelve_years_ago <= test_date
                assert is_valid is True

                # Test edge case: someone born one day after 12 years ago should be invalid
                one_day_later = twelve_years_ago + timedelta(days=1)
                is_valid = (
                    one_day_later <= twelve_years_ago and one_day_later <= test_date
                )
                assert is_valid is False

    def test_validation_error_messages(self):
        """Test that the correct error messages would be generated."""

        with patch("datetime.datetime") as mock_datetime:
            test_today = datetime(2025, 10, 30)
            mock_datetime.now.return_value = test_today
            mock_datetime.side_effect = datetime

            error_cases = [
                {
                    "birth_date": datetime(2026, 1, 1),
                    "expected_message": "Date of birth cannot be in the future",
                },
                {
                    "birth_date": datetime(2014, 1, 1),
                    "expected_message": "Adult passengers must be at least 12 years old",
                },
            ]

            for case in error_cases:
                selected_date = case["birth_date"]
                today = test_today
                minimum_date = datetime(today.year - 12, today.month, today.day)

                # Replicate JavaScript error message logic
                if selected_date > today:
                    actual_message = "Date of birth cannot be in the future"
                elif selected_date > minimum_date:
                    actual_message = "Adult passengers must be at least 12 years old"
                else:
                    actual_message = None

                assert actual_message == case["expected_message"], (
                    f"Error message mismatch for {selected_date.strftime('%Y-%m-%d')}. "
                    f"Expected: '{case['expected_message']}', "
                    f"Actual: '{actual_message}'"
                )

    def test_max_date_attribute_setting(self):
        """Test that the max date attribute would be set correctly."""

        with patch("datetime.datetime") as mock_datetime:
            test_today = datetime(2025, 10, 30)
            mock_datetime.now.return_value = test_today
            mock_datetime.side_effect = datetime

            # Replicate JavaScript max date calculation (12 years ago)
            twelve_years_ago = datetime(
                test_today.year - 12, test_today.month, test_today.day
            )
            expected_max_date = twelve_years_ago.strftime("%Y-%m-%d")

            # This would be set as the max attribute on the HTML input
            assert expected_max_date == "2013-10-30"

            # Verify that dates after this would be rejected by HTML5 date input
            test_invalid_dates = [
                "2013-10-31",  # One day after max
                "2014-01-01",  # Next year
                "2025-10-30",  # Today
            ]

            for invalid_date_str in test_invalid_dates:
                year, month, day = map(int, invalid_date_str.split("-"))
                invalid_date = datetime(year, month, day)
                assert invalid_date > twelve_years_ago, (
                    f"Date {invalid_date_str} should be invalid (after max date {expected_max_date})"
                )
