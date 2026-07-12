# LangGraph Architecture for Voya

> **Status:** Draft
> **Date:** 2025-12-11
> **See Also:** [LANGGRAPH_PROPOSAL.md](./LANGGRAPH_PROPOSAL.md) for detailed rationale

---

## Overview

This document describes the practical architecture for implementing LangGraph in Voya. It focuses on **what we'd build**, not why.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VOYA LANGGRAPH STACK                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Frontend (React)                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ChatBot Component  →  POST /api/chat/message  →  Response + Type   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   Backend (FastAPI)                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         LangGraph Engine                             │  │
│   │  ┌───────────┐    ┌───────────┐    ┌───────────┐                    │  │
│   │  │  Intent   │───►│  Flight   │    │   Hotel   │                    │  │
│   │  │  Router   │───►│   Agent   │    │   Agent   │                    │  │
│   │  └───────────┘    └─────┬─────┘    └─────┬─────┘                    │  │
│   │                         │                │                           │  │
│   │                         ▼                ▼                           │  │
│   │                   ┌─────────────────────────────┐                    │  │
│   │                   │          TOOLS              │                    │  │
│   │                   │  • resolve_airport          │                    │  │
│   │                   │  • parse_dates              │                    │  │
│   │                   │  • search_flights           │                    │  │
│   │                   │  • search_hotels            │                    │  │
│   │                   │  • get_flight_rules         │                    │  │
│   │                   │  • create_booking           │                    │  │
│   │                   └─────────────────────────────┘                    │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│   Storage                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  MongoDB: checkpoints, users, bookings    │  LangFuse: traces       │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
backend_python/
├── app/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── graph/                      # NEW: LangGraph implementation
│   │   │   ├── __init__.py             # Exports: get_graph(), ConversationState
│   │   │   ├── state.py                # State TypedDict definitions
│   │   │   ├── router.py               # Main graph with intent routing
│   │   │   ├── agents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── flight.py           # Flight booking ReAct agent
│   │   │   │   ├── hotel.py            # Hotel booking ReAct agent
│   │   │   │   └── general.py          # General travel queries
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py         # Exports all tools
│   │   │   │   ├── airport.py          # resolve_airport tool
│   │   │   │   ├── dates.py            # parse_dates tool
│   │   │   │   ├── flights.py          # search_flights, get_rules, book
│   │   │   │   └── hotels.py           # search_hotels, get_rates, book
│   │   │   ├── prompts/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── flight_agent.py     # Flight agent system prompt
│   │   │   │   ├── hotel_agent.py      # Hotel agent system prompt
│   │   │   │   └── intent.py           # Intent classification prompt
│   │   │   └── callbacks.py            # LangFuse integration
│   │   │
│   │   └── utils/                      # KEEP: Existing utilities
│   │       ├── date_parser.py          # Used by parse_dates tool
│   │       └── selection_parser.py     # Used by agents
│   │
│   ├── domains/                        # KEEP: Existing services (become tool backends)
│   │   ├── airport/
│   │   │   └── service.py              # AirportService → resolve_airport tool
│   │   ├── flight/
│   │   │   └── service.py              # FlightService → flight tools
│   │   └── hotel/
│   │       └── service.py              # HotelService → hotel tools
│   │
│   └── api/
│       └── chat.py                     # Updated to use LangGraph
```

---

## Core Components

### 1. State Definition

```python
# app/ai/graph/state.py

from typing import TypedDict, Literal, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class FlightParams(TypedDict, total=False):
    """Collected flight search parameters."""
    origin: str | None              # IATA code (e.g., "LHR")
    origin_name: str | None         # Display name (e.g., "London Heathrow")
    destination: str | None
    destination_name: str | None
    departure_date: str | None      # YYYY-MM-DD
    return_date: str | None
    adults: int
    children: int
    infants: int


class HotelParams(TypedDict, total=False):
    """Collected hotel search parameters."""
    city: str | None
    city_display: str | None        # "Paris, France"
    latitude: float | None
    longitude: float | None
    check_in: str | None
    check_out: str | None
    adults: int
    rooms: int


class ConversationState(TypedDict):
    """
    Single source of truth for conversation state.
    Replaces: SessionState, FlightFieldCollector, handler sessions.
    """
    # Message history (accumulates via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # Identifiers
    user_id: str
    chat_id: str

    # Current intent
    intent: Literal["flight", "hotel", "general", "view_bookings"] | None

    # Domain-specific params
    flight: FlightParams
    hotel: HotelParams

    # Search results (set after search, cleared on new search)
    flight_results: list[dict] | None
    hotel_results: list[dict] | None

    # Selected items (set after user selection)
    selected_flight: dict | None
    selected_hotel: dict | None
    selected_room: dict | None

    # Booking state
    booking_confirmed: bool
    booking_reference: str | None

    # Response formatting (tells frontend which component to render)
    response_type: str
    response_data: dict | None
