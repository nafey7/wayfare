"""Unit tests for flight booker navigation logic."""

from typing import ClassVar

import pytest


class TestFlightBookerNavigation:
    """Test navigation state management and validation in flight booker UI."""

    # Define step progression order for validation
    STEP_ORDER: ClassVar[list[str]] = [
        "search",
        "select",
        "rules",
        "passenger",
        "review",
        "payment",
        "confirmation",
    ]

    # Test scenarios for navigation validation
    NAVIGATION_TEST_SCENARIOS: ClassVar[list[dict]] = [
        {
            "name": "Navigate from search to search (same step)",
            "current_step": "search",
            "target_step": "search",
            "completed_steps": [],
            "has_search_results": False,
            "has_selected_flight": False,
            "has_fare_rules": False,
            "expected_allowed": True,
            "expected_reason": "current_step",
        },
        {
            "name": "Cannot navigate to future step without completion",
            "current_step": "search",
            "target_step": "select",
            "completed_steps": [],
            "has_search_results": False,
            "has_selected_flight": False,
            "has_fare_rules": False,
            "expected_allowed": False,
            "expected_reason": "step_not_completed",
        },
        {
            "name": "Can navigate to completed step",
            "current_step": "select",
            "target_step": "search",
            "completed_steps": ["search"],
            "has_search_results": True,
            "has_selected_flight": False,
            "has_fare_rules": False,
            "expected_allowed": True,
            "expected_reason": "completed_step",
        },
        {
            "name": "Cannot navigate to select without search results",
            "current_step": "rules",
            "target_step": "select",
            "completed_steps": ["search", "select"],
            "has_search_results": False,
            "has_selected_flight": True,
            "has_fare_rules": True,
            "expected_allowed": False,
            "expected_reason": "missing_data",
        },
        {
            "name": "Cannot navigate to rules without selected flight",
            "current_step": "passenger",
            "target_step": "rules",
            "completed_steps": ["search", "select", "rules"],
            "has_search_results": True,
            "has_selected_flight": False,
            "has_fare_rules": True,
            "expected_allowed": False,
            "expected_reason": "missing_data",
        },
        {
            "name": "Cannot navigate to passenger without fare rules",
            "current_step": "review",
            "target_step": "passenger",
            "completed_steps": ["search", "select", "rules", "passenger"],
            "has_search_results": True,
            "has_selected_flight": True,
            "has_fare_rules": False,
            "expected_allowed": False,
            "expected_reason": "missing_data",
        },
        {
            "name": "Can navigate to completed step with all data",
            "current_step": "review",
            "target_step": "search",
            "completed_steps": ["search", "select", "rules", "passenger"],
            "has_search_results": True,
            "has_selected_flight": True,
            "has_fare_rules": True,
            "expected_allowed": True,
            "expected_reason": "completed_step",
        },
        {
            "name": "Can navigate through full completed flow",
            "current_step": "confirmation",
            "target_step": "passenger",
            "completed_steps": [
                "search",
                "select",
                "rules",
                "passenger",
                "review",
                "payment",
            ],
            "has_search_results": True,
            "has_selected_flight": True,
            "has_fare_rules": True,
            "expected_allowed": True,
            "expected_reason": "completed_step",
        },
    ]

    def test_step_order_definition(self):
        """Test that step order is defined correctly."""
        expected_steps = [
            "search",
            "select",
            "rules",
            "passenger",
            "review",
            "payment",
            "confirmation",
        ]
        assert expected_steps == self.STEP_ORDER
        assert len(self.STEP_ORDER) == 7

    def test_initial_booking_state(self):
        """Test initial state allows only search step access."""
        # Mock initial booking state
        booking_state = self._create_booking_state(
            current_step="search",
            completed_steps=[],
            search_results=None,
            selected_flight=None,
            fare_rules=None,
        )

        # Should be able to access current step
        assert self._can_navigate_to_step("search", booking_state)

        # Should not be able to access future steps
        for step in [
            "select",
            "rules",
            "passenger",
            "review",
            "payment",
            "confirmation",
        ]:
            assert not self._can_navigate_to_step(step, booking_state)

    def test_step_completion_enables_navigation(self):
        """Test that completing a step enables navigation back to it."""
        # Mock state with completed search step
        booking_state = self._create_booking_state(
            current_step="select",
            completed_steps=["search"],
            search_results=["flight1", "flight2"],
            selected_flight=None,
            fare_rules=None,
        )

        # Should be able to navigate back to completed step
        assert self._can_navigate_to_step("search", booking_state)

        # Should be able to stay on current step
        assert self._can_navigate_to_step("select", booking_state)

        # Should not be able to navigate to future steps
        assert not self._can_navigate_to_step("rules", booking_state)

    def test_data_requirements_validation(self):
        """Test that navigation validates required data exists."""
        # Test select step requires search results
        booking_state = self._create_booking_state(
            current_step="rules",
            completed_steps=["search", "select"],
            search_results=None,  # Missing data
            selected_flight="flight1",
            fare_rules={"rules": "test"},
        )

        assert not self._can_navigate_to_step("select", booking_state)

        # Test rules step requires selected flight
        booking_state = self._create_booking_state(
            current_step="passenger",
            completed_steps=["search", "select", "rules"],
            search_results=["flight1"],
            selected_flight=None,  # Missing data
            fare_rules={"rules": "test"},
        )

        assert not self._can_navigate_to_step("rules", booking_state)

        # Test passenger step requires fare rules
        booking_state = self._create_booking_state(
            current_step="review",
            completed_steps=["search", "select", "rules", "passenger"],
            search_results=["flight1"],
            selected_flight="flight1",
            fare_rules=None,  # Missing data
        )

        assert not self._can_navigate_to_step("passenger", booking_state)

    @pytest.mark.parametrize("scenario", NAVIGATION_TEST_SCENARIOS)
    def test_navigation_scenarios(self, scenario):
        """Test various navigation scenarios."""
        # Create booking state based on scenario
        booking_state = self._create_booking_state(
            current_step=scenario["current_step"],
            completed_steps=scenario["completed_steps"],
            search_results=["flight1"] if scenario["has_search_results"] else None,
            selected_flight="flight1" if scenario["has_selected_flight"] else None,
            fare_rules={"rules": "test"} if scenario["has_fare_rules"] else None,
        )

        # Test navigation
        can_navigate = self._can_navigate_to_step(
            scenario["target_step"], booking_state
        )

        assert can_navigate == scenario["expected_allowed"], (
            f"Navigation test failed: {scenario['name']}\n"
            f"Current: {scenario['current_step']} -> Target: {scenario['target_step']}\n"
            f"Expected allowed: {scenario['expected_allowed']}, Got: {can_navigate}\n"
            f"Completed steps: {scenario['completed_steps']}\n"
            f"Data state: search_results={scenario['has_search_results']}, "
            f"selected_flight={scenario['has_selected_flight']}, "
            f"fare_rules={scenario['has_fare_rules']}"
        )

    def test_step_indicator_css_classes(self):
        """Test that step indicators would have correct CSS classes."""
        # Mock DOM element state
        booking_state = self._create_booking_state(
            current_step="passenger",
            completed_steps=["search", "select", "rules"],
            search_results=["flight1"],
            selected_flight="flight1",
            fare_rules={"rules": "test"},
        )

        expected_classes = {
            "search": ["completed"],
            "select": ["completed"],
            "rules": ["completed"],
            "passenger": ["active"],
            "review": [],
            "payment": [],
            "confirmation": [],
        }

        for step, expected in expected_classes.items():
            actual_classes = self._get_step_indicator_classes(step, booking_state)
            assert actual_classes == expected, (
                f"CSS classes mismatch for {step}: expected {expected}, got {actual_classes}"
            )

    def test_navigation_error_messages(self):
        """Test that appropriate error messages are generated."""
        error_scenarios = [
            {
                "target_step": "select",
                "booking_state": self._create_booking_state(
                    "rules", ["search", "select"], None, "flight1", {"rules": "test"}
                ),
                "expected_message": "Please search for flights first.",
            },
            {
                "target_step": "rules",
                "booking_state": self._create_booking_state(
                    "passenger",
                    ["search", "select", "rules"],
                    ["flight1"],
                    None,
                    {"rules": "test"},
                ),
                "expected_message": "Please select a flight first.",
            },
            {
                "target_step": "passenger",
                "booking_state": self._create_booking_state(
                    "review",
                    ["search", "select", "rules", "passenger"],
                    ["flight1"],
                    "flight1",
                    None,
                ),
                "expected_message": "Please review flight rules first.",
            },
            {
                "target_step": "review",
                "booking_state": self._create_booking_state(
                    "search", [], None, None, None
                ),
                "expected_message": "Please complete previous steps to access review.",
            },
        ]

        for scenario in error_scenarios:
            error_message = self._get_navigation_error_message(
                scenario["target_step"], scenario["booking_state"]
            )
            assert error_message == scenario["expected_message"], (
                f"Error message mismatch for {scenario['target_step']}: "
                f"expected '{scenario['expected_message']}', got '{error_message}'"
            )

    def test_full_booking_flow_navigation(self):
        """Test navigation through complete booking flow."""
        # Start with empty state
        booking_state = self._create_booking_state("search", [], None, None, None)

        # Progress through each step
        steps_progression = [
            ("search", ["search"], ["flight1"], None, None),
            ("select", ["search", "select"], ["flight1"], "flight1", None),
            (
                "rules",
                ["search", "select", "rules"],
                ["flight1"],
                "flight1",
                {"rules": "test"},
            ),
            (
                "passenger",
                ["search", "select", "rules", "passenger"],
                ["flight1"],
                "flight1",
                {"rules": "test"},
            ),
            (
                "review",
                ["search", "select", "rules", "passenger", "review"],
                ["flight1"],
                "flight1",
                {"rules": "test"},
            ),
            (
                "payment",
                ["search", "select", "rules", "passenger", "review", "payment"],
                ["flight1"],
                "flight1",
                {"rules": "test"},
            ),
            (
                "confirmation",
                [
                    "search",
                    "select",
                    "rules",
                    "passenger",
                    "review",
                    "payment",
                    "confirmation",
                ],
                ["flight1"],
                "flight1",
                {"rules": "test"},
            ),
        ]

        for (
            current_step,
            completed_steps,
            search_results,
            selected_flight,
            fare_rules,
        ) in steps_progression:
            booking_state = self._create_booking_state(
                current_step,
                completed_steps,
                search_results,
                selected_flight,
                fare_rules,
            )

            # Should be able to navigate to any completed step
            for completed_step in completed_steps:
                if (
                    completed_step != current_step
                ):  # Don't test current step (different logic)
                    assert self._can_navigate_to_step(completed_step, booking_state), (
                        f"Should be able to navigate from {current_step} back to completed step {completed_step}"
                    )

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        booking_state = self._create_booking_state("search", [], None, None, None)

        # Test invalid step name
        assert not self._can_navigate_to_step("invalid_step", booking_state)

        # Test empty step name
        assert not self._can_navigate_to_step("", booking_state)

        # Test None step name
        assert not self._can_navigate_to_step(None, booking_state)

    def _create_booking_state(
        self, current_step, completed_steps, search_results, selected_flight, fare_rules
    ):
        """Create a mock booking state for testing."""
        return {
            "current_step": current_step,
            "completed_steps": completed_steps,
            "search_results": search_results,
            "selected_flight": selected_flight,
            "fare_rules": fare_rules,
        }

    def _can_navigate_to_step(self, target_step, booking_state):
        """
        Replicate the JavaScript navigateToStep validation logic.

        This function mirrors the logic from the flight booker's navigateToStep function.
        """
        if not target_step or target_step not in self.STEP_ORDER:
            return False

        current_step = booking_state["current_step"]
        completed_steps = booking_state["completed_steps"]

        # Allow navigation to current step
        if target_step == current_step:
            return True

        # Allow navigation to completed steps only
        if target_step not in completed_steps:
            return False

        # Check if required data exists for the target step
        if target_step == "select":
            search_results = booking_state["search_results"]
            return search_results is not None and len(search_results) > 0

        if target_step == "rules":
            selected_flight = booking_state["selected_flight"]
            return selected_flight is not None

        if target_step == "passenger":
            fare_rules = booking_state["fare_rules"]
            return fare_rules is not None

        return True

    def _get_step_indicator_classes(self, step, booking_state):
        """Get the CSS classes that would be applied to a step indicator."""
        current_step = booking_state["current_step"]
        completed_steps = booking_state["completed_steps"]

        classes = []

        if step == current_step:
            classes.append("active")

        if step in completed_steps:
            classes.append("completed")

        return classes

    def _get_navigation_error_message(self, target_step, booking_state):
        """Get the error message that would be shown for blocked navigation."""
        if not self._can_navigate_to_step(target_step, booking_state):
            current_step = booking_state["current_step"]
            completed_steps = booking_state["completed_steps"]

            # Check specific data requirements
            if target_step == "select":
                search_results = booking_state["search_results"]
                if not search_results or len(search_results) == 0:
                    return "Please search for flights first."

            if target_step == "rules":
                selected_flight = booking_state["selected_flight"]
                if not selected_flight:
                    return "Please select a flight first."

            if target_step == "passenger":
                fare_rules = booking_state["fare_rules"]
                if not fare_rules:
                    return "Please review flight rules first."

            # Generic message for non-completed steps
            if target_step not in completed_steps:
                return f"Please complete previous steps to access {target_step}."

        return None


if __name__ == "__main__":
    """Run tests directly with python -m pytest or python test_flight_booker_navigation.py"""
    test_instance = TestFlightBookerNavigation()

    print("Running flight booker navigation tests...")
    print("=" * 80)

    # Test scenarios
    for i, scenario in enumerate(test_instance.NAVIGATION_TEST_SCENARIOS, 1):
        try:
            test_instance.test_navigation_scenarios(scenario)
            status = "✅ PASS"
        except AssertionError as e:
            status = f"❌ FAIL - {e}"

        print(f"{i:2d}. {scenario['name']}: {status}")

    print("=" * 80)

    # Test other key functions
    test_methods = [
        "test_initial_booking_state",
        "test_step_completion_enables_navigation",
        "test_data_requirements_validation",
        "test_step_indicator_css_classes",
        "test_navigation_error_messages",
        "test_full_booking_flow_navigation",
        "test_edge_cases",
    ]

    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ PASS: {method_name}")
        except AssertionError as e:
            print(f"❌ FAIL: {method_name} - {e}")

    print("=" * 80)
    print("Navigation tests completed!")
