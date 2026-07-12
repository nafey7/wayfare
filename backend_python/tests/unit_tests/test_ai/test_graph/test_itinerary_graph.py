"""Unit tests for LangGraph itinerary graph (V2).

Tests the itinerary graph singleton, invoke function, cleanup,
and prompt configuration.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.graph.prompts.itinerary_agent import ITINERARY_AGENT_PROMPT


class TestItineraryAgentPrompt:
    """Tests for the itinerary agent prompt template."""

    def test_prompt_has_current_date_placeholder(self) -> None:
        assert "{current_date}" in ITINERARY_AGENT_PROMPT

    def test_prompt_has_current_year_placeholder(self) -> None:
        assert "{current_year}" in ITINERARY_AGENT_PROMPT

    def test_prompt_does_not_have_message_placeholder(self) -> None:
        """Agent prompt should NOT have {message} — messages come via conversation."""
        assert "{message}" not in ITINERARY_AGENT_PROMPT

    def test_prompt_mentions_key_tools(self) -> None:
        """Prompt mentions tools that need usage guidance (agent gets full list from tool schemas)."""
        assert "update_trip_info" in ITINERARY_AGENT_PROMPT
        assert "generate_itinerary" in ITINERARY_AGENT_PROMPT
        assert "parsing dates" in ITINERARY_AGENT_PROMPT.lower()

    def test_prompt_instructs_to_use_tools_not_self(self) -> None:
        """Agent must use tools, not generate itineraries/budgets itself."""
        assert "generate_itinerary" in ITINERARY_AGENT_PROMPT

    def test_prompt_mentions_no_booking(self) -> None:
        """Agent should know it hands back for booking, not book itself."""
        lower = ITINERARY_AGENT_PROMPT.lower()
        assert (
            "NOT book" in ITINERARY_AGENT_PROMPT
            or "do NOT book" in lower
            or "hand_back_to_supervisor" in lower
        )


class TestCleanupItineraryGraph:
    """Tests for cleanup_itinerary_graph function."""

    def test_cleanup_resets_all_singletons(self) -> None:
        """Cleanup should reset all module-level singletons to None."""
        import app.ai.graph.itinerary_graph as module

        # Set singletons to mock values
        module._itinerary_checkpointer = MagicMock()
        module._itinerary_mongo_client = MagicMock()
        module._itinerary_compiled_graph = MagicMock()

        module.cleanup_itinerary_graph()

        assert module._itinerary_checkpointer is None
        assert module._itinerary_mongo_client is None
        assert module._itinerary_compiled_graph is None

    def test_cleanup_closes_mongo_client(self) -> None:
        """Cleanup should call close() on the MongoDB client."""
        import app.ai.graph.itinerary_graph as module

        mock_client = MagicMock()
        module._itinerary_mongo_client = mock_client
        module._itinerary_checkpointer = MagicMock()
        module._itinerary_compiled_graph = MagicMock()

        module.cleanup_itinerary_graph()

        mock_client.close.assert_called_once()

    def test_cleanup_noop_when_not_initialized(self) -> None:
        """Cleanup should be safe to call when singletons are None."""
        import app.ai.graph.itinerary_graph as module

        module._itinerary_checkpointer = None
        module._itinerary_mongo_client = None
        module._itinerary_compiled_graph = None

        # Should not raise
        module.cleanup_itinerary_graph()


class TestInvokeItineraryGraph:
    """Tests for invoke_itinerary_graph function."""

    @pytest.mark.asyncio
    async def test_returns_required_keys(self) -> None:
        """Response dict must contain all required keys."""
        mock_result = {
            "messages": [
                HumanMessage(content="Plan a trip to Paris"),
                AIMessage(content="I'd love to help you plan a trip to Paris!"),
            ],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            # Setup traced_observation context manager
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip to Paris",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert "message" in result
        assert "type" in result
        assert "intent_name" in result
        assert "message_id" in result
        assert "response_time" in result

    @pytest.mark.asyncio
    async def test_intent_name_default(self) -> None:
        """Default intent_name should be 'create_itinerary'."""
        mock_result = {
            "messages": [AIMessage(content="Planning your trip!")],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert result["intent_name"] == "create_itinerary"

    @pytest.mark.asyncio
    async def test_extracts_last_ai_message(self) -> None:
        """Should extract text from the last AIMessage in results."""
        mock_result = {
            "messages": [
                HumanMessage(content="Plan a trip to Tokyo"),
                AIMessage(content="First response"),
                AIMessage(content="Here's your Tokyo itinerary!"),
            ],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip to Tokyo",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert "Tokyo itinerary" in result["message"]

    @pytest.mark.asyncio
    async def test_empty_ai_response_returns_fallback(self) -> None:
        """Empty AI response should return friendly fallback message."""
        mock_result = {
            "messages": [HumanMessage(content="Plan a trip")],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert result["message"] != ""
        assert "trip" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_graph_error_returns_fallback(self) -> None:
        """Graph invocation error should return fallback response."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM failed"))

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert result["type"] == "fallback_response"
        assert result["message"] != ""
        assert result["intent_name"] == "create_itinerary"

    @pytest.mark.asyncio
    async def test_graph_creation_error_returns_fallback(self) -> None:
        """If get_itinerary_graph() fails, should return fallback."""
        with patch(
            "app.ai.graph.itinerary_graph.get_itinerary_graph",
            side_effect=ValueError("No API key"),
        ):
            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert result["type"] == "fallback_response"
        assert result["message"] != ""

    @pytest.mark.asyncio
    async def test_chat_id_passed_as_thread_id(self) -> None:
        """chat_id should be used as thread_id in config for checkpointing."""
        mock_result = {
            "messages": [AIMessage(content="Planning!")],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="my_chat_id",
            )

        # Verify ainvoke was called with correct thread_id
        call_args = mock_graph.ainvoke.call_args
        config = call_args[0][1]  # second positional arg is config
        assert config["configurable"]["thread_id"] == "my_chat_id"

    @pytest.mark.asyncio
    async def test_response_time_is_positive(self) -> None:
        """Response time should be a positive number."""
        mock_result = {
            "messages": [AIMessage(content="Done!")],
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_graph",
                return_value=mock_graph,
            ),
            patch(
                "app.ai.graph.itinerary_graph.traced_observation",
            ) as mock_traced,
        ):
            mock_traced.return_value.__enter__ = MagicMock(
                return_value=(None, None, None)
            )
            mock_traced.return_value.__exit__ = MagicMock(return_value=False)

            from app.ai.graph.itinerary_graph import invoke_itinerary_graph

            result = await invoke_itinerary_graph(
                message="Plan a trip",
                user_id="user_123",
                chat_id="chat_456",
            )

        assert result["response_time"] > 0


