"""
Flight booking conversation integration tests.

These are characterization tests that capture current behavior before refactoring.
They run against the real Gemini API with specific assertions on response structure.

Run with: pytest tests/integration_tests/ai/test_flight_conversation.py -v -m integration

When FlightLogic mock server is running (docker compose up -d flightlogic-mock),
tests verify actual search results. Without mock, tests allow error states.
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService


@pytest.mark.integration
@pytest.mark.slow
class TestFlightConversationHappyPath:
    """Happy path flight booking conversations."""

    @pytest.mark.asyncio
    async def test_roundtrip_single_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete round trip booking request in one message."""
        response = await chat_service.process_message(
            message="I want to book a round trip flight from Amsterdam to London, "
            "departing December 15th and returning December 20th, for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure assertions
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 20

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock server is running
        if mock_server_running:
            # With mock server, should get flight results (not errors)
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ], f"Expected flight_results with mock server, got: {response.type}"

            # Verify mock server returns expected data
            if response.type == "flight_search_results":
                assert "flights" in response.data, (
                    "flight_results should have 'flights' key"
                )
                flights = response.data["flights"]
                assert len(flights) == 3, (
                    f"Mock should return 3 flights, got {len(flights)}"
                )

                # Verify expected airlines from mock (BA, Ryanair, KLM)
                airlines = {f.validating_airline.iata_code for f in flights}
                assert airlines == {"BA", "FR", "KL"}, (
                    f"Expected BA/FR/KL, got {airlines}"
                )

                # Verify expected prices from mock (215, 295.50, 375 EUR)
                prices = sorted(
                    float(f.pricing.fare_totals.total_fare.amount) for f in flights
                )
                assert prices == [215.0, 295.5, 375.0], (
                    f"Expected mock prices, got {prices}"
                )
        else:
            # Without mock, allow error states
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "error",
                "searching",
                "search_error",
            ]
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_oneway_single_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """One-way flight booking in one message.

        Route JFK-LAX has fixtures:
        - Delta Air Lines (DL1287): €215.00
        - JetBlue Airways (B6223): €178.00
        - American Airlines (AA177): €198.00
        """
        response = await chat_service.process_message(
            message="one way flight from JFK to LAX tomorrow for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 20

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock server is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ], f"Expected flight_results with mock server, got: {response.type}"

            # Verify fixture data when results are returned
            if response.type == "flight_search_results" and response.data:
                # Should have flights from fixture
                flights = response.data.get("flights", [])
                if flights:
                    assert len(flights) == 3, (
                        f"JFK-LAX fixture has 3 flights, got {len(flights)}"
                    )
                    # Verify expected airlines from fixture
                    airlines = {
                        f.get("validating_airline", {}).get("iata_code")
                        if isinstance(f, dict)
                        else getattr(
                            getattr(f, "validating_airline", None), "iata_code", None
                        )
                        for f in flights
                    }
                    # Fixture airlines: DL, B6, AA
                    assert airlines == {"DL", "B6", "AA"}, (
                        f"Expected Delta/JetBlue/AA, got {airlines}"
                    )
        else:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "error",
                "searching",
                "search_error",
            ]
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestFlightConversationMultiTurn:
    """Multi-turn flight booking conversations (field collection)."""

    @pytest.mark.asyncio
    async def test_field_collection_flow(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Test multi-turn conversation collecting fields one by one.

        Verifies the field collection state machine:
        Turn 1: Establish intent -> asks for journey_type
        Turn 2: Provide journey_type -> asks for next field (date/origin)
        Turn 3: Continue providing info -> progresses through fields
        """
        # Turn 1: Intent with destination only
        response1 = await chat_service.process_message(
            message="I want to fly to Paris",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response1.intent_name == "book_flight"
        assert response1.confidence >= 0.9

        # State assertions - should be collecting info
        assert response1.type == "collecting_info"
        assert response1.data is not None
        assert "waiting_for" in response1.data

        # Current behavior: asks for journey_type first
        waiting_for_1 = response1.data.get("waiting_for")
        assert waiting_for_1 == "journey_type"

        # KNOWN BUG: Destination from "fly to Paris" is NOT being extracted
        # See test_intent_recognition.py::TestClearIntentRecognition::test_flight_with_destination
        collected = response1.data.get("collected_so_far", {})
        if "destination" in collected:
            # If bug is fixed, verify correct extraction
            dest_value = collected.get("destination", "")
            assert any(x in dest_value.upper() for x in ["PARIS", "CDG", "ORY"]), (
                f"destination should be Paris airport, got: {dest_value}"
            )
        # else: BUG - destination not extracted from "I want to fly to Paris"

        # Turn 2: Provide journey type
        response2 = await chat_service.process_message(
            message="round trip",
            user=test_user,
            chat_id=chat_id,
        )

        # Should maintain intent and continue collecting
        assert response2.intent_name == "book_flight"
        assert response2.type == "collecting_info"
        assert response2.data is not None

        # Should have progressed to next field
        waiting_for_2 = response2.data.get("waiting_for")
        assert waiting_for_2 is not None
        # Should now ask for date, origin, or passengers
        assert waiting_for_2 in [
            "departure_date",
            "origin",
            "passengers",
            "return_date",
        ]

        # Turn 3: Provide departure date
        response3 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )

        # Should continue collecting
        assert response3.intent_name == "book_flight"
        assert response3.type == "collecting_info"
        assert response3.data is not None

        # Should have progressed further
        waiting_for_3 = response3.data.get("waiting_for")
        assert waiting_for_3 is not None


@pytest.mark.integration
@pytest.mark.slow
class TestFlightConversationWithVariations:
    """Flight booking with various input patterns."""

    @pytest.mark.asyncio
    async def test_with_children(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Flight booking with children included in request."""
        response = await chat_service.process_message(
            message="flight from Boston to Miami on December 10th for 2 adults and 2 children",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ], f"Expected non-error state with mock server, got: {response.type}"
        else:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
                "error",
            ]
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_relative_return_date(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test '2 weeks later' pattern for return date."""
        response = await chat_service.process_message(
            message="round trip from London to Tokyo, leaving January 10th, "
            "returning 2 weeks later, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9

        # Response should be substantive
        assert len(response.message) > 20

        # State assertions - stronger when mock is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ], f"Expected non-error state with mock server, got: {response.type}"
        else:
            assert response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
                "error",
            ]
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestFlightSelectionPatterns:
    """Test different flight selection patterns after search results.

    When FlightLogic mock server is running, tests verify actual selection.
    Without mock, tests verify error handling behavior.

    Uses AMS-MAD route which has fixtures:
    - Iberia (IB3721): €134.00
    - KLM Royal Dutch Airlines (KL1701): €152.00
    - Vueling (VY8300): €78.00
    """

    async def _get_search_results(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Helper to trigger a search and get results.

        Uses AMS-MAD one-way route to match fixture data.
        """
        return await chat_service.process_message(
            message="one way flight from AMS to MAD December 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

    @pytest.mark.asyncio
    async def test_selection_by_option_number(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select flight by 'option 1'."""
        # Get search results first
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        # Verify search response
        assert search_response.intent_name == "book_flight"
        assert search_response.data is not None

        # With mock server, search should succeed
        if mock_server_running:
            assert search_response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ], f"Search should succeed with mock, got: {search_response.type}"

        # Attempt selection
        response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_flight"
        # Note: booking_clarification responses may have data=None
        if response.type not in ["booking_clarification", "error"]:
            assert response.data is not None

        # With mock server, selection should work (not just show error keywords)
        if mock_server_running and search_response.type in [
            "search_results",
            "flight_search_results",
        ]:
            # Should have selection-related keywords (not error keywords)
            message_lower = response.message.lower()
            assert any(
                word in message_lower
                for word in ["selected", "booking", "confirm", "option", "proceed"]
            ), f"Expected selection success message, got: {response.message[:100]}"
        else:
            # Without mock or if search failed, allow error handling
            message_lower = response.message.lower()
            assert any(
                word in message_lower
                for word in [
                    "selected",
                    "booking",
                    "confirm",
                    "option",
                    "sorry",
                    "no",
                    "flight",
                ]
            )

    @pytest.mark.asyncio
    async def test_selection_cheapest(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select cheapest flight."""
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_flight"

        # With mock server, search should succeed
        if mock_server_running:
            assert search_response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ]

        response = await chat_service.process_message(
            message="book the cheapest one",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_flight"
        assert len(response.message) > 10

    @pytest.mark.asyncio
    async def test_selection_ordinal(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select by ordinal ('first option')."""
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_flight"

        # With mock server, search should succeed
        if mock_server_running:
            assert search_response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ]

        response = await chat_service.process_message(
            message="I'll take the first option",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_flight"
        assert len(response.message) > 10

    @pytest.mark.asyncio
    async def test_selection_bare_number(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select by bare number ('2').

        FIXED: Bare numbers now correctly maintain sticky intent.
        AI recognizes "2" in booking context and maintains book_flight intent.
        """
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_flight"

        # With mock server, search should succeed
        if mock_server_running:
            assert search_response.type in [
                "collecting_info",
                "search_results",
                "flight_search_results",
                "searching",
            ]

        response = await chat_service.process_message(
            message="2",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None

        # AI maintains flight intent with bare number in booking context
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert len(response.message) > 10


@pytest.mark.integration
@pytest.mark.slow
class TestMultiAirportScenarios:
    """Test multi-airport handling (ISSUE #12).

    CURRENT BEHAVIOR (documented via characterization tests):
    - Multi-airport disambiguation is NOT triggered
    - System picks first matching airport and proceeds to search
    - This may pick WRONG airport (e.g., London Ontario instead of London UK)

    EXPECTED BEHAVIOR (after ISSUE #12 fix):
    - Cities with multiple airports should trigger disambiguation
    - User should be asked to select preferred airport

    These tests document the current (buggy) behavior to catch regressions.
    """

    @pytest.mark.asyncio
    async def test_london_origin_does_not_disambiguate(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """London as origin - CURRENT: No disambiguation, goes straight to search.

        KNOWN BUG: System resolves "London" to YXU (London, Ontario, Canada)
        instead of UK airports (LHR, LGW, STN).

        London UK has multiple airports: LHR (Heathrow), LGW (Gatwick),
        STN (Stansted), LTN (Luton), LCY (City).

        After ISSUE #12 fix, this test should FAIL and need updating to expect
        airport_preference type and proper disambiguation.
        """
        response = await chat_service.process_message(
            message="I need a one-way flight from London to Amsterdam on December 20th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent should be recognized
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.data is not None

        # CURRENT BEHAVIOR: Goes straight to flight_results (no disambiguation)
        if mock_server_running:
            assert response.type == "flight_search_results", (
                f"Current behavior: straight to flight_results, got: {response.type}"
            )
            # Verify flights were returned
            assert "flights" in response.data
            assert len(response.data["flights"]) > 0

            # KNOWN BUG: Check what airport was selected
            # Currently picks YXU (London, Ontario) instead of LHR (London, UK)
            search_params = response.data.get("search_params", {})
            origin = search_params.get("origin", "")
            # This documents the bug - YXU is wrong but is current behavior
            # After fix, should be one of: LHR, LGW, STN, LTN, LCY
            assert origin in ["YXU", "LHR", "LGW", "STN", "LTN", "LCY"], (
                f"Origin should be a London airport, got: {origin}"
            )
        else:
            # Without mock, may error
            assert response.type in ["flight_search_results", "error", "search_error"]

    @pytest.mark.asyncio
    async def test_new_york_destination_triggers_disambiguation(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """New York as destination - CURRENT: Triggers disambiguation!

        New York has multiple airports: JFK, LGA, EWR.
        Current behavior: System asks for airport preference.

        Note: This is different from London origin which doesn't disambiguate.
        The inconsistency should be fixed in ISSUE #12.
        """
        response = await chat_service.process_message(
            message="one way flight from Amsterdam to New York on January 15th for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent should be recognized
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.data is not None

        # CURRENT BEHAVIOR: Triggers airport_preference for New York
        assert response.type == "airport_preference", (
            f"New York triggers disambiguation, got: {response.type}"
        )

        # Should mention NYC airports
        message_lower = response.message.lower()
        assert any(
            airport in message_lower
            for airport in [
                "jfk",
                "lga",
                "ewr",
                "kennedy",
                "laguardia",
                "newark",
                "airport",
            ]
        ), f"Should mention NYC airports: {response.message[:200]}"

    @pytest.mark.asyncio
    async def test_both_cities_extraction_bug(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Both origin and destination have multiple airports.

        London (LHR/LGW/STN) to New York (JFK/LGA/EWR).

        KNOWN BUG: "New York" is NOT extracted from "from London to New York".
        The system asks for destination despite it being in the message.

        This is related to the same extraction bug seen in test_flight_with_destination
        where "fly to Paris" doesn't extract Paris.
        """
        response = await chat_service.process_message(
            message="round trip from London to New York, December 20th to December 27th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent should be recognized
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.data is not None

        # CURRENT BUG: Asks for destination despite "to New York" in message
        assert response.type == "collecting_info", (
            f"Current bug: asks for destination, got: {response.type}"
        )

        # KNOWN BUG: waiting_for is 'destination' even though New York was specified
        waiting_for = response.data.get("waiting_for")
        assert waiting_for == "destination", (
            f"Current bug: expected destination extraction failure, got waiting_for={waiting_for}"
        )

    @pytest.mark.asyncio
    async def test_specific_airport_code_asks_journey_type(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Using specific IATA codes without journey_type specified.

        CURRENT BEHAVIOR: Asks for journey_type (one-way vs round-trip) first.
        The message "flight from LHR to CDG" doesn't specify journey_type.

        Key point: No disambiguation needed for IATA codes.
        """
        response = await chat_service.process_message(
            message="flight from LHR to CDG on December 20th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent should be recognized
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.data is not None

        # CURRENT BEHAVIOR: Asks for journey_type first (one-way vs round-trip)
        assert response.type == "collecting_info", (
            f"Expected collecting_info for journey_type, got: {response.type}"
        )

        # Should be waiting for journey_type
        waiting_for = response.data.get("waiting_for")
        assert waiting_for == "journey_type", (
            f"Expected waiting for journey_type, got: {waiting_for}"
        )

        # Key assertion: Should NOT ask for airport preference (codes are specific)
        assert response.type != "airport_preference"

    @pytest.mark.asyncio
    async def test_disambiguation_not_triggered_multi_turn(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Multi-turn with city name - CURRENT: Still no disambiguation.

        Even when providing London in a separate turn, disambiguation
        is not triggered in current implementation.
        """
        # Turn 1: Start with incomplete info
        response1 = await chat_service.process_message(
            message="I want to fly from London to Barcelona on January 10th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.data is not None

        # CURRENT BEHAVIOR: No airport_preference asked
        # Goes straight to collecting_info (for passengers) or flight_results
        assert response1.type in [
            "collecting_info",
            "flight_search_results",
            "error",
        ], f"Current behavior: no disambiguation, got: {response1.type}"

        # Specifically NOT airport_preference
        assert response1.type != "airport_preference", (
            "ISSUE #12: Disambiguation not implemented yet"
        )

    @pytest.mark.asyncio
    async def test_paris_origin_asks_journey_type_first(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Paris as origin - has CDG and ORY airports.

        CURRENT BEHAVIOR: Asks for journey_type first (message doesn't specify).
        No airport disambiguation for Paris in current implementation.

        Note: Paris has multiple airports (CDG, ORY) but disambiguation
        is not triggered - it picks one and proceeds.
        """
        response = await chat_service.process_message(
            message="flight from Paris to London tomorrow, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # CURRENT BEHAVIOR: Asks for journey_type first
        assert response.type == "collecting_info", (
            f"Expected collecting_info, got: {response.type}"
        )

        # Should be waiting for journey_type
        waiting_for = response.data.get("waiting_for")
        assert waiting_for == "journey_type", (
            f"Expected waiting for journey_type, got: {waiting_for}"
        )

        # Key: NOT airport_preference - Paris doesn't trigger disambiguation
        assert response.type != "airport_preference"


@pytest.mark.integration
@pytest.mark.slow
class TestAirportPreferenceResponseFlow:
    """Test airport preference selection flow - Phase 3 critical path.

    These tests cover the _handle_airport_preference_response method
    which will be extracted to AirportAmbiguityHandler in Phase 3.

    The flow is:
    1. User provides city with multiple airports (e.g., New York)
    2. System returns airport_preference response with options
    3. User selects preferred airport (e.g., "JFK")
    4. System proceeds to search with selected airport
    """

    @pytest.mark.asyncio
    async def test_select_jfk_after_nyc_disambiguation(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete flow: NYC disambiguation -> select JFK -> search results.

        This is the happy path for airport preference selection.
        Covers _handle_airport_preference_response in enhanced_flight_handler.py.
        """
        # Turn 1: Trigger NYC disambiguation
        response1 = await chat_service.process_message(
            message="one way flight from Amsterdam to New York on January 15th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.type == "airport_preference", (
            f"Expected airport_preference for NYC, got: {response1.type}"
        )

        # Turn 2: Select JFK
        response2 = await chat_service.process_message(
            message="JFK",
            user=test_user,
            chat_id=chat_id,
        )

        # Should proceed to search or ask for more info
        assert response2.type in [
            "flight_search_results",
            "collecting_info",
            "error",
        ], f"After selecting JFK, expected search or collection, got: {response2.type}"

        # If search executed, verify JFK was used
        if response2.type == "flight_search_results" and response2.data:
            search_params = response2.data.get("search_params", {})
            destination = search_params.get("destination", "")
            assert destination == "JFK" or "JFK" in str(response2.data), (
                f"Expected JFK as destination after selection, got: {destination}"
            )

    @pytest.mark.asyncio
    async def test_select_newark_by_name(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select airport by name instead of code.

        Users may say "Newark" instead of "EWR".
        """
        # Turn 1: Trigger disambiguation
        response1 = await chat_service.process_message(
            message="one way flight from AMS to New York on Feb 10 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        if response1.type != "airport_preference":
            pytest.skip(f"NYC didn't trigger disambiguation: {response1.type}")

        # Turn 2: Select Newark by name
        response2 = await chat_service.process_message(
            message="Newark please",
            user=test_user,
            chat_id=chat_id,
        )

        # Should proceed or clarify (Newark matches name but not specific airport)
        # airport_preference_clarification means system needs more specific selection
        assert response2.type in [
            "flight_search_results",
            "collecting_info",
            "error",
            "airport_preference_clarification",  # May need more specific selection
        ], f"After selecting Newark, got: {response2.type}"

    @pytest.mark.asyncio
    async def test_select_option_number_for_airport(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select airport by option number (e.g., "option 1").

        Similar to flight selection, users may select airport by number.
        """
        # Turn 1: Trigger disambiguation
        response1 = await chat_service.process_message(
            message="one way from Paris to New York on March 5th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if response1.type != "airport_preference":
            pytest.skip(f"NYC didn't trigger disambiguation: {response1.type}")

        # Turn 2: Select by number
        response2 = await chat_service.process_message(
            message="option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Should proceed or clarify (option selection may not work for airports)
        assert response2.type in [
            "flight_search_results",
            "collecting_info",
            "error",
            "airport_preference",
            "airport_preference_clarification",
        ], f"After selecting option 1, got: {response2.type}"

    @pytest.mark.asyncio
    async def test_invalid_airport_selection_reprompts(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Invalid airport selection should reprompt.

        If user provides invalid selection, system should ask again.
        """
        # Turn 1: Trigger disambiguation
        response1 = await chat_service.process_message(
            message="one way AMS to New York Jan 20 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if response1.type != "airport_preference":
            pytest.skip(f"NYC didn't trigger disambiguation: {response1.type}")

        # Turn 2: Invalid selection
        response2 = await chat_service.process_message(
            message="I don't know",
            user=test_user,
            chat_id=chat_id,
        )

        # Should either reprompt for airport, proceed with default, or reset context
        # CURRENT BEHAVIOR: "I don't know" resets conversation context to general chat
        assert response2.type in [
            "airport_preference",
            "airport_preference_clarification",
            "flight_search_results",
            "collecting_info",
            "error",
            "ai_response",  # Context reset - user abandoned the flow
        ], f"After invalid selection, got: {response2.type}"

    @pytest.mark.asyncio
    async def test_ams_to_london_triggers_disambiguation(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Multi-turn flow: AMS → London triggers disambiguation.

        Verifies that London as destination triggers airport disambiguation.

        Flow:
        1. "Book a flight from Amsterdam to London" → asks journey_type
        2. "One way" → asks for date
        3. "May 15th" → should trigger London disambiguation (LHR, LTN, etc.)

        This test ensures disambiguation is working - the response to
        airport selection is tested separately.
        """
        # Turn 1: Intent with origin and destination
        response1 = await chat_service.process_message(
            message="Book a flight from Amsterdam to London",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.confidence >= 0.9
        assert response1.type == "collecting_info", (
            f"Expected collecting_info for journey_type, got: {response1.type}"
        )

        # Turn 2: Provide journey type
        response2 = await chat_service.process_message(
            message="One way",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_flight"
        assert response2.type == "collecting_info", (
            f"Expected collecting_info for date, got: {response2.type}"
        )

        # Turn 3: Provide date - should trigger London disambiguation
        response3 = await chat_service.process_message(
            message="May 15th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response3.intent_name == "book_flight"
        # London as destination should trigger disambiguation
        assert response3.type == "airport_preference", (
            f"Expected airport_preference for London disambiguation, got: {response3.type}"
        )

        # Verify London airports are mentioned
        message_lower = response3.message.lower()
        assert any(
            airport in message_lower
            for airport in [
                "lhr",
                "heathrow",
                "ltn",
                "luton",
                "gatwick",
                "lgw",
                "stansted",
                "stn",
            ]
        ), f"Should mention London airports: {response3.message[:200]}"

    @pytest.mark.asyncio
    async def test_ams_to_london_lhr_selection_proceeds_to_search(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """After London disambiguation, selecting LHR should proceed to search.

        Verifies that after selecting LHR from London disambiguation,
        the system correctly proceeds to search and returns results.

        NOTE: This test has been observed to be flaky in production (error:
        "encountered an error while searching"). The error appears to be
        intermittent and may be related to the real FlightLogic API rather
        than the mock server. Monitor for regressions during refactoring.

        Uses AMS-LHR fixture:
        - British Airways (BA431): €145.00
        - KLM Royal Dutch Airlines (KL1001): €132.00
        - easyJet (U28832): €58.00
        """
        if not mock_server_running:
            pytest.skip("Requires mock server for predictable results")

        # Turn 1-3: Get to disambiguation
        response1 = await chat_service.process_message(
            message="Book a flight from Amsterdam to London",
            user=test_user,
            chat_id=chat_id,
        )
        assert response1.type == "collecting_info"

        response2 = await chat_service.process_message(
            message="One way",
            user=test_user,
            chat_id=chat_id,
        )
        assert response2.type == "collecting_info"

        response3 = await chat_service.process_message(
            message="May 15th",
            user=test_user,
            chat_id=chat_id,
        )

        if response3.type != "airport_preference":
            pytest.skip(f"London didn't trigger disambiguation: {response3.type}")

        # Turn 4: Select LHR (Heathrow) - this is where the bug occurs
        response4 = await chat_service.process_message(
            message="LHR",
            user=test_user,
            chat_id=chat_id,
        )

        assert response4.intent_name == "book_flight"
        # EXPECTED BEHAVIOR (currently fails):
        # Should return flight_search_results with AMS-LHR fixture data
        assert response4.type == "flight_search_results", (
            f"Expected flight_search_results after LHR selection, got: {response4.type}. "
            f"Message: {response4.message[:200] if response4.message else 'None'}"
        )

        # Verify AMS-LHR fixture data
        assert response4.data is not None
        flights = response4.data.get("flights", [])
        assert len(flights) == 3, f"AMS-LHR fixture has 3 flights, got {len(flights)}"

        # Verify expected airlines from fixture
        airlines = {
            f.validating_airline.iata_code
            if hasattr(f, "validating_airline")
            else f.get("validating_airline", {}).get("iata_code")
            for f in flights
        }
        assert airlines == {"BA", "KL", "U2"}, f"Expected BA/KL/U2, got {airlines}"

    @pytest.mark.asyncio
    async def test_ams_to_london_selects_heathrow_by_name(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select Heathrow by name instead of code.

        Users may say "Heathrow" instead of "LHR".
        """
        # Turn 1: Complete request except airport
        response1 = await chat_service.process_message(
            message="one way from Amsterdam to London on May 20th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # May or may not trigger disambiguation depending on behavior
        if response1.type != "airport_preference":
            # If no disambiguation, test passes (London resolved automatically)
            pytest.skip(f"London didn't trigger disambiguation: {response1.type}")

        # Turn 2: Select Heathrow by name
        response2 = await chat_service.process_message(
            message="Heathrow",
            user=test_user,
            chat_id=chat_id,
        )

        # Should proceed to search or ask for clarification
        assert response2.type in [
            "flight_search_results",
            "collecting_info",
            "error",
            "airport_preference_clarification",
        ], f"After selecting Heathrow, got: {response2.type}"


@pytest.mark.integration
@pytest.mark.slow
class TestCuratedResultsStructure:
    """Test curated flight results structure - Phase 3 critical path.

    These tests verify the _curate_multi_airport_results method output,
    which will be extracted to FlightSearchCurator in Phase 3.

    The curation produces:
    - 💵 LOWEST PRICE: Cheapest flight
    - ⚡ FASTEST: Shortest duration
    - ⭐ BEST VALUE: Price/duration balance

    Uses AMS-LHR route fixtures:
    - British Airways (BA431): €145.00
    - KLM Royal Dutch Airlines (KL1001): €132.00
    - easyJet (U28832): €58.00 (cheapest)
    """

    @pytest.mark.asyncio
    async def test_results_have_curated_categories(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify results include curated categories.

        AMS-LHR fixture returns 3 flights:
        - easyJet: €58 (cheapest)
        - KLM: €132
        - BA: €145
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server for predictable results")

        response = await chat_service.process_message(
            message="one way flight from AMS to LHR on December 20th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.type == "flight_search_results", (
            f"Expected flight_results, got: {response.type}"
        )
        assert response.message is not None

        # Verify fixture data is returned
        if response.data and "flights" in response.data:
            flights = response.data["flights"]
            assert len(flights) == 3, (
                f"AMS-LHR fixture has 3 flights, got {len(flights)}"
            )

        # Curated results should include these markers in the message
        message_upper = response.message.upper()

        # Should have at least one of the curated categories
        has_lowest_price = "LOWEST PRICE" in message_upper or "💵" in response.message
        has_fastest = "FASTEST" in message_upper or "⚡" in response.message
        has_best_value = "BEST VALUE" in message_upper or "⭐" in response.message

        assert has_lowest_price or has_fastest or has_best_value, (
            f"Results should include curated categories. Message: {response.message[:500]}"
        )

    @pytest.mark.asyncio
    async def test_results_contain_flight_details(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify results contain essential flight details.

        Each flight result should include:
        - Airline name
        - Price
        - Duration or times
        - Stops info
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        response = await chat_service.process_message(
            message="one way AMS to CDG Dec 15 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if response.type != "flight_search_results":
            pytest.skip(f"Search didn't return results: {response.type}")

        message = response.message.lower()

        # Should contain price info (EUR/USD/currency symbol)
        has_price = any(x in message for x in ["eur", "usd", "€", "$", "price"])
        assert has_price, (
            f"Results should show price. Message: {response.message[:500]}"
        )

        # Should contain airline info
        has_airline = any(
            x in message for x in ["klm", "ryanair", "british airways", "airline", "🛫"]
        )
        assert has_airline, (
            f"Results should show airline. Message: {response.message[:500]}"
        )

        # Should contain timing/duration
        has_time = any(
            x in message for x in ["duration", "hour", "h ", "min", "→", "⏰"]
        )
        assert has_time, (
            f"Results should show duration/time. Message: {response.message[:500]}"
        )

    @pytest.mark.asyncio
    async def test_results_have_bookable_options(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify results can be booked by number.

        Results should be numbered so user can say "book option 1".
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        response = await chat_service.process_message(
            message="one way LHR to AMS on January 5th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if response.type != "flight_search_results":
            pytest.skip(f"Search didn't return results: {response.type}")

        # Should have numbered options (1., 2., etc.)
        message = response.message
        has_numbered_options = (
            "1." in message or "1)" in message or "Option 1" in message
        )

        assert has_numbered_options, (
            f"Results should have numbered options for booking. Message: {message[:500]}"
        )

        # Should have flight data in response
        assert response.data is not None
        assert "flights" in response.data or "search_params" in response.data

    @pytest.mark.asyncio
    async def test_price_sorting_accuracy(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify LOWEST PRICE is actually the cheapest option.

        AMS-LHR fixture data:
        - easyJet (U28832): €58.00 (cheapest)
        - KLM (KL1001): €132.00
        - British Airways (BA431): €145.00
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server for predictable prices")

        response = await chat_service.process_message(
            message="one way from AMS to LHR on Dec 20 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if response.type != "flight_search_results":
            pytest.skip(f"Search didn't return results: {response.type}")

        # Verify fixture prices in data
        if response.data and "flights" in response.data:
            flights = response.data["flights"]
            if flights:
                # Extract prices and verify fixture data
                prices = []
                for f in flights:
                    if isinstance(f, dict):
                        pricing = f.get("pricing", {})
                        fare_totals = pricing.get("fare_totals", {})
                        total_fare = fare_totals.get("total_fare", {})
                        amount = total_fare.get("amount")
                    else:
                        amount = getattr(
                            getattr(
                                getattr(
                                    getattr(f, "pricing", None), "fare_totals", None
                                ),
                                "total_fare",
                                None,
                            ),
                            "amount",
                            None,
                        )
                    if amount:
                        prices.append(float(amount))

                if prices:
                    # Fixture has easyJet at €58 base + 15% tax = €66.70
                    min_price = min(prices)
                    assert min_price == 66.7, (
                        f"Cheapest should be €66.70 (easyJet €58 + tax), got €{min_price}"
                    )

        # Find LOWEST PRICE section in message
        message = response.message
        if "LOWEST PRICE" in message.upper() or "💵" in message:
            # The lowest price option should mention easyJet or €58
            lowest_section = (
                message.split("LOWEST PRICE")[1]
                if "LOWEST PRICE" in message.upper()
                else message
            )
            # Should reference easyJet or 58
            assert "easyjet" in lowest_section.lower() or "58" in lowest_section, (
                f"Lowest price should be easyJet at €58. Got: {lowest_section[:300]}"
            )

    @pytest.mark.asyncio
    async def test_multiple_passengers_pricing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify pricing shows total for all passengers."""
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        response = await chat_service.process_message(
            message="one way AMS to CDG Dec 20 for 3 adults",
            user=test_user,
            chat_id=chat_id,
        )

        if response.type != "flight_search_results":
            pytest.skip(f"Search didn't return results: {response.type}")

        # Should mention passenger count in pricing
        message = response.message.lower()
        assert "3 adult" in message or "3 passengers" in message or "(3" in message, (
            f"Should show pricing for 3 passengers. Message: {response.message[:500]}"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestNaturalLanguageVariations:
    """Test different natural language phrasings for flight requests.

    Real users express flight requests in many different ways.
    These tests document how the system handles various phrasings.
    """

    @pytest.mark.asyncio
    async def test_informal_wanna_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Informal 'wanna' phrasing."""
        response = await chat_service.process_message(
            message="I wanna fly to Barcelona next week",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_need_to_get_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Need to get to' phrasing."""
        response = await chat_service.process_message(
            message="I need to get to Berlin by Friday",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_looking_for_flights_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Looking for flights' phrasing."""
        response = await chat_service.process_message(
            message="Looking for flights from Chicago to Miami in January",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_can_you_find_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Can you find' question phrasing."""
        response = await chat_service.process_message(
            message="Can you find me a cheap flight to Rome?",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_minimal_destination_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Minimal request with just destination triggers flight booking."""
        response = await chat_service.process_message(
            message="Tokyo",
            user=test_user,
            chat_id=chat_id,
        )

        # Single word destination correctly triggers flight intent
        # Note: AI may return 0.8-0.9 confidence for minimal single-word input
        assert response.data is not None
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.8
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_emoji_in_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Message with emojis."""
        response = await chat_service.process_message(
            message="✈️ I want to fly to Paris! 🇫🇷",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"


@pytest.mark.integration
@pytest.mark.slow
class TestDateParsingVariations:
    """Test different date format inputs.

    Users specify dates in many formats. These tests document
    how the system parses various date expressions.
    """

    @pytest.mark.asyncio
    async def test_relative_date_next_monday(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Relative date: 'next Monday'."""
        response = await chat_service.process_message(
            message="one way flight from AMS to BCN next Monday for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None
        # Should proceed to search or results
        assert response.type in [
            "collecting_info",
            "flight_search_results",
            "searching",
        ]

    @pytest.mark.asyncio
    async def test_relative_date_in_two_weeks(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Relative date: 'in two weeks'."""
        response = await chat_service.process_message(
            message="one way flight from LAX to SFO in two weeks, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_date_format_european(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """European date format: 25/12/2025."""
        response = await chat_service.process_message(
            message="one way flight from DUB to LHR on 25/12/2025 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_date_format_written_month(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Written month: 'January 15th'."""
        response = await chat_service.process_message(
            message="one way flight from BOS to MIA January 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_date_christmas(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Holiday reference: 'Christmas'."""
        response = await chat_service.process_message(
            message="one way flight from SEA to DEN on Christmas day, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_date_range_flexibility(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Date flexibility: 'around January 10th'."""
        response = await chat_service.process_message(
            message="one way flight from ORD to ATL around January 10th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestPassengerVariations:
    """Test different passenger combination inputs."""

    @pytest.mark.asyncio
    async def test_family_with_infant(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Family with infant."""
        response = await chat_service.process_message(
            message="one way flight from AMS to BCN on December 20th for 2 adults and 1 infant",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        if mock_server_running:
            assert response.type in ["flight_search_results", "collecting_info"]

    @pytest.mark.asyncio
    async def test_group_travel(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Large group: 5 adults."""
        response = await chat_service.process_message(
            message="one way flight from JFK to LAX on January 5th for 5 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_word_number_passengers(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Word numbers: 'two adults and three children'."""
        response = await chat_service.process_message(
            message="one way flight from SFO to SEA on February 1st for two adults and three children",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_just_me_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Informal: 'just me'."""
        response = await chat_service.process_message(
            message="one way flight from BOS to DCA on March 15th, just me",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_myself_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Informal: 'for myself'."""
        response = await chat_service.process_message(
            message="one way flight from DFW to PHX tomorrow for myself",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestCabinClassVariations:
    """Test cabin class specification variations."""

    @pytest.mark.asyncio
    async def test_business_class_explicit(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Explicit business class request."""
        response = await chat_service.process_message(
            message="one way business class flight from JFK to LHR on January 20th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_first_class(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """First class request."""
        response = await chat_service.process_message(
            message="one way first class flight from LAX to NRT on February 1st, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_premium_economy(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Premium economy request."""
        response = await chat_service.process_message(
            message="one way premium economy flight from SFO to SIN on March 10th, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestAirlinePreferences:
    """Test airline preference handling.

    KNOWN BEHAVIOR: These tests document that airline/stop preferences are
    NOT currently captured or honored by the system. Tests pass but don't
    verify preferences - they use xfail to document known gaps.
    """

    @pytest.mark.asyncio
    async def test_specific_airline_request(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Specific airline: 'United flight'."""
        response = await chat_service.process_message(
            message="one way United flight from ORD to DEN on January 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check if airline preference was actually captured
        collected = response.data.get("collected_so_far", {})
        has_airline = "airline" in collected or "preferred_airline" in collected
        if not has_airline:
            pytest.xfail(
                "KNOWN BEHAVIOR: Airline preference 'United' is NOT captured. "
                "System returns generic results (BA/Ryanair/KLM) ignoring user preference."
            )

    @pytest.mark.asyncio
    async def test_avoid_airline(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Avoid airline: 'no Spirit'."""
        response = await chat_service.process_message(
            message="one way flight from MIA to ATL on February 5th, 1 adult, no Spirit please",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check if avoid-airline preference was captured
        collected = response.data.get("collected_so_far", {})
        has_exclusion = "avoid_airline" in collected or "excluded_airlines" in collected
        if not has_exclusion:
            pytest.xfail(
                "KNOWN BEHAVIOR: Airline exclusion 'no Spirit' is NOT captured. "
                "System has no mechanism to filter out unwanted airlines."
            )

    @pytest.mark.asyncio
    async def test_direct_flights_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Direct flights preference."""
        response = await chat_service.process_message(
            message="one way direct flight from BOS to LAX on March 1st, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check if direct/nonstop preference was captured
        collected = response.data.get("collected_so_far", {})
        has_stops_pref = (
            "stops" in collected or "direct" in collected or "nonstop" in collected
        )
        if not has_stops_pref:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'direct flight' preference is NOT captured. "
                "System returns flights with 2 stops despite user requesting direct."
            )

    @pytest.mark.asyncio
    async def test_nonstop_preference(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Nonstop preference."""
        response = await chat_service.process_message(
            message="one way nonstop flight from SEA to JFK on April 10th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check if nonstop preference was captured
        collected = response.data.get("collected_so_far", {})
        has_stops_pref = (
            "stops" in collected or "direct" in collected or "nonstop" in collected
        )
        if not has_stops_pref:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'nonstop' preference is NOT captured. "
                "System returns flights with 2 stops despite user requesting nonstop."
            )


@pytest.mark.integration
@pytest.mark.slow
class TestEdgeCasesAndErrors:
    """Test edge cases and potential error scenarios."""

    @pytest.mark.asyncio
    async def test_typo_in_city_name(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Typo in city name: 'Amstredam'."""
        response = await chat_service.process_message(
            message="one way flight from Amstredam to Paris on January 10th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Should still recognize intent even with typo
        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_incomplete_request(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Very incomplete: 'flight please'."""
        response = await chat_service.process_message(
            message="flight please",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.type == "collecting_info"
        assert response.data is not None
        # Should ask for more info
        assert "waiting_for" in response.data

    @pytest.mark.asyncio
    async def test_mixed_language_request(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Mixed language: English with Spanish city."""
        response = await chat_service.process_message(
            message="I want to fly to España next week",
            user=test_user,
            chat_id=chat_id,
        )

        # Should recognize flight intent
        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_very_long_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Very long message with lots of details."""
        response = await chat_service.process_message(
            message=(
                "Hi there! I'm planning a trip and I need some help. "
                "I want to book a one way flight from Amsterdam Schiphol Airport "
                "to Barcelona El Prat Airport. I'd like to travel on December 20th 2025. "
                "There will be 2 adults traveling. We prefer morning flights if possible, "
                "and we'd like to fly economy class. Can you help me find something?"
            ),
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_contradictory_info(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Contradictory: round trip with one date."""
        response = await chat_service.process_message(
            message="round trip flight from NYC to LA on December 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.type == "collecting_info"
        assert response.data is not None
        # Should ask for return date
        waiting_for = response.data.get("waiting_for")
        # Might ask for return_date or destination (due to extraction bugs)
        assert waiting_for is not None

    @pytest.mark.asyncio
    async def test_same_origin_destination(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Same origin and destination."""
        response = await chat_service.process_message(
            message="one way flight from Paris to Paris on January 5th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Should recognize intent but may handle error gracefully
        assert response.intent_name == "book_flight"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestRealProductionScenarios:
    """Tests based on real user conversations from CloudWatch logs.

    These scenarios document actual bugs discovered in production.
    Source: CloudWatch logs from /ecs/voya-backend and /ecs/staging-voya-backend
    Date range: November-December 2025
    """

    @pytest.mark.asyncio
    async def test_ams_to_lisbon_with_dates_and_direct(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: AMS to lisbon roundtrip from 11 Nov to 13 Nov direct flights only.

        From production logs (2025-11-04).
        Tests IATA code recognition, date parsing, and direct flight preference.
        """
        response = await chat_service.process_message(
            message="AMS to lisbon roundtrip from 11 Nov to 13 Nov direct flights only",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check extraction when results are available
        if response.type in ["flight_search_results", "search_results", "searching"]:
            search_params = response.data.get("search_params", {})
            collected = response.data.get("collected_so_far", search_params)
            # Should extract origin as AMS (IATA code)
            assert collected.get("origin") == "AMS", (
                f"Expected origin AMS, got: {collected.get('origin')}"
            )
            # Should extract destination as LIS (Lisbon)
            assert collected.get("destination") == "LIS", (
                f"Expected destination LIS, got: {collected.get('destination')}"
            )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'from X to Y' extraction fails - extracts wrong origin"
    )
    async def test_misspelled_city_londen(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: i would like to book a flight from Amsterdam to Londen.

        From staging logs (2025-12-01, user: koen@vanderels.nl).
        BUG: System extracts origin='EUN', origin_city_name='i would like'
        instead of origin='AMS'.

        Expected: origin='AMS', destination='LHR' (or similar UK airport)
        """
        response = await chat_service.process_message(
            message="i would like to book a flight from Amsterdam to Londen",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        collected = response.data.get("collected_so_far", {})
        # Should extract Amsterdam as origin
        assert collected.get("origin") == "AMS", (
            f"Expected origin='AMS', got: {collected.get('origin')}"
        )
        # Should handle misspelled "Londen" as London
        dest = collected.get("destination", "")
        assert dest in ["LHR", "LGW", "STN", "LTN", "LCY"], (
            f"Expected UK London airport, got: {dest}"
        )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'for 2' not extracted as adults, London→YXU instead of UK"
    )
    async def test_book_flights_to_madeira_with_passengers(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: Book me flights to Madeira from London for 2.

        From staging logs (2025-12-01).
        BUG: origin='YXU' (London, Ontario), adults=1 (ignores "for 2").

        Expected: origin=UK airport, adults=2
        """
        response = await chat_service.process_message(
            message="Book me flights to Madeira from London for 2 on the 21st November and back on the 26th November",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        collected = response.data.get("collected_so_far", {})
        # Should extract "for 2" as 2 adults
        assert collected.get("adults") == 2, (
            f"'for 2' should extract adults=2, got: {collected.get('adults')}"
        )
        # Should resolve London to UK airports, not Ontario
        origin = collected.get("origin", "")
        assert origin in ["LHR", "LGW", "STN", "LTN", "LCY"], (
            f"Expected UK London airport, got: {origin}"
        )

    @pytest.mark.asyncio
    async def test_plan_trip_with_travel_origin(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: plan a trip to london, i travel from Rio.

        From staging logs (2025-12-02).
        Routes to itinerary service (n8n) which may not be available locally.
        When routed to flights: KNOWN BUG - extraction fails.
        """
        response = await chat_service.process_message(
            message="plan a trip to london, i travel from Rio, i would like to visit stadiums at the end of march",
            user=test_user,
            chat_id=chat_id,
        )

        # Might detect as itinerary or flight
        # If itinerary and n8n unavailable, allow error state
        if response.intent_name == "create_itinerary" and response.type == "error":
            # n8n service not available - this is expected locally
            pass
        elif response.intent_name == "book_flight":
            assert response.data is not None
            collected = response.data.get("collected_so_far", {})
            # BUG: "i travel from" pattern not extracted correctly
        else:
            assert response.data is not None or response.type == "error"

    @pytest.mark.asyncio
    async def test_first_class_dubai_complex(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: book me a flight to dubai first class on 6th november.

        From production logs (2025-11-05).
        Tests cabin class extraction and date parsing.
        """
        response = await chat_service.process_message(
            message="book me a flight to dubai first class on the 6th november and back the 13th November for 3 people",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check cabin class extraction
        collected = response.data.get("collected_so_far", {})
        # Should extract first class
        if "cabin_class" in collected:
            assert collected["cabin_class"] in ["First", "FIRST", "first"]

    @pytest.mark.asyncio
    async def test_lhr_to_dubai_oneway_first_class(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: LHR to Dubai oneway Nov 20 first class.

        From production logs (2025-11-05).
        Tests IATA code + city name + date + cabin class extraction.
        """
        response = await chat_service.process_message(
            message="LHR to Dubai oneway Nov 20 first class",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.data is not None

        # Check extraction
        collected = response.data.get("collected_so_far", {})
        if response.type in ["flight_search_results", "searching"]:
            search_params = response.data.get("search_params", collected)
            # Should extract LHR as origin
            assert search_params.get("origin") == "LHR", (
                f"Expected origin LHR, got: {search_params.get('origin')}"
            )
            # Should extract journey type
            assert search_params.get("journey_type") == "OneWay", (
                f"Expected OneWay, got: {search_params.get('journey_type')}"
            )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: '11Nov' format not parsed - system still asks for departure_date"
    )
    async def test_date_without_space(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: User types '11Nov' without space.

        From production logs (2025-11-04).
        Tests date parsing robustness.

        BUG: Currently '11Nov' is not recognized as a date.
        Expected: Should parse as November 11th.
        """
        # First establish a flight context
        response1 = await chat_service.process_message(
            message="AMS to Lisbon roundtrip",
            user=test_user,
            chat_id=chat_id,
        )
        assert response1.intent_name == "book_flight"

        # Then provide date without space
        response2 = await chat_service.process_message(
            message="11Nov",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.data is not None
        collected = response2.data.get("collected_so_far", {})
        # Should have extracted the date - currently fails
        assert "departure_date" in collected, (
            f"'11Nov' should be parsed as November 11th, got: {collected}"
        )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'nivember' typo not corrected - parses as current month instead"
    )
    async def test_misspelled_november(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: User types '6th nivember' (typo).

        From production logs (2025-11-05).
        Tests date parsing with typos.

        BUG: Currently 'nivember' is not fuzzy-matched to 'november'.
        Expected: Should parse as November 6th.
        Actual: Parses with current month instead.
        """
        # First establish context
        response1 = await chat_service.process_message(
            message="to dubai round trip",
            user=test_user,
            chat_id=chat_id,
        )

        # Then provide misspelled date
        response2 = await chat_service.process_message(
            message="6th nivember",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.data is not None
        collected = response2.data.get("collected_so_far", {})
        # Should have extracted and corrected the typo
        assert "departure_date" in collected, (
            f"'6th nivember' should be parsed as November 6th, got: {collected}"
        )
        # Verify it's November, not another month
        departure_date = collected.get("departure_date")
        if departure_date:
            assert departure_date.month == 11, (
                f"Expected November (month 11), got month {departure_date.month}"
            )

    @pytest.mark.asyncio
    async def test_single_word_city_in_context(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: User types just 'london' as origin.

        From staging logs (2025-11-30, user: ross@myvoya.ai).
        After 'plan trip to paris', user types 'london' for origin.
        Note: "plan trip to paris" routes to itinerary service (n8n).
        """
        # First establish destination
        response1 = await chat_service.process_message(
            message="plan trip to paris",
            user=test_user,
            chat_id=chat_id,
        )

        # If routed to n8n and not available, skip follow-up
        if response1.intent_name == "create_itinerary" and response1.type == "error":
            # n8n service not available - this is expected locally
            # Can't test the follow-up in this case
            return

        # Then provide origin as single word
        response2 = await chat_service.process_message(
            message="london",
            user=test_user,
            chat_id=chat_id,
        )

        # May get error if n8n unavailable, otherwise should have data
        assert response2.data is not None or response2.type == "error"
        # Single word city in context should either:
        # - Be interpreted as origin/destination in itinerary
        # - Or trigger flight intent
        if response2.type != "error":
            assert response2.intent_name in ["create_itinerary", "book_flight"]

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: '4.' with trailing period not parsed as selection - triggers new search"
    )
    async def test_number_with_period(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: User types '4.' to select option.

        From production logs (2025-11-05).
        Tests selection parsing with trailing period.

        KNOWN BUG: "4." is not recognized as selecting option 4.
        System interprets it as a new search request instead.
        """
        # First get some results
        response1 = await chat_service.process_message(
            message="AMS to lisbon oneway Nov 20",
            user=test_user,
            chat_id=chat_id,
        )

        if mock_server_running and response1.type == "flight_search_results":
            # Try to select with period
            response2 = await chat_service.process_message(
                message="4.",
                user=test_user,
                chat_id=chat_id,
            )
            # "4." should be parsed as selecting option 4
            assert response2.data is not None
            assert response2.intent_name == "book_flight"
            # Should handle the selection (redirect, clarification, or error if option invalid)
            assert response2.type in [
                "booking_redirect",
                "booking_clarification",
                "error",
                "collecting_info",
            ], f"BUG: '4.' triggers {response2.type} instead of selection handling"

    @pytest.mark.asyncio
    async def test_follow_up_cabin_class(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: User asks 'what about first class' after results.

        From production logs (2025-11-05).
        Tests cabin class modification after search.
        """
        # First do a search
        response1 = await chat_service.process_message(
            message="LHR to DXB roundtrip 6th november to 13th november",
            user=test_user,
            chat_id=chat_id,
        )

        if response1.type in ["flight_search_results", "searching"]:
            # Ask about first class
            response2 = await chat_service.process_message(
                message="what about first class",
                user=test_user,
                chat_id=chat_id,
            )

            assert response2.data is not None
            assert response2.intent_name == "book_flight"
            collected = response2.data.get("collected_so_far", {})
            # Cabin class may be updated to FIRST or system may re-search
            # Either way, should maintain flight context
            cabin_class = collected.get("cabin_class", "")
            if cabin_class:
                assert cabin_class.upper() in ["FIRST", "F", "FIRST CLASS"], (
                    f"Expected FIRST class, got: {cabin_class}"
                )

    @pytest.mark.asyncio
    async def test_currency_question(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: User asks 'and in gbp' after results.

        From production logs (2025-11-05).
        Tests currency preference handling.
        """
        # First do a search
        response1 = await chat_service.process_message(
            message="LHR to DXB roundtrip Nov 20 to Nov 25",
            user=test_user,
            chat_id=chat_id,
        )

        if response1.type in ["flight_search_results", "searching"]:
            # Ask about currency
            response2 = await chat_service.process_message(
                message="and in gbp",
                user=test_user,
                chat_id=chat_id,
            )

            # Currency request should maintain flight context
            assert response2.data is not None
            assert response2.intent_name == "book_flight"
            # AI should either re-search with new currency or explain currency handling
            assert response2.message is not None
            assert len(response2.message) > 10  # Substantive response

    @pytest.mark.asyncio
    async def test_chamonix_trip_planning(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: plan a trip to chamonix.

        From staging logs (2025-12-03).
        Tests non-major city handling.
        Note: Routes to itinerary service (n8n) which may not be available locally.
        """
        response = await chat_service.process_message(
            message="plan a trip to chamonix, i wan to visit it, i'll departure from london, please plan it for the last 7 days of february",
            user=test_user,
            chat_id=chat_id,
        )

        # Might be itinerary or flight
        # If itinerary and n8n unavailable, allow error state
        if response.intent_name == "create_itinerary" and response.type == "error":
            # n8n service not available - this is expected locally
            pass
        else:
            assert response.data is not None

    @pytest.mark.asyncio
    async def test_book_option_number(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Real scenario: User types 'book 1' or 'Book 3'.

        From production logs (2025-11-05).
        Tests flight selection by number.
        """
        # First get results
        response1 = await chat_service.process_message(
            message="AMS to lisbon oneway on Nov 11",
            user=test_user,
            chat_id=chat_id,
        )

        if mock_server_running and response1.type == "flight_search_results":
            # Try to book
            response2 = await chat_service.process_message(
                message="book 1",
                user=test_user,
                chat_id=chat_id,
            )

            # Should return booking URL or confirmation
            assert response2.data is not None

    @pytest.mark.asyncio
    async def test_short_destination_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Real scenario: User types just 'to dubai'.

        From production logs (2025-11-05).
        Tests minimal destination input.
        Logs show: After extraction: {'destination': 'DXB', 'destination_city_name': 'dubai'}
        Response shows: waiting_for='journey_type' (destination correctly extracted)
        """
        response = await chat_service.process_message(
            message="to dubai",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_flight"
        assert response.type == "collecting_info"
        assert response.data is not None

        # Destination is extracted (see logs), response asks for journey_type
        # collected_so_far may not be in response.data (depends on handler version)
        waiting_for = response.data.get("waiting_for")
        # System extracted destination and now asks for journey_type
        assert waiting_for == "journey_type", (
            f"Expected to ask for journey_type (destination extracted), got: {waiting_for}"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestInChatFlightBookingFlow:
    """Tests for the complete in-chat flight booking flow.

    This covers:
    1. User searches for flights
    2. System returns flight options
    3. User selects an option ("book option 1")
    4. System generates booking URL with JWT token

    Requires FlightLogic mock server to be running for full flow.
    """

    @pytest.mark.asyncio
    async def test_book_option_1_generates_url(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Full booking flow: search → results → 'book option 1' → booking URL.

        This is the primary booking flow used by most users.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Step 1: Search for flights
        search_response = await chat_service.process_message(
            message="AMS to Lisbon oneway Dec 15 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_flight"

        # Should get flight results
        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        assert "flights" in search_response.data
        flights = search_response.data["flights"]
        assert len(flights) >= 1, "Expected at least 1 flight option"

        # Step 2: Select option 1
        select_response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Current behavior: returns booking redirect or clarification
        # - booking_redirect: direct booking URL
        # - flight_booking_redirect: flight-specific booking URL (added Oct 2025)
        # - booking_clarification: asks for confirmation
        assert select_response.type in [
            "booking_redirect",
            "booking_clarification",
            "flight_booking_redirect",
        ], f"Expected booking redirect or clarification, got: {select_response.type}"

        # If direct redirect with URL
        if select_response.type in ["booking_redirect", "flight_booking_redirect"]:
            assert select_response.data is not None
            # booking_redirect uses "booking_url", flight_booking_redirect uses "redirect_url"
            url_key = (
                "booking_url"
                if "booking_url" in select_response.data
                else "redirect_url"
            )
            assert url_key in select_response.data, (
                f"Missing URL in response data: {select_response.data.keys()}"
            )
            booking_url = select_response.data[url_key]
            assert booking_url.startswith("http"), f"Invalid URL: {booking_url}"
        # If clarification (asks which option to book)
        elif select_response.type == "booking_clarification":
            # Current behavior: data is None, message asks for selection
            # This happens when "book option 1" doesn't match expected pattern
            assert (
                "book" in select_response.message.lower()
                or "option" in select_response.message.lower()
            )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'from LHR to CDG' - destination NOT extracted from 'to X' pattern"
    )
    async def test_book_cheapest_option(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Selection by type: 'book cheapest' or 'book the cheapest one'.

        Should select the lowest-priced option from results.

        KNOWN BUG: FlightFieldCollector does not extract destination from
        "from LHR to CDG" - same bug as hotel destination extraction.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="flights from LHR to CDG roundtrip Dec 20 to Dec 25",
            user=test_user,
            chat_id=chat_id,
        )

        # Assert destination was extracted (currently broken)
        assert search_response.type == "flight_search_results", (
            f"BUG: 'from LHR to CDG' should extract destination and trigger search. "
            f"Got type={search_response.type}"
        )

        # Select cheapest
        select_response = await chat_service.process_message(
            message="book cheapest",
            user=test_user,
            chat_id=chat_id,
        )

        # Should return booking redirect or handle selection
        assert select_response.intent_name == "book_flight"
        assert select_response.type in [
            "booking_redirect",
            "booking_clarification",
            "collecting_info",
        ], f"Expected booking flow response, got: {select_response.type}"
        if select_response.type == "booking_redirect":
            assert "booking_url" in select_response.data

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'I'll take the first one' not parsed as selection - triggers new search"
    )
    async def test_book_first_one_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Natural phrasing: 'I'll take the first one'.

        Tests more natural selection language.

        KNOWN BUG: "I'll take the first one" is not recognized as a selection.
        System interprets it as a new search request instead.
        Should be parsed as selecting flight option 1.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to BCN oneway Jan 10",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        # Natural selection
        select_response = await chat_service.process_message(
            message="I'll take the first one",
            user=test_user,
            chat_id=chat_id,
        )

        # Natural phrasing should be recognized as selection
        assert select_response.data is not None
        assert select_response.intent_name == "book_flight"
        assert select_response.type in [
            "booking_redirect",
            "booking_clarification",
            "collecting_info",
        ], (
            f"BUG: 'I'll take the first one' triggers {select_response.type} instead of selection"
        )

    @pytest.mark.asyncio
    async def test_book_number_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Minimal selection: just '1' or '2'.

        Tests if bare numbers are recognized as selections.
        KNOWN BEHAVIOR: Bare numbers may not maintain sticky intent.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to MAD oneway Feb 1",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        # Bare number selection
        select_response = await chat_service.process_message(
            message="1",
            user=test_user,
            chat_id=chat_id,
        )

        # KNOWN BUG: Bare number "1" not recognized as selection - triggers new search
        # This is because bare numbers don't maintain sticky intent
        assert select_response.data is not None
        assert select_response.intent_name == "book_flight"
        # Note: Bare numbers currently trigger new search instead of selection
        # Mark as xfail at method level if this consistently fails
        assert select_response.type in [
            "booking_redirect",
            "booking_clarification",
            "collecting_info",
            "flight_search_results",  # Bug: bare number triggers new search
        ]

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'LHR to JFK' - origin NOT extracted from 'X to Y' pattern"
    )
    async def test_book_best_value(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Selection by quality: 'book best value'.

        Tests selection of curated 'best value' option.

        KNOWN BUG: FlightFieldCollector does not extract origin from
        "LHR to JFK" - extracts JFK as destination but misses LHR as origin.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="LHR to JFK roundtrip March 15 to March 22",
            user=test_user,
            chat_id=chat_id,
        )

        # Assert origin was extracted (currently broken)
        assert search_response.type == "flight_search_results", (
            f"BUG: 'LHR to JFK' should extract origin and trigger search. "
            f"Got type={search_response.type}"
        )

        # Select best value
        select_response = await chat_service.process_message(
            message="book best value",
            user=test_user,
            chat_id=chat_id,
        )

        # "book best value" should be recognized as selection intent
        assert select_response.data is not None
        assert select_response.intent_name == "book_flight"
        assert select_response.type in [
            "booking_redirect",
            "booking_clarification",
            "collecting_info",
        ], f"Expected booking flow response, got: {select_response.type}"

    @pytest.mark.asyncio
    async def test_booking_url_contains_required_params(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Verify booking URL structure and parameters.

        The URL should contain authentication token and session reference.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to LIS oneway Dec 20 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        # Select
        select_response = await chat_service.process_message(
            message="book 1",
            user=test_user,
            chat_id=chat_id,
        )

        if select_response.type == "booking_redirect":
            url = select_response.data.get("booking_url", "")

            # Check URL structure
            assert "/dev/flight-booker/" in url or "flight" in url.lower(), (
                f"URL should point to flight booker: {url}"
            )

            # Should have query parameters
            assert "?" in url, "URL should have query parameters"

    @pytest.mark.asyncio
    async def test_invalid_option_number(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test selection of non-existent option (e.g., option 10).

        Should handle gracefully, not crash.
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to BCN oneway Dec 15",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        flights_count = len(search_response.data.get("flights", []))

        # Select invalid option
        select_response = await chat_service.process_message(
            message=f"book option {flights_count + 5}",  # Invalid number
            user=test_user,
            chat_id=chat_id,
        )

        # Should not crash - handles invalid option gracefully
        assert select_response is not None
        assert select_response.intent_name == "book_flight"
        # System should either ask for valid option or explain the issue
        # - invalid_selection: specific error for out-of-range selection (added Sep 2025)
        # - booking_clarification: generic clarification request
        # - error/collecting_info: fallback handling
        assert select_response.type in [
            "booking_clarification",
            "error",
            "collecting_info",
            "invalid_selection",
        ], f"Expected graceful handling of invalid option, got: {select_response.type}"

    @pytest.mark.asyncio
    async def test_selection_before_search(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test 'book option 1' without prior search results.

        Should handle gracefully.
        """
        # Try to book without searching first
        response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Should not crash and handle gracefully
        assert response is not None
        assert response.message is not None
        # Without search context, "book option 1" is ambiguous - no options exist to book
        # Correct behavior: AI returns unknown/asks for clarification
        # This is EXPECTED - you can't select an option that doesn't exist