```

### 2. Main Router Graph

```python
# app/ai/graph/router.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.graph.state import ConversationState
from app.ai.graph.agents.flight import flight_agent
from app.ai.graph.agents.hotel import hotel_agent
from app.ai.graph.agents.general import general_agent
from app.ai.graph.prompts.intent import INTENT_PROMPT
from app.core.config import settings


async def classify_intent(state: ConversationState) -> dict:
    """Classify user intent from latest message."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    last_message = state["messages"][-1].content
    current_intent = state.get("intent")

    # Include context about active flows
    context = ""
    if state.get("flight_results"):
        context = "User has active flight search results."
    elif state.get("hotel_results"):
        context = "User has active hotel search results."

    response = await llm.ainvoke(
        INTENT_PROMPT.format(
            message=last_message,
            current_intent=current_intent,
            context=context
        )
    )

    # Parse intent from response (structured output)
    intent = parse_intent_response(response.content)

    return {"intent": intent}


def route_by_intent(state: ConversationState) -> str:
    """Route to appropriate agent based on intent."""
    intent = state.get("intent")

    # Sticky routing: stay in current flow if active
    if state.get("flight_results") and intent != "hotel":
        return "flight_agent"
    if state.get("hotel_results") and intent != "flight":
        return "hotel_agent"

    # Route by detected intent
    if intent == "flight":
        return "flight_agent"
    elif intent == "hotel":
        return "hotel_agent"
    else:
        return "general_agent"


def create_graph() -> StateGraph:
    """Create the main conversation graph."""
    builder = StateGraph(ConversationState)

    # Nodes
    builder.add_node("classify", classify_intent)
    builder.add_node("flight_agent", flight_agent)
    builder.add_node("hotel_agent", hotel_agent)
    builder.add_node("general_agent", general_agent)

    # Edges
    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", route_by_intent)
    builder.add_edge("flight_agent", END)
    builder.add_edge("hotel_agent", END)
    builder.add_edge("general_agent", END)

    return builder


async def get_graph():
    """Get compiled graph with MongoDB checkpointing."""
    builder = create_graph()

    checkpointer = AsyncMongoDBSaver.from_conn_string(
        settings.MONGODB_URI,
        db_name="voya"
    )

    return builder.compile(checkpointer=checkpointer)
```

### 3. Flight Agent (ReAct)

```python
# app/ai/graph/agents/flight.py

from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.graph.state import ConversationState
from app.ai.graph.tools import (
    resolve_airport,
    parse_dates,
    search_flights,
    get_flight_rules,
    book_flight,
)
from app.ai.graph.prompts.flight_agent import FLIGHT_SYSTEM_PROMPT


def create_flight_agent():
    """Create ReAct agent for flight booking."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    tools = [
        resolve_airport,
        parse_dates,
        search_flights,
        get_flight_rules,
        book_flight,
    ]

    return create_react_agent(
        llm,
        tools,
        state_modifier=FLIGHT_SYSTEM_PROMPT,
    )


# The agent node function
_agent = create_flight_agent()

async def flight_agent(state: ConversationState) -> dict:
    """Execute flight agent and format response."""
    # Inject current params into prompt context
    prompt_with_state = FLIGHT_SYSTEM_PROMPT.format(
        origin=state["flight"].get("origin") or "not set",
        origin_name=state["flight"].get("origin_name") or "",
        destination=state["flight"].get("destination") or "not set",
        destination_name=state["flight"].get("destination_name") or "",
        departure_date=state["flight"].get("departure_date") or "not set",
        return_date=state["flight"].get("return_date") or "not set",
        adults=state["flight"].get("adults", 1),
        children=state["flight"].get("children", 0),
        infants=state["flight"].get("infants", 0),
        has_results=bool(state.get("flight_results")),
        selected_flight=state.get("selected_flight"),
    )

    # Run agent
    result = await _agent.ainvoke(
        {"messages": state["messages"]},
        {"configurable": {"state_modifier": prompt_with_state}}
    )

    # Extract state updates from agent's tool calls
    updates = extract_state_updates(result, state)

    return updates
```

### 4. Flight Agent Prompt

```python
# app/ai/graph/prompts/flight_agent.py

