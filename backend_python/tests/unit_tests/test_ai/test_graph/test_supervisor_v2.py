"""Unit tests for LangGraph Supervisor V2.

Tests cover:
- Structured AgentSignal (Phase A)
- Auto-chaining (Step 9)
- Shared context (unified cross-agent state)
- Partial booking recovery
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.graph.state import AgentSignal
from app.ai.graph.supervisor_v2 import (
    MAX_TASK_QUEUE_SIZE,
    RESET_KEYWORDS,
    SV2_CHECKPOINT_VERSION,
    _after_dispatch,
    _build_agent_messages,
    _build_conversation_recap,
    _build_recent_context,
    _build_task_queue_hint,
    _capture_shared_context,
    _clear_stale_agent_checkpoints,
    _clear_supervisor_checkpoint,
    _detect_agent_signal,
    _filter_detour_noise,
    _format_context_for_agent,
    _merge_shared_context,
    _normalize_llm_content,
    _parse_classification_response,
    _resolve_destination,
    _route_to_agent,
    _strip_orphaned_tool_messages,
    _validate_queued_intents,
    dispatch_flight,
    dispatch_general,
    dispatch_hotel,
    dispatch_itinerary,
    route_or_classify,
)
from app.ai.graph.tools.handback import hand_back_to_supervisor


def _make_state(**overrides: Any) -> dict[str, Any]:
    """Create a minimal SupervisorV2State-like dict for testing."""
    defaults: dict[str, Any] = {
        "messages": [HumanMessage(content="hello")],
        "user_id": "user123",
        "chat_id": "chat456",
        "user_email": "test@example.com",
        "active_agent": None,
        "previous_agent": None,
        "current_intent": None,
        "agent_signal": None,
        "agent_response": None,
        "auto_chain": [],
        "shared_context": {},
        "chain_responses": [],
        "task_queue": [],
        "detour_return": False,
        "hand_back_count": 0,
        "agent_start_index": 0,
        "detour_origin_index": 0,
        "classification_confidence": 1.0,
        "remaining_steps": 10,
    }
    defaults.update(overrides)
    return defaults


# ========================
# TestParseClassificationResponse
# ========================


class TestParseClassificationResponse:
    """Tests for parsing LLM classification response."""

    def test_parse_valid_json(self):
        text = '{"target_agent": "flight", "reasoning": "User wants to fly"}'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "flight"
        assert result["reasoning"] == "User wants to fly"

    def test_parse_json_in_code_block(self):
        text = '```json\n{"target_agent": "hotel", "reasoning": "Hotel request"}\n```'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "hotel"

    def test_parse_invalid_json_infers_flight(self):
        text = "The user wants to book a flight to Paris"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "flight"

    def test_parse_invalid_json_infers_hotel(self):
        text = "Looking for a hotel in Rome"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "hotel"

    def test_parse_invalid_json_infers_itinerary(self):
        text = "User wants to plan an itinerary"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "itinerary"

    def test_parse_invalid_json_defaults_to_general(self):
        text = "I don't understand this message"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "general"

    def test_parse_invalid_target_agent_defaults_to_general(self):
        text = '{"target_agent": "invalid_agent", "reasoning": "test"}'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "general"

    def test_parse_generic_code_block(self):
        text = '```\n{"target_agent": "itinerary", "reasoning": "Trip planning"}\n```'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "itinerary"

    # ------------------------------------------------------------------
    # Responses API content normalization (gpt-5.x returns list, not str)
    # ------------------------------------------------------------------

    def test_parse_responses_api_list_content(self):
        """Responses API returns content as list of blocks — must extract text."""
        content = [
            {
                "type": "text",
                "text": '{"target_agent": "itinerary", "reasoning": "Trip planning"}',
                "annotations": [],
                "id": "msg_abc123",
            }
        ]
        normalized = _normalize_llm_content(content)
        result = _parse_classification_response(normalized)
        assert result["target_agent"] == "itinerary"

    def test_parse_responses_api_multi_block_list(self):
        """Multiple text blocks in Responses API format — joined correctly."""
        content = [
            {"type": "text", "text": '{"target_agent": "flight"', "annotations": []},
            {
                "type": "text",
                "text": ', "reasoning": "flight search"}',
                "annotations": [],
            },
        ]
        normalized = _normalize_llm_content(content)
        result = _parse_classification_response(normalized)
        assert result["target_agent"] == "flight"

    def test_normalize_plain_string_passthrough(self):
        """Plain string content (Chat Completions, Gemini, xAI) passes through."""
        text = '{"target_agent": "hotel", "reasoning": "Hotel booking"}'
        assert _normalize_llm_content(text) == text
        result = _parse_classification_response(text)
        assert result["target_agent"] == "hotel"

    def test_normalize_none_returns_empty(self):
        """None content returns empty string."""
        assert _normalize_llm_content(None) == ""

    def test_normalize_non_string_coerced(self):
        """Non-string, non-list content is coerced to string."""
        assert _normalize_llm_content(42) == "42"

    def test_parse_empty_string_defaults_to_general(self):
        """Empty content (e.g. failed LLM call) defaults to general gracefully."""
        result = _parse_classification_response("")
        assert result["target_agent"] == "general"


# ========================
# TestDetectAgentSignal (Structured)
# ========================


class TestDetectAgentSignal:
    """Tests for _detect_agent_signal with structured AgentSignal."""

    def test_hand_back_signal_detected(self):
        result = {"signal": "hand_back", "type": "hand_back", "reason": "wrong domain"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "hand_back"
        assert signal["reason"] == "wrong domain"

    def test_hand_back_with_detour(self):
        result = {
            "signal": "hand_back",
            "reason": "weather question",
            "is_detour": True,
        }
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "hand_back"
        assert signal["is_detour"] is True

    def test_hand_back_without_detour(self):
        result = {"signal": "hand_back", "reason": "topic change"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "hand_back"
        assert signal.get("is_detour", False) is False

    def test_done_on_flight_redirect(self):
        result = {"type": "flight_booking_redirect"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "done"
        assert signal["done_reason"] == "booking_complete"

    def test_done_on_hotel_redirect(self):
        result = {"type": "hotel_booking_redirect"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "done"
        assert signal["done_reason"] == "booking_complete"

    def test_done_with_planning_complete(self):
        result = {
            "signal": "done",
            "done_reason": "planning_complete",
            "booking_plan": ["flight", "hotel"],
        }
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "done"
        assert signal["done_reason"] == "planning_complete"
        assert signal["booking_plan"] == ["flight", "hotel"]

    def test_done_with_query_answered(self):
        result = {"signal": "done", "done_reason": "query_answered"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "done"
        assert signal["done_reason"] == "query_answered"

    def test_needs_input_default(self):
        result = {"type": "flight_conversation"}
        signal = _detect_agent_signal(result)
        assert signal["agent_status"] == "needs_input"

    def test_needs_input_empty_result(self):
        signal = _detect_agent_signal({})
        assert signal["agent_status"] == "needs_input"


# ========================
# TestAfterDispatch (Structured)
# ========================


class TestAfterDispatch:
    """Tests for the _after_dispatch conditional edge with structured signals."""

    def test_hand_back_loops_back(self):
        state = _make_state(agent_signal=AgentSignal(agent_status="hand_back"))
        assert _after_dispatch(state) == "route_or_classify"

    def test_done_without_pending_ends(self):
        """DONE with no pending chain/queue/detour -> END directly."""
        state = _make_state(agent_signal=AgentSignal(agent_status="done"))
        assert _after_dispatch(state) == "__end__"

    def test_done_with_auto_chain_loops_back(self):
        """DONE with auto_chain pending -> loop back to route_or_classify."""
        state = _make_state(
            agent_signal=AgentSignal(agent_status="done"),
            auto_chain=["hotel"],
        )
        assert _after_dispatch(state) == "route_or_classify"

    def test_done_with_task_queue_loops_back(self):
        """DONE with task_queue pending -> loop back to route_or_classify."""
        state = _make_state(
            agent_signal=AgentSignal(agent_status="done"),
            task_queue=[{"agent": "flight", "context": "book flights"}],
        )
        assert _after_dispatch(state) == "route_or_classify"

    def test_done_with_detour_return_ends(self):
        """DONE with detour_return -> END. Return to original agent on NEXT message."""
        state = _make_state(
            agent_signal=AgentSignal(agent_status="done"),
            detour_return=True,
        )
        assert _after_dispatch(state) == "__end__"

    def test_done_with_booking_plan_loops_back(self):
        """DONE with booking_plan -> loop back so route_or_classify sets up auto-chain."""
        state = _make_state(
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="planning_complete",
                booking_plan=["flight", "hotel"],
            ),
        )
        assert _after_dispatch(state) == "route_or_classify"

    def test_failed_without_chain_ends(self):
        """Standalone failure (no chain) -> END, don't reclassify."""
        state = _make_state(agent_signal=AgentSignal(agent_status="failed"))
        assert _after_dispatch(state) == "__end__"

    def test_failed_with_chain_loops_back(self):
        """Failure during auto-chain -> loop back for recovery."""
        state = _make_state(
            agent_signal=AgentSignal(agent_status="failed"),
            auto_chain=["hotel"],
        )
        assert _after_dispatch(state) == "route_or_classify"

    def test_needs_input_ends(self):
        state = _make_state(agent_signal=AgentSignal(agent_status="needs_input"))
        assert _after_dispatch(state) == "__end__"

    def test_none_signal_ends(self):
        state = _make_state(agent_signal=None)
        assert _after_dispatch(state) == "__end__"


# ========================
# TestRouteToAgent
# ========================


class TestRouteToAgent:
    """Tests for the _route_to_agent conditional edge."""

    def test_routes_flight(self):
        state = _make_state(active_agent="flight")
        assert _route_to_agent(state) == "dispatch_flight"

    def test_routes_hotel(self):
        state = _make_state(active_agent="hotel")
        assert _route_to_agent(state) == "dispatch_hotel"

    def test_routes_itinerary_cold_turn_to_pre_resolve(self):
        """#1038: itinerary path detours through pre_resolve_trip when trip_ctx is empty."""
        state = _make_state(active_agent="itinerary")
        assert _route_to_agent(state) == "pre_resolve_trip"

    def test_routes_itinerary_direct_when_trip_ctx_populated(self):
        """#1038: skip pre_resolve_trip when destination_iata + departure_date
        already known AND origin is resolved.

        #1127: the gate now also re-fires pre_resolve_trip when origin needs
        resolving (e.g. user replied with a city name in a follow-up turn).
        Include origin_iata in the trip_ctx to assert the original
        skip-when-fully-resolved invariant.
        """
        state = _make_state(
            active_agent="itinerary",
            shared_context={
                "trip": {
                    "origin": "London",
                    "origin_iata": "LHR",
                    "destination": "Paris",
                    "destination_iata": "CDG",
                    "departure_date": "2026-06-20",
                }
            },
        )
        assert _route_to_agent(state) == "dispatch_itinerary"

    def test_routes_itinerary_back_to_pre_resolve_when_iata_missing(self):
        """#1038 follow-up: ambiguous-city turn writes `destination` but not
        `destination_iata`; the next turn should still detour through
        pre_resolve_trip so the IATA gets resolved before side-search fires."""
        state = _make_state(
            active_agent="itinerary",
            shared_context={
                "trip": {"destination": "Paris", "departure_date": "2026-06-20"}
            },
        )
        assert _route_to_agent(state) == "pre_resolve_trip"

    def test_routes_itinerary_back_to_pre_resolve_when_origin_unresolved(self):
        """#1127: destination + dates set BUT origin string is in trip_ctx
        without an IATA — re-fire pre_resolve_trip so origin gets resolved
        before dispatch. Otherwise the flight side-search silently skips and
        the FE falls back to using country strings."""
        state = _make_state(
            active_agent="itinerary",
            shared_context={
                "trip": {
                    "destination": "Montenegro",
                    "destination_iata": "TIV",
                    "departure_date": "2026-07-20",
                    "origin": "Dubai",  # set by previous update_trip_info
                    # origin_iata intentionally missing
                }
            },
        )
        assert _route_to_agent(state) == "pre_resolve_trip"

    def test_routes_itinerary_back_to_pre_resolve_for_bare_location_reply(self):
        """#1127: when the user replies with a bare location string after the
        agent asked for origin, the supervisor must detour to pre_resolve_trip
        so the extractor's origin-fallback fast-path can resolve it — even if
        destination + dates were already set."""
        from langchain_core.messages import HumanMessage

        state = _make_state(
            active_agent="itinerary",
            messages=[HumanMessage(content="Dubai")],
            shared_context={
                "trip": {
                    "destination": "Montenegro",
                    "destination_iata": "TIV",
                    "departure_date": "2026-07-20",
                    # origin not yet recorded, origin_iata missing
                }
            },
        )
        assert _route_to_agent(state) == "pre_resolve_trip"

    def test_routes_itinerary_stays_direct_for_conversational_reply(self):
        """#1127: the bare-location heuristic must NOT fire on conversational
        replies ("thanks", "hello", "yes") — those keep dispatch_itinerary as
        the route since origin isn't actually being provided."""
        from langchain_core.messages import HumanMessage

        state = _make_state(
            active_agent="itinerary",
            messages=[HumanMessage(content="thanks")],
            shared_context={
                "trip": {
                    "origin": "London",
                    "origin_iata": "LHR",
                    "destination": "Paris",
                    "destination_iata": "CDG",
                    "departure_date": "2026-06-20",
                }
            },
        )
        assert _route_to_agent(state) == "dispatch_itinerary"


class TestSkipFlightsPattern:
    """#1127 carve-out detection: phrases that release the
    ``block_missing_origin`` gate so the agent can produce a day-plan-only
    itinerary without first prompting for origin."""

    def test_matches_no_flights_variants(self):
        from app.ai.graph.supervisor_v2 import _SKIP_FLIGHTS_PATTERN

        for phrase in [
            "no flights please",
            "skip flights",
            "without flights",
            "I don't need flights",
            "I dont want flights",
            "just the plan",
            "just the itinerary",
            "plan only",
            "day plan only",
            "I'm already in Tokyo",
            "I am already in Paris",
        ]:
            assert _SKIP_FLIGHTS_PATTERN.search(phrase), f"should match: {phrase!r}"

    def test_does_not_match_regular_travel_phrasing(self):
        """Defensive: the pattern must NOT fire on normal trip-planning
        language. False positives would silently disable the origin
        requirement."""
        from app.ai.graph.supervisor_v2 import _SKIP_FLIGHTS_PATTERN

        for phrase in [
            "Plan a trip to Tokyo",
            "I want flights from London",
            "Find me flights",
            "Show flight options",
            "Book the cheapest flight",
            "I'm flying from Dubai",
            "departing from Mumbai",
            "Dubai",
        ]:
            assert not _SKIP_FLIGHTS_PATTERN.search(phrase), (
                f"should NOT match: {phrase!r}"
            )

    def test_routes_general(self):
        state = _make_state(active_agent="general")
        assert _route_to_agent(state) == "dispatch_general"

    def test_unknown_defaults_to_general(self):
        state = _make_state(active_agent="unknown")
        assert _route_to_agent(state) == "dispatch_general"

    def test_none_defaults_to_general(self):
        state = _make_state(active_agent=None)
        assert _route_to_agent(state) == "dispatch_general"


# ========================
# TestRouteOrClassify
# ========================


