"""State definitions for LangGraph travel agents.

This module defines the state schemas used by the flight and hotel booking graphs.
The state persists across conversation turns via MongoDB checkpointer.
"""

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class FlightParams(TypedDict, total=False):
    """Collected flight search parameters.

    All fields are optional (total=False) because they're progressively
    collected during conversation.
    """

    origin: str | None  # IATA code (e.g., "LHR")
    origin_name: str | None  # Display name (e.g., "London Heathrow")
    origin_is_city: bool | None  # True if user said city name, False if airport code
    destination: str | None  # IATA code
    destination_name: str | None  # Display name
    destination_is_city: (
        bool | None
    )  # True if user said city name, False if airport code
    departure_date: str | None  # YYYY-MM-DD format
    return_date: str | None  # YYYY-MM-DD format (None for one-way)
    adults: int  # Default: 1
    children: int  # Default: 0
    infants: int  # Default: 0
    destination_preference: str | None  # e.g., "warm", "beach", "ski"

    # Flight filters
    cabin_class: str | None  # 'economy', 'premium_economy', 'business', 'first'
    max_stops: int | None  # 0=direct (API), >0 post-filter
    price_min: float | None  # Minimum price post-filter
    price_max: float | None  # Maximum price post-filter
    preferred_airline: str | None  # IATA airline code (e.g., 'BA', 'EK')
    max_outbound_duration: (
        float | None
    )  # Max outbound flight duration in hours (post-filter)
    max_inbound_duration: (
        float | None
    )  # Max inbound/return flight duration in hours (post-filter)


class FlightState(TypedDict):
    """State for the flight booking conversation.

    This is the single source of truth for the flight booking flow.
    LangGraph automatically loads/saves this state via the checkpointer.

    Attributes:
        messages: Conversation history (auto-accumulated via add_messages reducer)
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (also used as thread_id for checkpointing)
        flight: Collected flight search parameters
        flight_results: Search results (set after search, cleared on new search)
        selected_flight: User's selected flight option
        response_type: Type hint for frontend rendering
        response_data: Additional data for frontend (e.g., flight cards)
        remaining_steps: LangGraph internal field for recursion limit (required in 1.x)
    """

    # Message history - add_messages reducer appends new messages to existing list
    messages: Annotated[list[BaseMessage], add_messages]

    # Identifiers
    user_id: str
    chat_id: str

    # Flight parameters (progressively collected)
    flight: FlightParams

    # Search results (set after search)
    flight_results: list[dict[str, Any]] | None

    # Selected flight (set after user selection)
    selected_flight: dict[str, Any] | None

    # Response formatting for frontend
    response_type: str
    response_data: dict[str, Any] | None

    # LangGraph internal - tracks remaining recursion steps (required in LangGraph 1.x)
    remaining_steps: int


class HotelParams(TypedDict, total=False):
    """Collected hotel search parameters.

    All fields are optional (total=False) because they're progressively
    collected during conversation.
    """

    city: str | None  # City name (e.g., "Paris")
    country: str | None  # Country name (e.g., "France")
    checkin: str | None  # YYYY-MM-DD format
    checkout: str | None  # YYYY-MM-DD format
    rooms: int  # Default: 1
    adults: int  # REQUIRED - agent must always ask
    children: int  # Default: 0
    # Post-filters
    price_min: float | None
    price_max: float | None
    min_rating: int | None
    property_types: list[str] | None
    refundable_only: bool | None
    required_facilities: list[str] | None
    max_distance_km: float | None
    locality: str | None
    nearby_lat: float | None
    nearby_lng: float | None


class HotelState(TypedDict):
    """State for the hotel booking conversation.

    This is the single source of truth for the hotel booking flow.
    LangGraph automatically loads/saves this state via the checkpointer.

    Attributes:
        messages: Conversation history (auto-accumulated via add_messages reducer)
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (also used as thread_id for checkpointing)
        hotel: Collected hotel search parameters
        hotel_results: Search results (set after search, cleared on new search)
        session_id: FlightLogic session ID (required for room rates/booking)
        selected_hotel: User's selected hotel option
        response_type: Type hint for frontend rendering
        response_data: Additional data for frontend (e.g., hotel cards)
        remaining_steps: LangGraph internal field for recursion limit (required in 1.x)
    """

    # Message history - add_messages reducer appends new messages to existing list
    messages: Annotated[list[BaseMessage], add_messages]

    # Identifiers
    user_id: str
    chat_id: str

    # Hotel parameters (progressively collected)
    hotel: HotelParams

    # Search results and session
    hotel_results: list[dict[str, Any]] | None
    session_id: str | None

    # Selected hotel (set after user selection)
    selected_hotel: dict[str, Any] | None

    # Response formatting for frontend
    response_type: str
    response_data: dict[str, Any] | None

    # LangGraph internal - tracks remaining recursion steps (required in LangGraph 1.x)
    remaining_steps: int


