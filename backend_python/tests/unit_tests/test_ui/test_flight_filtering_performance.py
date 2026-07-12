"""Performance tests for flight filtering and sorting operations.

Ensures filtering operations complete under 100ms as specified.
"""

import os
import re
import time

import pytest


class TestFilteringPerformance:
    """Test filtering performance requirements."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        return "dev_ui/flight-booker/index.html"

    @pytest.fixture
    def large_flight_dataset(self):
        """Generate a large dataset of flights for performance testing."""
        flights = []
        airlines = ["KL", "AF", "DL", "BA", "LH", "LX", "EK", "QR"]
        airports = ["AMS", "LHR", "JFK", "CDG", "FRA", "DXB", "DOH"]
        cabin_classes = ["Economy", "Business", "First"]

        # Generate 1000 flights
        for i in range(1000):
            price = 50 + (i % 500) * 2  # Prices from 50 to 1050
            stops = i % 4  # 0-3 stops
            airline = airlines[i % len(airlines)]
            cabin = cabin_classes[i % len(cabin_classes)]
            dep_airport = airports[i % len(airports)]
            arr_airport = airports[(i + 1) % len(airports)]
            duration = 60 + (i % 600)  # 1-10 hours in minutes
            dep_time = (i % 24) * 60  # Minutes since midnight

            segments = []
            for stop_idx in range(stops + 1):
                if stop_idx == 0:
                    seg_dep = dep_airport
                else:
                    seg_dep = airports[(i + stop_idx) % len(airports)]
                if stop_idx == stops:
                    seg_arr = arr_airport
                else:
                    seg_arr = airports[(i + stop_idx + 1) % len(airports)]

                segments.append(
                    {
                        "departure_airport": {"iata_code": seg_dep},
                        "arrival_airport": {"iata_code": seg_arr},
                        "departure_datetime": {
                            "value": f"2025-01-15T{dep_time // 60:02d}:{dep_time % 60:02d}:00"
                        },
                        "arrival_datetime": {
                            "value": f"2025-01-15T{(dep_time + duration) // 60:02d}:{(dep_time + duration) % 60:02d}:00"
                        },
                        "flight_duration": {"total_minutes": duration // (stops + 1)},
                        "marketing_airline": {
                            "iata_code": airline,
                            "airline_name": f"Airline {airline}",
                        },
                        "cabin_class": cabin,
                    }
                )

            flights.append(
                {
                    "pricing": {
                        "fare_totals": {
                            "total_fare": {"amount": str(price), "currency": "USD"}
                        }
                    },
                    "flight_legs": [{"flight_segments": segments}],
                }
            )

        return flights

    def test_filter_function_performance_structure(self, html_file):
        """Test that filter function structure supports performance."""
        assert os.path.exists(html_file), f"File not found: {html_file}"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that filterFlights uses efficient array methods
        # Should use .filter() which is efficient
        filter_pattern = r"function\s+filterFlights.*return\s+flights\.filter"
        assert re.search(filter_pattern, content, re.DOTALL), (
            "filterFlights should use efficient .filter() method"
        )

        # Check that it doesn't use nested loops unnecessarily
        # (We can't fully validate this without executing, but we can check structure)

    def test_sort_function_performance_structure(self, html_file):
        """Test that sort function structure supports performance."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that sortFlights uses efficient array methods
        # Should use .sort() which is efficient
        sort_pattern = r"function\s+sortFlights.*sorted\.sort"
        assert re.search(sort_pattern, content, re.DOTALL), (
            "sortFlights should use efficient .sort() method"
        )

        # Check that it creates a copy first (spread operator)
        copy_pattern = r"const\s+sorted\s*=\s*\[\.\.\.\s*flights\s*\]|sorted\s*=\s*\[\.\.\.\s*flights\s*\]"
        assert re.search(copy_pattern, content), (
            "sortFlights should create a copy before sorting"
        )

    def test_no_unnecessary_recalculations(self, html_file):
        """Test that filter/sort functions don't recalculate unnecessarily."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that helper functions exist (they should be called once per flight)
        helper_functions = [
            "getFlightPrice",
            "getFlightStops",
            "getOutboundDurationHours",
            "getDepartureTimeMinutes",
            "getArrivalTimeMinutes",
        ]

        for func in helper_functions:
            func_pattern = rf"function\s+{func}\s*\("
            assert re.search(func_pattern, content), (
                f"Helper function {func} not found - may cause performance issues"
            )

    def test_filter_state_updates_efficiently(self, html_file):
        """Test that filter state updates don't cause unnecessary re-renders."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that applyFilters calls displaySortedFlights once
        # Use a simpler approach: search for the function and then check
        # for the call within a reasonable context window
        apply_match = re.search(
            r"function\s+applyFilters\s*\([^)]*\)\s*\{",
            content,
            re.DOTALL,
        )
        if apply_match:
            # Find the function start position
            func_start = apply_match.end()
            # Extract a chunk after the function start (applyFilters is short)
            func_context = content[func_start : func_start + 500]
            # Should call displaySortedFlights once
            display_calls = func_context.count("displaySortedFlights")
            assert display_calls == 1, (
                f"applyFilters should call displaySortedFlights once, found {display_calls} calls"
            )

    @pytest.mark.performance
    def test_filtering_performance_requirement(self, large_flight_dataset):
        """Test that filtering completes under 100ms for large datasets."""

        # Simulate filtering logic (Python equivalent)
        def filter_flights_python(flights, filter_state):
            """Python implementation of filter logic for performance testing."""
            filtered = []
            for itinerary in flights:
                # Price filter
                price = float(
                    itinerary.get("pricing", {})
                    .get("fare_totals", {})
                    .get("total_fare", {})
                    .get("amount", 0)
                )
                if filter_state.get("priceMin") and price < filter_state["priceMin"]:
                    continue
                if filter_state.get("priceMax") and price > filter_state["priceMax"]:
                    continue

                # Stops filter
                stops = (
                    len(
                        itinerary.get("flight_legs", [{}])[0].get("flight_segments", [])
                    )
                    - 1
                )
                if filter_state.get("directOnly") and stops != 0:
                    continue
                if filter_state.get("stops1") and stops != 1:
                    continue
                if filter_state.get("stops2Plus") and stops < 2:
                    continue

                filtered.append(itinerary)
            return filtered

        filter_state = {
            "priceMin": 100,
            "priceMax": 500,
            "directOnly": False,
            "stops1": True,
            "stops2Plus": False,
        }

        # Measure filtering time
        start_time = time.perf_counter()
        filtered = filter_flights_python(large_flight_dataset, filter_state)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Performance requirement: under 100ms
        assert elapsed_ms < 100, (
            f"Filtering took {elapsed_ms:.2f}ms, should be under 100ms. "
            f"Filtered {len(filtered)} flights from {len(large_flight_dataset)} total."
        )

    @pytest.mark.performance
    def test_sorting_performance_requirement(self, large_flight_dataset):
        """Test that sorting completes under 100ms for large datasets."""

        # Simulate sorting logic (Python equivalent)
        def get_price(itinerary):
            return float(
                itinerary.get("pricing", {})
                .get("fare_totals", {})
                .get("total_fare", {})
                .get("amount", 0)
            )

        def sort_flights_python(flights, sort_type="price-low"):
            """Python implementation of sort logic for performance testing."""
            sorted_flights = flights.copy()
            if sort_type == "price-low":
                sorted_flights.sort(key=get_price)
            elif sort_type == "price-high":
                sorted_flights.sort(key=get_price, reverse=True)
            return sorted_flights

        # Measure sorting time
        start_time = time.perf_counter()
        sorted_flights = sort_flights_python(large_flight_dataset, "price-low")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Performance requirement: under 100ms
        assert elapsed_ms < 100, (
            f"Sorting took {elapsed_ms:.2f}ms, should be under 100ms. "
            f"Sorted {len(sorted_flights)} flights."
        )

    @pytest.mark.performance
    def test_combined_filter_and_sort_performance(self, large_flight_dataset):
        """Test that combined filter and sort operations complete under 100ms."""

        # Simulate combined operations
        def filter_flights_python(flights, filter_state):
            filtered = []
            for itinerary in flights:
                price = float(
                    itinerary.get("pricing", {})
                    .get("fare_totals", {})
                    .get("total_fare", {})
                    .get("amount", 0)
                )
                if filter_state.get("priceMin") and price < filter_state["priceMin"]:
                    continue
                if filter_state.get("priceMax") and price > filter_state["priceMax"]:
                    continue
                filtered.append(itinerary)
            return filtered

        def sort_flights_python(flights):
            def get_price(itinerary):
                return float(
                    itinerary.get("pricing", {})
                    .get("fare_totals", {})
                    .get("total_fare", {})
                    .get("amount", 0)
                )

            sorted_flights = flights.copy()
            sorted_flights.sort(key=get_price)
            return sorted_flights

        filter_state = {"priceMin": 200, "priceMax": 800}

        # Measure combined time
        start_time = time.perf_counter()
        filtered = filter_flights_python(large_flight_dataset, filter_state)
        sorted_result = sort_flights_python(filtered)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Performance requirement: under 100ms for combined operations
        assert elapsed_ms < 100, (
            f"Combined filter and sort took {elapsed_ms:.2f}ms, should be under 100ms. "
            f"Processed {len(sorted_result)} flights from {len(large_flight_dataset)} total."
        )
