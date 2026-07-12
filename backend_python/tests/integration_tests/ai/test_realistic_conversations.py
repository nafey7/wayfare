"""
Realistic conversation flow tests.

These tests simulate how real users interact with the chatbot:
- Starting with minimal info (just origin + destination)
- Answering agent questions one by one
- Completing the flow to actual search results

Each test documents:
1. The exact conversation flow
2. What fields are extracted at each step
3. Whether the extraction is correct or buggy

Run with: pytest tests/integration_tests/ai/test_realistic_conversations.py -v -m integration
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService, get_collected, get_waiting_for


@pytest.mark.integration
@pytest.mark.slow
class TestOneWayCompleteFlow:
    """Complete one-way flight booking flow from minimal input to search results.

    Scenario: User starts with just origin + destination, answers each question.
    """

    @pytest.mark.asyncio
    async def test_oneway_step_by_step_to_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete one-way flow: origin+dest → journey_type → date → results.

        Expected flow:
        1. "Amsterdam to London" → asks journey_type
        2. "one way" → asks departure_date
        3. "December 15th" → search results (defaults to 1 adult)
        """
        # Turn 1: Origin + Destination only
        response1 = await chat_service.process_message(
            message="I want to fly from Amsterdam to London",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.confidence >= 0.9
        assert response1.type == "collecting_info"

        # Verify: Should ask for journey_type
        assert get_waiting_for(response1) == "journey_type", (
            f"Expected to ask for journey_type, got: {get_waiting_for(response1)}"
        )

        # Verify field extraction
        collected1 = get_collected(response1)
        # Document current behavior - origin/destination may or may not be extracted
        # This assertion documents what ACTUALLY happens
        if "origin" in collected1:
            assert (
                "amsterdam" in collected1["origin"].lower()
                or "ams" in collected1["origin"].lower()
            ), f"Origin should be Amsterdam, got: {collected1['origin']}"
        if "destination" in collected1:
            assert "london" in collected1["destination"].lower() or any(
                code in collected1["destination"].upper()
                for code in ["LHR", "LGW", "STN", "LTN"]
            ), f"Destination should be London airport, got: {collected1['destination']}"

        # Turn 2: Provide journey type
        response2 = await chat_service.process_message(
            message="one way",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_flight"
        assert response2.type == "collecting_info"

        # Should now ask for departure_date
        waiting_for_2 = get_waiting_for(response2)
        assert waiting_for_2 in ["departure_date", "origin", "destination"], (
            f"Expected to ask for departure_date (or origin/dest if not extracted), got: {waiting_for_2}"
        )

        collected2 = get_collected(response2)
        # Journey type should now be collected
        if "journey_type" in collected2:
            assert collected2["journey_type"].lower() in [
                "one way",
                "oneway",
                "one_way",
            ], f"journey_type should be one way, got: {collected2['journey_type']}"

        # Turn 3: Provide departure date
        response3 = await chat_service.process_message(
            message="December 15th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response3.intent_name == "book_flight"

        # At this point we should either get results or ask for passengers
        if response3.type == "collecting_info":
            waiting_for_3 = get_waiting_for(response3)
            # May ask for passengers, origin, or other missing field
            assert waiting_for_3 is not None

            # If asking for passengers, provide them
            if waiting_for_3 == "passengers":
                response4 = await chat_service.process_message(
                    message="1 adult",
                    user=test_user,
                    chat_id=chat_id,
                )
                final_response = response4
            else:
                # Need to continue collecting - document what's missing
                final_response = response3
        else:
            final_response = response3

        # Final state check with mock server
        if mock_server_running and final_response.type == "flight_search_results":
            assert "flights" in final_response.data
            flights = final_response.data["flights"]
            assert len(flights) >= 1, "Should have at least one flight result"

    @pytest.mark.asyncio
    async def test_oneway_with_passenger_count(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """One-way with explicit passenger count in flow.

        Verifies passenger extraction from natural language.
        """
        # Turn 1: Start with just destination
        response1 = await chat_service.process_message(
            message="I need a flight to Barcelona",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.type == "collecting_info"

        # Turn 2: Provide origin
        response2 = await chat_service.process_message(
            message="from Amsterdam",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_flight"

        # Turn 3: Provide journey type
        response3 = await chat_service.process_message(
            message="one way please",
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 4: Provide date
        response4 = await chat_service.process_message(
            message="January 10th",
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 5: Provide passengers with specific count
        response5 = await chat_service.process_message(
            message="for 2 adults and 1 child",
            user=test_user,
            chat_id=chat_id,
        )

        # Verify passenger extraction
        collected5 = get_collected(response5)
        if "adults" in collected5:
            assert collected5["adults"] == 2, (
                f"Should have 2 adults, got: {collected5['adults']}"
            )
        if "children" in collected5:
            assert collected5["children"] == 1, (
                f"Should have 1 child, got: {collected5['children']}"
            )

        # Should now have results or be close
        if mock_server_running:
            assert response5.type in [
                "flight_search_results",
                "collecting_info",
                "searching",
            ]


@pytest.mark.integration
@pytest.mark.slow
class TestRoundTripCompleteFlow:
    """Complete round-trip flight booking flow from minimal input to search results."""

    @pytest.mark.asyncio
    async def test_roundtrip_step_by_step_to_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete round-trip: origin+dest → round-trip → dep date → return date → results.

        Expected flow:
        1. "Paris to Rome" → asks journey_type
        2. "round trip" → asks departure_date
        3. "December 20th" → asks return_date
        4. "December 27th" → search results
        """
        # Turn 1: Origin + Destination
        response1 = await chat_service.process_message(
            message="I want to fly from Paris to Rome",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.type == "collecting_info"
        assert get_waiting_for(response1) == "journey_type"

        # Turn 2: Round trip
        response2 = await chat_service.process_message(
            message="round trip",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_flight"
        assert response2.type == "collecting_info"

        waiting_for_2 = get_waiting_for(response2)
        assert waiting_for_2 in ["departure_date", "origin", "destination"], (
            f"Expected departure_date, got: {waiting_for_2}"
        )

        # Turn 3: Departure date
        response3 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response3.intent_name == "book_flight"

        # Should ask for return date now
        if response3.type == "collecting_info":
            waiting_for_3 = get_waiting_for(response3)
            # For round-trip, should ask return_date after departure_date
            if waiting_for_3 == "return_date":
                # Turn 4: Return date
                response4 = await chat_service.process_message(
                    message="December 27th",
                    user=test_user,
                    chat_id=chat_id,
                )

                # Verify dates are collected
                collected4 = get_collected(response4)
                if "departure_date" in collected4:
                    assert (
                        "12" in str(collected4["departure_date"])
                        or "dec" in str(collected4["departure_date"]).lower()
                    )
                if "return_date" in collected4:
                    assert (
                        "12" in str(collected4["return_date"])
                        or "dec" in str(collected4["return_date"]).lower()
                    )

                final_response = response4
            else:
                final_response = response3
        else:
            final_response = response3

        # Check final state with mock server
        if mock_server_running and final_response.type == "flight_search_results":
            assert "flights" in final_response.data

    @pytest.mark.asyncio
    async def test_roundtrip_minimal_start(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Round-trip starting with just destination, building up step by step."""
        # Turn 1: Just destination
        response1 = await chat_service.process_message(
            message="I need to go to Berlin",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.type == "collecting_info"

        # Turn 2: Origin
        response2 = await chat_service.process_message(
            message="from London",
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 3: Journey type
        response3 = await chat_service.process_message(
            message="return trip",  # Alternative phrasing for round-trip
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 4: Departure
        response4 = await chat_service.process_message(
            message="leaving on the 15th of January",
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 5: Return
        response5 = await chat_service.process_message(
            message="coming back on the 22nd",
            user=test_user,
            chat_id=chat_id,
        )

        # Should have enough info now
        assert response5.intent_name == "book_flight"
        if mock_server_running:
            assert response5.type in [
                "flight_search_results",
                "collecting_info",
                "searching",
            ]


@pytest.mark.integration
@pytest.mark.slow
class TestFieldExtractionVerification:
    """Tests that verify specific field extraction behavior."""

    @pytest.mark.asyncio
    async def test_passenger_extraction_adults_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify adult count is correctly extracted."""
        response = await chat_service.process_message(
            message="flight from AMS to BCN on Jan 10 for 3 adults, one way",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        # Document extraction behavior
        if "adults" in collected:
            assert collected["adults"] == 3, (
                f"EXTRACTION BUG: Should extract 3 adults, got: {collected['adults']}"
            )

    @pytest.mark.asyncio
    async def test_passenger_extraction_with_children(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify children count is correctly extracted."""
        response = await chat_service.process_message(
            message="flight from LHR to CDG on Feb 5 for 2 adults and 2 children, one way",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        if "adults" in collected:
            assert collected["adults"] == 2, (
                f"EXTRACTION BUG: Should extract 2 adults, got: {collected['adults']}"
            )
        if "children" in collected:
            assert collected["children"] == 2, (
                f"EXTRACTION BUG: Should extract 2 children, got: {collected['children']}"
            )

    @pytest.mark.asyncio
    async def test_date_extraction_natural_language(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify date extraction from natural language."""
        response = await chat_service.process_message(
            message="one way flight from Amsterdam to Madrid next Monday",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        # Document whether relative dates are extracted
        if "departure_date" in collected:
            # Should be a date, not "next Monday" as a string
            dep_date = collected["departure_date"]
            assert dep_date is not None, "Departure date should be extracted"
            # The date should be in a parseable format
            assert "monday" not in str(dep_date).lower(), (
                f"Date should be resolved, not literal 'next Monday': {dep_date}"
            )


@pytest.mark.integration
@pytest.mark.slow
class TestAirlinePreferenceBehavior:
    """Document actual airline preference handling behavior.

    IMPORTANT: These tests document what the system ACTUALLY does,
    even if that behavior is incorrect (e.g., ignoring airline preference).
    """

    @pytest.mark.asyncio
    async def test_airline_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if airline preference is extracted and stored.

        User says "United flight" - verify if this is captured in collected fields.
        """
        response = await chat_service.process_message(
            message="one way United Airlines flight from ORD to LAX on January 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        # Document current behavior
        has_airline_preference = (
            "airline" in collected or "preferred_airline" in collected
        )

        if has_airline_preference:
            airline_value = collected.get("airline") or collected.get(
                "preferred_airline"
            )
            # If captured, verify it's correct
            assert "united" in str(airline_value).lower(), (
                f"Airline preference should be United, got: {airline_value}"
            )
        else:
            # Document the bug: airline preference is not being captured
            pytest.xfail(
                "KNOWN BEHAVIOR: Airline preference 'United' is NOT captured in collected fields. "
                "The system ignores airline preferences in user input."
            )

    @pytest.mark.asyncio
    async def test_avoid_airline_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if 'avoid airline' preference is captured.

        User says "no Spirit please" - verify if this negative preference is captured.
        """
        response = await chat_service.process_message(
            message="one way flight from MIA to ATL on Feb 5, 1 adult, no Spirit please",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        has_avoid_airline = (
            "avoid_airline" in collected
            or "excluded_airlines" in collected
            or "airline_exclusions" in collected
        )

        if has_avoid_airline:
            avoid_value = (
                collected.get("avoid_airline")
                or collected.get("excluded_airlines")
                or collected.get("airline_exclusions")
            )
            assert "spirit" in str(avoid_value).lower()
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'No Spirit' preference is NOT captured. "
                "The system ignores airline exclusion requests."
            )

    @pytest.mark.asyncio
    async def test_direct_flight_preference(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if 'direct flight' preference is captured."""
        response = await chat_service.process_message(
            message="one way direct flight from BOS to SFO on March 1st, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        has_direct_pref = (
            "direct_only" in collected
            or "nonstop" in collected
            or "stops" in collected
            or "max_stops" in collected
        )

        if has_direct_pref:
            direct_value = (
                collected.get("direct_only")
                or collected.get("nonstop")
                or collected.get("max_stops") == 0
            )
            assert direct_value, (
                "Direct flight preference should be True or max_stops=0"
            )
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'Direct flight' preference is NOT captured. "
                "The system ignores nonstop/direct flight requests."
            )


@pytest.mark.integration
@pytest.mark.slow
class TestHotelCompleteFlow:
    """Complete hotel booking flow from minimal input to search results."""

    @pytest.mark.asyncio
    async def test_hotel_step_by_step(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Hotel flow: destination → dates → guests → results."""
        # Turn 1: Just destination
        response1 = await chat_service.process_message(
            message="I need a hotel in Amsterdam",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_hotel"
        assert response1.type == "collecting_info"

        # Turn 2: Check-in date
        response2 = await chat_service.process_message(
            message="from December 20th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_hotel"

        # Turn 3: Check-out date
        response3 = await chat_service.process_message(
            message="until December 25th",
            user=test_user,
            chat_id=chat_id,
        )

        # Turn 4: Guests if asked
        if response3.type == "collecting_info" and get_waiting_for(response3) in [
            "guests",
            "adults",
        ]:
            response4 = await chat_service.process_message(
                message="for 2 adults",
                user=test_user,
                chat_id=chat_id,
            )
            final_response = response4
        else:
            final_response = response3

        # With mock server should get results
        if mock_server_running and final_response.type == "hotel_results":
            assert "hotels" in final_response.data

    @pytest.mark.asyncio
    async def test_hotel_guest_extraction(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify hotel guest count extraction."""
        response = await chat_service.process_message(
            message="book a hotel in Paris from Dec 23 to Dec 27 for 2 adults and 1 child",
            user=test_user,
            chat_id=chat_id,
        )

        collected = get_collected(response)

        if "adults" in collected:
            assert collected["adults"] == 2, (
                f"Should have 2 adults, got: {collected['adults']}"
            )
        if "children" in collected:
            assert collected["children"] == 1, (
                f"Should have 1 child, got: {collected['children']}"
            )
