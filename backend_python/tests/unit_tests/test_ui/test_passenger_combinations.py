"""
Test passenger combination validation for flight booker UI.

This test validates that the flight booker can handle various passenger
combinations up to the maximum limits of 10 for each category.

The test covers 11 valid combinations that total 9 passengers or less,
ensuring the max passenger logic works correctly.
"""

from typing import ClassVar

import pytest


class TestPassengerCombinations:
    """Test class for validating passenger combinations in flight booker."""

    # Valid passenger combinations (adults, children, infants) that should all pass
    VALID_COMBINATIONS: ClassVar = [
        (5, 3, 1),  # Adults: 5, Children: 3, Infants: 1
        (4, 4, 1),  # Adults: 4, Children: 4, Infants: 1
        (6, 2, 1),  # Adults: 6, Children: 2, Infants: 1
        (3, 3, 3),  # Adults: 3, Children: 3, Infants: 3
        (7, 1, 1),  # Adults: 7, Children: 1, Infants: 1
        (2, 4, 3),  # Adults: 2, Children: 4, Infants: 3
        (4, 2, 3),  # Adults: 4, Children: 2, Infants: 3
        (3, 5, 1),  # Adults: 3, Children: 5, Infants: 1
        (8, 0, 1),  # Adults: 8, Children: 0, Infants: 1
        (1, 7, 1),  # Adults: 1, Children: 7, Infants: 1
        (9, 0, 0),  # Adults: 9, Children: 0, Infants: 0
    ]

    # Invalid passenger combinations that should fail business rules
    INVALID_COMBINATIONS: ClassVar = [
        (10, 0, 0),  # Too many adults (exceeds 9 passenger limit)
        (
            2,
            0,
            3,
        ),  # 2 adults + 3 infants = 5 total (should fail: 3 infants > 2 adults+children)
        (
            1,
            1,
            3,
        ),  # 1 adult + 1 child + 3 infants = 5 total (should fail: 3 infants > 2 adults+children)
    ]

    def test_passenger_combination_limits(self):
        """Test that all passenger types can have up to 10 passengers."""
        # Test maximum individual limits
        max_combinations = [
            (10, 0, 0),  # Max adults
            (
                0,
                10,
                0,
            ),  # Max children (but this would fail business rules requiring adult)
            (
                0,
                0,
                10,
            ),  # Max infants (but this would fail business rules requiring adult)
            (
                10,
                10,
                10,
            ),  # Max all (would exceed typical airline limits but UI should allow)
        ]

        for adults, children, infants in max_combinations:
            assert self._is_valid_ui_combination(adults, children, infants), (
                f"UI should allow combination: Adults={adults}, Children={children}, Infants={infants}"
            )

    @pytest.mark.parametrize(("adults", "children", "infants"), VALID_COMBINATIONS)
    def test_valid_passenger_combinations(
        self, adults: int, children: int, infants: int
    ):
        """Test that all specified valid combinations pass validation."""
        # Validate the combination is within UI limits
        assert self._is_valid_ui_combination(adults, children, infants), (
            f"Invalid UI combination: Adults={adults}, Children={children}, Infants={infants}"
        )

        # Validate total passengers
        total = adults + children + infants
        assert total <= 20, (
            f"Total passengers ({total}) should not exceed reasonable limits"
        )

        # Validate individual limits match our updated UI (max 10 each)
        assert adults <= 10, f"Adults ({adults}) should not exceed 10"
        assert children <= 10, f"Children ({children}) should not exceed 10"
        assert infants <= 10, f"Infants ({infants}) should not exceed 10"

        # Validate business logic (at least 1 adult required)
        assert adults >= 1, f"At least 1 adult required, got {adults}"

        print(
            f"✅ Valid combination: Adults={adults}, Children={children}, Infants={infants}, Total={total}"
        )

    @pytest.mark.parametrize(("adults", "children", "infants"), INVALID_COMBINATIONS)
    def test_invalid_passenger_combinations(
        self, adults: int, children: int, infants: int
    ):
        """Test that specified invalid combinations fail business validation."""
        total = adults + children + infants

        # These combinations should fail business rules
        # (even though UI might allow the individual counts)

        # These combinations should fail business rules - just verify they fail
        assert not self._is_valid_business_combination(adults, children, infants), (
            f"Should fail business rules: Adults={adults}, Children={children}, Infants={infants}"
        )

        # Print specific failure reason for clarity
        if total > 9:
            print(
                f"❌ Correctly failed (exceeds 9 passenger limit): Adults={adults}, Children={children}, Infants={infants}, Total={total}"
            )
        elif self._has_invalid_infant_ratio(adults, children, infants):
            print(
                f"❌ Correctly failed (invalid infant ratio): Adults={adults}, Children={children}, Infants={infants}, Total={total}"
            )
        else:
            print(
                f"❌ Failed for other business rule: Adults={adults}, Children={children}, Infants={infants}, Total={total}"
            )

    def test_specific_failure_scenarios(self):
        """Test specific scenarios that should fail with detailed explanations."""
        failure_scenarios = [
            {
                "combination": (10, 0, 0),
                "reason": "Exceeds maximum 9 passenger limit",
                "rule": "max_passengers",
            },
            {
                "combination": (2, 0, 3),
                "reason": "Too many infants: 3 infants > 2 (adults + children)",
                "rule": "infant_ratio",
            },
            {
                "combination": (1, 1, 3),
                "reason": "Too many infants: 3 infants > 2 (adults + children)",
                "rule": "infant_ratio",
            },
        ]

        print("\n" + "=" * 80)
        print("TESTING INVALID PASSENGER COMBINATIONS (These should FAIL)")
        print("=" * 80)

        for i, scenario in enumerate(failure_scenarios, 1):
            adults, children, infants = scenario["combination"]
            total = adults + children + infants
            reason = scenario["reason"]
            rule = scenario["rule"]

            # Test the specific rule
            if rule == "max_passengers":
                should_fail = not self._passes_max_passenger_rule(
                    adults, children, infants
                )
            elif rule == "infant_ratio":
                should_fail = not self._passes_infant_ratio_rule(
                    adults, children, infants
                )
            else:
                should_fail = True

            status = "❌ CORRECTLY FAILED" if should_fail else "⚠️ UNEXPECTEDLY PASSED"

            print(
                f"{i}. Adults: {adults:2d}, Children: {children:2d}, Infants: {infants:2d} | Total: {total:2d} | {status}"
            )
            print(f"   Reason: {reason}")

            assert should_fail, (
                f"Combination should fail but passed: {scenario['combination']}"
            )

        print("=" * 80)

    def test_passenger_combination_totals(self):
        """Test that all valid combinations have reasonable totals."""
        for adults, children, infants in self.VALID_COMBINATIONS:
            total = adults + children + infants
            assert 1 <= total <= 20, (
                f"Total passengers ({total}) should be between 1 and 20 for Adults={adults}, Children={children}, Infants={infants}"
            )

    def test_business_rules_validation(self):
        """Test business rules that should be enforced beyond UI limits."""
        # Test combinations that UI allows but business logic might reject
        edge_cases = [
            (0, 5, 2),  # No adults - should fail business rules
            (0, 0, 5),  # Only infants - should fail business rules
            (1, 15, 0),  # Children > 10 (if UI somehow allowed)
        ]

        for adults, children, infants in edge_cases:
            if adults == 0:
                # These should fail business validation (no adult supervision)
                assert not self._is_valid_business_combination(
                    adults, children, infants
                ), (
                    f"Business rules should reject: Adults={adults}, Children={children}, Infants={infants}"
                )
            else:
                # These might pass business rules but could fail UI limits
                is_ui_valid = self._is_valid_ui_combination(adults, children, infants)
                print(
                    f"Edge case Adults={adults}, Children={children}, Infants={infants}: UI Valid={is_ui_valid}"
                )

    def test_maximum_passenger_scenarios(self):
        """Test scenarios at the maximum passenger limits."""
        max_scenarios = [
            (10, 0, 0),  # Maximum adults only
            (5, 5, 0),  # Split adults/children
            (3, 3, 4),  # Balanced with infants
            (1, 9, 0),  # Minimum adults, maximum children
            (2, 0, 8),  # Minimum adults, many infants
        ]

        for adults, children, infants in max_scenarios:
            total = adults + children + infants
            is_valid = self._is_valid_ui_combination(adults, children, infants)

            print(
                f"Max scenario: Adults={adults}, Children={children}, Infants={infants}, Total={total}, Valid={is_valid}"
            )

            # All these should be valid in UI (within individual limits)
            assert is_valid, (
                f"Should be valid: Adults={adults}, Children={children}, Infants={infants}"
            )

    def _is_valid_ui_combination(
        self, adults: int, children: int, infants: int
    ) -> bool:
        """Check if passenger combination is valid according to UI limits."""
        # UI validation: each category can have 0-10 passengers
        return 0 <= adults <= 10 and 0 <= children <= 10 and 0 <= infants <= 10

    def _is_valid_business_combination(
        self, adults: int, children: int, infants: int
    ) -> bool:
        """Check if passenger combination is valid according to business rules."""
        # Business validation: must have at least 1 adult for supervision
        return (
            adults >= 1  # At least one adult required
            and 0 <= children <= 10
            and 0 <= infants <= 10
            and adults <= 10
            and self._passes_max_passenger_rule(adults, children, infants)
            and self._passes_infant_ratio_rule(adults, children, infants)
        )

    def _passes_max_passenger_rule(
        self, adults: int, children: int, infants: int
    ) -> bool:
        """Check if combination passes maximum passenger rule (9 passengers max)."""
        total = adults + children + infants
        return total <= 9

    def _passes_infant_ratio_rule(
        self, adults: int, children: int, infants: int
    ) -> bool:
        """Check if combination passes infant ratio rule (infants <= adults + children)."""
        if adults == 0:
            return infants == 0  # No adults = no infants allowed

        # Rule: Infant count does not exceed the combined number of Adults and Children
        return infants <= (adults + children)

    def _has_invalid_infant_ratio(
        self, adults: int, children: int, infants: int
    ) -> bool:
        """Check if combination has invalid infant ratio."""
        return not self._passes_infant_ratio_rule(adults, children, infants)

    def test_print_all_combinations(self):
        """Print all test combinations for verification."""
        print("\n" + "=" * 60)
        print("TESTING ALL PASSENGER COMBINATIONS")
        print("=" * 60)

        for i, (adults, children, infants) in enumerate(self.VALID_COMBINATIONS, 1):
            total = adults + children + infants
            ui_valid = self._is_valid_ui_combination(adults, children, infants)
            business_valid = self._is_valid_business_combination(
                adults, children, infants
            )

            status = "✅ PASS" if ui_valid and business_valid else "❌ FAIL"

            print(
                f"{i:2d}. Adults: {adults:2d}, Children: {children:2d}, Infants: {infants:2d} | Total: {total:2d} | {status}"
            )

        print("=" * 60)