class TestRouteOrClassify:
    """Tests for the route_or_classify graph node."""

    @pytest.mark.asyncio
    async def test_fast_path_forwards_to_active_agent(self):
        """When active_agent is set, forward without LLM call."""
        state = _make_state(active_agent="flight", current_intent="FLIGHT")
        result = await route_or_classify(state)
        # Fast path returns {} (empty update) — active_agent is preserved by
        # LangGraph state (not in the returned dict). So either the key is
        # absent or explicitly None; both mean "keep existing state value".
        assert "active_agent" not in result or result.get("active_agent") is None

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_classify_new_routes_to_flight(self, mock_prompt, mock_llm):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "flight", "reasoning": "Flight request"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(messages=[HumanMessage(content="Book a flight to Paris")])
        result = await route_or_classify(state)
        assert result["active_agent"] == "flight"
        assert result["current_intent"] == "FLIGHT"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_classify_new_routes_to_hotel(self, mock_prompt, mock_llm):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "hotel", "reasoning": "Hotel request"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(messages=[HumanMessage(content="Find me a hotel in Rome")])
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        assert result["current_intent"] == "HOTEL"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_classify_new_routes_to_itinerary(self, mock_prompt, mock_llm):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "itinerary", "reasoning": "Trip planning"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(messages=[HumanMessage(content="Plan a trip to Japan")])
        result = await route_or_classify(state)
        assert result["active_agent"] == "itinerary"
        assert result["current_intent"] == "ITINERARY"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_classify_new_routes_to_general(self, mock_prompt, mock_llm):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "Greeting"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(messages=[HumanMessage(content="Hello!")])
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"
        assert result["current_intent"] == "GENERAL"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_multi_city_flight_routes_to_flight_not_itinerary(
        self, mock_prompt, mock_llm
    ):
        """Regression: multi-city flight queries must route to flight, not itinerary.

        Bug: "LHR to CDG April 30, CDG to FCO May 7" was classified as itinerary
        because the supervisor saw multi-leg date sequences as trip planning.
        Rule 8 in the supervisor prompt now handles this.
        """
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "flight", "reasoning": "Multi-city flight booking"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[
                HumanMessage(content="LHR to CDG April 30, CDG to FCO May 7, 2 adults")
            ]
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "flight"
        assert result["current_intent"] == "FLIGHT"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_itinerary_modification_routes_to_itinerary_not_hotel(
        self, mock_prompt, mock_llm
    ):
        """Regression: post-itinerary modification queries must route to itinerary.

        Bug: "update 4 star to 5 star hotel" after itinerary generation was
        classified as hotel because the word "hotel" triggered hotel routing.
        Rule #8 + previous_agent_hint now ensures modifications stay with itinerary.
        """
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "itinerary", "reasoning": '
            '"Itinerary modification, not hotel search"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[
                HumanMessage(content="update 4 star to 5 star hotel"),
            ],
            previous_agent="itinerary",
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "itinerary"
        assert result["current_intent"] == "ITINERARY"

        # Verify the classification prompt includes previous_agent context
        call_args = mock_llm.return_value.ainvoke.call_args
        prompt_input = call_args[0][0]
        # prompt_input may be a list of messages or a string
        if isinstance(prompt_input, list):
            prompt_text = " ".join(
                m.content if hasattr(m, "content") else str(m) for m in prompt_input
            )
        else:
            prompt_text = str(prompt_input)
        assert "itinerary" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_reset_keyword_clears_active_agent(self):
        for keyword in RESET_KEYWORDS:
            state = _make_state(
                messages=[HumanMessage(content=keyword)],
                active_agent="flight",
                current_intent="FLIGHT",
            )
            result = await route_or_classify(state)
            assert result["active_agent"] is None
            assert result["previous_agent"] is None
            assert result["current_intent"] == "CANCEL_RESET"

    @pytest.mark.asyncio
    async def test_reset_keyword_clears_chain_and_shared_context(self):
        """Reset clears auto_chain and shared_context."""
        state = _make_state(
            messages=[HumanMessage(content="cancel")],
            active_agent="flight",
            auto_chain=["hotel"],
            shared_context={"trip": {"origin_iata": "AMS"}},
        )
        result = await route_or_classify(state)
        assert result["auto_chain"] == []
        assert result["shared_context"] == {}

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_hand_back_signal_clears_active_agent_and_reclassifies(
        self, mock_prompt, mock_llm
    ):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "general", "reasoning": "Weather question"}'
        )
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[HumanMessage(content="What's the weather?")],
            active_agent="flight",
            agent_signal=AgentSignal(agent_status="hand_back", reason="not flight"),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"
        assert result["previous_agent"] == "flight"
        assert result["agent_signal"] is None

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_done_signal_clears_active_agent(self, mock_prompt, mock_llm):
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "Default"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[HumanMessage(content="Thanks!")],
            active_agent="hotel",
            agent_signal=AgentSignal(agent_status="done"),
        )
        result = await route_or_classify(state)
        assert result["agent_signal"] is None

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_failed_signal_clears_and_defaults_to_general(
        self, mock_prompt, mock_llm
    ):
        mock_prompt.return_value = "You are a router."
        mock_llm.return_value = AsyncMock(
            ainvoke=AsyncMock(side_effect=Exception("LLM error"))
        )

        state = _make_state(
            messages=[HumanMessage(content="try again")],
            active_agent="flight",
            agent_signal=AgentSignal(agent_status="failed"),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_classification_error_defaults_to_general(
        self, mock_prompt, mock_llm
    ):
        mock_prompt.return_value = "You are a router."
        mock_llm.return_value = AsyncMock(
            ainvoke=AsyncMock(side_effect=Exception("Network error"))
        )

        state = _make_state(messages=[HumanMessage(content="Something")])
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"


# ========================
# TestAutoChain (Step 9)
# ========================


class TestAutoChain:
    """Tests for auto-chaining from itinerary planning_complete."""

    @pytest.mark.asyncio
    async def test_planning_complete_starts_auto_chain(self):
        """Itinerary planning_complete with booking_plan starts auto-chain."""
        state = _make_state(
            active_agent="itinerary",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="planning_complete",
                booking_plan=["flight", "hotel"],
            ),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "flight"
        assert result["auto_chain"] == ["hotel"]
        assert result["previous_agent"] == "itinerary"

    @pytest.mark.asyncio
    async def test_planning_complete_single_agent(self):
        """booking_plan with single agent -- no chain remaining."""
        state = _make_state(
            active_agent="itinerary",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="planning_complete",
                booking_plan=["flight"],
            ),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "flight"
        assert result["auto_chain"] == []

    @pytest.mark.asyncio
    async def test_planning_complete_hotel_first_order(self):
        """User-specified order: hotel first, then flight."""
        state = _make_state(
            active_agent="itinerary",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="planning_complete",
                booking_plan=["hotel", "flight"],
            ),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        assert result["auto_chain"] == ["flight"]

    @pytest.mark.asyncio
    async def test_auto_chain_pop_on_done(self):
        """When agent done and auto_chain has entries, pop next."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],
            agent_signal=AgentSignal(
                agent_status="done", done_reason="booking_complete"
            ),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        assert result["auto_chain"] == []
        assert result["previous_agent"] == "flight"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_auto_chain_empty_clears(self, mock_prompt, mock_llm):
        """When auto_chain is empty after done, clear active_agent."""
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "Done"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            active_agent="hotel",
            auto_chain=[],
            agent_signal=AgentSignal(
                agent_status="done", done_reason="booking_complete"
            ),
        )
        result = await route_or_classify(state)
        # Should go to LLM classification (active_agent cleared)
        assert result["agent_signal"] is None


# ========================
# TestPartialBookingRecovery (Step 9)
# ========================


class TestPartialBookingRecovery:
    """Tests for partial booking recovery when agent fails mid-chain."""

    @pytest.mark.asyncio
    async def test_failed_during_chain_routes_to_general(self):
        """Failed agent during auto-chain routes to general."""
        state = _make_state(
            active_agent="hotel",
            auto_chain=["flight"],
            shared_context={
                "flight_booking": {"booked": True, "confirmation_id": "FL-123"}
            },
            agent_signal=AgentSignal(agent_status="failed"),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"
        assert result["auto_chain"] == []
        assert result["previous_agent"] == "hotel"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_failed_without_chain_clears(self, mock_prompt, mock_llm):
        """Failed agent without chain/data just clears and reclassifies."""
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "fallback"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[HumanMessage(content="help")],
            active_agent="flight",
            agent_signal=AgentSignal(agent_status="failed"),
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "general"


# ========================
# TestPendingNeedsInputAgent
# ========================


class TestPendingNeedsInputAgent:
    """Tests for pending_needs_input_agent preservation and restoration.

    Scenario: "book everything" → flight returns NEEDS_INPUT (missing origin)
    while hotel is still in the auto_chain. The supervisor:
      1. Saves flight as pending_needs_input_agent and routes to hotel.
      2. When hotel finishes (DONE, auto_chain empty), restores flight as
         active_agent so the next user message goes back to the waiting agent.
    """

    @pytest.mark.asyncio
    async def test_needs_input_with_auto_chain_sets_pending_agent(self):
        """NEEDS_INPUT + non-empty auto_chain → pending agent saved, routes to next."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],
            agent_signal=AgentSignal(agent_status="needs_input"),
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "hotel"
        assert result["pending_needs_input_agent"] == "flight"
        assert result["auto_chain"] == []

    @pytest.mark.asyncio
    async def test_needs_input_with_multi_chain_sets_pending_and_pops_next(self):
        """NEEDS_INPUT + multi-entry auto_chain → pending saved, chain properly trimmed."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel", "itinerary"],
            agent_signal=AgentSignal(agent_status="needs_input"),
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "hotel"
        assert result["pending_needs_input_agent"] == "flight"
        assert result["auto_chain"] == ["itinerary"]

    @pytest.mark.asyncio
    async def test_done_with_pending_agent_and_empty_chain_restores_it(self):
        """DONE + empty auto_chain + pending_needs_input_agent → restores waiting agent."""
        state = _make_state(
            active_agent="hotel",
            auto_chain=[],
            pending_needs_input_agent="flight",
            agent_signal=AgentSignal(
                agent_status="done", done_reason="booking_complete"
            ),
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "flight"
        assert result["pending_needs_input_agent"] is None
        assert result["agent_signal"] is None

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_done_without_pending_agent_does_not_restore(
        self, mock_prompt, mock_llm
    ):
        """DONE + empty chain + no pending agent → does NOT set active_agent to a stale value."""
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "Done"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            messages=[HumanMessage(content="Thanks!")],
            active_agent="hotel",
            auto_chain=[],
            # pending_needs_input_agent not set (None by default via _make_state)
            agent_signal=AgentSignal(
                agent_status="done", done_reason="booking_complete"
            ),
        )
        result = await route_or_classify(state)

        # Should not restore any pending agent — result should NOT have active_agent="flight"
        assert result.get("pending_needs_input_agent") is None
        # LLM classified to general; crucially, flight was not restored
        assert result.get("active_agent") != "flight"


# ========================
# TestMergeSharedContext
# ========================


class TestMergeSharedContext:
    """Tests for _merge_shared_context helper."""

    def test_merge_new_key(self):
        existing = {"trip": {"origin": "AMS"}}
        updates = {"flight": {"destination": "NRT"}}
        merged = _merge_shared_context(existing, updates)
        assert merged["trip"]["origin"] == "AMS"
        assert merged["flight"]["destination"] == "NRT"

    def test_merge_existing_key_shallow(self):
        existing = {"trip": {"origin": "AMS", "adults": 2}}
        updates = {"trip": {"destination": "NRT"}}
        merged = _merge_shared_context(existing, updates)
        assert merged["trip"]["origin"] == "AMS"
        assert merged["trip"]["destination"] == "NRT"
        assert merged["trip"]["adults"] == 2

    def test_merge_override_value(self):
        existing = {"trip": {"origin": "AMS"}}
        updates = {"trip": {"origin": "LHR"}}
        merged = _merge_shared_context(existing, updates)
        assert merged["trip"]["origin"] == "LHR"

    def test_merge_empty_updates(self):
        existing = {"trip": {"origin": "AMS"}}
        merged = _merge_shared_context(existing, {})
        assert merged == existing

    def test_merge_empty_existing(self):
        updates = {"trip": {"origin": "AMS"}}
        merged = _merge_shared_context({}, updates)
        assert merged == updates

    def test_merge_non_dict_value(self):
        existing = {"count": 1}
        updates = {"count": 2}
        merged = _merge_shared_context(existing, updates)
        assert merged["count"] == 2


# ========================
# TestDispatchAgents
# ========================


class TestDispatchAgents:
    """Tests for the per-agent dispatch nodes with unified state (inner agents)."""

    def _make_mock_inner_agent(self, input_messages, new_ai_message="AI response"):
        """Create a mock inner agent that returns input messages + new AI message."""
        ai_msg = AIMessage(content=new_ai_message)
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [*input_messages, ai_msg]}
        )
        return mock_agent

    @pytest.mark.asyncio
    async def test_dispatch_flight(self):
        state = _make_state(active_agent="flight")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Where would you like to fly?")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value={
                    "message": "Where would you like to fly?",
                    "type": "flight_conversation",
                },
            ),
        ):
            result = await dispatch_flight(state)
            assert result["agent_response"]["message"] == "Where would you like to fly?"
            assert result["agent_signal"]["agent_status"] == "needs_input"
            # New messages appended
            assert len(result["messages"]) == 1  # 1 new AI message

    @pytest.mark.asyncio
    async def test_dispatch_hotel(self):
        state = _make_state(active_agent="hotel")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Which city for your hotel?")
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value={
                    "message": "Which city for your hotel?",
                    "type": "hotel_conversation",
                },
            ),
        ):
            result = await dispatch_hotel(state)
            assert result["agent_response"]["message"] == "Which city for your hotel?"
            assert result["agent_signal"]["agent_status"] == "needs_input"

    @pytest.mark.asyncio
    async def test_dispatch_itinerary(self):
        state = _make_state(active_agent="itinerary")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Let's plan your trip!")
        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value={"message": "Let's plan your trip!", "type": "message"},
            ),
        ):
            result = await dispatch_itinerary(state)
            assert result["agent_response"]["message"] == "Let's plan your trip!"
            assert result["agent_signal"]["agent_status"] == "needs_input"

    @pytest.mark.asyncio
    async def test_dispatch_general(self):
        state = _make_state(active_agent="general")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Hello! How can I help?")
        with (
            patch(
                "app.ai.graph.general_graph.get_general_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.general_graph.process_general_messages",
                return_value={
                    "message": "Hello! How can I help?",
                    "type": "ai_response",
                },
            ),
        ):
            result = await dispatch_general(state)
            assert result["agent_response"]["message"] == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_dispatch_detects_hand_back_signal(self):
        state = _make_state(active_agent="flight")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Let me redirect you.")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value={
                    "message": "Let me redirect you.",
                    "type": "hand_back",
                    "signal": "hand_back",
                    "reason": "User asking about hotels",
                    "is_detour": False,
                },
            ),
        ):
            result = await dispatch_flight(state)
            assert result["agent_signal"]["agent_status"] == "hand_back"

    @pytest.mark.asyncio
    async def test_dispatch_detects_done_signal_from_redirect(self):
        state = _make_state(active_agent="hotel")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Great choice!")
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value={
                    "message": "Great choice!",
                    "type": "hotel_booking_redirect",
                    "redirect_url": "https://example.com/book",
                },
            ),
        ):
            result = await dispatch_hotel(state)
            assert result["agent_signal"]["agent_status"] == "done"
            assert result["agent_signal"]["done_reason"] == "booking_complete"

    @pytest.mark.asyncio
    async def test_dispatch_error_returns_failed_signal(self):
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("Agent crashed"))
        with patch(
            "app.ai.graph.flight_graph.get_flight_inner_agent",
            return_value=mock_agent,
        ):
            state = _make_state(active_agent="flight")
            result = await dispatch_flight(state)
            assert result["agent_signal"]["agent_status"] == "failed"
            # AI-CHAT-010: the catch-all now routes through the classifier;
            # a bare ``Exception`` lands in the UNKNOWN class, which surfaces
            # the "Something unexpected happened" copy + error_class field.
            assert result["agent_response"]["type"] == "error"
            assert result["agent_response"]["error_class"] == "unknown"
            assert "unexpected" in result["agent_response"]["message"].lower()

    @pytest.mark.asyncio
    async def test_dispatch_passes_full_messages_to_inner_agent(self):
        """Inner agent receives the supervisor's full message history."""
        state = _make_state(
            active_agent="flight",
            messages=[
                HumanMessage(content="Plan a trip to Tokyo"),
                AIMessage(content="I'll help plan your Tokyo trip!"),
                HumanMessage(content="Now book flights"),
            ],
        )
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Searching flights to Tokyo...")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value={
                    "message": "Searching flights to Tokyo...",
                    "type": "flight_conversation",
                },
            ),
        ):
            await dispatch_flight(state)
            # Verify inner agent received ALL messages
            call_args = mock_agent.ainvoke.call_args
            passed_messages = call_args[0][0]["messages"]
            assert len(passed_messages) == 3
            assert passed_messages[0].content == "Plan a trip to Tokyo"
            assert passed_messages[2].content == "Now book flights"

    @pytest.mark.asyncio
    async def test_dispatch_returns_only_new_messages(self):
        """Only new messages from inner agent are returned (not full history)."""
        state = _make_state(
            active_agent="general",
            messages=[HumanMessage(content="hello"), AIMessage(content="previous")],
        )
        msgs = state["messages"]
        new_ai = AIMessage(content="New response")
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={"messages": [*msgs, new_ai]})
        with (
            patch(
                "app.ai.graph.general_graph.get_general_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.general_graph.process_general_messages",
                return_value={"message": "New response", "type": "ai_response"},
            ),
        ):
            result = await dispatch_general(state)
            # Only the new AI message, not the original 2
            assert len(result["messages"]) == 1
            assert result["messages"][0].content == "New response"

    @pytest.mark.asyncio
    async def test_dispatch_hotel_passes_user_id_in_config(self):
        """Hotel inner agent receives user_id in config for select_hotel tool."""
        state = _make_state(active_agent="hotel", user_id="user-abc")
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Searching hotels...")
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value={
                    "message": "Searching hotels...",
                    "type": "hotel_conversation",
                },
            ),
        ):
            await dispatch_hotel(state)
            call_kwargs = mock_agent.ainvoke.call_args[1]
            assert call_kwargs["config"]["configurable"]["user_id"] == "user-abc"


# ========================
# TestHandBackTool
# ========================


class TestHandBackTool:
    """Tests for the hand_back_to_supervisor tool."""

    @pytest.mark.asyncio
    async def test_tool_returns_correct_schema(self):
        result = await hand_back_to_supervisor.ainvoke(
            {"reason": "User asking about hotels"}
        )
        assert result["status"] == "hand_back"
        assert result["reason"] == "User asking about hotels"
        assert result["is_detour"] is False
        assert "instruction" in result

    @pytest.mark.asyncio
    async def test_tool_with_is_detour_true(self):
        result = await hand_back_to_supervisor.ainvoke(
            {"reason": "Weather question", "is_detour": True}
        )
        assert result["status"] == "hand_back"
        assert result["is_detour"] is True

    @pytest.mark.asyncio
    async def test_tool_captures_reason(self):
        result = await hand_back_to_supervisor.ainvoke(
            {"reason": "Weather question, not my domain"}
        )
        assert result["reason"] == "Weather question, not my domain"

    def test_tool_has_docstring(self):
        assert hand_back_to_supervisor.description
        assert "NOT related to your domain" in hand_back_to_supervisor.description

    def test_tool_name(self):
        assert hand_back_to_supervisor.name == "hand_back_to_supervisor"


# ========================
# TestBuildRecentContext
# ========================


class TestBuildRecentContext:
    """Tests for _build_recent_context helper."""

    def test_builds_context_from_human_messages(self):
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi!"),
            HumanMessage(content="Book a flight"),
        ]
        context = _build_recent_context(messages, max_messages=5)
        assert "User: Hello" in context
        assert "User: Book a flight" in context
        assert "Hi!" not in context

    def test_limits_messages(self):
        messages = [HumanMessage(content=f"msg{i}") for i in range(10)]
        context = _build_recent_context(messages, max_messages=3)
        assert "msg7" in context
        assert "msg8" in context
        assert "msg9" in context
        assert "msg0" not in context

    def test_empty_messages_returns_empty(self):
        assert _build_recent_context([], max_messages=5) == ""


class TestClearStaleAgentCheckpoints:
    """Tests for _clear_stale_agent_checkpoints (V1->V2 migration guard)."""

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client")
    def test_clears_checkpoints_and_writes(self, mock_client):
        mock_collection = MagicMock()
        mock_collection.delete_many.return_value = MagicMock(deleted_count=1)
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        _clear_stale_agent_checkpoints("chat-old")

        assert mock_collection.delete_many.call_count == 14
        mock_collection.delete_many.assert_any_call({"thread_id": "chat-old"})

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client", None)
    def test_skips_when_no_client(self):
        _clear_stale_agent_checkpoints("chat-old")

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client")
    def test_handles_db_error_gracefully(self, mock_client):
        mock_collection = MagicMock()
        mock_collection.delete_many.side_effect = Exception("DB error")
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        _clear_stale_agent_checkpoints("chat-old")


# ========================
# TestCaptureSharedContext (Structured Context)
# ========================


class TestCaptureSharedContext:
    """Tests for _capture_shared_context -- extracting data from agent responses."""

    @pytest.mark.asyncio
    async def test_capture_from_itinerary_cross_agent_data(self):
        """Itinerary cross_agent_data -> shared_context['trip']."""
        response = {
            "cross_agent_data": {
                "origin_iata": "AMS",
                "destination_iata": "NRT",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
            },
        }
        result = await _capture_shared_context("itinerary", response, {})
        assert result["trip"]["origin_iata"] == "AMS"
        assert result["trip"]["destination_iata"] == "NRT"
        assert result["trip"]["departure_date"] == "2026-04-01"
        assert result["trip"]["adults"] == 2

    @pytest.mark.asyncio
    async def test_capture_from_flight_collected_params(self):
        """Flight collected_params -> shared_context['flight']."""
        response = {
            "collected_params": {
                "origin": "AMS",
                "destination": "NRT",
                "departure_date": "2026-04-01",
                "adults": 2,
            },
            "type": "flight_conversation",
        }
        result = await _capture_shared_context("flight", response, {})
        assert result["flight"]["origin"] == "AMS"
        assert result["flight"]["destination"] == "NRT"

    @pytest.mark.asyncio
    async def test_capture_from_hotel_collected_params(self):
        """Hotel collected_params -> shared_context['hotel']."""
        response = {
            "collected_params": {
                "city": "Tokyo",
                "country": "Japan",
                "checkin": "2026-04-01",
                "checkout": "2026-04-06",
                "adults": 2,
            },
            "type": "hotel_conversation",
        }
        result = await _capture_shared_context("hotel", response, {})
        assert result["hotel"]["city"] == "Tokyo"
        assert result["hotel"]["checkin"] == "2026-04-01"

    @pytest.mark.asyncio
    async def test_capture_flight_booking_redirect(self):
        """Flight booking redirect -> shared_context['flight_booking']."""
        response = {
            "type": "flight_booking_redirect",
            "session_id": "sess-123",
        }
        result = await _capture_shared_context("flight", response, {})
        assert result["flight_booking"]["booked"] is True
        assert result["flight_booking"]["session_id"] == "sess-123"

    @pytest.mark.asyncio
    async def test_capture_hotel_booking_redirect(self):
        """Hotel booking redirect -> shared_context['hotel_booking']."""
        response = {
            "type": "hotel_booking_redirect",
            "session_id": "sess-456",
        }
        result = await _capture_shared_context("hotel", response, {})
        assert result["hotel_booking"]["booked"] is True

    @pytest.mark.asyncio
    async def test_capture_preserves_existing_context(self):
        """New context merged with existing, not replaced."""
        existing = {"trip": {"origin_iata": "AMS"}}
        response = {
            "collected_params": {"origin": "LHR", "destination": "CDG"},
            "type": "flight_conversation",
        }
        result = await _capture_shared_context("flight", response, existing)
        assert result["trip"]["origin_iata"] == "AMS"
        assert result["flight"]["origin"] == "LHR"

    @pytest.mark.asyncio
    async def test_capture_empty_response_returns_existing(self):
        """No capturable data -> return existing context unchanged."""
        existing = {"trip": {"origin_iata": "AMS"}}
        response = {"message": "Hello", "type": "message"}
        result = await _capture_shared_context("itinerary", response, existing)
        assert result is existing

    @pytest.mark.asyncio
    async def test_capture_general_agent_without_travel_context_returns_existing(self):
        """General agent without travel_context produces no shared context update."""
        existing = {"trip": {"origin_iata": "AMS"}}
        response = {"message": "Hello", "type": "ai_response"}
        result = await _capture_shared_context("general", response, existing)
        assert result is existing

    @pytest.mark.asyncio
    async def test_capture_general_agent_with_travel_context(self):
        """General agent travel_context -> shared_context['general']."""
        existing = {"trip": {"origin_iata": "AMS"}}
        response = {
            "message": "Dubai sounds great!",
            "type": "ai_response",
            "travel_context": {
                "destination": "Dubai",
                "dates": "next weekend",
                "travelers": "2 adults",
                "interests": "beaches, food",
            },
        }
        result = await _capture_shared_context("general", response, existing)
        assert result["general"]["destination"] == "Dubai"
        assert result["general"]["dates"] == "next weekend"
        assert result["general"]["travelers"] == "2 adults"
        assert result["general"]["interests"] == "beaches, food"
        # Existing context preserved
        assert result["trip"]["origin_iata"] == "AMS"

    @pytest.mark.asyncio
    async def test_capture_general_agent_partial_travel_context(self):
        """General agent with only destination in travel_context."""
        response = {
            "travel_context": {"destination": "Japan"},
        }
        result = await _capture_shared_context("general", response, {})
        assert result["general"]["destination"] == "Japan"


# ========================
# TestResolveDestination
# ========================


class TestResolveDestination:
    """Tests for _resolve_destination — geocoding landmarks vs cities."""

    @pytest.mark.asyncio
    @patch("app.domains.airport.airport_resolver.AirportResolver")
    @patch("app.shared.geocoding.GeocodingService.geocode_city")
    async def test_landmark_returns_city_and_nearby_coords(
        self, mock_geocode, mock_resolver_cls
    ):
        """Landmark (Walt Disney World) → nearest airport city + nearby_lat/nearby_lng.

        Geocoding returns "Bay Lake" (tiny municipality) but the travel city
        upgrade finds MCO (Orlando International) nearby and returns "Orlando".
        """
        from app.shared.geocoding import GeocodingResult

        # Mock AirportResolver so unit test doesn't need airports_cache.json
        mock_resolver = AsyncMock()
        mock_resolver.get_airports_by_city_name = AsyncMock(return_value=[])
        mock_resolver.airports_data = {
            "MCO": {
                "iata": "MCO",
                "name": "Orlando International Airport",
                "city": "Orlando",
                "lat": 28.4312,
                "lon": -81.3081,
            }
        }
        mock_resolver_cls.return_value = mock_resolver

        mock_geocode.return_value = [
            GeocodingResult(
                city="Bay Lake",
                country="United States",
                country_code="US",
                formatted_address="Walt Disney World, FL, USA",
                lat=28.3772,
                lng=-81.5707,
                result_types=["amusement_park", "point_of_interest"],
            )
        ]
        result = await _resolve_destination("Walt Disney World")
        # Bay Lake has no airport → upgraded to Orlando (nearest intl airport)
        assert result["destination_city"] == "Orlando"
        assert result["destination_country"] == "United States"
        assert result["nearby_lat"] == 28.3772
        assert result["nearby_lng"] == -81.5707

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService.geocode_city")
    async def test_city_returns_city_without_nearby_coords(self, mock_geocode):
        """Plain city (Paris) → destination_city set, no nearby_lat/nearby_lng."""
        from app.shared.geocoding import GeocodingResult

        mock_geocode.return_value = [
            GeocodingResult(
                city="Paris",
                country="France",
                country_code="FR",
                formatted_address="Paris, France",
                lat=48.8566,
                lng=2.3522,
                result_types=["locality", "political"],
            )
        ]
        result = await _resolve_destination("Paris")
        assert result["destination_city"] == "Paris"
        assert result["destination_country"] == "France"
        assert "nearby_lat" not in result
        assert "nearby_lng" not in result

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService.geocode_city")
    async def test_geocoding_failure_returns_empty(self, mock_geocode):
        """Geocoding failure → empty dict (graceful fallback)."""
        mock_geocode.return_value = []
        result = await _resolve_destination("Nonexistent Place")
        assert result == {}

    @pytest.mark.asyncio
    @patch("app.shared.geocoding.GeocodingService.geocode_city")
    async def test_geocoding_exception_returns_empty(self, mock_geocode):
        """Geocoding raises exception → empty dict."""
        mock_geocode.side_effect = Exception("API down")
        result = await _resolve_destination("Walt Disney World")
        assert result == {}


