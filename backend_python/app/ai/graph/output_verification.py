"""Output verification for the V2 Supervisor (AI-CHAT-011).

The bug class this module catches
---------------------------------
Production feedback #5 + #6: Voya occasionally claims an itinerary / flight /
hotel result has been produced when the corresponding tool was either never
called or returned empty. The user sees a confident success message but no
cards.

This module covers the **deterministic** sub-class of the bug: when the
agent has set ``agent_response["type"]`` to a results-type identifier
(``itinerary_results`` / ``flight_search_results`` / ``hotel_search_results``)
but the corresponding artifact field is missing or empty.

The prose-only sub-class — where the LLM writes "Here's your itinerary!" in
the message body but never sets the results type — is left for a follow-up
commit once production telemetry tells us how often it fires relative to
this deterministic case.

Why deterministic-only first
----------------------------
- Cheap: pure dict lookup, no regex / no LLM call.
- Zero false positives: structural mismatch is unambiguous.
- Easy to test: state shapes are well-defined and stable.
- Telemetry-first rollout: log the detection events and let production
  data drive whether prose-pattern matching is worth adding.

Architecture context
--------------------
The supervisor's graph dispatches to one of four agent nodes (flight /
hotel / itinerary / general). Each agent's success contract:

================ ================================ ===========================
``active_agent`` Success ``response["type"]``    Artifact location
================ ================================ ===========================
``itinerary``    ``"itinerary_results"``          ``response["metadata"]["structured_itinerary"]``
``flight``       ``"flight_search_results"``      ``response["flights"]``  (non-empty list)
``hotel``        ``"hotel_search_results"``       ``response["hotels"]``   (non-empty list)
``general``      n/a — produces no artifact       n/a
================ ================================ ===========================

A type/artifact mismatch is the signal we act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.ai.graph.constants import AgentName


class ClaimType(StrEnum):
    """Which artifact the agent claimed to have produced.

    Used as a stable tag in logs + future Sentry breadcrumbs so we can
    pivot frequency by class in CloudWatch / dashboards.
    """

    ITINERARY = "itinerary"
    FLIGHT = "flight"
    HOTEL = "hotel"


# Reasons the verifier surfaces. ``StrEnum`` so logs render cleanly and
# downstream consumers (retry handler, fallback node) can branch on it.
class VerificationFailureReason(StrEnum):
    """Specific shape of the failure the verifier detected."""

    #: Agent set ``type`` to a results identifier but the artifact field
    #: is missing or empty. The deterministic case.
    TYPE_CLAIMED_ARTIFACT_MISSING = "type_claimed_artifact_missing"


@dataclass(frozen=True, slots=True)
class VerificationFailure:
    """Result of a verification miss — the agent claimed completion but
    the structured artifact backing the claim is absent.

    Attributes:
        claim_type: Which artifact class was claimed (itinerary / flight / hotel).
        reason: Specific failure shape (see :class:`VerificationFailureReason`).
        agent: ``active_agent`` value at the time of the failed dispatch.
        response_type: The ``type`` field the agent actually set on
            its response — useful in logs for spotting drift if agents
            start returning new type strings.
    """

    claim_type: ClaimType
    reason: VerificationFailureReason
    agent: str
    response_type: str


# Per-agent contract: (expected_type, required_tool_name, ClaimType).
# Single source of truth for every "what should this agent's success look
# like" lookup in this module — the verifier reads ``expected_type``, the
# retry handler reads ``tool_name`` via :func:`_get_required_tool_name`,
# and the post-flag lookup reads ``ClaimType``.
_AGENT_SUCCESS_CONTRACT: dict[AgentName, tuple[str, str, ClaimType]] = {
    AgentName.ITINERARY: (
        "itinerary_results",
        "generate_itinerary",
        ClaimType.ITINERARY,
    ),
    AgentName.FLIGHT: ("flight_search_results", "search_flights", ClaimType.FLIGHT),
    AgentName.HOTEL: ("hotel_search_results", "search_hotels", ClaimType.HOTEL),
}

# Reverse map: ClaimType → tool name, derived from the contract so the
# two never drift. Built at import time; no runtime cost.
_CLAIM_TYPE_TO_TOOL: dict[ClaimType, str] = {
    contract[2]: contract[1] for contract in _AGENT_SUCCESS_CONTRACT.values()
}


def _has_itinerary_artifact(response: dict[str, Any]) -> bool:
    """True if ``response`` carries a non-empty ``structured_itinerary``.

    The itinerary tool nests the structured payload under ``metadata`` —
    a dict of dicts; an empty dict here counts as missing.
    """
    metadata = response.get("metadata") or {}
    structured = metadata.get("structured_itinerary")
    if not isinstance(structured, dict) or not structured:
        return False
    # Be conservative: a structured_itinerary with no items is the same
    # as no itinerary for the user's purposes.
    items = structured.get("itineraryItems")
    return bool(items)


def _has_flight_artifact(response: dict[str, Any]) -> bool:
    """True if ``response`` carries a non-empty top-level ``flights`` list."""
    flights = response.get("flights")
    # Shape-check first: ``"not-a-list"`` is truthy under ``bool()`` so
    # the order matters.
    return isinstance(flights, list) and bool(flights)


def _has_hotel_artifact(response: dict[str, Any]) -> bool:
    """True if ``response`` carries a non-empty top-level ``hotels`` list."""
    hotels = response.get("hotels")
    return isinstance(hotels, list) and bool(hotels)


def _get_required_tool_name(claim_type: ClaimType) -> str:
    """Return the tool name the agent should call to fulfil ``claim_type``.

    Used by the retry handler to inject a stricter system message like
    *'Your previous response set type=itinerary_results but no
    structured_itinerary was produced. You MUST call
    generate_itinerary now.'* Derived from :data:`_AGENT_SUCCESS_CONTRACT`
    so the two never drift.
    """
    return _CLAIM_TYPE_TO_TOOL[claim_type]


def verify_agent_output(state: dict[str, Any]) -> VerificationFailure | None:
    """Verify that the dispatched agent produced the artifact its response claims.

    Args:
        state: The supervisor's :class:`SupervisorV2State` dict at the
            point the verifier runs (after the agent node has finished).

    Returns:
        :class:`VerificationFailure` when the agent's ``response.type`` claims a
        result class but the corresponding artifact is missing or empty.
        ``None`` for every other case — including legitimate conversation
        turns where the agent asks for more info, hand-backs, and the
        general agent which produces no artifact.

    Why this is conservative
    ------------------------
    We only flag the case where the agent ITSELF marked the turn as a
    result (``type == "itinerary_results"`` etc.). If the agent left the
    type as ``"message"`` or ``"flight_conversation"``, we trust that —
    it's the agent saying *"I'm still in conversation mode."* The
    prose-claims-completion-but-type-says-otherwise case is the
    follow-up commit.
    """
    active_agent_raw = state.get("active_agent")
    if active_agent_raw is None:
        return None

    # active_agent is stored as a string (AgentName.value) in checkpointed
    # state. Coerce so the membership check works for both shapes.
    try:
        active_agent = AgentName(active_agent_raw)
    except ValueError:
        return None  # unknown agent — nothing to verify

    if active_agent not in _AGENT_SUCCESS_CONTRACT:
        return None  # general agent — nothing to verify

    response = state.get("agent_response") or {}
    response_type = str(response.get("type") or "")

    expected_type, _required_tool, claim_type = _AGENT_SUCCESS_CONTRACT[active_agent]

    # Only verify when the agent's response_type CLAIMS a result. If the
    # agent set type to something conversational (asking for info,
    # hand-back, etc.) we have nothing to check — the agent didn't claim
    # completion, so there's nothing to disprove.
    if response_type != expected_type:
        return None

    # Per-agent artifact check.
    artifact_present = {
        AgentName.ITINERARY: _has_itinerary_artifact,
        AgentName.FLIGHT: _has_flight_artifact,
        AgentName.HOTEL: _has_hotel_artifact,
    }[active_agent](response)

    if artifact_present:
        return None  # all good

    return VerificationFailure(
        claim_type=claim_type,
        reason=VerificationFailureReason.TYPE_CLAIMED_ARTIFACT_MISSING,
        agent=active_agent.value,
        response_type=response_type,
    )


__all__ = [
    "ClaimType",
    "VerificationFailure",
    "VerificationFailureReason",
    "_get_required_tool_name",
    "verify_agent_output",
]
