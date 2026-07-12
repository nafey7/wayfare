"""Pre-routing capability check node (AI-CHAT-013).

Sits as the entry point of the supervisor StateGraph, BEFORE
``route_or_classify``. Matches the latest user message against
``KNOWN_LIMITATIONS``; on hit, short-circuits the entire graph with a
disclosure response.

Why a node, not LangChain middleware
------------------------------------
Voya's supervisor is a custom ``StateGraph`` (see ``supervisor_v2.py:2762``),
not a ``create_agent(...)`` agent, so the LangChain 1.0 ``before_agent``
middleware mechanism doesn't apply. The equivalent in this architecture
is a dedicated entry node + conditional edge to ``END``.

Rule for new nodes in this file (or any sibling module)
-------------------------------------------------------
State-typed callables registered as graph nodes or conditional-edge
routers (``add_node``, ``add_conditional_edges``) must have their state
type importable at runtime, NOT only under ``TYPE_CHECKING``. LangGraph
calls ``typing.get_type_hints()`` against the callable during graph
compile to derive the input schema; with ``from __future__ import
annotations`` the annotation is a string forward reference resolved
against this module's globals, so a TYPE_CHECKING-only import crashes
the compile with ``NameError`` and breaks every chat turn (see #1109).
``noqa: TC001`` on the runtime import is intentional.

Routing
-------
The conditional edge after this node returns ``END`` when
``capability_disclosure_id`` is set in state, otherwise ``route_or_classify``.
See ``supervisor_v2.py`` graph wiring.

Telemetry
---------
Sets ``classification_confidence=1.0`` to signal a deterministic decision
(consistent with the existing fast-path forwarding tier marker). The
matched limitation id is written to ``agent_response.data.limitation_id``
and also emitted via ``logger.info`` for CloudWatch grep-based analysis
of "top-triggered limitations this week". A dedicated Langfuse trace tag
is tracked as a follow-up — wiring it requires threading metadata
through ``traced_observation`` and isn't done in v1.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.graph.limitations import LimitationMatch, match_limitation

# Runtime import (not TYPE_CHECKING): LangGraph's `add_conditional_edges`
# resolves node-callable annotations via `typing.get_type_hints()` during
# graph compile, which evaluates the string forward reference against this
# module's globals. A TYPE_CHECKING-only import crashes the compile with
# NameError, breaking every chat turn (see test_capability_check.py).
from app.ai.graph.state import SupervisorV2State  # noqa: TC001

logger = logging.getLogger(__name__)


def _latest_user_text(messages: list[Any]) -> str:
    """Return the most recent ``HumanMessage`` content, or empty string.

    Equivalent shape to ``supervisor_v2._get_latest_user_message`` but
    duplicated here so this module has no dependency on the supervisor.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""


def capability_check_node(state: SupervisorV2State) -> dict[str, Any]:
    """Entry node: match the latest user message against KNOWN_LIMITATIONS.

    Returns one of two state updates:

    1. Match — short-circuit. Sets ``capability_disclosure_id`` so the
       conditional edge routes to ``END``. Builds an ``agent_response`` with
       the disclosure text and appends an ``AIMessage`` to the conversation
       so the disclosure shows in chat history. Preserves ``active_agent`` so
       the user can resume their prior flow on the next turn.

    2. No match — empty dict (passes through). The graph proceeds to
       ``route_or_classify`` and normal routing happens.
    """
    user_message = _latest_user_text(state.get("messages", []))
    if not user_message:
        # Always clear the sentinel — checkpointed state from a prior
        # disclosure turn would otherwise route this turn to END too.
        return {"capability_disclosure_id": None}

    hit: LimitationMatch | None = match_limitation(user_message)
    if not hit:
        # No match this turn: clear any leftover sentinel from a prior turn
        # so the conditional edge correctly routes to route_or_classify.
        return {"capability_disclosure_id": None}

    active_agent = state.get("active_agent")
    disclosure_text = _build_disclosure_response(hit, active_agent)

    logger.info(
        "capability_disclosure: id=%s matched=%r active_agent=%s",
        hit.limitation_id,
        hit.matched_text,
        active_agent,
    )

    agent_response: dict[str, Any] = {
        "message": disclosure_text,
        "type": "capability_disclosure",
        "data": {
            "limitation_id": hit.limitation_id,
            "matched_text": hit.matched_text,
            "active_agent_at_trigger": active_agent,
        },
    }

    return {
        "messages": [AIMessage(content=disclosure_text)],
        "agent_response": agent_response,
        # RESET chain_responses (not append). route_or_classify normally
        # clears it on every new turn, but the disclosure path short-circuits
        # to END so that reset never runs. Without resetting here, the
        # checkpointer carries prior-turn responses into this turn, and
        # ChatService (domains/chat/service.py:365) re-persists
        # ``chain_responses[:-1]`` as new bot messages — i.e. the previous
        # turn's reply would duplicate into chat history.
        "chain_responses": [agent_response],
        # active_agent is intentionally NOT cleared — user can resume their
        # flight/hotel/itinerary conversation with their next message.
        # Tier indicator: 1.0 = deterministic decision (matches fast-path marker).
        "classification_confidence": 1.0,
        # Sentinel for the conditional edge to route to END.
        "capability_disclosure_id": hit.limitation_id,
    }


def _build_disclosure_response(hit: LimitationMatch, active_agent: str | None) -> str:
    """Compose a single-paragraph disclosure: body + one offer.

    The offer is context-aware when ``active_agent`` matches a key in
    ``hit.offer_when_active``; otherwise it's the cold-turn default. This
    keeps the message one coherent question (e.g. "Want me to continue
    your itinerary, or search standard hotel rooms?") instead of two
    competing offers in separate paragraphs.
    """
    offer = hit.offer_when_active.get(active_agent or "", hit.offer_default)
    # Single space, not newline — these are two halves of one statement,
    # not two messages.
    return f"{hit.disclosure_body} {offer}"


def route_after_capability_check(state: SupervisorV2State) -> str:
    """Conditional edge: END on disclosure, else proceed to ``route_or_classify``."""
    if state.get("capability_disclosure_id"):
        return "END"
    return "route_or_classify"


__all__ = [
    "capability_check_node",
    "route_after_capability_check",
]