class TestCaptureWithDestinationResolution:
    """Tests for _capture_shared_context with destination resolution."""

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.supervisor_v2._resolve_destination",
        return_value={
            "destination_city": "Bay Lake",
            "destination_country": "United States",
            "nearby_lat": 28.3772,
            "nearby_lng": -81.5707,
        },
    )
    async def test_itinerary_landmark_resolved_to_city(self, mock_resolve):
        """Itinerary with landmark destination → city + coords stored."""
        response = {
            "type": "itinerary_results",
            "cross_agent_data": {
                "destination": "Walt Disney World",
                "departure_date": "2026-05-15",
                "return_date": "2026-05-20",
                "adults": 2,
            },
        }
        result = await _capture_shared_context("itinerary", response, {})
        trip = result["trip"]
        assert trip["destination"] == "Walt Disney World"
        assert trip["destination_city"] == "Bay Lake"
        assert trip["destination_country"] == "United States"
        assert trip["nearby_lat"] == 28.3772
        assert trip["nearby_lng"] == -81.5707
        mock_resolve.assert_awaited_once_with("Walt Disney World")

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._resolve_destination")
    async def test_skips_resolution_when_already_resolved(self, mock_resolve):
        """No geocoding call if destination_city already in context."""
        existing = {
            "trip": {
                "destination": "Walt Disney World",
                "destination_city": "Bay Lake",
            }
        }
        response = {
            "cross_agent_data": {
                "destination": "Walt Disney World",
                "adults": 3,
            },
        }
        await _capture_shared_context("itinerary", response, existing)
        mock_resolve.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._resolve_destination")
    async def test_no_destination_skips_resolution(self, mock_resolve):
        """No destination in itinerary response → no geocoding call."""
        response = {
            "cross_agent_data": {"origin_iata": "AMS", "adults": 2},
        }
        await _capture_shared_context("itinerary", response, {})
        mock_resolve.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._resolve_destination", return_value={})
    async def test_failed_resolution_preserves_original(self, mock_resolve):
        """Geocoding returns empty → original destination preserved, no crash."""
        response = {
            "cross_agent_data": {"destination": "Unknown Place", "adults": 1},
        }
        result = await _capture_shared_context("itinerary", response, {})
        assert result["trip"]["destination"] == "Unknown Place"
        assert "destination_city" not in result["trip"]


class TestFormatContextWithNearby:
    """Tests for _format_context_for_agent with nearby coords."""

    def test_hotel_context_uses_resolved_city(self):
        """Hotel context uses destination_city over raw destination."""
        context = {
            "trip": {
                "destination": "Walt Disney World",
                "destination_city": "Bay Lake",
                "destination_country": "United States",
                "departure_date": "2026-05-15",
                "return_date": "2026-05-20",
                "adults": 2,
                "nearby_lat": 28.3772,
                "nearby_lng": -81.5707,
            }
        }
        formatted, _ = _format_context_for_agent(context, "hotel")
        assert "Bay Lake" in formatted
        assert "United States" in formatted
        assert "28.3772" in formatted
        assert "-81.5707" in formatted
        assert "search_hotels" in formatted
        # The raw destination should NOT appear as the city
        assert "City: Walt Disney World" not in formatted

    def test_hotel_context_includes_nearby_in_search_call(self):
        """When nearby coords present, search_hotels call includes them."""
        context = {
            "trip": {
                "destination": "Colosseum",
                "destination_city": "Rome",
                "destination_country": "Italy",
                "departure_date": "2026-06-01",
                "return_date": "2026-06-05",
                "adults": 2,
                "nearby_lat": 41.8902,
                "nearby_lng": 12.4922,
            }
        }
        formatted, _ = _format_context_for_agent(context, "hotel")
        assert "nearby_lat=41.89" in formatted
        assert "nearby_lng=12.49" in formatted

    def test_hotel_context_no_nearby_for_city(self):
        """Plain city → no nearby coords in context."""
        context = {
            "trip": {
                "destination": "Paris",
                "destination_city": "Paris",
                "destination_country": "France",
                "departure_date": "2026-06-01",
                "return_date": "2026-06-05",
                "adults": 2,
            }
        }
        formatted, _ = _format_context_for_agent(context, "hotel")
        assert "Paris" in formatted
        assert "nearby_lat" not in formatted
        assert "nearby_lng" not in formatted

    def test_flight_context_uses_resolved_city(self):
        """Flight context uses destination_city for airport resolution."""
        context = {
            "trip": {
                "destination": "Walt Disney World",
                "destination_city": "Bay Lake",
                "departure_date": "2026-05-15",
                "adults": 2,
            }
        }
        formatted, _ = _format_context_for_agent(context, "flight")
        assert "Destination: Bay Lake" in formatted
        # Should NOT use the raw landmark as destination
        assert "Destination: Walt Disney World" not in formatted


# ========================
# TestFormatContextForAgent
# ========================


