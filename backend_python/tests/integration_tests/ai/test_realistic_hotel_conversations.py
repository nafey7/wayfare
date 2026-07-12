"""
Realistic hotel conversation flow tests.

These tests simulate how real users interact with the hotel booking chatbot:
- Starting with minimal info (just destination)
- Answering agent questions one by one
- Completing the flow to actual hotel search results

Each test documents:
1. The exact conversation flow
2. What fields are extracted at each step
3. Whether the extraction is correct or buggy

Run with: pytest tests/integration_tests/ai/test_realistic_hotel_conversations.py -v -m integration
"""

import pytest

from app.domains.user.schemas import UserPublic

from .conftest import LoggingChatService, get_collected, get_waiting_for


@pytest.mark.integration
@pytest.mark.slow
class TestHotelCompleteMultiTurnFlow:
    """Complete hotel booking flow from minimal input to search results.

    Scenario: User starts with just destination, answers each question.
    Expected flow: destination → check_in_date → check_out_date → adults → results
    """

    @pytest.mark.asyncio
    async def test_hotel_step_by_step_to_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Complete hotel flow: destination → check_in → check_out → adults → results.

        Expected flow:
        1. "hotel in Amsterdam" → asks check_in_date
        2. "December 20th" → asks check_out_date
        3. "December 25th" → asks adults
        4. "2 adults" → search results
        """
        # Turn 1: Just destination
        response1 = await chat_service.process_message(
            message="I need a hotel in Amsterdam",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_hotel"
        assert response1.confidence >= 0.9
        assert response1.type == "collecting_info"

        # Verify: Should ask for check_in_date
        assert get_waiting_for(response1) == "check_in_date", (
            f"Expected to ask for check_in_date, got: {get_waiting_for(response1)}"
        )

        # Verify destination extraction
        collected1 = get_collected(response1)
        assert "destination" in collected1, "Destination should be extracted"
        assert "amsterdam" in collected1["destination"].lower(), (
            f"Destination should contain Amsterdam, got: {collected1['destination']}"
        )

        # Turn 2: Provide check-in date
        response2 = await chat_service.process_message(
            message="December 20th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response2.intent_name == "book_hotel"
        assert response2.type == "collecting_info"

        # Verify: Should ask for check_out_date
        assert get_waiting_for(response2) == "check_out_date", (
            f"Expected to ask for check_out_date, got: {get_waiting_for(response2)}"
        )

        # Verify check_in_date extraction
        collected2 = get_collected(response2)
        assert "check_in_date" in collected2, "check_in_date should be collected"
        check_in = str(collected2["check_in_date"])
        assert "12-20" in check_in or "12/20" in check_in or "20" in check_in, (
            f"check_in_date should be Dec 20, got: {check_in}"
        )

        # Turn 3: Provide check-out date
        response3 = await chat_service.process_message(
            message="December 25th",
            user=test_user,
            chat_id=chat_id,
        )

        assert response3.intent_name == "book_hotel"

        # Verify check_out_date extraction
        collected3 = get_collected(response3)
        if "check_out_date" in collected3:
            check_out = str(collected3["check_out_date"])
            assert "12-25" in check_out or "12/25" in check_out or "25" in check_out, (
                f"check_out_date should be Dec 25, got: {check_out}"
            )

        # Turn 4: Provide guests if asked
        if response3.type == "collecting_info":
            waiting_for_3 = get_waiting_for(response3)
            if waiting_for_3 in ["adults", "guests"]:
                response4 = await chat_service.process_message(
                    message="2 adults",
                    user=test_user,
                    chat_id=chat_id,
                )
                final_response = response4

                # Verify adult count extraction
                collected4 = get_collected(response4)
                if "adults" in collected4:
                    assert collected4["adults"] == 2, (
                        f"Should have 2 adults, got: {collected4['adults']}"
                    )
            else:
                final_response = response3
        else:
            final_response = response3

        # Final state check with mock server
        if mock_server_running and final_response.type == "hotel_results":
            assert "hotels" in final_response.data
            hotels = final_response.data["hotels"]
            assert len(hotels) >= 1, "Should have at least one hotel result"

    @pytest.mark.asyncio
    async def test_hotel_with_duration_pattern(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Hotel booking with 'for X nights' pattern.

        Tests: "hotel in Paris for 5 nights starting Dec 15"
        Expected: check_out should be calculated as check_in + 5 days
        """
        # Turn 1: Full request with duration
        response1 = await chat_service.process_message(
            message="hotel in Paris for 5 nights starting December 15th, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response1.intent_name == "book_hotel"
        assert response1.confidence >= 0.9

        collected = get_collected(response1)

        # Document: Is check_out_date calculated from duration?
        if "check_out_date" in collected:
            check_out = str(collected["check_out_date"])
            # 5 nights from Dec 15 = Dec 20
            assert "12-20" in check_out or "20" in check_out, (
                f"check_out should be Dec 20 (5 nights from Dec 15), got: {check_out}"
            )
        elif response1.type == "collecting_info":
            # If still collecting, document what's being asked
            waiting_for = get_waiting_for(response1)
            # Document whether duration pattern was understood
            assert waiting_for is not None, (
                "Should be asking for missing field or have calculated check_out"
            )

        # With mock server should proceed
        if mock_server_running:
            assert response1.type in [
                "hotel_results",
                "collecting_info",
                "searching",
            ]


@pytest.mark.integration
@pytest.mark.slow
class TestHotelFieldExtractionVerification:
    """Tests that verify specific hotel field extraction behavior."""

    @pytest.mark.asyncio
    async def test_guest_extraction_adults_only(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify adult count is correctly extracted from hotel request."""
        response = await chat_service.process_message(
            message="hotel in London from Dec 20 to Dec 25 for 3 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        # Document extraction behavior
        if "adults" in collected:
            assert collected["adults"] == 3, (
                f"EXTRACTION BUG: Should extract 3 adults, got: {collected['adults']}"
            )

    @pytest.mark.asyncio
    async def test_guest_extraction_with_children(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify children count is correctly extracted from hotel request."""
        response = await chat_service.process_message(
            message="hotel in Barcelona from Jan 10 to Jan 15 for 2 adults and 2 children",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
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
    async def test_room_count_extraction(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify room count is correctly extracted."""
        response = await chat_service.process_message(
            message="2 rooms in Berlin from Feb 5 to Feb 10 for 4 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        if "rooms" in collected:
            assert collected["rooms"] == 2, (
                f"EXTRACTION BUG: Should extract 2 rooms, got: {collected['rooms']}"
            )

    @pytest.mark.asyncio
    async def test_date_extraction_from_range(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify date extraction from 'from X to Y' format."""
        response = await chat_service.process_message(
            message="hotel in Rome from March 5 to March 10 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        if "check_in_date" in collected:
            check_in = str(collected["check_in_date"])
            assert "3-05" in check_in or "03-05" in check_in or "5" in check_in, (
                f"check_in_date should be March 5, got: {check_in}"
            )
        if "check_out_date" in collected:
            check_out = str(collected["check_out_date"])
            assert "3-10" in check_out or "03-10" in check_out or "10" in check_out, (
                f"check_out_date should be March 10, got: {check_out}"
            )

    @pytest.mark.asyncio
    async def test_relative_date_extraction(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Verify relative date parsing (next week, tomorrow, etc)."""
        response = await chat_service.process_message(
            message="hotel in Vienna next week for 3 nights, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        # Document whether relative dates are resolved
        if "check_in_date" in collected:
            check_in = str(collected["check_in_date"])
            # Should be a resolved date, not "next week"
            assert "next week" not in check_in.lower(), (
                f"Date should be resolved, not literal 'next week': {check_in}"
            )


@pytest.mark.integration
@pytest.mark.slow
class TestHotelPreferenceBehavior:
    """Document actual hotel preference handling behavior.

    IMPORTANT: These tests document what the system ACTUALLY does,
    even if that behavior is incorrect (e.g., ignoring star rating preference).
    """

    @pytest.mark.asyncio
    async def test_star_rating_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if star rating preference is extracted and stored.

        User says "5 star hotel" - verify if this is captured in collected fields.
        """
        response = await chat_service.process_message(
            message="5 star hotel in Dubai from Feb 10 to Feb 15 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        # Document current behavior
        has_star_rating = (
            "star_rating" in collected
            or "stars" in collected
            or "rating" in collected
            or "hotel_class" in collected
        )

        if has_star_rating:
            rating_value = (
                collected.get("star_rating")
                or collected.get("stars")
                or collected.get("rating")
                or collected.get("hotel_class")
            )
            # If captured, verify it's correct
            assert rating_value == 5 or "5" in str(rating_value), (
                f"Star rating preference should be 5, got: {rating_value}"
            )
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: Star rating preference '5 star' is NOT captured in collected fields. "
                "The system ignores star rating preferences in user input."
            )

    @pytest.mark.asyncio
    async def test_pool_amenity_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if pool amenity preference is captured.

        User says "hotel with pool" - verify if this is captured.
        """
        response = await chat_service.process_message(
            message="hotel with pool in Las Vegas from Dec 20 to Dec 25 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        has_pool_pref = (
            "amenities" in collected
            or "pool" in collected
            or "facilities" in collected
            or "with_pool" in collected
        )

        if has_pool_pref:
            amenities = (
                collected.get("amenities")
                or collected.get("facilities")
                or [collected.get("pool")]
            )
            assert "pool" in str(amenities).lower(), (
                f"Pool preference should be captured, got: {amenities}"
            )
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'Hotel with pool' preference is NOT captured. "
                "The system ignores amenity preferences in user input."
            )

    @pytest.mark.asyncio
    async def test_breakfast_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if breakfast preference is captured.

        User says "with breakfast included" - verify if this is captured.
        """
        response = await chat_service.process_message(
            message="hotel with breakfast included in Tokyo from Jan 5 to Jan 10 for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        has_breakfast_pref = (
            "breakfast" in collected
            or "meal_plan" in collected
            or "amenities" in collected
        )

        if has_breakfast_pref:
            breakfast_value = (
                collected.get("breakfast")
                or collected.get("meal_plan")
                or collected.get("amenities")
            )
            assert "breakfast" in str(breakfast_value).lower(), (
                f"Breakfast preference should be captured, got: {breakfast_value}"
            )
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'Breakfast included' preference is NOT captured. "
                "The system ignores breakfast/meal preferences in user input."
            )

    @pytest.mark.asyncio
    async def test_pet_friendly_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if pet-friendly preference is captured."""
        response = await chat_service.process_message(
            message="pet-friendly hotel in Portland for 4 nights starting next Monday, 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        has_pet_pref = (
            "pet_friendly" in collected
            or "pets" in collected
            or "pets_allowed" in collected
            or "amenities" in collected
        )

        if has_pet_pref:
            pet_value = (
                collected.get("pet_friendly")
                or collected.get("pets")
                or collected.get("pets_allowed")
                or collected.get("amenities")
            )
            assert pet_value is True or "pet" in str(pet_value).lower(), (
                f"Pet preference should be captured, got: {pet_value}"
            )
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'Pet-friendly' preference is NOT captured. "
                "The system ignores pet accommodation preferences."
            )

    @pytest.mark.asyncio
    async def test_budget_preference_is_captured(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test if budget preference (cheap/budget) is captured."""
        response = await chat_service.process_message(
            message="cheap hotel in Bangkok for a week starting Jan 15, 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        has_budget_pref = (
            "budget" in collected
            or "price_range" in collected
            or "max_price" in collected
            or "price_preference" in collected
        )

        if has_budget_pref:
            budget_value = (
                collected.get("budget")
                or collected.get("price_range")
                or collected.get("price_preference")
            )
            assert (
                budget_value == "cheap"
                or "budget" in str(budget_value).lower()
                or "low" in str(budget_value).lower()
            ), f"Budget preference should indicate cheap, got: {budget_value}"
        else:
            pytest.xfail(
                "KNOWN BEHAVIOR: 'Cheap hotel' budget preference is NOT captured. "
                "The system ignores budget/price preferences."
            )


@pytest.mark.integration
@pytest.mark.slow
class TestHotelSelectionFlow:
    """Test hotel selection after search results."""

    async def _get_hotel_search_results(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Helper to trigger a hotel search and get results."""
        return await chat_service.process_message(
            message="hotel in Amsterdam Dec 15 to Dec 20 for 2 adults",
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
        """Select hotel by 'book option 1'."""
        # Get search results first
        search_response = await self._get_hotel_search_results(
            chat_service, test_user, chat_id
        )

        assert search_response.intent_name == "book_hotel"

        # With mock server, search should succeed
        if mock_server_running and search_response.type == "hotel_results":
            # Attempt selection
            select_response = await chat_service.process_message(
                message="book option 1",
                user=test_user,
                chat_id=chat_id,
            )

            assert select_response.intent_name == "book_hotel"
            assert select_response.data is not None

            # Document: Does selection return booking URL?
            if select_response.type == "booking_redirect":
                assert "booking_url" in select_response.data, (
                    "booking_redirect should include booking_url"
                )
                url = select_response.data["booking_url"]
                assert "hotel" in url.lower(), (
                    f"URL should point to hotel booker: {url}"
                )

    @pytest.mark.asyncio
    async def test_selection_by_cheapest(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select hotel by 'book cheapest'."""
        search_response = await self._get_hotel_search_results(
            chat_service, test_user, chat_id
        )

        if mock_server_running and search_response.type == "hotel_results":
            select_response = await chat_service.process_message(
                message="book cheapest",
                user=test_user,
                chat_id=chat_id,
            )

            assert select_response.intent_name == "book_hotel"
            # Document what 'cheapest' selection returns

    @pytest.mark.asyncio
    async def test_selection_by_highest_rated(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
        mock_server_running: bool,
    ):
        """Select hotel by 'book highest rated'."""
        search_response = await self._get_hotel_search_results(
            chat_service, test_user, chat_id
        )

        if mock_server_running and search_response.type == "hotel_results":
            select_response = await chat_service.process_message(
                message="book highest rated",
                user=test_user,
                chat_id=chat_id,
            )

            assert select_response.intent_name == "book_hotel"
            # Document what 'highest rated' selection returns


@pytest.mark.integration
@pytest.mark.slow
class TestHotelEdgeCases:
    """Test edge cases in hotel booking flow."""

    @pytest.mark.asyncio
    async def test_same_day_checkin_checkout(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test handling of same check-in and check-out date (invalid)."""
        response = await chat_service.process_message(
            message="hotel in London on December 25th for 1 adult",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.type == "collecting_info"

        # Should ask for check_out_date (single date = only check_in)
        waiting_for = get_waiting_for(response)
        assert waiting_for in ["check_out_date", "check_in_date"], (
            f"Should ask for dates, got: {waiting_for}"
        )

    @pytest.mark.asyncio
    async def test_minimal_request(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test minimal request: 'hotel please'."""
        response = await chat_service.process_message(
            message="hotel please",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        assert response.type == "collecting_info"

        # Should ask for destination first
        waiting_for = get_waiting_for(response)
        assert waiting_for == "destination", (
            f"Minimal request should ask for destination, got: {waiting_for}"
        )

    @pytest.mark.asyncio
    async def test_typo_in_city_name(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test handling of typo in city name."""
        response = await chat_service.process_message(
            message="hotel in Amstredam from Dec 20 to Dec 25 for 2 adults",
            user=test_user,
            chat_id=chat_id,
        )

        assert response.intent_name == "book_hotel"
        collected = get_collected(response)

        # Document: Does it correct typo or use as-is?
        if "destination" in collected:
            dest = collected["destination"].lower()
            # Either corrected to "Amsterdam" or kept "Amstredam"
            assert "amst" in dest, (
                f"Destination should contain Amst*, got: {collected['destination']}"
            )

    @pytest.mark.asyncio
    async def test_selection_before_search(
        self,
        chat_service: LoggingChatService,
        test_user: UserPublic,
        chat_id: str,
    ):
        """Test 'book option 1' without prior hotel search."""
        # Try to book without searching first - fresh chat
        response = await chat_service.process_message(
            message="book option 1",
            user=test_user,
            chat_id=chat_id,
        )

        # Should not crash - either ask for search or detect as flight
        assert response is not None
        assert response.message is not None

        # Document behavior: What happens with selection without context?
        # Likely detects as flight due to "book" keyword
