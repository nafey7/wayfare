"""Unit tests for the select_hotel LangGraph tool.

Tests selection parsing, session storage, and redirect URL generation.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.graph.tools.hotel_booking import select_hotel

# Path to mock BookingSessionService - it's imported inside the function
BOOKING_SESSION_SERVICE_PATH = (
    "app.domains.booking_sessions.service.BookingSessionService"
)


def make_config(user_id: str = "user_123", chat_id: str = "chat_456") -> dict:
    """Create config dict with user_id and chat_id for tool injection."""
    return {"configurable": {"user_id": user_id, "thread_id": chat_id}}


# Sample hotel data for tests
SAMPLE_HOTELS = [
    {
        "hotel_id": "hotel_1",
        "hotel_name": "Best Value Hotel",
        "total_price": 200.0,
        "currency": "USD",
    },
    {
        "hotel_id": "hotel_2",
        "hotel_name": "Cheapest Hotel",
        "total_price": 150.0,
        "currency": "USD",
    },
    {
        "hotel_id": "hotel_3",
        "hotel_name": "Highest Rated Hotel",
        "total_price": 300.0,
        "currency": "USD",
        "hotel_rating": 5,
    },
]

SAMPLE_SEARCH_PARAMS = {
    "city": "Paris",
    "country": "France",
    "checkin": "2025-01-20",
    "checkout": "2025-01-25",
    "rooms": 1,
    "adults": 2,
    "children": 0,
}


class TestSelectHotelTool:
    """Tests for the select_hotel tool."""

    @pytest.mark.asyncio
    async def test_select_by_number(self) -> None:
        """Test selection by option number."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "book 1",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            assert "redirect_url" in result
            assert "hotel-booker" in result["redirect_url"]
            assert result["selected_hotel"] == "Best Value Hotel"
            assert result["selected_option"] == 1

    @pytest.mark.asyncio
    async def test_select_by_option_pattern(self) -> None:
        """Test selection by 'book option X' pattern."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "book option 2",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            assert result["selected_hotel"] == "Cheapest Hotel"
            assert result["selected_option"] == 2

    @pytest.mark.asyncio
    async def test_select_by_label_cheapest(self) -> None:
        """Test selection by 'cheapest' label."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "book the cheapest one",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            # "cheapest" maps to option 2 in SelectionParser
            assert result["selected_option"] == 2

    @pytest.mark.asyncio
    async def test_select_by_ordinal(self) -> None:
        """Test selection by ordinal word."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "I'll take the first one",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            assert result["selected_option"] == 1

    @pytest.mark.asyncio
    async def test_select_bare_number(self) -> None:
        """Test selection by bare number."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "3",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            assert result["selected_hotel"] == "Highest Rated Hotel"
            assert result["selected_option"] == 3

    @pytest.mark.asyncio
    async def test_select_out_of_range(self) -> None:
        """Test selection with out-of-range number."""
        result = await select_hotel.ainvoke(
            {
                "selection": "book 10",
                "hotels": SAMPLE_HOTELS,
                "session_id": "fl_session_123",
                "search_params": SAMPLE_SEARCH_PARAMS,
            },
            config=make_config(),
        )

        assert result["status"] == "error"
        assert "out of range" in result["error"]
        assert result["valid_range"] == "1 to 3"

    @pytest.mark.asyncio
    async def test_select_invalid_selection_text(self) -> None:
        """Test selection with unparseable text."""
        result = await select_hotel.ainvoke(
            {
                "selection": "hello world",
                "hotels": SAMPLE_HOTELS,
                "session_id": "fl_session_123",
                "search_params": SAMPLE_SEARCH_PARAMS,
            },
            config=make_config(),
        )

        assert result["status"] == "error"
        assert "Could not understand" in result["error"]

    @pytest.mark.asyncio
    async def test_select_empty_hotels(self) -> None:
        """Test selection with empty hotels list."""
        result = await select_hotel.ainvoke(
            {
                "selection": "book 1",
                "hotels": [],
                "session_id": "fl_session_123",
                "search_params": SAMPLE_SEARCH_PARAMS,
            },
            config=make_config(),
        )

        assert result["status"] == "error"
        assert "No hotels provided" in result["error"]

    @pytest.mark.asyncio
    async def test_select_missing_session_id(self) -> None:
        """Test selection with missing session_id."""
        result = await select_hotel.ainvoke(
            {
                "selection": "book 1",
                "hotels": SAMPLE_HOTELS,
                "session_id": "",
                "search_params": SAMPLE_SEARCH_PARAMS,
            },
            config=make_config(),
        )

        assert result["status"] == "error"
        assert "No session_id provided" in result["error"]

    @pytest.mark.asyncio
    async def test_session_data_stored_correctly(self) -> None:
        """Test that session data is stored with correct fields."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            await select_hotel.ainvoke(
                {
                    "selection": "book 1",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            # Verify store_session was called with correct args
            mock_session.store_session.assert_called_once()
            call_args = mock_session.store_session.call_args

            assert call_args.kwargs["session_id"] == "chat_456"
            assert call_args.kwargs["user_id"] == "user_123"
            assert call_args.kwargs["ttl_hours"] == 2

            session_data = call_args.kwargs["session_data"]
            assert session_data["selected_hotel"] == SAMPLE_HOTELS[0]
            assert session_data["selected_option"] == 1
            assert session_data["booking_stage"] == "hotel_selected"
            assert session_data["flightlogic_session_id"] == "fl_session_123"
            assert session_data["source"] == "langgraph_agent"

            # Verify search_params includes original + enhanced fields
            stored_params = session_data["search_params"]
            assert stored_params["city"] == SAMPLE_SEARCH_PARAMS["city"]
            assert stored_params["country"] == SAMPLE_SEARCH_PARAMS["country"]
            assert stored_params["checkin"] == SAMPLE_SEARCH_PARAMS["checkin"]
            assert stored_params["checkout"] == SAMPLE_SEARCH_PARAMS["checkout"]
            # Enhanced fields with defaults
            assert stored_params["rooms"] == 1
            assert stored_params["adults"] == 2
            assert stored_params["children"] == 0
            assert "room_configuration" in stored_params
            assert len(stored_params["room_configuration"]) == 1
            assert stored_params["room_configuration"][0]["adults"] == 2

    @pytest.mark.asyncio
    async def test_jwt_token_in_redirect_url(self) -> None:
        """Test that JWT token is included in redirect URL."""
        with patch(BOOKING_SESSION_SERVICE_PATH) as mock_session:
            mock_session.store_session = AsyncMock()
            mock_session.update_session_data = AsyncMock()

            result = await select_hotel.ainvoke(
                {
                    "selection": "book 1",
                    "hotels": SAMPLE_HOTELS,
                    "session_id": "fl_session_123",
                    "search_params": SAMPLE_SEARCH_PARAMS,
                },
                config=make_config(),
            )

            assert result["status"] == "redirect"
            assert "auth_token=" in result["redirect_url"]
            assert "session_id=chat_456" in result["redirect_url"]