class TestFormatContextForAgent:
    """Tests for _format_context_for_agent -- formatting shared_context for agents."""

    def test_format_for_flight_from_trip(self):
        """Trip data formatted for flight agent."""
        ctx = {
            "trip": {
                "origin_iata": "AMS",
                "destination_iata": "NRT",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "KNOWN CONTEXT" in result
        assert "AMS" in result
        assert "NRT" in result
        assert "2026-04-01" in result
        assert "Adults: 2" in result

    def test_format_for_hotel_from_trip(self):
        """Trip data mapped for hotel agent (destination -> city)."""
        ctx = {
            "trip": {
                "destination": "Tokyo",
                "destination_country": "Japan",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "KNOWN CONTEXT" in result
        assert "Tokyo" in result
        assert "Japan" in result
        assert "2026-04-01" in result

    def test_format_for_flight_from_hotel(self):
        """Hotel data mapped for flight agent (city -> destination)."""
        ctx = {
            "hotel": {
                "city": "Rome",
                "checkin": "2026-05-05",
                "checkout": "2026-05-10",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "KNOWN CONTEXT" in result
        assert "Rome" in result
        assert "2026-05-05" in result

    def test_format_for_hotel_from_flight(self):
        """Flight data mapped for hotel agent — city name used, not IATA code."""
        ctx = {
            "flight": {
                "destination": "NRT",
                "destination_city": "Tokyo",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "KNOWN CONTEXT" in result
        assert "Tokyo" in result
        assert "NRT" not in result  # IATA codes must not be passed as city names
        assert "2026-04-01" in result

    def test_prefers_city_name_over_iata_in_trip_context(self):
        """Regression test for #796: when both origin and origin_iata present, city name wins."""
        ctx = {
            "trip": {
                "origin": "London",
                "origin_iata": "LHR",
                "destination": "Cancun",
                "destination_iata": "CUN",
                "departure_date": "2026-05-01",
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "London" in result
        assert "Cancun" in result
        assert "LHR" not in result
        assert "CUN" not in result

    def test_format_for_general_returns_empty(self):
        """General agent gets no context."""
        ctx = {"trip": {"origin_iata": "AMS"}}
        result, _ = _format_context_for_agent(ctx, "general")
        assert result == ""

    def test_format_empty_context_returns_empty(self):
        """Empty shared_context returns empty string."""
        result, _ = _format_context_for_agent({}, "flight")
        assert result == ""

    def test_flight_destination_locked_annotation(self):
        """Flight destination is annotated as locked when pre-filled."""
        ctx = {"trip": {"destination": "London"}}
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Destination: London" in result
        assert "do NOT ask the user about this" in result

    def test_flight_missing_fields_listed(self):
        """Flight agent receives explicit list of missing fields to ask."""
        ctx = {"trip": {"destination": "London"}}
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Ask for ALL of these in ONE numbered message" in result
        assert "origin city" in result
        assert "departure date" in result
        assert "passenger count" in result
        assert "trip type" in result

    def test_flight_roundtrip_inferred_from_return_date(self):
        """When both departure and return dates exist, trip type = round-trip."""
        ctx = {
            "trip": {
                "destination": "London",
                "departure_date": "2026-04-10",
                "return_date": "2026-04-17",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "round-trip (inferred from return date" in result
        assert "trip type (one-way or round-trip)" not in result

    def test_flight_no_return_asks_trip_type(self):
        """Without return date, trip type is in the missing fields list."""
        ctx = {
            "trip": {
                "destination": "London",
                "departure_date": "2026-04-10",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "trip type (one-way or round-trip)" in result
        assert "round-trip (inferred" not in result

    def test_flight_all_fields_present_no_ask_hint(self):
        """When origin is present, no 'Ask for ALL' hint is added."""
        ctx = {
            "trip": {
                "origin_iata": "AMS",
                "destination": "London",
                "departure_date": "2026-04-10",
                "return_date": "2026-04-17",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Ask for ALL" not in result

    def test_hotel_missing_fields_listed(self):
        """Hotel agent receives explicit list of missing fields to ask."""
        ctx = {"trip": {"destination": "London"}}
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "Ask for ALL of these in ONE numbered message" in result
        assert "number of adults" in result

    def test_hotel_all_fields_present_no_ask_hint(self):
        """When all hotel fields are present, no 'Ask for ALL' hint."""
        ctx = {
            "trip": {
                "destination": "London",
                "departure_date": "2026-04-10",
                "return_date": "2026-04-17",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "Ask for ALL" not in result

    def test_hotel_all_fields_with_country_injects_search_hotels(self):
        """When city, country, dates, and adults are present, inject search_hotels call."""
        ctx = {
            "trip": {
                "destination": "Paris",
                "destination_country": "France",
                "departure_date": "2026-05-01",
                "return_date": "2026-05-05",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "search_hotels" in result
        assert "IMMEDIATELY" in result
        assert "Paris" in result
        assert "France" in result
        assert "Do NOT call resolve_city" in result

    def test_hotel_all_fields_without_country_injects_resolve_city(self):
        """When country is missing but other fields present, inject resolve_city call."""
        ctx = {
            "trip": {
                "destination": "Tokyo",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-06",
                "adults": 2,
            }
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "resolve_city" in result
        assert 'resolve_city("Tokyo")' in result
        assert "search_hotels" in result

    def test_hotel_chain_from_flight_with_country(self):
        """Hotel chain dispatch from flight: country from trip context triggers immediate search."""
        ctx = {
            "flight": {
                "destination": "CDG",
                "destination_city": "Paris",
                "departure_date": "2026-05-01",
                "return_date": "2026-05-05",
                "adults": 2,
            },
            "trip": {
                "destination_country": "France",
            },
        }
        result, _ = _format_context_for_agent(ctx, "hotel")
        assert "search_hotels" in result
        assert "IMMEDIATELY" in result
        assert "Paris" in result
        assert "CDG" not in result  # IATA should not leak as city name


# ========================
# TestBuildAgentMessages
# ========================


class TestBuildAgentMessages:
    """Tests for _build_agent_messages -- message construction for agents."""

    def test_auto_chain_with_context(self):
        """Auto-chain: returns single HumanMessage with context, NOT full history."""
        state = _make_state(
            messages=[
                HumanMessage(content="Plan a trip to Tokyo"),
                AIMessage(content="I planned your trip!"),
                HumanMessage(content="book everything"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={
                "trip": {
                    "origin_iata": "AMS",
                    "destination_iata": "NRT",
                    "departure_date": "2026-04-01",
                    "adults": 2,
                }
            },
        )
        msgs = _build_agent_messages(state, "flight")
        # Single HumanMessage with context + instruction merged
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert "SYSTEM CONTEXT" in msgs[0].content
        assert "AMS" in msgs[0].content

    def test_continuation_same_agent(self):
        """Continuation: returns full messages for same agent."""
        state = _make_state(
            messages=[
                HumanMessage(content="Book a flight to Tokyo"),
                AIMessage(content="Where are you flying from?"),
                HumanMessage(content="Amsterdam"),
            ],
            active_agent="flight",
            shared_context={},
        )
        msgs = _build_agent_messages(state, "flight")
        # No shared context, same agent -> full messages
        assert len(msgs) == 3
        assert msgs[0].content == "Book a flight to Tokyo"
        assert msgs[2].content == "Amsterdam"

    def test_dispatch_uses_context_messages(self):
        """Verify _build_agent_messages produces context for agent switch."""
        state = _make_state(
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={
                "trip": {
                    "origin_iata": "AMS",
                    "destination_iata": "NRT",
                    "departure_date": "2026-04-01",
                    "adults": 2,
                }
            },
        )
        # The messages built should have context, not full history
        msgs = _build_agent_messages(state, "flight")
        assert isinstance(msgs[0], HumanMessage)
        assert "SYSTEM CONTEXT" in msgs[0].content

    def test_agent_switch_without_context_sends_recap_and_user_message(self):
        """Agent switch without shared_context -> recap + latest user message."""
        state = _make_state(
            messages=[
                HumanMessage(content="Plan a trip to Tokyo"),
                AIMessage(content="I've planned your trip!"),
                HumanMessage(content="now book the flights"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={},  # No context captured
        )
        msgs = _build_agent_messages(state, "flight")
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        # Recap provides conversation context even without shared_context
        assert "SYSTEM CONTEXT" in msgs[0].content
        assert "now book the flights" in msgs[0].content
        assert "Tokyo" in msgs[0].content

    def test_same_agent_handback_redispatch_sends_agent_conversation(self):
        """Same agent hands back + re-dispatched -> agent's full conversation segment."""
        state = _make_state(
            messages=[
                HumanMessage(content="Book a flight to Paris"),
                AIMessage(content="Sure!"),
                HumanMessage(content="from London"),
            ],
            active_agent="flight",
            previous_agent="flight",  # Same agent handed back
            shared_context={},
            agent_start_index=0,
        )
        msgs = _build_agent_messages(state, "flight")
        # Mode 2: returns full conversation from agent_start_index
        assert len(msgs) == 3
        assert msgs[0].content == "Book a flight to Paris"
        assert msgs[2].content == "from London"


class TestBuildAgentMessagesSearchContext:
    """Tests for 'No search has been performed yet' in _build_agent_messages."""

    def test_auto_chain_contains_no_search_yet(self):
        """Auto-chain instruction includes 'No search has been performed yet'."""
        state = _make_state(
            messages=[
                HumanMessage(content="book everything"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={
                "trip": {
                    "destination": "London",
                    "departure_date": "2026-04-10",
                    "return_date": "2026-04-17",
                    "adults": 2,
                }
            },
            auto_chain=["flight"],
            chain_responses=[],
        )
        msgs = _build_agent_messages(state, "flight")
        assert "No search has been performed yet" in msgs[0].content

    def test_auto_chain_no_last_message_suffix_in_instruction(self):
        """Auto-chain mode does NOT append 'The user's last message was' suffix."""
        state = _make_state(
            messages=[
                HumanMessage(content="book everything"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={"trip": {"destination": "London"}},
            auto_chain=["flight"],
            chain_responses=[],
        )
        msgs = _build_agent_messages(state, "flight")
        # Auto-chain omits the "The user's last message was:" suffix
        assert "The user's last message was" not in msgs[0].content

    def test_non_auto_chain_includes_user_message(self):
        """Non-auto-chain agent switch includes user's last message."""
        state = _make_state(
            messages=[
                HumanMessage(content="I want to fly to London"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={"trip": {"destination": "London"}},
        )
        msgs = _build_agent_messages(state, "flight")
        assert "I want to fly to London" in msgs[0].content
        assert "No search has been performed yet" in msgs[0].content


class TestAfterDispatchLoopGuard:
    """Tests for _after_dispatch loop limit enforcement."""

    def test_loop_ends_when_remaining_steps_zero(self):
        """_after_dispatch returns END when remaining_steps <= 0."""
        state = _make_state(
            remaining_steps=0,
            agent_signal=AgentSignal(agent_status="hand_back", reason="confused"),
        )
        # With 0 remaining, should force END even though signal says hand_back
        assert _after_dispatch(state) == "__end__"

    def test_loop_continues_with_remaining_steps(self):
        """_after_dispatch loops when remaining_steps > 0 and signal is actionable."""
        state = _make_state(
            remaining_steps=3,
            agent_signal=AgentSignal(agent_status="hand_back", reason="test"),
        )
        assert _after_dispatch(state) == "route_or_classify"

    def test_loop_ends_on_needs_input(self):
        """_after_dispatch returns END for needs_input regardless of remaining_steps."""
        state = _make_state(
            remaining_steps=5,
            agent_signal=AgentSignal(agent_status="needs_input"),
        )
        assert _after_dispatch(state) == "__end__"


# ========================
# TestDispatchTimeout
# ========================


class TestDispatchTimeout:
    """Tests for timeout and error handling in _dispatch_agent."""

    @pytest.mark.asyncio
    async def test_dispatch_flight_timeout_returns_error(self):
        """TimeoutError on flight agent returns error response, not exception."""
        state = _make_state(active_agent="flight", remaining_steps=5)
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=TimeoutError())

        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_agent,
            ),
        ):
            result = await dispatch_flight(state)

        assert result["agent_response"]["type"] == "error"
        # AI-CHAT-010: error message + class now come from the central
        # classifier. TimeoutError maps to TRANSIENT_API.
        assert result["agent_response"]["error_class"] == "transient_api"
        assert (
            "travel-data partner is slow" in result["agent_response"]["message"].lower()
        )
        assert result["agent_signal"]["agent_status"] == "failed"
        assert result["previous_agent"] is None
        assert result["remaining_steps"] == 4

    @pytest.mark.asyncio
    async def test_dispatch_hotel_timeout_returns_error(self):
        """TimeoutError on hotel agent returns error response."""
        state = _make_state(active_agent="hotel", remaining_steps=5)
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=TimeoutError())

        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_agent,
            ),
        ):
            result = await dispatch_hotel(state)

        assert result["agent_response"]["type"] == "error"
        assert result["agent_signal"]["agent_status"] == "failed"

    @pytest.mark.asyncio
    async def test_dispatch_general_exception_returns_error(self):
        """Generic exception on agent returns error response, not exception."""
        state = _make_state(active_agent="general", remaining_steps=5)
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=RuntimeError("API down"))

        with (
            patch(
                "app.ai.graph.general_graph.get_general_inner_agent",
                return_value=mock_agent,
            ),
        ):
            result = await dispatch_general(state)

        assert result["agent_response"]["type"] == "error"
        assert result["agent_signal"]["agent_status"] == "failed"
        assert result["previous_agent"] is None


# ========================
# TestSharedContextIntegration
# ========================


class TestSharedContextIntegration:
    """Integration tests: shared context capture → format → agent receives it."""

    @pytest.mark.asyncio
    async def test_itinerary_capture_then_format_for_flight(self):
        """Full flow: itinerary response captured → formatted for flight agent."""
        itinerary_response = {
            "message": "Here is your itinerary!",
            "type": "message",
            "cross_agent_data": {
                "origin_iata": "AMS",
                "destination_iata": "NRT",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-08",
                "adults": 2,
            },
        }
        # Step 1: capture
        context = await _capture_shared_context("itinerary", itinerary_response, {})
        assert context["trip"]["origin_iata"] == "AMS"
        assert context["trip"]["destination_iata"] == "NRT"

        # Step 2: format for flight agent
        formatted, _ = _format_context_for_agent(context, "flight")
        assert "KNOWN CONTEXT" in formatted
        assert "AMS" in formatted
        assert "NRT" in formatted
        assert "2026-04-01" in formatted
        assert "Adults: 2" in formatted

    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.supervisor_v2._resolve_destination",
        return_value={
            "destination_city": "Tokyo",
            "destination_country": "Japan",
        },
    )
    async def test_itinerary_capture_then_format_for_hotel(self, mock_resolve):
        """Full flow: itinerary response captured → formatted for hotel agent."""
        itinerary_response = {
            "message": "Here is your itinerary!",
            "type": "message",
            "cross_agent_data": {
                "destination": "Tokyo",
                "destination_country": "Japan",
                "departure_date": "2026-04-01",
                "return_date": "2026-04-08",
                "adults": 2,
            },
        }
        context = await _capture_shared_context("itinerary", itinerary_response, {})
        formatted, _ = _format_context_for_agent(context, "hotel")
        assert "KNOWN CONTEXT" in formatted
        assert "Tokyo" in formatted

    @pytest.mark.asyncio
    async def test_capture_does_not_mutate_existing_context(self):
        """_capture_shared_context returns new dict, never mutates existing."""
        existing = {"trip": {"origin_iata": "AMS"}}
        existing_id = id(existing)

        response = {
            "message": "ok",
            "type": "message",
            "cross_agent_data": {"destination_iata": "NRT"},
        }
        updated = await _capture_shared_context("itinerary", response, existing)

        # Original dict unchanged
        assert id(existing) == existing_id
        assert "destination_iata" not in existing.get("trip", {})
        # New dict has both
        assert updated["trip"]["destination_iata"] == "NRT"

    def test_build_agent_messages_uses_captured_context(self):
        """After capture, _build_agent_messages injects context as HumanMessage."""
        context = {
            "trip": {
                "origin_iata": "LHR",
                "destination_iata": "JFK",
                "departure_date": "2026-06-01",
                "adults": 1,
            }
        }
        state = _make_state(
            messages=[HumanMessage(content="book the flight")],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context=context,
        )
        msgs = _build_agent_messages(state, "flight")
        assert isinstance(msgs[0], HumanMessage)
        assert "LHR" in msgs[0].content
        assert "JFK" in msgs[0].content


# ========================
# TestDetourReturn
# ========================


class TestDetourReturn:
    """Tests for the detour/return pattern (Step 10).

    Scenario: user is booking a flight, asks a side question ("what's the weather?"),
    the general agent answers, then supervisor returns to flight — without corrupting
    the auto_chain.
    """

    @pytest.mark.asyncio
    async def test_hand_back_with_detour_sets_detour_return(self):
        """hand_back with is_detour=True sets detour_return in state update."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="weather question",
                is_detour=True,
            ),
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "general", "reasoning": "weather question"}'
        )
        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)
        assert result["detour_return"] is True
        assert result["previous_agent"] == "flight"

    @pytest.mark.asyncio
    async def test_hand_back_without_detour_does_not_set_detour_return(self):
        """hand_back without is_detour keeps detour_return=False."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="wants hotel",
            ),
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "hotel", "reasoning": "wants hotel"}'
        )
        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)
        assert result.get("detour_return") is False

    @pytest.mark.asyncio
    async def test_done_after_detour_returns_to_previous_agent(self):
        """After detour, done signal returns to previous agent, not auto_chain."""
        state = _make_state(
            active_agent="general",
            previous_agent="flight",
            auto_chain=["hotel"],
            detour_return=True,
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="query_answered",
            ),
        )
        result = await route_or_classify(state)
        # Returns to flight (the agent that initiated the detour)
        assert result["active_agent"] == "flight"
        # Auto-chain preserved — NOT popped
        assert "auto_chain" not in result
        # Detour flag cleared
        assert result["detour_return"] is False

    @pytest.mark.asyncio
    async def test_done_without_detour_pops_auto_chain(self):
        """Normal done (no detour) pops auto_chain as expected."""
        state = _make_state(
            active_agent="flight",
            previous_agent="itinerary",
            auto_chain=["hotel"],
            detour_return=False,
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="booking_complete",
            ),
        )
        result = await route_or_classify(state)
        # Pops auto_chain
        assert result["active_agent"] == "hotel"
        assert result["auto_chain"] == []


# ========================
# MULTI-INTENT TASK QUEUE (Step 13)
# ========================


class TestValidateQueuedIntents:
    """Test _validate_queued_intents helper."""

    def test_valid_single_intent(self) -> None:
        result = _validate_queued_intents(
            [{"agent": "hotel", "context": "hotel in Tokyo"}], "flight"
        )
        assert result == [{"agent": "hotel", "context": "hotel in Tokyo"}]

    def test_filters_non_queueable_agents(self) -> None:
        result = _validate_queued_intents(
            [{"agent": "general", "context": "weather"}], "flight"
        )
        assert result == []

    def test_deduplicates_agents(self) -> None:
        result = _validate_queued_intents(
            [
                {"agent": "hotel", "context": "hotel A"},
                {"agent": "hotel", "context": "hotel B"},
            ],
            "flight",
        )
        assert len(result) == 1

    def test_excludes_target_agent(self) -> None:
        result = _validate_queued_intents(
            [{"agent": "flight", "context": "another flight"}], "flight"
        )
        assert result == []

    def test_enforces_max_limit(self) -> None:
        intents = [
            {"agent": agent, "context": f"ctx {agent}"}
            for agent in ["flight", "hotel", "itinerary"]
        ]
        result = _validate_queued_intents(intents, "general")
        assert len(result) <= MAX_TASK_QUEUE_SIZE

    def test_skips_invalid_items(self) -> None:
        result = _validate_queued_intents(
            ["not_a_dict", 42, {"agent": "hotel", "context": "ok"}], "flight"
        )
        assert result == [{"agent": "hotel", "context": "ok"}]

    def test_empty_input(self) -> None:
        assert _validate_queued_intents([], "flight") == []

    def test_non_list_input(self) -> None:
        assert _validate_queued_intents("not a list", "flight") == []  # type: ignore[arg-type]


class TestExplicitBookingVerbPattern:
    """#1133 follow-up: pattern must match booking imperatives but NOT
    descriptive trip-context phrasing. False positives spawn wasted flight +
    hotel agent dispatches; false negatives leave the user re-asking."""

    def test_matches_explicit_booking_requests(self) -> None:
        from app.ai.graph.supervisor_v2 import _EXPLICIT_BOOKING_VERB_PATTERN

        for phrase in [
            "book a flight to Tokyo",
            "book flights",
            "book the hotel",
            "book everything",
            "book all",
            "find me flights",
            "find a hotel",
            "search flights to Tokyo",
            "search hotels in Paris",
            "show me flight options",
            "show flights",
            "get me hotels in Dubai",
            "look up flights from LAX",
            "reserve a room",
            # PR #1138 review: ``make`` / ``arrange`` were missing; common in
            # business-trip phrasing.
            "make a hotel reservation",
            "make a booking",
            "arrange flights from LAX",
            "arrange a hotel for the team",
        ]:
            assert _EXPLICIT_BOOKING_VERB_PATTERN.search(phrase), (
                f"should match: {phrase!r}"
            )

    def test_does_not_match_trip_context(self) -> None:
        from app.ai.graph.supervisor_v2 import _EXPLICIT_BOOKING_VERB_PATTERN

        for phrase in [
            "Plan a trip to Tokyo, flying in from the US, staying in Shibuya hotel",
            "Plan a 5-day trip to Paris",
            "flying from London",
            "departing from LAX",
            "staying in Shibuya",
            "with a 4-star hotel",
            "I want to fly to Tokyo",
            "trip with cheap flights",
            "good hotels nearby",
            "Tokyo for 7 days",
            # PR #1138 review: ``make`` / ``arrange`` false-positive guards.
            # The verbs are common in non-booking contexts — must NOT trip
            # the pattern unless paired with a booking noun.
            "make a list of things to do",
            "make sense of the itinerary",
            "make sure I bring my passport",
            "arrange the activities by day",
            "arrange the meeting after the trip",
        ]:
            assert not _EXPLICIT_BOOKING_VERB_PATTERN.search(phrase), (
                f"should NOT match: {phrase!r}"
            )


class TestStripTripContextQueue:
    """#1133 follow-up: deterministic backstop drops queued flight/hotel
    agents when the user is just describing the trip on an itinerary turn."""

    def test_drops_queue_for_itinerary_without_booking_verb(self) -> None:
        from app.ai.graph.supervisor_v2 import _strip_trip_context_queue

        msg = "Plan a 7-day trip to Tokyo, flying in from the US, staying in Shibuya hotel"
        queued = [
            {"agent": "flight", "context": "flights LAX→HND"},
            {"agent": "hotel", "context": "hotel in Tokyo"},
        ]
        result = _strip_trip_context_queue(msg, "itinerary", queued)
        assert result == []

    def test_keeps_queue_for_itinerary_with_booking_verb(self) -> None:
        from app.ai.graph.supervisor_v2 import _strip_trip_context_queue

        msg = "Plan a trip to Tokyo and book flights"
        queued = [{"agent": "flight", "context": "flights to Tokyo"}]
        result = _strip_trip_context_queue(msg, "itinerary", queued)
        assert result == queued

    def test_does_not_touch_flight_primary(self) -> None:
        """Only the itinerary branch is guarded — flight/hotel primaries
        carry their own explicit booking intent already."""
        from app.ai.graph.supervisor_v2 import _strip_trip_context_queue

        msg = "Find me a flight"  # plain flight intent, no booking verb chain
        queued = [{"agent": "hotel", "context": "hotel for the trip"}]
        result = _strip_trip_context_queue(msg, "flight", queued)
        assert result == queued

    def test_does_not_touch_hotel_primary(self) -> None:
        from app.ai.graph.supervisor_v2 import _strip_trip_context_queue

        queued = [{"agent": "flight", "context": "flight to the same city"}]
        result = _strip_trip_context_queue("just a hotel question", "hotel", queued)
        assert result == queued

    def test_empty_queue_is_passthrough(self) -> None:
        from app.ai.graph.supervisor_v2 import _strip_trip_context_queue

        result = _strip_trip_context_queue("anything", "itinerary", [])
        assert result == []


class TestParseClassificationWithQueuedIntents:
    """Test _parse_classification_response extracts queued_intents."""

    def test_single_intent_returns_empty_queue(self) -> None:
        text = '{"decision_type": "classify_new", "target_agent": "flight", "queued_intents": [], "reasoning": "flight booking"}'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "flight"
        assert result["queued_intents"] == []

    def test_multi_intent_returns_queued(self) -> None:
        text = '{"decision_type": "classify_new", "target_agent": "flight", "queued_intents": [{"agent": "hotel", "context": "hotel in London"}], "reasoning": "two intents"}'
        result = _parse_classification_response(text)
        assert result["target_agent"] == "flight"
        assert len(result["queued_intents"]) == 1
        assert result["queued_intents"][0]["agent"] == "hotel"

    def test_missing_queued_intents_defaults_to_empty(self) -> None:
        text = '{"target_agent": "flight", "reasoning": "ok"}'
        result = _parse_classification_response(text)
        assert result["queued_intents"] == []

    def test_fallback_parsing_returns_empty_queue(self) -> None:
        text = "FLIGHT is the best choice"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "flight"
        assert result["queued_intents"] == []

    def test_invalid_json_returns_empty_queue(self) -> None:
        text = "this is not json at all"
        result = _parse_classification_response(text)
        assert result["target_agent"] == "general"
        assert result["queued_intents"] == []


class TestTaskQueueRouting:
    """Test task_queue population and consumption in route_or_classify."""

    @pytest.mark.asyncio
    async def test_queue_consumed_after_done(self) -> None:
        """Agent done + task_queue non-empty → pop next task."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="booking_complete",
            ),
            task_queue=[{"agent": "hotel", "context": "hotel in London"}],
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        assert result["task_queue"] == []
        assert result["previous_agent"] == "flight"

    @pytest.mark.asyncio
    async def test_auto_chain_priority_over_task_queue(self) -> None:
        """auto_chain is consumed before task_queue."""
        state = _make_state(
            active_agent="itinerary",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="booking_complete",
            ),
            auto_chain=["flight"],
            task_queue=[{"agent": "hotel", "context": "hotel in Paris"}],
        )
        result = await route_or_classify(state)
        # auto_chain pops first
        assert result["active_agent"] == "flight"
        assert result["auto_chain"] == []
        # task_queue untouched (still in state for next done signal)
        assert "task_queue" not in result or result.get("task_queue") is None

    @pytest.mark.asyncio
    async def test_queue_cleared_on_reset(self) -> None:
        """Cancel/reset clears task_queue."""
        state = _make_state(
            messages=[HumanMessage(content="cancel")],
            active_agent="flight",
            task_queue=[{"agent": "hotel", "context": "hotel"}],
        )
        result = await route_or_classify(state)
        assert result["task_queue"] == []
        assert result["active_agent"] is None

    @pytest.mark.asyncio
    async def test_queue_survives_detour(self) -> None:
        """Side question (detour return) doesn't clear task_queue."""
        state = _make_state(
            active_agent="general",
            previous_agent="flight",
            detour_return=True,
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="query_answered",
            ),
            task_queue=[{"agent": "hotel", "context": "hotel in Tokyo"}],
        )
        result = await route_or_classify(state)
        # Returns to flight (detour return), task_queue not cleared
        assert result["active_agent"] == "flight"
        assert "task_queue" not in result  # Not modified by detour return

    @pytest.mark.asyncio
    async def test_single_intent_no_queue(self) -> None:
        """Normal single-intent classification → task_queue stays empty."""
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "flight", "queued_intents": [], "reasoning": "single"}'
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(active_agent=None)

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "flight"
        assert "task_queue" not in result  # Empty queue not written

    @pytest.mark.asyncio
    async def test_multi_intent_populates_queue(self) -> None:
        """Multi-intent classification populates task_queue."""
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "flight", "queued_intents": [{"agent": "hotel", "context": "hotel in London"}], "reasoning": "two intents"}'
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(active_agent=None)

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "flight"
        assert len(result["task_queue"]) == 1
        assert result["task_queue"][0]["agent"] == "hotel"

    @pytest.mark.asyncio
    async def test_queue_no_duplicates_on_merge(self) -> None:
        """Existing queue items are not duplicated when new intents arrive.

        #1133 follow-up: the user message must contain an explicit booking
        verb ("book hotels") so the new trip-context strip lets the queued
        hotel intent through to the merge step.
        """
        from langchain_core.messages import HumanMessage

        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "itinerary", "queued_intents": [{"agent": "hotel", "context": "new hotel"}], "reasoning": "merge"}'
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(
            active_agent=None,
            messages=[HumanMessage(content="Plan a trip to Tokyo and book hotels")],
            task_queue=[{"agent": "hotel", "context": "existing hotel"}],
        )

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "itinerary"
        # hotel already in queue — not duplicated
        hotel_entries = [t for t in result["task_queue"] if t["agent"] == "hotel"]
        assert len(hotel_entries) == 1

    @pytest.mark.asyncio
    async def test_itinerary_with_trip_context_strips_queue(self) -> None:
        """#1133 follow-up: the classifier LLM tends to over-queue flight +
        hotel agents on itinerary prompts that *describe* the trip ("flying
        in from US", "staying in Shibuya hotel"). The deterministic strip
        must drop the queue so we don't spawn wasted full-agent runs that
        duplicate the silent side-search."""
        from langchain_core.messages import HumanMessage

        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "itinerary", "queued_intents": '
            '[{"agent": "flight", "context": "flights LAX→HND"}, '
            '{"agent": "hotel", "context": "hotel in Tokyo"}], '
            '"reasoning": "user mentioned flying and hotel"}'
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(
            active_agent=None,
            messages=[
                HumanMessage(
                    content=(
                        "Plan a 7 days trip to Tokyo, flying in from the US, "
                        "staying in Shibuya hotel, with departure 30 days from now"
                    )
                )
            ],
        )

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "itinerary"
        # No queued intents persisted — strip dropped them.
        assert result.get("task_queue", []) == []


# ========================
# TestBookEverythingE2E
# ========================

# Sample response shapes matching what process_flight_messages / process_hotel_messages return
_MOCK_FLIGHT_SEARCH_RESPONSE: dict[str, Any] = {
    "message": "I found 6 flights from London to Paris.",
    "type": "flight_search_results",
    "data": {
        "search_params": {
            "origin": "LHR",
            "destination": "CDG",
            "departure_date": "2026-03-20",
            "return_date": "2026-03-25",
            "journey_type": "RoundTrip",
            "passengers": {"adults": 2, "children": 0, "infants": 0},
            "origin_is_city": True,
            "destination_is_city": True,
            "cabin_class": "Economy",
            "direct_flight": 0,
            "origin_iata": "LHR",
            "destination_iata": "CDG",
        },
        "summary": {
            "total_flights": 6,
            "direct_count": 2,
            "price_range": {"min": 120.0, "max": 450.0, "currency": "USD"},
        },
        "categories": {
            "cheapest": {"label": "Cheapest", "flights": [{"id": "f1"}]},
            "fastest": {"label": "Fastest", "flights": [{"id": "f2"}]},
            "best_value": {"label": "Best Value", "flights": [{"id": "f3"}]},
        },
    },
    "flights": [{"id": "f1"}, {"id": "f2"}, {"id": "f3"}],
    "session_id": "flight-session-123",
    "collected_params": {
        "origin": "LHR",
        "destination": "CDG",
        "departure_date": "2026-03-20",
        "return_date": "2026-03-25",
        "adults": 2,
    },
    "message_id": "msg_flight_001",
}

_MOCK_HOTEL_SEARCH_RESPONSE: dict[str, Any] = {
    "message": "I found 3 hotels in Paris for 5 nights.",
    "type": "hotel_search_results",
    "data": {
        "search_params": {
            "destination_city": "Paris",
            "country": "FR",
            "check_in_date": "2026-03-20",
            "check_out_date": "2026-03-25",
            "rooms": 1,
            "adults": 2,
            "children": 0,
        },
        "summary": {
            "total_hotels": 3,
            "nights": 5,
            "price_range": {"min": 95.0, "max": 320.0, "currency": "USD"},
        },
        "categories": {
            "best_value": {"label": "Best Value", "hotels": [{"id": "h1"}]},
            "cheapest": {"label": "Cheapest", "hotels": [{"id": "h2"}]},
            "highest_rated": {"label": "Highest Rated", "hotels": [{"id": "h3"}]},
        },
    },
    "hotels": [{"id": "h1"}, {"id": "h2"}, {"id": "h3"}],
    "session_id": "hotel-session-456",
    "collected_params": {
        "city": "Paris",
        "country": "FR",
        "checkin": "2026-03-20",
        "checkout": "2026-03-25",
        "adults": 2,
    },
    "message_id": "msg_hotel_001",
}


class TestBookEverythingE2E:
    """End-to-end test for 'book everything' auto-chain flow.

    Validates the complete pipeline:
    1. Itinerary hand_back with booking_plan → sets up auto-chain
    2. Flight agent dispatched with shared_context → returns flight_search_results
    3. Hotel agent dispatched with shared_context → returns hotel_search_results
    4. chain_responses accumulated with both results
    5. Response shapes match what frontend components expect
    """

    @staticmethod
    def _make_mock_inner_agent(
        input_messages: list[Any], new_ai_message: str = "AI response"
    ) -> AsyncMock:
        ai_msg = AIMessage(content=new_ai_message)
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [*input_messages, ai_msg]}
        )
        return mock_agent

    # ------------------------------------------------------------------
    # Step 1: Itinerary done → auto-chain setup
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_planning_complete_sets_auto_chain(self) -> None:
        """When itinerary returns DONE + booking_plan, route_or_classify
        sets active_agent=flight and auto_chain=['hotel']."""
        state = _make_state(
            active_agent="itinerary",
            agent_signal={
                "agent_status": "done",
                "done_reason": "planning_complete",
                "booking_plan": ["flight", "hotel"],
            },
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "flight"
        assert result["auto_chain"] == ["hotel"]
        assert result["previous_agent"] == "itinerary"
        assert result["agent_signal"] is None

    # ------------------------------------------------------------------
    # Step 2: shared_context captured from itinerary top-level fields
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    @patch(
        "app.ai.graph.supervisor_v2._resolve_destination",
        return_value={
            "destination_city": "Paris",
            "destination_country": "France",
        },
    )
    async def test_capture_shared_context_from_itinerary_results(
        self, mock_resolve
    ) -> None:
        """_capture_shared_context extracts trip data from itinerary_results
        response that has individual top-level fields (not cross_agent_data)."""
        response = {
            "type": "itinerary_results",
            "message": "Here's your itinerary!",
            "origin": "London",
            "origin_iata": "LHR",
            "origin_name": "London Heathrow Airport",
            "destination": "Paris",
            "destination_iata": "CDG",
            "destination_name": "Charles de Gaulle Airport",
            "departure_date": "2026-03-20",
            "return_date": "2026-03-25",
            "adults": 2,
            "children": 0,
        }
        updated = await _capture_shared_context("itinerary", response, {})
        assert "trip" in updated
        trip = updated["trip"]
        assert trip["origin"] == "London"
        assert trip["origin_iata"] == "LHR"
        assert trip["destination"] == "Paris"
        assert trip["destination_iata"] == "CDG"
        assert trip["departure_date"] == "2026-03-20"
        assert trip["return_date"] == "2026-03-25"
        assert trip["adults"] == 2
        # Destination resolved to city
        assert trip["destination_city"] == "Paris"

    @pytest.mark.asyncio
    async def test_capture_shared_context_prefers_cross_agent_data(self) -> None:
        """When cross_agent_data is present, it takes priority over
        top-level fields."""
        response = {
            "type": "hand_back",
            "cross_agent_data": {"origin_iata": "STN", "destination_iata": "ORY"},
            "origin_iata": "LHR",  # Should be ignored
        }
        updated = await _capture_shared_context("itinerary", response, {})
        assert updated["trip"]["origin_iata"] == "STN"

    # ------------------------------------------------------------------
    # Step 3: shared_context formatted for flight agent
    # ------------------------------------------------------------------
    def test_format_context_for_flight_agent(self) -> None:
        """_format_context_for_agent produces correct text for flight agent."""
        shared_context = {
            "trip": {
                "origin_iata": "LHR",
                "destination_iata": "CDG",
                "departure_date": "2026-03-20",
                "return_date": "2026-03-25",
                "adults": 2,
            }
        }
        text, _ = _format_context_for_agent(shared_context, "flight")
        assert "LHR" in text
        assert "CDG" in text
        assert "2026-03-20" in text
        assert "2026-03-25" in text
        assert "2" in text

    def test_format_context_for_hotel_agent(self) -> None:
        """_format_context_for_agent produces correct text for hotel agent."""
        shared_context = {
            "trip": {
                "destination": "Paris",
                "departure_date": "2026-03-20",
                "return_date": "2026-03-25",
                "adults": 2,
            }
        }
        text, _ = _format_context_for_agent(shared_context, "hotel")
        assert "Paris" in text
        assert "2026-03-20" in text
        assert "2026-03-25" in text

    # ------------------------------------------------------------------
    # Step 4: _build_agent_messages with shared_context
    # ------------------------------------------------------------------
    def test_build_agent_messages_injects_context_on_agent_switch(self) -> None:
        """When previous_agent is set and shared_context has data,
        _build_agent_messages injects single HumanMessage with context."""
        state = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={
                "trip": {
                    "origin_iata": "LHR",
                    "destination_iata": "CDG",
                    "departure_date": "2026-03-20",
                    "return_date": "2026-03-25",
                    "adults": 2,
                }
            },
        )
        msgs = _build_agent_messages(state, "flight")
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert "LHR" in msgs[0].content
        assert "CDG" in msgs[0].content
        assert "book everything" in msgs[0].content

    def test_build_agent_messages_no_context_sends_recap_with_user_message(
        self,
    ) -> None:
        """When previous_agent is set but shared_context is empty,
        recap + user's message is sent."""
        state = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="flight",
            previous_agent="itinerary",
            shared_context={},
        )
        msgs = _build_agent_messages(state, "flight")
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert "SYSTEM CONTEXT" in msgs[0].content
        assert "book everything" in msgs[0].content

    # ------------------------------------------------------------------
    # Step 5: _after_dispatch continues chain on NEEDS_INPUT
    # ------------------------------------------------------------------
    def test_after_dispatch_continues_chain_on_needs_input(self) -> None:
        """When agent returns NEEDS_INPUT but auto_chain has remaining agents,
        _after_dispatch loops back to route_or_classify."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],
            agent_signal={"agent_status": "needs_input"},
            remaining_steps=6,
        )
        result = _after_dispatch(state)
        assert result == "route_or_classify"

    def test_after_dispatch_ends_on_needs_input_no_chain(self) -> None:
        """When agent returns NEEDS_INPUT and no auto_chain, graph ends."""
        state = _make_state(
            active_agent="flight",
            auto_chain=[],
            agent_signal={"agent_status": "needs_input"},
            remaining_steps=6,
        )
        result = _after_dispatch(state)
        assert result == "__end__"

    # ------------------------------------------------------------------
    # Step 6: route_or_classify pops next from chain on NEEDS_INPUT
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_needs_input_pops_auto_chain(self) -> None:
        """When agent returns NEEDS_INPUT with auto_chain, route_or_classify
        pops next agent and dispatches it."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],
            agent_signal={"agent_status": "needs_input"},
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        assert result["auto_chain"] == []
        assert result["previous_agent"] == "flight"

    # ------------------------------------------------------------------
    # Step 7: Dispatch accumulates chain_responses
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_dispatch_accumulates_chain_responses(self) -> None:
        """During auto-chain, dispatch accumulates responses in chain_responses."""
        state = _make_state(
            active_agent="flight",
            auto_chain=["hotel"],  # auto_chain active → triggers accumulation
            chain_responses=[],
        )
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Found flights!")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value=_MOCK_FLIGHT_SEARCH_RESPONSE,
            ),
        ):
            result = await dispatch_flight(state)
        assert len(result["chain_responses"]) == 1
        assert result["chain_responses"][0]["type"] == "flight_search_results"

    @pytest.mark.asyncio
    async def test_dispatch_appends_to_existing_chain_responses(self) -> None:
        """Second dispatch in chain appends to existing chain_responses."""
        existing_flight_resp = {**_MOCK_FLIGHT_SEARCH_RESPONSE}
        state = _make_state(
            active_agent="hotel",
            auto_chain=[],
            chain_responses=[existing_flight_resp],
            previous_agent="flight",
            shared_context={
                "trip": {"destination": "Paris", "adults": 2},
                "flight": {"origin": "LHR", "destination": "CDG"},
            },
        )
        msgs = state["messages"]
        mock_agent = self._make_mock_inner_agent(msgs, "Found hotels!")
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_agent,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value=_MOCK_HOTEL_SEARCH_RESPONSE,
            ),
        ):
            result = await dispatch_hotel(state)
        assert len(result["chain_responses"]) == 2
        assert result["chain_responses"][0]["type"] == "flight_search_results"
        assert result["chain_responses"][1]["type"] == "hotel_search_results"

    # ------------------------------------------------------------------
    # Step 8: Flight response shape matches frontend expectations
    # ------------------------------------------------------------------
    def test_flight_response_has_required_frontend_fields(self) -> None:
        """Flight search response has the fields FlightResultMessage expects:
        data.search_params, data.summary, data.categories, flights, session_id."""
        resp = _MOCK_FLIGHT_SEARCH_RESPONSE
        assert resp["type"] == "flight_search_results"
        assert "data" in resp
        data = resp["data"]
        assert "search_params" in data
        assert "summary" in data
        assert "categories" in data
        assert "flights" in resp
        assert "session_id" in resp
        # Categories must have the expected keys
        cats = data["categories"]
        assert "cheapest" in cats
        assert "fastest" in cats
        assert "best_value" in cats

    def test_hotel_response_has_required_frontend_fields(self) -> None:
        """Hotel search response has the fields HotelResultMessage expects:
        data.search_params, data.summary, data.categories, hotels, session_id."""
        resp = _MOCK_HOTEL_SEARCH_RESPONSE
        assert resp["type"] == "hotel_search_results"
        assert "data" in resp
        data = resp["data"]
        assert "search_params" in data
        assert "summary" in data
        assert "categories" in data
        assert "hotels" in resp
        assert "session_id" in resp
        cats = data["categories"]
        assert "best_value" in cats
        assert "cheapest" in cats
        assert "highest_rated" in cats

    # ------------------------------------------------------------------
    # Step 9: Full chain — planning_complete → flight → hotel
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_full_book_everything_chain(self) -> None:
        """Integration test: simulates the full 'book everything' flow
        through route_or_classify and dispatch nodes.

        Verifies:
        - Planning complete triggers auto-chain [flight, hotel]
        - Flight dispatches with shared_context
        - NEEDS_INPUT + auto_chain → continues to hotel
        - Hotel dispatches with shared_context
        - Both responses accumulated in chain_responses
        """
        trip_context = {
            "trip": {
                "origin": "London",
                "origin_iata": "LHR",
                "destination": "Paris",
                "destination_iata": "CDG",
                "departure_date": "2026-03-20",
                "return_date": "2026-03-25",
                "adults": 2,
            }
        }

        # --- Phase 1: Itinerary DONE → sets up auto-chain ---
        state_1 = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="itinerary",
            shared_context=trip_context,
            agent_signal={
                "agent_status": "done",
                "done_reason": "planning_complete",
                "booking_plan": ["flight", "hotel"],
            },
        )
        result_1 = await route_or_classify(state_1)
        assert result_1["active_agent"] == "flight"
        assert result_1["auto_chain"] == ["hotel"]

        # --- Phase 2: Flight dispatch → flight_search_results ---
        state_2 = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="flight",
            previous_agent="itinerary",
            auto_chain=["hotel"],
            shared_context=trip_context,
            chain_responses=[],
        )
        msgs_2 = _build_agent_messages(state_2, "flight")
        # Single HumanMessage with context + instruction
        assert len(msgs_2) == 1
        assert isinstance(msgs_2[0], HumanMessage)
        assert "London" in msgs_2[0].content

        mock_flight = self._make_mock_inner_agent(msgs_2, "Found flights!")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_flight,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value=_MOCK_FLIGHT_SEARCH_RESPONSE,
            ),
        ):
            result_2 = await dispatch_flight(state_2)

        assert result_2["agent_response"]["type"] == "flight_search_results"
        assert result_2["agent_signal"]["agent_status"] == "needs_input"
        assert len(result_2["chain_responses"]) == 1

        # _after_dispatch should loop back
        state_2_post = {**state_2, **result_2}
        edge_2 = _after_dispatch(state_2_post)
        assert edge_2 == "route_or_classify"

        # --- Phase 3: route_or_classify pops hotel from chain ---
        state_3 = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="flight",
            auto_chain=["hotel"],
            shared_context={
                **trip_context,
                "flight": result_2.get("shared_context", {}).get("flight", {}),
            },
            agent_signal={"agent_status": "needs_input"},
        )
        result_3 = await route_or_classify(state_3)
        assert result_3["active_agent"] == "hotel"
        assert result_3["auto_chain"] == []
        assert result_3["previous_agent"] == "flight"

        # --- Phase 4: Hotel dispatch → hotel_search_results ---
        state_4 = _make_state(
            messages=[HumanMessage(content="book everything")],
            active_agent="hotel",
            previous_agent="flight",
            auto_chain=[],
            shared_context={**trip_context, "flight": {"origin": "LHR"}},
            chain_responses=[_MOCK_FLIGHT_SEARCH_RESPONSE],
        )
        msgs_4 = _build_agent_messages(state_4, "hotel")
        # Single HumanMessage with context + instruction
        assert len(msgs_4) == 1
        assert isinstance(msgs_4[0], HumanMessage)
        assert "Paris" in msgs_4[0].content

        mock_hotel = self._make_mock_inner_agent(msgs_4, "Found hotels!")
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_hotel,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value=_MOCK_HOTEL_SEARCH_RESPONSE,
            ),
        ):
            result_4 = await dispatch_hotel(state_4)

        assert result_4["agent_response"]["type"] == "hotel_search_results"
        assert len(result_4["chain_responses"]) == 2

        # --- Phase 5: Validate both chain responses have frontend-compatible shapes ---
        flight_resp = result_4["chain_responses"][0]
        hotel_resp = result_4["chain_responses"][1]

        # Flight: must have data.search_params, data.summary, data.categories
        assert flight_resp["type"] == "flight_search_results"
        assert "data" in flight_resp
        assert "search_params" in flight_resp["data"]
        assert "summary" in flight_resp["data"]
        assert "categories" in flight_resp["data"]
        assert "flights" in flight_resp
        assert "session_id" in flight_resp

        # Hotel: must have data.search_params, data.summary, data.categories
        assert hotel_resp["type"] == "hotel_search_results"
        assert "data" in hotel_resp
        assert "search_params" in hotel_resp["data"]
        assert "summary" in hotel_resp["data"]
        assert "categories" in hotel_resp["data"]
        assert "hotels" in hotel_resp
        assert "session_id" in hotel_resp

        # _after_dispatch should END (no more chain)
        state_4_post = {**state_4, **result_4}
        edge_4 = _after_dispatch(state_4_post)
        assert edge_4 == "__end__"


