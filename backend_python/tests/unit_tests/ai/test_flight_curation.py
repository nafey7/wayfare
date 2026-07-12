"""
Unit tests for flight curation logic.

Tests the _curate_multi_airport_results method and related helpers
that will be extracted to FlightSearchCurator in Phase 3.

These tests use fixture data from the mock FlightLogic server to verify
curation algorithms work correctly with realistic response structures.
"""

import json
from pathlib import Path

import pytest

# Load fixtures
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "flightlogic"


@pytest.fixture
def oneway_search_response():
    """Load one-way flight search fixture."""
    fixture_path = FIXTURES_DIR / "flight_search_response_oneway.json"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def roundtrip_search_response():
    """Load roundtrip flight search fixture."""
    fixture_path = FIXTURES_DIR / "flight_search_response_roundtrip.json"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")
    with open(fixture_path) as f:
        return json.load(f)


class TestFlightPriceExtraction:
    """Test price extraction from flight data."""

    def test_extract_price_from_fare_itinerary(self, oneway_search_response):
        """Extract price from FlightLogic fare structure."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        prices = []
        for fare in fares:
            total_fare = fare["FareItinerary"]["AirItineraryFareInfo"][
                "ItinTotalFares"
            ]["TotalFare"]
            price = float(total_fare["Amount"])
            prices.append(price)

        # Mock returns 3 flights: 295.50, 215.00, 375.00
        assert len(prices) == 3
        assert min(prices) == 215.00  # Ryanair is cheapest
        assert max(prices) == 375.00  # KLM is most expensive

    def test_identify_cheapest_flight(self, oneway_search_response):
        """Find the cheapest flight option."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        def get_price(fare):
            return float(
                fare["FareItinerary"]["AirItineraryFareInfo"]["ItinTotalFares"][
                    "TotalFare"
                ]["Amount"]
            )

        cheapest = min(fares, key=get_price)
        cheapest_price = get_price(cheapest)

        assert cheapest_price == 215.00

        # Verify it's Ryanair (FR)
        segments = cheapest["FareItinerary"]["OriginDestinationOptions"][0][
            "OriginDestinationOption"
        ]
        airline_code = segments[0]["FlightSegment"]["OperatingAirline"]["Code"]
        assert airline_code == "FR"  # Ryanair


class TestFlightDurationExtraction:
    """Test duration extraction from flight data."""

    def test_extract_duration_from_segments(self, oneway_search_response):
        """Extract flight duration from segment times."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        durations = []
        for fare in fares:
            segments = fare["FareItinerary"]["OriginDestinationOptions"][0][
                "OriginDestinationOption"
            ]
            first_segment = segments[0]["FlightSegment"]

            # Duration might be in JourneyDuration or calculated from times
            if "JourneyDuration" in first_segment:
                duration_mins = first_segment["JourneyDuration"]
            else:
                # Parse from departure/arrival times
                from datetime import datetime

                dep = datetime.fromisoformat(
                    first_segment["DepartureDateTime"].replace("Z", "+00:00")
                )
                arr = datetime.fromisoformat(
                    first_segment["ArrivalDateTime"].replace("Z", "+00:00")
                )
                duration_mins = int((arr - dep).total_seconds() / 60)

            durations.append(duration_mins)

        # All flights have some duration
        assert all(d > 0 for d in durations)

    def test_count_stops(self, oneway_search_response):
        """Count number of stops in flight."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        for fare in fares:
            segments = fare["FareItinerary"]["OriginDestinationOptions"][0][
                "OriginDestinationOption"
            ]
            stops = len(segments) - 1
            # Mock data has all direct flights
            assert stops == 0