FLIGHT_SYSTEM_PROMPT = """You are MyVoya, a friendly flight booking assistant.

## Current Booking State
- Origin: {origin} {origin_name}
- Destination: {destination} {destination_name}
- Departure: {departure_date}
- Return: {return_date}
- Passengers: {adults} adults, {children} children, {infants} infants
- Has search results: {has_results}
- Selected flight: {selected_flight}

## Your Tools
- `resolve_airport`: Look up airport IATA codes for cities/locations
- `parse_dates`: Parse dates from natural language ("next Tuesday", "Jan 15-20")
- `search_flights`: Search for available flights (requires origin, destination, departure_date)
- `get_flight_rules`: Get fare rules and baggage info for a specific flight
- `book_flight`: Create a booking (requires selected flight + passenger details)

## Instructions

1. **When user mentions a location**: Call `resolve_airport` immediately
   - If multiple airports returned, ask user to choose
   - Example: "London has several airports - Heathrow, Gatwick, Stansted. Which do you prefer?"

2. **When user mentions dates**: Call `parse_dates` immediately
   - Handles: "next Tuesday", "Jan 15 for a week", "15th to 20th"

3. **When you have origin + destination + departure_date**: Call `search_flights`
   - Present results in categories: Cheapest, Fastest, Best Value
   - Always show top 3 options per category

4. **When user selects a flight**: ("book option 1", "I'll take the cheapest")
   - Confirm the selection details
   - Ask for passenger information if not provided

5. **When user provides passenger details**: Call `book_flight`
   - Confirm booking details before finalizing

## Response Style
- Be concise and friendly
- Ask ONE question at a time for missing information
- Use emojis sparingly (✈️ for flights, 💵 for prices)
- Always confirm what you understood before searching

## Example Conversation
User: "I want to fly from London to Paris next week"
You: [call resolve_airport("London", "origin")]
You: [call resolve_airport("Paris", "destination")]
You: [call parse_dates("next week")]
You: "Great! I found London Heathrow (LHR) and Paris CDG. Flying next Monday, January 20th.
      Should I search for flights, or would you prefer a different London airport?"
"""
```

### 5. Tools

```python
# app/ai/graph/tools/airport.py

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class AirportInput(BaseModel):
    """Input for airport resolution."""
    query: str = Field(description="City name, airport code, or airport name")
    context: str | None = Field(
        default=None,
        description="Either 'origin' or 'destination' to help with disambiguation"
    )


@tool(args_schema=AirportInput)
async def resolve_airport(query: str, context: str | None = None) -> dict:
    """
    Resolve a location to airport IATA code(s).

    Returns:
    - status: "resolved" | "multiple" | "not_found"
    - airport: Single airport if resolved
    - options: List of airports if multiple matches
    - message: Human-readable result description

    Examples:
    - "London" → multiple options (LHR, LGW, STN, LTN, LCY)
    - "LHR" → resolved to London Heathrow
    - "Charles de Gaulle" → resolved to CDG
    """
    from app.domains.airport import get_airport_service

    service = get_airport_service()
    result = await service.resolve(query, context)

    if result.status == "resolved" and not result.needs_disambiguation:
        return {
            "status": "resolved",
            "airport": {
                "iata": result.airport.iata,
                "name": result.airport.name,
                "city": result.airport.city,
                "country": result.airport.country,
            },
            "message": f"Resolved to {result.airport.name} ({result.airport.iata})"
        }

    if result.all_airports:
        return {
            "status": "multiple",
            "options": [
                {
                    "iata": a.iata,
                    "name": a.name,
                    "city": a.city,
                }
                for a in result.all_airports[:5]
            ],
            "message": f"Found {len(result.all_airports)} airports. Please ask user to choose."
        }

    return {
        "status": "not_found",
        "message": f"No airports found for '{query}'. Ask user to try a different name."
    }
```

```python
# app/ai/graph/tools/dates.py

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class DateInput(BaseModel):
    """Input for date parsing."""
    text: str = Field(description="Text containing date references")


@tool(args_schema=DateInput)
def parse_dates(text: str) -> dict:
    """
    Parse dates from natural language.

    Handles:
    - Relative: "tomorrow", "next Tuesday", "in 2 weeks"
    - Absolute: "January 15", "15/01/2025", "Jan 15-20"
    - Ranges: "Monday to Friday", "15th for a week"

    Returns:
    - departure_date: YYYY-MM-DD or None
    - return_date: YYYY-MM-DD or None
    - is_return: Whether this is a round trip
    """
    from app.ai.utils import DateParser

    parser = DateParser()
    result = parser.parse(text)

    return {
        "departure_date": result.get("departure_date"),
        "return_date": result.get("return_date"),
        "is_return": result.get("return_date") is not None,
        "parsed_from": text,
    }
