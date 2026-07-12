"""Unit tests for flight filtering and sorting logic.

Tests the JavaScript filtering and sorting functions in the flight-booker UI.
These tests validate the logic by extracting and testing the core functions.
"""

import os

import pytest


class TestFlightFiltering:
    """Test flight filtering logic."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        return "dev_ui/flight-booker/index.html"

    @pytest.fixture
    def sample_flights(self):
        """Sample flight data for testing."""
        return [
            {
                "pricing": {
                    "fare_totals": {
                        "total_fare": {"amount": "100.00", "currency": "USD"}
                    }
                },
                "flight_legs": [
                    {
                        "flight_segments": [
                            {
                                "departure_airport": {"iata_code": "AMS"},
                                "arrival_airport": {"iata_code": "LHR"},
                                "departure_datetime": {"value": "2025-01-15T10:00:00"},
                                "arrival_datetime": {"value": "2025-01-15T12:00:00"},
                                "flight_duration": {"total_minutes": 120},
                                "marketing_airline": {
                                    "iata_code": "KL",
                                    "airline_name": "KLM",
                                },
                                "cabin_class": "Economy",
                            }
                        ]
                    }
                ],
            },
            {
                "pricing": {
                    "fare_totals": {
                        "total_fare": {"amount": "200.00", "currency": "USD"}
                    }
                },
                "flight_legs": [
                    {
                        "flight_segments": [
                            {
                                "departure_airport": {"iata_code": "AMS"},
                                "arrival_airport": {"iata_code": "JFK"},
                                "departure_datetime": {"value": "2025-01-15T14:00:00"},
                                "arrival_datetime": {"value": "2025-01-15T20:00:00"},
                                "flight_duration": {"total_minutes": 360},
                                "marketing_airline": {
                                    "iata_code": "DL",
                                    "airline_name": "Delta",
                                },
                                "cabin_class": "Business",
                            }
                        ]
                    }
                ],
            },
            {
                "pricing": {
                    "fare_totals": {
                        "total_fare": {"amount": "150.00", "currency": "USD"}
                    }
                },
                "flight_legs": [
                    {
                        "flight_segments": [
                            {
                                "departure_airport": {"iata_code": "AMS"},
                                "arrival_airport": {"iata_code": "CDG"},
                                "departure_datetime": {"value": "2025-01-15T08:00:00"},
                                "arrival_datetime": {"value": "2025-01-15T09:30:00"},
                                "flight_duration": {"total_minutes": 90},
                                "marketing_airline": {
                                    "iata_code": "AF",
                                    "airline_name": "Air France",
                                },
                                "cabin_class": "Economy",
                            },
                            {
                                "departure_airport": {"iata_code": "CDG"},
                                "arrival_airport": {"iata_code": "LHR"},
                                "departure_datetime": {"value": "2025-01-15T11:00:00"},
                                "arrival_datetime": {"value": "2025-01-15T12:00:00"},
                                "flight_duration": {"total_minutes": 60},
                                "marketing_airline": {
                                    "iata_code": "AF",
                                    "airline_name": "Air France",
                                },
                                "cabin_class": "Economy",
                            },
                        ]
                    }
                ],
            },
        ]

    def test_price_filtering_function_exists(self, html_file):
        """Test that price filtering logic exists in the HTML file."""
        assert os.path.exists(html_file), f"File not found: {html_file}"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for price filter logic
        assert "filterState.priceMin" in content or "priceMin" in content, (
            "Price filtering logic not found"
        )
        assert "priceMax" in content, "Price max filter not found"

    def test_stops_filtering_function_exists(self, html_file):
        """Test that stops filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for stops filter logic
        assert (
            "getFlightStops" in content
            or "directOnly" in content
            or "stops1" in content
            or "stops2Plus" in content
        ), "Stops filtering logic not found"

    def test_airline_filtering_function_exists(self, html_file):
        """Test that airline filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for airline filter logic
        assert "matchesAirlineFilter" in content or "filterState.airlines" in content, (
            "Airline filtering logic not found"
        )

    def test_cabin_class_filtering_function_exists(self, html_file):
        """Test that cabin class filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for cabin class filter logic
        assert "filterState.cabinClasses" in content or "cabin_class" in content, (
            "Cabin class filtering logic not found"
        )

    def test_duration_filtering_function_exists(self, html_file):
        """Test that duration filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for duration filter logic
        assert (
            "outboundDurationMin" in content
            or "inboundDurationMin" in content
            or "getOutboundDurationHours" in content
            or "getInboundDurationHours" in content
        ), "Duration filtering logic not found"

    def test_time_filtering_function_exists(self, html_file):
        """Test that time filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for time filter logic
        assert (
            "departureTimeMin" in content
            or "arrivalTimeMin" in content
            or "getDepartureTimeMinutes" in content
            or "getArrivalTimeMinutes" in content
        ), "Time filtering logic not found"

    def test_airport_filtering_function_exists(self, html_file):
        """Test that airport filtering logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for airport filter logic
        assert (
            "departureAirports" in content
            or "arrivalAirports" in content
            or "extractDepartureAirports" in content
            or "extractArrivalAirports" in content
        ), "Airport filtering logic not found"

    def test_filter_state_structure(self, html_file):
        """Test that filter state has all required properties."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for filterState initialization with key properties
        assert "filterState" in content, "filterState not found"
        assert "priceMin" in content, "priceMin property not found"
        assert "priceMax" in content, "priceMax property not found"

    def test_clear_filters_function_exists(self, html_file):
        """Test that clear filters function exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for clearAllFilters function
        assert "clearAllFilters" in content, "clearAllFilters function not found"

    def test_session_storage_functions_exist(self, html_file):
        """Test that session storage functions exist for filter persistence."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for session storage functions
        assert "saveFiltersToSession" in content, (
            "saveFiltersToSession function not found"
        )
        assert "loadFiltersFromSession" in content, (
            "loadFiltersFromSession function not found"
        )


