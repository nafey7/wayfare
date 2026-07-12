"""
LangGraph flight agent integration tests.

These tests document bugs in the LangGraph flight agent and verify fixes.

Run with: pytest tests/integration_tests/ai/test_langgraph_flight_agent.py -v -m integration

REQUIREMENTS:
- FlightLogic mock server: docker compose up -d
- Gemini API key: GOOGLE_GENERATIVE_AI_API_KEY in .env
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


@pytest.mark.integration
@pytest.mark.slow
class TestLangGraphIntentBugs:
    """Tests for intent recognition bugs when using LangGraph."""

    @pytest.mark.asyncio
    async def test_marco_polo_maintains_flight_intent(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Bug 7: 'Marco Polo' should maintain BOOK_FLIGHT intent during airport selection.

        Scenario:
        1. User: "Book a flight from Amsterdam to Venice"
        2. Agent: "Venice has multiple airports. Which do you prefer: Marco Polo (VCE)..."
        3. User: "Marco Polo"
        4. Bug: Agent responds about the explorer Marco Polo instead of selecting the airport
        """
        # Turn 1: Start flight booking to Venice (has multiple airports)
        response1 = await chat_service.process_message(
            message="Book a flight from Amsterdam to Venice",
            user=test_user,
            chat_id=chat_id,
        )

        # Should ask about Venice airports (Venice has VCE, TSF, etc.)
        assert response1.intent_name == "book_flight"
        # Check if asking about airports (flexible assertion for LLM variability)
        airport_keywords = ["airport", "prefer", "marco polo", "vce", "tessera"]
        assert any(kw in response1.message.lower() for kw in airport_keywords), (
            f"Expected airport question, got: {response1.message}"
        )

        # Turn 2: User responds with airport name
        response2 = await chat_service.process_message(
            message="Marco Polo",
            user=test_user,
            chat_id=chat_id,
        )

        # Bug: Currently routes to general_travel_handler and talks about the explorer
        # Fix: Should maintain BOOK_FLIGHT intent and select VCE airport

        # Should NOT talk about Marco Polo the explorer
        explorer_phrases = [
            "incredible inspiration",
            "adventure",
            "explorer",
            "traveler",
            "silk road",
            "calling your name",
        ]
        assert not any(
            phrase in response2.message.lower() for phrase in explorer_phrases
        ), (
            f"Response talks about Marco Polo explorer instead of airport: {response2.message}"
        )

        # Should maintain flight booking intent
        assert response2.intent_name == "book_flight", (
            f"Expected book_flight intent, got: {response2.intent_name}"
        )

        # Should ask about next step (dates, passengers, trip type, etc.) or confirm VCE selection
        # Be flexible since LLM can ask about different booking details
        flight_keywords = [
            "when",
            "date",
            "travel",
            "passenger",
            "vce",
            "selected",
            "round-trip",
            "one-way",
            "return",
            "depart",
            "how many",
        ]
        assert any(kw in response2.message.lower() for kw in flight_keywords), (
            f"Expected flight-related response, got: {response2.message}"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestLangGraphAirportResolution:
    """Tests for airport resolution bugs in LangGraph."""

    @pytest.mark.asyncio
    async def test_goa_resolves_to_india_not_genoa(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Bug 1: 'Book a flight to Goa' should use GOI (Goa, India) not GOA (Genoa).

        Scenario:
        1. User: "Book a flight to Goa"
        2. Bug: Agent uses GOA (Genoa, Italy) instead of GOI (Goa, India)

        GOA = IATA code for Genoa Cristoforo Colombo Airport, Italy
        GOI = IATA code for Goa International Airport, India

        When user says "Goa" they mean the Indian state, not Genoa.

        Acceptable outcomes:
        - Uses GOI directly (Goa, India)
        - Asks for disambiguation between Goa (India) and Genoa (Italy)
        """
        response = await chat_service.process_message(
            message="Book a flight from Amsterdam to Goa next month for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Should detect as flight booking
        assert response.intent_name == "book_flight"

        response_lower = response.message.lower()

        # Acceptable: Asks for disambiguation between Goa and Genoa
        is_disambiguating = any(
            phrase in response_lower
            for phrase in ["genoa", "italy", "india", "which", "mean", "did you mean"]
        )

        # If it returns search results, check destination is GOI not GOA
        if response.type == "flight_search_results" and response.data:
            # Check if there are flights in the response
            flights = response.data.get("flights", [])
            if flights:
                # Get destination codes from flights
                destinations = set()
                for flight in flights:
                    if hasattr(flight, "destination_code"):
                        destinations.add(flight.destination_code)
                    elif isinstance(flight, dict):
                        destinations.add(flight.get("destination_code", ""))
                        destinations.add(flight.get("destination", ""))

                # Should be GOI (Goa, India), not GOA (Genoa, Italy)
                assert "GOA" not in destinations, (
                    f"Used GOA (Genoa) instead of GOI (Goa, India). Destinations: {destinations}"
                )

        # If NOT disambiguating, should NOT mention Genoa as the destination
        if not is_disambiguating:
            assert "genoa" not in response_lower, (
                f"Response mentions Genoa instead of Goa: {response.message}"
            )

            # Should mention Goa (India) in some form
            goa_keywords = ["goa", "goi", "india", "dabolim"]
            assert any(kw in response_lower for kw in goa_keywords), (
                f"Expected reference to Goa/India, got: {response.message}"
            )


@pytest.mark.integration
@pytest.mark.slow
class TestLangGraphStateManagement:
    """Tests for state management bugs in LangGraph."""

    @pytest.mark.asyncio
    async def test_new_chat_ignores_old_search_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        mock_server_running: bool,
    ):
        """Bug 2: New chat should not return stale search results from previous searches.

        Scenario:
        1. Chat A: Complete a flight search (results stored in checkpoint)
        2. Start new Chat B: "Book a flight to London"
        3. Bug: Response includes old search results from Chat A

        Root cause: _extract_flight_search_results() scans ALL messages in
        checkpoint history, finding old search_flights tool results.
        """
        # Use a unique chat_id for first search
        chat_id_a = f"test-chat-stale-A-{id(self)}"

        # Turn 1: Complete a flight search in Chat A
        response1 = await chat_service.process_message(
            message="Book a round trip flight from Amsterdam to Paris, December 20 to 25, 2 adults",
            user=test_user,
            chat_id=chat_id_a,
        )

        # Verify first search completed (may or may not have results)
        assert response1.intent_name == "book_flight"

        # Use a different unique chat_id for second chat
        chat_id_b = f"test-chat-stale-B-{id(self)}"

        # Turn 2: Start NEW chat with only destination (no origin, dates, passengers)
        response2 = await chat_service.process_message(
            message="Book a flight to London",
            user=test_user,
            chat_id=chat_id_b,
        )

        # Should ask for missing info, NOT return search results
        assert response2.intent_name == "book_flight"

        # Bug: response.type is "flight_search_results" with old data
        # Fix: Should be "collecting_info" or similar, asking for origin

        # Should NOT have flight results
        assert response2.type != "flight_search_results", (
            f"New chat returned stale search results. Type: {response2.type}"
        )

        # Should ask about origin or other missing info
        asking_keywords = ["where", "from", "flying from", "origin", "departing"]
        assert any(kw in response2.message.lower() for kw in asking_keywords), (
            f"Expected question about missing info, got: {response2.message}"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestLangGraphDisambiguation:
    """Tests for city/airport disambiguation bugs."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Bug 4: Springfield shows airports from different states without disambiguation"
    )
    async def test_springfield_disambiguates_states(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Bug 4: 'Springfield' should ask which state, not mix airports from different states.

        Scenario:
        1. User: "Book a flight to Springfield"
        2. Bug: Shows "Springfield has multiple airports: SGF, SPI, VSF..."
           where SGF=Missouri, SPI=Illinois, VSF=Vermont
        3. Fix: Should first ask "Which Springfield? Missouri, Illinois, Vermont..."

        This is a disambiguation issue where same-country, different-state
        cities are not properly disambiguated.
        """
        response = await chat_service.process_message(
            message="Book a flight from New York to Springfield",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"

        response_lower = response.message.lower()

        # Bug: Lists airports from multiple states without asking which Springfield
        # Check if it mixed airports from different states
        mixed_state_indicators = [
            # If mentions airports from multiple states
            ("sgf" in response_lower and "spi" in response_lower),
            ("missouri" in response_lower and "illinois" in response_lower),
            # If just lists airports without state context
            ("multiple" in response_lower and "airports" in response_lower),
        ]

        # Should NOT mix airports from different states
        assert not any(mixed_state_indicators), (
            f"Mixed airports from different Springfield states: {response.message}"
        )

        # Should ask which Springfield the user means
        disambiguation_keywords = [
            "which springfield",
            "missouri",
            "illinois",
            "ohio",
            "massachusetts",
            "vermont",
            "which state",
        ]
        assert any(kw in response_lower for kw in disambiguation_keywords), (
            f"Expected disambiguation question about which Springfield, got: {response.message}"
        )