```

```python
# app/ai/graph/tools/flights.py

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FlightSearchInput(BaseModel):
    """Input for flight search."""
    origin: str = Field(description="Origin IATA code (e.g., 'LHR')")
    destination: str = Field(description="Destination IATA code (e.g., 'CDG')")
    departure_date: str = Field(description="Departure date YYYY-MM-DD")
    return_date: str | None = Field(default=None, description="Return date for round trips")
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0)
    infants: int = Field(default=0, ge=0)


@tool(args_schema=FlightSearchInput)
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
) -> dict:
    """
    Search for flights using FlightLogic API.

    Returns curated results in categories:
    - cheapest: Top 3 lowest price flights
    - fastest: Top 3 shortest duration flights
    - best_value: Top 3 optimal price/duration ratio

    Also includes summary with price range and direct flight count.
    """
    from app.domains.flight import get_flight_service

    service = get_flight_service()
    results = await service.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants=infants,
    )

    # Curate into categories
    cheapest = sorted(results, key=lambda f: f["total_fare"]["amount"])[:3]
    fastest = sorted(results, key=lambda f: f["duration_minutes"])[:3]

    def value_score(f):
        return f["total_fare"]["amount"] + (f["duration_minutes"] * 0.5)
    best_value = sorted(results, key=value_score)[:3]

    prices = [f["total_fare"]["amount"] for f in results]

    return {
        "total_found": len(results),
        "direct_flights": sum(1 for f in results if f.get("stops", 0) == 0),
        "price_range": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "currency": results[0]["total_fare"]["currency"] if results else "GBP",
        },
        "categories": {
            "cheapest": format_flights(cheapest, "Cheapest 💵"),
            "fastest": format_flights(fastest, "Fastest ⚡"),
            "best_value": format_flights(best_value, "Best Value ⭐"),
        },
    }


def format_flights(flights: list, label: str) -> dict:
    """Format flights for display."""
    return {
        "label": label,
        "flights": [
            {
                "option_number": i + 1,
                "airline": f["airline"],
                "flight_number": f["flight_number"],
                "departure": f["departure_time"],
                "arrival": f["arrival_time"],
                "duration": f["duration_display"],
                "stops": f.get("stops", 0),
                "price": f["total_fare"]["amount"],
                "currency": f["total_fare"]["currency"],
            }
            for i, f in enumerate(flights)
        ],
    }
```

### 6. API Integration

```python
# app/api/chat.py

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage, AIMessage

from app.ai.graph.router import get_graph
from app.ai.graph.callbacks import get_langfuse_handler
from app.domains.chat.schemas import ChatRequest, ChatResponse
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    user=Depends(get_current_user),
):
    """
    Process chat message through LangGraph.

    The graph:
    1. Classifies intent
    2. Routes to appropriate agent (flight/hotel/general)
    3. Agent decides which tools to call
    4. Returns formatted response for frontend

    State is automatically persisted via MongoDB checkpointer.
    """
    graph = await get_graph()

    # Config for this conversation
    config = {
        "configurable": {"thread_id": request.chat_id},
        "callbacks": [get_langfuse_handler(user.id, request.chat_id)],
    }

    # Invoke graph - previous state loaded automatically
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "user_id": str(user.id),
            "chat_id": request.chat_id,
        },
        config,
    )

    # Extract response
    last_ai_message = next(
        (m for m in reversed(result["messages"]) if isinstance(m, AIMessage)),
        None,
    )

    return ChatResponse(
        message=last_ai_message.content if last_ai_message else "",
        chat_id=request.chat_id,
        intent_name=result.get("intent") or "general",
        confidence=1.0,
        type=result.get("response_type", "message"),
        data=result.get("response_data"),
    )
```

---

## Data Flow

### Flight Search Flow

```
User: "Fly from London to Paris next Tuesday"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. CLASSIFY INTENT                                                         │
│     Input: message                                                          │
│     Output: intent = "flight"                                               │
│     Route: → flight_agent                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. FLIGHT AGENT (ReAct Loop)                                               │
│                                                                             │
│     LLM sees: "Fly from London to Paris next Tuesday"                       │
│     LLM thinks: "I need to resolve airports and parse dates"                │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  Tool Call: resolve_airport("London", "origin")                  │    │
│     │  Result: {status: "multiple", options: [LHR, LGW, STN, ...]}    │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  Tool Call: resolve_airport("Paris", "destination")              │    │
│     │  Result: {status: "resolved", airport: {iata: "CDG", ...}}      │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  Tool Call: parse_dates("next Tuesday")                          │    │
│     │  Result: {departure_date: "2025-01-14", is_return: false}       │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│     LLM sees: London has multiple airports, Paris resolved, date parsed     │
│     LLM responds: "I found Paris CDG and your date is Jan 14.               │
│                    London has several airports - Heathrow, Gatwick,         │
│                    or Stansted. Which would you prefer?"                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. STATE CHECKPOINT SAVED                                                  │
│                                                                             │
│     flight: {                                                               │
│       destination: "CDG",                                                   │
│       destination_name: "Paris Charles de Gaulle",                          │
│       departure_date: "2025-01-14",                                         │
│       origin: null  # Still needs user choice                               │
│     }                                                                       │
│     response_type: "airport_disambiguation"                                 │
│     response_data: {options: [...]}                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
              [Response to User]