# ========================
# ITINERARY V2 STATES
# ========================


class ItineraryParams(TypedDict, total=False):
    """Collected itinerary planning parameters (V2).

    All fields are optional (total=False) because they're progressively
    collected during conversation. Replaces the 60+ field
    ItinerarySupervisorState with a simpler schema — the ReAct agent
    handles flow dynamically, no stage tracking needed.
    """

    origin: str | None  # City name (e.g., "Amsterdam")
    origin_iata: str | None  # IATA code (e.g., "AMS")
    origin_name: str | None  # Airport display name
    origin_country: str | None
    destination: str | None  # City OR country label as user wrote it
    destination_iata: str | None  # IATA code (e.g., "NRT")
    destination_name: str | None  # Airport display name
    destination_country: str | None
    # #1127: True when ``destination`` resolves to a country (Montenegro) rather
    # than a city — the side-searches then use ``destination_search_city`` as
    # the FlightLogic input while the itinerary destination stays country-wide.
    destination_is_country: bool | None
    destination_search_city: str | None
    # #1127: dedup key for the hotel side-search; bumps the hotel
    # FlightLogic call when origin lands on a follow-up turn but hotel
    # inputs are unchanged.
    last_hotel_search_key: str | None
    departure_date: str | None  # YYYY-MM-DD
    return_date: str | None  # YYYY-MM-DD
    trip_duration_days: int | None
    adults: int  # Default: 1
    children: int  # Default: 0
    interests: list[str]  # e.g., ["food", "temples", "hiking"]


class ItineraryState(TypedDict):
    """State for the itinerary planning conversation (V2).

    Replaces ItinerarySupervisorState for the V2 dynamic agent.
    The ReAct agent handles flow dynamically — no stage tracking needed.

    Attributes:
        messages: Conversation history (auto-accumulated via add_messages reducer)
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (also used as thread_id for checkpointing)
        itinerary: Collected trip planning parameters
        planning_result: Generated day-by-day itinerary (from save_itinerary tool)
        budget_estimate: Budget breakdown (from save_budget tool)
        response_type: Type hint for frontend rendering
        response_data: Additional data for frontend
        remaining_steps: LangGraph internal field for recursion limit (required in 1.x)
    """

    # Message history - add_messages reducer appends new messages to existing list
    messages: Annotated[list[BaseMessage], add_messages]

    # Identifiers
    user_id: str
    chat_id: str

    # Itinerary parameters (progressively collected)
    itinerary: ItineraryParams

    # Results from tools
    planning_result: dict[str, Any] | None
    budget_estimate: dict[str, Any] | None

    # Response formatting for frontend
    response_type: str
    response_data: dict[str, Any] | None

    # LangGraph internal - tracks remaining recursion steps (required in LangGraph 1.x)
    remaining_steps: int


class SharedTripContext(TypedDict, total=False):
    """Trip data extracted from itinerary agent for cross-agent sharing."""

    origin_iata: str | None
    destination_iata: str | None
    destination: str | None
    destination_country: str | None
    departure_date: str | None
    return_date: str | None
    adults: int
    children: int
    hotel_cities: list[dict[str, str]]  # [{city, country, checkin, checkout}]


class SharedFlightContext(TypedDict, total=False):
    """Flight data extracted from flight agent for cross-agent sharing."""

    origin: str | None
    destination: str | None
    departure_date: str | None
    return_date: str | None
    adults: int
    children: int


class SharedHotelContext(TypedDict, total=False):
    """Hotel data extracted from hotel agent for cross-agent sharing."""

    city: str | None
    country: str | None
    checkin: str | None
    checkout: str | None
    rooms: int
    adults: int
    children: int


class SharedBookingContext(TypedDict, total=False):
    """Booking completion data for cross-agent awareness."""

    booked: bool
    session_id: str | None
    confirmation_id: str | None


class SharedContext(TypedDict, total=False):
    """Typed schema for the unified cross-agent shared_context.

    Accumulated by supervisor from every agent response. Each agent
    writes to its own section; all agents can read from any section.
    """

    trip: SharedTripContext
    flight: SharedFlightContext
    hotel: SharedHotelContext
    flight_booking: SharedBookingContext
    hotel_booking: SharedBookingContext
    hotel_city_index: int  # Tracks which hotel_city is being booked in multi-city


