"""
Hotel booking conversation integration tests.

These are characterization tests that capture current behavior before refactoring.
They run against the real Gemini API with specific assertions on response structure.

Run with: pytest tests/integration_tests/ai/test_hotel_conversation.py -v -m integration

NOTE: Tests that trigger hotel searches require FlightLogic credentials to be configured.
Without credentials, tests verify error handling behavior.
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService


@pytest.mark.integration
@pytest.mark.slow
class TestHotelConversationHappyPath:
    """Happy path hotel booking conversations.

    Uses cities with fixture data:
    - London: The Savoy (€650, 5★), Premier Inn (€95, 3★), citizenM (€175, 4★)
    - Amsterdam: Hotel V Nesplein (€185), The Dylan (€425), citizenM (€135)
    - Paris: Hôtel Plaza Athénée (€890), Hotel Le Marais (€145), Hôtel des Arts (€98)
    """

    @pytest.mark.asyncio
    async def test_complete_booking_single_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete hotel booking request in one message.

        London fixture hotels:
        - The Savoy: €650/night, 5★, 9.3 rating
        - Premier Inn London City: €95/night, 3★, 8.1 rating
        - citizenM Tower of London: €175/night, 4★, 8.7 rating
        """
        response = await chat_service.process_message(
            message="Book a hotel in London from December 23 to December 27 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure assertions
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 20

        # Intent assertions
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock server is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
            ], f"Expected hotel_results with mock server, got: {response.type}"

            # Verify fixture data when results are returned
            if response.type == "hotel_results" and response.data:
                hotels = response.data.get("hotels", [])
                if hotels:
                    # Curation shows 2-3 hotels (Best Value + Highest Rated + optional)
                    assert 2 <= len(hotels) <= 3, (
                        f"London fixture has 3 hotels, curation shows 2-3, got {len(hotels)}"
                    )
                    # Verify returned hotels are from fixture
                    hotel_names = {
                        h.get("hotel_name", h.get("name", "")) for h in hotels
                    }
                    expected_names = {
                        "The Savoy",
                        "Premier Inn London City",
                        "citizenM Tower of London",
                    }
                    # At least some expected hotels should appear
                    assert (
                        hotel_names <= expected_names or hotel_names & expected_names
                    ), f"Expected London fixture hotels, got {hotel_names}"
        else:
            # Without mock, allow error states
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "error",
                "searching",
                "search_error",
            ]
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelConversationMultiTurn:
    """Multi-turn hotel booking conversations (field collection)."""

    @pytest.mark.asyncio
    async def test_field_collection_flow(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Test multi-turn conversation collecting fields one by one.

        Verifies the field collection state machine:
        Turn 1: Establish intent with destination -> asks for check_in_date
        Turn 2: Provide check_in_date -> asks for check_out_date
        Turn 3: Provide check_out_date -> asks for guests or triggers search
        """
        # Turn 1: Intent with destination only
        response1 = await chat_service.process_message(
            message="I need a hotel in Amsterdam",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response1.intent_name == "book_hotel"
        assert response1.confidence >= 0.9

        # State assertions - should be collecting info
        assert response1.type == "collecting_info"
        assert response1.data is not None
        assert "waiting_for" in response1.data

        # Should be asking for check-in date (destination was provided)
        waiting_for_1 = response1.data.get("waiting_for")
        assert waiting_for_1 == "check_in_date"

        # Verify collected_so_far contains destination with correct value
        collected = response1.data.get("collected_so_far", {})
        assert "destination" in collected, "destination should be in collected_so_far"
        assert "amsterdam" in collected.get("destination", "").lower(), (
            f"destination should contain 'Amsterdam', got: {collected.get('destination')}"
        )

        # Turn 2: Provide check-in date
        response2 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )

        # Should maintain intent and continue collecting
        assert response2.intent_name == "book_hotel"
        assert response2.type == "collecting_info"
        assert response2.data is not None

        # Should have progressed to check_out_date
        waiting_for_2 = response2.data.get("waiting_for")
        assert waiting_for_2 == "check_out_date"

        # Verify check_in_date was correctly extracted
        collected_2 = response2.data.get("collected_so_far", {})
        assert "check_in_date" in collected_2, "check_in_date should be collected"
        # Should be December 20, 2025 (next occurrence)
        check_in = collected_2.get("check_in_date")
        if hasattr(check_in, "month"):  # datetime.date object
            assert check_in.month == 12, (
                f"check_in month should be 12, got {check_in.month}"
            )
            assert check_in.day == 20, f"check_in day should be 20, got {check_in.day}"

        # Turn 3: Provide check-out date
        response3 = await chat_service.process_message(
            message="December 25th",
            user=test_user,
            chat_id=chat_id,
        )

        # Should continue flow
        assert response3.intent_name == "book_hotel"
        assert response3.data is not None

        # Should ask for guests or be searching
        assert response3.type in [
            "collecting_info",
            "searching",
            "search_results",
            "error",
        ]

        # Verify check_out_date was correctly extracted
        collected_3 = response3.data.get("collected_so_far", {})
        if "check_out_date" in collected_3:
            check_out = collected_3.get("check_out_date")
            if hasattr(check_out, "month"):  # datetime.date object
                assert check_out.month == 12, (
                    f"check_out month should be 12, got {check_out.month}"
                )
                assert check_out.day == 25, (
                    f"check_out day should be 25, got {check_out.day}"
                )


@pytest.mark.integration
@pytest.mark.slow
class TestHotelConversationWithVariations:
    """Hotel booking with various input patterns."""

    @pytest.mark.asyncio
    async def test_duration_pattern(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test 'for 5 nights' pattern - should calculate check-out date."""
        response = await chat_service.process_message(
            message="hotel in Paris for 5 nights starting December 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
            ], f"Expected non-error state with mock server, got: {response.type}"
        else:
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
                "error",
            ]
        assert response.data is not None

        # If still collecting, verify what field is being requested
        if response.type == "collecting_info":
            waiting_for = response.data.get("waiting_for")
            # Should have processed dates, asking for something else
            assert waiting_for is not None

    @pytest.mark.asyncio
    async def test_multiple_rooms(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test booking with multiple rooms."""
        response = await chat_service.process_message(
            message="I need 2 rooms in Barcelona from January 10 to January 15 for 4 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # State assertions - stronger when mock is running
        if mock_server_running:
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
            ], f"Expected non-error state with mock server, got: {response.type}"
        else:
            assert response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
                "error",
            ]
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelSelectionPatterns:
    """Test different hotel selection patterns after search results.

    Uses Tokyo which has fixture data:
    - Park Hyatt Tokyo: €580/night, 5★, 9.2 rating
    - Shinjuku Granbell Hotel: €145/night, 4★, 8.4 rating
    - 9 Hours Shinjuku: €35/night, 2★, 7.9 rating (cheapest)
    """

    async def _get_search_results(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Helper to trigger a search and get results.

        Uses Tokyo which has fixture data for deterministic testing.
        """
        return await chat_service.process_message(
            message="hotel in Tokyo from March 1 to March 7, 2 adults",
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
        """Select hotel by 'option 1'."""
        # Get search results first
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        # Verify search response
        assert search_response.intent_name == "book_hotel"
        assert search_response.data is not None

        # With mock server, search should succeed
        if mock_server_running:
            assert search_response.type in [
                "collecting_info",
                "search_results",
                "hotel_results",
                "searching",
            ], f"Search should succeed with mock, got: {search_response.type}"

        # Attempt selection (option 1 works with any number of results)
        response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_hotel"

        # With mock server, selection should succeed
        if mock_server_running and search_response.type in [
            "search_results",
            "hotel_results",
        ]:
            assert response.data is not None
            message_lower = response.message.lower()
            assert any(
                word in message_lower
                for word in ["selected", "booking", "confirm", "option", "proceed"]
            ), f"Expected selection success message, got: {response.message[:100]}"
        else:
            # Without mock or if search failed, allow various responses
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
                    "hotel",
                ]
            )

    @pytest.mark.asyncio
    async def test_selection_highest_rated(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Select highest rated hotel."""
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_hotel"

        response = await chat_service.process_message(
            message="book the highest rated",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_hotel"
        assert len(response.message) > 10

    @pytest.mark.asyncio
    async def test_selection_first_one(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Select first hotel."""
        search_response = await self._get_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_hotel"

        response = await chat_service.process_message(
            message="book the first one",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name == "book_hotel"
        assert len(response.message) > 10


@pytest.mark.integration
@pytest.mark.slow
class TestHotelNaturalLanguageVariations:
    """Test different natural language phrasings for hotel requests.

    Real users express hotel requests in many different ways.
    These tests document how the system handles various phrasings.
    """

    @pytest.mark.asyncio
    async def test_place_to_stay_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Place to stay' phrasing."""
        response = await chat_service.process_message(
            message="I need a place to stay in Rome next week",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_accommodation_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Accommodation' phrasing."""
        response = await chat_service.process_message(
            message="Looking for accommodation in Berlin for 3 nights",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_somewhere_to_sleep_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Informal 'somewhere to sleep' phrasing."""
        response = await chat_service.process_message(
            message="I need somewhere to sleep in Madrid this weekend",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_can_you_find_hotel_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Can you find' question phrasing."""
        response = await chat_service.process_message(
            message="Can you find me a nice hotel in Vienna?",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_want_to_book_room_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Book a room' phrasing."""
        response = await chat_service.process_message(
            message="I want to book a room in Prague for next Friday",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="LLM variability: 'staying' phrasing inconsistent (60% fail rate)",
        strict=False,
    )
    async def test_staying_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """'Staying in' phrasing correctly identifies hotel intent.

        KNOWN BEHAVIOR: LLM sometimes interprets "staying" differently:
        - Sometimes extracts destination correctly (Athens)
        - Sometimes asks clarifying question instead

        Failure Rate: 60% (3/5 runs in characterization testing)
        """
        response = await chat_service.process_message(
            message="I'll be staying in Athens from January 5 to 10",
            user=test_user,
            chat_id=chat_id,
        )

        # AI correctly identifies hotel intent despite " to " in date range
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelDateVariations:
    """Test different date and duration inputs for hotels."""

    @pytest.mark.asyncio
    async def test_nights_duration(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Duration: 'for 3 nights'."""
        response = await chat_service.process_message(
            message="hotel in Dublin for 3 nights starting Monday, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_week_duration(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Duration: 'for a week'."""
        response = await chat_service.process_message(
            message="hotel in Lisbon for a week starting January 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_weekend_stay(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Weekend reference."""
        response = await chat_service.process_message(
            message="hotel in Brussels this weekend for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_new_years_eve(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Holiday reference: New Year's Eve."""
        response = await chat_service.process_message(
            message="hotel in Sydney for New Year's Eve, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_date_range_to_format(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Date range with 'to': 'March 5 to March 10'."""
        response = await chat_service.process_message(
            message="hotel in Copenhagen March 5 to March 10, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_checkout_before_noon(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Specific checkout time mention."""
        response = await chat_service.process_message(
            message="hotel in Munich from Dec 20 to Dec 23 for 1 adult, need late checkout",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelGuestVariations:
    """Test different guest and room configurations."""

    @pytest.mark.asyncio
    async def test_family_with_children(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Family with children."""
        response = await chat_service.process_message(
            message="hotel in Orlando from Dec 20 to Dec 27 for 2 adults and 2 children",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_solo_traveler(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Solo traveler: 'just me'."""
        response = await chat_service.process_message(
            message="hotel in Stockholm for 2 nights next week, just me",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_couple(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Couple: 'for two'."""
        response = await chat_service.process_message(
            message="romantic hotel in Venice for two, February 14th for 2 nights",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_multiple_rooms_explicit(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Multiple rooms explicit."""
        response = await chat_service.process_message(
            message="3 rooms in Frankfurt from Jan 10 to Jan 12 for 6 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_group_booking(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Group booking."""
        response = await chat_service.process_message(
            message="hotel for a group of 8 people in Edinburgh next month",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelLocationVariations:
    """Test different location specification patterns."""

    @pytest.mark.asyncio
    async def test_near_landmark(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Near landmark: 'near the Eiffel Tower'."""
        response = await chat_service.process_message(
            message="hotel near the Eiffel Tower for 2 nights, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_near_airport(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Near airport."""
        response = await chat_service.process_message(
            message="hotel near Heathrow airport for tomorrow night, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_city_center(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """City center preference."""
        response = await chat_service.process_message(
            message="hotel in the center of Milan from March 1 to March 3, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_neighborhood(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Specific neighborhood."""
        response = await chat_service.process_message(
            message="hotel in Soho, London for this weekend, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_beachfront(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Beachfront location."""
        response = await chat_service.process_message(
            message="beachfront hotel in Miami for 5 nights in January, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestHotelPreferences:
    """Test hotel preference and amenity requests.

    KNOWN BEHAVIOR: These tests document that hotel preferences (star rating,
    amenities, budget) are NOT currently captured by the field collector.
    Tests pass but don't verify preferences - they use xfail to document known gaps.

    Uses cities with fixture data:
    - Dubai: Burj Al Arab (€1850, 5★), Rove Downtown (€85, 3★), Atlantis (€520, 5★)
    - Bangkok: Mandarin Oriental (€425, 5★), Ibis (€42, 3★), Lub d (€18, 2★)
    - Monaco: Hôtel de Paris (€1250, 5★), Fairmont (€385, 4★), Novotel (€215, 4★)
    - Las Vegas: Bellagio (€285, 5★), LINQ (€95, 4★), Circus Circus (€45, 3★)
    - Portland: The Nines (€275, 5★), Ace Hotel (€165, 4★), Jupiter (€95, 3★)
    - Tokyo: Park Hyatt (€580, 5★), Shinjuku Granbell (€145, 4★), 9 Hours (€35, 2★)
    """

    @pytest.mark.asyncio
    async def test_star_rating(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Star rating preference.

        Dubai fixture has two 5★ hotels:
        - Burj Al Arab Jumeirah: €1850/night
        - Atlantis The Palm: €520/night
        """
        response = await chat_service.process_message(
            message="5 star hotel in Dubai from Feb 10 to Feb 15, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if star rating was actually captured
        collected = response.data.get("collected_so_far", {})
        has_star_rating = "star_rating" in collected or "stars" in collected
        if not has_star_rating:
            pytest.xfail(
                "KNOWN BEHAVIOR: Star rating preference '5 star' is NOT captured. "
                "HotelFieldCollector does not extract star rating from user input."
            )

    @pytest.mark.asyncio
    async def test_budget_preference(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Budget preference.

        Bangkok fixture has budget option:
        - Lub d Bangkok Silom: €18/night, 2★, 8.5 rating (cheapest)
        """
        response = await chat_service.process_message(
            message="cheap hotel in Bangkok for a week, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if budget preference was captured
        collected = response.data.get("collected_so_far", {})
        has_budget = (
            "budget" in collected or "price_range" in collected or "cheap" in collected
        )
        if not has_budget:
            pytest.xfail(
                "KNOWN BEHAVIOR: Budget preference 'cheap' is NOT captured. "
                "System has no mechanism to filter by price range."
            )

    @pytest.mark.asyncio
    async def test_luxury_preference(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Luxury preference.

        Monaco fixture has luxury options:
        - Hôtel de Paris Monte-Carlo: €1250/night, 5★, 9.4 rating
        - Fairmont Monte Carlo: €385/night, 4★, 8.8 rating
        """
        response = await chat_service.process_message(
            message="luxury hotel in Monaco for 3 nights, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if luxury preference was captured
        collected = response.data.get("collected_so_far", {})
        has_luxury = (
            "luxury" in collected
            or "category" in collected
            or "star_rating" in collected
        )
        if not has_luxury:
            pytest.xfail(
                "KNOWN BEHAVIOR: Luxury preference is NOT captured. "
                "System does not distinguish luxury vs budget hotels."
            )

    @pytest.mark.asyncio
    async def test_with_pool(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Amenity: pool.

        Las Vegas fixture - all have pools:
        - Bellagio: €285/night, 5★, 9.0 rating (has Pool in facilities)
        - LINQ: €95/night, 4★, 8.2 rating (has Pool in facilities)
        - Circus Circus: €45/night, 3★, 7.1 rating (has Pool in facilities)
        """
        response = await chat_service.process_message(
            message="hotel with pool in Las Vegas from Dec 20 to Dec 25, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if pool amenity was captured
        collected = response.data.get("collected_so_far", {})
        has_amenity = "amenities" in collected or "pool" in collected
        if not has_amenity:
            pytest.xfail(
                "KNOWN BEHAVIOR: Pool amenity preference is NOT captured. "
                "HotelFieldCollector does not extract amenity requirements."
            )

    @pytest.mark.asyncio
    async def test_breakfast_included(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Amenity: breakfast.

        Tokyo fixture:
        - Park Hyatt Tokyo: €580/night, 5★, has Restaurant (not explicit breakfast)
        - Shinjuku Granbell: €145/night, 4★, has Restaurant
        - 9 Hours Shinjuku: €35/night, 2★, capsule hotel (no breakfast)
        """
        response = await chat_service.process_message(
            message="hotel with breakfast included in Tokyo, Jan 5-10, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if breakfast amenity was captured
        collected = response.data.get("collected_so_far", {})
        has_breakfast = "breakfast" in collected or "amenities" in collected
        if not has_breakfast:
            pytest.xfail(
                "KNOWN BEHAVIOR: Breakfast preference is NOT captured. "
                "System does not filter by meal inclusion."
            )

    @pytest.mark.asyncio
    async def test_pet_friendly(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Pet-friendly preference.

        Portland fixture - has pet-friendly options:
        - The Nines Portland: €275/night, 5★ (Pet-friendly in facilities)
        - Jupiter Hotel: €95/night, 3★ (Pet-friendly in facilities)
        """
        response = await chat_service.process_message(
            message="pet-friendly hotel in Portland for 4 nights, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Check if pet-friendly preference was captured
        collected = response.data.get("collected_so_far", {})
        has_pet_pref = (
            "pet_friendly" in collected
            or "pets" in collected
            or "amenities" in collected
        )
        if not has_pet_pref:
            pytest.xfail(
                "KNOWN BEHAVIOR: Pet-friendly preference is NOT captured. "
                "System has no mechanism to filter pet-friendly hotels."
            )


@pytest.mark.integration
@pytest.mark.slow
class TestHotelEdgeCases:
    """Test edge cases and error scenarios for hotels."""

    @pytest.mark.asyncio
    async def test_typo_in_city(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Typo in city name."""
        response = await chat_service.process_message(
            message="hotel in Amstredam from Dec 20 to Dec 25, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        # Should still recognize intent even with typo
        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_minimal_request(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Minimal: 'hotel please'."""
        response = await chat_service.process_message(
            message="hotel please",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.type == "collecting_info"
        assert response.data is not None
        assert "waiting_for" in response.data

    @pytest.mark.asyncio
    async def test_just_city_name(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Just city name as input."""
        response = await chat_service.process_message(
            message="Paris hotel",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.type == "collecting_info"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_same_checkin_checkout(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Same check-in and check-out date (day trip?)."""
        response = await chat_service.process_message(
            message="hotel in London on December 25th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Should recognize intent but ask for checkout
        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_very_long_stay(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Very long stay: 30 days."""
        response = await chat_service.process_message(
            message="hotel in Bali for 30 days starting January 1st, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_mixed_language(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Mixed language: English with foreign city spelling."""
        response = await chat_service.process_message(
            message="hotel in München for 2 nights, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_emoji_message(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Message with emojis."""
        response = await chat_service.process_message(
            message="🏨 Need a hotel in NYC! 🗽 Next week for 3 nights",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestInChatHotelBookingFlow:
    """Tests for the complete in-chat hotel booking flow.

    This covers:
    1. User searches for hotels
    2. System returns hotel options
    3. User selects an option ("book option 1")
    4. System generates booking URL with JWT token

    Uses cities with fixture data for deterministic testing:
    - Amsterdam: Hotel V Nesplein (€185), The Dylan (€425), citizenM (€135)
    - London: The Savoy (€650), Premier Inn (€95), citizenM (€175)
    - Paris: Hôtel Plaza Athénée (€890), Hotel Le Marais (€145), Hôtel des Arts (€98)
    - Barcelona: Hotel Arts (€385), Hotel Praktik Rambla (€125), Generator (€45)
    """

    @pytest.mark.asyncio
    async def test_hotel_search_returns_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Search for hotels should return results or collecting_info.

        Amsterdam fixture hotels:
        - Hotel V Nesplein: €185/night, 4★, 8.9 rating
        - The Dylan Amsterdam: €425/night, 5★, 9.2 rating
        - citizenM Amsterdam City: €135/night, 4★, 8.5 rating (cheapest)
        """
        response = await chat_service.process_message(
            message="hotel in Amsterdam Dec 15 to Dec 18 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Stronger assertions when mock server is running
        if mock_server_running:
            # Should get hotel results (not errors)
            assert response.type in [
                "hotel_results",
                "search_results",
                "collecting_info",
                "searching",
            ], f"Expected non-error state with mock server, got: {response.type}"

            # Verify fixture data when results are returned
            if response.type == "hotel_results" and response.data:
                hotels = response.data.get("hotels", [])
                if hotels:
                    assert len(hotels) == 3, (
                        f"Amsterdam fixture has 3 hotels, got {len(hotels)}"
                    )
        else:
            # Without mock, allow error states
            assert response.type in [
                "hotel_results",
                "search_results",
                "collecting_info",
                "searching",
                "error",
                "search_error",
            ]

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'hotel in London' - destination NOT extracted. System asks 'Which city?'"
    )
    async def test_book_hotel_option_1(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Full booking flow: search → results → 'book option 1' → booking URL.

        KNOWN BUG: HotelFieldCollector does not extract destination from
        "hotel in London Dec 20 to Dec 23" - it extracts dates/adults but
        NOT the city name, causing system to ask "Which city would you like to stay in?"
        """
        # Search
        search_response = await chat_service.process_message(
            message="hotel in London Dec 20 to Dec 23 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        assert search_response.data is not None

        # Verify destination was extracted (currently broken)
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in London' should extract destination. "
            f"collected_so_far={collected}"
        )

        # Should trigger search when all required fields present
        assert search_response.type in [
            "hotel_results",
            "search_results",
            "searching",
        ], f"Expected search to trigger, got type={search_response.type}"

        # If we got results, try to book
        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="book option 1",
                user=test_user,
                chat_id=chat_id,
            )

            # Should return booking redirect or handle selection
            assert select_response is not None
            assert select_response.data is not None
            assert select_response.type == "booking_redirect", (
                f"Expected booking_redirect, got {select_response.type}"
            )
            assert "booking_url" in select_response.data

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'hotel in Paris' - destination NOT extracted. System asks 'Which city?'"
    )
    async def test_book_cheapest_hotel(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Selection by price: 'book cheapest'.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        # Search
        search_response = await chat_service.process_message(
            message="hotel in Paris Jan 10 to Jan 12 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Paris' should extract destination. collected={collected}"
        )

        assert search_response.type in [
            "hotel_results",
            "search_results",
            "searching",
        ], f"Expected search, got type={search_response.type}"

        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="book cheapest",
                user=test_user,
                chat_id=chat_id,
            )
            assert select_response is not None
            assert select_response.data is not None

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: 'hotel in Barcelona' - destination NOT extracted")
    async def test_book_highest_rated_hotel(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Selection by rating: 'book highest rated'.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        search_response = await chat_service.process_message(
            message="hotel in Barcelona Feb 5 to Feb 8 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Barcelona' should extract destination. collected={collected}"
        )

        assert search_response.type in ["hotel_results", "search_results", "searching"]

        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="book highest rated",
                user=test_user,
                chat_id=chat_id,
            )
            assert select_response is not None
            assert select_response.data is not None

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: 'hotel in Rome' - destination NOT extracted")
    async def test_book_best_value_hotel(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Selection by value: 'book best value'.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        search_response = await chat_service.process_message(
            message="hotel in Rome March 1 to March 4 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Rome' should extract destination. collected={collected}"
        )

        assert search_response.type in ["hotel_results", "search_results", "searching"]

        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="book best value",
                user=test_user,
                chat_id=chat_id,
            )
            assert select_response is not None
            assert select_response.data is not None

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: 'hotels in Madrid' - destination NOT extracted")
    async def test_hotel_selection_natural_phrasing(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Natural phrasing: 'I'll take the second hotel'.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        search_response = await chat_service.process_message(
            message="hotels in Madrid April 15 to April 18 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotels in Madrid' should extract destination. collected={collected}"
        )

        assert search_response.type in ["hotel_results", "search_results", "searching"]

        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="I'll take the second hotel",
                user=test_user,
                chat_id=chat_id,
            )
            assert select_response is not None
            assert select_response.data is not None

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: 'hotel in Vienna' - destination NOT extracted")
    async def test_hotel_booking_url_structure(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify hotel booking URL structure when booking completes.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        search_response = await chat_service.process_message(
            message="hotel in Vienna May 20 to May 23 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Vienna' should extract destination. collected={collected}"
        )

        assert search_response.type in ["hotel_results", "search_results", "searching"]

        if search_response.type in ["hotel_results", "search_results"]:
            select_response = await chat_service.process_message(
                message="book 1",
                user=test_user,
                chat_id=chat_id,
            )

            assert select_response.type == "booking_redirect", (
                f"Expected booking_redirect, got {select_response.type}"
            )
            url = select_response.data.get("booking_url", "")
            assert "hotel" in url.lower(), f"URL should point to hotel booker: {url}"
            assert "?" in url, "URL should have query parameters"

    @pytest.mark.asyncio
    async def test_hotel_selection_before_search(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test 'book option 1' without prior hotel search.

        Without prior search context, 'book option 1' is ambiguous.
        AI defaults to flight intent (more common booking type).
        """
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

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: 'hotel in Berlin' - destination NOT extracted")
    async def test_multi_room_hotel_booking_flow(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Multi-room hotel booking: 2 rooms for different guests.

        KNOWN BUG: Same as test_book_hotel_option_1 - destination not extracted.
        """
        search_response = await chat_service.process_message(
            message="hotel in Berlin June 1 to June 5 for 4 adults, 2 rooms",
            user=test_user,
            chat_id=chat_id,
        )

        assert search_response.intent_name == "book_hotel"
        assert search_response.data is not None

        # Verify destination was extracted
        collected = search_response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Berlin' should extract destination. collected={collected}"
        )

        # Verify multi-room was extracted
        assert collected.get("rooms") == 2, (
            f"Should extract '2 rooms'. collected={collected}"
        )
        assert collected.get("adults") == 4, (
            f"Should extract '4 adults'. collected={collected}"
        )

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="BUG: 'hotel in Lisbon' - destination NOT extracted, children ages NOT extracted"
    )
    async def test_hotel_with_children(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Hotel booking with children included.

        KNOWN BUGS:
        1. Destination not extracted from "hotel in Lisbon"
        2. Children ages "5 and 8" not extracted
        """
        response = await chat_service.process_message(
            message="hotel in Lisbon July 10 to July 15 for 2 adults and 2 children ages 5 and 8",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.data is not None

        # Verify destination was extracted
        collected = response.data.get("collected_so_far", {})
        assert "destination" in collected, (
            f"BUG: 'hotel in Lisbon' should extract destination. collected={collected}"
        )

        # Verify children and ages were extracted
        assert collected.get("children") == 2, (
            f"Should extract '2 children'. collected={collected}"
        )
        child_ages = collected.get("child_ages", [])
        assert 5 in child_ages, f"Should extract age 5. child_ages={child_ages}"
        assert 8 in child_ages, f"Should extract age 8. child_ages={child_ages}"
