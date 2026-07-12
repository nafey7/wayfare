# Supervisor System Architecture

**Version**: 1.0
**Last Updated**: January 2026
**Author**: Voya AI Team
**Purpose**: Multi-stage trip planning and booking orchestration

---

## Table of Contents

- [Overview](#overview)
- [How Backend Routes to Supervisor](#how-backend-routes-to-supervisor)
- [System Architecture](#system-architecture)
- [Agents in the Supervisor (High-Level)](#agents-in-the-supervisor-high-level)
- [The 5-Stage Flow](#the-5-stage-flow)
- [Agent Implementation Details](#agent-implementation-details)
- [Routing Logic (Code)](#routing-logic-code)
- [State Management](#state-management)
- [Tools Used](#tools-used)
- [Complete Flow Example](#complete-flow-example)
- [Code Locations](#code-locations)

---

## Overview

The **Supervisor System** is a LangGraph-based orchestrator that manages complex, multi-stage trip planning workflows. Unlike the simple Router system (for quick queries), the Supervisor handles end-to-end itinerary creation with:

- ✅ Progressive data collection across conversation turns
- ✅ 5-stage workflow with automatic progression
- ✅ Persistent state management via MongoDB
- ✅ Specialized sub-agents for planning, flights, and hotels
- ✅ Human-in-the-loop for disambiguation
- ✅ On-demand search (flights/hotels searched when needed, not pre-cached)

**Entry Point**: `/api/itinerary/create`

**Use Case**: User says "I want to plan a ski trip to Chamonix in February" → System guides through data collection, itinerary generation, budget calculation, and booking.

---

## How Backend Routes to Supervisor

### Request Flow: Frontend → API → Supervisor Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST FLOW DIAGRAM                         │
└─────────────────────────────────────────────────────────────────┘

    Frontend (React)
         │
         │ POST /api/itinerary/create
         │ {
         │   "message": "Plan a ski trip to Chamonix",
         │   "user_id": "user_123",
         │   "chat_id": "chat_abc" (optional)
         │ }
         ↓
    ┌─────────────────────────────────────┐
    │  FastAPI Backend                    │
    │  Route: POST /api/itinerary/create  │
    └─────────────────┬───────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────────┐
    │  ChatService.process_message()              │
    │  Location: app/domains/chat/service.py      │
    │                                             │
    │  1. Authenticate user (JWT validation)      │
    │  2. Get or create chat_id                   │
    │  3. Detect if itinerary mode requested      │
    └─────────────────┬───────────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────────┐
    │  invoke_supervisor_graph()                  │
    │  Location: app/ai/graph/supervisor.py       │
    │                                             │
    │  1. Load existing state from MongoDB        │
    │     (via LangGraph checkpointer)            │
    │  2. Prepare input state                     │
    │  3. Invoke LangGraph supervisor             │
    └─────────────────┬───────────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────────┐
    │  LangGraph Supervisor Graph                 │
    │  Compiled StateGraph                        │
    │                                             │
    │  → supervisor_node (routing)                │
    │  → planning_agent / flight / hotel          │
    │  → stage_progression_node (auto-advance)    │
    └─────────────────┬───────────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────────┐
    │  Response Formatting                        │
    │                                             │
    │  1. Extract AI message from graph result    │
    │  2. Determine response_type                 │
    │  3. Format for frontend (JSON)              │
    └─────────────────┬───────────────────────────┘
                      │
                      ↓
    ┌─────────────────────────────────────────────┐
    │  Response to Frontend                       │
    │  {                                          │
    │    "message": "Got it! Planning...",        │
    │    "type": "itinerary_display",             │
    │    "chat_id": "chat_abc",                   │
    │    "stage": "ROUTE_REFINEMENT",             │
    │    "metadata": {...}                        │
    │  }                                          │
    └─────────────────────────────────────────────┘
```

### Entry Point Code

**API Route** (`app/api/itinerary/itinerary.py`):
```python
@router.post("/create", response_model=ChatResponse)
async def create_itinerary(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new itinerary using the supervisor system.

    This endpoint initiates the 5-stage trip planning flow.
    """

    # Delegate to ChatService
    response = await ChatService.process_message(
        user_id=str(current_user.id),
        message=request.message,
        chat_id=request.chat_id,
        use_supervisor=True  # Force supervisor mode
    )

    return response
```

**ChatService** (`app/domains/chat/service.py`):
```python
async def process_message(
    user_id: str,
    message: str,
    chat_id: str | None = None,
    use_supervisor: bool = False
) -> dict:
    """
    Process user message and route to appropriate system.
    """

    # Create or retrieve chat
    if not chat_id:
        chat = await create_chat(user_id, title="Trip Planning")
        chat_id = str(chat.id)

    # Route to supervisor if requested or detected
    if use_supervisor or _is_itinerary_intent(message):
        response = await invoke_supervisor_graph(
            message=message,
            user_id=user_id,
            chat_id=chat_id,
            user_email=current_user.email
        )
    else:
        # Use simple router for quick queries
        response = await invoke_router_graph(...)

    return response
```

**Supervisor Invocation** (`app/ai/graph/supervisor.py`):
```python
async def invoke_supervisor_graph(
    message: str,
    user_id: str,
    chat_id: str,
    user_email: str | None = None
) -> dict:
    """
    Main entry point to supervisor system.

    Loads existing state from MongoDB checkpoint and continues
    the multi-stage planning workflow.
    """

    # 1. Get compiled supervisor graph (singleton)
    supervisor_graph = get_supervisor_graph()

    # 2. Build config for checkpointer
    config = {
        "configurable": {"thread_id": chat_id},
        "recursion_limit": 10
    }

    # 3. Check for existing state
    existing_state = supervisor_graph.get_state(config)

    # 4. Prepare input (merged with checkpoint)
    input_state = {
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "chat_id": chat_id,
        "stage": existing_state.values.get("stage", StageEnum.INITIAL_VISION)
    }

    # 5. Invoke graph
    result = await supervisor_graph.ainvoke(input_state, config)

    # 6. Format response for frontend
    return format_supervisor_response(result)
```

### Key Points

1. **Single Entry Point**: `/api/itinerary/create` triggers supervisor mode
2. **Automatic State Loading**: LangGraph checkpointer loads previous state from MongoDB using `thread_id=chat_id`
3. **Stateless API**: API layer doesn't manage state - LangGraph handles it
4. **Progressive Conversations**: Each message builds on previous state
5. **Isolated Threads**: Supervisor uses `chat_id`, sub-agents use `chat_id_flight`, `chat_id_hotel`

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     SUPERVISOR SYSTEM                          │
│                   (5-Stage Orchestrator)                       │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ User Message
                              ↓
                    ┌─────────────────┐
                    │ supervisor_node │  ← Master Routing Logic
                    │   (Orchestrator) │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ↓                   ↓                   ↓
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Planning Agent │  │ Flight Booking │  │ Hotel Booking  │
│                │  │     Agent      │  │     Agent      │
│ (Structured    │  │  (ReAct via    │  │  (ReAct via    │
│   Chains)      │  │  delegation)   │  │  delegation)   │
└────────┬───────┘  └────────┬───────┘  └────────┬───────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ↓
                ┌────────────────────────┐
                │   stage_progression    │  ← Auto-advance logic
                │       _node            │
                └────────────────────────┘
                             │
                             ↓
                    ┌────────────────┐
                    │  MongoDB State │
                    │  Checkpointer  │
                    └────────────────┘
```

---

## Agents in the Supervisor (High-Level)

The Supervisor System orchestrates **5 key components** that work together to guide users through trip planning:

### 1. supervisor_node - The Master Controller

**What It Does**:
Think of this as the "air traffic controller" of the system. It looks at where the user is in their trip planning journey (which stage) and decides what needs to happen next.

**Key Responsibilities**:
- **Analyze Current Situation**: Checks which stage we're in and what data we have
- **Make Routing Decisions**: Decides which specialized agent should handle the next step
- **Handle User Commands**: Recognizes when users say "back", "reset", or "stop"
- **Coordinate Results**: Takes output from sub-agents and integrates it into the master plan

**How It Works**:
- Uses pure Python logic (no AI) - it's deterministic and predictable
- Examines the current stage and missing data
- Routes to Planning Agent for data/itinerary/budget
- Routes to Booking Agents when user is ready to book

**Example**: User is in INITIAL_VISION stage and hasn't provided destination yet → Routes to Planning Agent to ask for destination.

---

### 2. Planning Agent - The Trip Planner

**What It Does**:
This is the "smart assistant" that extracts information from conversations, generates itineraries, and calculates budgets. It works in three different modes depending on which stage it's called in.

**Key Responsibilities**:
- **INITIAL_VISION Mode**: Understand what the user wants
  - Extract travel details from natural conversation
  - Find airports for cities mentioned
  - Parse dates like "next Friday" into actual dates
  - Handle cases where clarification is needed (e.g., "London has 3 airports - which one?")

- **ROUTE_REFINEMENT Mode**: Create the itinerary
  - Generate day-by-day travel plan
  - Suggest activities based on user interests (skiing, culture, food, etc.)
  - Include local tips and highlights
  - Make it feel like a real travel agent created it

- **BUDGET_ESTIMATION Mode**: Calculate costs
  - Estimate flight prices based on route
  - Calculate hotel costs (nights × average rate)
  - Add activity/food/transport costs
  - Present clear breakdown

**How It Works**:
- Uses **Structured Chains** (not ReAct) for reliability
- Makes single, focused LLM calls with specific output formats
- Validates results using Pydantic schemas (type-safe)
- Faster and more predictable than multi-turn reasoning

**Why This Approach?**
When extracting data or calculating budgets, you want consistency. Structured chains guarantee the output format, making it reliable for downstream processing.

---

### 3. Flight Booking Agent - The Flight Specialist

**What It Does**:
This agent takes over when the user is ready to book flights. It has all the trip details from the Planning Agent, so it can search immediately.

**Key Responsibilities**:
- **Pre-filled Search**: Uses dates, airports, passenger count from planning stage
- **Delegate to Flight Graph**: Hands off to the specialized flight ReAct agent
- **Present Options**: Shows curated results (cheapest, fastest, best value)
- **Track Completion**: Knows when flight booking is done

**How It Works**:
- Acts as a "bridge" between supervisor and flight_graph
- Extracts relevant parameters from supervisor state
- Creates isolated conversation thread for flight booking
- Returns results back to supervisor for user

**The Delegation Pattern**:
1. Supervisor says "book flights"
2. Flight Booking Agent prepares: origin=CDG, destination=GVA, dates, passengers
3. Calls flight_graph with pre-filled params
4. Flight graph searches and returns results
5. Flight Booking Agent tells supervisor "done, here are the results"

**Why Separate Thread?**
Uses `chat_id_flight` instead of `chat_id` to keep flight conversation separate from main planning conversation. Prevents confusion and state conflicts.

---

### 4. Hotel Booking Agent - The Accommodation Specialist

**What It Does**:
Similar to Flight Booking Agent, but for hotels. Takes trip details and finds accommodation options.

**Key Responsibilities**:
- **Pre-filled Search**: Uses destination city, check-in/out dates from planning
- **Delegate to Hotel Graph**: Hands off to specialized hotel ReAct agent
- **Present Options**: Shows curated results (best value, cheapest, highest rated)
- **Handle Selection**: Manages when user picks a hotel ("book 2")
- **Generate Booking Link**: Creates redirect URL to complete reservation

**How It Works**:
- Similar bridge pattern as Flight Booking Agent
- Extracts city, country, dates from supervisor
- Creates isolated thread (`chat_id_hotel`)
- Handles multi-turn flow (search → results → selection → redirect)

**Multi-Step Flow**:
1. Search hotels with pre-filled params
2. Show 3 options to user
3. User says "book 2"
4. Generate booking redirect URL
5. Return to supervisor with completion status

---

### 5. stage_progression_node - The Stage Advancer

**What It Does**:
This is the "checkpoint validator" that decides when to move forward in the 5-stage journey. It's like a gate that only opens when requirements are met.

**Key Responsibilities**:
- **Validate Requirements**: Check if stage is complete (all data collected?)
- **Detect Triggers**: Listen for user saying "yes", "proceed", "book"
- **Auto-Advance**: Move to next stage when ready
- **Pause When Needed**: Wait for user input when not ready

**How It Works**:
- Pure logic/rules (no AI)
- Checks stage-specific requirements
- Listens for stage-specific trigger words
- Sets `remaining_steps=0` to pause when waiting

**Example Decision Flow**:
```
INITIAL_VISION stage:
├─ Check: Do we have origin, destination, dates?
├─ Yes? → Advance to ROUTE_REFINEMENT
└─ No? → Stay in INITIAL_VISION, keep collecting

ROUTE_REFINEMENT stage:
├─ Check: Do we have itinerary?
├─ Check: Did user say "yes" or "check availability"?
├─ Both Yes? → Advance to BUDGET_ESTIMATION
└─ No? → Wait for user confirmation

BOOKING_HANDOFF stage:
├─ Check: Did user say "flight", "hotel", or "both"?
├─ Check: Are requested bookings complete?
├─ Both Yes? → End conversation
└─ No? → Continue booking flow
```

**Why Separate Node?**
Keeps routing logic (supervisor_node) separate from progression logic (stage_progression_node). Clean separation of concerns.

---

### How They Work Together

```
User: "Plan a ski trip to Chamonix in February"
                    ↓
           ┌────────────────┐
           │ supervisor_node│
           │ "INITIAL_VISION, no data yet"
           │ → Route to Planning Agent
           └────────┬───────┘
                    ↓
         ┌──────────────────┐
         │  Planning Agent   │
         │  Extract: destination=Chamonix,
         │           dates=February,
         │           interests=skiing
         └──────────┬─────────┘
                    ↓
         ┌──────────────────────┐
         │ stage_progression_node│
         │ Check: origin✅ destination✅ dates✅
         │ → Advance to ROUTE_REFINEMENT
         └──────────┬───────────┘
                    ↓
           ┌────────────────┐
           │ supervisor_node│
           │ "ROUTE_REFINEMENT, need itinerary"
           │ → Route to Planning Agent
           └────────┬───────┘
                    ↓
         ┌──────────────────┐
         │  Planning Agent   │
         │  Generate day-by-day itinerary
         └──────────┬─────────┘
                    ↓
         (Continue through stages...)
```

---

## The 5-Stage Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 1: INITIAL_VISION                                         │
│  Goal: Collect trip information                                  │
├──────────────────────────────────────────────────────────────────┤
│  Active Agent: Planning Agent                                    │
│                                                                  │
│  Requirements to Complete:                                       │
│  ✓ origin, destination (city names)                             │
│  ✓ origin_iata, destination_iata (IATA codes)                   │
│  ✓ departure_date, return_date (YYYY-MM-DD)                     │
│                                                                  │
│  Actions:                                                        │
│  1. Extract trip info from user messages                         │
│  2. Resolve airports using resolve_airport tool                  │
│  3. Parse dates using parse_dates tool                           │
│  4. Handle disambiguation if needed (multiple airports)          │
│                                                                  │
│  Auto-Advance: When all requirements met                         │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 2: ROUTE_REFINEMENT                                       │
│  Goal: Generate trip itinerary                                   │
├──────────────────────────────────────────────────────────────────┤
│  Active Agent: Planning Agent                                    │
│                                                                  │
│  Requirements to Complete:                                       │
│  ✓ All INITIAL_VISION data                                      │
│  ✓ planning_result (generated itinerary)                        │
│                                                                  │
│  Actions:                                                        │
│  1. Generate day-by-day itinerary                                │
│  2. Include activities based on interests                        │
│  3. Add highlights and local tips                                │
│  4. Format for frontend display                                  │
│                                                                  │
│  User Trigger: "yes", "check", "availability", "proceed"        │
│  Auto-Advance: After user confirms                               │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3: AVAILABILITY_CHECK (DEPRECATED - SKIPPED)             │
│  Goal: Pre-search flights and hotels                             │
├──────────────────────────────────────────────────────────────────┤
│  Status: SKIPPED in normal flow                                  │
│                                                                  │
│  Why Skipped:                                                    │
│  - Slows planning with unnecessary API calls                     │
│  - Search results become stale by booking time                   │
│  - Wastes API quota                                              │
│                                                                  │
│  Solution: Search ON-DEMAND in BOOKING_HANDOFF                   │
│                                                                  │
│  Legacy: Only used if user explicitly requests during planning   │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 4: BUDGET_ESTIMATION                                      │
│  Goal: Calculate trip costs                                      │
├──────────────────────────────────────────────────────────────────┤
│  Active Agent: Planning Agent                                    │
│                                                                  │
│  Requirements to Complete:                                       │
│  ✓ budget_estimate (calculated breakdown)                       │
│                                                                  │
│  Actions:                                                        │
│  1. Calculate costs by category:                                 │
│     • Flights (estimated based on route/dates)                   │
│     • Hotels (per night × number of nights)                      │
│     • Activities/experiences                                     │
│     • Food & dining                                              │
│     • Local transport                                            │
│  2. Provide total estimate                                       │
│                                                                  │
│  User Trigger: "budget", "cost", "price", "book"                │
│  Auto-Advance: When trigger detected + budget exists             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 5: BOOKING_HANDOFF                                        │
│  Goal: Execute flight and/or hotel bookings                      │
├──────────────────────────────────────────────────────────────────┤
│  Active Agents: Flight Booking Agent, Hotel Booking Agent        │
│                                                                  │
│  Intent Detection: Parse user message                            │
│  • "yes", "1", "flight" → Flight Booking Agent                   │
│  • "2", "hotel", "accommodation" → Hotel Booking Agent           │
│  • "3", "both", "everything" → Both (sequential)                 │
│                                                                  │
│  Flow for "both":                                                │
│  1. Invoke Flight Booking Agent                                  │
│     - Search flights with pre-populated params                   │
│     - Return curated results (cheapest, fastest, best value)     │
│     - Set flight_booking_complete = True                         │
│  2. Invoke Hotel Booking Agent                                   │
│     - Search hotels with pre-populated params                    │
│     - Return curated results (best value, cheapest, highest)     │
│     - User selects hotel → Generate redirect URL                 │
│     - Set hotel_booking_complete = True                          │
│                                                                  │
│  Note: Search happens ON-DEMAND here (not pre-searched)          │
│                                                                  │
│  End Condition: All requested bookings complete                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Implementation Details

Now that you understand **what** each agent does, let's dive into **how** they're implemented in code.

### 1. supervisor_node - Implementation

**Location**: `backend_python/app/ai/graph/supervisor.py`

This is the core routing function that makes all decisions about which agent to invoke.

```python
def supervisor_node(state: ItinerarySupervisorState) -> dict:
    """
    Master routing logic - decides which agent to invoke.
    """

    # ═══════════════════════════════════════════════════════
    # GLOBAL INTERCEPTS (any stage)
    # ═══════════════════════════════════════════════════════

    if "back" in message or "reset" in message or "stop" in message:
        return {
            "stage": StageEnum.BUDGET_ESTIMATION,
            "booking_intent": None
        }

    if "budget" in message and stage == StageEnum.BOOKING_HANDOFF:
        return {"stage": StageEnum.BUDGET_ESTIMATION}

    # ═══════════════════════════════════════════════════════
    # STAGE-SPECIFIC ROUTING
    # ═══════════════════════════════════════════════════════

    current_stage = state.get("stage")

    # ─────────────────────────────────────────────────────
    # STAGE 1: INITIAL_VISION
    # ─────────────────────────────────────────────────────
    if current_stage == StageEnum.INITIAL_VISION:
        # Check if all required data collected
        required = [
            "origin", "destination",
            "origin_iata", "destination_iata",
            "departure_date", "return_date"
        ]

        missing = [f for f in required if not state.get(f)]

        if missing:
            # Data incomplete - invoke Planning Agent
            return {"active_agent": "planning"}
        else:
            # Data complete - ready for progression
            return {"active_agent": None}

    # ─────────────────────────────────────────────────────
    # STAGE 2: ROUTE_REFINEMENT
    # ─────────────────────────────────────────────────────
    elif current_stage == StageEnum.ROUTE_REFINEMENT:
        if not state.get("planning_result"):
            # No itinerary - invoke Planning Agent
            return {"active_agent": "planning"}
        else:
            # Itinerary exists - wait for user trigger
            return {"active_agent": None}

    # ─────────────────────────────────────────────────────
    # STAGE 3: AVAILABILITY_CHECK (Skipped)
    # ─────────────────────────────────────────────────────
    elif current_stage == StageEnum.AVAILABILITY_CHECK:
        # This stage is deprecated - auto-skip
        return {"active_agent": None}

    # ─────────────────────────────────────────────────────
    # STAGE 4: BUDGET_ESTIMATION
    # ─────────────────────────────────────────────────────
    elif current_stage == StageEnum.BUDGET_ESTIMATION:
        if not state.get("budget_estimate"):
            # No budget - invoke Planning Agent
            return {"active_agent": "planning"}
        else:
            # Budget exists - wait for booking intent
            return {"active_agent": None}

    # ─────────────────────────────────────────────────────
    # STAGE 5: BOOKING_HANDOFF
    # ─────────────────────────────────────────────────────
    elif current_stage == StageEnum.BOOKING_HANDOFF:
        # Parse booking intent from user message
        booking_intent = parse_booking_intent(message)

        if booking_intent == "flight":
            return {
                "active_agent": "flight_booking",
                "booking_intent": "flight"
            }

        elif booking_intent == "hotel":
            return {
                "active_agent": "hotel_booking",
                "booking_intent": "hotel"
            }

        elif booking_intent == "both":
            # Sequential: flights first, then hotels
            flight_done = state.get("flight_booking_complete", False)
            hotel_done = state.get("hotel_booking_complete", False)

            if not flight_done:
                return {
                    "active_agent": "flight_booking",
                    "booking_intent": "both"
                }
            elif not hotel_done:
                return {
                    "active_agent": "hotel_booking",
                    "booking_intent": "both"
                }
            else:
                # All bookings complete
                return {"active_agent": None}

        else:
            # Intent unclear - ask user
            return {"active_agent": "booking_intent_collector"}

    return {"active_agent": None}
```

---

### Booking Intent Recognition

```python
def parse_booking_intent(message: str) -> str | None:
    """
    Parse user message to determine booking intent.
    """

    msg = message.lower()

    # Flight patterns
    flight_patterns = [
        "yes", "yeah", "ok", "sure",
        "1", "flight", "flights", "fly",
        "cheapest", "fastest", "best value",
        "option 1", "first option"
    ]

    # Hotel patterns
    hotel_patterns = [
        "2", "hotel", "hotels", "room", "rooms",
        "accommodation", "stay", "lodging",
        "option 2", "second option"
    ]

    # Both patterns
    both_patterns = [
        "3", "both", "everything", "all",
        "flight and hotel", "flights and hotels",
        "option 3", "third option"
    ]

    if any(p in msg for p in both_patterns):
        return "both"
    elif any(p in msg for p in hotel_patterns):
        return "hotel"
    elif any(p in msg for p in flight_patterns):
        return "flight"

    return None  # Unclear intent
```

---

## State Management

### ItinerarySupervisorState Schema

```python
class ItinerarySupervisorState(TypedDict):
    """
    Master state for the supervisor system.
    Persisted to MongoDB via LangGraph checkpointer.
    """

    # ═══════════════════════════════════════════════════════
    # Message History
    # ═══════════════════════════════════════════════════════
    messages: Annotated[list[BaseMessage], add_messages]
    # Auto-managed by LangGraph's add_messages reducer
    # Appends new messages, preserves history

    # ═══════════════════════════════════════════════════════
    # User Context
    # ═══════════════════════════════════════════════════════
    user_id: str              # Authenticated user ID
    chat_id: str              # Conversation ID (thread_id for checkpointer)

    # ═══════════════════════════════════════════════════════
    # Stage Tracking
    # ═══════════════════════════════════════════════════════
    stage: StageEnum          # Current stage in 5-stage flow
                              # INITIAL_VISION | ROUTE_REFINEMENT |
                              # AVAILABILITY_CHECK | BUDGET_ESTIMATION |
                              # BOOKING_HANDOFF

    # ═══════════════════════════════════════════════════════
    # Travel Parameters (Progressively Collected)
    # ═══════════════════════════════════════════════════════
    origin: str | None                    # City name: "Paris"
    origin_iata: str | None               # Airport code: "CDG"
    origin_name: str | None               # Full name: "Paris Charles de Gaulle"
    origin_country: str | None            # "France"

    destination: str | None               # "London"
    destination_iata: str | None          # "LHR"
    destination_name: str | None          # "London Heathrow"
    destination_country: str | None       # "United Kingdom"

    departure_date: str | None            # "2026-05-06"
    return_date: str | None               # "2026-05-13"

    adults: int                           # 1+ passengers
    children: int                         # 0+ children
    interests: list[str]                  # ["skiing", "culture", "food"]

    # ═══════════════════════════════════════════════════════
    # Sub-Agent Results
    # ═══════════════════════════════════════════════════════
    planning_result: dict | None          # Itinerary from Planning Agent
    flight_result: dict | None            # Flight search results
    hotel_result: dict | None             # Hotel search results
    budget_estimate: dict | None          # Budget breakdown

    # ═══════════════════════════════════════════════════════
    # Booking State (BOOKING_HANDOFF)
    # ═══════════════════════════════════════════════════════
    booking_intent: str | None            # "flight" | "hotel" | "both"
    flight_booking_complete: bool         # Track completion
    hotel_booking_complete: bool
    flight_booking_result: dict | None    # Final booking data
    hotel_booking_result: dict | None

    # ═══════════════════════════════════════════════════════
    # Disambiguation/Clarification
    # ═══════════════════════════════════════════════════════
    needs_clarification: bool             # Flag for human-in-the-loop
    clarification_question: str | None    # Question to ask user
    pending_field: str | None             # Field needing clarification
    disambiguation_options: list[dict]    # Options to present
    user_clarification: str | None        # User's response

    # ═══════════════════════════════════════════════════════
    # Frontend Communication
    # ═══════════════════════════════════════════════════════
    response_type: str                    # "message" | "flight_search_results" |
                                          # "hotel_search_results" | "itinerary_display" |
                                          # "flight_booking_redirect" | etc.
    response_data: dict | None            # Additional data for UI

    # ═══════════════════════════════════════════════════════
    # LangGraph Internal
    # ═══════════════════════════════════════════════════════
    remaining_steps: int                  # Recursion tracking (max 25)
    active_agent: str | None              # Current agent being invoked
```

---

### Checkpointing Strategy

**MongoDB Checkpointer** via `MongoDBSaver`:

```
Component             Thread ID              Database/Collection
────────────────────────────────────────────────────────────────
Supervisor            {chat_id}              voya/checkpoints
Flight Graph          {chat_id}_flight       voya/checkpoints
Hotel Graph           {chat_id}_hotel        voya/checkpoints
```

**Critical**: Sub-agents use **isolated thread_ids** to prevent conflicts.

**Example**:
```python
# ❌ WRONG - Overwrites supervisor state
await invoke_flight_graph(chat_id="abc123", ...)

# ✅ CORRECT - Isolated checkpoint
await invoke_flight_graph(chat_id="abc123_flight", ...)
```

---

## Tools Used

The Supervisor System uses **6 tools** (via sub-agents):

### Planning Agent Tools

1. **resolve_airport(query: str) → dict**
   - Converts city/airport names to IATA codes
   - Handles disambiguation (multiple airports)
   - Data: mwgg/Airports (29K+ airports)

2. **parse_dates(text: str) → dict**
   - Natural language → YYYY-MM-DD
   - Examples: "tomorrow", "next Friday", "Dec 20-25"

### Flight Graph Tools

3. **resolve_airport** (same as above)
4. **parse_dates** (same as above)
5. **search_flights(...) → dict**
   - Searches FlightLogic API
   - Returns curated results (cheapest, fastest, best value)

### Hotel Graph Tools

6. **resolve_city(city: str) → dict**
   - Resolves city names to city/country pairs
   - Uses Google Geocoding API

7. **parse_dates** (same as above)

8. **search_hotels(...) → dict**
   - Searches FlightLogic Hotel API
   - Returns curated results (best value, cheapest, highest rated)

9. **select_hotel(...) → dict**
   - Generates booking redirect URL
   - Handles selection patterns ("book 1", "cheapest", etc.)

---

## Complete Flow Example

### User Journey: Ski Trip to Chamonix

```
═══════════════════════════════════════════════════════════════
STAGE 1: INITIAL_VISION
═══════════════════════════════════════════════════════════════

User: "I want to plan a ski trip to Chamonix in February"

1. NEW SESSION CREATED
   ├─ chat_id: "trip_abc123"
   ├─ user_id: "user_456"
   └─ stage: INITIAL_VISION

2. supervisor_node: Route to Planning Agent
   ├─ Check requirements: origin ❌, destination ❌, dates ❌
   └─ active_agent: "planning"

3. Planning Agent: Extract trip info
   ├─ LLM structured output:
   │  └─ {destination: "Chamonix", departure_date: "February",
   │      interests: ["skiing"]}
   │
   ├─ resolve_airport("Chamonix"):
   │  └─ {status: "no_own_airport",
   │      nearby: [{iata: "GVA", name: "Geneva"}]}
   │
   └─ Set: needs_clarification=True

4. ask_user_node: Interrupt (Human-in-the-Loop)
   └─ Question: "Chamonix doesn't have an airport. Use Geneva (GVA)?"

5. Save checkpoint to MongoDB
   └─ State paused, waiting for user response

═══════════════════════════════════════════════════════════════

User: "Yes, Geneva is fine"

6. Resume graph execution
   ├─ Load checkpoint from MongoDB
   ├─ Continue from interruption point
   └─ Update: destination_iata="GVA", needs_clarification=False

7. Planning Agent: Continue extraction
   ├─ resolve_airport("Paris") [inferred from user profile]
   │  └─ {iata: "CDG", name: "Paris Charles de Gaulle"}
   │
   ├─ parse_dates("February")
   │  └─ {departure_date: "2026-02-07", return_date: "2026-02-14"}
   │
   └─ State complete:
      ├─ origin_iata="CDG", origin_name="Paris Charles de Gaulle"
      ├─ destination_iata="GVA", destination_name="Geneva"
      └─ departure_date="2026-02-07", return_date="2026-02-14"

8. stage_progression: Auto-advance
   └─ All requirements met → stage: ROUTE_REFINEMENT

9. Return to user:
   "Got it! Planning your ski trip from Paris (CDG) to Geneva (GVA),
    February 7-14. Let me create your itinerary."

═══════════════════════════════════════════════════════════════
STAGE 2: ROUTE_REFINEMENT
═══════════════════════════════════════════════════════════════

User: "Yes, create the itinerary"

10. supervisor_node: Route to Planning Agent
    └─ planning_result missing → active_agent: "planning"

11. Planning Agent: Generate itinerary
    ├─ LLM structured output with day-by-day plan:
    │  Day 1: Arrive Geneva, transfer to Chamonix (45 min), settle in
    │  Day 2: Ski at Grands Montets (expert terrain)
    │  Day 3: Ski at Brévent-Flégère (amazing views)
    │  Day 4: Rest day - explore Chamonix town, visit Aiguille du Midi
    │  Day 5-6: More skiing at various resorts
    │  Day 7: Depart Chamonix, return to Geneva
    │
    └─ planning_result saved to state

12. stage_progression: Auto-advance
    └─ stage: BUDGET_ESTIMATION

13. Return itinerary to user:
    ├─ response_type: "itinerary_display"
    └─ Frontend shows day-by-day cards with activities

═══════════════════════════════════════════════════════════════
STAGE 4: BUDGET_ESTIMATION
═══════════════════════════════════════════════════════════════

User: "What will this cost?"

14. supervisor_node: Route to Planning Agent
    └─ budget_estimate missing → active_agent: "planning"

15. Planning Agent: Calculate budget
    └─ {
        flights: 300,           # Estimated Paris-Geneva return
        hotels: 1050,           # 150/night × 7 nights
        activities: 400,        # Lift passes, ski rentals
        food: 350,              # 50/day × 7 days
        transport: 100          # Airport transfers
        total: 2200
    }

16. stage_progression: Auto-advance
    └─ stage: BOOKING_HANDOFF

17. Return budget breakdown:
    "Budget estimate for your trip:
     • Flights: $300
     • Hotels: $1,050 (7 nights)
     • Activities: $400
     • Food & Dining: $350
     • Transport: $100
     Total: $2,200

     Ready to book? Say 'book flights', 'book hotels', or 'book both'."

═══════════════════════════════════════════════════════════════
STAGE 5: BOOKING_HANDOFF
═══════════════════════════════════════════════════════════════

User: "Book both flights and hotels"

18. supervisor_node: Parse intent
    └─ booking_intent="both", active_agent="flight_booking"

19. call_flight_booking_agent:
    ├─ Pre-populate flight_params:
    │  {origin: "CDG", destination: "GVA",
    │   departure_date: "2026-02-07", return_date: "2026-02-14",
    │   adults: 1}
    │
    ├─ Invoke flight_graph(chat_id="trip_abc123_flight")
    │
    │  Flight Graph (ReAct):
    │  ├─ Params pre-filled → Search immediately
    │  ├─ Call: search_flights(CDG, GVA, ...) → Results
    │  └─ Return: 3 curated flights (cheapest, fastest, best value)
    │
    └─ Merge results into supervisor state
       └─ flight_booking_complete=True

20. Return flight results to user:
    ├─ response_type: "flight_search_results"
    └─ Frontend displays flight cards

═══════════════════════════════════════════════════════════════

User: "Show me hotels now"

21. supervisor_node: booking_intent="both", flight_complete=True
    └─ active_agent="hotel_booking"

22. call_hotel_booking_agent:
    ├─ Pre-populate hotel_params:
    │  {city: "Chamonix", country: "France",
    │   checkin: "2026-02-07", checkout: "2026-02-14",
    │   adults: 1}
    │
    ├─ Invoke hotel_graph(chat_id="trip_abc123_hotel")
    │
    │  Hotel Graph (ReAct):
    │  ├─ Params pre-filled → Search immediately
    │  ├─ Call: search_hotels(Chamonix, France, ...) → Results
    │  └─ Return: 3 curated hotels
    │
    └─ Return hotel cards to user

23. Return hotel results:
    ├─ response_type: "hotel_search_results"
    └─ Frontend displays hotel cards:
       1. Best Value ⭐: Alpine Lodge ($120/night)
       2. Cheapest 💵: Mountain Hostel ($65/night)
       3. Highest Rated 🏆: Grand Hotel ($280/night)

═══════════════════════════════════════════════════════════════

User: "book 2" (selects cheapest hotel)

24. Hotel Graph (ReAct):
    ├─ LLM: "User said 'book 2' - call select_hotel"
    ├─ Call: select_hotel(
    │     selection="book 2",
    │     hotels=[...from search...],
    │     session_id="HOTEL_SESSION_...",
    │     search_params={...}
    │  )
    └─ ToolMessage:
       {status: "redirect",
        redirect_url: "http://localhost:8000/dev/hotel-booker/..."}

25. Supervisor merges result:
    ├─ hotel_booking_complete=True
    ├─ response_type: "hotel_booking_redirect"
    └─ Frontend displays redirect button

26. All bookings complete:
    ├─ booking_intent="both"
    ├─ flight_booking_complete=True
    ├─ hotel_booking_complete=True
    └─ Graph ends (remaining_steps=0)

═══════════════════════════════════════════════════════════════
END OF FLOW
═══════════════════════════════════════════════════════════════
```

---

## Code Locations

```
backend_python/app/ai/graph/
├── supervisor.py                  # Main orchestrator
│   ├── supervisor_node()          # Master routing logic
│   ├── call_planning_agent()      # INITIAL_VISION, ROUTE_REFINEMENT, BUDGET
│   ├── call_flight_booking_agent() # BOOKING_HANDOFF (flights)
│   ├── call_hotel_booking_agent()  # BOOKING_HANDOFF (hotels)
│   └── stage_progression_node()    # Auto-advance logic
│
├── planning_agent.py              # Trip planning chains
│   ├── _extract_trip_info()       # INITIAL_VISION extraction
│   ├── _generate_itinerary()      # ROUTE_REFINEMENT generation
│   └── _estimate_budget()         # BUDGET_ESTIMATION calculation
│
├── flight_graph.py                # Flight ReAct agent (delegated)
│   └── invoke_flight_graph()      # Entry point
│
├── hotel_graph.py                 # Hotel ReAct agent (delegated)
│   └── invoke_hotel_graph()       # Entry point
│
├── state.py                       # State schemas
│   ├── ItinerarySupervisorState   # Supervisor state
│   ├── FlightState                # Flight graph state
│   └── HotelState                 # Hotel graph state
│
└── tools/
    ├── airport_resolution.py      # resolve_airport
    ├── date_parser.py             # parse_dates
    ├── flight_search.py           # search_flights
    ├── city_resolution.py         # resolve_city
    ├── hotel_search.py            # search_hotels
    └── hotel_booking.py           # select_hotel
```

---

## Key Takeaways

✅ **5-Stage Workflow**: Progressive data collection → itinerary → budget → booking

✅ **Automatic Progression**: Stages auto-advance when requirements met + triggers detected

✅ **Isolated Checkpoints**: Sub-agents use unique thread_ids (no state conflicts)

✅ **On-Demand Search**: Flights/hotels searched in BOOKING_HANDOFF (not pre-cached)

✅ **Human-in-the-Loop**: Disambiguation for airports/cities

✅ **Structured Chains for Planning**: Deterministic extraction (not ReAct)

✅ **ReAct for Booking**: Flexible multi-turn tool use for flights/hotels

✅ **MongoDB Persistence**: Full state saved across conversation turns

---

**Last Updated**: January 2026
**Maintainer**: Voya AI Team
**Questions?** See `backend_python/CLAUDE.md` or create GitHub issue
