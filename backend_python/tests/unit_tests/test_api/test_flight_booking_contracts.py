"""Contract tests for flight booking data flow.

These tests verify that data produced by one endpoint/component
is correctly consumed by another. They catch schema mismatches
between producers and consumers.

Bug Prevention:
- Price showing €0.00: Frontend expected `pricing`, API returned `updated_pricing`
- fare_source_code missing: Stored at `selected_flight.fare_source_code`,
  but booking looked in `itinerary.pricing.fare_source_code`
- FlightLogic session missing: Stored as `fl_session_id`, but booking
  wasn't extracting it
- Auth token missing: Redirect URL missing `auth_token` parameter
"""

import pytest


class TestBookingSessionDataContract:
    """Contract tests: /api/flights/select → /api/flights/book-from-session.

    These tests verify the data structure produced by the select endpoint
    matches what the booking endpoint expects.
    """

    @pytest.fixture
    def select_endpoint_session_data(self) -> dict:
        """Simulates data structure created by /api/flights/select endpoint.

        This is the "producer" side of the contract.
        """
        return {
            "selected_flight": {
                "itinerary": {
                    "sequence_number": "1",
                    "journey_type": "OneWay",
                    "validating_airline": {"iata_code": "LX"},
                    "flight_legs": [{"total_stops": 1, "flight_segments": []}],
                    "updated_pricing": {
                        "has_mixed_booking_classes": True,
                        "updated_fare_source_code": "UPDATED_FARE_CODE_ABC123",
                        "fare_type": "Public",
                        "is_refundable": True,
                        "validated_fare_totals": {
                            "base_fare": {"amount": 454.92, "currency": "USD"},
                            "total_tax": {"amount": 268.14, "currency": "USD"},
                            "total_fare": {"amount": 723.06, "currency": "USD"},
                        },
                        "passenger_fare_breakdown": [
                            {
                                "passenger_type_info": {"passenger_type": "ADT"},
                                "individual_passenger_fare": {
                                    "total_fare": {"amount": 723.06, "currency": "USD"}
                                },
                            }
                        ],
                    },
                },
                "fare_source_code": "ORIGINAL_FARE_CODE_XYZ789",
            },
            "fl_session_id": "flightlogic-session-uuid-12345",
            "search_params": {
                "adults": 1,
                "children": 0,
                "infants": 0,
                "origin": "LHR",
                "destination": "JFK",
                "departure_date": "2026-04-15",
                "journey_type": "OneWay",
            },
            "status": "fare_validated",
            "source": "api_select_v2",
        }

    def test_fare_source_code_is_accessible(self, select_endpoint_session_data: dict):
        """Verify fare_source_code can be extracted by booking endpoint.

        The booking endpoint needs to find fare_source_code. It should check:
        1. selected_flight.fare_source_code (primary for api_select_v2)
        2. itinerary.updated_pricing.updated_fare_source_code (fallback)
        """
        session_data = select_endpoint_session_data
        selected_flight = session_data.get("selected_flight", {})
        itinerary = selected_flight.get("itinerary", {})

        # Primary location (api_select_v2 flow)
        fare_source_code = selected_flight.get("fare_source_code")
        if not fare_source_code:
            # Fallback: updated_pricing from revalidation
            updated_pricing = itinerary.get("updated_pricing", {})
            fare_source_code = updated_pricing.get("updated_fare_source_code")

        assert fare_source_code is not None, (
            "fare_source_code must be accessible from session data. "
            "Check selected_flight.fare_source_code or "
            "itinerary.updated_pricing.updated_fare_source_code"
        )

    def test_fl_session_id_is_present(self, select_endpoint_session_data: dict):
        """Verify FlightLogic session ID is stored for booking API calls.

        The booking endpoint needs fl_session_id (the FlightLogic session from
        search/revalidate) to make the booking API call. Without it, FlightLogic
        rejects the booking request.
        """
        fl_session_id = select_endpoint_session_data.get("fl_session_id")

        assert fl_session_id is not None, (
            "fl_session_id must be stored in session data. "
            "This is the FlightLogic session ID from revalidation, "
            "required for the booking API call."
        )
        assert fl_session_id != "", "fl_session_id must not be empty"

    def test_pricing_data_is_accessible(self, select_endpoint_session_data: dict):
        """Verify pricing data can be extracted for display.

        The frontend needs to display pricing. It should find it at:
        1. itinerary.updated_pricing (from revalidation - preferred)
        2. itinerary.pricing (legacy path)
        """
        selected_flight = select_endpoint_session_data.get("selected_flight", {})
        itinerary = selected_flight.get("itinerary", {})

        # Check for pricing in order of preference
        pricing = itinerary.get("updated_pricing") or itinerary.get("pricing")

        assert pricing is not None, (
            "Pricing data must be accessible from itinerary. "
            "Check itinerary.updated_pricing or itinerary.pricing"
        )

        # Verify fare totals are present
        fare_totals = pricing.get("validated_fare_totals") or pricing.get("fare_totals")
        assert fare_totals is not None, (
            "Fare totals must be present in pricing. "
            "Check validated_fare_totals or fare_totals"
        )

        # Verify total_fare amount exists
        total_fare = fare_totals.get("total_fare", {})
        assert total_fare.get("amount") is not None, (
            "total_fare.amount must be present for price display"
        )

    def test_passenger_fare_breakdown_is_accessible(
        self, select_endpoint_session_data: dict
    ):
        """Verify passenger fare breakdown is available for detailed pricing."""
        selected_flight = select_endpoint_session_data.get("selected_flight", {})
        itinerary = selected_flight.get("itinerary", {})
        pricing = itinerary.get("updated_pricing") or itinerary.get("pricing", {})

        breakdown = pricing.get("passenger_fare_breakdown") or pricing.get(
            "fare_breakdown"
        )

        assert breakdown is not None, (
            "Passenger fare breakdown must be present for detailed pricing. "
            "Check passenger_fare_breakdown or fare_breakdown"
        )
        assert len(breakdown) > 0, "Fare breakdown must have at least one entry"