class TestGetItineraryGraph:
    """Tests for get_itinerary_graph singleton."""

    def test_singleton_returns_same_instance(self) -> None:
        """get_itinerary_graph should return the same instance on repeated calls."""
        import app.ai.graph.itinerary_graph as module

        mock_graph = MagicMock()
        module._itinerary_compiled_graph = mock_graph

        result = module.get_itinerary_graph()
        assert result is mock_graph

    def test_cleanup_allows_recreation(self) -> None:
        """After cleanup, get_itinerary_graph should create a new instance."""
        import app.ai.graph.itinerary_graph as module

        mock_graph = MagicMock()
        module._itinerary_compiled_graph = mock_graph
        module._itinerary_mongo_client = MagicMock()
        module._itinerary_checkpointer = MagicMock()

        module.cleanup_itinerary_graph()

        assert module._itinerary_compiled_graph is None


def _make_mock_itinerary_result():
    """Create a mock StructuredItineraryResult for testing."""
    from app.ai.graph.tools.itinerary import (
        BudgetSnapshot,
        DayTip,
        ExpandedContent,
        ItineraryActivity,
        ItineraryDay,
        LocalExperience,
        StructuredItineraryResult,
    )

    return StructuredItineraryResult(
        itinerary_items=[
            ItineraryDay(
                day=1,
                title="Arrival & Asakusa",
                description="Arrive in Tokyo and explore Asakusa.",
                expanded_content=ExpandedContent(
                    activities=[
                        ItineraryActivity(
                            location="Narita Airport",
                            description="✈️ Arrive at Narita and take express to hotel.",
                            duration="2h",
                        ),
                        ItineraryActivity(
                            location="Senso-ji Temple",
                            description="🛕 Visit Tokyo's oldest temple.",
                            duration="1h 30m",
                        ),
                    ],
                    tip=DayTip(text="Get a Suica card at the airport"),
                ),
            ),
            ItineraryDay(
                day=2,
                title="Shibuya & Harajuku",
                description="Explore trendy neighbourhoods.",
                expanded_content=ExpandedContent(
                    activities=[
                        ItineraryActivity(
                            location="Meiji Shrine",
                            description="⛩️ Peaceful morning walk.",
                            duration="1h 30m",
                        ),
                    ],
                    tip=DayTip(text="Visit Shibuya crossing at night"),
                ),
            ),
            ItineraryDay(
                day=3,
                title="Departure",
                description="Last morning in Tokyo.",
                expanded_content=ExpandedContent(
                    activities=[
                        ItineraryActivity(
                            location="Ueno Park",
                            description="🌸 Morning stroll in the park.",
                            duration="1h",
                        ),
                    ],
                    tip=DayTip(text="Leave early for Narita"),
                ),
            ),
        ],
        budget_snapshot=BudgetSnapshot(
            description="Expect around $2,000 USD per person"
        ),
        local_experiences=[
            LocalExperience(
                id="1", title="Ramen Tour", description="Try authentic ramen."
            ),
        ],
    )