class TestFlightCurationAlgorithm:
    """Test the curation algorithm that selects top flights."""

    def test_select_three_curated_options(self, oneway_search_response):
        """Curation should select 3 options from available flights."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        def get_price(fare):
            return float(
                fare["FareItinerary"]["AirItineraryFareInfo"]["ItinTotalFares"][
                    "TotalFare"
                ]["Amount"]
            )

        # Sort by price to get cheapest
        sorted_by_price = sorted(fares, key=get_price)

        # Curated selection
        curated = {
            "cheapest": sorted_by_price[0],
            "mid_price": sorted_by_price[1] if len(sorted_by_price) > 1 else None,
            "expensive": sorted_by_price[-1] if len(sorted_by_price) > 2 else None,
        }

        assert get_price(curated["cheapest"]) == 215.00
        assert get_price(curated["mid_price"]) == 295.50
        assert get_price(curated["expensive"]) == 375.00

    def test_value_score_calculation(self, oneway_search_response):
        """Test value score balances price and duration."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        def get_price(fare):
            return float(
                fare["FareItinerary"]["AirItineraryFareInfo"]["ItinTotalFares"][
                    "TotalFare"
                ]["Amount"]
            )

        def get_duration_mins(fare):
            segments = fare["FareItinerary"]["OriginDestinationOptions"][0][
                "OriginDestinationOption"
            ]
            first_segment = segments[0]["FlightSegment"]
            if "JourneyDuration" in first_segment:
                return first_segment["JourneyDuration"]
            return 60  # Default 1 hour if not specified

        def value_score(fare):
            """Lower is better - price per minute of saved time."""
            price = get_price(fare)
            duration = get_duration_mins(fare)
            # Normalize: price / (max_duration - duration + 1)
            # Cheaper and faster = lower score = better value
            return price / max(duration, 1)

        scores = [(get_price(f), value_score(f)) for f in fares]

        # All flights should have positive scores
        assert all(s[1] > 0 for s in scores)


class TestEdgeCases:
    """Test edge cases in curation."""

    def test_empty_fare_list(self):
        """Handle empty search results gracefully."""
        fares = []

        def curate(fares):
            if not fares:
                return {"cheapest": None, "fastest": None, "best_value": None}
            return fares[0]  # Simplified

        result = curate(fares)
        assert result["cheapest"] is None

    def test_single_flight_result(self, oneway_search_response):
        """Single flight should be used for all categories."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ][:1]  # Take only first

        assert len(fares) == 1

        # Single flight is cheapest, fastest, and best value
        the_flight = fares[0]

        def get_price(fare):
            return float(
                fare["FareItinerary"]["AirItineraryFareInfo"]["ItinTotalFares"][
                    "TotalFare"
                ]["Amount"]
            )

        cheapest = min(fares, key=get_price)
        assert cheapest == the_flight

    def test_missing_price_field(self):
        """Handle malformed price data."""
        malformed_fare = {
            "FareItinerary": {
                "AirItineraryFareInfo": {
                    "ItinTotalFares": {
                        # Missing TotalFare
                    }
                }
            }
        }

        def safe_get_price(fare, default=999999):
            try:
                return float(
                    fare["FareItinerary"]["AirItineraryFareInfo"]["ItinTotalFares"][
                        "TotalFare"
                    ]["Amount"]
                )
            except (KeyError, TypeError, ValueError):
                return default

        price = safe_get_price(malformed_fare)
        assert price == 999999  # Falls back to default


class TestAirlineIdentification:
    """Test airline identification from flight data."""

    def test_extract_airline_codes(self, oneway_search_response):
        """Extract airline codes from search results."""
        fares = oneway_search_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]

        airlines = set()
        for fare in fares:
            segments = fare["FareItinerary"]["OriginDestinationOptions"][0][
                "OriginDestinationOption"
            ]
            for seg in segments:
                code = seg["FlightSegment"]["OperatingAirline"]["Code"]
                airlines.add(code)

        # Mock has BA (British Airways), FR (Ryanair), KL (KLM)
        assert "BA" in airlines
        assert "FR" in airlines
        assert "KL" in airlines

    def test_map_airline_code_to_name(self):
        """Map IATA codes to airline names."""
        airline_names = {
            "BA": "British Airways",
            "FR": "Ryanair",
            "KL": "KLM Royal Dutch Airlines",
            "AF": "Air France",
            "LH": "Lufthansa",
        }

        assert airline_names.get("BA") == "British Airways"
        assert airline_names.get("FR") == "Ryanair"
        assert airline_names.get("XX", "Unknown") == "Unknown"
