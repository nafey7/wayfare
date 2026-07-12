"""
Intent recognition integration tests.

These are characterization tests that capture current behavior before refactoring.
They run against the real Gemini API with specific assertions on response structure.

Run with: pytest tests/integration_tests/ai/test_intent_recognition.py -v -m integration
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService


@pytest.mark.integration
@pytest.mark.slow
class TestClearIntentRecognition:
    """Test clear, unambiguous intent recognition."""

    @pytest.mark.asyncio
    async def test_clear_flight_intent(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Explicit flight booking request."""
        response = await chat_service.process_message(
            message="I want to book a flight",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure assertions
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 0

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9  # High confidence for clear intent

        # State assertions - should be collecting info
        assert response.type == "collecting_info"
        assert response.data is not None
        assert "waiting_for" in response.data

    @pytest.mark.asyncio
    async def test_clear_hotel_intent(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Explicit hotel booking request."""
        response = await chat_service.process_message(
            message="I need a hotel room",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure assertions
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 0

        # Intent assertions
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9  # High confidence for clear intent

        # State assertions - should be collecting info
        assert response.type == "collecting_info"
        assert response.data is not None
        assert "waiting_for" in response.data

    @pytest.mark.asyncio
    async def test_flight_with_destination(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Flight intent with destination included."""
        response = await chat_service.process_message(
            message="I need to fly to Paris",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_flight"
        assert response.confidence >= 0.9

        # State assertions
        assert response.type == "collecting_info"
        assert response.data is not None

        # Should be collecting next required field
        waiting_for = response.data.get("waiting_for")
        assert waiting_for is not None

        # KNOWN BUG: Destination from "fly to Paris" is NOT being extracted
        # The field collector fails to parse destination from this phrase pattern.
        # Current behavior: asks for journey_type, destination not in collected_so_far
        collected = response.data.get("collected_so_far", {})
        if "destination" in collected:
            # If bug is fixed, verify correct extraction
            dest_value = collected.get("destination", "")
            assert any(x in dest_value.upper() for x in ["PARIS", "CDG", "ORY"]), (
                f"destination should be Paris airport, got: {dest_value}"
            )
        else:
            # BUG: destination not extracted - document current broken behavior
            # TODO: Fix flight_field_collector.py to extract destination from "fly to X"
            assert waiting_for == "journey_type", (
                f"With destination bug, should ask for journey_type first, got: {waiting_for}"
            )

    @pytest.mark.asyncio
    async def test_hotel_with_location(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Hotel intent with location included."""
        response = await chat_service.process_message(
            message="I need accommodation in London",
            user=test_user,
            chat_id=chat_id,
        )

        # Intent assertions
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # State assertions
        assert response.type == "collecting_info"
        assert response.data is not None

        # Should have collected destination and be asking for next field
        waiting_for = response.data.get("waiting_for")
        assert waiting_for is not None
        # Location was provided, so should ask for dates or guests
        assert waiting_for in [
            "check_in_date",
            "check_out_date",
            "destination",
            "adults",
        ]

        # Verify destination was extracted correctly
        collected = response.data.get("collected_so_far", {})
        assert "destination" in collected, "destination should be in collected_so_far"
        assert "london" in collected.get("destination", "").lower(), (
            f"destination should contain 'London', got: {collected.get('destination')}"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestKnownIntentBugs:
    """
    Document known bugs in intent recognition.

    These tests assert CURRENT behavior, which may be buggy.
    When bugs are fixed, update the assertions to match correct behavior.

    KNOWN BUG: The " to " keyword in FLIGHT_KEYWORDS causes hotel phrases
    like "want to stay" or "want to book" to be classified as BOOK_FLIGHT
    because they contain " to ".
    """

    @pytest.mark.asyncio
    async def test_to_keyword_bug_stay_in_hotel(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """
        FIXED: "want to stay" contains " to " but AI correctly recognizes hotel intent.

        Previous bug: " to " keyword matching interfered with hotel detection.
        Current: AI correctly identifies BOOK_HOTEL with high confidence.
        """
        response = await chat_service.process_message(
            message="I want to stay in a hotel in Paris",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert response.intent_name is not None
        assert response.confidence is not None

        # AI correctly recognizes hotel intent despite " to " in message
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9  # High confidence expected

        # Should be collecting hotel info
        assert response.type == "collecting_info"

    @pytest.mark.asyncio
    async def test_to_keyword_bug_want_to_book(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """
        BUG: "want to book a hotel" contains " to " which matches FLIGHT_KEYWORDS.

        Expected: BOOK_HOTEL
        Actual: Should be BOOK_HOTEL since "hotel" is explicit

        This test documents current behavior.
        """
        response = await chat_service.process_message(
            message="I want to book a hotel",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None

        # With explicit "hotel" keyword, AI should recognize hotel intent
        # even with " to " present
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # Should be collecting hotel info
        assert response.type == "collecting_info"
        assert response.data is not None
        assert "waiting_for" in response.data


@pytest.mark.integration
@pytest.mark.slow
class TestAmbiguousQueries:
    """Test handling of ambiguous or unclear queries."""

    @pytest.mark.asyncio
    async def test_general_travel_query(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """General travel query without specific booking intent."""
        response = await chat_service.process_message(
            message="I'm planning a trip to Paris",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None
        assert len(response.message) > 20  # Substantive response

        # Intent - could be flight (common interpretation) or general
        # Note: AI may return "general_query" or "general_travel" for ambiguous queries
        assert response.intent_name in [
            "book_flight",
            "book_hotel",
            "general_travel",
            "general_query",
            "create_itinerary",
        ]
        assert response.confidence is not None

        # Should be in some active state
        assert response.type is not None

    @pytest.mark.asyncio
    async def test_stay_keyword_suggests_hotel(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """'stay' keyword correctly triggers hotel intent."""
        response = await chat_service.process_message(
            message="I need somewhere to stay in London",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response is not None
        assert response.message is not None

        # "stay" correctly triggers hotel intent
        assert response.intent_name == "book_hotel"
        assert response.confidence >= 0.9

        # Should be collecting hotel info
        assert response.type == "collecting_info"
        assert response.data is not None


@pytest.mark.integration
@pytest.mark.slow
class TestStickyIntentBehavior:
    """Test sticky intent system (high confidence threshold)."""

    @pytest.mark.asyncio
    async def test_intent_persists_across_turns(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """Once intent is established, unclear messages should maintain it."""
        # Turn 1: Establish flight intent with clear message
        response1 = await chat_service.process_message(
            message="I want to book a flight from Amsterdam to Paris",
            user=test_user,
            chat_id=chat_id,
        )

        # Verify intent established
        assert response1.intent_name == "book_flight"
        assert response1.confidence >= 0.9
        assert response1.type == "collecting_info"

        # Turn 2: Follow-up without clear intent should maintain flight context
        response2 = await chat_service.process_message(
            message="next Monday",
            user=test_user,
            chat_id=chat_id,
        )

        # Should maintain flight intent (sticky behavior)
        assert response2.intent_name == "book_flight"
        assert response2.type == "collecting_info"

        # Should have progressed in field collection
        assert response2.data is not None
        # Either collected the date or asking for next field
        waiting_for = response2.data.get("waiting_for")
        assert waiting_for is not None

    @pytest.mark.asyncio
    async def test_high_confidence_can_switch_intent(
        self, chat_service: LoggingChatService, test_user: UserPublic, chat_id: str
    ):
        """High confidence message switches intent from flight to hotel."""
        # Turn 1: Establish flight intent
        response1 = await chat_service.process_message(
            message="I want to fly to London",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_flight"
        assert response1.confidence >= 0.9

        # Turn 2: Clear hotel intent switches context
        response2 = await chat_service.process_message(
            message="Actually I need a place to stay too",
            user=test_user,
            chat_id=chat_id,
        )

        # Response structure
        assert response2 is not None
        assert response2.message is not None
        assert response2.intent_name is not None

        # "stay" keyword with high confidence switches to hotel intent
        assert response2.intent_name == "book_hotel"
        assert response2.confidence >= 0.9
        assert response2.type == "collecting_info"
        assert response2.data is not None