# ========================
# TestChainResponsesClearing
# ========================


class TestChainResponsesClearing:
    """Tests that chain_responses is cleared after chain completion.

    Verifies that stale chain_responses from a completed auto-chain
    do not persist into subsequent non-chain user messages.
    """

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_chain_responses_cleared_on_done_no_pending(
        self, mock_prompt: MagicMock, mock_llm: MagicMock
    ) -> None:
        """When agent signals DONE with no auto_chain/task_queue pending,
        chain_responses should be cleared."""
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "follow-up"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            active_agent="hotel",
            agent_signal={"agent_status": "done", "done_reason": "query_answered"},
            chain_responses=[
                {"type": "flight_search_results", "message": "Found flights"},
                {"type": "hotel_search_results", "message": "Found hotels"},
            ],
        )
        result = await route_or_classify(state)
        assert result.get("chain_responses") == []

    @pytest.mark.asyncio
    async def test_chain_responses_cleared_on_reset(self) -> None:
        """Reset keywords should clear chain_responses along with other state."""
        state = _make_state(
            messages=[HumanMessage(content="cancel")],
            active_agent="flight",
            chain_responses=[
                {"type": "flight_search_results", "message": "Found flights"},
            ],
        )
        result = await route_or_classify(state)
        assert result.get("chain_responses") == []
        assert result.get("auto_chain") == []
        assert result.get("task_queue") == []

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._get_sv2_llm")
    @patch("app.ai.graph.supervisor_v2._get_formatted_prompt")
    async def test_chain_responses_cleared_on_agent_failure(
        self, mock_prompt: MagicMock, mock_llm: MagicMock
    ) -> None:
        """When agent fails with no chain pending, chain_responses should be cleared."""
        mock_prompt.return_value = "You are a router."
        mock_response = MagicMock()
        mock_response.content = '{"target_agent": "general", "reasoning": "recovery"}'
        mock_llm.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_response))

        state = _make_state(
            active_agent="flight",
            agent_signal={"agent_status": "failed", "failed_reason": "timeout"},
            chain_responses=[
                {"type": "flight_search_results", "message": "Partial results"},
            ],
        )
        result = await route_or_classify(state)
        assert result.get("chain_responses") == []

    @pytest.mark.asyncio
    async def test_chain_responses_not_cleared_mid_chain(self) -> None:
        """chain_responses should NOT be cleared when auto_chain still has agents."""
        state = _make_state(
            active_agent="flight",
            agent_signal={"agent_status": "done", "done_reason": "query_answered"},
            auto_chain=["hotel"],
            chain_responses=[
                {"type": "flight_search_results", "message": "Found flights"},
            ],
        )
        result = await route_or_classify(state)
        assert result["active_agent"] == "hotel"
        # chain_responses not in result means it persists from checkpoint (not cleared)
        assert "chain_responses" not in result


# ========================
# TestDetourLoopBreak
# ========================


class TestDetourLoopBreak:
    """Tests for the detour hand_back loop-break mechanism.

    Verifies that:
    - First hand_back increments count and re-classifies
    - Second hand_back from same agent force-routes to general
    - hand_back_count resets on successful DONE signal
    - Hand_back reason is injected into classification prompt
    """

    @pytest.mark.asyncio
    async def test_first_hand_back_increments_count(self):
        """First hand_back should increment count and allow re-classification."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User asking about baggage",
                is_detour=True,
            ),
            hand_back_count=0,
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm") as mock_llm_fn,
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = MagicMock(
                content='{"target_agent": "general", "reasoning": "knowledge question"}'
            )
            mock_llm_fn.return_value = mock_llm
            result = await route_or_classify(state)

        assert result["hand_back_count"] == 1
        assert result["active_agent"] == "general"

    @pytest.mark.asyncio
    async def test_second_hand_back_force_routes_to_general(self):
        """Second hand_back from same agent should force-route to general."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User asking about baggage",
                is_detour=True,
            ),
            hand_back_count=1,  # Already handed back once
        )
        # No LLM mock needed — should force-route without calling LLM
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["hand_back_count"] == 0
        assert result["previous_agent"] == "flight"
        assert result["detour_return"] is True

    @pytest.mark.asyncio
    async def test_force_route_works_for_any_agent(self):
        """Force-route to general works for hotel agent too."""
        state = _make_state(
            active_agent="hotel",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User asking about visa requirements",
                is_detour=True,
            ),
            hand_back_count=1,
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["previous_agent"] == "hotel"

    @pytest.mark.asyncio
    async def test_done_signal_resets_hand_back_count(self):
        """DONE signal should reset hand_back_count to 0."""
        state = _make_state(
            active_agent="general",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="query_answered",
            ),
            hand_back_count=2,
            detour_return=True,
            previous_agent="flight",
        )
        result = await route_or_classify(state)

        # Should return to flight (detour complete)
        assert result["active_agent"] == "flight"
        assert result.get("hand_back_count", 0) == 0

    @pytest.mark.asyncio
    async def test_hand_back_reason_injected_into_classification(self):
        """Hand_back reason should appear in the LLM classification prompt."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User is asking about baggage allowance",
                is_detour=True,
            ),
            hand_back_count=0,
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm") as mock_llm_fn,
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = MagicMock(
                content='{"target_agent": "general", "reasoning": "knowledge question"}'
            )
            mock_llm_fn.return_value = mock_llm
            await route_or_classify(state)

        # Check that the classification prompt includes the hand_back hint
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "flight" in call_args
        assert "baggage allowance" in call_args
        assert "DIFFERENT agent" in call_args

    @pytest.mark.asyncio
    async def test_non_detour_hand_back_also_breaks_loop(self):
        """Non-detour hand_back (is_detour=False) should also trigger force-route."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User wants hotel instead",
                is_detour=False,
            ),
            hand_back_count=1,
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["detour_return"] is False

    @pytest.mark.asyncio
    async def test_detour_return_preserved_when_intermediary_hands_back(self):
        """When general agent hands back during a detour, detour_return stays True."""
        state = _make_state(
            active_agent="general",
            previous_agent="flight",  # Original agent we need to return to
            detour_return=True,  # Set by original flight hand_back
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User is asking about baggage",
                is_detour=False,  # General says is_detour=False
            ),
            hand_back_count=1,
        )
        result = await route_or_classify(state)

        # detour_return should be preserved (not overwritten by general's is_detour=False)
        assert result["detour_return"] is True
        # previous_agent should still be flight (not general)
        assert result["previous_agent"] == "flight"

    @pytest.mark.asyncio
    async def test_detour_return_triggers_return_to_original_agent(self):
        """After detour agent completes (DONE), control returns to the original agent."""
        state = _make_state(
            active_agent="general",
            previous_agent="flight",  # Original agent
            detour_return=True,
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="query_answered",
            ),
            hand_back_count=0,
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "flight"
        assert result["previous_agent"] is None  # Cleared for Mode 2 (continuation)
        assert result["detour_return"] is False

    @pytest.mark.asyncio
    async def test_previous_agent_preserved_during_force_route_in_detour(self):
        """Force-route to general during detour preserves original previous_agent."""
        state = _make_state(
            active_agent="general",
            previous_agent="hotel",  # Original agent we need to return to
            detour_return=True,
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="Cannot answer",
                is_detour=False,
            ),
            hand_back_count=1,  # Will trigger force-route
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["previous_agent"] == "hotel"  # Preserved, not "general"
        assert result["detour_return"] is True


# ========================
# TestMultiTurnHandoffIntegration
# ========================