class TestGenerateItineraryTool:
    """Tests for the generate_itinerary smart tool."""

    @pytest.mark.asyncio
    async def test_returns_content_and_artifact_tuple(self) -> None:
        """Raw function returns (content_str, artifact_dict) tuple."""
        mock_result = _make_mock_itinerary_result()

        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            # Call the underlying coroutine directly to get the raw tuple
            result = await generate_itinerary.coroutine(
                destination="Tokyo, Japan",
                num_days=3,
                origin="Los Angeles",  # #1127: origin required on first generation
                adults=2,
                interests=["temples", "food"],
            )

        # Raw function returns (str, dict) tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
        content_str, artifact = result

        # Content: compact JSON with summary (no itinerary data)
        content = json.loads(content_str)
        assert content["status"] == "success"
        assert content["destination"] == "Tokyo, Japan"
        assert "instruction" in content
        assert "itinerary" not in content  # itinerary NOT in content

        # Artifact: full itinerary dict
        assert isinstance(artifact, dict)
        assert len(artifact["itineraryItems"]) == 3
        assert artifact["itineraryItems"][0]["title"] == "Arrival & Asakusa"

    @pytest.mark.asyncio
    async def test_ainvoke_returns_content_string(self) -> None:
        """ainvoke() extracts content string from content_and_artifact tuple."""
        mock_result = _make_mock_itinerary_result()

        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo, Japan",
                    "num_days": 3,
                    "origin": "Los Angeles",  # #1127: origin required
                    "adults": 2,
                    "interests": ["temples", "food"],
                }
            )

        # ainvoke returns content string (not tuple)
        assert isinstance(result_str, str)
        result = json.loads(result_str)
        assert result["status"] == "success"
        assert result["destination"] == "Tokyo, Japan"
        assert "instruction" in result

    @pytest.mark.asyncio
    async def test_num_days_auto_calculated_from_dates(self) -> None:
        """num_days=0 with both dates calculates correct duration."""
        mock_result = _make_mock_itinerary_result()

        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ) as mock_llm,
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 0,
                    "origin": "Los Angeles",  # #1127: origin required
                    "departure_date": "2026-04-10",
                    "return_date": "2026-04-17",
                }
            )

        # Tool should have computed num_days=8 (Apr 10-17 inclusive = 8 days)
        call_kwargs = mock_llm.call_args
        assert call_kwargs[1]["num_days"] == 8

    @pytest.mark.asyncio
    async def test_num_days_explicit_passthrough(self) -> None:
        """Explicit num_days>0 is used as-is without date derivation."""
        mock_result = _make_mock_itinerary_result()

        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ) as mock_llm,
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                    "origin": "Los Angeles",  # #1127: origin required
                }
            )

        call_kwargs = mock_llm.call_args
        assert call_kwargs[1]["num_days"] == 5

    @pytest.mark.asyncio
    async def test_num_days_zero_no_dates_returns_error(self) -> None:
        """num_days=0 without dates returns error content string."""
        from app.ai.graph.tools.itinerary import generate_itinerary

        # ainvoke extracts the content string from the (error_json, {}) tuple
        # #1127: pass origin so we hit the num_days gate, not the missing-origin gate
        result_str = await generate_itinerary.ainvoke(
            {
                "destination": "Tokyo",
                "num_days": 0,
                "origin": "Los Angeles",
            }
        )

        content = json.loads(result_str)
        assert content["status"] == "error"
        assert "duration" in content["error"].lower()

    @pytest.mark.asyncio
    async def test_num_days_zero_no_dates_raw_returns_error_tuple(self) -> None:
        """Raw coroutine: num_days=0 without dates returns (error_json, {})."""
        from app.ai.graph.tools.itinerary import generate_itinerary

        result = await generate_itinerary.coroutine(destination="Tokyo", num_days=0)

        assert isinstance(result, tuple)
        content = json.loads(result[0])
        assert content["status"] == "error"
        assert result[1] == {}

    @pytest.mark.asyncio
    async def test_num_days_zero_invalid_dates_returns_error(self) -> None:
        """num_days=0 with malformed dates returns error."""
        from app.ai.graph.tools.itinerary import generate_itinerary

        result = await generate_itinerary.coroutine(
            destination="Tokyo",
            num_days=0,
            departure_date="not-a-date",
            return_date="also-bad",
        )

        assert isinstance(result, tuple)
        content = json.loads(result[0])
        assert content["status"] == "error"
        assert result[1] == {}

    @pytest.mark.asyncio
    async def test_error_on_llm_failure_returns_tuple(self) -> None:
        """LLM failure returns (error_json, {}) tuple — not bare string."""
        with patch(
            "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result = await generate_itinerary.coroutine(destination="Tokyo", num_days=3)

        assert isinstance(result, tuple)
        content_str, artifact = result
        content = json.loads(content_str)
        assert content["status"] == "error"
        assert "instruction" in content
        assert artifact == {}

    @pytest.mark.asyncio
    async def test_enrichment_timeout_does_not_block_response(self) -> None:
        """#1053 Phase 1 O6: enrichment is capped — slow enrichment must NOT
        block the itinerary response. When ``enrich_itinerary`` takes longer
        than ENRICHMENT_TIMEOUT_S, the tool returns the (partially-enriched)
        itinerary anyway with status="success"."""
        import asyncio as _asyncio
        import time as _time

        mock_result = _make_mock_itinerary_result()

        async def _slow_enrich(itinerary: object, destination: str) -> object:
            # Simulate a slow Google Places / Routes round trip — much longer
            # than the 4.0s ENRICHMENT_TIMEOUT_S cap.
            await _asyncio.sleep(5.5)
            return itinerary

        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                side_effect=_slow_enrich,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            t0 = _time.monotonic()
            result = await generate_itinerary.coroutine(
                destination="Tokyo, Japan",
                num_days=3,
                origin="Los Angeles",  # #1127: origin required
            )
            elapsed = _time.monotonic() - t0

        # Must complete in roughly the timeout window (4.0s) + small overhead,
        # NOT the full 5.5s the slow enricher would otherwise take. Generous
        # ceiling at 5.0s to avoid CI flakiness while still catching the
        # "didn't cap at all" regression.
        assert elapsed < 5.0, (
            f"Enrichment timeout failed to cap latency: took {elapsed:.2f}s "
            f"(expected ~4.0s)"
        )
        # Itinerary is still returned successfully (partial enrichment is fine)
        assert isinstance(result, tuple)
        content_str, artifact = result
        content = json.loads(content_str)
        assert content["status"] == "success"
        assert artifact  # non-empty dict


class TestPopulateItineraryImages:
    """Regression tests for image enrichment task ordering (#1143)."""

    @pytest.mark.asyncio
    async def test_local_experience_tasks_queued_before_day_tasks(self) -> None:
        """Local experience image tasks must be queued FIRST so they complete
        within the enrichment timeout budget rather than being starved by the
        larger pool of day-card + activity tasks."""
        from unittest.mock import AsyncMock, patch

        from app.ai.graph.enrichment import populate_itinerary_images
        from app.ai.graph.tools.itinerary import (
            BudgetSnapshot,
            DayTip,
            ExpandedContent,
            ItineraryActivity,
            ItineraryDay,
            LocalExperience,
            StructuredItineraryResult,
        )

        call_order: list[str] = []

        async def _mock_resolve(place_name: str, max_width: int) -> str:
            call_order.append(place_name)
            return f"/api/places/photos/fake/media?q={place_name}"

        mock_client = AsyncMock()
        mock_client.api_key = "fake-key"
        mock_client.resolve_place_image_url.side_effect = _mock_resolve

        activity = ItineraryActivity(
            location="Big Ben",
            description="Visit Big Ben",
            image_url="",
            duration="1h",
        )
        day = ItineraryDay(
            day=1,
            title="Westminster",
            description="Day 1",
            image_url="",
            expanded_content=ExpandedContent(
                activities=[activity],
                tip=DayTip(text="Sample tip"),
            ),
        )
        exp = LocalExperience(
            id="1", title="Afternoon Tea", description="Classic ritual", image_url=""
        )

        result = StructuredItineraryResult(
            itinerary_items=[day],
            local_experiences=[exp],
            footer_section_title="Must-Try",
            budget_snapshot=BudgetSnapshot(description="~$500 USD per person"),
        )

        with patch(
            "integrations.googleplaces.client.GooglePlacesClient",
            return_value=mock_client,
        ):
            await populate_itinerary_images(result, "London")

        # Local experience query must appear before day-card queries
        assert call_order, "No places queries were made"
        local_exp_idx = next(
            (i for i, q in enumerate(call_order) if "Afternoon Tea" in q), None
        )
        day_card_idx = next(
            (i for i, q in enumerate(call_order) if "Westminster" in q), None
        )
        assert local_exp_idx is not None, "Local experience query not found"
        assert day_card_idx is not None, "Day card query not found"
        assert local_exp_idx < day_card_idx, (
            f"Local experience task (idx {local_exp_idx}) must be queued "
            f"before day-card task (idx {day_card_idx})"
        )


class TestGenerateItineraryCountryOnlyOriginGate:
    """Regression tests for #1105: hard tool-level gate blocks generation
    when the user's origin resolved to a country, not a city.

    Prompt-level BLOCKING is unreliable (LLM ignores it ~half the time);
    this gate makes the refusal deterministic.
    """

    @pytest.mark.asyncio
    async def test_country_only_origin_blocks_generation(self) -> None:
        """Supervisor sets ``block_country_only_origin=True`` → tool refuses."""
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        result_str = await generate_itinerary.ainvoke(
            {
                "destination": "Tokyo",
                "num_days": 7,
                "origin": "the US",
                "adults": 1,
            },
            config={
                "configurable": {
                    "block_country_only_origin": True,
                    "country_only_origin_value": "the US",
                }
            },
        )

        result = json.loads(result_str)
        assert result["status"] == "error"
        assert "the US" in result["error"]
        assert "specific city" in result["error"] or "country" in result["error"]
        # Instruction must direct the agent to ask + suggest cities + NOT retry.
        instr = result["instruction"]
        instr_lower = instr.lower()
        assert "which city of the us" in instr_lower
        assert "iata" in instr_lower
        assert "do not retry generate_itinerary" in instr_lower

    @pytest.mark.asyncio
    async def test_country_only_origin_uses_origin_when_value_missing(self) -> None:
        """If supervisor didn't pass ``country_only_origin_value``, fall back
        to the ``origin`` arg the agent passed (defensive)."""
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        result_str = await generate_itinerary.ainvoke(
            {
                "destination": "Paris",
                "num_days": 5,
                "origin": "India",
                "adults": 1,
            },
            config={
                "configurable": {
                    "block_country_only_origin": True,
                    # country_only_origin_value absent — falls back to origin arg
                }
            },
        )

        result = json.loads(result_str)
        assert result["status"] == "error"
        assert "India" in result["error"]

    @pytest.mark.asyncio
    async def test_no_block_when_flag_off(self) -> None:
        """Without ``block_country_only_origin`` the gate stays open
        (default behaviour for normal city origins)."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 3,
                    "origin": "Los Angeles",
                    "adults": 1,
                },
                config={"configurable": {"block_country_only_origin": False}},
            )

        result = json.loads(result_str)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_itinerary_already_generated_bypasses_gate(self) -> None:
        """Re-generation of an EXISTING itinerary skips the gate — origin
        disambiguation only matters on the FIRST plan. The signal comes from
        the supervisor-set ``itinerary_already_generated`` flag (NOT from a
        hallucinated ``modification_notes`` string).
        """
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 7,
                    "origin": "the US",
                    "adults": 1,
                    "modification_notes": "Make day 3 a free day instead",
                },
                config={
                    "configurable": {
                        "block_country_only_origin": True,
                        "country_only_origin_value": "the US",
                        "itinerary_already_generated": True,
                    }
                },
            )

        result = json.loads(result_str)
        # Gate bypassed — LLM regen ran.
        assert result["status"] == "success"

    async def test_modification_notes_alone_does_not_bypass_gate(self) -> None:
        """Defensive: if the LLM hallucinates ``modification_notes`` on a first
        call (no real itinerary yet), the gate must still fire because
        ``itinerary_already_generated`` is False.
        """
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        result_str = await generate_itinerary.ainvoke(
            {
                "destination": "Tokyo",
                "num_days": 7,
                "origin": "the US",
                "adults": 1,
                "modification_notes": "Make day 3 a free day instead",
            },
            config={
                "configurable": {
                    "block_country_only_origin": True,
                    "country_only_origin_value": "the US",
                    # itinerary_already_generated omitted → False
                }
            },
        )

        result = json.loads(result_str)
        assert result["status"] == "error"
        assert "country" in result["error"].lower()


class TestGenerateItineraryRegionDestinationGate:
    """Regression tests for #1053 Phase 2 R5/R6: hard tool-level gate blocks
    generation when ``destination`` names a continent / region instead of a
    specific city.

    Prompt-level BLOCKING (Phase 2 O11) is unreliable — about 1 in 3 runs the
    LLM ignores the suggestion-flow rule and calls generate_itinerary with
    "Europe" as the destination, producing a nonsense "4-day Europe
    itinerary". This gate makes the refusal deterministic.
    """

    @pytest.mark.asyncio
    async def test_continent_destination_blocks_generation(self) -> None:
        """destination='Europe' → tool refuses with actionable instruction."""
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        result_str = await generate_itinerary.ainvoke(
            {"destination": "Europe", "num_days": 4, "adults": 1},
        )
        result = json.loads(result_str)
        assert result["status"] == "error"
        assert "Europe" in result["error"]
        assert (
            "region" in result["error"].lower()
            or "continent" in result["error"].lower()
        )
        # Instruction must guide the agent to suggest cities + NOT retry.
        instr = result["instruction"].lower()
        assert "suggest" in instr
        assert "do not retry generate_itinerary" in instr

    @pytest.mark.asyncio
    async def test_sub_region_destination_blocks_generation(self) -> None:
        """Sub-regions like 'the Caribbean' / 'Southeast Asia' are blocked too."""
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        for region in ("the Caribbean", "Southeast Asia", "Scandinavia"):
            result_str = await generate_itinerary.ainvoke(
                {"destination": region, "num_days": 5, "adults": 1},
            )
            result = json.loads(result_str)
            assert result["status"] == "error", (
                f"Expected region {region!r} to be blocked, got: {result}"
            )

    @pytest.mark.asyncio
    async def test_real_city_passes_gate(self) -> None:
        """Specific cities pass the gate — generation proceeds normally."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 3,
                    "origin": "Los Angeles",  # #1127: origin required
                    "departure_date": "2026-07-10",
                    "return_date": "2026-07-12",
                    "adults": 1,
                },
            )

        result = json.loads(result_str)
        # Gate did not fire — generation proceeded.
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_region_destination_with_itinerary_already_generated_bypasses(
        self,
    ) -> None:
        """Re-generation of an existing plan skips the region gate — the
        original plan was for a real city; the user is now amending. Bypass
        requires the supervisor's ``itinerary_already_generated`` flag.
        """
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Europe",
                    "num_days": 4,
                    "adults": 1,
                    "modification_notes": "Make day 2 more relaxed",
                },
                config={"configurable": {"itinerary_already_generated": True}},
            )

        result = json.loads(result_str)
        # Gate bypassed when supervisor signals re-generation of an existing plan.
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_modification_notes_alone_does_not_bypass_region_gate(self) -> None:
        """Defensive: a hallucinated ``modification_notes`` on a FIRST call
        (no real itinerary yet) must NOT slip past the region gate. Bypass
        requires the supervisor's ``itinerary_already_generated`` flag.
        Same hardening as block_country_only_origin (#1105)."""
        import json

        from app.ai.graph.tools.itinerary import generate_itinerary

        result_str = await generate_itinerary.ainvoke(
            {
                "destination": "Europe",
                "num_days": 4,
                "adults": 1,
                "modification_notes": "Make day 2 more relaxed",
            },
            # itinerary_already_generated omitted → False → gate fires
        )

        result = json.loads(result_str)
        assert result["status"] == "error"
        assert (
            "region" in result["error"].lower()
            or "continent" in result["error"].lower()
        )


