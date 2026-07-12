"""Unit tests for AI-CHAT-011 output verification.

Covers every shape ``verify_agent_output`` should and should NOT flag:

- itinerary / flight / hotel happy paths (artifact present) → no failure
- itinerary / flight / hotel type-claimed-but-missing → ``VerificationFailure``
- general agent → never flagged (no artifact to verify)
- agent in conversation mode (``type="message"`` etc.) → never flagged
- missing active_agent → never flagged
- unknown active_agent string → never flagged (defensive guard)

The state shapes mirror what each agent actually returns in production —
see the comment block on each class for the cross-reference to the
producing code.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.graph.constants import AgentName
from app.ai.graph.output_verification import (
    ClaimType,
    VerificationFailure,
    VerificationFailureReason,
    _get_required_tool_name,
    verify_agent_output,
)

# ---------------------------------------------------------------------------
# Itinerary verification
# ---------------------------------------------------------------------------


class TestItineraryVerification:
    """Itinerary success contract:
    ``response["type"] == "itinerary_results"``
    AND ``response["metadata"]["structured_itinerary"]["itineraryItems"]`` non-empty.

    Source: ``app/ai/graph/itinerary_graph.py`` (agent dispatch return).
    """

    @staticmethod
    def _state(response: dict[str, Any]) -> dict[str, Any]:
        return {
            "active_agent": AgentName.ITINERARY.value,
            "agent_response": response,
        }

    def test_happy_path_no_failure(self) -> None:
        """Real itinerary with items: verifier silent."""
        state = self._state(
            {
                "type": "itinerary_results",
                "message": "Here's your 5-day Tokyo trip!",
                "metadata": {
                    "structured_itinerary": {
                        "itineraryItems": [
                            {"day": 1, "activities": ["..."]},
                            {"day": 2, "activities": ["..."]},
                        ],
                    },
                },
            }
        )
        assert verify_agent_output(state) is None

    def test_type_claimed_but_metadata_missing_flagged(self) -> None:
        """Agent set type=itinerary_results but never produced metadata.

        The smoking-gun case from production feedback #5/#6.
        """
        state = self._state(
            {
                "type": "itinerary_results",
                "message": "Here's your itinerary!",
                # NB: no `metadata` key at all
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.ITINERARY
        assert result.reason is VerificationFailureReason.TYPE_CLAIMED_ARTIFACT_MISSING
        assert result.agent == "itinerary"
        assert result.response_type == "itinerary_results"

    def test_type_claimed_but_structured_itinerary_empty_flagged(self) -> None:
        """metadata present but structured_itinerary missing/falsy."""
        state = self._state(
            {
                "type": "itinerary_results",
                "message": "Here's your itinerary!",
                "metadata": {"structured_itinerary": None},
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.ITINERARY

    def test_type_claimed_but_itinerary_items_empty_flagged(self) -> None:
        """structured_itinerary present but itineraryItems is empty.

        An itinerary with zero days is unusable for the user — treat as missing.
        """
        state = self._state(
            {
                "type": "itinerary_results",
                "metadata": {"structured_itinerary": {"itineraryItems": []}},
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.ITINERARY

    def test_conversation_mode_not_flagged(self) -> None:
        """Agent asking for dates (type=message) — silent regardless of prose."""
        state = self._state(
            {
                "type": "message",
                "message": "When would you like to travel?",
            }
        )
        assert verify_agent_output(state) is None

    def test_hand_back_not_flagged(self) -> None:
        """Hand-back to supervisor — silent."""
        state = self._state(
            {
                "type": "hand_back",
                "message": "Routing you to the flight agent.",
            }
        )
        assert verify_agent_output(state) is None


# ---------------------------------------------------------------------------
# Flight verification
# ---------------------------------------------------------------------------


class TestFlightVerification:
    """Flight success contract:
    ``response["type"] == "flight_search_results"``
    AND ``response["flights"]`` is a non-empty list.

    Source: ``app/ai/graph/flight_graph.py:344`` (agent dispatch return).
    """

    @staticmethod
    def _state(response: dict[str, Any]) -> dict[str, Any]:
        return {
            "active_agent": AgentName.FLIGHT.value,
            "agent_response": response,
        }

    def test_happy_path_no_failure(self) -> None:
        state = self._state(
            {
                "type": "flight_search_results",
                "message": "I found 12 flights.",
                "flights": [{"id": "f1"}, {"id": "f2"}],
                "session_id": "fs1",
            }
        )
        assert verify_agent_output(state) is None

    def test_type_claimed_but_flights_missing_flagged(self) -> None:
        state = self._state(
            {
                "type": "flight_search_results",
                "message": "I found 12 flights from London to Paris.",
                # `flights` key entirely absent
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.FLIGHT
        assert result.reason is VerificationFailureReason.TYPE_CLAIMED_ARTIFACT_MISSING
        assert result.response_type == "flight_search_results"

    def test_type_claimed_but_flights_empty_list_flagged(self) -> None:
        state = self._state(
            {
                "type": "flight_search_results",
                "message": "I found 12 flights.",
                "flights": [],
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.FLIGHT

    def test_type_claimed_but_flights_wrong_shape_flagged(self) -> None:
        """``flights`` key present but not a list — treat as missing."""
        state = self._state(
            {
                "type": "flight_search_results",
                "flights": "not-a-list",
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)

    def test_conversation_mode_not_flagged(self) -> None:
        """Agent collecting params — silent."""
        state = self._state(
            {
                "type": "flight_conversation",
                "message": "What's your departure city?",
            }
        )
        assert verify_agent_output(state) is None

    def test_multicity_results_not_verified_yet(self) -> None:
        """``multicity_flight_search_results`` isn't in the contract (different
        artifact shape) — verifier silent for now. Follow-up if telemetry
        shows hallucinations on multi-city."""
        state = self._state(
            {
                "type": "multicity_flight_search_results",
                "message": "Found options.",
                # No flights array — but type isn't the standard one we verify
            }
        )
        assert verify_agent_output(state) is None


# ---------------------------------------------------------------------------
# Hotel verification
# ---------------------------------------------------------------------------


class TestHotelVerification:
    """Hotel success contract:
    ``response["type"] == "hotel_search_results"``
    AND ``response["hotels"]`` is a non-empty list.

    Source: ``app/ai/graph/hotel_graph.py:188-191`` (agent dispatch return).
    """

    @staticmethod
    def _state(response: dict[str, Any]) -> dict[str, Any]:
        return {
            "active_agent": AgentName.HOTEL.value,
            "agent_response": response,
        }

    def test_happy_path_no_failure(self) -> None:
        state = self._state(
            {
                "type": "hotel_search_results",
                "message": "I found 8 hotels.",
                "hotels": [{"hotel_id": "h1"}],
                "session_id": "hs1",
            }
        )
        assert verify_agent_output(state) is None

    def test_type_claimed_but_hotels_missing_flagged(self) -> None:
        state = self._state(
            {
                "type": "hotel_search_results",
                "message": "I found 8 hotels in Paris.",
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.HOTEL
        assert result.response_type == "hotel_search_results"

    def test_type_claimed_but_hotels_empty_list_flagged(self) -> None:
        state = self._state(
            {
                "type": "hotel_search_results",
                "hotels": [],
            }
        )
        result = verify_agent_output(state)
        assert isinstance(result, VerificationFailure)
        assert result.claim_type is ClaimType.HOTEL

    def test_conversation_mode_not_flagged(self) -> None:
        state = self._state(
            {
                "type": "hotel_conversation",
                "message": "Which city are you staying in?",
            }
        )
        assert verify_agent_output(state) is None


# ---------------------------------------------------------------------------
# Non-artifact agents and defensive edge cases
# ---------------------------------------------------------------------------


class TestGeneralAndEdgeCases:
    def test_general_agent_never_flagged(self) -> None:
        """General agent produces no artifact — silent regardless of response."""
        state = {
            "active_agent": AgentName.GENERAL.value,
            "agent_response": {
                "type": "message",
                "message": "Here's some general travel info!",
            },
        }
        assert verify_agent_output(state) is None

    def test_no_active_agent_never_flagged(self) -> None:
        """Cold first turn / pre-dispatch — silent."""
        state: dict[str, Any] = {"active_agent": None, "agent_response": None}
        assert verify_agent_output(state) is None

    def test_no_agent_response_never_flagged(self) -> None:
        """active_agent set but response missing — silent. Don't double-fault."""
        state: dict[str, Any] = {
            "active_agent": AgentName.ITINERARY.value,
            "agent_response": None,
        }
        assert verify_agent_output(state) is None

    def test_unknown_agent_string_never_flagged(self) -> None:
        """Defensive: a future / typo agent name shouldn't crash the verifier."""
        state = {
            "active_agent": "transit",
            "agent_response": {"type": "transit_results", "message": "x"},
        }
        assert verify_agent_output(state) is None

    def test_empty_state_never_flagged(self) -> None:
        """Truly minimal state dict — silent, never raises."""
        assert verify_agent_output({}) is None