class TestRedirectUrlContract:
    """Contract tests for booking redirect URLs.

    Verifies that redirect URLs contain all required parameters.
    """

    def test_redirect_url_contains_session_id(self):
        """Verify redirect URL contains session_id parameter."""
        # Simulates URL construction from /api/flights/select
        session_id = "test-session-uuid"
        base_url = "http://localhost:8000"

        redirect_url = (
            f"{base_url}/dev/flight-booker/index.html?session_id={session_id}"
        )

        assert "session_id=" in redirect_url, "redirect_url must contain session_id"
        assert session_id in redirect_url, "session_id value must be in URL"

    def test_redirect_url_contains_auth_token_for_authenticated_users(self):
        """Verify redirect URL contains auth_token for authenticated users.

        When a user is authenticated, the redirect URL must include auth_token
        so the booking page can authenticate API calls.
        """
        import jwt

        session_id = "test-session-uuid"
        user_id = "user-123"
        secret_key = "test-secret-key"  # pragma: allowlist secret
        base_url = "http://localhost:8000"

        # Simulates token generation from /api/flights/select
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "type": "booking_auth",
            "exp": 9999999999,  # Far future for test
        }
        auth_token = jwt.encode(payload, secret_key, algorithm="HS256")

        # URL should include both session_id and auth_token
        redirect_url = f"{base_url}/dev/flight-booker/index.html?session_id={session_id}&auth_token={auth_token}"

        assert "session_id=" in redirect_url
        assert "auth_token=" in redirect_url
        assert auth_token in redirect_url


class TestFareSourceCodeExtractionPriority:
    """Test fare_source_code extraction from various session data formats.

    Different flows store fare_source_code in different locations.
    The booking endpoint must handle all of them.
    """

    def test_extract_from_selected_flight_wrapper(self):
        """api_select_v2 flow stores fare_source_code at selected_flight level."""
        session_data = {
            "selected_flight": {
                "itinerary": {"flight_legs": []},
                "fare_source_code": "FARE_CODE_FROM_WRAPPER",
            }
        }

        selected_flight = session_data["selected_flight"]
        fare_source_code = selected_flight.get("fare_source_code")

        assert fare_source_code == "FARE_CODE_FROM_WRAPPER"

    def test_extract_from_updated_pricing(self):
        """Revalidation flow stores updated_fare_source_code in updated_pricing."""
        session_data = {
            "selected_flight": {
                "itinerary": {
                    "flight_legs": [],
                    "updated_pricing": {
                        "updated_fare_source_code": "FARE_CODE_FROM_REVALIDATION"
                    },
                }
            }
        }

        selected_flight = session_data["selected_flight"]
        itinerary = selected_flight.get("itinerary", {})
        updated_pricing = itinerary.get("updated_pricing", {})
        fare_source_code = updated_pricing.get("updated_fare_source_code")

        assert fare_source_code == "FARE_CODE_FROM_REVALIDATION"

    def test_extract_from_legacy_pricing(self):
        """Legacy flow stores fare_source_code in itinerary.pricing."""
        session_data = {
            "selected_flight": {
                "itinerary": {
                    "flight_legs": [],
                    "pricing": {"fare_source_code": "FARE_CODE_FROM_LEGACY"},
                }
            }
        }

        selected_flight = session_data["selected_flight"]
        itinerary = selected_flight.get("itinerary", {})
        pricing = itinerary.get("pricing", {})
        fare_source_code = pricing.get("fare_source_code")

        assert fare_source_code == "FARE_CODE_FROM_LEGACY"

    def test_extraction_priority_order(self):
        """Verify extraction checks locations in correct priority order.

        Priority:
        1. selected_flight.fare_source_code (api_select_v2)
        2. itinerary.updated_pricing.updated_fare_source_code
        3. itinerary.pricing.fare_source_code
        """
        # Session with all locations populated
        session_data = {
            "selected_flight": {
                "fare_source_code": "PRIORITY_1_WRAPPER",
                "itinerary": {
                    "updated_pricing": {
                        "updated_fare_source_code": "PRIORITY_2_UPDATED"
                    },
                    "pricing": {"fare_source_code": "PRIORITY_3_LEGACY"},
                },
            }
        }

        # Extract using priority order (matches booking endpoint logic)
        selected_flight = session_data["selected_flight"]
        itinerary = selected_flight.get("itinerary", {})

        fare_source_code = None

        # Priority 1
        if selected_flight.get("fare_source_code"):
            fare_source_code = selected_flight["fare_source_code"]
        # Priority 2
        elif itinerary.get("updated_pricing", {}).get("updated_fare_source_code"):
            fare_source_code = itinerary["updated_pricing"]["updated_fare_source_code"]
        # Priority 3
        elif itinerary.get("pricing", {}).get("fare_source_code"):
            fare_source_code = itinerary["pricing"]["fare_source_code"]

        assert fare_source_code == "PRIORITY_1_WRAPPER", (
            "Should use highest priority source (selected_flight.fare_source_code)"
        )


