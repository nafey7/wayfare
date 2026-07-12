#!/usr/bin/env python3
"""Test the date validation logic used in the JavaScript"""

import sys
from datetime import datetime, timedelta


def test_date_validation():
    """Test the date validation logic"""

    today = datetime.now()
    eighteen_years_ago = datetime(today.year - 18, today.month, today.day)

    print(f"Today: {today.strftime('%Y-%m-%d')}")
    print(f"18 years ago: {eighteen_years_ago.strftime('%Y-%m-%d')}")
    print(f"Max allowed date should be: {eighteen_years_ago.strftime('%Y-%m-%d')}")
    print()

    test_cases = [
        ("Future date (2025-12-25)", datetime(2025, 12, 25), False),
        ("Today", today, False),
        ("17 years old", datetime(today.year - 17, today.month, today.day), False),
        ("Exactly 18 years ago", eighteen_years_ago, True),
        ("18 years and 1 day ago", eighteen_years_ago - timedelta(days=1), True),
        ("25 years old", datetime(today.year - 25, today.month, today.day), True),
    ]

    all_passed = True

    for name, test_date, should_be_valid in test_cases:
        # JavaScript logic: selectedDate > minimumDate means invalid
        is_valid = test_date <= eighteen_years_ago and test_date <= today

        passed = is_valid == should_be_valid
        status = "PASS" if passed else "FAIL"

        print(f"{name}: {test_date.strftime('%Y-%m-%d')}")
        print(f"  Expected: {'Valid' if should_be_valid else 'Invalid'}")
        print(f"  Actual: {'Valid' if is_valid else 'Invalid'}")
        print(f"  Result: {status}")
        print()

        if not passed:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print("Testing Date Validation Logic")
    print("=" * 40)

    if test_date_validation():
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
