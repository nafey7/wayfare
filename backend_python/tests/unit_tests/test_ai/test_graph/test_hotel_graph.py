"""Unit tests for hotel_graph.py invoke_hotel_graph function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# Mock MongoDB before importing hotel_graph to prevent connection attempts
with patch("pymongo.MongoClient"):
    from app.ai.graph.hotel_graph import (
        _extract_hotel_no_results_message,
        _extract_search_params_from_messages,
        invoke_hotel_graph,
    )


def _create_mock_ai_message_with_tool_calls(tool_calls):
    """Create a mock AIMessage that passes isinstance checks and has tool_calls."""
    mock_msg = MagicMock()
    mock_msg.tool_calls = tool_calls
    # Make isinstance(msg, AIMessage) return True
    mock_msg.__class__ = AIMessage
    return mock_msg


class TestInvokeHotelGraph:
    """Test cases for invoke_hotel_graph function."""

    @pytest.fixture
    def mock_graph(self):
        """Mock LangGraph instance."""
        graph = MagicMock()
        graph.ainvoke = AsyncMock()
        return graph

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_includes_search_params(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that invoke_hotel_graph includes search_params in response when hotel search results are present."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Mock graph result with hotel search results
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="I want to book a hotel in Paris"),
                AIMessage(content="I found some hotels for you"),
                ToolMessage(
                    content='{"hotels": [{"hotel_name": "Test Hotel"}], "session_id": "fl_session_123"}',
                    tool_call_id="search_hotels_123",
                ),
            ],
            "hotel": {
                "city": "Paris",
                "country": "France",
                "checkin": "2026-04-15",
                "checkout": "2026-04-20",
                "rooms": 2,
                "adults": 4,
                "children": 1,
            },
        }

        # Mock _extract_hotel_search_results to return hotel results
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {},
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel in Paris",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify search_params are included
            # When hotel search results exist, type is "hotel_search_results"
            assert result["type"] == "hotel_search_results"
            assert "data" in result
            assert "search_params" in result["data"]
            search_params = result["data"]["search_params"]

            assert search_params["destination_city"] == "Paris"
            assert search_params["country"] == "France"
            assert search_params["check_in_date"] == "2026-04-15"
            assert search_params["check_out_date"] == "2026-04-20"
            assert search_params["rooms"] == 2
            assert search_params["adults"] == 4
            assert search_params["children"] == 1

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_search_params_defaults(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that search_params use default values when fields are missing."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Mock graph result with minimal hotel params
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="I want to book a hotel"),
                AIMessage(content="I found some hotels"),
                ToolMessage(
                    content='{"hotels": [{"hotel_name": "Test Hotel"}], "session_id": "fl_session_123"}',
                    tool_call_id="search_hotels_123",
                ),
            ],
            "hotel": {
                "city": "London",
                "checkin": "2026-04-10",
                "checkout": "2026-04-15",
                # Missing rooms, adults, children
            },
        }

        # Mock _extract_hotel_search_results
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {},
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify default values are used
            assert "data" in result
            assert "search_params" in result["data"]
            search_params = result["data"]["search_params"]

            assert search_params["rooms"] == 1  # Default
            assert search_params["adults"] is None  # No default — must be provided
            assert search_params["children"] == 0  # Default

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_search_params_with_existing_data(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that search_params are added to existing data dict."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Mock graph result
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="I want to book a hotel"),
                AIMessage(content="I found some hotels"),
                ToolMessage(
                    content='{"hotels": [{"hotel_name": "Test Hotel"}], "session_id": "fl_session_123"}',
                    tool_call_id="search_hotels_123",
                ),
            ],
            "hotel": {
                "city": "Tokyo",
                "country": "Japan",
                "checkin": "2026-04-01",
                "checkout": "2026-04-10",
                "rooms": 1,
                "adults": 2,
                "children": 0,
            },
        }

        # Mock _extract_hotel_search_results with existing data
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {
                    "existing_key": "existing_value",
                },
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify existing data is preserved and search_params are added
            assert "data" in result
            assert result["data"]["existing_key"] == "existing_value"
            assert "search_params" in result["data"]
            search_params = result["data"]["search_params"]
            assert search_params["destination_city"] == "Tokyo"
            assert search_params["country"] == "Japan"

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_no_search_results_no_search_params(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that search_params are not included when there are no hotel search results."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Mock graph result without hotel search results
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="How can I help you?"),
            ],
            "hotel": {},
        }

        # Mock _extract_hotel_search_results to return None
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = None

            result = await invoke_hotel_graph(
                message="Hello",
                user_id="user123",
                chat_id="chat123",
            )

            # Should return conversation response without search_params
            assert result["type"] != "hotel_search_results"
            # search_params should not be in data if no hotel results
            if "data" in result and result["data"] is not None:
                assert "search_params" not in result["data"]


class TestExtractSearchParamsFromMessages:
    """Test cases for _extract_search_params_from_messages function."""

    def test_extract_search_params_from_messages_success(self):
        """Test successful extraction of search params from AIMessage with tool calls."""
        # Create mock AIMessage with tool_calls
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "country_name": "France",
                        "checkin": "2026-04-15",
                        "checkout": "2026-04-20",
                        "rooms": 2,
                        "adults": 4,
                        "children": 1,
                    },
                }
            ]
        )

        messages = [
            HumanMessage(content="I want to book a hotel"),
            mock_ai_message,
        ]

        result = _extract_search_params_from_messages(messages)

        assert result["destination_city"] == "Paris"
        assert result["country"] == "France"
        assert result["check_in_date"] == "2026-04-15"
        assert result["check_out_date"] == "2026-04-20"
        assert result["rooms"] == 2
        assert result["adults"] == 4
        assert result["children"] == 1

    def test_extract_search_params_from_messages_with_defaults(self):
        """Test extraction with default values when fields are missing."""
        # Create mock AIMessage with tool_calls
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "London",
                        "checkin": "2026-04-10",
                        # Missing country, checkout, rooms, adults, children
                    },
                }
            ]
        )

        messages = [mock_ai_message]

        result = _extract_search_params_from_messages(messages)

        assert result["destination_city"] == "London"
        assert result["country"] == ""  # Default empty string
        assert result["check_in_date"] == "2026-04-10"
        assert result["check_out_date"] == ""  # Default empty string
        assert result["rooms"] == 1  # Default
        assert result["adults"] is None  # No default — must be provided
        assert result["children"] == 0  # Default

    def test_extract_search_params_from_messages_reverse_order(self):
        """Test that function finds the most recent search_hotels tool call."""
        # Create mock AIMessages with tool_calls
        mock_ai_message1 = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Tokyo",
                        "checkin": "2026-01-01",
                    },
                }
            ]
        )

        mock_ai_message2 = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "checkin": "2026-04-15",
                    },
                }
            ]
        )

        messages = [mock_ai_message1, mock_ai_message2]

        result = _extract_search_params_from_messages(messages)

        # Should return the most recent (last) search
        assert result["destination_city"] == "Paris"
        assert result["check_in_date"] == "2026-04-15"

    def test_extract_search_params_from_messages_no_search_hotels(self):
        """Test that function returns empty dict when no search_hotels tool call exists."""
        # Create mock AIMessage with different tool call
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "resolve_city",
                    "args": {"city": "Paris"},
                }
            ]
        )

        messages = [mock_ai_message]

        result = _extract_search_params_from_messages(messages)

        assert result == {}

    def test_extract_search_params_from_messages_no_tool_calls(self):
        """Test that function returns empty dict when AIMessage has no tool_calls."""
        messages = [
            AIMessage(content="Just a regular message"),
            HumanMessage(content="User message"),
        ]

        result = _extract_search_params_from_messages(messages)

        assert result == {}

    def test_extract_search_params_from_messages_empty_list(self):
        """Test that function returns empty dict for empty message list."""
        result = _extract_search_params_from_messages([])

        assert result == {}

    def test_extract_search_params_from_messages_none_tool_calls(self):
        """Test that function handles AIMessage with tool_calls=None."""
        # Create mock AIMessage with tool_calls=None
        mock_ai_message = _create_mock_ai_message_with_tool_calls(None)

        messages = [mock_ai_message]

        result = _extract_search_params_from_messages(messages)

        assert result == {}

    def test_extract_search_params_from_messages_empty_tool_calls(self):
        """Test that function handles AIMessage with empty tool_calls list."""
        # Create mock AIMessage with empty tool_calls
        mock_ai_message = _create_mock_ai_message_with_tool_calls([])

        messages = [mock_ai_message]

        result = _extract_search_params_from_messages(messages)

        assert result == {}


class TestExtractSearchParamsFilters:
    """Test that filter fields are correctly extracted from search_hotels tool call args."""

    def test_extract_price_filters(self):
        """price_min and price_max are extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Rome",
                        "country_name": "Italy",
                        "checkin": "2026-05-01",
                        "checkout": "2026-05-05",
                        "adults": 2,
                        "price_min": 80.0,
                        "price_max": 150.0,
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["price_min"] == 80.0
        assert result["price_max"] == 150.0

    def test_extract_min_rating(self):
        """min_rating is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "country_name": "France",
                        "checkin": "2026-06-01",
                        "checkout": "2026-06-05",
                        "adults": 2,
                        "min_rating": 5,
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["min_rating"] == 5

    def test_extract_property_types(self):
        """property_types list is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Ibiza",
                        "country_name": "Spain",
                        "checkin": "2026-07-01",
                        "checkout": "2026-07-07",
                        "adults": 2,
                        "property_types": ["Resort"],
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["property_types"] == ["Resort"]

    def test_extract_refundable_only(self):
        """refundable_only is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "London",
                        "country_name": "UK",
                        "checkin": "2026-08-01",
                        "checkout": "2026-08-03",
                        "adults": 1,
                        "refundable_only": True,
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["refundable_only"] is True

    def test_extract_required_facilities(self):
        """required_facilities list is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Barcelona",
                        "country_name": "Spain",
                        "checkin": "2026-09-01",
                        "checkout": "2026-09-05",
                        "adults": 2,
                        "required_facilities": ["pool", "spa"],
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["required_facilities"] == ["pool", "spa"]

    def test_extract_max_distance_km(self):
        """max_distance_km is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Amsterdam",
                        "country_name": "Netherlands",
                        "checkin": "2026-10-01",
                        "checkout": "2026-10-04",
                        "adults": 2,
                        "max_distance_km": 2.0,
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["max_distance_km"] == 2.0

    def test_extract_locality(self):
        """locality is extracted from tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "country_name": "France",
                        "checkin": "2026-07-15",
                        "checkout": "2026-07-22",
                        "adults": 2,
                        "locality": "Montmartre",
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["locality"] == "Montmartre"

    def test_extract_filters_return_none_when_absent(self):
        """All filter fields return None when not present in tool call args."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Berlin",
                        "country_name": "Germany",
                        "checkin": "2026-11-01",
                        "checkout": "2026-11-05",
                        "adults": 2,
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["price_min"] is None
        assert result["price_max"] is None
        assert result["min_rating"] is None
        assert result["property_types"] is None
        assert result["refundable_only"] is None
        assert result["required_facilities"] is None
        assert result["max_distance_km"] is None
        assert result["locality"] is None

    def test_extract_all_filters_combined(self):
        """All 8 filter fields extracted correctly in one tool call."""
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Dubai",
                        "country_name": "UAE",
                        "checkin": "2026-12-20",
                        "checkout": "2026-12-27",
                        "adults": 2,
                        "price_min": 200.0,
                        "price_max": 500.0,
                        "min_rating": 5,
                        "property_types": ["Resort", "Hotel"],
                        "refundable_only": True,
                        "required_facilities": ["pool", "gym"],
                        "max_distance_km": 5.0,
                        "locality": "Downtown",
                    },
                }
            ]
        )
        result = _extract_search_params_from_messages([mock_ai_message])
        assert result["price_min"] == 200.0
        assert result["price_max"] == 500.0
        assert result["min_rating"] == 5
        assert result["property_types"] == ["Resort", "Hotel"]
        assert result["refundable_only"] is True
        assert result["required_facilities"] == ["pool", "gym"]
        assert result["max_distance_km"] == 5.0
        assert result["locality"] == "Downtown"


class TestInvokeHotelGraphMessageExtraction:
    """Test cases for invoke_hotel_graph using message extraction (bug fix)."""

    @pytest.fixture
    def mock_graph(self):
        """Mock LangGraph instance."""
        graph = MagicMock()
        graph.ainvoke = AsyncMock()
        return graph

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_prefers_messages_over_state(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that invoke_hotel_graph prefers extracting params from messages over state."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Create mock AIMessage with tool_calls
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "country_name": "France",
                        "checkin": "2026-04-15",
                        "checkout": "2026-04-20",
                        "rooms": 2,
                        "adults": 4,
                        "children": 1,
                    },
                }
            ]
        )

        # Mock graph result with AIMessage containing search_hotels tool call
        # and state with different values (to verify messages are preferred)
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="I want to book a hotel in Paris"),
                mock_ai_message,
                ToolMessage(
                    content='{"hotels": [{"hotel_name": "Test Hotel"}], "session_id": "fl_session_123"}',
                    tool_call_id="search_hotels_123",
                ),
            ],
            # State has different values - should be ignored in favor of messages
            "hotel": {
                "city": "London",  # Different from messages
                "country": "UK",  # Different from messages
                "checkin": "2026-01-01",  # Different from messages
                "checkout": "2026-01-05",  # Different from messages
                "rooms": 1,  # Different from messages
                "adults": 2,  # Different from messages
                "children": 0,  # Different from messages
            },
        }

        # Mock _extract_hotel_search_results to return hotel results
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {},
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel in Paris",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify search_params come from messages, not state
            assert result["type"] == "hotel_search_results"
            assert "data" in result
            assert "search_params" in result["data"]
            search_params = result["data"]["search_params"]

            # Should match message values, not state values
            assert search_params["destination_city"] == "Paris"  # From messages
            assert search_params["country"] == "France"  # From messages
            assert search_params["check_in_date"] == "2026-04-15"  # From messages
            assert search_params["check_out_date"] == "2026-04-20"  # From messages
            assert search_params["rooms"] == 2  # From messages
            assert search_params["adults"] == 4  # From messages
            assert search_params["children"] == 1  # From messages

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_falls_back_to_state_when_messages_fail(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that invoke_hotel_graph falls back to state when message extraction fails."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Mock graph result without search_hotels tool call in messages
        # (message extraction will fail, should fall back to state)
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="I want to book a hotel"),
                AIMessage(content="I found some hotels"),  # No tool_calls
                ToolMessage(
                    content='{"hotels": [{"hotel_name": "Test Hotel"}], "session_id": "fl_session_123"}',
                    tool_call_id="search_hotels_123",
                ),
            ],
            # State has the values - should be used as fallback
            "hotel": {
                "city": "Tokyo",
                "country": "Japan",
                "checkin": "2026-04-01",
                "checkout": "2026-04-10",
                "rooms": 1,
                "adults": 2,
                "children": 0,
            },
        }

        # Mock _extract_hotel_search_results to return hotel results
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {},
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify search_params come from state (fallback)
            assert result["type"] == "hotel_search_results"
            assert "data" in result
            assert "search_params" in result["data"]
            search_params = result["data"]["search_params"]

            # Should match state values
            assert search_params["destination_city"] == "Tokyo"
            assert search_params["country"] == "Japan"
            assert search_params["check_in_date"] == "2026-04-01"
            assert search_params["check_out_date"] == "2026-04-10"
            assert search_params["rooms"] == 1
            assert search_params["adults"] == 2
            assert search_params["children"] == 0

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.hotel_graph.create_checkpointer",
        return_value=(MagicMock(), MagicMock()),
    )
    @patch("app.ai.graph.hotel_graph.get_hotel_graph")
    @patch("app.ai.graph.hotel_graph.traced_observation")
    async def test_invoke_hotel_graph_falls_back_when_destination_city_missing(
        self, mock_traced_observation, mock_get_graph, mock_checkpointer, mock_graph
    ):
        """Test that invoke_hotel_graph falls back to state when extracted params lack destination_city."""
        # Setup mocks
        mock_checkpointer.return_value = MagicMock()
        mock_get_graph.return_value = mock_graph

        # Mock traced_observation context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=(None, None, None))
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_traced_observation.return_value = mock_context

        # Create mock AIMessage with tool_calls but missing city_name
        mock_ai_message = _create_mock_ai_message_with_tool_calls(
            [
                {
                    "name": "search_hotels",
                    "args": {
                        # Missing city_name - should trigger fallback
                        "checkin": "2026-04-15",
                        "checkout": "2026-04-20",
                    },
                }
            ]
        )

        # Mock graph result with search_hotels tool call but missing city_name
        mock_graph.ainvoke.return_value = {
            "messages": [mock_ai_message],
            # State has complete values - should be used
            "hotel": {
                "city": "Berlin",
                "country": "Germany",
                "checkin": "2026-04-15",
                "checkout": "2026-04-20",
                "rooms": 1,
                "adults": 2,
                "children": 0,
            },
        }

        # Mock _extract_hotel_search_results
        with patch(
            "app.ai.graph.hotel_graph._extract_hotel_search_results"
        ) as mock_extract:
            mock_extract.return_value = {
                "hotels": [{"hotel_name": "Test Hotel"}],
                "session_id": "fl_session_123",
                "data": {},
            }

            result = await invoke_hotel_graph(
                message="I want to book a hotel",
                user_id="user123",
                chat_id="chat123",
            )

            # Verify search_params come from state (fallback due to missing destination_city)
            assert result["type"] == "hotel_search_results"
            search_params = result["data"]["search_params"]

            # Should match state values
            assert search_params["destination_city"] == "Berlin"
            assert search_params["country"] == "Germany"


class TestExtractHotelNoResultsMessage:
    """Tests for _extract_hotel_no_results_message."""

    def _make_tool_msg(self, content: str | dict) -> ToolMessage:
        """Create a ToolMessage with the given content."""
        import json

        msg = MagicMock(spec=ToolMessage)
        msg.__class__ = ToolMessage
        msg.name = "search_hotels"
        msg.content = json.dumps(content) if isinstance(content, dict) else content
        return msg

    def test_returns_message_with_suggestion(self) -> None:
        """Returns combined message + suggestion when status is no_results."""
        msg = self._make_tool_msg(
            {
                "status": "no_results",
                "message": "No hotels found in that area.",
                "suggestion": "Try searching near the Eiffel Tower instead.",
            }
        )
        result = _extract_hotel_no_results_message([msg])
        assert (
            result
            == "No hotels found in that area. Try searching near the Eiffel Tower instead."
        )

    def test_returns_message_without_suggestion(self) -> None:
        """Returns just the message when no suggestion is present."""
        msg = self._make_tool_msg(
            {"status": "no_results", "message": "No hotels available."}
        )
        result = _extract_hotel_no_results_message([msg])
        assert result == "No hotels available."

    def test_defaults_message_when_missing(self) -> None:
        """Falls back to default message when 'message' key absent."""
        msg = self._make_tool_msg({"status": "no_results"})
        result = _extract_hotel_no_results_message([msg])
        assert result == "No hotels found."

    def test_skips_non_no_results_status(self) -> None:
        """Returns None when the tool result has a different status."""
        msg = self._make_tool_msg({"status": "success", "hotels": []})
        result = _extract_hotel_no_results_message([msg])
        assert result is None

    def test_skips_non_search_hotels_tool(self) -> None:
        """Returns None when the ToolMessage is from a different tool."""
        msg = MagicMock(spec=ToolMessage)
        msg.__class__ = ToolMessage
        msg.name = "resolve_city"
        msg.content = '{"status": "no_results"}'
        result = _extract_hotel_no_results_message([msg])
        assert result is None

    def test_handles_dict_content(self) -> None:
        """Handles content that is already a dict (not a JSON string)."""
        msg = MagicMock(spec=ToolMessage)
        msg.__class__ = ToolMessage
        msg.name = "search_hotels"
        msg.content = {
            "status": "no_results",
            "message": "No hotels found in that area.",
        }
        result = _extract_hotel_no_results_message([msg])
        assert result == "No hotels found in that area."

    def test_returns_none_for_empty_messages(self) -> None:
        """Returns None when messages list is empty."""
        result = _extract_hotel_no_results_message([])
        assert result is None

    def test_uses_most_recent_no_results_message(self) -> None:
        """Scans messages in reverse — returns the latest no_results."""
        old_msg = self._make_tool_msg(
            {"status": "no_results", "message": "Old message."}
        )
        new_msg = self._make_tool_msg(
            {"status": "no_results", "message": "New message."}
        )
        result = _extract_hotel_no_results_message([old_msg, new_msg])
        assert result == "New message."