# ---------------------------------------------------------------------------
# Return-shape + helper-function contracts
# ---------------------------------------------------------------------------


class TestReturnShapeAndHelpers:
    def test_verification_failure_is_frozen(self) -> None:
        result = verify_agent_output(
            {
                "active_agent": AgentName.ITINERARY.value,
                "agent_response": {"type": "itinerary_results"},
            }
        )
        assert isinstance(result, VerificationFailure)
        with pytest.raises((AttributeError, TypeError)):
            result.agent = "flight"  # type: ignore[misc]

    @pytest.mark.parametrize(
        ("claim_type", "expected_tool"),
        [
            (ClaimType.ITINERARY, "generate_itinerary"),
            (ClaimType.FLIGHT, "search_flights"),
            (ClaimType.HOTEL, "search_hotels"),
        ],
    )
    def test_required_tool_name_maps_to_each_claim_type(
        self, claim_type: ClaimType, expected_tool: str
    ) -> None:
        """Retry-handler contract: each claim has a single tool the agent
        must call to fulfil it."""
        assert _get_required_tool_name(claim_type) == expected_tool

    def test_claim_type_values_are_stable_strings(self) -> None:
        """Stable cross-system tag values — guard against accidental drift."""
        assert ClaimType.ITINERARY.value == "itinerary"
        assert ClaimType.FLIGHT.value == "flight"
        assert ClaimType.HOTEL.value == "hotel"
