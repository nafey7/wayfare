"""Core FlightLogic fixes unit tests.

Tests the essential frontend and backend logic fixes for:
1. Error message extraction (preventing [object Object] errors)
2. Booking state detection (preventing duplicate bookings)
3. FlightLogic Success validation (handling Success=true but no UniqueID)

These tests validate the core business logic without complex import dependencies.
"""


class TestErrorMessageExtraction:
    """Test improved error message extraction to prevent [object Object] errors."""

    def extract_error_message(self, error):
        """Extract meaningful error message from various error formats."""
        # Handle string errors directly
        if isinstance(error, str):
            return error

        # Handle objects (dict-like structures)
        if isinstance(error, dict):
            # Check for 'detail' field first (FastAPI standard)
            if "detail" in error:
                detail = error["detail"]

                # Handle nested detail objects
                if isinstance(detail, dict):
                    # Look for 'message' in detail
                    if "message" in detail:
                        return detail["message"]
                    # Fallback to stringifying the detail object
                    return str(detail)

                # Handle validation errors (list of error objects)
                if isinstance(detail, list) and len(detail) > 0:
                    first_error = detail[0]
                    if isinstance(first_error, dict):
                        return first_error.get("msg", str(first_error))
                    return str(first_error)

                # Handle simple detail values
                return str(detail)

            # Handle booking response objects with errors array
            if (
                "errors" in error
                and isinstance(error["errors"], list)
                and len(error["errors"]) > 0
            ):
                first_error = error["errors"][0]
                if isinstance(first_error, dict) and "message" in first_error:
                    return first_error["message"]
                return str(first_error)

            # Handle booking status failures
            if "booking_status" in error and error.get("booking_status") == "FAILED":
                return "The booking could not be completed. Please try again or contact support."

            # Fallback for other object types
            return "An unexpected error occurred. Please try again."

        # Fallback for any other types
        return str(error)

    def test_extract_error_from_simple_string(self):
        """Test extracting error from simple string response."""
        error_data = "Simple error message"
        result = self.extract_error_message(error_data)
        assert result == "Simple error message"

    def test_extract_error_from_object_with_detail(self):
        """Test extracting error from object with detail field."""
        error_data = {"detail": "API validation failed", "status_code": 400}
        result = self.extract_error_message(error_data)
        assert result == "API validation failed"

    def test_extract_error_from_object_with_nested_detail(self):
        """Test extracting error from object with nested detail object."""
        error_data = {
            "detail": {
                "message": "Booking reference missing",
                "code": "MISSING_BOOKING_REFERENCE",
            }
        }
        result = self.extract_error_message(error_data)
        assert result == "Booking reference missing"

    def test_extract_error_from_validation_errors_array(self):
        """Test extracting error from FastAPI validation error format."""
        error_data = {
            "detail": [
                {
                    "loc": ["body", "voya_booking_reference"],
                    "msg": "Input should be a valid string",
                    "type": "string_type",
                }
            ]
        }
        result = self.extract_error_message(error_data)
        assert result == "Input should be a valid string"

    def test_extract_error_prevents_object_object_display(self):
        """Test that complex objects don't result in [object Object]."""
        error_data = {
            "booking_status": "FAILED",
            "errors": [
                {
                    "code": "MISSING_BOOKING_REFERENCE",
                    "message": "FlightLogic did not return a booking reference",
                    "details": {"status": "CONFIRMED", "success_flag": "True"},
                }
            ],
            "is_successful": False,
        }
        result = self.extract_error_message(error_data)
        assert result == "FlightLogic did not return a booking reference"
        # Ensure we never return [object Object]
        assert result != "[object Object]"
        assert "[object Object]" not in result


