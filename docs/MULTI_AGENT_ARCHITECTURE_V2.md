# Voya Multi-Agent Architecture V2

> **Status**: Proposal (Reviewed) — **Recommended starting architecture**
> **Date**: 2026-02-20
> **Goal**: Replace the current intent-recognition + feature-flag routing system with a clean, scalable multi-agent architecture following industry best practices.
> **Companion doc**: [V3](MULTI_AGENT_ARCHITECTURE_V3.md) — peer-to-peer handoff variant. V2 is recommended as the starting architecture; V3's direct handoff pattern can be adopted for auto-chain paths after production validation.

---

## Table of Contents

1. [Why Redesign](#1-why-redesign)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Specifications](#3-agent-specifications)
4. [Smart Tools Layer](#4-smart-tools-layer)
5. [Shared Infrastructure](#5-shared-infrastructure)
6. [Multi-Query Handling](#6-multi-query-handling)
7. [Request Lifecycle](#7-request-lifecycle)
8. [Human-in-the-Loop](#8-human-in-the-loop)
9. [Edge Cases & Failure Handling](#9-edge-cases--failure-handling)
10. [Scalability & Extensibility](#10-scalability--extensibility)
11. [LangGraph Implementation](#11-langgraph-implementation)
    - [11.5 Middleware Stack (Built-in vs Custom)](#115-middleware-stack-built-in-vs-custom)
12. [Benefits Over Current System](#12-benefits-over-current-system)

---

## 1. Why Redesign

### Problems with Current Architecture

| Problem | Impact |
|---------|--------|
| **Priority-based routing** (5 levels in ChatService) | Fragile, hard to debug, order-dependent |
| **Feature flags everywhere** (4 flags controlling dual paths) | Legacy + new code running in parallel, doubles maintenance |
| **IntentRecognizer as separate component** | Extra LLM call before actual work begins, wasted latency |
| **Supervisor with 5 rigid stages** | Cannot adapt to dynamic conversations, stages are hardcoded |
| **Massive agent prompts** (358 lines for flight, 271 for hotel) | Agents doing tool orchestration work, brittle to changes |
| **Dead code** (n8n, supervisor graph, legacy handlers, field collectors) | Confusing codebase, unclear what's active |
| **Scattered state management** (checkpointer + BookingSession + ConversationState) | Multiple sources of truth, inconsistent state |

### Design Principles for V2

1. **Smart Tools, Simple Agents** — Push complexity into tools, keep agent prompts under 50 lines
2. **Single Path** — No feature flags, no dual paths, one way to do everything
3. **Agent Autonomy** — Each agent owns its full lifecycle (collect → execute → respond)
4. **Dynamic over Rigid** — Agents reason about next steps, no hardcoded stage sequences
5. **Plug and Play** — Adding a new agent = create agent + register tools, zero changes elsewhere
6. **Unified State** — One memory store, one session manager, one source of truth
7. **No Agent-to-Agent Coupling** — Agents never talk to each other; all handoffs go through the Supervisor via cross-agent memory
8. **Separation of Concerns** — Routing, domain work, and general Q&A are handled by separate components to prevent any single agent from becoming overly centralized or monolithic component
9. **Handoff Pattern** — Active agent owns the conversation and receives messages directly. No central keyword matching or heuristic routing. Agents hand back to Supervisor when they encounter requests outside their domain — inspired by OpenAI Agents SDK, built on LangGraph
10. **No Keyword Matching** — All intent understanding is done by LLMs with full conversation context. Zero keyword lists, zero regex patterns, zero heuristic tiers

---

## 2. Architecture Overview

```
                            ┌──────────────────┐
                            │   User Message    │
                            └────────┬─────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │       SUPERVISOR AGENT         │
                     │    (always the entry point)    │
                     │                                │
                     │  Every message enters here.    │
                     │                                │
                     │  Reads session state:          │
                     │  • active_agent set?           │
                     │    → forward to that agent     │
                     │      (NO LLM call, just state  │
                     │       read + forward)          │
                     │  • No active agent?            │
                     │    → classify intent (LLM)     │
                     │    → route to agent            │
                     │    → set as active_agent       │
                     │  • Agent signaled DONE?        │
                     │    → check auto-chain / queue  │
                     │  • Agent handed back?          │
                     │    → re-classify intent (LLM)  │
                     │                                │
                     │  Does NOT answer questions     │
                     │  or do domain work.            │
                     │  Does NOT use keywords or      │
                     │  heuristics for routing.       │
                     └──┬──────┬──────┬──────┬───────┘
                        │      │      │      │
           ┌────────────┘      │      │      └────────────┐
           │                   │      │                   │
           ▼                   ▼      ▼                   ▼
┌───────────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐
│ FLIGHT AGENT  │  │HOTEL AGENT │  │  ITINERARY   │  │  GENERAL AGENT   │
│               │  │            │  │  AGENT       │  │                  │
│ Smart Tools:  │  │ Smart Tools│  │              │  │  Handles:        │
│ •resolve_     │  │•resolve_   │  │ Smart Tools: │  │  • Travel Q&A    │
│  airport      │  │ city       │  │ •resolve_    │  │  • Weather/visa  │
│ •parse_dates  │  │•parse_dates│  │  airport     │  │  • Tips/advice   │
│ •search_      │  │•search_    │  │ •parse_dates │  │  • Anything not  │
│  flights      │  │ hotels     │  │ •generate_   │  │    booking-      │
│ •select_      │  │•select_    │  │  itinerary   │  │    related       │
│  flight       │  │ hotel      │  │ •estimate_   │  │                  │
│               │  │            │  │  budget      │  │  LLM: Capable    │
│ + hand_back   │  │+ hand_back │  │ •save_       │  │  Tools: None     │
│   _to_        │  │  _to_      │  │  itinerary   │  │  + hand_back     │
│   supervisor  │  │  supervisor│  │ + hand_back  │  │    _to_          │
│               │  │            │  │   _to_       │  │    supervisor    │
│               │  │            │  │   supervisor │  │                  │
└───────┬───────┘  └─────┬──────┘  └──────┬───────┘  └────────┬─────────┘
        │                │               │                    │
        └────────────────┼───────────────┼────────────────────┘
                         │               │
             ┌───────────▼───────────────▼──┐
             │       SHARED LAYER           │
             │                              │
             │  • Memory Store              │
             │  • Tool Registry             │
             │  • LLM Gateway               │
             │  • Tracing & Observability    │
             └──────────────────────────────┘

KEY RULES:
  1. Every message goes through the Supervisor — it is always the entry point.
  2. When active_agent is set, Supervisor forwards immediately (no LLM call).
  3. Agents decide when to hand back — they call hand_back_to_supervisor tool.
  4. Agents NEVER talk to each other directly. All handoffs go through Supervisor.
  5. Cross-agent data passes through the shared Memory Store.
  6. No keyword matching or heuristic routing anywhere — LLMs decide intent.
```

### Handoff Pattern (Inspired by OpenAI Agents SDK)

The core routing model is based on the **handoff pattern**: once an agent becomes active, it owns the conversation. The Supervisor still sees every message, but when an active agent is set, it forwards immediately without any LLM call or analysis.

**How it works**:

```
1. User sends first message → Supervisor classifies (LLM) → routes to Agent X → sets active_agent = X
2. User sends next message → Supervisor sees active_agent = X → forwards to Agent X (no LLM call)
3. Agent X handles all messages until it either:
   a. Completes its task → signals DONE → Supervisor checks auto-chain / queue
   b. Detects an unrelated request → calls hand_back_to_supervisor → Supervisor re-classifies (LLM)
   c. Fails → signals FAILED → Supervisor handles gracefully
```

**The Supervisor always sees every message**, but when `active_agent` is set, it just reads one state field and forwards — no LLM call, no keyword matching, no classification. It's a pass-through. The intelligence about "is this message for me?" lives in the **active agent's LLM**, not in the Supervisor.

**Key insight from our experience with `intent_recognizer.py`**: Keyword matching and heuristic routing don't work for unpredictable user input. Users ask questions in unexpected ways, use different languages, misspell words, and paraphrase. Instead of trying to pre-classify messages with keywords, we let the **active agent's LLM** decide what's relevant to its domain and what isn't. The LLM already has the full conversation context — it's the best judge.

| Scenario | Supervisor Action | Speed |
|----------|------------------|-------|
| Active agent set (continuation) | Forward to active agent (no LLM) | ~5-10ms (state read + forward) |
| Agent calls `hand_back_to_supervisor` | Re-classify intent (LLM) and route | ~200-400ms |
| Agent signals DONE + auto-chain pending | Route to next agent in chain | ~50-100ms (no LLM) |
| Agent signals DONE + no pending work | Clear active_agent | ~50-100ms |
| No active agent (fresh conversation) | Classify intent (LLM) and route | ~200-400ms |

**Most messages (70-80%) are continuations** — Supervisor forwards them without an LLM call. The key difference from the old architecture: Supervisor doesn't try to understand the message during forwarding. It trusts the active agent to handle it or hand back.

### Why NOT Keyword/Heuristic Routing

Our current `intent_recognizer.py` uses exactly this approach — keyword matching with LLM fallback. After extensive testing, we found:

1. **Users are unpredictable**: They don't use domain keywords. "I need to get to Tokyo by Friday" has no flight keywords, but it's clearly a flight request.
2. **Keyword overlap**: "book" appears in both flight and hotel contexts. "plan" could be itinerary or general advice.
3. **Context matters more than keywords**: "yes" after a flight search means "continue flight", but keyword matching can't know that without conversation context.
4. **Non-English users**: Keyword lists only work in one language.
5. **Maintenance burden**: Every new edge case means more keywords, more exceptions, more bugs.

**The handoff pattern eliminates all of this.** The active agent's LLM has full conversation context and decides intelligently. When it encounters something outside its domain, it hands back — that's a clear, reliable signal that doesn't need keyword parsing.

### Two Lightweight Optimizations (Not Routing Logic)

The handoff pattern handles all routing via LLM. One narrow safety net protects against LLM failure on high-stakes actions — without reintroducing keyword-based routing.

#### Critical Action Safety Net

For a small set of high-stakes actions where LLM failure has real consequences, a minimal pre-check runs **before** the active agent. This is not routing — it's a guard rail.

```
Critical actions (exhaustive list — only these 3):

CANCEL:  Message starts with or equals:
         "cancel" | "start over" | "forget everything" | "reset"
         → Active agent is cleared, Supervisor responds: "Starting fresh."
         → Why: If the agent's LLM ignores a cancel request and continues
           booking, the user loses trust. This is a safety net.

EMERGENCY STOP (future):
         "stop" | "don't book" | "wait" (during active booking step)
         → Halt any in-progress booking API calls
         → Why: Booking = real money. A missed "stop" = unwanted charge.
```

**What this is NOT**:
- Not a routing tier — doesn't decide which agent to use
- Not keyword matching for intents — doesn't classify "book flight" vs "book hotel"
- Not extensible — this list stays at 2-3 items max, forever
- Not a fallback chain — no "if this fails, try that"

**What this IS**: A circuit breaker for irreversible actions. Same concept as a hardware kill switch — you don't rely on software alone for critical safety.

**Implementation**: ~10 lines of code in the graph entry point, before `route_message`. If the message doesn't match (99%+ of the time), zero overhead — it's a string comparison, not an LLM call.

### Component Count

| Layer | Components | Purpose |
|-------|-----------|---------|
| Entry | 1 API endpoint | `POST /chat/message` |
| Supervisor | 1 Supervisor Agent | Single entry point — routing, session awareness, task queue, auto-chaining |
| Specialists | 4 Agents (Flight, Hotel, Itinerary, General) | Domain-specific work |
| Tools | ~10 Smart Tools (with built-in validation) | All domain logic and edge case handling |
| Infrastructure | 4 shared services | State, LLM, tracing, registry |

**Total: 5 agents, ~10 tools, 4 infrastructure services.**

---

## 3. Agent Specifications

### 3.1 Supervisor Agent

**Role**: Entry point for every message. Sees all messages but stays thin — when an active agent is set, forwards immediately without LLM call. Only uses LLM for initial classification and re-classification after hand-backs.

**Replaces**: IntentRecognizer + ChatService priority routing + BookingSessionService + all feature flags

```
┌─────────────────────────────────────┐
│         SUPERVISOR AGENT            │
│                                     │
│  Sees EVERY message. But:          │
│                                     │
│  active_agent set?                 │
│  → Forward immediately (no LLM)   │
│                                     │
│  No active_agent?                  │
│  → Classify intent (LLM call)     │
│  → Route to correct specialist    │
│  → Set as active_agent            │
│  → Detect multi-query → queue     │
│                                     │
│  Agent signaled DONE?             │
│  → Check auto-chain / pop queue   │
│  → Read cross-agent memory for    │
│    pre-filled handoff params      │
│                                     │
│  Agent handed back?               │
│  → Re-classify intent (LLM call) │
│  → Route to new agent             │
│                                     │
│  Does NOT:                          │
│  • Answer travel questions          │
│  • Do any domain work              │
│  • Use keyword matching            │
│  • Use heuristic routing           │
│  • Analyze message content when    │
│    forwarding to active agent      │
│                                     │
│  LLM: Fast model                   │
│  Tools: None (pure routing)         │
│  Prompt: ~20 lines                  │
└─────────────────────────────────────┘
```

**Structured Output (Required)**

The Supervisor ALWAYS returns a structured JSON decision — never free-form text. This makes every routing decision testable, observable, and resistant to prompt drift.

```
Supervisor output schema:

When active_agent is set (continuation — no LLM call):
{
  "decision_type": "forward",
  "target_agent": "flight"              // just forward, no analysis
}

When LLM is invoked (new intent, hand-back, DONE):
{
  "decision_type": "classify_new" | "auto_chain" | "queue_pop" |
                   "hand_back_reroute" | "detour_return" | "cancel_reset" |
                   "no_matching_agent",
  "target_agent": "flight" | "hotel" | "itinerary" | "general" | null,
  "detected_intents": ["itinerary", "hotel"],     // only when decision_type = "classify_new"
  "pre_filled_params": { ... } | null,            // from cross-agent memory
  "auto_chain_remaining": ["hotel"] | [],
  "user_message": "Let's handle your flight first, then the hotel." | null,
  "set_session": {
    "active_agent": "flight",
    "task_queue": [...],
    "auto_chain": [...]
  }
}
```

The `forward` decision is deterministic — no LLM needed, just read `active_agent` from session state and forward. All other decision types require the Supervisor's LLM.

**Supervisor Agent Prompt** (complete — this is the actual prompt, not a summary):

```
You are a pure routing coordinator for a travel assistant.
Your ONLY job is to decide which specialist agent should handle the user's request.

Rules you MUST follow:
- NEVER answer travel questions yourself.
- NEVER reason about flights, hotels, itineraries, or general travel facts.
- When active_agent is set → always return {"decision_type": "forward", "target_agent": "<active_agent>"}
- Only use LLM classification when there is NO active_agent or when an agent explicitly hands back.
- Always return valid JSON matching the exact schema — no extra text, no explanations.
- For multi-intent messages, pick the FIRST/most urgent booking-related intent and queue the rest.
- If user says "cancel", "start over", "forget", return {"decision_type": "cancel_reset"}

Available specialists: "flight", "hotel", "itinerary", "general".
If the request doesn't match any specialist, return {"decision_type": "no_matching_agent"}
and respond helpfully: "I currently specialize in flights, hotels, and trip planning.
I can help with [list what you can do]. Would you like help with one of those?"

Specialist descriptions:
- "flight": searching for or booking flights
- "hotel": searching for or booking hotels
- "itinerary": planning trips, creating day-by-day itineraries
- "general": travel questions (weather, visa, tips, advice, anything non-booking)
```

This prompt stays at ~15 lines **forever** — regardless of how many agents are added. New agents just add one line to the "Available specialists" list.

**Why structured output matters**:
- **Testable**: Unit test every routing decision without running full agent
- **Observable**: Every decision logged as structured data in Langfuse traces
- **Stable**: JSON schema constrains behavior — Supervisor can't drift into domain reasoning
- **Debuggable**: "Why did it route to hotel?" → read the JSON, not interpret free-form text

**Why separate from General Agent**: Prevents the "overly centralized or monolithic" anti-pattern. If routing + Q&A + handoff management + context stitching all live in one agent, its prompt grows massive over time — exactly the problem we're solving. Keeping the Supervisor thin means:
- 70-80% of messages are forwarded without LLM call (just state read)
- LLM only invoked for classification, hand-backs, and completion handling
- Prompt stays ~20 lines forever, regardless of how many agents we add
- Easy to A/B test routing logic without affecting any domain behavior

### The `hand_back_to_supervisor` Tool

Every specialist agent has access to a special tool that returns control to the Supervisor. This is how agents handle topic changes — they don't need keyword matching because their LLM naturally understands what's outside their domain.

```python
# Tool definition (available to all agents)
def hand_back_to_supervisor(reason: str) -> str:
    """
    Call this when the user's message is NOT related to your domain.

    Args:
        reason: Why you're handing back. Examples:
            - "User is asking about hotels, not flights"
            - "User wants general travel advice"
            - "User wants to plan an itinerary"
            - "User said 'cancel' / 'start over'"

    The Supervisor will re-classify the user's intent and route
    to the appropriate agent.
    """
    return "Handing back to supervisor for re-routing."
```

**How it works in practice**:

```
Active agent: Flight Agent
User: "Actually, what's the weather like in Tokyo in April?"

Flight Agent's LLM sees:
  - Conversation context: we were discussing flights to Tokyo
  - Current message: asking about weather (not flight-related)
  - Available tools: resolve_airport, parse_dates, search_flights, hand_back_to_supervisor

Flight Agent decides: This is a weather question, not a flight question.
  → Calls hand_back_to_supervisor(reason="User asking about weather")
  → Supervisor activates, classifies as GENERAL_QUERY
  → Routes to General Agent (becomes new active_agent)
  → General Agent answers the weather question
```

**Why this works better than keyword matching**:
- The agent's LLM has **full conversation context** — it knows "Tokyo" is the flight destination
- It understands **intent, not just words** — "what about accommodations?" doesn't need a hotel keyword list
- It handles **any language** — the LLM understands multilingual requests naturally
- It's **self-correcting** — if the agent wrongly handles a message, the user's follow-up clarifies, and the agent can hand back then

**When agents should NOT hand back**:
- Follow-up questions about their domain ("what about return flights?")
- Clarifying questions ("is that one-way?")
- Short replies ("yes", "option 1", "2 adults") — these are always continuations
- Modifications ("change the dates", "try a different airport")

---

### 3.2 General Agent

**Role**: Handles all non-booking travel queries — weather, visa info, travel tips, destination advice, general conversation.

**Replaces**: GeneralTravelHandler

```
┌─────────────────────────────────────┐
│          GENERAL AGENT              │
│                                     │
│  Handles:                           │
│  • "What's the weather in Tokyo?"   │
│  • "Do I need a visa for Japan?"    │
│  • "Best time to visit Bali?"       │
│  • "Baggage policy for Emirates?"   │
│  • "Tips for traveling in Europe"   │
│  • Any non-booking conversation     │
│                                     │
│  Does NOT:                          │
│  • Book flights or hotels           │
│  • Search for flights or hotels     │
│  • Plan itineraries                 │
│                                     │
│  LLM: Capable model                │
│  Tools: None (knowledge-based)      │
│  Prompt: ~20 lines                  │
└─────────────────────────────────────┘
```

**Why a separate agent instead of inline in Supervisor**: General queries can require long, detailed responses (visa requirements, travel guides). A fast Supervisor model optimized for classification would produce shallow answers. The General Agent uses a capable model that generates high-quality travel content.

**General Agent stays active for follow-ups**: Unlike V2's original design where General Agent signaled `done` after every answer (forcing Supervisor re-classification on every follow-up), General Agent now signals `needs_input` and stays as the active agent. This means:

```
User: "What's the weather in Tokyo?"  → Supervisor → General Agent → answers
User: "What about Kyoto?"            → General Agent directly (no Supervisor hop)
User: "And visa requirements?"       → General Agent directly (no Supervisor hop)
User: "OK book me a flight to Tokyo" → General Agent: not my domain → hand_back_to_supervisor
```

This saves 2 unnecessary Supervisor LLM calls in a typical 3-question conversation. General Agent hands back only when the user switches to a booking/planning topic — same pattern as Flight/Hotel agents.

**V1 Known Limitation: No Real-Time Data**

V1 launches with no tools — the General Agent relies solely on LLM knowledge. This means:
- **Weather**: Answers will be seasonal generalizations ("Bali is dry April-October"), not real-time forecasts. Acceptable for trip planning, inadequate for "will it rain tomorrow?"
- **Visa requirements**: LLM knowledge has a cutoff date. Visa rules change — answers may be outdated. The agent's prompt should include a disclaimer: "Visa requirements change frequently. Please verify with the embassy before traveling."
- **Travel advisories**: Cannot reflect current events (wars, natural disasters, pandemics). Same disclaimer applies.
- **Prices**: Cannot give real-time pricing. Only general ranges ("Tokyo hotels average $100-200/night").

This is a **conscious trade-off** for V1: shipping without tools is faster, and LLM knowledge answers 80%+ of general travel questions adequately. But real-time accuracy for weather, visas, and advisories is a gap that will cause incorrect answers. Track user feedback on wrong answers to prioritize which tool to add first.

**Future Enhancement: Read-Only Tools**

When user demand justifies the maintenance cost, the General Agent can gain **read-only** tools that don't modify state:

| Potential Tool | Purpose |
|---------------|---------|
| `get_weather_forecast` | Real-time weather for travel planning |
| `get_travel_advisory` | Government travel warnings and alerts |
| `search_visa_requirements` | Visa rules by passport + destination |
| `get_flight_price_trend` | Historical price data (read-only) |

These tools are stateless and safe — they don't create sessions, bookings, or modify any data. Adding them follows the same pattern: create tool → register in Tool Registry → done.

---

### 3.3 Flight Agent

**Role**: Handles the complete flight booking lifecycle from first message to booking confirmation.

**Replaces**: flight_graph + 358-line prompt + FlightBookingHandler + EnhancedFlightHandler + FlightFieldCollector

```
┌─────────────────────────────────────┐
│           FLIGHT AGENT              │
│                                     │
│  Lifecycle:                         │
│  1. Collect: origin, destination,   │
│     dates, trip type, passengers    │
│  2. Search: call search_flights     │
│  3. Present: show results           │
│  4. Book: handle selection          │
│                                     │
│  Smart Tools:                       │
│  • resolve_airport                  │
│  • parse_dates                      │
│  • search_flights                   │
│  • select_flight                    │
│                                     │
│  LLM: Capable model (tool use)     │
│  Prompt: ~35 lines                  │
└─────────────────────────────────────┘
```

**Why 35 lines instead of 358**: All edge cases — disambiguation, city-wide search flags, date parsing scenarios, time preference extraction, result formatting, output validation — are handled inside smart tools. The agent only knows: "collect info, call tools, show results."

---

### 3.4 Hotel Agent

**Role**: Handles the complete hotel booking lifecycle.

**Replaces**: hotel_graph + 271-line prompt + HotelBookingHandler + EnhancedHotelHandler + HotelFieldCollector

```
┌─────────────────────────────────────┐
│           HOTEL AGENT               │
│                                     │
│  Lifecycle:                         │
│  1. Collect: city, check-in,        │
│     check-out, guests, rooms        │
│  2. Search: call search_hotels      │
│  3. Present: show results           │
│  4. Refine: filter by star rating   │
│  5. Book: handle selection          │
│                                     │
│  Smart Tools:                       │
│  • resolve_city                     │
│  • parse_dates                      │
│  • search_hotels                    │
│  • select_hotel                     │
│                                     │
│  LLM: Capable model (tool use)     │
│  Prompt: ~35 lines                  │
└─────────────────────────────────────┘
```

---

### 3.5 Itinerary Agent

**Role**: Plans complete trips dynamically. Does NOT book anything.

**Replaces**: supervisor (5 rigid stages) + planning_agent + booking_intent_collector

```
┌─────────────────────────────────────┐
│         ITINERARY AGENT             │
│                                     │
│  Dynamic Planning (NO fixed stages):│
│                                     │
│  1. Understand trip vision          │
│     (where, when, who, interests)   │
│  2. Resolve airports + parse dates  │
│  3. Generate day-by-day itinerary   │
│  4. Estimate budget breakdown       │
│  5. Handle modifications anytime    │
│  6. Save finalized itinerary        │
│                                     │
│  Does NOT book flights or hotels.   │
│  When user says "book flights",     │
│  signals DONE → Supervisor reads    │
│  trip data from cross-agent memory  │
│  and auto-chains to Flight/Hotel.   │
│                                     │
│  Smart Tools:                       │
│  • resolve_airport                  │
│  • parse_dates                      │
│  • generate_itinerary              │
│  • estimate_budget                  │
│  • save_itinerary                  │
│                                     │
│  LLM: Capable model (tool use)     │
│  Prompt: ~40 lines                  │
└─────────────────────────────────────┘
```

**Key design decision: Itinerary Agent does NOT delegate to Flight/Hotel agents.**

The Supervisor manages all agent handoffs. When a user finishes planning and says "book the flights", the Supervisor:
1. Reads trip data from cross-agent memory (origin, destination, dates, passengers)
2. Hands off to Flight Agent with pre-filled params
3. After Flight Agent completes, asks user about hotels
4. Hands off to Hotel Agent with pre-filled params

**Auto-chaining**: When user says "book everything", the Itinerary Agent writes `booking_plan` to memory and the Supervisor auto-chains through agents in that order — no separate user confirmation needed between steps.

This means:
- **No agent-to-agent coupling** — Itinerary doesn't know Flight/Hotel exist
- **Supervisor is the single handoff point** — one place for all transitions
- **Consistent pattern** — every agent talks only to the Supervisor, never to each other
- **Simpler Itinerary Agent** — only planning tools, no delegation logic

**Why dynamic instead of 5 stages**:

```
CURRENT (rigid):
  Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5
  (must go in order, can't skip, can't go back easily)

PROPOSED (dynamic):
  User: "Plan a 5-day trip to Japan in April"
  Agent reasons: I need origin, I have destination + rough dates
  → asks for origin
  → generates itinerary
  → user says "add a day in Kyoto" → modifies
  → user says "book the flights" → signals DONE, Supervisor auto-chains to Flight Agent
  → user says "actually change dates" → Supervisor returns to Itinerary Agent
  → user says "what's the budget?" → estimates

  No fixed order. Agent decides what to do based on conversation context.
```

---

### 3.6 Agent Completion Signaling

Every specialist agent communicates its status back to the Supervisor through a **structured metadata object in their state update** — not free-form text. This is how the Supervisor knows when to auto-chain, pop the task queue, or handle failures.

**How agents trigger signals**: Agents return a structured `agent_signal` field as part of their LangGraph state update. This is NOT embedded in the chat message — it's a separate state field that the Supervisor reads via conditional edges.

```python
# Agent signals DONE (e.g., booking complete)
return {
    "messages": [response],
    "agent_signal": {"agent_status": "done", "done_reason": "booking_complete"}
}

# Agent signals HAND-BACK (e.g., user asking about hotels during flight)
return {
    "messages": [response],
    "agent_signal": {"agent_status": "hand_back", "reason": "User asking about hotels"}
}

# Agent signals NEEDS INPUT (waiting for user reply)
return {
    "messages": [response],
    "agent_signal": {"agent_status": "needs_input"}
}
```

The Supervisor reads `agent_signal` after each agent turn via LangGraph conditional edges — never by parsing free-form text.

**Signal Schema** (returned as part of agent's state update):

```
{
  "agent_status": "done" | "failed" | "needs_input" | "hand_back" | "active",
  "done_reason": "booking_complete" | "planning_complete" | "query_answered" | null,
  "failed_reason": "tool_failures_exceeded" | "api_unavailable" | "invalid_state" | null,
  "reason": "User asking about hotels" | null,  // hand_back reason (free text for debugging)
  "consecutive_failures": 0,          // counter for tool failures
  "planning_complete": false,         // Itinerary-specific: triggers auto-chain eligibility
  "cross_agent_memory_updated": true  // whether handoff data was written
}
```

**How it works in LangGraph**: Each agent node returns a state update dict. The Supervisor reads this in the next graph step via conditional edges:

```python
# Agent node returns status in state
async def flight_agent_node(state: AgentState) -> dict:
    # ... agent work ...
    if booking_confirmed:
        return {
            "messages": [...],
            "agent_signal": {
                "agent_status": "done",
                "done_reason": "booking_complete",
                "cross_agent_memory_updated": True,
            }
        }
    if consecutive_failures >= 3:
        return {
            "messages": [...],
            "agent_signal": {
                "agent_status": "failed",
                "failed_reason": "tool_failures_exceeded",
                "consecutive_failures": 3,
            }
        }
    # Still collecting info / showing results
    return {
        "messages": [...],
        "agent_signal": {"agent_status": "needs_input"}
    }

# Supervisor reads the signal via conditional edge
def after_agent(state: AgentState) -> str:
    signal = state.get("agent_signal", {})
    status = signal.get("agent_status")

    if status == "done":
        return "supervisor"        # Supervisor checks auto-chain / queue
    elif status == "failed":
        return "supervisor"        # Supervisor routes to General Agent
    elif status == "needs_input":
        return END                 # Wait for next user message
    return "supervisor"            # Default: return to Supervisor
```

**Signal meanings**:

| Status | When | Supervisor Action |
|--------|------|-------------------|
| `done` + `booking_complete` | Flight/Hotel booked successfully | Check auto-chain → pop queue → or clear session |
| `done` + `planning_complete` | Itinerary finalized, `booking_plan` + trip data written to memory | Set auto_chain from `booking_plan` order → route to first agent |
| `needs_input` | Any agent waiting for user response (asking for clarification, follow-up Q&A, etc.) | Return to user, keep `active_agent` unchanged — next user message goes back to the same agent |
| `failed` + `tool_failures_exceeded` | 3+ consecutive tool failures | Route to General Agent with error context |
| `failed` + `api_unavailable` | External API down | Route to General Agent with error context |
| `active` | Agent mid-processing (multi-step) | Continue in same agent |

**Key**: Signals are part of graph state, not separate messages. The Supervisor never "parses" agent output — it reads structured fields from the shared state.

---

## 4. Smart Tools Layer

### Core Principle

**Tools handle complexity, agents handle conversation.**

The biggest architectural shift in V2. Currently, ~80% of agent prompt lines teach the LLM how to orchestrate tools (handle response codes, format output, manage flags, track state). In V2, all that logic moves into the tools themselves.

### Current vs Proposed Tool Design

```
CURRENT (dumb tools, smart prompts):       PROPOSED (smart tools, simple prompts):
┌──────────────────────┐                   ┌──────────────────────────┐
│ resolve_airport()    │                   │ resolve_airport()        │
│                      │                   │                          │
│ Input: query string  │                   │ Input: query string      │
│ Output: raw data     │                   │ Output:                  │
│  {iata, name,        │                   │  • Resolved? → iata +   │
│   query_is_city}     │                   │    metadata              │
│                      │                   │  • Ambiguous? → formatted│
│ Agent prompt must    │                   │    message for user      │
│ teach LLM to:        │                   │  • Not found? → helpful  │
│ • Handle all status  │                   │    suggestion            │
│   codes              │                   │                          │
│ • Format messages    │                   │ All formatting, edge     │
│ • Track city flags   │                   │ cases, and state updates │
│ • Pass through       │                   │ handled internally.      │
│   instructions       │                   │                          │
│                      │                   │ Agent prompt:            │
│ = 40+ prompt lines   │                   │ "Use resolve_airport.    │
│                      │                   │  If ask_user, show msg." │
│                      │                   │ = 2 prompt lines         │
└──────────────────────┘                   └──────────────────────────┘
```

### Built-in Output Validation (Critic Pattern)

Every smart tool that returns data to the user includes a lightweight **validation step** before returning results. This catches bad data before the agent shows it to the user.

```
Tool call flow (with validation):

  Agent calls search_flights(params)
    │
    ▼
  Tool executes: calls FlightLogic API
    │
    ▼
  Tool validates output (built-in critic):
    • Are dates in the future? (not expired)
    • Are prices reasonable? (not $0, not $999,999)
    • Do origin/destination match request?
    • Are required fields present?
    • Is the formatted display complete?
    │
    ├─ Valid → return formatted results to agent
    │
    └─ Invalid → return error with helpful message
       ("No valid flights found. Try different dates?")
```

This is **not** a separate critic agent — it's a validation function built into each smart tool. Fast (no extra LLM call), reliable (deterministic checks), and targeted (each tool knows its own domain constraints).

**Impact**: Catches 30-60% of cases where raw API data would confuse users (expired fares, missing fields, wrong airports, price anomalies).

### Tool Inventory

#### Shared Tools (used by multiple agents)

| Tool | Used By | Responsibility |
|------|---------|---------------|
| `resolve_airport` | Flight, Itinerary | Resolve any airport/city query to IATA code. Handles disambiguation internally (multi-airport cities). Returns status + formatted user message when clarification needed. Tracks city-vs-airport flag internally. Validates IATA codes before returning. |
| `resolve_city` | Hotel, Itinerary | Resolve city names to city/country pair. Handles ambiguity (e.g., Birmingham UK vs USA) with formatted user message. Validates city/country pair exists. |
| `parse_dates` | Flight, Hotel, Itinerary | Parse ANY date expression into ISO dates. Context-aware: accepts already-known dates so "after 5 days" calculates from departure, not today. Handles relative dates, absolute dates, ranges, durations, seasonal references (with destination context), and holidays. Validates dates are in the future. |

#### Flight-Specific Tools

| Tool | Responsibility |
|------|---------------|
| `search_flights` | Accepts all search params. Handles city-wide multi-airport search internally using is_city flags. Applies time-of-day preference filtering. Returns **formatted, display-ready results** with curated categories (cheapest, fastest, best value). **Built-in validation**: checks prices, dates, route correctness before returning. |
| `select_flight` | Accepts user's natural language selection ("book 1", "cheapest"). Matches to correct flight from previous results. Creates booking session. Returns redirect URL or confirmation. Validates selection matches available options. |

#### Hotel-Specific Tools

| Tool | Responsibility |
|------|---------------|
| `search_hotels` | Accepts all search params (city, country, dates, guests, rooms). Returns **formatted, display-ready results** with categories (best value, cheapest, highest rated). **Built-in validation**: checks availability, pricing, date correctness. Handles star rating filtering on existing results. |
| `select_hotel` | Accepts user's selection. Creates booking session. Returns redirect URL. Validates selection against available results. |

#### Itinerary-Specific Tools

| Tool | Responsibility |
|------|---------------|
| `generate_itinerary` | Takes trip params (destination, dates, travelers, interests). Returns structured day-by-day plan with activities, transport suggestions, accommodation areas. Validates logical flow (no impossible transit times, reasonable daily activity count). |
| `estimate_budget` | Takes itinerary + traveler count. Returns itemized budget breakdown (flights, hotels, activities, food, local transport, misc). Validates totals match line items. |
| `save_itinerary` | Persists finalized itinerary to database. Returns itinerary ID for future reference. |

### Impact of Smart Tools on Prompt Size

| Agent | Current Prompt | V2 Prompt | Reduction |
|-------|---------------|-----------|-----------|
| Flight | 358 lines | ~35 lines | -90% |
| Hotel | 271 lines | ~35 lines | -87% |
| Itinerary | ~200 lines (supervisor + planning) | ~40 lines | -80% |
| Supervisor | N/A (new) | ~20 lines | — |
| General | N/A (new) | ~20 lines | — |
| **Total** | **~829 lines** | **~150 lines** | **-82%** |

---

## 5. Shared Infrastructure

### 5.1 Memory Store

**Replaces**: MongoDB Checkpointer + BookingSessionService + ConversationStateManager

Single unified persistence layer with three tiers:

```
┌──────────────────────────────────────────┐
│              MEMORY STORE                │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │  Conversation Memory            │     │
│  │  (per chat_id, short-term)      │     │
│  │                                 │     │
│  │  • Message history              │     │
│  │  • Active agent + its state     │     │
│  │  • Collected parameters         │     │
│  │  • Search results (for select)  │     │
│  └─────────────────────────────────┘     │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │  Cross-Agent Memory             │     │
│  │  (per chat_id, handoff data)    │     │
│  │                                 │     │
│  │  Written by: any agent          │     │
│  │  Read by: Supervisor only        │     │
│  │  (agents never read each        │     │
│  │   other's data directly)        │     │
│  │                                 │     │
│  │  Uses structured handoff        │     │
│  │  schemas (typed contracts per   │     │
│  │  agent) — no free-form data.    │     │
│  │                                 │     │
│  │  • Trip context from Itinerary  │     │
│  │    (origin, dest, dates,        │     │
│  │     passengers, hotel cities)   │     │
│  │  • Supervisor passes relevant    │     │
│  │    as pre-filled params when    │     │
│  │    handing off to next agent    │     │
│  └─────────────────────────────────┘     │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │  User Memory                    │     │
│  │  (per user_id, long-term)       │     │
│  │                                 │     │
│  │  Backed by LangGraph BaseStore  │     │
│  │  API (cross-thread persistence):│     │
│  │                                 │     │
│  │  • Past bookings                │     │
│  │  • Preferences (seat type,      │     │
│  │    hotel star rating, airlines) │     │
│  │  • Frequent destinations        │     │
│  │                                 │     │
│  │  Namespace: ("preferences",     │     │
│  │             user_id)            │     │
│  │  Supports semantic search via   │     │
│  │  embedding functions.           │     │
│  └─────────────────────────────────┘     │
│                                          │
│  Backend: MongoDB                        │
│  Access: All agents via single interface │
│  User Memory: LangGraph BaseStore API    │
└──────────────────────────────────────────┘
```

**Key designs**:
- Agents read/write through one `MemoryStore` interface. No direct DB access from agents.
- Cross-agent memory uses **structured handoff schemas** (typed contracts per agent), not free-form data. This eliminates the need for a "context adapter" layer — the schema IS the adapter.
- Supervisor reads cross-agent memory to build pre-filled params. No agent reads another agent's data.
- **History filtering on hand-back**: Handled by `ContextEditingMiddleware` (LangChain v1 built-in). When routing to a new agent after hand-back, old tool call/result pairs from the previous agent (e.g., raw `search_flights` results) are automatically cleared while keeping the most recent ones. User messages and agent responses are preserved. No custom filtering code needed — configured per-agent in `create_agent` middleware stack.

### Handoff Schemas

Each agent writes to cross-agent memory using a typed schema:

| Agent | Writes | Schema Fields |
|-------|--------|--------------|
| Itinerary | Trip plan data | origin_iata, destination_iata, departure_date, return_date, passengers, hotel_cities[], daily_plan[] |
| Flight | Booking result | booked (bool), confirmation_id, flight_details |
| Hotel | Booking result | booked (bool), confirmation_id, hotel_details |

Supervisor reads these schemas and maps them to pre-filled params for the next agent. Because schemas are typed, mapping is deterministic — no LLM interpretation needed.

---

### 5.2 Session State (Owned by Supervisor)

**Replaces**: BookingSessionService + ChatService priority routing logic

The Supervisor maintains session state per conversation. This is not a separate routing layer — it's the Supervisor's internal state that it reads on every message to decide how to route.

**Session structure** (per chat_id):

| Field | Purpose |
|-------|---------|
| `active_agent` | Which agent currently owns the conversation (flight, hotel, itinerary, general, or null) |
| `previous_agent` | Which agent was active before (for context after handoff) |
| `detour_return` | If true, auto-return to `previous_agent` when current agent signals DONE (detour pattern) |
| `task_queue` | Pending tasks from multi-query detection (FIFO) |
| `auto_chain` | Ordered list of agents to auto-start after current completes. Set from Itinerary Agent's `booking_plan` — order reflects user's preference, not a hardcoded default |
| `agent_state` | Agent-specific state (collected params, search results, etc.) |

#### Detour/Return Pattern

When a user asks a cross-domain question during an active booking (e.g., "What's the baggage allowance?" during flight booking), the system should answer the question and **automatically return** to the active booking — not force the user through re-classification.

```
Flight Agent is active. User: "Is there a lounge at Heathrow Terminal 5?"
  │
  ▼
Flight Agent: not my domain, but contextually related to the flight
  → Calls hand_back_to_supervisor(reason="contextual question, not a topic change")
  │
  ▼
Supervisor:
  │ Reads hand-back reason: "not a topic change"
  │ Sets: previous_agent = "flight", detour_return = true
  │ Classifies: GENERAL_QUERY
  │ Routes to General Agent
  │
  ▼
General Agent: answers the lounge question → hands back (or signals DONE)
  │
  ▼
Supervisor:
  │ detour_return = true, previous_agent = "flight"
  │ Auto-returns to Flight Agent (no re-classification needed)
  │ Clears detour_return
  │ Sends bridging context: "User's side question was answered. Resume booking flow."
  │
  ▼
Flight Agent: picks up where it left off (state preserved in agent_state)
  │ "Back to your flight booking — would you like to proceed with option 2?"
```

**When `detour_return` is set vs not**:

| Hand-back Reason | `detour_return` | What Happens |
|-----------------|-----------------|-------------|
| "contextual question, not a topic change" | `true` | Auto-return after General answers |
| "User asking about hotels" (topic switch) | `false` | Supervisor classifies normally |
| "User said cancel" | `false` | Supervisor clears everything |
| "User wants to switch to itinerary" | `false` | Supervisor routes to Itinerary |

The agent's LLM decides whether it's a detour or a real topic change — this is the "reason" string in `hand_back_to_supervisor`. The Supervisor parses a simple flag from it, not free-form text analysis.

**Implementation**: Add a `is_detour: bool` parameter to `hand_back_to_supervisor`:

```python
def hand_back_to_supervisor(reason: str, is_detour: bool = False) -> str:
    """
    Call when the user's message is NOT related to your domain.

    Args:
        reason: Why you're handing back.
        is_detour: If True, Supervisor will auto-return to you after the
                   next agent answers. Use for contextual questions that
                   don't represent a real topic change.
    """
```

**Supervisor routing logic**:

```
Message arrives for chat_123
  → Supervisor reads session state
  → active_agent set?
    YES → Forward to active agent (no LLM call, ~5-10ms)
  → No active agent?
    → Classify intent with LLM (~200-400ms)
    → Route to specialist, set as active_agent

After agent processes message:
  → Agent responds normally → Supervisor not involved until next message
  → Agent calls hand_back_to_supervisor(is_detour=false) → Supervisor re-classifies (LLM)
  → Agent calls hand_back_to_supervisor(is_detour=true) → Supervisor routes to General,
    sets detour_return=true, previous_agent saved
  → Agent signals DONE + detour_return=true → Supervisor auto-returns to previous_agent
  → Agent signals DONE + auto_chain pending → Supervisor routes to next in chain
  → Agent signals DONE + task_queue pending → Supervisor pops next task
  → Agent signals DONE (nothing pending) → Supervisor clears active_agent
  → Agent signals FAILED → Supervisor handles gracefully
```

No priority levels. No feature flags. No keyword matching. No heuristic tiers. Supervisor is always the entry point, but forwards without analysis when an active agent is set.

#### Long Conversation Handling (Context Window)

For conversations longer than ~30 turns, the message history can exceed what's useful for agents. This is handled by **LangChain v1 built-in middleware** — no custom implementation needed:

- **`SummarizationMiddleware`**: Automatically compresses older messages when token count exceeds a threshold. Recent messages are kept verbatim. Configured per-agent via `trigger=("tokens", 8000)` and `keep=("messages", 10)`.
- **`ContextEditingMiddleware`**: On hand-back, clears old tool call/result pairs from the previous agent while keeping recent ones. The new agent isn't confused by irrelevant internal state. Configured via `ClearToolUsesEdit(keep=3)`.
- **Cross-agent memory is the durable store**: Important data (trip plan, booking confirmations) lives in cross-agent memory — agents don't rely on scrolling back through conversation history to find it.

Both middleware are configured in each agent's `create_agent` call (see Section 11) and run automatically — no custom pre-processing step needed.

#### Session Timeout & Cleanup

Sessions don't live forever. When users abandon conversations mid-flow, the system must clean up gracefully.

**Session TTL Rules**:

| Session State | TTL | Reason |
|---------------|-----|--------|
| `active_agent` set (mid-booking) | **30 minutes** of inactivity | User likely distracted; booking data still relevant |
| `task_queue` has pending items | **30 minutes** of inactivity | Same as above — queued tasks expire together |
| `auto_chain` in progress | **30 minutes** of inactivity | Mid-chain pause; user may return |
| `auto_chain` paused (interrupted) | **24 hours** of inactivity | User may resume; longer than active because it's already paused |
| No active agent (idle session) | **24 hours** | Cross-agent memory (trip data) may still be useful |
| Cross-agent memory only (no active session) | **7 days** | User may return to book after planning |

**What happens on timeout**:

```
Session expires (30 min inactivity, active_agent was "flight"):
  │
  ▼
Cleanup (background job, not Supervisor):
  1. Clear: active_agent, task_queue, auto_chain
  2. Preserve: cross-agent memory (trip data, booking confirmations)
  3. Preserve: conversation history (for context if user returns)
  4. Log: session expiry event in Langfuse (with last active agent + state)
```

**When user returns after timeout**:

```
User returns after 2 hours, sends "continue booking"
  │
  ▼
Supervisor:
  │ Reads session: active_agent = null (cleared by timeout)
  │ Reads cross-agent memory: trip data exists (preserved)
  │ Classifies intent: BOOK_FLIGHT (or whatever user asks)
  │ Routes to agent with pre-filled params from preserved memory
  │
  │ User experience: "Welcome back! I still have your Japan trip details.
  │   Let me search for flights from Amsterdam to Tokyo, Apr 1-6."
```

**Key**: Timeout clears the active workflow but preserves data. Users don't lose their trip planning — they just need to re-initiate the booking step. Completed bookings (confirmation IDs) are never cleared by timeout.

**Auto-chain expiration**: Paused or incomplete auto-chains expire after **24 hours** of inactivity (configurable). On expiry, clear `auto_chain` but preserve any completed booking confirmations in cross-agent memory. If only flights were booked before the chain paused, the flight confirmation survives — user can re-initiate hotel booking later.

**Implementation**: MongoDB TTL index on `session.last_activity` field. Background cleanup runs via the existing MongoDB TTL mechanism — no separate cron job needed.

---

### 5.3 LLM Gateway

**Replaces**: Scattered LLM instantiation across agents and tools

Single interface for all LLM interactions across the system.

```
┌───────────────────────────────────┐
│          LLM GATEWAY              │
│                                   │
│  Model Selection:                 │
│  • Supervisor → Fast model        │
│    (classification when needed)   │
│  • General Agent → Capable model  │
│  • Flight/Hotel/Itinerary →      │
│    Capable model (tool use)       │
│  • Tools (where LLM needed) →    │
│    Fast model                     │
│                                   │
│  Built-in Features:               │
│  • Automatic Langfuse tracing     │
│  • Prompt management (cached)     │
│  • Token usage tracking per agent │
│  • Model version management       │
│                                   │
│  Handled by LangChain v1          │
│  Middleware (per-agent config):    │
│  • ModelFallbackMiddleware         │
│    (auto-switch on failure)       │
│  • ModelRetryMiddleware            │
│    (retry on transient errors)    │
│  • ModelCallLimitMiddleware        │
│    (cost control per agent)       │
└───────────────────────────────────┘
```

**Benefits**: Change model for any agent in one place. All tracing automatic. No agent code touches LLM configuration directly. Rate limiting, fallback, and retry are middleware — configured per-agent in `create_agent`, not custom infrastructure code.

---

### 5.4 Tool Registry

Central registration of which tools each agent can access.

| Agent | Tools |
|-------|-------|
| Supervisor | None (pure routing — only activates at transitions) |
| General | hand_back_to_supervisor |
| Flight | resolve_airport, parse_dates, search_flights, select_flight, hand_back_to_supervisor |
| Hotel | resolve_city, parse_dates, search_hotels, select_hotel, hand_back_to_supervisor |
| Itinerary | resolve_airport, parse_dates, generate_itinerary, estimate_budget, save_itinerary, hand_back_to_supervisor |

**All agents have `hand_back_to_supervisor`** — this is the handoff mechanism. When an agent's LLM encounters a request outside its domain, it calls this tool to return control to the Supervisor.

**All 3 booking agents follow the same pattern**: resolve location → parse dates → domain-specific tools. This consistency makes the system predictable and easy to extend.

**Adding a new agent**: Register the agent name + its tool list. Supervisor discovers and routes to it automatically. Zero changes to existing agents or Supervisor logic.

---

### 5.5 Tracing & Observability

Full request tracing through Langfuse with enhanced debugging data:

```
User Message
  → [trace: supervisor] session check + routing decision
    → [classify intent — only when no active agent or hand-back]
    → [trace: flight_agent] conversation turn
      → [trace: tool:resolve_airport] resolution call + validation
      → [trace: tool:search_flights] API call + validation + formatting
    → [trace: flight_agent] response generation
  → [trace: supervisor] handback + auto-chain check

Each trace includes:
  • Agent name + routing reason (why this agent was chosen)
  • Tool calls + latency + validation pass/fail
  • LLM model + token usage
  • Session/chat_id
  • Cross-agent memory reads/writes (which keys, which values)
  • Active agent switches + reason (user explicit / auto-chain / queue)
  • Task queue state snapshot
  • User feedback (thumbs up/down)
```

**Enhanced debugging data** (beyond basic tracing):

| Data Point | Purpose |
|-----------|---------|
| Cross-agent memory reads/writes per turn | "Why did Flight Agent get those pre-filled params?" |
| Agent switch reason | "Was this a user request, auto-chain, or queue pop?" |
| Task queue snapshots | "What was queued when the user said 'book everything'?" |
| Tool validation results | "Did the flight results pass validation? What failed?" |

This makes 90% of "why did it do that?" questions answerable directly from traces.

---

## 6. Multi-Query Handling

### How the Supervisor handles multiple requests in one message

```
User: "Plan me a trip to Japan and also book a hotel in Paris for next weekend"

┌─────────────────────────────────────────────┐
│            SUPERVISOR AGENT                 │
│                                         │
│  Step 1: Detect multiple intents        │
│  → Task A: "Plan trip to Japan"         │
│    (itinerary)                          │
│  → Task B: "Book hotel in Paris"        │
│    (hotel)                              │
│                                         │
│  Step 2: Prioritize                     │
│  → Both are interactive flows           │
│  → Run sequentially (need user input)   │
│                                         │
│  Step 3: Execute + Queue                │
│  → Start Task A (itinerary)             │
│  → Queue Task B (hotel)                 │
│  → Tell user: "Let's plan your Japan    │
│    trip first, then I'll handle the     │
│    Paris hotel."                        │
│                                         │
│  Step 4: On Task A completion           │
│  → Auto-start Task B from queue         │
│  → "Now let's find that Paris hotel!"   │
└─────────────────────────────────────────┘
```

### Decision Matrix

| Scenario | Supervisor Action |
|----------|--------------|
| Single intent | Route to one specialist agent |
| Multiple general queries | Route to General Agent (answers all inline) |
| Multiple booking tasks | Queue them, run sequentially, inform user |
| General query + booking mixed | Route general to General Agent, queue booking for specialist |
| Related sub-tasks (e.g., "trip with flights and hotels") | Itinerary Agent plans → Supervisor auto-chains to Flight → Hotel |
| New task while agent is active | Queue it, continue active agent, inform user |
| User says "stop, do X instead" | Pause/cancel active agent, switch to new task |
| "Book everything" after itinerary | Supervisor auto-chains: Flight Agent → Hotel Agent (no user confirmation needed between) |

### Auto-Chain Trigger Detection

Auto-chaining activates when the **Itinerary Agent itself detects** that the user wants to book. Since the Itinerary Agent's LLM has full conversation context, it's the best judge of booking intent.

**How it works**:

```
User: "Looks great, book everything!"
  │
  ▼
Itinerary Agent (active_agent):
  │ LLM sees: itinerary is finalized, user says "book everything"
  │ LLM decides: user wants to book, my planning work is done
  │ Signals: DONE with done_reason = "planning_complete"
  │ Writes to cross-agent memory:
  │   booking_plan: ["flight", "hotel"] | ["hotel", "flight"] | ["flight"] | ["hotel"]
  │   trip_data: {origin, destination, dates, passengers, hotel_cities}
  │
  ▼
Supervisor (activated by DONE signal):
  │ Reads cross-agent memory: booking_plan = ["flight", "hotel"]
  │ Sets auto_chain: ["flight", "hotel"]  (preserves user's order)
  │ Routes to first agent in chain with pre-filled params
```

**Why the agent detects booking intent, not the Supervisor**:
- The Itinerary Agent has **full conversation context** — it knows what was planned
- No keyword matching needed — the LLM understands "sounds great, make it happen" and "alles buchen" equally
- No false positives — "book" said during planning isn't misinterpreted because the agent knows it's still mid-planning
- Works in **any language** — LLM handles multilingual naturally

**What the Itinerary Agent's prompt says**:
```
When the user indicates they want to book, signal DONE with planning_complete
and write booking_plan to cross-agent memory as an ordered list.

Determine the order from what the user said:
- "book everything" / "make it happen" → ["flight", "hotel"]  (default order)
- "book the hotel first, then flights" → ["hotel", "flight"]
- "just book the flights" → ["flight"]
- "only the hotel" → ["hotel"]

You don't do bookings — the Supervisor will route to agents in your specified order.
```

That's it. No keyword lists. No pattern matching tiers. The LLM handles the intent detection as part of normal conversation understanding.

**Observability safety net**: If the Itinerary Agent doesn't signal `planning_complete` when it should (LLM misses the booking intent), the user will simply repeat themselves — "I said book the flights" — and the agent gets another chance. To detect this failure mode, log every Itinerary Agent turn where `planning_complete` is NOT set but the user message contains high-confidence booking language. Review these in Langfuse to measure miss rate and tune the agent's prompt if needed. This is monitoring, not routing logic.

### Auto-Chaining (Seamless Booking After Planning)

```
User: "Looks great, book everything!"
  │
  ▼
Itinerary Agent: signals DONE + writes booking_plan: ["flight", "hotel"]
  │
  ▼
Supervisor (activated by DONE signal):
  │ Reads booking_plan from cross-agent memory → sets auto_chain: ["flight", "hotel"]
  │ Reads trip_data: origin=AMS, dest=NRT, dates=Apr 1-6, passengers=2, hotel=Tokyo
  │
  ▼
Flight Agent: starts with pre-filled params → searches → user selects → books
  │ Signals: DONE
  │
  ▼
Supervisor: auto_chain has ["hotel"] remaining
  │ "Flights booked! Now searching hotels..."
  │
  ▼
Hotel Agent: starts with pre-filled params → searches → user selects → books
  │ Signals: DONE
  │
  ▼
Supervisor: auto_chain empty
  │ "All set! Flights and hotels for your Japan trip are booked."
```

**Flexible ordering** — the Itinerary Agent decides chain order based on what the user said:

```
User: "Book the hotel first, then get flights"
  → Itinerary Agent writes booking_plan: ["hotel", "flight"]
  → Supervisor chains: Hotel Agent → Flight Agent

User: "Just book the flights for now"
  → Itinerary Agent writes booking_plan: ["flight"]
  → Supervisor chains: Flight Agent only (no hotel)
```

**Key**: User experiences one seamless flow. Under the hood, the Itinerary Agent determines *what* to book and *in what order* — the Supervisor executes the chain. No hardcoded `[flight, hotel]` ordering anywhere.

### Mid-Conversation Interruption

With the handoff pattern, interruptions are handled naturally by the active agent:

```
Active: Flight Agent (mid-booking)
User: "Actually, also find me a hotel in the same city"

Supervisor: active_agent = "flight" → forward to Flight Agent (no LLM)

Flight Agent:
  │ LLM sees: user wants a hotel (different domain)
  │ Two possible behaviors (depends on agent prompt):
  │
  │ Option A: Hand back immediately
  │   → Calls hand_back_to_supervisor(reason="User wants hotel booking")
  │   → Supervisor queues hotel task, returns to Flight Agent to finish
  │
  │ Option B: Acknowledge and continue (recommended)
  │   → Responds: "Got it! I'll note the hotel request. Let's finish
  │     your flight first, then we'll handle the hotel."
  │   → Writes hotel request to cross-agent memory
  │   → Continues flight booking
  │   → On DONE: Supervisor sees hotel task in memory → routes to Hotel Agent

Option B is preferred because it doesn't interrupt the user's current flow.
```

### Interruption During Auto-Chain

When user changes direction mid-auto-chain, the active agent handles it:

```
Auto-chain active: Flight Agent showing results (hotel queued next)
User: "Actually, change the dates to next month"

Supervisor: active_agent = "flight" → forward to Flight Agent (no LLM)

Flight Agent:
  │ LLM sees: "change dates" → this IS flight-related
  │ Handles it normally (re-searches with new dates)
  │ Auto-chain stays intact — Supervisor isn't involved

---

User: "Actually, forget the flights. Just book the hotel."

Flight Agent:
  │ LLM sees: user wants to cancel flights and switch to hotels
  │ Calls hand_back_to_supervisor(reason="User cancelled flight, wants hotel only")
  │
  ▼
Supervisor:
  │ Clears flight from auto-chain
  │ Routes to Hotel Agent with pre-filled params
```

**Key**: The active agent's LLM decides what's a same-domain change (handle it) vs what's a different-domain request (hand back). No keyword matching, no interruption classification logic in the Supervisor.

| Interruption Type | Who Handles | What Happens |
|-------------------|------------|------------|
| Same-domain change ("change dates") | Active agent handles directly | Auto-chain stays intact |
| Different-domain request ("find a hotel") | Agent notes it or hands back | Supervisor queues/routes |
| Explicit switch ("now do hotels", "skip to hotel") | Agent calls hand_back_to_supervisor | Supervisor treats as new intent, queues current task |
| "Cancel" / "start over" | Agent calls hand_back_to_supervisor | Supervisor clears everything |
| "Continue" / "what's next" | Active agent or Supervisor | Resumes from where paused |

---

## 7. Request Lifecycle

### 7.1 Direct Booking Flow

```
User: "Book me a flight from London to Paris tomorrow"
  │
  ▼
API: POST /chat/message
  │
  ▼
Supervisor:
  │ Reads session: no active agent
  │ Classifies intent (~200ms): BOOK_FLIGHT
  │ Sets session: {active_agent: "flight"}
  │ Routes to Flight Agent
  │
  ▼
Flight Agent (now active_agent):
  │ Extracts from message: origin=London, dest=Paris, date=tomorrow
  │ Calls tools in parallel:
  │   → resolve_airport("London") → resolved, LHR, is_city=true (validated ✓)
  │   → resolve_airport("Paris")  → resolved, CDG, is_city=true (validated ✓)
  │   → parse_dates("tomorrow")   → departure_date=2026-02-20 (validated ✓)
  │
  │ Missing: trip type, passengers
  │ Responds: "One-way or round-trip?"
  │
  ▼
User: "Round trip, returning in 5 days, just me"
  │
  ▼
Supervisor: active_agent = "flight" → forward to Flight Agent (no LLM)
  │
  ▼
Flight Agent:
  │ Calls parse_dates("returning in 5 days", known_dates={departure: "2026-02-20"})
  │   → return_date=2026-02-25 (validated ✓)
  │ Calls search_flights(all params)
  │   → validation: prices ok ✓, dates future ✓, routes match ✓
  │   → formatted display-ready results
  │ Shows results to user
  │
  ▼
User: "Book option 1"
  │
  ▼
Supervisor: active_agent = "flight" → forward to Flight Agent (no LLM)
  │
  ▼
Flight Agent:
  │ Calls select_flight("book option 1")
  │   → validation: selection matches available options ✓
  │   → redirect_url for booking form
  │ Shows booking link to user
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal):
  │ Clears active_agent
  │ "Flight booked! Anything else I can help with?"
```

### 7.2 Itinerary Flow (Agent Handoff Pattern)

```
User: "Plan me a 5-day trip to Japan in April, 2 people"
  │
  ▼
Supervisor:
  │ Reads session: no active agent
  │ Classifies intent (~200ms): CREATE_ITINERARY
  │ Sets session: {active_agent: "itinerary"}
  │ Routes to Itinerary Agent
  │
  ▼
Itinerary Agent (now active_agent):
  │ Extracts: destination=Japan, duration=5 days, month=April, travelers=2
  │ Missing: origin city
  │ Responds: "Where will you be flying from?"
  │
  ▼
User: "Amsterdam"
  │
  ▼
Supervisor: active_agent = "itinerary" → forward to Itinerary Agent (no LLM)
  │
  ▼
Itinerary Agent:
  │ Resolves airport: Amsterdam → AMS
  │ Parses dates: "5 days in April" → Apr 1-6
  │ Generates itinerary: Day-by-day plan (Tokyo, Kyoto, Osaka)
  │ Writes to cross-agent memory:
  │   {origin: AMS, dest: NRT, dates: Apr 1-6, passengers: 2,
  │    hotel_cities: [{city: Tokyo, checkin: Apr 1, checkout: Apr 3},
  │                   {city: Kyoto, checkin: Apr 3, checkout: Apr 6}]}
  │ Shows itinerary to user
  │
  ▼
User: "Looks great, book everything"
  │
  ▼
Supervisor: active_agent = "itinerary" → forward to Itinerary Agent (no LLM)
  │
  ▼
Itinerary Agent:
  │ LLM understands: user wants to book everything, planning is done
  │ Writes booking_plan: ["flight", "hotel"] to cross-agent memory
  │ Signals: DONE (done_reason: "planning_complete")
  │
  ▼
Supervisor (activated by DONE signal):
  │ Reads cross-agent memory → booking_plan = ["flight", "hotel"], trip data available
  │ Sets auto_chain: ["flight", "hotel"]
  │ Hands off to first in chain (Flight Agent) with pre-filled params
  │
  ▼
Flight Agent (now active_agent):
  │ All params present → searches immediately (validated ✓)
  │ Shows results → User selects (Supervisor forwards, no LLM) → Books
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal):
  │ auto_chain: [hotel] remaining
  │ "Flights booked! Now searching hotels for your trip..."
  │ Hands off to Hotel Agent with pre-filled params from schema
  │
  ▼
Hotel Agent (now active_agent):
  │ Params present → searches immediately (validated ✓)
  │ Shows results → User selects (Supervisor forwards, no LLM) → Books
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal): auto_chain empty
  │ "All set! Flights and hotels for your Japan trip are booked."
```

### 7.3 Multi-Query Flow

```
User: "Book a flight to Tokyo and find me a hotel in London"
  │
  ▼
Supervisor:
  │ Reads session: no active agent
  │ Classifies intent (~200ms): detects 2 tasks
  │   → flight (Tokyo) + hotel (London)
  │ Starts: Flight Agent for Tokyo (becomes active_agent)
  │ Queues: Hotel Agent for London
  │ Responds: "I'll help with both! Let's start with your Tokyo flight,
  │           then I'll find the London hotel."
  │
  ▼
Flight Agent handles Tokyo flight booking (Supervisor forwards all messages, no LLM)...
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal):
  │ Checks queue → hotel task pending
  │ Starts: Hotel Agent for London (becomes active_agent)
  │ Responds: "Tokyo flight is booked! Now let's find your London hotel."
  │
  ▼
Hotel Agent handles London hotel booking (Supervisor forwards all messages, no LLM)...
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal): "All done! Flight to Tokyo and hotel in London are both booked."
```

### 7.4 General Query Flow

```
User: "What's the best time to visit Bali?"
  │
  ▼
Supervisor:
  │ Reads session: no active agent
  │ Classifies intent (~200ms): GENERAL_QUERY
  │ Routes to General Agent (becomes active_agent)
  │
  ▼
General Agent:
  │ Answers using travel knowledge
  │ "The best time to visit Bali is during the dry season (April-October)..."
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal): clears active_agent
```

### 7.5 Topic Change Flow (Hand-Back in Action)

```
Active: Flight Agent (user was searching flights to Tokyo)
User: "Actually, what's the weather like in Tokyo in April?"
  │
  ▼
Supervisor: active_agent = "flight" → forward to Flight Agent (no LLM)
  │
  ▼
Flight Agent:
  │ LLM sees: user asking about weather, not flights
  │ Calls hand_back_to_supervisor(reason="User asking about weather")
  │
  ▼
Supervisor (activated by hand-back):
  │ Classifies: GENERAL_QUERY
  │ Saves flight session state (for potential return)
  │ Sets active_agent = "general"
  │ Routes to General Agent
  │
  ▼
General Agent:
  │ Answers: "Tokyo in April averages 15-20°C with cherry blossoms..."
  │ Signals: DONE
  │
  ▼
Supervisor (activated by DONE signal):
  │ Previous agent was "flight" with saved state
  │ "By the way, we were looking at flights to Tokyo. Want to continue?"
  │ If user says yes → restore Flight Agent as active_agent
  │ If user says something else → classify new intent
```

---

## 8. Human-in-the-Loop

Each agent handles its own user interactions autonomously. No central `ask_user_node` needed.

### Interaction Points by Agent

| Agent | User Interactions |
|-------|------------------|
| **Supervisor** | Routing messages only ("I'll handle X first, then Y"), auto-chain announcements |
| **General** | Full conversational responses to travel questions |
| **Flight** | Collecting missing info ("Where from?", "One-way or round-trip?"), airport disambiguation (via smart tool), trip type changes |
| **Hotel** | Collecting missing info ("Which city?", "Check-in and check-out?"), city disambiguation (via smart tool), star rating refinement |
| **Itinerary** | Collecting trip vision ("Where from?", "What are your interests?"), itinerary modifications ("Want to change anything?"), signaling readiness to book |

### Disambiguation (Handled by Smart Tools)

```
User: "Flight to London"
  │
  ▼
Flight Agent calls resolve_airport("London")
  │
  ▼
Smart tool returns:
  status: "ask_user"
  message: "London has multiple airports:
            1. Heathrow (LHR)
            2. Gatwick (LGW)
            3. Stansted (STN)
            Which one do you prefer?"
  │
  ▼
Flight Agent: Shows the tool's message directly (zero prompt instructions needed)
  │
  ▼
User: "Heathrow"
  │
  ▼
Flight Agent calls resolve_airport("Heathrow")
  │
  ▼
Smart tool returns: status: "resolved", iata: "LHR", is_city: false (validated ✓)
  │
  ▼
Flight Agent continues with remaining fields
```

**Key insight**: The agent doesn't need 40 lines of prompt explaining how to handle disambiguation. The tool formats the message, the agent just relays it. The tool validates the result, the agent just trusts it.

---

## 9. Edge Cases & Failure Handling

### 9.1 Supervisor Edge Cases

| Scenario | Supervisor Action | decision_type |
|----------|------------------|---------------|
| User says "cancel" / "start over" / "forget it" | Clear active_agent, task_queue, auto_chain. Respond: "Starting fresh. What would you like to do?" | `cancel_reset` |
| User says "forget the previous plan" | Clear cross-agent memory for this chat + reset session. Itinerary data is wiped. | `cancel_reset` |
| User sends empty / gibberish message | Route to General Agent (let it handle gracefully) | `classify_new` |
| User sends message during agent processing | Queue message, process after current turn completes | N/A (handled at API level) |
| Unknown intent (Supervisor can't classify) | Route to General Agent as fallback | `classify_new` |
| Unsupported domain ("Book a rental car", "Get travel insurance", "Book a cruise") | Supervisor responds directly: "I currently specialize in flights, hotels, and trip planning. I can search flights, book hotels, plan itineraries, and answer general travel questions. Would you like help with one of those, or should I note this request for future improvement?" Does NOT route to any agent. | `no_matching_agent` |

### 9.2 Task Queue Limits

**Hard limit: 5 queued tasks per chat session.**

If user tries to add more:
- Supervisor responds: "You have several tasks queued already. Let me finish these first, then we can add more."
- New task is rejected (not silently dropped)
- Existing queue continues processing

**Why 5**: Travel bookings require user interaction (selecting flights/hotels). More than 5 queued tasks means the user will lose context by the time later tasks start. Better to complete existing tasks first.

### 9.3 Repeated Tool Failures

When a specialist agent's tools fail repeatedly, the Supervisor detects and recovers:

```
Flight Agent calls search_flights → API error (1st attempt)
Flight Agent retries → API error (2nd attempt)
Flight Agent retries → API error (3rd attempt)
Flight Agent signals: FAILED (3 consecutive tool failures)
  │
  ▼
Supervisor detects FAILED signal:
  │ Clears active_agent
  │ Routes to General Agent with context:
  │   "The flight search service is temporarily unavailable."
  │
  ▼
General Agent:
  │ "I'm sorry, the flight search is temporarily unavailable.
  │  You can try again in a few minutes, or I can help with
  │  something else in the meantime."
```

**Failure threshold**: 3 consecutive tool validation failures or API errors within a single agent session → Supervisor takes over with graceful degradation.

**Important**: Individual tool retries (e.g., API timeout → retry) are handled by `ToolRetryMiddleware` (LangChain v1 built-in) — configured per-agent with `max_retries=2` and exponential backoff. No custom tenacity decorators needed inside tools. The Supervisor only intervenes when the agent signals it cannot proceed after retries are exhausted.

### 9.4 Partial Booking Recovery (Auto-Chain Failure)

When auto-chain completes some bookings but fails on others, the system must handle the partial state gracefully.

```
Auto-chain: Flight → Hotel
  │
  ▼
Flight Agent: books successfully ✓
  │ Writes to cross-agent memory: {booked: true, confirmation_id: "FL-12345"}
  │ Signals: DONE
  │
  ▼
Hotel Agent: search fails (API down) or user cancels mid-booking
  │ Signals: FAILED or user says "forget the hotel"
  │
  ▼
Supervisor:
  │ Reads cross-agent memory:
  │   flight: {booked: true, confirmation_id: "FL-12345"}
  │   hotel: {booked: false}
  │
  │ Actions:
  │ 1. Inform user of partial state:
  │    "Your flight is booked (confirmation: FL-12345).
  │     The hotel booking couldn't be completed — [reason].
  │     Would you like to try again, or continue without a hotel?"
  │ 2. Clear auto-chain (remaining steps cancelled)
  │ 3. Keep flight booking data in cross-agent memory (not wiped)
  │ 4. If user says "try again" → re-route to Hotel Agent with same params
  │ 5. If user says "forget it" → clear session, hotel data only
```

**Key rules for partial booking**:
- **Never silently lose a completed booking** — always show confirmation IDs
- **Never auto-cancel a successful booking** because a later step failed
- **Cross-agent memory preserves completed booking data** even after failures
- **User decides** whether to retry the failed step or move on
- **Supervisor explicitly states** what succeeded and what failed — no ambiguity

| Scenario | Flight Status | Hotel Status | Supervisor Action |
|----------|--------------|-------------|-------------------|
| Both succeed | ✅ Booked | ✅ Booked | "All set! Both booked." |
| Flight succeeds, hotel fails | ✅ Booked | ❌ Failed | Show flight confirmation + offer hotel retry |
| Flight succeeds, user cancels hotel | ✅ Booked | ⏭ Skipped | Show flight confirmation, clear hotel from chain |
| Flight fails, hotel not started | ❌ Failed | ⏸ Not started | Offer flight retry, hotel stays in chain |

### 9.5 Rate Limiting

Rate limiting uses a mix of **LangChain v1 middleware** (per-agent) and **API-level middleware** (per-user):

| Protection | Where | Limit |
|-----------|-------|-------|
| Messages per minute per user | FastAPI middleware | 30 msg/min |
| LLM calls per agent run | `ModelCallLimitMiddleware` (per-agent) | 15 calls/run |
| Tool calls per agent run | `ToolCallLimitMiddleware` (per-agent) | 30 calls/run |
| Concurrent active sessions per user | Session state | 3 sessions |

**Per-agent limits** are configured in each agent's middleware stack — no custom rate-limiting infrastructure needed. When a middleware limit is hit, the agent gracefully stops (configurable: `exit_behavior="end"` or `"error"`). API-level rate limiting (per-user) remains in FastAPI middleware.

---

## 10. Scalability & Extensibility

### 10.1 Adding a New Specialist Agent

**Example**: Adding an **Activity Agent** for tours, experiences, cooking classes.

| Step | What to Do | Files Touched |
|------|-----------|---------------|
| 1 | Create agent with ~35 line prompt | 1 new file |
| 2 | Create smart tools (search_activities, book_activity) with built-in validation | 1-2 new files |
| 3 | Register agent + tools in Tool Registry | 1 existing file (add 1 line) |
| 4 | Done — Supervisor routes naturally | 0 changes |

**Compare to current system**: Add intent to IntentRecognizer, add priority level in ChatService, add feature flag, create handler, wire routing — touching 5+ existing files.

### 10.2 Adding a New Tool to Existing Agent

| Step | What to Do |
|------|-----------|
| 1 | Create the tool (with built-in validation) |
| 2 | Add to relevant agent(s) in Tool Registry |
| 3 | Done — agent discovers and uses it |

No prompt changes needed. The agent's LLM naturally discovers available tools.

### 10.3 Growth Path

```
Current 4 specialist agents:
  Flight ─ Hotel ─ Itinerary ─ General

Future expansion (each = 1 agent + 2-3 tools + 1 registry line):
  Flight ─ Hotel ─ Itinerary ─ General ─ Activity ─ Car Rental ─ Insurance ─ Visa
```

Zero changes to existing agents or Supervisor when adding new domains.

### 10.4 Scaling Patterns

| Scaling Need | Solution | What Changes |
|-------------|----------|-------------|
| More travel domains | Add specialist agent + tools | New files only |
| Better tool performance | Optimize individual tools | Tool code only |
| Different LLM per agent | Configure in LLM Gateway | Gateway config only |
| More concurrent users | Scale API + session store horizontally | Infrastructure only |
| Better agent responses | Update agent prompts (~35 lines) | 1 prompt file |
| New data sources | Add/modify tools | Tool code only |
| Multi-language support | Add translation layer in LLM Gateway | Gateway only |
| Better observability | Enhance tracing | Tracing config only |
| A/B test routing | Swap Supervisor model/prompt | Supervisor config only |
| A/B test domain agent | Swap one agent model/prompt | Agent config only |

**Key pattern**: Every scaling concern maps to exactly one layer. No change requires touching multiple layers simultaneously.

---

## 11. LangGraph Implementation

### Why LangGraph (Not OpenAI Agents SDK)

The handoff pattern is inspired by OpenAI Agents SDK, but we implement it on **LangGraph v1** + **LangChain v1** because:

| Requirement | LangGraph v1 + LangChain v1 | OpenAI Agents SDK |
|-------------|-----------|-------------------|
| Gemini model support | ✅ Native | ❌ OpenAI models only |
| MongoDB persistence | ✅ Built-in checkpointer | ❌ Custom implementation |
| Langfuse tracing | ✅ Native integration | ❌ Custom implementation |
| Human-in-the-loop | ✅ `interrupt()` + `HumanInTheLoopMiddleware` | ❌ Custom implementation |
| Deterministic routing | ✅ Conditional edges | ❌ All routing via LLM |
| Active agent pattern | ✅ Via `active_agent` state + conditional edges | ✅ Native handoff |
| Middleware (summarization, retries, limits) | ✅ 14 built-in middleware | ❌ Custom implementation |
| Cross-thread memory (user preferences) | ✅ `BaseStore` API | ❌ Custom implementation |

**Note**: We do NOT use the `langgraph-swarm` library (v0.1.0, known bugs). We build the handoff pattern directly on core LangGraph + LangChain middleware, which are stable and mature.

### Graph Structure

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver

class AgentState(TypedDict):
    messages: list[BaseMessage]
    active_agent: str | None          # Which agent owns the conversation
    previous_agent: str | None        # For context after hand-back
    task_queue: list[dict]            # Pending tasks from multi-query
    auto_chain: list[str]             # Next agents after current completes
    agent_signal: dict | None         # DONE/FAILED/needs_input/hand_back signal
    cross_agent_memory: dict          # Handoff data between agents
    chat_id: str
    user_id: str

# Supervisor is ALWAYS the entry point
# Inside supervisor_node, it checks active_agent:
#   - If set → forward to active agent (no LLM call)
#   - If not set → classify intent with LLM → route
#   - If agent signaled DONE → check auto-chain / queue
#   - If agent handed back → re-classify with LLM

async def supervisor_node(state: AgentState) -> dict:
    """Entry point for every message. Thin supervisor."""
    active = state.get("active_agent")
    signal = state.get("agent_signal", {})

    # Agent handed back or signaled DONE/FAILED → needs LLM decision
    if signal.get("agent_status") in ("hand_back", "done", "failed"):
        return await handle_transition(state, signal)

    # Active agent set → forward immediately (no LLM)
    if active:
        return {"target_agent": active, "decision_type": "forward"}

    # No active agent → classify with LLM
    return await classify_and_route(state)

# After Supervisor decides, route to the target agent
def route_from_supervisor(state: AgentState) -> str:
    return state.get("target_agent", "general")

# After an agent runs, check its signal
def after_agent(state: AgentState) -> str:
    signal = state.get("agent_signal", {})
    status = signal.get("agent_status")

    if status in ("done", "failed", "hand_back"):
        return "supervisor"    # Supervisor handles the transition
    elif status == "needs_input":
        return END             # Wait for next user message
    return END                 # Default: wait for user

# Build the graph
graph = StateGraph(AgentState)

# Supervisor is the entry point — always
graph.set_entry_point("supervisor")
graph.add_node("supervisor", supervisor_node)
graph.add_node("flight", flight_agent_node)
graph.add_node("hotel", hotel_agent_node)
graph.add_node("itinerary", itinerary_agent_node)
graph.add_node("general", general_agent_node)

# Supervisor routes to the target agent
graph.add_conditional_edges("supervisor", route_from_supervisor)

# After each agent: check signal → back to supervisor or END
for agent in ["flight", "hotel", "itinerary", "general"]:
    graph.add_conditional_edges(agent, after_agent)

# Compile with MongoDB persistence
checkpointer = MongoDBSaver(mongodb_client, db_name="voya")
app = graph.compile(checkpointer=checkpointer)
```

### Agent Nodes Use `create_agent` + Middleware

Each specialist agent uses LangChain v1's `create_agent` as its inner ReAct engine, wrapped in a thin custom node that extracts signals for the Supervisor. This gives us built-in middleware (summarization, retries, cost limits) for free — no custom ReAct loop needed.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    ToolRetryMiddleware,
    ModelCallLimitMiddleware,
    ContextEditingMiddleware,
)

# Inner engine: create_agent handles ReAct loop + middleware
flight_inner_agent = create_agent(
    model=ChatGoogleGenerativeAI(model="gemini-2.0-flash"),
    tools=[resolve_airport, parse_dates, search_flights, select_flight, hand_back_to_supervisor],
    middleware=[
        SummarizationMiddleware(
            model="gemini-2.0-flash",
            trigger=("tokens", 8000),     # Summarize when context > 8K tokens
            keep=("messages", 10),        # Keep last 10 messages verbatim
        ),
        ToolRetryMiddleware(max_retries=2, backoff_factor=2),  # Auto-retry failed API calls
        ModelCallLimitMiddleware(run_limit=15),                 # Prevent runaway loops
        ContextEditingMiddleware(                                # Filter old tool outputs on hand-back
            strategy=ClearToolUsesEdit(keep=3),
        ),
    ],
)

# Custom node: wraps inner agent, extracts signal for Supervisor
async def flight_agent_node(state: AgentState) -> dict:
    result = await flight_inner_agent.ainvoke(state)

    # Check if agent called hand_back_to_supervisor
    signal = extract_agent_signal(result)  # Small custom middleware or post-processing
    return {
        "messages": result["messages"],
        "agent_signal": signal,
        "active_agent": None if signal["agent_status"] == "hand_back" else "flight",
        "previous_agent": "flight" if signal["agent_status"] == "hand_back" else state.get("previous_agent"),
    }
```

**What `create_agent` handles** (no custom code needed):
- ReAct loop (think → call tool → observe → repeat)
- Conversation summarization when context grows large
- Auto-retry on tool failures with exponential backoff
- Loop protection (max model calls per run)
- Old tool output cleanup

**What the custom wrapper handles** (Voya-specific):
- `agent_signal` extraction for Supervisor routing
- `hand_back_to_supervisor` detection and state updates
- `active_agent` / `previous_agent` state management

### Message Flow Through the Graph

```
User message → graph.invoke({"messages": [user_msg], ...}, config={"configurable": {"thread_id": chat_id}})
  │
  ▼
supervisor_node (always first):
  │ active_agent = "flight"? → forward (no LLM) → flight_agent_node
  │ active_agent = None?     → classify (LLM)   → target agent node
  │ agent_signal = "done"?   → handle transition → next agent or END
  │
  ▼
agent processes → returns state update with agent_signal
  │
  ▼
after_agent(state):
  │ "needs_input" → END (respond to user, wait for next message)
  │ "done"        → supervisor_node (check auto-chain)
  │ "hand_back"   → supervisor_node (re-classify)
  │ "failed"      → supervisor_node (handle error)
```

**Persistence**: LangGraph's `MongoDBSaver` automatically persists the full state (including `active_agent`, `task_queue`, `auto_chain`) after every step. When the next message arrives, state is loaded from MongoDB — the `active_agent` is preserved across requests.

---

## 11.5 Middleware Stack (Built-in vs Custom)

LangChain v1 provides 14 built-in middleware that eliminate the need for custom implementations of common concerns. Each agent's `create_agent` call composes the middleware it needs.

### Built-in Middleware We Use

| Middleware | Purpose | Replaces | Per-Agent Config |
|-----------|---------|----------|-----------------|
| `SummarizationMiddleware` | Auto-compress long conversations | Custom summarization code | `trigger=("tokens", 8000), keep=("messages", 10)` |
| `ContextEditingMiddleware` | Clear old tool outputs on hand-back | Custom history filtering | `ClearToolUsesEdit(keep=3)` |
| `ToolRetryMiddleware` | Retry failed tool calls with backoff | Custom tenacity decorators in tools | `max_retries=2, backoff_factor=2` |
| `ModelCallLimitMiddleware` | Prevent runaway agent loops | Custom loop counters | `run_limit=15` |
| `ToolCallLimitMiddleware` | Cap tool executions per run | Custom tool call counters | `run_limit=30` |
| `ModelFallbackMiddleware` | Switch to cheaper model on failure | Custom fallback logic in LLM Gateway | `fallback_models=[...]` |
| `ModelRetryMiddleware` | Retry on Gemini API transient errors | Custom try/except in agent code | `max_retries=2` |
| `PIIMiddleware` | Redact credit cards, emails in chat logs | No current equivalent (new security win) | `types=["credit_card", "email"], strategy="redact"` |
| `HumanInTheLoopMiddleware` | Pause for approval on booking tools | Custom `interrupt()` patterns | `interrupt_on={"select_flight": {...}}` |

### Custom Middleware (Voya-Specific)

| Middleware | Purpose | ~Lines |
|-----------|---------|--------|
| `AgentSignalMiddleware` | Extract `agent_signal` from agent output for Supervisor routing | ~20 |

### What Remains Custom (Not Middleware)

These are Voya-specific business logic — correctly custom, not generic concerns:

| Component | Why Custom |
|-----------|-----------|
| Supervisor StateGraph | Our routing pattern (active_agent forwarding, auto-chain, task queue, detour/return) |
| `hand_back_to_supervisor` tool | Multi-agent handoff signal |
| Cross-agent memory schemas | Typed contracts between agents (trip data, booking results) |
| Smart tools (validation, formatting) | Domain-specific (FlightLogic API, hotel data, airport resolution) |
| Critical Action Safety Net | ~10 lines string matching for cancel/stop |
| Session timeout & cleanup | Voya-specific TTL rules (MongoDB TTL index) |

### Impact: ~30% Custom Code, ~70% Built-in

Before LangChain v1 middleware, we estimated ~60% custom code. The middleware system eliminates all generic infrastructure concerns (retries, summarization, limits, fallbacks, PII, history filtering), leaving only Voya-specific business logic as custom — which is exactly what should be custom.

---

## 12. Benefits Over Current System

### Side-by-Side Comparison

| Aspect | Current (V1) | Proposed (V2) |
|--------|-------------|---------------|
| **Routing** | IntentRecognizer (3-tier) + 5 priority levels + 4 feature flags | Handoff pattern: active agent receives directly, Supervisor only at transitions |
| **Code paths** | Dual paths for everything (legacy + LangGraph) | Single path per flow |
| **Agent prompts** | 358 lines (flight), 271 lines (hotel), ~200 (itinerary) | ~35, ~35, ~40, ~20, ~20 lines respectively |
| **Adding new agent** | Touch 5+ files, add feature flag, wire routing | 1 agent + tools + 1 registry line |
| **Itinerary planning** | 5 rigid stages, hardcoded transitions | Dynamic reasoning, no fixed stages |
| **State management** | 3 separate systems | 1 unified Memory Store |
| **General queries** | Separate GeneralTravelHandler class | Dedicated General Agent (proper responses) |
| **Multi-query** | Not supported | Built-in task queue + auto-chaining |
| **Dead code** | ~15 legacy files behind feature flags | None — single implementation per feature |
| **Tool design** | Dumb tools + massive prompts | Smart tools with built-in validation + minimal prompts |
| **Debugging** | Navigate 5 priority levels + feature flag branches | Linear trace: Supervisor → Agent → Tool (with full context) |
| **Onboarding** | Read 800+ lines of prompts + understand complex routing | Read ~35-line prompt + tool descriptions |
| **Agent handoff** | BookingSessionService + priority routing | hand_back_to_supervisor tool + auto-chaining |
| **Conversation interruption** | Not handled cleanly | Task queue with explicit pause/resume |
| **Output quality** | Raw API data shown to user | Built-in tool validation catches bad data |
| **Infrastructure** | Custom retry, fallback, rate limiting code | LangChain v1 middleware (built-in, composable) |
| **PII protection** | None | `PIIMiddleware` redacts credit cards, emails |
| **Monolith risk** | ChatService (1000 lines) | Supervisor (~20 lines) — only activates at transitions |
| **Latency (active session)** | IntentRecognizer + handler (~2-3s) | Supervisor forward (~5-10ms state read, no LLM) |
| **Latency (new intent)** | IntentRecognizer + handler (~2-3s) | Supervisor (~200-400ms) + agent |

### Quantified Improvements

| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Total agent prompt lines | ~829 | ~150 | **-82%** |
| Files involved in routing | ~6 | 1 (Supervisor Agent) | **-83%** |
| Feature flags | 4 | 0 | **-100%** |
| State management systems | 3 | 1 | **-67%** |
| Routing latency (active session) | ~2-3s (IntentRecognizer) | ~5-10ms (Supervisor forward, no LLM) | **-99%** |
| Routing latency (new intent) | ~2-3s (IntentRecognizer) | ~200-400ms (Supervisor fast model) | **-85%** |
| Steps to add new agent | ~10 across 5+ files | 3 across 2 files | **-70% effort** |
| Dead/legacy code files | ~15 | 0 | **-100%** |
| User-facing bad data | No validation | Built-in tool validation | **-30-60% errors** |
