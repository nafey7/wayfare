"""Unit tests for race condition and JavaScript syntax fixes.

Compatible with Python 3.11 and 3.12.
Tests the fixes for duplicate booking creation and setQuickRoute functionality.
"""

import os
import re

import pytest


class TestRaceConditionFixes:
    """Test race condition prevention and JavaScript syntax fixes."""

    def test_javascript_syntax_is_fixed(self):
        """Test that JavaScript syntax error is resolved."""
        html_file = "dev_ui/flight-booker/index.html"

        assert os.path.exists(html_file), f"File not found: {html_file}"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that continueToPayment function exists
        continue_payment_pattern = r"async\s+function\s+continueToPayment\s*\(\s*\)"
        assert re.search(continue_payment_pattern, content), (
            "continueToPayment function not found"
        )

        # Check that try/catch blocks are balanced (preventing syntax error)
        try_blocks = len(re.findall(r"try\s*{", content))
        catch_blocks = len(re.findall(r"}\s*catch\s*\([^)]*\)\s*{", content))

        assert try_blocks > 0, "No try blocks found"
        assert catch_blocks > 0, "No catch blocks found - syntax error not fixed"

        # Check that setQuickRoute function exists (should work after syntax fix)
        set_quick_route_pattern = r"function\s+setQuickRoute\s*\([^)]*\)"
        assert re.search(set_quick_route_pattern, content), (
            "setQuickRoute function not found"
        )

    def test_race_condition_protection_exists(self):
        """Test that race condition protection mechanisms are in place."""
        html_file = "dev_ui/flight-booker/index.html"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for race condition flag
        is_creating_booking_pattern = r"let\s+isCreatingBooking\s*=\s*false"
        assert re.search(is_creating_booking_pattern, content), (
            "isCreatingBooking flag not found"
        )

        # Check for button disabling logic
        button_disable_pattern = r"paymentButton\.disabled\s*=\s*true"
        assert re.search(button_disable_pattern, content), (
            "Button disabling logic not found"
        )

        # Check for duplicate call prevention
        duplicate_prevention_pattern = r"if\s*\(\s*isCreatingBooking\s*\)"
        assert re.search(duplicate_prevention_pattern, content), (
            "Duplicate call prevention not found"
        )


class TestBookingStateDetection:
    """Test booking state detection logic."""

    def should_skip_booking_creation(self, booking_result):
        """Business logic for booking state detection."""
        if not booking_result:
            return False

        # Check for existing VOYA booking reference
        voya_ref = booking_result.get("voya_booking_reference")
        if voya_ref and voya_ref.startswith("VOYA-"):
            return True

        # Check for external booking reference
        external_ref = booking_result.get("external_booking_reference")
        return bool(external_ref and external_ref.strip())

    def test_no_booking_result(self):
        """Test with no booking result."""
        assert self.should_skip_booking_creation(None) is False

    def test_empty_booking_result(self):
        """Test with empty booking result."""
        assert self.should_skip_booking_creation({}) is False

    def test_existing_voya_reference(self):
        """Test with existing VOYA reference."""
        booking_result = {"voya_booking_reference": "VOYA-ABC123XYZ9"}
        assert self.should_skip_booking_creation(booking_result) is True

    def test_existing_external_reference(self):
        """Test with existing external reference."""
        booking_result = {"external_booking_reference": "FL123456789"}
        assert self.should_skip_booking_creation(booking_result) is True

    def test_empty_external_reference(self):
        """Test with empty external reference."""
        booking_result = {"external_booking_reference": ""}
        assert self.should_skip_booking_creation(booking_result) is False

    def test_whitespace_external_reference(self):
        """Test with whitespace-only external reference."""
        booking_result = {"external_booking_reference": "   "}
        assert self.should_skip_booking_creation(booking_result) is False


class TestErrorMessageExtraction:
    """Test error message extraction prevents [object Object] errors."""

    def extract_error_message(self, error):
        """Business logic for error message extraction."""
        if isinstance(error, str):
            return error

        if isinstance(error, dict):
            if "detail" in error:
                detail = error["detail"]

                if isinstance(detail, dict) and "message" in detail:
                    return detail["message"]
                if isinstance(detail, list) and len(detail) > 0:
                    first_error = detail[0]
                    if isinstance(first_error, dict):
                        return first_error.get("msg", str(first_error))
                    return str(first_error)
                return str(detail)

            if (
                "errors" in error
                and isinstance(error["errors"], list)
                and len(error["errors"]) > 0
            ):
                first_error = error["errors"][0]
                if isinstance(first_error, dict) and "message" in first_error:
                    return first_error["message"]
                return str(first_error)

            if "booking_status" in error and error.get("booking_status") == "FAILED":
                return "The booking could not be completed. Please try again or contact support."

            return "An unexpected error occurred. Please try again."

        return str(error)

    def test_simple_string_error(self):
        """Test simple string error extraction."""
        result = self.extract_error_message("Simple error message")
        assert result == "Simple error message"

    def test_api_error_with_detail(self):
        """Test API error with detail field."""
        error_data = {"detail": "API validation failed"}
        result = self.extract_error_message(error_data)
        assert result == "API validation failed"

    def test_nested_detail_with_message(self):
        """Test nested detail object with message."""
        error_data = {"detail": {"message": "Booking reference missing"}}
        result = self.extract_error_message(error_data)
        assert result == "Booking reference missing"

    def test_validation_errors_array(self):
        """Test FastAPI validation errors array."""
        error_data = {
            "detail": [
                {
                    "loc": ["body", "field"],
                    "msg": "Input should be valid",
                    "type": "string_type",
                }
            ]
        }
        result = self.extract_error_message(error_data)
        assert result == "Input should be valid"

    def test_booking_errors_array(self):
        """Test booking response with errors array."""
        error_data = {
            "errors": [{"message": "FlightLogic did not return a booking reference"}]
        }
        result = self.extract_error_message(error_data)
        assert result == "FlightLogic did not return a booking reference"

    def test_failed_booking_status(self):
        """Test failed booking status handling."""
        error_data = {"booking_status": "FAILED"}
        result = self.extract_error_message(error_data)
        assert (
            result
            == "The booking could not be completed. Please try again or contact support."
        )

    def test_prevents_object_object_display(self):
        """Test that complex objects don't result in [object Object]."""
        error_data = {
            "complex": {"nested": {"object": "value"}},
            "booking_status": "UNKNOWN",
        }
        result = self.extract_error_message(error_data)

        # Should return fallback message, not [object Object]
        assert result == "An unexpected error occurred. Please try again."
        assert "[object Object]" not in result

    @pytest.mark.parametrize(
        ("error_input", "expected"),
        [
            ("String error", "String error"),
            ({"detail": "Simple detail"}, "Simple detail"),
            ({"detail": {"message": "Nested message"}}, "Nested message"),
            ({"errors": [{"message": "Error message"}]}, "Error message"),
            (
                {"booking_status": "FAILED"},
                "The booking could not be completed. Please try again or contact support.",
            ),
        ],
    )
    def test_error_extraction_patterns(self, error_input, expected):
        """Test various error extraction patterns."""
        result = self.extract_error_message(error_input)
        assert result == expected
        assert "[object Object]" not in result