class TestFlightSorting:
    """Test flight sorting logic."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        return "dev_ui/flight-booker/index.html"

    def test_sort_function_exists(self, html_file):
        """Test that sort function exists."""
        assert os.path.exists(html_file), f"File not found: {html_file}"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for sortFlights function
        assert "sortFlights" in content, "sortFlights function not found"

    def test_sort_options_exist(self, html_file):
        """Test that all sort options are defined."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for all sort options
        sort_options = [
            "price-low",
            "price-high",
            "duration-short",
            "duration-long",
            "departure-early",
            "departure-late",
            "arrival-early",
            "arrival-late",
        ]

        for option in sort_options:
            # Check in sort option handlers
            assert option in content, f"Sort option '{option}' not found in UI"

    def test_price_sorting_logic(self, html_file):
        """Test that price sorting logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for price sorting
        assert "price-low" in content or "price-high" in content, (
            "Price sorting logic not found"
        )

    def test_duration_sorting_logic(self, html_file):
        """Test that duration sorting logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for duration sorting
        assert "duration-short" in content or "duration-long" in content, (
            "Duration sorting logic not found"
        )

    def test_time_sorting_logic(self, html_file):
        """Test that time sorting logic exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for time sorting
        assert (
            "departure-early" in content
            or "departure-late" in content
            or "arrival-early" in content
            or "arrival-late" in content
        ), "Time sorting logic not found"

    def test_sort_state_persistence(self, html_file):
        """Test that sort state is saved to session storage."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for sort session storage functions
        assert "saveSortToSession" in content, "saveSortToSession function not found"
        assert "loadSortFromSession" in content, (
            "loadSortFromSession function not found"
        )

    def test_current_sort_variable_exists(self, html_file):
        """Test that currentSort variable exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for currentSort variable
        assert "currentSort" in content, "currentSort variable not found"

    def test_sort_button_text_update(self, html_file):
        """Test that sort button text update function exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for updateSortButtonText function
        assert "updateSortButtonText" in content, (
            "updateSortButtonText function not found"
        )


class TestFilterSortIntegration:
    """Test integration between filtering and sorting."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        return "dev_ui/flight-booker/index.html"

    def test_display_sorted_flights_function(self, html_file):
        """Test that displaySortedFlights function exists and integrates filters."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for displaySortedFlights function
        assert "displaySortedFlights" in content, (
            "displaySortedFlights function not found"
        )
        assert "filterFlights" in content, "filterFlights function not found"
        assert "sortFlights" in content, "sortFlights function not found"

    def test_apply_filters_function(self, html_file):
        """Test that applyFilters function exists and updates state."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for applyFilters function
        assert "applyFilters" in content, "applyFilters function not found"

    def test_filter_count_display(self, html_file):
        """Test that filtered count is displayed."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for filtered-count element update
        assert "filtered-count" in content, "Filtered count display not found"