class AgentSignal(TypedDict, total=False):
    """Structured signal from sub-agent to supervisor.

    Replaces simple string signals with rich metadata for auto-chaining,
    cross-agent data transfer, and detour/return patterns.
    See Architecture Doc Section 3.6.
    """

    agent_status: str  # "done" | "failed" | "needs_input" | "hand_back"
    done_reason: (
        str | None
    )  # "booking_complete" | "planning_complete" | "query_answered"
    failed_reason: str | None  # "tool_failures_exceeded" | "api_unavailable"
    reason: str | None  # Hand-back reason (free text for debugging)
    is_detour: bool  # True = side question, auto-return after (Step 10)
    booking_plan: list[str]  # ["flight", "hotel"] — from itinerary on planning_complete


class SupervisorV2State(TypedDict):
    """Unified state for the V2 Supervisor multi-agent system.

    Single source of truth for all routing, cross-agent context, and session
    management. All agents read from and write to shared_context, ensuring
    trip data, booking results, and collected params flow between agents
    regardless of how transitions occur (auto-chain, hand-back, or classify).

    Attributes:
        messages: Conversation history (auto-accumulated via add_messages reducer)
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (also used as thread_id for checkpointing)
        user_email: Optional user email for tracing
        active_agent: Which sub-agent is currently handling the conversation
        previous_agent: Agent that handed back (for context injection)
        current_intent: Last classified intent
        agent_signal: Structured signal from sub-agent (AgentSignal dict or None)
        agent_response: Response dict from sub-agent invocation
        task_queue: Multi-intent task queue (FIFO, max 5)
        auto_chain: Remaining agents in auto-chain from itinerary booking_plan
        shared_context: Unified cross-agent memory — accumulated from all agents.
            Structure:
            {
                "trip": {origin, destination, dates, passengers, hotel_cities},
                "flight": {origin, destination, dates, adults, ...},
                "hotel": {city, country, checkin, checkout, rooms, adults, ...},
                "flight_booking": {booked, confirmation_id, details},
                "hotel_booking": {booked, confirmation_id, details},
            }
        detour_return: True when current dispatch is a detour (auto-return after)
        chain_responses: Accumulated agent responses during auto-chain dispatch.
            When "book everything" triggers flight+hotel, both responses are collected
            so ChatService can store each as a separate bot message.
        pending_needs_input_agent: Agent that returned NEEDS_INPUT during auto-chain
            (e.g. flight asked for origin while hotel ran in parallel). Restored as
            active_agent once the auto-chain completes so the next user message
            routes back to the waiting agent.
        remaining_steps: LangGraph internal field for recursion limit
    """

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    chat_id: str
    user_email: str | None
    active_agent: str | None
    previous_agent: str | None
    current_intent: str | None
    agent_signal: AgentSignal | None
    agent_response: dict[str, Any] | None
    task_queue: list[dict[str, Any]]
    auto_chain: list[str]
    shared_context: dict[str, Any]
    chain_responses: list[dict[str, Any]]
    detour_return: bool
    pending_needs_input_agent: str | None
    hand_back_count: (
        int  # Consecutive hand-backs from same agent (reset on successful dispatch)
    )
    agent_start_index: (
        int  # Message index when current agent became active (for Mode 2 filtering)
    )
    detour_origin_index: (
        int  # Saved agent_start_index before detour (restored on return)
    )
    classification_confidence: (
        float  # Tier indicator: 1.0=fast-path, 0.9=LLM-classified, 0.5=fallback
    )
    pending_task_context: (
        str  # Free-text context from dequeued task (passed directly to agent LLM)
    )
    checkpoint_version: (
        int  # Schema version — cleared on mismatch (see SV2_CHECKPOINT_VERSION)
    )
    remaining_steps: int
    # ---- AI-CHAT-010 backend-error-resilience telemetry ----
    error_count: int  # Lifetime error count for this chat session (never decremented).
    error_count_since_success: (
        int
        # Consecutive errors with no successful turn between them. Reset to 0
        # on every successful turn; on >=3 the supervisor offers a soft reset
        # and fires a Slack alert via SLACK_WEBHOOK_URL.
    )
    last_error_classes: (
        list[str]
        # Rolling buffer of the most recent ErrorClass values (max 3), used
        # by the Slack alert body to show the failure pattern. FIFO; oldest
        # dropped when length exceeds 3.
    )
    # ---- AI-CHAT-013 capability-disclosure routing ----
    capability_disclosure_id: (
        str | None
        # Set by capability_check_node when a known limitation matches the
        # user's message (AI-CHAT-013). Drives the conditional edge from
        # capability_check to END, bypassing route_or_classify. None on
        # the normal path.
    )


__all__ = [
    "AgentSignal",
    "FlightParams",
    "FlightState",
    "HotelParams",
    "HotelState",
    "ItineraryParams",
    "ItineraryState",
    "SharedBookingContext",
    "SharedContext",
    "SharedFlightContext",
    "SharedHotelContext",
    "SharedTripContext",
    "SupervisorV2State",
]