class TestMultiTurnHandoffIntegration:
    """End-to-end integration tests simulating multi-turn conversations.

    Each test walks through the full supervisor cycle:
    route_or_classify → _build_agent_messages → dispatch_* → _after_dispatch
    across multiple turns, verifying state transitions, message construction,
    shared_context propagation, and detour/return flows.

    These tests mock inner agents and LLM classification but exercise ALL
    supervisor logic (routing, signal handling, context capture/injection,
    message slicing, detour_origin_index save/restore).
    """

    @staticmethod
    def _mock_agent_response(
        input_messages: list[Any], new_content: str = "Agent response"
    ) -> AsyncMock:
        """Create a mock inner agent that returns input messages + new AI message."""
        ai_msg = AIMessage(content=new_content)
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value={"messages": [*input_messages, ai_msg]})
        return mock

    @staticmethod
    def _apply_update(state: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Apply a route_or_classify or dispatch update to state.

        Simulates LangGraph's state merging: messages use add_messages reducer
        (append), other keys are replaced.
        """
        new_state = dict(state)
        for key, value in update.items():
            if key == "messages" and isinstance(value, list):
                # add_messages reducer: append new messages
                new_state["messages"] = list(new_state.get("messages", [])) + value
            else:
                new_state[key] = value
        return new_state

    # ------------------------------------------------------------------
    # Scenario 1: Flight → search results → switch to hotel
    # User books flight, gets results, then says "now hotels"
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_flight_search_then_switch_to_hotel(self):
        """After flight returns search results (signal:done), user says 'now hotels'.

        Verifies:
        1. Flight agent dispatched, returns flight_search_results with signal:done
        2. _after_dispatch returns END (no pending work)
        3. Next turn: active_agent=None (cleared by done), LLM classifies → hotel
        4. Hotel agent receives shared_context from flight's collected_params
        5. Hotel agent's _build_agent_messages uses Mode 1 (agent switch)
        """
        # --- Turn 1: User sends flight request, classified to flight ---
        state = _make_state(
            messages=[HumanMessage(content="Book a flight to Tokyo from Amsterdam")],
            active_agent="flight",
            previous_agent=None,
            agent_start_index=0,
        )

        # Flight agent returns search results
        msgs = _build_agent_messages(state, "flight")
        mock_flight = self._mock_agent_response(msgs, "Found 6 flights to Tokyo!")
        flight_response = {
            **_MOCK_FLIGHT_SEARCH_RESPONSE,
            "signal": "done",
            "collected_params": {
                "origin": "AMS",
                "destination": "NRT",
                "destination_city": "Tokyo",
                "departure_date": "2026-04-01",
                "adults": 2,
            },
        }
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_flight,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value=flight_response,
            ),
        ):
            dispatch_result = await dispatch_flight(state)

        # Signal is DONE (search results complete)
        assert dispatch_result["agent_signal"]["agent_status"] == "done"
        # shared_context captured from flight's collected_params
        assert dispatch_result["shared_context"]["flight"]["origin"] == "AMS"
        assert dispatch_result["shared_context"]["flight"]["destination"] == "NRT"

        # _after_dispatch: no chain/queue → END
        state_post = self._apply_update(state, dispatch_result)
        assert _after_dispatch(state_post) == "__end__"

        # --- Turn 2: "now hotels" — route_or_classify handles DONE + classifies in one call ---
        # In the real graph, Turn 2 starts with active_agent=flight + signal=done still in state.
        # route_or_classify processes DONE (clears active_agent, sets previous_agent=flight)
        # then falls through to the LLM slow path to classify "now hotels".
        state_post["messages"].append(HumanMessage(content="now hotels"))
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "hotel", "reasoning": "User wants hotels"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="You are a router.",
            ),
        ):
            classify_result = await route_or_classify(state_post)

        # DONE handler ran (previous_agent=flight) + LLM classified → hotel
        assert classify_result["previous_agent"] == "flight"
        assert classify_result["active_agent"] == "hotel"

        # Hotel _build_agent_messages: Mode 1 (agent switch), flight context injected
        state_hotel = self._apply_update(state_post, classify_result)
        hotel_msgs = _build_agent_messages(state_hotel, "hotel")
        # Mode 1: single HumanMessage with context + instruction
        assert len(hotel_msgs) == 1
        assert isinstance(hotel_msgs[0], HumanMessage)
        assert "Tokyo" in hotel_msgs[0].content or "AMS" in hotel_msgs[0].content
        assert "now hotels" in hotel_msgs[0].content

    # ------------------------------------------------------------------
    # Scenario 2: Itinerary → hotel → flight (cross-agent context chains)
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_itinerary_to_hotel_to_flight_context_chain(self):
        """After itinerary produces results, user switches to hotel, then flight.

        Verifies:
        1. Itinerary returns done with signal:done → clears active_agent
        2. Hotel receives trip context from itinerary
        3. After hotel results, flight receives context from both trip AND hotel
        """
        trip_context = {
            "trip": {
                "origin": "Amsterdam",
                "origin_iata": "AMS",
                "destination": "Tokyo",
                "destination_iata": "NRT",
                "departure_date": "2026-04-10",
                "return_date": "2026-04-12",
                "adults": 2,
            }
        }

        # --- After itinerary done, user says "now hotels" ---
        state = _make_state(
            messages=[
                HumanMessage(content="Plan a 2 day trip to Tokyo"),
                AIMessage(content="Here's your itinerary!"),
                HumanMessage(content="now hotels"),
            ],
            active_agent="hotel",
            previous_agent="itinerary",
            shared_context=trip_context,
            agent_start_index=2,
        )

        # Hotel gets Mode 1 messages with trip context
        hotel_msgs = _build_agent_messages(state, "hotel")
        assert len(hotel_msgs) == 1
        assert isinstance(hotel_msgs[0], HumanMessage)
        assert "Tokyo" in hotel_msgs[0].content  # destination from trip
        assert "2026-04-10" in hotel_msgs[0].content  # departure_date as check-in

        # Hotel returns search results with done signal
        mock_hotel = self._mock_agent_response(hotel_msgs, "Found hotels!")
        hotel_response = {
            **_MOCK_HOTEL_SEARCH_RESPONSE,
            "signal": "done",
            "collected_params": {
                "city": "Tokyo",
                "country": "JP",
                "checkin": "2026-04-10",
                "checkout": "2026-04-12",
                "adults": 2,
            },
        }
        with (
            patch(
                "app.ai.graph.hotel_graph.get_hotel_inner_agent",
                return_value=mock_hotel,
            ),
            patch(
                "app.ai.graph.hotel_graph.process_hotel_messages",
                return_value=hotel_response,
            ),
        ):
            hotel_dispatch = await dispatch_hotel(state)

        # shared_context now has trip AND hotel
        updated_ctx = hotel_dispatch["shared_context"]
        assert updated_ctx["trip"]["destination"] == "Tokyo"
        assert updated_ctx["hotel"]["city"] == "Tokyo"

        # --- After hotel done, user says "now flights" ---
        state_post_hotel = self._apply_update(state, hotel_dispatch)
        # Simulate route_or_classify DONE handler setting previous_agent=hotel
        state_post_hotel["previous_agent"] = "hotel"
        state_post_hotel["active_agent"] = "flight"
        state_post_hotel["messages"].append(HumanMessage(content="now flights"))
        state_post_hotel["agent_start_index"] = len(state_post_hotel["messages"]) - 1

        # Flight gets Mode 1 messages with context from trip + hotel
        flight_msgs = _build_agent_messages(state_post_hotel, "flight")
        assert len(flight_msgs) == 1
        assert isinstance(flight_msgs[0], HumanMessage)
        context_text = flight_msgs[0].content
        assert (
            "Amsterdam" in context_text
        )  # origin from trip (city name preferred over IATA)
        assert (
            "Tokyo" in context_text
        )  # destination from trip (city name preferred over IATA)
        assert "2026-04-10" in context_text  # departure from trip

    # ------------------------------------------------------------------
    # Scenario 3: Flight → detour question → return to flight
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_flight_detour_to_general_and_return(self):
        """User is booking flight, asks side question, general answers, returns to flight.

        Verifies:
        1. Flight hands back with is_detour=True
        2. Supervisor saves detour_origin_index
        3. General agent dispatched and answers
        4. _after_dispatch returns END (detour_return NOT in has_pending)
        5. Next turn: route_or_classify restores flight with detour_origin_index
        6. Flight gets Mode 2 messages (continuation from saved index)
        """
        # --- User was talking to flight agent, conversation has 5 messages ---
        flight_msgs = [
            HumanMessage(content="Book a flight to Tokyo from Amsterdam"),
            AIMessage(content="What date would you like to depart?"),
            HumanMessage(content="April 1st"),
            AIMessage(content="How many passengers?"),
            HumanMessage(content="What's the baggage allowance on KLM?"),
        ]
        state = _make_state(
            messages=flight_msgs,
            active_agent="flight",
            previous_agent=None,
            agent_start_index=0,
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User asking about baggage allowance, not flight booking",
                is_detour=True,
            ),
        )

        # --- Step 1: route_or_classify handles hand_back with detour ---
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "general", "reasoning": "Knowledge question"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            roc_result = await route_or_classify(state)

        assert roc_result["active_agent"] == "general"
        assert roc_result["previous_agent"] == "flight"
        assert roc_result["detour_return"] is True
        assert (
            roc_result["detour_origin_index"] == 0
        )  # Saved flight's agent_start_index
        assert roc_result["hand_back_count"] == 1

        # --- Step 2: General agent dispatched and answers ---
        state_general = self._apply_update(state, roc_result)
        general_msgs = _build_agent_messages(state_general, "general")
        mock_general = self._mock_agent_response(
            general_msgs, "KLM allows 23kg checked baggage on economy."
        )
        with (
            patch(
                "app.ai.graph.general_graph.get_general_inner_agent",
                return_value=mock_general,
            ),
            patch(
                "app.ai.graph.general_graph.process_general_messages",
                return_value={
                    "message": "KLM allows 23kg checked baggage on economy.",
                    "type": "ai_response",
                    "signal": "done",
                    "done_reason": "query_answered",
                },
            ),
        ):
            general_result = await dispatch_general(state_general)

        assert general_result["agent_signal"]["agent_status"] == "done"
        # previous_agent preserved during detour (dispatch preserves when detour_return=True)
        assert general_result["previous_agent"] == "flight"

        # --- Step 3: _after_dispatch returns END (not loop back) ---
        state_after_general = self._apply_update(state_general, general_result)
        edge = _after_dispatch(state_after_general)
        assert edge == "__end__"  # Key fix: detour_return NOT in has_pending

        # --- Step 4: Next turn — user says "alright one way" ---
        state_after_general["messages"].append(HumanMessage(content="alright one way"))
        # detour_return=True persists in checkpoint
        roc_return = await route_or_classify(state_after_general)

        # Detour return: flight restored with saved index
        assert roc_return["active_agent"] == "flight"
        assert roc_return["previous_agent"] is None  # Cleared for Mode 2
        assert roc_return["detour_return"] is False
        assert roc_return["agent_start_index"] == 0  # Restored from detour_origin_index

        # --- Step 5: Flight gets Mode 2 messages from saved index ---
        state_flight_return = self._apply_update(state_after_general, roc_return)
        flight_return_msgs = _build_agent_messages(state_flight_return, "flight")
        # Should include the original flight conversation + new "alright one way"
        human_contents = [
            m.content for m in flight_return_msgs if isinstance(m, HumanMessage)
        ]
        assert "alright one way" in human_contents
        # Should NOT re-ask for already-answered questions
        assert any(
            "Book a flight" in m.content
            for m in flight_return_msgs
            if isinstance(m, HumanMessage)
        )

    # ------------------------------------------------------------------
    # Scenario 4: Detour during auto-chain preserves chain
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_detour_during_auto_chain_preserves_chain(self):
        """During itinerary→flight auto-chain, flight detours to general.
        After general answers, flight resumes AND auto_chain is preserved.

        Verifies:
        1. auto_chain=["hotel"] survives the detour round-trip
        2. After flight completes, hotel is dispatched from auto_chain
        """
        state = _make_state(
            messages=[
                HumanMessage(content="book everything"),
                AIMessage(content="Searching flights..."),
                HumanMessage(content="What's the baggage policy?"),
            ],
            active_agent="flight",
            previous_agent="itinerary",
            auto_chain=["hotel"],
            shared_context={"trip": {"origin_iata": "AMS", "destination_iata": "NRT"}},
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="Baggage question",
                is_detour=True,
            ),
            agent_start_index=0,
        )

        # route_or_classify: hand_back → classify → general
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "general", "reasoning": "knowledge question"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            roc_detour = await route_or_classify(state)

        assert roc_detour["active_agent"] == "general"
        assert roc_detour["detour_return"] is True
        # auto_chain is NOT cleared by hand_back
        assert "auto_chain" not in roc_detour  # Not modified = preserved in state

        # General answers → DONE
        state_g = self._apply_update(state, roc_detour)
        state_g["agent_signal"] = AgentSignal(
            agent_status="done", done_reason="query_answered"
        )

        # Detour return → flight
        roc_return = await route_or_classify(state_g)
        assert roc_return["active_agent"] == "flight"
        assert roc_return["detour_return"] is False
        # auto_chain preserved through detour
        assert "auto_chain" not in roc_return  # Not touched

        # Flight completes → check auto_chain pops hotel
        state_flight = self._apply_update(state_g, roc_return)
        state_flight["auto_chain"] = ["hotel"]  # Still in state
        state_flight["agent_signal"] = AgentSignal(
            agent_status="done", done_reason="booking_complete"
        )
        roc_chain = await route_or_classify(state_flight)
        assert roc_chain["active_agent"] == "hotel"
        assert roc_chain["auto_chain"] == []

    # ------------------------------------------------------------------
    # Scenario 5: Flight continuation with shared_context injection
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_continuation_mode2_injects_cross_agent_context(self):
        """Same agent continuation (Mode 2) injects cross-agent context.

        User: plan trip → itinerary sets shared_context
        User: book flights → flight agent
        User: "2 adults" → continuation, flight still needs trip context

        Verifies:
        1. Mode 2 prepends [SYSTEM CONTEXT] HumanMessage with trip data
        2. Agent's conversation segment is preserved (not just latest message)
        """
        state = _make_state(
            messages=[
                HumanMessage(content="Plan a trip to Tokyo"),
                AIMessage(content="Here's your itinerary!"),
                HumanMessage(content="book flights"),
                AIMessage(content="What date would you like to depart?"),
                HumanMessage(content="April 1st"),
            ],
            active_agent="flight",
            previous_agent=None,  # Same agent continuation (not a switch)
            shared_context={
                "trip": {
                    "origin_iata": "AMS",
                    "destination_iata": "NRT",
                    "departure_date": "2026-04-10",
                    "adults": 2,
                }
            },
            agent_start_index=2,  # Flight started at message index 2
        )

        msgs = _build_agent_messages(state, "flight")

        # Mode 2: [SYSTEM CONTEXT] + sliced messages from index 2
        assert isinstance(msgs[0], HumanMessage)
        assert "[SYSTEM CONTEXT]" in msgs[0].content
        assert "AMS" in msgs[0].content
        assert "NRT" in msgs[0].content

        # Agent's conversation (from index 2 onward) follows
        remaining = msgs[1:]
        assert len(remaining) == 3  # "book flights", AI response, "April 1st"
        assert remaining[0].content == "book flights"
        assert remaining[2].content == "April 1st"

    # ------------------------------------------------------------------
    # Scenario 6: Reset clears everything mid-flow
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_reset_clears_all_state_mid_chain(self):
        """User says 'cancel' during auto-chain.

        Verifies: active_agent, auto_chain, task_queue, shared_context all cleared.
        """
        state = _make_state(
            messages=[HumanMessage(content="cancel")],
            active_agent="hotel",
            auto_chain=["flight"],
            task_queue=[{"agent": "itinerary", "context": "plan trip"}],
            shared_context={"trip": {"origin_iata": "AMS"}},
            detour_return=False,
        )
        result = await route_or_classify(state)

        assert result["active_agent"] is None
        assert result["previous_agent"] is None
        assert result["auto_chain"] == []
        assert result["task_queue"] == []
        assert result["shared_context"] == {}
        assert result["current_intent"] == "CANCEL_RESET"

    # ------------------------------------------------------------------
    # Scenario 7: Double detour (flight → general → general force-route)
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_double_hand_back_force_routes_preserves_return(self):
        """Agent hands back, general also hands back → force-route to general.

        Verifies:
        1. First hand_back: flight → general (count=1)
        2. General hands back too (count=2) → force-route to general
        3. previous_agent still points to flight (original agent)
        4. detour_return still True
        """
        # Step 1: Flight hands back with detour
        state = _make_state(
            messages=[HumanMessage(content="Is KLM reliable?")],
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="General knowledge question",
                is_detour=True,
            ),
            hand_back_count=0,
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "general", "reasoning": "knowledge"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            r1 = await route_or_classify(state)

        assert r1["active_agent"] == "general"
        assert r1["hand_back_count"] == 1
        assert r1["detour_return"] is True
        assert r1["previous_agent"] == "flight"

        # Step 2: General also hands back (weird edge case)
        state2 = self._apply_update(state, r1)
        state2["agent_signal"] = AgentSignal(
            agent_status="hand_back",
            reason="I cannot answer this either",
            is_detour=False,
        )
        r2 = await route_or_classify(state2)

        # Force-route to general (count was 1, now hits ≥2)
        assert r2["active_agent"] == "general"
        assert r2["hand_back_count"] == 0  # Reset by force-route
        assert r2["previous_agent"] == "flight"  # Preserved original
        assert r2["detour_return"] is True  # Still detour

    # ------------------------------------------------------------------
    # Scenario 8: Agent switch Mode 1 message format is Gemini-safe
    # ------------------------------------------------------------------
    def test_mode1_messages_are_gemini_compatible(self):
        """Mode 1 (agent switch) must produce messages that satisfy Gemini:
        - All messages are HumanMessage (Gemini-safe, no SystemMessage)
        - With context: [HumanMessage(context + instruction)]
        - Without context: [HumanMessage(user message)]
        """
        # With context
        state_ctx = _make_state(
            messages=[HumanMessage(content="now hotels")],
            active_agent="hotel",
            previous_agent="flight",
            shared_context={"flight": {"destination": "NRT", "adults": 2}},
        )
        msgs_ctx = _build_agent_messages(state_ctx, "hotel")
        assert len(msgs_ctx) == 1
        assert isinstance(msgs_ctx[0], HumanMessage)
        assert "SYSTEM CONTEXT" in msgs_ctx[0].content

        # Without context
        state_no_ctx = _make_state(
            messages=[HumanMessage(content="now hotels")],
            active_agent="hotel",
            previous_agent="flight",
            shared_context={},
        )
        msgs_no_ctx = _build_agent_messages(state_no_ctx, "hotel")
        assert len(msgs_no_ctx) == 1
        assert isinstance(msgs_no_ctx[0], HumanMessage)

    # ------------------------------------------------------------------
    # Scenario 9: Mode 2 continuation skips non-HumanMessage starts
    # ------------------------------------------------------------------
    def test_mode2_skips_to_first_human_message_when_no_context(self):
        """Mode 2 without shared_context: if sliced messages start with
        AIMessage, skip forward to first HumanMessage (Gemini requirement).
        """
        state = _make_state(
            messages=[
                HumanMessage(content="earlier message"),
                AIMessage(content="AI from different agent"),
                AIMessage(content="another AI message"),
                HumanMessage(content="user answer"),
                AIMessage(content="agent follow-up"),
                HumanMessage(content="latest"),
            ],
            active_agent="flight",
            previous_agent=None,  # Same agent
            shared_context={},
            agent_start_index=1,  # Starts at AIMessage
        )
        msgs = _build_agent_messages(state, "flight")
        # Should skip AIMessages and start from first HumanMessage
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "user answer"

    # ------------------------------------------------------------------
    # Scenario 10: Done signal with signal:done from search results
    # ------------------------------------------------------------------
    def test_search_results_signal_done_clears_active_agent(self):
        """When flight/hotel returns signal:done (search results),
        _detect_agent_signal returns DONE and route_or_classify clears
        active_agent so the next message triggers classification.
        """
        # Flight search results with signal:done
        flight_result = {
            "type": "flight_search_results",
            "signal": "done",
            "message": "Found flights!",
        }
        signal = _detect_agent_signal(flight_result)
        assert signal["agent_status"] == "done"

        # Hotel search results with signal:done
        hotel_result = {
            "type": "hotel_search_results",
            "signal": "done",
            "message": "Found hotels!",
        }
        signal_h = _detect_agent_signal(hotel_result)
        assert signal_h["agent_status"] == "done"

        # Itinerary results with signal:done
        itin_result = {
            "type": "itinerary_results",
            "signal": "done",
            "message": "Here's your itinerary!",
        }
        signal_i = _detect_agent_signal(itin_result)
        assert signal_i["agent_status"] == "done"

    # ------------------------------------------------------------------
    # Scenario 11: Full detour round-trip preserves detour_origin_index
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_detour_origin_index_saved_and_restored(self):
        """detour_origin_index saves flight's agent_start_index before detour
        and restores it when returning to flight.

        Verifies the full index lifecycle:
        1. Flight at agent_start_index=3
        2. Detour: saves detour_origin_index=3
        3. General dispatched with new agent_start_index
        4. Return: agent_start_index restored to 3
        """
        state = _make_state(
            messages=[
                HumanMessage(content="Hi"),
                AIMessage(content="Welcome!"),
                HumanMessage(content="Book flight AMS to NRT"),
                AIMessage(content="What date?"),
                HumanMessage(content="What's KLM baggage limit?"),
            ],
            active_agent="flight",
            agent_start_index=2,  # Flight started here
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="Baggage question",
                is_detour=True,
            ),
        )

        # Hand_back saves detour_origin_index
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "general", "reasoning": "knowledge"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            roc_result = await route_or_classify(state)

        assert roc_result["detour_origin_index"] == 2  # Saved from agent_start_index
        assert roc_result["detour_return"] is True

        # General completes → return to flight
        state2 = self._apply_update(state, roc_result)
        state2["agent_signal"] = AgentSignal(
            agent_status="done", done_reason="query_answered"
        )
        state2["messages"].append(AIMessage(content="KLM allows 23kg"))
        state2["messages"].append(HumanMessage(content="ok April 1st"))

        roc_return = await route_or_classify(state2)

        assert roc_return["active_agent"] == "flight"
        assert roc_return["agent_start_index"] == 2  # Restored from detour_origin_index
        assert roc_return["detour_return"] is False

        # Verify Mode 2 slices from the restored index
        state3 = self._apply_update(state2, roc_return)
        msgs = _build_agent_messages(state3, "flight")
        # Messages from index 2 onward: "Book flight AMS to NRT", "What date?",
        # "What's KLM baggage limit?", AI:"KLM allows 23kg", "ok April 1st"
        human_msgs = [m.content for m in msgs if isinstance(m, HumanMessage)]
        # Should include the original flight context AND the new answer
        assert "ok April 1st" in human_msgs

    # ------------------------------------------------------------------
    # Scenario 12: dispatch preserves previous_agent during detour
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_dispatch_preserves_previous_agent_during_detour(self):
        """When detour_return=True, _dispatch_agent preserves previous_agent
        in its return dict so route_or_classify knows where to return.
        """
        state = _make_state(
            active_agent="general",
            previous_agent="flight",
            detour_return=True,
        )
        msgs = state["messages"]
        mock_general = self._mock_agent_response(msgs, "Here's the answer.")
        with (
            patch(
                "app.ai.graph.general_graph.get_general_inner_agent",
                return_value=mock_general,
            ),
            patch(
                "app.ai.graph.general_graph.process_general_messages",
                return_value={
                    "message": "Here's the answer.",
                    "type": "ai_response",
                    "signal": "done",
                    "done_reason": "query_answered",
                },
            ),
        ):
            result = await dispatch_general(state)

        # previous_agent=flight preserved (not cleared to None)
        assert result["previous_agent"] == "flight"

    # ------------------------------------------------------------------
    # Scenario 13: dispatch does NOT preserve previous_agent when no detour
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_dispatch_clears_previous_agent_when_no_detour(self):
        """When detour_return=False, _dispatch_agent clears previous_agent."""
        state = _make_state(
            active_agent="flight",
            previous_agent="itinerary",
            detour_return=False,
        )
        msgs = state["messages"]
        mock_flight = self._mock_agent_response(msgs, "Searching flights...")
        with (
            patch(
                "app.ai.graph.flight_graph.get_flight_inner_agent",
                return_value=mock_flight,
            ),
            patch(
                "app.ai.graph.flight_graph.process_flight_messages",
                return_value={
                    "message": "Searching flights...",
                    "type": "flight_conversation",
                },
            ),
        ):
            result = await dispatch_flight(state)

        assert result["previous_agent"] is None


# ========================
# TestFilterDetourNoise
# ========================


class TestFilterDetourNoise:
    """Tests for _filter_detour_noise — stripping hand_back tool calls
    and surrounding detour messages from agent message history."""

    def test_no_detour_noise_returns_unchanged(self):
        """Messages without hand_back ToolMessages are returned as-is."""
        msgs = [
            HumanMessage(content="Book a flight"),
            AIMessage(content="Where to?"),
            HumanMessage(content="Tokyo"),
        ]
        assert _filter_detour_noise(msgs) == msgs

    def test_removes_full_detour_pattern(self):
        """Removes: detour trigger, tool_call AI, ToolMessage, fallback AI, detour answer AI."""
        msgs = [
            HumanMessage(content="Book a flight to Tokyo"),
            AIMessage(content="One-way or round-trip?"),
            HumanMessage(content="What's the baggage allowance?"),  # detour trigger
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "hand_back_to_supervisor", "args": {}, "id": "tc_hb"}
                ],
            ),
            ToolMessage(
                content='{"status": "hand_back", "reason": "baggage question"}',
                name="hand_back_to_supervisor",
                tool_call_id="tc1",
            ),
            AIMessage(content="I can't answer that directly."),  # agent fallback
            AIMessage(content="KLM allows 23kg on economy."),  # general's answer
            HumanMessage(content="alright one way"),
        ]
        filtered = _filter_detour_noise(msgs)
        contents = [m.content for m in filtered]
        assert "Book a flight to Tokyo" in contents
        assert "One-way or round-trip?" in contents
        assert "alright one way" in contents
        # Detour noise removed
        assert "What's the baggage allowance?" not in contents
        assert "I can't answer that directly." not in contents
        assert "KLM allows 23kg on economy." not in contents
        assert len(filtered) == 3

    def test_preserves_normal_tool_messages(self):
        """ToolMessages that are NOT hand_back are preserved."""
        msgs = [
            HumanMessage(content="Search flights"),
            AIMessage(
                content="",
                tool_calls=[{"name": "search_flights", "args": {}, "id": "tc_sf"}],
            ),
            ToolMessage(
                content='{"flights": [{"id": "f1"}]}',
                tool_call_id="tc2",
            ),
            AIMessage(content="Found 3 flights!"),
        ]
        filtered = _filter_detour_noise(msgs)
        assert len(filtered) == 4  # All preserved

    def test_handles_empty_messages(self):
        assert _filter_detour_noise([]) == []

    def test_handles_multiple_detours(self):
        """Two detour round-trips in the same history are both cleaned."""
        msgs = [
            HumanMessage(content="Book a flight"),
            AIMessage(content="Where to?"),
            # First detour
            HumanMessage(content="What's the weather?"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "hand_back_to_supervisor", "args": {}, "id": "tc_hb"}
                ],
            ),
            ToolMessage(
                content='{"status": "hand_back"}',
                name="hand_back_to_supervisor",
                tool_call_id="tc1",
            ),
            AIMessage(content="Sunny today."),
            # Back to conversation
            HumanMessage(content="Tokyo"),
            AIMessage(content="What date?"),
            # Second detour
            HumanMessage(content="Is KLM good?"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "hand_back_to_supervisor", "args": {}, "id": "tc_hb"}
                ],
            ),
            ToolMessage(
                content='{"status": "hand_back"}',
                name="hand_back_to_supervisor",
                tool_call_id="tc2",
            ),
            AIMessage(content="KLM is great!"),
            # Back again
            HumanMessage(content="April 1st"),
        ]
        filtered = _filter_detour_noise(msgs)
        contents = [m.content for m in filtered]
        assert "Book a flight" in contents
        assert "Where to?" in contents
        assert "Tokyo" in contents
        assert "What date?" in contents
        assert "April 1st" in contents
        # Detour noise removed
        assert "What's the weather?" not in contents
        assert "Sunny today." not in contents
        assert "Is KLM good?" not in contents
        assert "KLM is great!" not in contents

    def test_build_agent_messages_mode2_filters_detour_on_return(self):
        """_build_agent_messages Mode 2 applies detour noise filter,
        so returning agent sees clean conversation + latest user message."""
        msgs = [
            HumanMessage(content="Book a flight to Tokyo"),
            AIMessage(content="One-way or round-trip?"),
            HumanMessage(content="What's KLM baggage limit?"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "hand_back_to_supervisor", "args": {}, "id": "tc_hb"}
                ],
            ),
            ToolMessage(
                content='{"status": "hand_back", "reason": "baggage"}',
                name="hand_back_to_supervisor",
                tool_call_id="tc1",
            ),
            AIMessage(content="I can't answer that."),
            AIMessage(content="KLM allows 23kg."),
            HumanMessage(content="alright one way"),
        ]
        state = _make_state(
            messages=msgs,
            active_agent="flight",
            previous_agent=None,  # Mode 2 (continuation)
            shared_context={},
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        contents = [m.content for m in result]
        assert "Book a flight to Tokyo" in contents
        assert "One-way or round-trip?" in contents
        assert "alright one way" in contents
        # Detour noise stripped
        assert "What's KLM baggage limit?" not in contents
        assert "KLM allows 23kg." not in contents


# ========================
# TestDispatchItineraryGeocoding
# ========================


class TestDispatchItineraryGeocoding:
    """Tests for destination coordinate enrichment in dispatch_itinerary."""

    def _make_geo_result(self, lat: float, lng: float):
        from app.shared.geocoding import GeocodingResult

        return GeocodingResult(
            city="Sydney",
            country="Australia",
            country_code="AU",
            formatted_address="Sydney NSW, Australia",
            lat=lat,
            lng=lng,
            result_types=["locality", "political"],
        )

    @pytest.mark.asyncio
    async def test_geocodes_destination_for_itinerary_results(self) -> None:
        """Coordinates are added to response when type=itinerary_results."""
        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your 5-day Sydney itinerary.",
            "destination": "Sydney",
        }

        geo_result = self._make_geo_result(lat=-33.8688, lng=151.2093)

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(return_value=[geo_result])
            mock_geo_cls.return_value = mock_geo_instance

            result = await dispatch_itinerary(state)

        agent_response = result["agent_response"]
        assert agent_response["destination_location"]["latitude"] == pytest.approx(
            -33.8688
        )
        assert agent_response["destination_location"]["longitude"] == pytest.approx(
            151.2093
        )

    @pytest.mark.asyncio
    async def test_no_coordinates_when_geocoding_returns_empty(self) -> None:
        """No coordinates added when geocoding returns empty list."""
        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your itinerary.",
            "destination": "SomeUnknownPlace",
        }

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(return_value=[])
            mock_geo_cls.return_value = mock_geo_instance

            result = await dispatch_itinerary(state)

        agent_response = result["agent_response"]
        assert "destination_location" not in agent_response

    @pytest.mark.asyncio
    async def test_geocoding_failure_does_not_break_response(self) -> None:
        """Geocoding exception is silently swallowed — response still returned."""
        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your itinerary.",
            "destination": "Paris",
        }

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(
                side_effect=RuntimeError("API unavailable")
            )
            mock_geo_cls.return_value = mock_geo_instance

            result = await dispatch_itinerary(state)

        # Response is returned despite geocoding failure
        assert result["agent_response"]["type"] == "itinerary_results"
        assert "destination_lat" not in result["agent_response"]
        assert "destination_lng" not in result["agent_response"]

    @pytest.mark.asyncio
    async def test_geocodes_origin_and_destination_in_parallel(self) -> None:
        """#1133 follow-up: when both origin and destination are present on
        the itinerary response, BOTH must be geocoded so the FE has
        coordinates for the route line / map fit. Previously only
        destination was geocoded — origin_location was always missing."""
        from app.shared.geocoding import GeocodingResult

        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your 7-day Tokyo itinerary.",
            "origin": "Los Angeles",
            "destination": "Tokyo",
        }

        lax_geo = GeocodingResult(
            city="Los Angeles",
            country="United States",
            country_code="US",
            formatted_address="Los Angeles, CA, USA",
            lat=34.0522,
            lng=-118.2437,
            result_types=["locality", "political"],
        )
        tyo_geo = GeocodingResult(
            city="Tokyo",
            country="Japan",
            country_code="JP",
            formatted_address="Tokyo, Japan",
            lat=35.6762,
            lng=139.6503,
            result_types=["locality", "political"],
        )

        # geocode_city is called twice (once for origin, once for destination).
        geocode_results = {
            "Los Angeles": [lax_geo],
            "Tokyo": [tyo_geo],
        }

        async def fake_geocode(city: str):
            return geocode_results.get(city, [])

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(side_effect=fake_geocode)
            mock_geo_cls.return_value = mock_geo_instance

            result = await dispatch_itinerary(state)

        agent_response = result["agent_response"]
        # Origin coords surfaced.
        assert agent_response["origin_location"]["latitude"] == pytest.approx(34.0522)
        assert agent_response["origin_location"]["longitude"] == pytest.approx(
            -118.2437
        )
        # Destination coords also surfaced (no regression).
        assert agent_response["destination_location"]["latitude"] == pytest.approx(
            35.6762
        )
        assert agent_response["destination_location"]["longitude"] == pytest.approx(
            139.6503
        )
        # Both geocodes actually fired (pin the asyncio.gather contract —
        # if someone collapses the helper to a single call, the
        # await_count check catches it before the FE-side regression
        # bites). ``>= 2`` rather than ``== 2`` because the dispatch path
        # also calls geocode_city in ``_capture_shared_context`` to refine
        # destination → coords; we tolerate that overhead.
        assert mock_geo_instance.geocode_city.await_count >= 2

    @pytest.mark.asyncio
    async def test_destination_only_response_omits_origin_location(self) -> None:
        """When the itinerary response has no origin (e.g. user is already in
        the destination, or origin wasn't collected), the response payload
        should not carry an empty ``origin_location`` — the field is
        OMITTED, not set to None / {} (matches the existing convention for
        destination_location-on-failure)."""
        from app.shared.geocoding import GeocodingResult

        state = _make_state(active_agent="itinerary")
        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your Tokyo day plan.",
            "destination": "Tokyo",
            # origin intentionally absent
        }
        tyo_geo = GeocodingResult(
            city="Tokyo",
            country="Japan",
            country_code="JP",
            formatted_address="Tokyo, Japan",
            lat=35.6762,
            lng=139.6503,
            result_types=["locality", "political"],
        )

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(return_value=[tyo_geo])
            mock_geo_cls.return_value = mock_geo_instance

            result = await dispatch_itinerary(state)

        agent_response = result["agent_response"]
        assert "origin_location" not in agent_response
        assert agent_response["destination_location"]["latitude"] == pytest.approx(
            35.6762
        )

    @pytest.mark.asyncio
    async def test_geocoding_runs_for_non_itinerary_response_type_with_destination(
        self,
    ) -> None:
        """Geocoding IS attempted even for message type when destination is present.

        The supervisor resolves destinations in _capture_shared_context so that
        subsequent agent dispatches have the correct city + nearby coords.
        """
        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        # e.g. agent replied with a plain message, not itinerary_results
        itinerary_response = {
            "type": "message",
            "message": "I need a few more details before planning your trip.",
            "destination": "Tokyo",
        }

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            mock_geo_instance = AsyncMock()
            mock_geo_instance.geocode_city = AsyncMock(return_value=[])
            mock_geo_cls.return_value = mock_geo_instance

            await dispatch_itinerary(state)

        # Geocoding called because _capture_shared_context resolves
        # any itinerary destination for downstream agents.
        mock_geo_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_geocoding_skipped_when_destination_missing(self) -> None:
        """Geocoding is not attempted when destination is absent from response."""
        state = _make_state(active_agent="itinerary")

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})

        itinerary_response = {
            "type": "itinerary_results",
            "message": "Here is your itinerary.",
            # no "destination" key
        }

        with (
            patch(
                "app.ai.graph.itinerary_graph.get_itinerary_inner_agent",
                return_value=mock_inner,
            ),
            patch(
                "app.ai.graph.itinerary_graph.process_itinerary_messages",
                return_value=itinerary_response,
            ),
            patch(
                "app.shared.geocoding.GeocodingService",
            ) as mock_geo_cls,
        ):
            await dispatch_itinerary(state)

        mock_geo_cls.assert_not_called()


# ========================
# TestBuildTaskQueueHint
# ========================


class TestBuildTaskQueueHint:
    """Tests for _build_task_queue_hint -- multi-intent UX acknowledgment."""

    def test_empty_queue_returns_empty_string(self):
        assert _build_task_queue_hint([]) == ""

    def test_single_queued_intent(self):
        queue = [{"agent": "hotel", "context": "London"}]
        hint = _build_task_queue_hint(queue)
        assert "hotels" in hint
        assert "MULTI-INTENT" in hint

    def test_multiple_queued_intents(self):
        queue = [
            {"agent": "hotel", "context": "London"},
            {"agent": "itinerary", "context": "plan"},
        ]
        hint = _build_task_queue_hint(queue)
        assert "hotels" in hint
        assert "trip planning" in hint

    def test_unknown_agent_uses_raw_name(self):
        queue = [{"agent": "unknown_agent"}]
        hint = _build_task_queue_hint(queue)
        assert "unknown_agent" in hint

    def test_instructs_handling_after_finish(self):
        """Hint should tell agent that queued intents will be handled after finish."""
        queue = [{"agent": "hotel"}]
        hint = _build_task_queue_hint(queue)
        assert "handled automatically after you finish" in hint

    def test_includes_task_context_in_hint(self):
        """Hint includes extracted context from queued tasks."""
        queue = [{"agent": "hotel", "context": "hotel in London"}]
        hint = _build_task_queue_hint(queue)
        assert "hotel in London" in hint
        assert "hotels" in hint

    def test_no_context_shows_not_extracted(self):
        """When queued tasks have no context, hint says 'No context extracted'."""
        queue = [{"agent": "hotel"}]
        hint = _build_task_queue_hint(queue)
        assert "No context extracted yet" in hint
        assert "Already extracted" not in hint


# ========================
# TestMaxAgentHistory
# ========================


class TestMaxAgentHistory:
    """Tests for MAX_AGENT_HISTORY cap in _build_agent_messages."""

    def test_caps_messages_in_continuation_mode(self):
        """Mode 2: messages exceeding MAX_AGENT_HISTORY are trimmed to last N."""
        # Create 84 messages (alternating human/AI) — well above MAX_AGENT_HISTORY=40
        messages = []
        for i in range(42):
            messages.append(HumanMessage(content=f"user msg {i}"))
            messages.append(AIMessage(content=f"bot msg {i}"))

        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,  # Mode 2 (continuation)
            shared_context={},
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        # Should be capped to 40 (MAX_AGENT_HISTORY)
        assert len(result) <= 40

    def test_keeps_recent_messages(self):
        """Capped messages should be the most recent ones."""
        messages = []
        for i in range(15):
            messages.append(HumanMessage(content=f"user msg {i}"))

        state = _make_state(
            messages=messages,
            active_agent="flight",
            shared_context={},
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        # Last message should be the most recent
        assert "user msg 14" in result[-1].content

    def test_short_history_not_truncated(self):
        """Messages below MAX_AGENT_HISTORY should not be truncated."""
        messages = [
            HumanMessage(content="Book a flight"),
            AIMessage(content="Where to?"),
            HumanMessage(content="London"),
        ]
        state = _make_state(
            messages=messages,
            active_agent="flight",
            shared_context={},
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        assert len(result) == 3

    def test_context_prepended_after_cap(self):
        """In Mode 2 with context, context msg is prepended AFTER capping."""
        messages = []
        for i in range(15):
            messages.append(HumanMessage(content=f"msg {i}"))

        state = _make_state(
            messages=messages,
            active_agent="hotel",
            shared_context={
                "flight": {
                    "destination": "LHR",
                    "destination_city": "London",
                    "departure_date": "2026-04-01",
                }
            },
            agent_start_index=1,  # Mode 2 with start_idx
        )
        result = _build_agent_messages(state, "hotel")
        # First message should be context, rest should be capped history
        assert isinstance(result[0], HumanMessage)
        assert "SYSTEM CONTEXT" in result[0].content
        # Total = 1 context + max 20 history messages
        assert len(result) <= 21


# ========================
# TestGeminiFirstMessageGuard
# ========================


class TestGeminiFirstMessageGuard:
    """Tests for the Gemini first-message guard (will_prepend_context).

    When MAX_AGENT_HISTORY windowing drops the first HumanMessage, the guard
    must scan forward to find one so Gemini doesn't receive AIMessage at index 0.
    """

    def test_windowing_drops_first_human_guard_fixes(self):
        """21+ messages: windowing drops first HumanMessage, guard trims to next one."""
        # Build 22 messages: HumanMessage + 19 AI/Tool pairs + HumanMessage
        messages = [HumanMessage(content="original question")]
        for i in range(10):
            messages.append(
                AIMessage(
                    content=f"AI response {i}",
                    tool_calls=[{"name": "t", "args": {}, "id": f"tc{i}"}],
                )
            )
            messages.append(ToolMessage(content=f"tool {i}", tool_call_id=f"tc{i}"))
        messages.append(HumanMessage(content="latest question"))
        assert len(messages) == 22

        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,  # Same agent (Mode 2)
            shared_context={},  # No context → guard should run
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        # MAX_AGENT_HISTORY=20 trims first HumanMessage+AIMessage
        # Guard should skip forward to next HumanMessage
        assert isinstance(result[0], HumanMessage)

    def test_guard_skipped_when_context_will_be_prepended(self):
        """When context_text exists and start_idx > 0, guard is skipped
        because the context HumanMessage will be prepended."""
        # Messages starting with AIMessage (simulates agent_start_index slicing)
        messages = [
            HumanMessage(content="earlier"),  # index 0
            AIMessage(
                content="search results",
                tool_calls=[{"name": "t", "args": {}, "id": "tc1"}],
            ),  # index 1
            ToolMessage(content="tool data", tool_call_id="tc1"),  # index 2
            AIMessage(content="Here are results"),  # index 3
            HumanMessage(content="book fastest"),  # index 4
        ]
        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,  # Same agent
            shared_context={
                "trip": {
                    "origin_iata": "LHR",
                    "destination_iata": "CDG",
                    "departure_date": "2026-03-20",
                    "adults": 2,
                }
            },
            agent_start_index=1,  # Starts at AIMessage
        )
        result = _build_agent_messages(state, "flight")
        # Context is prepended as HumanMessage, AIMessage/ToolMessage preserved
        assert isinstance(result[0], HumanMessage)
        assert "SYSTEM CONTEXT" in result[0].content
        # The AIMessage/ToolMessage pairs should NOT be stripped
        assert len(result) == 5  # context + 4 messages from slice

    def test_guard_runs_when_start_idx_zero_no_context(self):
        """When start_idx=0 and no shared_context, guard must run to ensure
        HumanMessage at index 0 after windowing drops the original."""
        # Build 21 messages so MAX_AGENT_HISTORY=20 drops the original HumanMessage
        messages = [HumanMessage(content="original")]
        for i in range(9):
            messages.append(
                AIMessage(
                    content=f"response {i}",
                    tool_calls=[{"name": "t", "args": {}, "id": f"tc{i}"}],
                )
            )
            messages.append(ToolMessage(content=f"tool {i}", tool_call_id=f"tc{i}"))
        messages.append(AIMessage(content="response 9"))
        messages.append(HumanMessage(content="latest"))
        assert len(messages) == 21

        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,
            shared_context={},  # No context → guard must find next HumanMessage
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        # MAX_AGENT_HISTORY=20 drops first msg; guard skips AIMessages → HumanMessage
        assert isinstance(result[0], HumanMessage)

    def test_start_idx_zero_with_context_injects_system_context(self):
        """When start_idx=0 AND context is available, SYSTEM CONTEXT is prepended.

        This is the fix for the 'user picks alternative airport' bug:
        MAX_AGENT_HISTORY=10 windows out the original HumanMessage, leaving the
        list starting with an AIMessage. Without context injection, the guard strips
        everything up to the last HumanMessage, giving the agent 1 message with no
        history. With context injection the agent gets explicit params + full history.
        """
        # 11 messages: original HumanMessage + 9 AI/Tool + new HumanMessage
        messages = [
            HumanMessage(content="fly London to Buffalo tomorrow 2 adults"),
            AIMessage(
                content="resolving...",
                tool_calls=[
                    {"name": "resolve_origin", "args": {}, "id": "tc1"},
                    {"name": "resolve_dest", "args": {}, "id": "tc2"},
                    {"name": "parse_dates", "args": {}, "id": "tc3"},
                ],
            ),
            ToolMessage(content='{"iata":"LHR"}', tool_call_id="tc1"),
            ToolMessage(content='{"iata":"BUF"}', tool_call_id="tc2"),
            ToolMessage(content='{"departure_date":"2026-04-01"}', tool_call_id="tc3"),
            AIMessage(
                content="searching...",
                tool_calls=[
                    {"name": "search_flights", "args": {}, "id": "tc4"},
                ],
            ),
            ToolMessage(content='{"status":"unsupported_airport"}', tool_call_id="tc4"),
            AIMessage(content="Buffalo not supported. Nearby: Rochester (ROC)"),
            HumanMessage(content="go with ROC"),
            AIMessage(content="extra1"),
            HumanMessage(content="extra2"),
        ]
        assert len(messages) == 11

        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,
            shared_context={
                "flight": {
                    "origin": "LHR",
                    "destination": "BUF",
                    "departure_date": "2026-04-01",
                    "adults": 2,
                }
            },
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        # SYSTEM CONTEXT injected as first message
        assert isinstance(result[0], HumanMessage)
        assert "SYSTEM CONTEXT" in result[0].content
        assert "LHR" in result[0].content
        # All 11 messages fit within MAX_AGENT_HISTORY=20 (no windowing)
        assert len(result) == 12  # 1 context + 11 messages

    def test_start_idx_zero_with_context_preserves_tool_messages(self):
        """When context is injected at start_idx=0, the HumanMessage guard does NOT
        strip AIMessage/ToolMessage pairs — the agent sees its full tool history."""
        messages = [
            HumanMessage(content="fly to BUF"),
            AIMessage(
                content="tool call",
                tool_calls=[{"name": "resolve", "args": {}, "id": "tc1"}],
            ),
            ToolMessage(content='{"status":"unsupported_airport"}', tool_call_id="tc1"),
            AIMessage(content="BUF not supported. Try ROC."),
            HumanMessage(content="use ROC"),
        ]
        state = _make_state(
            messages=messages,
            active_agent="flight",
            previous_agent=None,
            shared_context={
                "flight": {"origin": "LHR", "destination": "BUF", "adults": 2}
            },
            agent_start_index=0,
        )
        result = _build_agent_messages(state, "flight")
        assert "SYSTEM CONTEXT" in result[0].content
        # ToolMessage is preserved (not stripped by guard)
        tool_msgs = [m for m in result if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 1


# ========================
# TestBookFastestPreservesStartIndex
# ========================


class TestBookFastestPreservesStartIndex:
    """Tests for agent_start_index preservation when same agent is re-classified
    after DONE signal (the 'book fastest re-search' bug fix)."""

    @pytest.mark.asyncio
    async def test_done_then_reclassify_same_agent_preserves_start_index(self):
        """After flight returns DONE, 'book fastest' re-classifies to flight.
        agent_start_index must be preserved so the agent sees its search results."""
        # Flight agent was active from index 0, returned search results (DONE)
        state = _make_state(
            messages=[
                HumanMessage(content="fly London to Paris"),
                AIMessage(
                    content="searching...",
                    tool_calls=[{"name": "search", "args": {}, "id": "tc1"}],
                ),
                ToolMessage(content="search results", tool_call_id="tc1"),
                AIMessage(content="Found 3 flights!"),
                HumanMessage(content="book fastest"),
            ],
            active_agent="flight",
            agent_signal={"agent_status": "done", "done_reason": None},
            agent_start_index=0,
        )

        # route_or_classify processes DONE (clears active, sets previous_agent=flight)
        # then classifies "book fastest" → flight (same agent)
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "flight", "reasoning": "User wants to book fastest flight"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="You are a router.",
            ),
        ):
            result = await route_or_classify(state)

        # Same agent re-classified: agent_start_index must be preserved (0, not 4)
        assert result["active_agent"] == "flight"
        assert result["previous_agent"] == "flight"
        assert result["agent_start_index"] == 0  # Preserved, not reset to 4

    @pytest.mark.asyncio
    async def test_done_then_classify_different_agent_resets_start_index(self):
        """After flight DONE, 'now hotels' classifies to hotel.
        agent_start_index should be reset to current message count."""
        state = _make_state(
            messages=[
                HumanMessage(content="fly London to Paris"),
                AIMessage(content="Found flights!"),
                HumanMessage(content="now hotels"),
            ],
            active_agent="flight",
            agent_signal={"agent_status": "done", "done_reason": None},
            agent_start_index=0,
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"target_agent": "hotel", "reasoning": "User wants hotels"}'
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="You are a router.",
            ),
        ):
            result = await route_or_classify(state)

        # Different agent: agent_start_index reset to current position
        assert result["active_agent"] == "hotel"
        assert result["agent_start_index"] == 2  # Reset to last msg index


# ========================
# TestAutoChainMessageIsolation
# ========================


class TestAutoChainMessageIsolation:
    """Tests for auto-chain message isolation in _build_agent_messages."""

    def test_auto_chain_does_not_append_last_message_suffix(self):
        """Auto-chain should not append 'The user's last message was' suffix."""
        state = _make_state(
            messages=[
                HumanMessage(content="Find flights and hotel in London"),
                AIMessage(content="Flight results"),
                HumanMessage(content="AMS, 2 adults, March 20-27"),
            ],
            active_agent="hotel",
            previous_agent="flight",
            auto_chain=["hotel"],
            chain_responses=[{"type": "flight_search_results"}],
            shared_context={
                "flight": {
                    "origin": "AMS",
                    "destination": "LHR",
                    "destination_city": "London",
                    "departure_date": "2026-03-20",
                    "return_date": "2026-03-27",
                    "adults": 2,
                }
            },
        )
        result = _build_agent_messages(state, "hotel")
        all_content = " ".join(m.content for m in result)
        # Auto-chain should NOT include the "last message" suffix
        assert "The user's last message was" not in all_content
        # But structured context should be present
        assert "KNOWN CONTEXT" in all_content

    def test_auto_chain_sends_clean_instruction(self):
        """Auto-chain sends a clean instruction, not the user's raw message."""
        state = _make_state(
            messages=[HumanMessage(content="AMS, 2 adults, March 20-27")],
            active_agent="hotel",
            previous_agent="flight",
            chain_responses=[{"type": "flight_search_results"}],
            shared_context={
                "flight": {
                    "destination_city": "London",
                    "departure_date": "2026-03-20",
                }
            },
        )
        result = _build_agent_messages(state, "hotel")
        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert "SYSTEM CONTEXT" in result[0].content
        assert "search immediately" in result[0].content

    def test_non_auto_chain_passes_user_message(self):
        """Normal agent switch (not auto-chain) passes user's message."""
        state = _make_state(
            messages=[HumanMessage(content="now book a hotel in London")],
            active_agent="hotel",
            previous_agent="flight",
            chain_responses=[],  # Not auto-chain
            auto_chain=[],
            shared_context={
                "flight": {
                    "destination_city": "London",
                }
            },
        )
        result = _build_agent_messages(state, "hotel")
        all_content = " ".join(m.content for m in result)
        assert "now book a hotel in London" in all_content


# ========================
# TestClearSupervisorCheckpoint
# ========================


class TestClearSupervisorCheckpoint:
    """Tests for _clear_supervisor_checkpoint."""

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client")
    def test_clears_supervisor_collections(self, mock_client):
        mock_collection = MagicMock()
        mock_collection.delete_many.return_value = MagicMock(deleted_count=1)
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        _clear_supervisor_checkpoint("chat-123")

        # Should clear both checkpoints and writes collections
        assert mock_collection.delete_many.call_count == 2
        mock_collection.delete_many.assert_any_call({"thread_id": "chat-123"})

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client", None)
    def test_skips_when_no_client(self):
        """Should not raise when client is None."""
        _clear_supervisor_checkpoint("chat-123")

    @patch("app.ai.graph.supervisor_v2._sv2_mongo_client")
    def test_handles_db_error_gracefully(self, mock_client):
        mock_collection = MagicMock()
        mock_collection.delete_many.side_effect = Exception("DB error")
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        # Should not raise
        _clear_supervisor_checkpoint("chat-123")


# ========================
# TestCheckpointVersionGuard
# ========================


class TestCheckpointVersionGuard:
    """Tests for checkpoint version guard in invoke_supervisor_v2."""

    def test_sv2_checkpoint_version_is_positive_int(self):
        """Version constant should be a positive integer."""
        assert isinstance(SV2_CHECKPOINT_VERSION, int)
        assert SV2_CHECKPOINT_VERSION >= 1

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_clears_on_version_mismatch(
        self, mock_graph, mock_checkpointer, mock_clear_agent, mock_clear_sv
    ):
        """When stored version differs from code version, checkpoints are cleared."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        # Simulate existing checkpoint with old version
        mock_cp = MagicMock()
        mock_cp.get.return_value = {
            "channel_values": {"checkpoint_version": 0},  # Old version
        }
        mock_checkpointer.return_value = mock_cp

        # Mock graph to avoid actual LLM call
        mock_result = {
            "messages": [AIMessage(content="Hello")],
            "agent_response": {"message": "Hello", "type": "message"},
            "active_agent": "general",
            "chain_responses": [],
        }
        mock_graph_instance = MagicMock()
        mock_graph_instance.ainvoke = AsyncMock(return_value=mock_result)
        mock_graph.return_value = mock_graph_instance

        await invoke_supervisor_v2("hi", "user1", "chat1")

        # Both clear functions should have been called
        mock_clear_agent.assert_called_once_with("chat1")
        mock_clear_sv.assert_called_once_with("chat1")

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_no_clear_when_version_matches(
        self, mock_graph, mock_checkpointer, mock_clear_agent, mock_clear_sv
    ):
        """When stored version matches code version, checkpoints are NOT cleared."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        mock_cp = MagicMock()
        mock_cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_checkpointer.return_value = mock_cp

        mock_result = {
            "messages": [AIMessage(content="Hello")],
            "agent_response": {"message": "Hello", "type": "message"},
            "active_agent": "general",
            "chain_responses": [],
        }
        mock_graph_instance = MagicMock()
        mock_graph_instance.ainvoke = AsyncMock(return_value=mock_result)
        mock_graph.return_value = mock_graph_instance

        await invoke_supervisor_v2("hi", "user1", "chat1")

        # Neither clear function should have been called
        mock_clear_sv.assert_not_called()


# ========================
# TestCheckpointTTL
# ========================


class TestCheckpointTTL:
    """Tests for checkpoint TTL constant."""

    def test_ttl_is_30_days(self):
        """Multi-conversation chat: checkpoints live long enough for users to
        return to older conversations with agent memory intact."""
        from app.ai.graph.base import CHECKPOINT_TTL_SECONDS

        assert CHECKPOINT_TTL_SECONDS == 30 * 24 * 60 * 60  # 2_592_000


# ========================
# TestPromptManagementSDKCache
# ========================


class TestPromptManagementSDKCache:
    """Tests for Langfuse SDK cache_ttl_seconds usage."""

    def setup_method(self):
        import app.ai.prompt_management as pm

        pm._langfuse_available = None

    @patch("app.ai.prompt_management.settings")
    @patch("langfuse.get_client")
    def test_sdk_cache_ttl_passed_to_get_prompt(self, mock_get_client, mock_settings):
        """Verify cache_ttl_seconds is passed to Langfuse SDK get_prompt."""
        mock_settings.LANGFUSE_ENABLED = True
        mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
        mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
        mock_settings.LANGFUSE_PROMPT_LABEL = "production"

        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Test prompt"
        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt
        mock_get_client.return_value = mock_client

        from app.ai.prompt_management import get_flight_prompt

        get_flight_prompt()

        # Verify cache_ttl_seconds=300 was passed
        call_kwargs = mock_client.get_prompt.call_args
        assert call_kwargs.kwargs.get("cache_ttl_seconds") == 300

    @patch("app.ai.prompt_management.settings")
    @patch("langfuse.get_client")
    def test_no_app_level_cache(self, mock_get_client, mock_settings):
        """Verify app-level cache is removed — each call hits SDK (which caches internally)."""
        mock_settings.LANGFUSE_ENABLED = True
        mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
        mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
        mock_settings.LANGFUSE_PROMPT_LABEL = "production"

        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Test prompt"
        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt
        mock_get_client.return_value = mock_client

        from app.ai.prompt_management import get_flight_prompt

        get_flight_prompt()
        get_flight_prompt()

        # SDK get_prompt should be called TWICE (no app-level cache)
        assert mock_client.get_prompt.call_count == 2


# ========================
# TestParseClassificationConfidence
# ========================


class TestParseClassificationConfidence:
    """Tests for confidence field in _parse_classification_response."""

    def test_parse_confidence_high(self):
        text = '{"target_agent": "flight", "confidence": "high", "reasoning": "clear"}'
        result = _parse_classification_response(text)
        assert result["confidence"] == "high"

    def test_parse_confidence_low(self):
        text = (
            '{"target_agent": "general", "confidence": "low", "reasoning": "unclear"}'
        )
        result = _parse_classification_response(text)
        assert result["confidence"] == "low"

    def test_parse_confidence_defaults_to_high(self):
        """When confidence field is missing, default to 'high'."""
        text = '{"target_agent": "flight", "reasoning": "Flight request"}'
        result = _parse_classification_response(text)
        assert result["confidence"] == "high"


# ========================
# TestLowConfidenceRouting
# ========================


class TestLowConfidenceRouting:
    """Tests for low-confidence classification forcing to general."""

    @pytest.mark.asyncio
    async def test_low_confidence_forces_to_general(self):
        """LLM says target=flight, confidence=low → forced to general."""
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "flight", "confidence": "low", "reasoning": "unclear"}'
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(active_agent=None)

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["classification_confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_low_confidence_general_stays_general(self):
        """LLM says target=general, confidence=low → stays general (no double-override)."""
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "general", "confidence": "low", "reasoning": "gibberish"}'
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(active_agent=None)

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        assert result["classification_confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_high_confidence_routes_normally(self):
        """confidence=high doesn't interfere with routing."""
        mock_response = MagicMock()
        mock_response.content = (
            '{"target_agent": "flight", "confidence": "high", "reasoning": "flight"}'
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        state = _make_state(active_agent=None)

        with patch("app.ai.graph.supervisor_v2._get_sv2_llm", return_value=mock_llm):
            result = await route_or_classify(state)

        assert result["active_agent"] == "flight"
        assert result["classification_confidence"] == 0.9


# ========================
# TestForceRouteGeneralPreservesStartIndex
# ========================


class TestForceRouteGeneralPreservesStartIndex:
    """Test that force-routing general back to itself preserves agent_start_index."""

    @pytest.mark.asyncio
    async def test_force_route_general_preserves_agent_start_index(self):
        """When general hands back twice and is force-routed to itself,
        agent_start_index stays at the original value so the user's
        HumanMessage isn't sliced out."""
        state = _make_state(
            messages=[
                HumanMessage(content="Bk of kigali"),
                AIMessage(content="What can I help with?"),
            ],
            active_agent="general",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="Unclear input",
                is_detour=False,
            ),
            hand_back_count=1,  # Second hand-back → force route
            agent_start_index=0,  # Original index with user message
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        # Must preserve original start index, not bump forward
        assert result["agent_start_index"] == 0

    @pytest.mark.asyncio
    async def test_force_route_non_general_uses_agent_start(self):
        """Non-general force-route uses standard agent_start (msg_count - 1)."""
        state = _make_state(
            messages=[
                HumanMessage(content="hello"),
                AIMessage(content="hi"),
                HumanMessage(content="baggage question"),
            ],
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="Knowledge question",
                is_detour=True,
            ),
            hand_back_count=1,
        )
        result = await route_or_classify(state)

        assert result["active_agent"] == "general"
        # Non-general: uses max(msg_count - 1, 0) as new start index
        assert result["agent_start_index"] == 2


# ========================
# TestHandBackHintContextAware
# ========================


class TestHandBackHintContextAware:
    """Tests for context-aware hand-back hints in classification."""

    @pytest.mark.asyncio
    async def test_general_hand_back_hint_allows_reroute_to_general(self):
        """When general agent hands back, hint allows routing back to general."""
        state = _make_state(
            active_agent="general",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User wants flights",
                is_detour=False,
            ),
            hand_back_count=0,
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm") as mock_llm_fn,
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = MagicMock(
                content='{"target_agent": "flight", "confidence": "high", "reasoning": "wants flights"}'
            )
            mock_llm_fn.return_value = mock_llm
            await route_or_classify(state)

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "MAY route back to general" in call_args

    @pytest.mark.asyncio
    async def test_non_general_hand_back_hint_routes_different(self):
        """When non-general agent hands back, hint says route to DIFFERENT agent."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="hand_back",
                reason="User asking about weather",
                is_detour=True,
            ),
            hand_back_count=0,
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm") as mock_llm_fn,
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = MagicMock(
                content='{"target_agent": "general", "reasoning": "weather question"}'
            )
            mock_llm_fn.return_value = mock_llm
            await route_or_classify(state)

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "DIFFERENT agent" in call_args


# ========================
# TestBuildConversationRecap
# ========================


class TestBuildConversationRecap:
    """Tests for _build_conversation_recap helper."""

    def test_builds_recap_from_recent_turns(self):
        messages = [
            HumanMessage(content="I want to go to Dubai"),
            AIMessage(content="Dubai is amazing!"),
            HumanMessage(content="round trip"),
        ]
        recap = _build_conversation_recap(messages, max_turns=3)
        assert "User: I want to go to Dubai" in recap
        assert "Assistant: Dubai is amazing!" in recap
        assert "User: round trip" in recap
        assert "Recent conversation:" in recap

    def test_limits_to_max_turns(self):
        messages = [
            HumanMessage(content="msg1"),
            AIMessage(content="reply1"),
            HumanMessage(content="msg2"),
            AIMessage(content="reply2"),
            HumanMessage(content="msg3"),
            AIMessage(content="reply3"),
        ]
        recap = _build_conversation_recap(messages, max_turns=1)
        # max_turns=1 means 1 turn = 2 messages (user + AI)
        assert "msg3" in recap
        assert "reply3" in recap
        # Earlier messages should be excluded
        assert "msg1" not in recap

    def test_empty_messages_returns_empty(self):
        assert _build_conversation_recap([]) == ""

    def test_skips_tool_messages(self):
        messages = [
            HumanMessage(content="hello"),
            AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "resolve", "args": {}}],
            ),
            ToolMessage(content='{"result": "ok"}', tool_call_id="tc1"),
            AIMessage(content="Here are your results"),
        ]
        recap = _build_conversation_recap(messages)
        assert "User: hello" in recap
        assert "Here are your results" in recap
        # ToolMessage content should not appear in recap
        assert '{"result"' not in recap

    def test_truncates_long_ai_messages(self):
        long_msg = "x" * 500
        messages = [AIMessage(content=long_msg)]
        recap = _build_conversation_recap(messages)
        # AI messages are truncated to 200 chars
        assert len(recap) < 300


# ========================
# TestFormatContextGeneralFallback
# ========================


class TestFormatContextGeneralFallback:
    """Tests for general agent context used as fallback in _format_context_for_agent."""

    def test_general_destination_used_as_fallback(self):
        """general.destination used when trip/flight/hotel have no destination."""
        ctx = {"general": {"destination": "Dubai"}}
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Dubai" in result

    def test_general_dates_appended_when_no_departure(self):
        """Free-text dates from general appended when no parsed departure."""
        ctx = {"general": {"destination": "Tokyo", "dates": "next weekend"}}
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Travel dates (from conversation): next weekend" in result

    def test_general_travelers_appended_when_no_adults(self):
        """Travelers from general used as fallback when no adults count."""
        ctx = {"general": {"destination": "Paris", "travelers": "2 adults"}}
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Travelers (from conversation): 2 adults" in result

    def test_general_interests_always_appended(self):
        """Interests from general are always included."""
        ctx = {
            "general": {"destination": "Bali", "interests": "beaches, food"},
            "trip": {"adults": 2},
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Interests: beaches, food" in result

    def test_general_dates_not_appended_when_departure_exists(self):
        """When parsed departure exists, general.dates is NOT appended."""
        ctx = {
            "general": {"dates": "next weekend"},
            "trip": {"departure_date": "2026-05-01", "destination": "London"},
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Travel dates (from conversation)" not in result

    def test_general_travelers_not_appended_when_adults_exists(self):
        """When adults is already set, general.travelers is NOT appended."""
        ctx = {
            "general": {"travelers": "2 adults"},
            "trip": {"adults": 2, "destination": "London"},
        }
        result, _ = _format_context_for_agent(ctx, "flight")
        assert "Travelers (from conversation)" not in result


# ========================
# TestBuildAgentMessagesNewFeatures
# ========================


class TestBuildAgentMessagesNewFeatures:
    """Tests for new features in _build_agent_messages (recap, pending_task_context)."""

    def test_mode1_includes_conversation_recap(self):
        """Agent switch includes recap of prior conversation."""
        state = _make_state(
            messages=[
                HumanMessage(content="I want to go to Dubai"),
                AIMessage(content="Dubai is amazing!"),
                HumanMessage(content="book flights"),
            ],
            active_agent="flight",
            previous_agent="general",
            shared_context={},
        )
        msgs = _build_agent_messages(state, "flight")
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert "Dubai" in msgs[0].content

    def test_mode1_includes_pending_task_context(self):
        """Task queue context passed to agent on switch."""
        state = _make_state(
            messages=[HumanMessage(content="book flights and hotels")],
            active_agent="hotel",
            previous_agent="flight",
            shared_context={"flight": {"destination": "London"}},
            pending_task_context="hotel in London",
        )
        msgs = _build_agent_messages(state, "hotel")
        assert len(msgs) == 1
        content = msgs[0].content
        assert "hotel in London" in content

    def test_mode1_recap_and_context_combined(self):
        """Both context and recap appear in agent switch message."""
        state = _make_state(
            messages=[
                HumanMessage(content="I want to go to Tokyo"),
                AIMessage(content="Tokyo is great!"),
                HumanMessage(content="find me flights"),
            ],
            active_agent="flight",
            previous_agent="general",
            shared_context={"general": {"destination": "Tokyo"}},
        )
        msgs = _build_agent_messages(state, "flight")
        content = msgs[0].content
        assert "SYSTEM CONTEXT" in content
        assert "Tokyo" in content


# ========================
# TestTaskQueueContextPropagation
# ========================


class TestTaskQueueContextPropagation:
    """Tests for pending_task_context populated when dequeuing."""

    @pytest.mark.asyncio
    async def test_dequeued_task_context_stored_in_pending(self) -> None:
        """When task queue is consumed, context is stored in pending_task_context."""
        state = _make_state(
            active_agent="flight",
            agent_signal=AgentSignal(
                agent_status="done",
                done_reason="flight_search_redirect",
            ),
            task_queue=[{"agent": "hotel", "context": "hotel in Rome"}],
            auto_chain=[],
        )
        with (
            patch("app.ai.graph.supervisor_v2._get_sv2_llm"),
            patch(
                "app.ai.graph.supervisor_v2._get_formatted_prompt",
                return_value="prompt",
            ),
        ):
            result = await route_or_classify(state)

        assert result["active_agent"] == "hotel"
        assert result.get("pending_task_context") == "hotel in Rome"


# ========================
# TestStripOrphanedToolMessages
# ========================


class TestStripOrphanedToolMessages:
    """Tests for _strip_orphaned_tool_messages (issue #808 core fix)."""

    def test_drops_orphaned_tool_message(self):
        """ToolMessage with no matching AIMessage tool_call is dropped."""
        messages = [
            HumanMessage(content="hello"),
            ToolMessage(content="orphan", tool_call_id="tc_missing"),
            AIMessage(content="response"),
        ]
        result = _strip_orphaned_tool_messages(messages)
        assert len(result) == 2
        assert all(not isinstance(m, ToolMessage) for m in result)

    def test_keeps_matched_tool_message(self):
        """ToolMessage whose tool_call_id matches an AIMessage tool_call is kept."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(
                content="calling tool",
                tool_calls=[{"name": "resolve", "args": {}, "id": "tc1"}],
            ),
            ToolMessage(content="result", tool_call_id="tc1"),
            AIMessage(content="done"),
        ]
        result = _strip_orphaned_tool_messages(messages)
        assert len(result) == 4
        assert isinstance(result[2], ToolMessage)

    def test_empty_list_noop(self):
        """Empty list returns empty list."""
        assert _strip_orphaned_tool_messages([]) == []

    def test_ai_messages_always_preserved(self):
        """AIMessages are never dropped, even when ToolMessages are stripped."""
        messages = [
            HumanMessage(content="start"),
            AIMessage(
                content="with tool",
                tool_calls=[{"name": "t", "args": {}, "id": "tc1"}],
            ),
            ToolMessage(content="matched", tool_call_id="tc1"),
            ToolMessage(content="orphan", tool_call_id="tc_gone"),
            AIMessage(content="no tools"),
        ]
        result = _strip_orphaned_tool_messages(messages)
        assert len(result) == 4  # orphan dropped
        ai_msgs = [m for m in result if isinstance(m, AIMessage)]
        assert len(ai_msgs) == 2  # both AIMessages kept

    def test_multiple_tool_calls_single_ai_message(self):
        """AIMessage with multiple tool_calls keeps all matching ToolMessages."""
        messages = [
            AIMessage(
                content="parallel calls",
                tool_calls=[
                    {"name": "a", "args": {}, "id": "tc1"},
                    {"name": "b", "args": {}, "id": "tc2"},
                ],
            ),
            ToolMessage(content="res1", tool_call_id="tc1"),
            ToolMessage(content="res2", tool_call_id="tc2"),
        ]
        result = _strip_orphaned_tool_messages(messages)
        assert len(result) == 3  # all kept


# ========================
# TestAuthErrorHandler
# ========================


class TestAuthErrorHandler:
    """Tests for _AUTH_ERRORS catch in _dispatch_agent (issue #808, Category 1)."""

    @pytest.mark.asyncio
    async def test_auth_error_returns_user_friendly_message(self):
        """AuthenticationError returns user-friendly error, not raw exception."""
        from openai import AuthenticationError

        state = _make_state(active_agent="flight", remaining_steps=5)
        mock_agent = AsyncMock()
        # Simulate OpenAI 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.headers = {}
        mock_agent.ainvoke = AsyncMock(
            side_effect=AuthenticationError(
                message="Incorrect API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}},
            ),
        )

        with patch(
            "app.ai.graph.flight_graph.get_flight_inner_agent",
            return_value=mock_agent,
        ):
            result = await dispatch_flight(state)

        assert result["agent_response"]["type"] == "error"
        # AI-CHAT-010: classifier routes AuthenticationError -> QUOTA so the
        # user sees "we've hit our daily AI quota and engineering has been
        # notified" instead of the previous "temporarily unavailable" copy.
        assert result["agent_response"]["error_class"] == "quota"
        assert "quota" in result["agent_response"]["message"].lower()
        assert result["agent_signal"]["agent_status"] == "failed"
        assert result["agent_signal"]["failed_reason"] == "auth_error"
        assert result["remaining_steps"] == 4


# ========================
# TestGraphCompiles
# ========================


class TestGraphCompiles:
    """Smoke test: the supervisor V2 graph must compile without raising.

    Regression for staging incident 2026-05-20: a node module had its state
    annotation imported only under ``TYPE_CHECKING`` while using
    ``from __future__ import annotations``. LangGraph's
    ``add_conditional_edges`` introspects node-callable annotations via
    ``typing.get_type_hints()``, which evaluates string forward references
    against the function's module globals; a TYPE_CHECKING-only import
    leaves the name undefined at runtime, the graph compile raises
    ``NameError``, and every chat turn fails.

    Every test that mocks ``get_supervisor_v2_graph`` skips this code path,
    so this is the gate that catches the whole class of bugs.
    """

    def test_get_supervisor_v2_graph_compiles(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from app.ai.graph import supervisor_v2

        with (
            patch.object(supervisor_v2, "_sv2_compiled_graph", None),
            patch.object(
                supervisor_v2,
                "_get_sv2_checkpointer",
                return_value=MemorySaver(),
            ),
        ):
            graph = supervisor_v2.get_supervisor_v2_graph()

        assert graph is not None