class TestGenerateItineraryMissingOriginGate:
    """Tests for origin handling in generate_itinerary (#1127 gate, #1157 relaxation).

    #1127 added a hard gate that blocked generation when origin was missing.
    #1157 removed that gate — origin is now optional. The flight side-search
    is skipped automatically when origin is absent; the day-plan still generates.
    """

    @pytest.mark.asyncio
    async def test_missing_origin_allowed(self) -> None:
        """#1157: origin is now optional — generation proceeds without it."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                    "adults": 1,
                    # origin intentionally omitted — now optional
                },
            )

        result = json.loads(result_str)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_empty_string_origin_allowed(self) -> None:
        """#1157: empty origin is treated same as missing — generation proceeds."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                    "origin": "",
                    "adults": 1,
                },
            )

        result = json.loads(result_str)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_origin_present_passes_gate(self) -> None:
        """With ``origin`` set, the gate releases and generation proceeds."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 3,
                    "origin": "Los Angeles",
                    "adults": 1,
                },
            )

        result = json.loads(result_str)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_itinerary_already_generated_bypasses_gate(self) -> None:
        """Regeneration must skip the origin gate — amend turns are valid
        even if origin was never collected on the first turn. The signal
        comes from the supervisor-set ``itinerary_already_generated`` flag
        (NOT from a hallucinated ``modification_notes`` string)."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                    "modification_notes": "Make day 3 a free day",
                    # origin intentionally still omitted
                },
                config={
                    "configurable": {
                        "itinerary_already_generated": True,
                    }
                },
            )

        result = json.loads(result_str)
        # Gate bypassed — regeneration ran without origin.
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_skip_flights_requested_bypasses_gate(self) -> None:
        """#1127 carve-out: when the supervisor detected the user said
        'no flights' / 'I'm already in <destination>' / 'just the plan', the
        ``skip_flights_requested`` configurable flag releases the missing-origin
        gate so the agent can produce a day-plan-only itinerary."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                    # origin intentionally omitted — user opted out of flights
                },
                config={
                    "configurable": {
                        "skip_flights_requested": True,
                    }
                },
            )

        result = json.loads(result_str)
        # Gate bypassed via the carve-out; day-plan-only generation ran.
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_skip_flights_false_with_missing_origin_still_proceeds(self) -> None:
        """#1157: origin is optional — skip_flights_requested=False no longer
        gates on missing origin. Generation proceeds regardless."""
        import json

        mock_result = _make_mock_itinerary_result()
        with (
            patch(
                "app.ai.graph.tools.itinerary._generate_itinerary_with_llm",
                return_value=mock_result,
            ),
            patch(
                "app.ai.graph.enrichment.enrich_itinerary",
                return_value=mock_result,
            ),
        ):
            from app.ai.graph.tools.itinerary import generate_itinerary

            result_str = await generate_itinerary.ainvoke(
                {
                    "destination": "Tokyo",
                    "num_days": 5,
                },
                config={
                    "configurable": {
                        "skip_flights_requested": False,
                    }
                },
            )

        result = json.loads(result_str)
        assert result["status"] == "success"


class TestItineraryValidation:
    """Tests for itinerary and budget validation logic."""

    def test_validate_itinerary_correct_days(self) -> None:
        """Validation passes when days are sequential and have activities."""
        from app.ai.graph.tools.itinerary import (
            BudgetSnapshot,
            DayTip,
            ExpandedContent,
            ItineraryActivity,
            ItineraryDay,
            StructuredItineraryResult,
            _validate_itinerary,
        )

        itinerary = StructuredItineraryResult(
            itinerary_items=[
                ItineraryDay(
                    day=1,
                    title="Day 1",
                    description="First day.",
                    expanded_content=ExpandedContent(
                        activities=[
                            ItineraryActivity(
                                location="A", description="B", duration="1h"
                            ),
                        ],
                        tip=DayTip(text="Tip"),
                    ),
                ),
                ItineraryDay(
                    day=2,
                    title="Day 2",
                    description="Second day.",
                    expanded_content=ExpandedContent(
                        activities=[
                            ItineraryActivity(
                                location="C", description="D", duration="2h"
                            ),
                        ],
                        tip=DayTip(text="Tip"),
                    ),
                ),
            ],
            budget_snapshot=BudgetSnapshot(description="$500 per person"),
            local_experiences=[],
        )

        result = _validate_itinerary(itinerary)
        assert result["valid"] is True
        assert result["warnings"] == []

    def test_validate_itinerary_wrong_day_count(self) -> None:
        """Validation warns when a day has no activities."""
        from app.ai.graph.tools.itinerary import (
            BudgetSnapshot,
            DayTip,
            ExpandedContent,
            ItineraryDay,
            StructuredItineraryResult,
            _validate_itinerary,
        )

        itinerary = StructuredItineraryResult(
            itinerary_items=[
                ItineraryDay(
                    day=1,
                    title="Day 1",
                    description="Empty day.",
                    expanded_content=ExpandedContent(
                        activities=[],
                        tip=DayTip(text="Tip"),
                    ),
                ),
            ],
            budget_snapshot=BudgetSnapshot(description="$500 per person"),
            local_experiences=[],
        )

        result = _validate_itinerary(itinerary)
        assert result["valid"] is False
        assert any("Day 1 has no activities" in w for w in result["warnings"])


# ========================
# TestBookingIntentDetection (Steps 9-10)
# ========================


class TestBookingIntentDetection:
    """Tests for _detect_booking_intent_v1 and _extract_cross_agent_data."""

    def test_detect_book_everything(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {
            "itinerary": {
                "destination": "Tokyo",
                "destination_iata": "NRT",
                "departure_date": "2026-04-01",
            },
        }
        plan = _detect_booking_intent_v1("book everything", [], result_state)
        assert plan == ["flight", "hotel"]

    def test_detect_book_flights_only(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {
            "itinerary": {
                "destination": "Tokyo",
                "destination_iata": "NRT",
                "departure_date": "2026-04-01",
            },
        }
        plan = _detect_booking_intent_v1("just book the flights", [], result_state)
        assert plan == ["flight"]

    def test_detect_book_hotel_only(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {
            "itinerary": {
                "destination": "Tokyo",
                "departure_date": "2026-04-01",
            },
        }
        plan = _detect_booking_intent_v1("book the hotel", [], result_state)
        assert plan == ["hotel"]

    def test_no_booking_intent(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {"itinerary": {"destination": "Tokyo"}}
        plan = _detect_booking_intent_v1("tell me more about Tokyo", [], result_state)
        assert plan is None

    def test_booking_intent_without_trip_data_returns_none(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {"itinerary": {}}
        plan = _detect_booking_intent_v1("book everything", [], result_state)
        assert plan is None

    def test_hotel_first_order(self) -> None:
        from app.ai.graph.itinerary_graph import _detect_booking_intent_v1

        result_state = {
            "itinerary": {
                "destination": "Tokyo",
                "departure_date": "2026-04-01",
            },
        }
        plan = _detect_booking_intent_v1(
            "book everything, hotel first", [], result_state
        )
        assert plan == ["hotel", "flight"]

    def test_extract_cross_agent_data(self) -> None:
        from app.ai.graph.itinerary_graph import _extract_cross_agent_data

        result_state = {
            "itinerary": {
                "origin_iata": "AMS",
                "destination": "Tokyo",
                "destination_iata": "NRT",
                "destination_country": "Japan",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
                "children": 0,
            },
        }
        data = _extract_cross_agent_data(result_state)
        assert data["origin_iata"] == "AMS"
        assert data["destination_iata"] == "NRT"
        assert data["departure_date"] == "2026-04-01"
        assert data["return_date"] == "2026-04-06"
        assert data["adults"] == 2
        assert len(data["hotel_cities"]) == 1
        assert data["hotel_cities"][0]["city"] == "Tokyo"
        assert data["hotel_cities"][0]["country"] == "Japan"

    def test_extract_cross_agent_data_empty(self) -> None:
        from app.ai.graph.itinerary_graph import _extract_cross_agent_data

        data = _extract_cross_agent_data({"itinerary": {}})
        assert data == {}


# ========================
# TestProcessItineraryMessagesV2 (Structured Context)
# ========================


class TestProcessItineraryMessagesV2:
    """Tests for V2 planning_complete detection in process_itinerary_messages."""

    def test_detects_planning_complete_hand_back(self) -> None:
        """V2: hand_back with planning_complete reason returns booking_plan."""
        from langchain_core.messages import ToolMessage

        from app.ai.graph.itinerary_graph import process_itinerary_messages

        messages = [
            HumanMessage(content="Plan a trip to Tokyo"),
            AIMessage(content="Here's your Tokyo itinerary!"),
            # update_trip_info with trip data
            AIMessage(
                content="",
                tool_calls=[{"name": "update_trip_info", "id": "tc1", "args": {}}],
            ),
            ToolMessage(
                content='{"status": "success", "trip_info": {"origin_iata": "AMS", "destination_iata": "NRT", "destination": "Tokyo", "destination_country": "Japan", "departure_date": "2026-04-01", "return_date": "2026-04-06", "adults": 2}}',
                tool_call_id="tc1",
                name="update_trip_info",
            ),
            HumanMessage(content="book everything"),
            AIMessage(content="Starting your bookings!"),
            # hand_back with planning_complete
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "hand_back_to_supervisor",
                        "id": "tc2",
                        "args": {
                            "reason": "planning_complete: book flight and hotel",
                            "is_detour": False,
                        },
                    }
                ],
            ),
            ToolMessage(
                content='{"status": "hand_back", "reason": "planning_complete: book flight and hotel", "is_detour": false, "instruction": "Handing back."}',
                tool_call_id="tc2",
                name="hand_back_to_supervisor",
            ),
        ]

        result = process_itinerary_messages(messages)

        assert result["signal"] == "done"
        assert result["done_reason"] == "planning_complete"
        assert result["booking_plan"] == ["flight", "hotel"]
        assert result["cross_agent_data"]["origin_iata"] == "AMS"
        assert result["cross_agent_data"]["destination_iata"] == "NRT"
        assert result["cross_agent_data"]["adults"] == 2

    def test_extract_cross_agent_data_from_messages(self) -> None:
        """_extract_cross_agent_data_from_messages scans update_trip_info ToolMessages."""
        from langchain_core.messages import ToolMessage

        from app.ai.graph.itinerary_graph import _extract_cross_agent_data_from_messages

        messages = [
            AIMessage(
                content="",
                tool_calls=[{"name": "update_trip_info", "id": "tc1", "args": {}}],
            ),
            ToolMessage(
                content='{"status": "success", "trip_info": {"origin_iata": "AMS", "destination": "Tokyo", "destination_iata": "NRT", "destination_country": "Japan", "departure_date": "2026-04-01", "return_date": "2026-04-06", "adults": 2}}',
                tool_call_id="tc1",
                name="update_trip_info",
            ),
        ]

        data = _extract_cross_agent_data_from_messages(messages)
        assert data["origin_iata"] == "AMS"
        assert data["destination_iata"] == "NRT"
        assert data["departure_date"] == "2026-04-01"
        assert data["adults"] == 2
        assert len(data["hotel_cities"]) == 1
        assert data["hotel_cities"][0]["city"] == "Tokyo"

    def test_parse_booking_plan_from_reason(self) -> None:
        """_parse_booking_plan_from_reason extracts agent order from reason."""
        from app.ai.graph.itinerary_graph import _parse_booking_plan_from_reason

        assert _parse_booking_plan_from_reason(
            "planning_complete: book flight and hotel"
        ) == ["flight", "hotel"]
        assert _parse_booking_plan_from_reason(
            "planning_complete: book hotel then flight"
        ) == ["hotel", "flight"]
        assert _parse_booking_plan_from_reason("planning_complete: book flight") == [
            "flight"
        ]
        assert _parse_booking_plan_from_reason("planning_complete: book hotel") == [
            "hotel"
        ]
        assert _parse_booking_plan_from_reason("planning_complete") == [
            "flight",
            "hotel",
        ]


class TestProcessItineraryMessagesArtifact:
    """Tests for process_itinerary_messages reading ToolMessage.artifact."""

    def _make_generate_tool_msg(
        self,
        content_json: dict,
        artifact: dict | None = None,
        tool_call_id: str = "tc_gen",
    ) -> ToolMessage:
        """Helper: create a generate_itinerary ToolMessage with optional artifact."""
        msg = ToolMessage(
            content=json.dumps(content_json),
            tool_call_id=tool_call_id,
            name="generate_itinerary",
        )
        msg.artifact = artifact
        return msg

    def _make_update_trip_msg(self) -> list:
        """Helper: update_trip_info messages so cross_data has destination+dates."""
        return [
            AIMessage(
                content="",
                tool_calls=[{"name": "update_trip_info", "id": "tc_trip", "args": {}}],
            ),
            ToolMessage(
                content=json.dumps(
                    {
                        "status": "success",
                        "trip_info": {
                            "destination": "Tokyo",
                            "departure_date": "2026-04-10",
                            "return_date": "2026-04-17",
                            "adults": 2,
                        },
                    }
                ),
                tool_call_id="tc_trip",
                name="update_trip_info",
            ),
        ]

    def test_reads_itinerary_from_artifact(self) -> None:
        """Primary path: reads structured itinerary from msg.artifact."""
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        itinerary_dict = {
            "itineraryItems": [{"day": 1, "title": "Day 1"}],
            "budgetSnapshot": {"description": "$2000"},
        }
        content = {"status": "success", "destination": "Tokyo"}

        messages = [
            *self._make_update_trip_msg(),
            AIMessage(
                content="",
                tool_calls=[{"name": "generate_itinerary", "id": "tc_gen", "args": {}}],
            ),
            self._make_generate_tool_msg(content, artifact=itinerary_dict),
            AIMessage(content="Here's your itinerary!"),
        ]

        result = process_itinerary_messages(messages)
        assert result["type"] == "itinerary_results"
        assert result["metadata"]["structured_itinerary"] == itinerary_dict

    def test_fallback_to_content_when_no_artifact(self) -> None:
        """Fallback path: reads itinerary from inline content JSON when artifact is None."""
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        itinerary_dict = {
            "itineraryItems": [{"day": 1, "title": "Day 1"}],
            "budgetSnapshot": {"description": "$2000"},
        }
        content = {
            "status": "success",
            "destination": "Tokyo",
            "itinerary": itinerary_dict,
        }

        messages = [
            *self._make_update_trip_msg(),
            AIMessage(
                content="",
                tool_calls=[{"name": "generate_itinerary", "id": "tc_gen", "args": {}}],
            ),
            self._make_generate_tool_msg(content, artifact=None),
            AIMessage(content="Here's your itinerary!"),
        ]

        result = process_itinerary_messages(messages)
        assert result["type"] == "itinerary_results"
        assert result["metadata"]["structured_itinerary"] == itinerary_dict

    def test_artifact_takes_priority_over_content(self) -> None:
        """When both artifact and inline content have itinerary, artifact wins."""
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        artifact_itinerary = {
            "itineraryItems": [{"day": 1, "title": "From Artifact"}],
            "budgetSnapshot": {"description": "$2000"},
        }
        content_itinerary = {
            "itineraryItems": [{"day": 1, "title": "From Content"}],
        }
        content = {
            "status": "success",
            "destination": "Tokyo",
            "itinerary": content_itinerary,
        }

        messages = [
            *self._make_update_trip_msg(),
            AIMessage(
                content="",
                tool_calls=[{"name": "generate_itinerary", "id": "tc_gen", "args": {}}],
            ),
            self._make_generate_tool_msg(content, artifact=artifact_itinerary),
            AIMessage(content="Here's your itinerary!"),
        ]

        result = process_itinerary_messages(messages)
        assert result["type"] == "itinerary_results"
        # Artifact wins
        assert (
            result["metadata"]["structured_itinerary"]["itineraryItems"][0]["title"]
            == "From Artifact"
        )


# ========================
# TestFormatTravelStylePreferences
# ========================


class TestFormatTravelStylePreferences:
    """Tests for format_travel_style_preferences helper."""

    def test_returns_empty_when_document_not_exists(self) -> None:
        from app.ai.graph.itinerary_graph import format_travel_style_preferences
        from app.domains.user_preferences.schemas import UserPreferencesResponse

        prefs = UserPreferencesResponse(document_exists=False)
        assert format_travel_style_preferences(prefs) == ""

    def test_returns_empty_when_all_fields_empty(self) -> None:
        from app.ai.graph.itinerary_graph import format_travel_style_preferences
        from app.domains.user_preferences.schemas import UserPreferencesResponse

        prefs = UserPreferencesResponse(document_exists=True)
        assert format_travel_style_preferences(prefs) == ""

    def test_partial_fields(self) -> None:
        from app.ai.graph.itinerary_graph import format_travel_style_preferences
        from app.domains.user_preferences.schemas import (
            TravelStylePreferences,
            UserPreferencesResponse,
        )

        prefs = UserPreferencesResponse(
            document_exists=True,
            travel_style=TravelStylePreferences(
                travel_pace="relaxed",
                budget_mindset="luxury",
            ),
        )
        result = format_travel_style_preferences(prefs)
        assert "[USER TRAVEL PREFERENCES]" in result
        assert "- Travel pace: relaxed" in result
        assert "- Budget mindset: luxury" in result
        assert "Accommodation" not in result

    def test_full_preferences(self) -> None:
        from app.ai.graph.itinerary_graph import format_travel_style_preferences
        from app.domains.user_preferences.schemas import (
            TravelStylePreferences,
            UserPreferencesResponse,
        )

        prefs = UserPreferencesResponse(
            document_exists=True,
            travel_style=TravelStylePreferences(
                travel_pace="packed",
                budget_mindset="comfort",
                accommodation="5star",
                activity_density="structured",
                primary_goals=["food", "culture"],
                getting_around=["walking", "public"],
            ),
        )
        result = format_travel_style_preferences(prefs)
        assert "- Travel pace: packed" in result
        assert "- Budget mindset: comfort" in result
        assert "- Accommodation preference: 5star" in result
        assert "- Activity density: structured" in result
        assert "- Primary interests: food, culture" in result
        assert "- Getting around: walking, public" in result
        assert "Personalize the itinerary" in result

    def test_only_list_fields(self) -> None:
        from app.ai.graph.itinerary_graph import format_travel_style_preferences
        from app.domains.user_preferences.schemas import (
            TravelStylePreferences,
            UserPreferencesResponse,
        )

        prefs = UserPreferencesResponse(
            document_exists=True,
            travel_style=TravelStylePreferences(
                primary_goals=["nature"],
                getting_around=["rental"],
            ),
        )
        result = format_travel_style_preferences(prefs)
        assert "- Primary interests: nature" in result
        assert "- Getting around: rental" in result
        assert "Travel pace" not in result


# ========================
# TestProcessItineraryMessagesPreferences
# ========================


class TestProcessItineraryMessagesPreferences:
    """Tests for preferences_summary parameter in process_itinerary_messages."""

    def _make_itinerary_messages(self) -> list:
        """Create minimal messages with a generate_itinerary tool result."""
        trip_msgs = [
            AIMessage(
                content="",
                tool_calls=[{"name": "update_trip_info", "id": "tc_trip", "args": {}}],
            ),
            ToolMessage(
                content=json.dumps(
                    {
                        "status": "success",
                        "trip_info": {
                            "destination": "Paris",
                            "departure_date": "2026-05-01",
                            "return_date": "2026-05-04",
                            "adults": 1,
                        },
                    }
                ),
                tool_call_id="tc_trip",
                name="update_trip_info",
            ),
        ]
        gen_msg = ToolMessage(
            content=json.dumps({"status": "success", "destination": "Paris"}),
            tool_call_id="tc_gen",
            name="generate_itinerary",
        )
        gen_msg.artifact = {
            "itineraryItems": [
                {"day": 1, "title": "Day 1"},
                {"day": 2, "title": "Day 2"},
                {"day": 3, "title": "Day 3"},
            ],
            "budgetSnapshot": {"description": "$1500"},
        }
        return [
            *trip_msgs,
            AIMessage(
                content="",
                tool_calls=[{"name": "generate_itinerary", "id": "tc_gen", "args": {}}],
            ),
            gen_msg,
            AIMessage(content="Here's your itinerary!"),
        ]

    def test_summary_includes_preferences_when_provided(self) -> None:
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        result = process_itinerary_messages(
            self._make_itinerary_messages(),
            preferences_summary="relaxed, luxury, food & culture",
        )
        assert (
            "personalized for your relaxed, luxury, food & culture preferences"
            in result["message"]
        )

    def test_summary_no_preferences_when_empty(self) -> None:
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        result = process_itinerary_messages(
            self._make_itinerary_messages(),
            preferences_summary="",
        )
        assert "personalized" not in result["message"]

    def test_summary_no_preferences_when_omitted(self) -> None:
        from app.ai.graph.itinerary_graph import process_itinerary_messages

        result = process_itinerary_messages(self._make_itinerary_messages())
        assert "personalized" not in result["message"]
