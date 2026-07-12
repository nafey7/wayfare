"""Unit tests for the AI-CHAT-013 capability_check graph node.

Covers:
- Node returns empty/sentinel-clear dict when no limitation matches
- Node returns full disclosure update when a limitation matches
- active_agent is preserved (not cleared) on disclosure — user resumes their flow
- active_agent context acknowledgement is appended (flight / hotel / itinerary)
- school_calendar limitation does NOT append the ack (its template covers it)
- Stale ``capability_disclosure_id`` is always cleared on no-match
  (regression test for the scenario 31.15 bug found during development)
- ``route_after_capability_check`` returns the right edge target
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.graph.capability_check import (
    capability_check_node,
    route_after_capability_check,
)

if TYPE_CHECKING:
    from app.ai.graph.state import SupervisorV2State

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(
    *,
    messages: list[Any] | None = None,
    active_agent: str | None = None,
    chain_responses: list[dict[str, Any]] | None = None,
    capability_disclosure_id: str | None = None,
) -> SupervisorV2State:
    """Build a minimal SupervisorV2State for node-level tests.

    We cast to the TypedDict since the test only populates the handful of
    fields the node reads.
    """
    return cast(
        "SupervisorV2State",
        {
            "messages": messages or [],
            "active_agent": active_agent,
            "chain_responses": chain_responses or [],
            "capability_disclosure_id": capability_disclosure_id,
            # Required by TypedDict but unread by capability_check_node:
            "user_id": "u1",
            "chat_id": "test-chat",
            "user_email": "",
            "previous_agent": None,
            "current_intent": None,
            "agent_signal": None,
            "agent_response": None,
            "task_queue": [],
            "auto_chain": [],
            "shared_context": {},
            "detour_return": False,
            "pending_needs_input_agent": None,
            "hand_back_count": 0,
            "agent_start_index": 0,
            "detour_origin_index": 0,
            "classification_confidence": 0.0,
            "pending_task_context": "",
            "checkpoint_version": 1,
            "remaining_steps": 10,
        },
    )


# ---------------------------------------------------------------------------
# No-match path — node passes through to route_or_classify.
# ---------------------------------------------------------------------------


class TestCapabilityCheckNoMatch:
    def test_returns_sentinel_clear_when_no_limitation_matches(self) -> None:
        """A normal trip request must NOT trigger a disclosure."""
        state = _state(messages=[HumanMessage(content="Plan a 3-day trip to Tokyo")])
        result = capability_check_node(state)
        # Should ONLY clear the sentinel — no other state mutations.
        assert result == {"capability_disclosure_id": None}

    def test_returns_sentinel_clear_when_messages_empty(self) -> None:
        state = _state(messages=[])
        result = capability_check_node(state)
        assert result == {"capability_disclosure_id": None}

    def test_returns_sentinel_clear_when_no_human_messages(self) -> None:
        """Only AI messages in history — no user text to check against."""
        state = _state(messages=[AIMessage(content="Hello, how can I help?")])
        result = capability_check_node(state)
        assert result == {"capability_disclosure_id": None}

    def test_clears_stale_sentinel_after_prior_disclosure_turn(self) -> None:
        """Regression test for the 31.15 bug.

        After turn N fires a disclosure, ``capability_disclosure_id`` is set
        in state. On turn N+1, even if no new limitation matches, the
        conditional edge must route to ``route_or_classify`` — NOT short-
        circuit again to END with the stale disclosure.
        """
        state = _state(
            messages=[
                HumanMessage(content="Plan a 3-day trip to Tokyo"),
                AIMessage(content="<previous disclosure>"),
                HumanMessage(content="OK just continue with the itinerary"),
            ],
            active_agent="itinerary",
            capability_disclosure_id="large_villa_bedrooms",  # ← stale!
        )
        result = capability_check_node(state)
        # MUST clear the sentinel — otherwise the conditional edge sees the
        # stale id and routes to END with the previous disclosure response.
        assert result.get("capability_disclosure_id") is None


# ---------------------------------------------------------------------------
# Match path — node returns full disclosure update.
# ---------------------------------------------------------------------------


class TestCapabilityCheckMatch:
    def test_returns_capability_disclosure_response_on_match(self) -> None:
        state = _state(
            messages=[
                HumanMessage(content="Find me an Airbnb in Lisbon for June 15-20")
            ]
        )
        result = capability_check_node(state)
        # All required disclosure fields present.
        assert result["capability_disclosure_id"] == "external_listings"
        assert result["agent_response"]["type"] == "capability_disclosure"
        # New combined-offer shape: body mentions partner inventory or
        # third-party platforms; offer mentions what Voya CAN do.
        message = result["agent_response"]["message"]
        assert "partner inventory" in message or "third-party" in message
        assert "hotels" in message or "serviced apartments" in message

    def test_disclosure_data_includes_telemetry_fields(self) -> None:
        """data.limitation_id + data.matched_text drive Langfuse top-trigger metrics."""
        state = _state(
            messages=[HumanMessage(content="Find me hotels all of Albania next month")],
            active_agent="hotel",
        )
        result = capability_check_node(state)
        data = result["agent_response"]["data"]
        assert data["limitation_id"] == "region_wide_search"
        assert "all of Albania" in data["matched_text"]
        assert data["active_agent_at_trigger"] == "hotel"

    def test_disclosure_appends_ai_message_to_history(self) -> None:
        """The disclosure must show up in chat history (messages list)."""
        state = _state(
            messages=[HumanMessage(content="Find me a 5 bedroom villa in Bali")]
        )
        result = capability_check_node(state)
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    def test_disclosure_resets_chain_responses_to_single_entry(self) -> None:
        """Stale chain_responses from a prior turn must NOT carry over.

        route_or_classify normally clears ``chain_responses`` on every new
        turn, but the disclosure path short-circuits to END so that reset
        never runs. Without our reset here, ChatService re-persists
        ``chain_responses[:-1]`` as new bot messages — i.e. prior-turn
        responses would duplicate into chat history every time a disclosure
        fires mid-conversation.
        """
        stale = [{"type": "message", "message": "stale response from prior turn"}]
        state = _state(
            messages=[HumanMessage(content="When are UK school holidays this summer?")],
            chain_responses=stale,
        )
        result = capability_check_node(state)
        # Only the new disclosure — the stale entry from the prior turn is
        # dropped, mirroring how route_or_classify resets the field.
        assert len(result["chain_responses"]) == 1
        assert result["chain_responses"][0]["type"] == "capability_disclosure"

    def test_active_agent_is_preserved_on_disclosure(self) -> None:
        """User must be able to resume their itinerary/flight/hotel flow."""
        state = _state(
            messages=[HumanMessage(content="Find me a 5 bedroom villa in Bali")],
            active_agent="itinerary",
        )
        result = capability_check_node(state)
        # active_agent is intentionally NOT returned — meaning it's preserved
        # from state (no overwrite).
        assert "active_agent" not in result


# ---------------------------------------------------------------------------
# active_agent context acknowledgement (mid-flow disclosure UX).
# ---------------------------------------------------------------------------


class TestActiveAgentAcknowledgement:
    def test_flight_active_agent_uses_flight_offer(self) -> None:
        state = _state(
            messages=[HumanMessage(content="Find me an Airbnb in Paris for June")],
            active_agent="flight",
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        # The combined offer mentions continuing the flight flow.
        assert "flight search" in message.lower()

    def test_hotel_active_agent_uses_hotel_offer(self) -> None:
        state = _state(
            messages=[HumanMessage(content="Find me an Airbnb in Paris for June")],
            active_agent="hotel",
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        assert "hotel" in message.lower()

    def test_itinerary_active_agent_uses_itinerary_offer(self) -> None:
        state = _state(
            messages=[HumanMessage(content="Find me a 5 bedroom villa")],
            active_agent="itinerary",
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        assert "itinerary" in message.lower()
        # And the alternative is still surfaced (single combined question).
        assert "standard hotel rooms" in message.lower()

    def test_no_active_agent_uses_default_offer(self) -> None:
        """Cold first turn — no active agent, use offer_default."""
        state = _state(
            messages=[HumanMessage(content="Find me an Airbnb in Paris for June")],
            active_agent=None,
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        # Default offer is generic — no per-agent phrasing like
        # "continue your flight search".
        assert "continue your" not in message.lower()
        # But should still propose what Voya CAN do.
        assert "hotels" in message.lower() or "serviced apartments" in message.lower()

    def test_school_calendar_uses_default_offer_even_with_active_agent(self) -> None:
        """school_calendar deliberately defines no offer_when_active overrides
        — the default already covers resume ("tell me a date range")."""
        state = _state(
            messages=[HumanMessage(content="When are UK school holidays this summer?")],
            active_agent="itinerary",
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        # The default offer ("specific date range") is present.
        assert "date range" in message.lower()

    def test_disclosure_is_single_paragraph_no_double_newlines(self) -> None:
        """Body + offer must be one paragraph — no `\\n\\n` split that makes
        the message feel like two robot responses glued together."""
        state = _state(
            messages=[HumanMessage(content="Find me a 5 bedroom villa")],
            active_agent="itinerary",
        )
        result = capability_check_node(state)
        message = result["agent_response"]["message"]
        assert "\n\n" not in message, (
            f"disclosure must be one paragraph, got:\n{message!r}"
        )


# ---------------------------------------------------------------------------
# route_after_capability_check — conditional edge function.
# ---------------------------------------------------------------------------


class TestRouteAfterCapabilityCheck:
    def test_returns_END_when_disclosure_id_set(self) -> None:
        state = _state(capability_disclosure_id="region_wide_search")
        assert route_after_capability_check(state) == "END"

    def test_returns_route_or_classify_when_disclosure_id_none(self) -> None:
        state = _state(capability_disclosure_id=None)
        assert route_after_capability_check(state) == "route_or_classify"

    def test_returns_route_or_classify_when_disclosure_id_missing(self) -> None:
        """Defensive: TypedDict can omit the field entirely; default to None."""
        state = cast("SupervisorV2State", {"messages": []})
        assert route_after_capability_check(state) == "route_or_classify"


# ---------------------------------------------------------------------------
# Regression: node annotations must resolve at runtime.
# ---------------------------------------------------------------------------


class TestNodeAnnotationsResolveAtRuntime:
    """LangGraph introspects node-callable annotations via ``typing.get_type_hints()``
    during ``add_conditional_edges`` (see ``langgraph.graph._branch.
    _get_branch_path_input_schema``). With ``from __future__ import annotations``
    in this module, the annotation is a string forward reference and
    ``get_type_hints`` evaluates it against the module's globals.

    If ``SupervisorV2State`` is imported only under ``TYPE_CHECKING``, the
    eval fails with ``NameError`` at graph compile time, which crashes every
    chat turn (the broad ``except`` in ``chat/service.py`` swallows it into
    the generic "I'm having trouble processing your request" error).

    Regression for staging incident 2026-05-20 (PR #1077 deploy).
    """

    def test_capability_check_node_type_hints_resolve(self) -> None:
        from typing import get_type_hints

        get_type_hints(capability_check_node)

    def test_route_after_capability_check_type_hints_resolve(self) -> None:
        from typing import get_type_hints

        get_type_hints(route_after_capability_check)
