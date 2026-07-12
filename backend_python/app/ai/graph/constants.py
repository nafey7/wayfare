"""Shared constants for V2 multi-agent graph architecture.

Single source of truth for agent names, signal types, response types,
and LLM configuration.  Eliminates magic strings across supervisor_v2.py,
graph modules, and tools.
"""

from enum import StrEnum

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

# Standard temperatures by use-case
TEMPERATURE_CLASSIFICATION = 0.1  # Supervisor routing — low for consistency
TEMPERATURE_AGENT = 0.3  # Agent conversation — balanced
TEMPERATURE_CREATIVE = 0.7  # Itinerary generation — more creative
TEMPERATURE_DETERMINISTIC = 0.0  # Summarization / date parsing — exact
TEMPERATURE_BUDGET = 0.2  # Budget estimation — mostly deterministic


class AgentName(StrEnum):
    """Specialist agent identifiers used in routing and dispatch."""

    FLIGHT = "flight"
    HOTEL = "hotel"
    ITINERARY = "itinerary"
    GENERAL = "general"


class AgentStatus(StrEnum):
    """Structured signal statuses returned by agents to the supervisor."""

    DONE = "done"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"
    HAND_BACK = "hand_back"


class DoneReason(StrEnum):
    """Reasons an agent signals 'done' — drives auto-chain and queue logic."""

    BOOKING_COMPLETE = "booking_complete"
    PLANNING_COMPLETE = "planning_complete"
    QUERY_ANSWERED = "query_answered"


class SignalType(StrEnum):
    """Signal field values set by agent dispatch functions."""

    DONE = "done"
    HAND_BACK = "hand_back"


class ResponseType(StrEnum):
    """Response type identifiers for booking redirect detection."""

    FLIGHT_BOOKING_REDIRECT = "flight_booking_redirect"
    HOTEL_BOOKING_REDIRECT = "hotel_booking_redirect"


# Sets for validation
VALID_AGENTS = frozenset(AgentName)
QUEUEABLE_AGENTS = frozenset({AgentName.FLIGHT, AgentName.HOTEL, AgentName.ITINERARY})

# ---------------------------------------------------------------------------
# History management — conversation checkpoint pruning
# ---------------------------------------------------------------------------

# Maximum messages to keep in the supervisor checkpoint after windowing.
MAX_MESSAGES_IN_CHECKPOINT = 30

# Only trigger windowing when messages exceed this count (avoids pruning
# on every single dispatch when hovering near the limit).
PRUNE_TRIGGER_THRESHOLD = 40

# Tool names whose ToolMessage output is large enough to warrant compaction
# in the checkpoint. ``search_flights`` and ``search_hotels`` no longer need
# compaction post #1034 — they use ``response_format="content_and_artifact"``
# so the LLM-visible content is already compact (summary + instruction) and
# the heavy payload lives on ``ToolMessage.artifact`` (excluded from LLM
# context by design). Only ``generate_itinerary`` still needs runtime
# compaction.
COMPACTABLE_TOOLS = frozenset(
    {
        "generate_itinerary",
    }
)

# ---------------------------------------------------------------------------
# Cross-agent shared trip fields
# ---------------------------------------------------------------------------

# Fields extracted from itinerary/trip data and shared between agents
# (e.g. supervisor context capture, itinerary cross-agent extraction).
TRIP_FIELDS = (
    "origin",
    "origin_iata",
    "origin_name",
    "origin_is_country",
    "destination",
    "destination_city",
    "destination_iata",
    "destination_name",
    "destination_country",
    # #1127: when the user names a country instead of a city
    # ("Montenegro", "Iceland"), ``destination`` stays the country label so
    # the itinerary LLM produces a multi-city country plan, and
    # ``destination_search_city`` carries the resolved tourist hub used by
    # the flight + hotel side-searches (which require a real city).
    "destination_is_country",
    "destination_search_city",
    # #1127: dedup key for the hotel side-search inputs so a re-entry to
    # pre_resolve_trip on a follow-up turn doesn't repeat the FlightLogic
    # hotel call when only origin changed.
    "last_hotel_search_key",
    "departure_date",
    "return_date",
    "trip_duration_days",
    "adults",
    "children",
    "infants",
    "nearby_lat",
    "nearby_lng",
    "interests",
)