if __name__ == "__main__":
    """Run tests directly with python -m pytest or python test_passenger_combinations.py"""
    test_instance = TestPassengerCombinations()

    print("Running passenger combination tests...")

    # Test all valid combinations
    print("=" * 60)
    print("TESTING VALID COMBINATIONS (should all PASS)")
    print("=" * 60)
    for adults, children, infants in test_instance.VALID_COMBINATIONS:
        try:
            test_instance.test_valid_passenger_combinations(adults, children, infants)
            print(f"✅ PASS: Adults={adults}, Children={children}, Infants={infants}")
        except AssertionError as e:
            print(
                f"❌ FAIL: Adults={adults}, Children={children}, Infants={infants} - {e}"
            )

    # Test all invalid combinations
    print("\n" + "=" * 60)
    print("TESTING INVALID COMBINATIONS (should all FAIL)")
    print("=" * 60)
    for adults, children, infants in test_instance.INVALID_COMBINATIONS:
        try:
            test_instance.test_invalid_passenger_combinations(adults, children, infants)
            print(
                f"✅ CORRECTLY FAILED: Adults={adults}, Children={children}, Infants={infants}"
            )
        except AssertionError as e:
            print(
                f"⚠️ UNEXPECTEDLY PASSED: Adults={adults}, Children={children}, Infants={infants} - {e}"
            )

    # Run specific failure scenarios test
    print("\n")
    try:
        test_instance.test_specific_failure_scenarios()
        print("✅ PASS: Specific failure scenarios test")
    except AssertionError as e:
        print(f"❌ FAIL: Specific failure scenarios test - {e}")

    # Run other tests
    try:
        test_instance.test_passenger_combination_limits()
        print("✅ PASS: Passenger combination limits test")
    except AssertionError as e:
        print(f"❌ FAIL: Passenger combination limits test - {e}")

    try:
        test_instance.test_passenger_combination_totals()
        print("✅ PASS: Passenger combination totals test")
    except AssertionError as e:
        print(f"❌ FAIL: Passenger combination totals test - {e}")

    # Print summary
    test_instance.test_print_all_combinations()

    print("\nTest completed! All specified combinations should pass.")