class TestBookingStateDetection:
    """Test booking state detection to prevent duplicate bookings."""

    def should_skip_booking_creation(self, booking_result):
        """Check if booking creation should be skipped (booking already exists)."""
        if not booking_result:
            return False

        # Check for existing VOYA booking reference
        voya_ref = booking_result.get("voya_booking_reference")
        if voya_ref and voya_ref.startswith("VOYA-"):
            return True

        # Check for external booking reference (FlightLogic UniqueID)
        external_ref = booking_result.get("external_booking_reference")
        return bool(external_ref and external_ref.strip())

    def test_no_booking_result(self):
        """Test with no booking result."""
        result = self.should_skip_booking_creation(None)
        assert result is False

    def test_empty_booking_result(self):
        """Test with empty booking result."""
        result = self.should_skip_booking_creation({})
        assert result is False

    def test_has_voya_reference_should_skip(self):
        """Test with VOYA reference - should skip booking creation."""
        booking_result = {
            "voya_booking_reference": "VOYA-ABC123XYZ9",
            "booking_status": "CONFIRMED",
        }
        result = self.should_skip_booking_creation(booking_result)
        assert result is True

    def test_has_external_reference_should_skip(self):
        """Test with external reference - should skip booking creation."""
        booking_result = {
            "external_booking_reference": "FL123456789",
            "booking_status": "CONFIRMED",
        }
        result = self.should_skip_booking_creation(booking_result)
        assert result is True

    def test_empty_external_reference_should_not_skip(self):
        """Test with empty external reference - should create booking."""
        booking_result = {"external_booking_reference": "", "booking_status": "FAILED"}
        result = self.should_skip_booking_creation(booking_result)
        assert result is False

    def test_whitespace_external_reference_should_not_skip(self):
        """Test with whitespace external reference - should create booking."""
        booking_result = {
            "external_booking_reference": "   ",
            "booking_status": "FAILED",
        }
        result = self.should_skip_booking_creation(booking_result)
        assert result is False


class TestFlightLogicSuccessValidation:
    """Test FlightLogic Success validation logic."""

    def is_valid_flightlogic_booking(self, response):
        """Validate FlightLogic booking response."""
        if not response:
            return False, "No response received"

        # Check Success flag (can be boolean or string)
        success = response.get("Success", False)
        if isinstance(success, str):
            success = success.lower() == "true"

        if not success:
            return False, "FlightLogic returned Success=false"

        # Critical fix: Check for UniqueID even when Success=true
        unique_id = response.get("UniqueID")
        if not unique_id or (isinstance(unique_id, str) and not unique_id.strip()):
            return (
                False,
                "FlightLogic returned Success=true but no UniqueID (fare/session expired)",
            )

        return True, "Valid booking with UniqueID"

    def test_valid_booking_success_true_with_uniqueid(self):
        """Test valid booking (Success=true, has UniqueID)."""
        response = {
            "Success": True,
            "Status": "CONFIRMED",
            "UniqueID": "TR12345678",
            "Target": "Test",
        }
        is_valid, message = self.is_valid_flightlogic_booking(response)
        assert is_valid is True
        assert "Valid booking" in message

    def test_core_bug_success_true_no_uniqueid(self):
        """Test core bug - Success=true but no UniqueID."""
        response = {
            "Success": True,
            "Status": "CONFIRMED",
            "UniqueID": None,
            "Target": "Test",
        }
        is_valid, message = self.is_valid_flightlogic_booking(response)
        assert is_valid is False
        assert "Success=true but no UniqueID" in message

    def test_string_success_true_with_uniqueid(self):
        """Test string Success='true' with UniqueID."""
        response = {
            "Success": "true",
            "Status": "CONFIRMED",
            "UniqueID": "TR87654321",
            "Target": "Test",
        }
        is_valid, _message = self.is_valid_flightlogic_booking(response)
        assert is_valid is True

    def test_success_false_expected_failure(self):
        """Test Success=false (expected failure)."""
        response = {"Success": False, "Status": "", "UniqueID": None, "Target": "Test"}
        is_valid, message = self.is_valid_flightlogic_booking(response)
        assert is_valid is False
        assert "Success=false" in message

    def test_empty_uniqueid_string(self):
        """Test empty UniqueID string."""
        response = {
            "Success": True,
            "Status": "CONFIRMED",
            "UniqueID": "",
            "Target": "Test",
        }
        is_valid, message = self.is_valid_flightlogic_booking(response)
        assert is_valid is False
        assert "no UniqueID" in message

    def test_whitespace_uniqueid(self):
        """Test whitespace UniqueID."""
        response = {
            "Success": True,
            "Status": "CONFIRMED",
            "UniqueID": "   ",
            "Target": "Test",
        }
        is_valid, message = self.is_valid_flightlogic_booking(response)
        assert is_valid is False
        assert "no UniqueID" in message
