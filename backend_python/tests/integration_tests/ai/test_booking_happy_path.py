"""
Booking Happy Path Tests - Critical E2E Flows

These tests verify the core booking flows that MUST work:
1. Single sentence with all info → search results → "book 1" → booking URL
2. Multi-turn conversation → search results → "book 1" → booking URL

These tests REQUIRE:
- FlightLogic mock server running
- Response type == "booking_redirect" (not just "booking_clarification")
- booking_url present in response data

Run with: pytest tests/integration_tests/ai/test_booking_happy_path.py -v -m integration
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService


@pytest.mark.integration
@pytest.mark.slow
class TestFlightBookingHappyPath:
    """Flight booking happy path - MUST pass for production readiness."""

    @pytest.mark.asyncio
    async def test_single_sentence_to_booking_url(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """CRITICAL: Single complete message → search → "book 1" → booking URL.

        This is the most common user flow:
        User: "AMS to Lisbon Dec 15 oneway for 1 adult"
        Agent: [shows 3 flight options]
        User: "book option 1"
        Agent: [returns booking URL]
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Step 1: Complete search request in one message
        search_response = await chat_service.process_message(
            message="AMS to Lisbon Dec 15 oneway for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        # Verify intent and search results
        assert search_response.intent_name == "book_flight", (
            f"Expected book_flight intent, got: {search_response.intent_name}"
        )
        assert search_response.type == "flight_search_results", (
            f"Expected flight_results, got: {search_response.type}. "
            f"Message: {search_response.message[:200] if search_response.message else 'None'}"
        )
        assert search_response.data is not None
        assert "flights" in search_response.data
        flights = search_response.data["flights"]
        assert len(flights) >= 1, "Expected at least 1 flight option"

        # Step 2: Book option 1
        select_response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # STRICT: Must return booking redirect with URL
        # Response type can be "booking_redirect" or "flight_booking_redirect"
        assert select_response.type in [
            "booking_redirect",
            "flight_booking_redirect",
        ], (
            f"Expected booking redirect, got: {select_response.type}. "
            f"Message: {select_response.message[:200] if select_response.message else 'None'}"
        )
        assert select_response.data is not None

        # URL can be in "booking_url" or "redirect_url" field
        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None, (
            f"Missing booking URL in response data: {select_response.data.keys()}"
        )

        # Verify URL structure
        assert booking_url.startswith("http"), f"Invalid URL format: {booking_url}"
        assert "flight" in booking_url.lower(), (
            f"URL should contain 'flight': {booking_url}"
        )

    @pytest.mark.asyncio
    async def test_multi_turn_to_booking_url(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """CRITICAL: Multi-turn conversation → search → "book 1" → booking URL.

        This tests the field collection flow:
        User: "I need a flight"
        Agent: "Where would you like to fly from?"
        User: "Amsterdam"
        Agent: "Where would you like to fly to?"
        User: "Lisbon"
        Agent: "When would you like to depart?"
        User: "December 20th"
        Agent: "Is this a one-way or round trip?"
        User: "One way"
        Agent: [shows flight options]
        User: "book option 1"
        Agent: [returns booking URL]
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Turn 1: Establish intent
        response1 = await chat_service.process_message(
            message="I want to book a flight",
            user=test_user,
            chat_id=chat_id,
        )
        assert response1.intent_name == "book_flight"
        assert response1.type == "collecting_info"

        # Turn 2: Provide origin
        response2 = await chat_service.process_message(
            message="From Amsterdam",
            user=test_user,
            chat_id=chat_id,
        )
        assert response2.intent_name == "book_flight"

        # Turn 3: Provide destination
        response3 = await chat_service.process_message(
            message="To Lisbon",
            user=test_user,
            chat_id=chat_id,
        )
        assert response3.intent_name == "book_flight"

        # Turn 4: Provide date
        response4 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )
        assert response4.intent_name == "book_flight"

        # Turn 5: Provide journey type (if asked)
        if response4.type == "collecting_info":
            response5 = await chat_service.process_message(
                message="One way",
                user=test_user,
                chat_id=chat_id,
            )
        else:
            response5 = response4

        # At this point we should have search results or be very close
        # May need one more turn for passengers
        if response5.type == "collecting_info":
            response6 = await chat_service.process_message(
                message="1 adult",
                user=test_user,
                chat_id=chat_id,
            )
        else:
            response6 = response5

        # Now we should have flight results
        assert response6.type == "flight_search_results", (
            f"Expected flight_results after providing all fields, got: {response6.type}. "
            f"Message: {response6.message[:200] if response6.message else 'None'}"
        )
        assert response6.data is not None
        assert "flights" in response6.data
        assert len(response6.data["flights"]) >= 1

        # Final step: Book option 1
        select_response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # STRICT: Must return booking redirect with URL
        assert select_response.type in [
            "booking_redirect",
            "flight_booking_redirect",
        ], (
            f"Expected booking redirect, got: {select_response.type}. "
            f"Message: {select_response.message[:200] if select_response.message else 'None'}"
        )
        assert select_response.data is not None

        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None
        assert booking_url.startswith("http")
        assert "flight" in booking_url.lower()


@pytest.mark.integration
@pytest.mark.slow
class TestHotelBookingHappyPath:
    """Hotel booking happy path - MUST pass for production readiness."""

    @pytest.mark.asyncio
    async def test_single_sentence_to_booking_url(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """CRITICAL: Single complete message → search → "book 1" → booking URL.

        This is the most common user flow:
        User: "Please book a hotel in London for 2 adults, check-in Dec 15, check-out Dec 18"
        Agent: [shows hotel options]
        User: "book option 1"
        Agent: [returns booking URL]
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Step 1: Complete search request in one message
        # NOTE: Explicit "book a hotel" phrasing works better than "Hotel in..."
        search_response = await chat_service.process_message(
            message="Please book a hotel in London for 2 adults, with check-in on Dec 15 and check-out on Dec 18",
            user=test_user,
            chat_id=chat_id,
        )

        # Verify intent
        assert search_response.intent_name == "book_hotel", (
            f"Expected book_hotel intent, got: {search_response.intent_name}"
        )

        # Check if we got results or are still collecting
        if search_response.type == "collecting_info":
            collected = search_response.data.get("collected_so_far", {})
            waiting_for = search_response.data.get("waiting_for", "unknown")
            pytest.fail(
                f"Hotel search did not trigger. "
                f"Waiting for: {waiting_for}. "
                f"Collected: {collected}."
            )

        assert search_response.type in ["hotel_results", "search_results"], (
            f"Expected hotel_results, got: {search_response.type}. "
            f"Message: {search_response.message[:200] if search_response.message else 'None'}"
        )
        assert search_response.data is not None
        hotels = search_response.data.get("hotels", [])
        assert len(hotels) >= 1, "Expected at least 1 hotel option"

        # Step 2: Book option 1
        select_response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # STRICT: Must return booking redirect with URL
        assert select_response.type in ["booking_redirect", "hotel_booking_redirect"], (
            f"Expected booking redirect, got: {select_response.type}. "
            f"Message: {select_response.message[:200] if select_response.message else 'None'}"
        )
        assert select_response.data is not None

        # URL can be in "booking_url" or "redirect_url" field
        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None, (
            f"Missing booking URL in response data: {select_response.data.keys()}"
        )

        # Verify URL structure
        assert booking_url.startswith("http"), f"Invalid URL format: {booking_url}"
        assert "hotel" in booking_url.lower(), (
            f"URL should contain 'hotel': {booking_url}"
        )

    @pytest.mark.asyncio
    async def test_multi_turn_to_booking_url(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """CRITICAL: Multi-turn conversation → search → "book 1" → booking URL.

        This tests the field collection flow:
        User: "I need a hotel"
        Agent: "Which city would you like to stay in?"
        User: "London"
        Agent: "What's your check-in date?"
        User: "December 20th"
        Agent: "What's your check-out date?"
        User: "December 25th"
        Agent: "How many guests?"
        User: "2 adults"
        Agent: [shows hotel options]
        User: "book option 1"
        Agent: [returns booking URL]
        """
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Turn 1: Establish intent with destination
        response1 = await chat_service.process_message(
            message="I need a hotel in London",
            user=test_user,
            chat_id=chat_id,
        )
        assert response1.intent_name == "book_hotel"
        assert response1.type == "collecting_info"

        # Verify destination was collected
        collected = response1.data.get("collected_so_far", {})
        assert "destination" in collected or "city" in collected, (
            f"Destination should be extracted from 'hotel in London'. "
            f"Collected: {collected}"
        )

        # Turn 2: Provide check-in date
        response2 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )
        assert response2.intent_name == "book_hotel"

        # Turn 3: Provide check-out date
        response3 = await chat_service.process_message(
            message="December 25th",
            user=test_user,
            chat_id=chat_id,
        )
        assert response3.intent_name == "book_hotel"

        # Turn 4: Provide guests (if asked)
        if response3.type == "collecting_info":
            response4 = await chat_service.process_message(
                message="2 adults",
                user=test_user,
                chat_id=chat_id,
            )
        else:
            response4 = response3

        # Now we should have hotel results
        if response4.type == "collecting_info":
            # Provide one more piece of info if still collecting
            response5 = await chat_service.process_message(
                message="1 room",
                user=test_user,
                chat_id=chat_id,
            )
        else:
            response5 = response4

        assert response5.type in ["hotel_results", "search_results"], (
            f"Expected hotel_results after providing all fields, got: {response5.type}. "
            f"Message: {response5.message[:200] if response5.message else 'None'}"
        )
        assert response5.data is not None
        hotels = response5.data.get("hotels", [])
        assert len(hotels) >= 1

        # Final step: Book option 1
        select_response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # STRICT: Must return booking redirect with URL
        assert select_response.type in ["booking_redirect", "hotel_booking_redirect"], (
            f"Expected booking redirect, got: {select_response.type}. "
            f"Message: {select_response.message[:200] if select_response.message else 'None'}"
        )
        assert select_response.data is not None

        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None
        assert booking_url.startswith("http")
        assert "hotel" in booking_url.lower()


@pytest.mark.integration
@pytest.mark.slow
class TestBookingSelectionVariations:
    """Test different selection phrases for booking."""

    @pytest.mark.asyncio
    async def test_flight_book_option_2(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test selecting option 2 instead of option 1."""
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to Lisbon Dec 15 oneway for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        flights = search_response.data.get("flights", [])
        if len(flights) < 2:
            pytest.skip("Need at least 2 flight options to test option 2")

        # Book option 2
        select_response = await chat_service.process_message(
            message="book option 2",
            user=test_user,
            chat_id=chat_id,
        )

        assert select_response.type in [
            "booking_redirect",
            "flight_booking_redirect",
        ], f"Expected booking redirect for option 2, got: {select_response.type}"
        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None

    @pytest.mark.asyncio
    async def test_flight_book_option_3(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test selecting option 3."""
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="AMS to Lisbon Dec 15 oneway for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type != "flight_search_results":
            pytest.skip(f"Search did not return results: {search_response.type}")

        flights = search_response.data.get("flights", [])
        if len(flights) < 3:
            pytest.skip("Need at least 3 flight options to test option 3")

        # Book option 3
        select_response = await chat_service.process_message(
            message="book option 3",
            user=test_user,
            chat_id=chat_id,
        )

        assert select_response.type in [
            "booking_redirect",
            "flight_booking_redirect",
        ], f"Expected booking redirect for option 3, got: {select_response.type}"
        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None

    @pytest.mark.asyncio
    async def test_hotel_book_option_2(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Test selecting hotel option 2."""
        if not mock_server_running:
            pytest.skip("Requires FlightLogic mock server")

        # Search
        search_response = await chat_service.process_message(
            message="Hotel in London Dec 15 to Dec 18 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        if search_response.type not in ["hotel_results", "search_results"]:
            pytest.skip(f"Search did not return results: {search_response.type}")

        hotels = search_response.data.get("hotels", [])
        if len(hotels) < 2:
            pytest.skip("Need at least 2 hotel options to test option 2")

        # Book option 2
        select_response = await chat_service.process_message(
            message="book option 2",
            user=test_user,
            chat_id=chat_id,
        )

        assert select_response.type in ["booking_redirect", "hotel_booking_redirect"], (
            f"Expected booking redirect for hotel option 2, got: {select_response.type}"
        )
        booking_url = select_response.data.get(
            "booking_url", select_response.data.get("redirect_url")
        )
        assert booking_url is not None
        assert "hotel" in booking_url.lower()