═══════════════════════════════════════════════════════════════════════════════


User: "Heathrow"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. STATE LOADED FROM CHECKPOINT                                            │
│     (Knows: destination=CDG, departure=2025-01-14, origin=pending)          │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. FLIGHT AGENT                                                            │
│                                                                             │
│     LLM sees: User said "Heathrow", we were waiting for airport choice      │
│     LLM thinks: "User selected Heathrow. Now I have all required fields."   │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  Tool Call: search_flights(                                      │    │
│     │    origin="LHR",                                                 │    │
│     │    destination="CDG",                                            │    │
│     │    departure_date="2025-01-14"                                   │    │
│     │  )                                                               │    │
│     │  Result: {total: 45, categories: {...}}                         │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│     LLM responds: "I found 45 flights from London Heathrow to Paris!        │
│                    Prices start from £89. Here are your options..."         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  6. RESPONSE                                                                │
│                                                                             │
│     response_type: "flight_search_results"                                  │
│     response_data: {                                                        │
│       summary: {total: 45, price_range: {min: 89, max: 450}},              │
│       categories: {cheapest: [...], fastest: [...], best_value: [...]}     │
│     }                                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Response Types

The `response_type` field tells the frontend which component to render:

| response_type | Frontend Component | When Used |
|---------------|-------------------|-----------|
| `message` | `ChatMessage` | Simple text response |
| `flight_search_results` | `FlightResultsCard` | After flight search |
| `hotel_search_results` | `HotelResultsCard` | After hotel search |
| `airport_disambiguation` | `AirportPicker` | Multiple airport options |
| `city_disambiguation` | `CityPicker` | Multiple city options |
| `flight_selected` | `FlightDetailsCard` | User selected a flight |
| `booking_confirmed` | `BookingConfirmation` | Booking complete |

---

## Dependencies

```toml
# pyproject.toml additions

[project.dependencies]
langgraph = ">=0.2.0,<0.3.0"
langgraph-checkpoint-mongodb = ">=0.3.0,<0.4.0"
langchain-google-genai = ">=2.0.0,<3.0.0"
langchain-core = ">=0.3.0,<0.4.0"
langfuse = ">=2.0.0,<3.0.0"
```

---

## Key Differences from Current Architecture

| Aspect | Current | LangGraph |
|--------|---------|-----------|
| **State storage** | 3 places (handler, collector, MongoDB) | 1 place (checkpointer) |
| **Field extraction** | 2,000 lines of regex | LLM calls tools |
| **Routing logic** | if/else in ChatService | Graph edges |
| **Tool invocation** | Hardcoded in handler | LLM decides autonomously |
| **Error handling** | Try/catch everywhere | Centralized in agent |
| **Testing** | Integration tests only | Unit test each tool |
| **Debugging** | Log files | LangFuse traces |

---

## Files to Keep

These existing files remain unchanged (become tool backends):

- `app/domains/airport/service.py` → powers `resolve_airport` tool
- `app/domains/flight/service.py` → powers `search_flights` tool
- `app/domains/hotel/service.py` → powers `search_hotels` tool
- `app/ai/utils/date_parser.py` → powers `parse_dates` tool
- `app/ai/utils/selection_parser.py` → used by agents for parsing "option 1"

---

## Files to Delete (After Migration)

- `app/ai/enhanced_flight_handler.py` (3,531 lines)
- `app/ai/flight_field_collector.py` (1,569 lines)
- `app/ai/flight_booking_handler.py` (788 lines)
- `app/ai/enhanced_hotel_handler.py` (428 lines)
- `app/ai/hotel_field_collector.py` (206 lines)
- `app/ai/hotel_booking_handler.py` (278 lines)
- `app/ai/base/session_state_manager.py` (268 lines)

**Total removed:** ~7,068 lines
**Total added:** ~1,500 lines
**Net reduction:** ~5,500 lines (78%)
