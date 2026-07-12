"""Unit tests for the general travel agent (LangGraph).

Tests the general_graph module without invoking the full LangGraph agent.
Imports are done inside test methods to avoid circular import issues.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInvokeGeneralGraph:
    """Tests for invoke_general_graph."""

    @pytest.mark.asyncio
    async def test_returns_expected_response_format(self) -> None:
        """invoke_general_graph returns dict with message, type, intent_name, message_id."""
        from langchain_core.messages import AIMessage

        from app.ai.graph.general_graph import invoke_general_graph

        with patch("app.ai.graph.general_graph.get_general_graph") as mock_get_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {
                "messages": [
                    AIMessage(
                        content="Welcome to Voya! How can I help you plan your trip?"
                    )
                ],
            }
            mock_get_graph.return_value = mock_graph

            result = await invoke_general_graph(
                message="Hello",
                user_id="test-user",
                chat_id="test-chat",
            )

            assert "message" in result
            assert "type" in result
            assert "intent_name" in result
            assert "message_id" in result
            assert result["type"] == "ai_response"
            assert result["intent_name"] == "general_query"
            assert (
                result["message"]
                == "Welcome to Voya! How can I help you plan your trip?"
            )

    @pytest.mark.asyncio
    async def test_returns_fallback_on_error(self) -> None:
        """invoke_general_graph returns fallback response when graph fails."""
        from app.ai.graph.general_graph import invoke_general_graph

        with patch("app.ai.graph.general_graph.get_general_graph") as mock_get_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.side_effect = Exception("LLM failed")
            mock_get_graph.return_value = mock_graph

            result = await invoke_general_graph(
                message="Hello",
                user_id="test-user",
                chat_id="test-chat",
            )

            assert result["type"] == "fallback_response"
            assert "message" in result
            assert result["message_id"] is not None

    @pytest.mark.asyncio
    async def test_passes_chat_id_as_thread_id(self) -> None:
        """invoke_general_graph uses chat_id as thread_id for checkpointer."""
        from langchain_core.messages import AIMessage

        from app.ai.graph.general_graph import invoke_general_graph

        with patch("app.ai.graph.general_graph.get_general_graph") as mock_get_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {
                "messages": [AIMessage(content="Hi!")],
            }
            mock_get_graph.return_value = mock_graph

            await invoke_general_graph(
                message="Hello",
                user_id="test-user",
                chat_id="my-chat-123",
            )

            # Verify ainvoke was called with correct thread_id config
            call_args = mock_graph.ainvoke.call_args
            config = call_args[0][1]  # Second positional arg is config
            assert config["configurable"]["thread_id"] == "my-chat-123"

    @pytest.mark.asyncio
    async def test_empty_ai_response_returns_fallback_message(self) -> None:
        """invoke_general_graph returns fallback when AI response is empty."""
        from app.ai.graph.general_graph import invoke_general_graph

        with patch("app.ai.graph.general_graph.get_general_graph") as mock_get_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"messages": []}
            mock_get_graph.return_value = mock_graph

            result = await invoke_general_graph(
                message="Hello",
                user_id="test-user",
                chat_id="test-chat",
            )

            assert result["message"] != ""
            assert result["type"] == "ai_response"


class TestGeneralGraphCreation:
    """Tests for get_general_graph singleton."""

    def test_get_general_graph_creates_singleton(self) -> None:
        """get_general_graph returns the same instance on repeated calls."""
        import app.ai.graph.general_graph as module

        # Reset singleton
        module._general_compiled_graph = None

        with (
            patch(
                "app.ai.graph.general_graph.create_checkpointer",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "app.ai.graph.general_graph.create_agent_engine",
                return_value=MagicMock(),
            ) as mock_create,
        ):
            graph1 = module.get_general_graph()
            graph2 = module.get_general_graph()

            assert graph1 is graph2
            mock_create.assert_called_once()

        # Cleanup
        module._general_compiled_graph = None


class TestGeneralGraphCleanup:
    """Tests for cleanup_general_graph."""

    def test_cleanup_closes_mongo_client(self) -> None:
        """cleanup_general_graph closes MongoDB connection."""
        import app.ai.graph.general_graph as module

        mock_client = MagicMock()
        module._general_mongo_client = mock_client
        module._general_checkpointer = MagicMock()
        module._general_compiled_graph = MagicMock()

        module.cleanup_general_graph()

        mock_client.close.assert_called_once()
        assert module._general_mongo_client is None
        assert module._general_checkpointer is None
        assert module._general_compiled_graph is None

    def test_cleanup_handles_no_client(self) -> None:
        """cleanup_general_graph handles case where client is None."""
        import app.ai.graph.general_graph as module

        module._general_mongo_client = None
        module._general_checkpointer = None
        module._general_compiled_graph = None

        # Should not raise
        module.cleanup_general_graph()


class TestGeneralPrompt:
    """Tests for the general agent prompt."""

    def test_prompt_has_date_placeholders(self) -> None:
        """General prompt contains current_date and current_year placeholders."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "{current_date}" in GENERAL_AGENT_PROMPT
        assert "{current_year}" in GENERAL_AGENT_PROMPT

    def test_prompt_no_message_placeholder(self) -> None:
        """General prompt should NOT have {message} — LangGraph handles messages via state."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "{message}" not in GENERAL_AGENT_PROMPT

    def test_prompt_no_specific_context_placeholder(self) -> None:
        """General prompt should NOT have {specific_context} — removed in V2."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "{specific_context}" not in GENERAL_AGENT_PROMPT

    def test_prompt_formats_with_date_variables(self) -> None:
        """General prompt can be formatted with date variables."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        formatted = GENERAL_AGENT_PROMPT.format(
            current_date="2026-02-27",
            current_year=2026,
        )

        assert "2026-02-27" in formatted
        assert "2026" in formatted

    def test_prompt_has_hand_back_rules(self) -> None:
        """General prompt contains hand-back guidance."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "Hand-Back to Supervisor" in GENERAL_AGENT_PROMPT
        assert "NEVER hand back for ambiguous" in GENERAL_AGENT_PROMPT

    def test_prompt_has_travel_bias_rule(self) -> None:
        """General prompt contains travel-bias rule for ambiguous messages."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "TRAVEL assistant" in GENERAL_AGENT_PROMPT
        assert "travel lens" in GENERAL_AGENT_PROMPT

    def test_prompt_has_save_travel_context_section(self) -> None:
        """General prompt mentions save_travel_context tool."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "save_travel_context" in GENERAL_AGENT_PROMPT

    def test_prompt_has_booking_hand_back_triggers(self) -> None:
        """General prompt lists booking-related terms that trigger hand-back."""
        from app.ai.graph.prompts.general_agent import (
            GENERAL_AGENT_PROMPT,
        )

        assert "round trip" in GENERAL_AGENT_PROMPT
        assert "one way" in GENERAL_AGENT_PROMPT
        assert "full trip" in GENERAL_AGENT_PROMPT