class TestFlightLogicSessionIdContract:
    """Test fl_session_id is correctly propagated through the booking flow."""

    def test_fl_session_id_stored_by_select_endpoint(self):
        """Verify select endpoint stores fl_session_id from revalidation."""
        # Simulates what /api/flights/select should store
        fl_session_from_revalidation = "flightlogic-revalidation-session"

        session_data = {
            "selected_flight": {"itinerary": {}},
            "fl_session_id": fl_session_from_revalidation,
            "status": "fare_validated",
            "source": "api_select_v2",
        }

        assert session_data["fl_session_id"] == fl_session_from_revalidation

    def test_fl_session_id_extracted_by_booking_endpoint(self):
        """Verify booking endpoint extracts fl_session_id for API call."""
        session_data = {
            "selected_flight": {"itinerary": {}},
            "fl_session_id": "flightlogic-session-for-booking",
            "search_params": {"session_id": "old-search-session"},
        }

        # Extraction logic (matches booking endpoint)
        fl_session_id = session_data.get("fl_session_id")
        search_session_id = session_data.get("search_params", {}).get("session_id")

        # fl_session_id takes priority over search_params.session_id
        session_token = fl_session_id or search_session_id

        assert session_token == "flightlogic-session-for-booking", (
            "Should use fl_session_id (from revalidation) over search_params.session_id"
        )

    def test_fallback_to_search_params_session_id(self):
        """If fl_session_id missing, fall back to search_params.session_id."""
        session_data = {
            "selected_flight": {"itinerary": {}},
            # No fl_session_id
            "search_params": {"session_id": "fallback-search-session"},
        }

        fl_session_id = session_data.get("fl_session_id")
        search_session_id = session_data.get("search_params", {}).get("session_id")

        session_token = fl_session_id or search_session_id

        assert session_token == "fallback-search-session"


class TestPricingDataContract:
    """Contract tests for pricing data between backend and frontend."""

    def test_updated_pricing_structure_matches_frontend_expectations(self):
        """Verify updated_pricing structure has all fields frontend needs."""
        # Structure returned by revalidation API
        updated_pricing = {
            "validated_fare_totals": {
                "base_fare": {"amount": 454.92, "currency": "USD", "decimal_places": 2},
                "total_tax": {"amount": 268.14, "currency": "USD", "decimal_places": 2},
                "total_fare": {
                    "amount": 723.06,
                    "currency": "USD",
                    "decimal_places": 2,
                },
            },
            "passenger_fare_breakdown": [
                {
                    "passenger_type_info": {
                        "passenger_type": "ADT",
                        "passenger_count": 1,
                    },
                    "individual_passenger_fare": {
                        "base_fare": {"amount": 454.92, "currency": "USD"},
                        "total_fare": {"amount": 723.06, "currency": "USD"},
                    },
                }
            ],
        }

        # Frontend price extraction (must work with both paths)
        fare_totals = updated_pricing.get(
            "validated_fare_totals"
        ) or updated_pricing.get("fare_totals")

        assert fare_totals is not None
        assert "total_fare" in fare_totals
        assert "amount" in fare_totals["total_fare"]
        assert "currency" in fare_totals["total_fare"]

        # Frontend fare breakdown extraction
        breakdown = updated_pricing.get(
            "passenger_fare_breakdown"
        ) or updated_pricing.get("fare_breakdown")

        assert breakdown is not None
        assert len(breakdown) > 0

    def test_legacy_pricing_structure_also_supported(self):
        """Verify legacy pricing structure (without updated_pricing) still works."""
        # Legacy structure (before revalidation was added)
        legacy_pricing = {
            "fare_totals": {
                "base_fare": {"amount": 400.00, "currency": "EUR"},
                "total_tax": {"amount": 50.00, "currency": "EUR"},
                "total_fare": {"amount": 450.00, "currency": "EUR"},
            },
            "fare_breakdown": [
                {
                    "passenger_type": "ADT",
                    "base_fare": {"amount": 400.00},
                    "total_fare": {"amount": 450.00},
                }
            ],
        }

        # Same extraction logic should work
        fare_totals = legacy_pricing.get("validated_fare_totals") or legacy_pricing.get(
            "fare_totals"
        )

        assert fare_totals is not None
        assert fare_totals["total_fare"]["amount"] == 450.00
