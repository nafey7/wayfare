# Langfuse Prompt Management

**Total Prompts**: 7 | **Cache TTL**: 5 minutes | **Last Updated**: January 2026

Voya uses Langfuse for centralized prompt management. All prompts have hardcoded fallbacks.

**Naming Convention**: `voya-{agent-name}-{purpose}`

---

## All Prompts Summary

| Prompt Name | Agent | Stage/Purpose | Variables | Type |
|-------------|-------|---------------|-----------|------|
| `voya-router-agent` | Router | Intent classification | `{{current_date}}`, `{{current_year}}` | ReAct |
| `voya-planning-trip-extraction` | Planning | INITIAL_VISION - Extract trip info | None | Structured Chain |
| `voya-planning-trip-acknowledgment` | Planning | INITIAL_VISION - Acknowledge user | None | Structured Chain |
| `voya-planning-itinerary-generation` | Planning | ROUTE_REFINEMENT - Generate itinerary | `{{origin}}`, `{{destination}}`, `{{departure_date}}`, `{{return_date}}`, `{{adults}}`, `{{children}}`, `{{interests}}` | Structured Chain |
| `voya-planning-budget-estimation` | Planning | BUDGET_ESTIMATION - Calculate costs | `{{origin}}`, `{{destination}}`, `{{departure_date}}`, `{{return_date}}`, `{{adults}}`, `{{children}}`, `{{interests}}` | Structured Chain |
| `voya-flight-agent` | Flight | Search and book flights | `{{current_date}}`, `{{current_year}}`, `{{next_year}}` | ReAct |
| `voya-hotel-agent` | Hotel | Search and book hotels | `{{current_date}}`, `{{current_year}}`, `{{next_year}}` | ReAct |

---

## Prompt Details

### Router Agent

**`voya-router-agent`**
- **Purpose**: Classifies user intent to route messages to the correct agent
- **Variables**: `{{current_date}}`, `{{current_year}}` (no `next_year`)
- **Detects**: `BOOK_FLIGHT`, `BOOK_HOTEL`, `CREATE_ITINERARY`, `GENERAL`
- **Used in**: Quick query mode (non-supervisor flows)
- **Fallback**: `app/ai/graph/prompts/router_agent.py` → `ROUTER_SYSTEM_PROMPT`

### Planning Agent

**`voya-planning-trip-extraction`**
- **Purpose**: Extracts structured trip information from natural language
- **Extracts**: origin, destination, dates, travelers, interests
- **Output**: JSON (Pydantic model `TripInfoExtraction`)
- **Fallback**: `app/ai/graph/prompts/planning_agent.py` → `TRIP_INFO_EXTRACTION_PROMPT`

**`voya-planning-trip-acknowledgment`**
- **Purpose**: Generates friendly confirmation message after extracting trip details
- **Output**: 1-2 sentence acknowledgment
- **Example**: "Got it! Planning a trip from Paris (CDG) to London (LHR)"
- **Fallback**: `app/ai/graph/prompts/planning_agent.py` → `TRIP_ACKNOWLEDGMENT_PROMPT`

**`voya-planning-itinerary-generation`**
- **Purpose**: Creates detailed day-by-day travel itinerary
- **Output**: JSON with `itinerary` (markdown) and `highlights` (list)
- **Includes**: Daily activities, timing, local tips, personalized suggestions
- **Fallback**: `app/ai/graph/prompts/planning_agent.py` → `ITINERARY_GENERATION_PROMPT`

**`voya-planning-budget-estimation`**
- **Purpose**: Calculates realistic trip costs with breakdown
- **Output**: JSON with cost breakdown (flights, accommodation, food, activities, transport, misc)
- **Based on**: Market rates, destination, duration, travelers
- **Fallback**: `app/ai/graph/prompts/planning_agent.py` → `BUDGET_ESTIMATION_PROMPT`

### Flight Agent

**`voya-flight-agent`**
- **Purpose**: Handles flight search and booking using natural language
- **Tools**: `resolve_airport`, `parse_dates`, `search_flights`
- **Features**: Airport resolution, date parsing, curated results (cheapest, fastest, best value)
- **Used in**: Direct flight bookings or supervisor's BOOKING_HANDOFF stage
- **Fallback**: `app/ai/graph/prompts/flight_agent.py` → `FLIGHT_SYSTEM_PROMPT`

### Hotel Agent

**`voya-hotel-agent`**
- **Purpose**: Handles hotel search and booking using natural language
- **Tools**: `resolve_city`, `parse_dates`, `search_hotels`, `select_hotel`
- **Features**: City disambiguation, date parsing, curated results (best value, cheapest, highest rated)
- **Used in**: Direct hotel bookings or supervisor's BOOKING_HANDOFF stage
- **Fallback**: `app/ai/graph/prompts/hotel_agent.py` → `HOTEL_SYSTEM_PROMPT`

---

## Variable Syntax

**In Langfuse prompts**: Always use `{{variable}}` (double braces)
**In fallback code**: Uses `{variable}` (single braces - Python format strings)

### Agent Prompts (Router, Flight, Hotel)

**Variables**:
- `{{current_date}}` - Today's date (e.g., "2026-01-12")
- `{{current_year}}` - Current year (e.g., 2026)
- `{{next_year}}` - Next year (e.g., 2027) - **Not used by Router**

**Processing**: Langfuse `.compile()` replaces `{{variable}}` with actual values

### Planning Prompts (Itinerary, Budget)

**Variables**:
- `{{origin}}`, `{{destination}}` - City names with airport codes
- `{{departure_date}}`, `{{return_date}}` - YYYY-MM-DD dates
- `{{adults}}`, `{{children}}` - Number of travelers
- `{{interests}}` - Comma-separated interests

**Processing**: Backend converts `{{variable}}` → `{variable}` then uses Python `.format()`

---

## How to Update Prompts

1. Access Langfuse → Prompts section
2. Edit prompt (create new version, keep same label: `production`)
3. Wait 5 minutes OR restart: `docker compose restart backend`
4. Verify in logs: `✅ Fetched prompt from Langfuse: voya-xxx`

---

## Fallback Mechanism

**Order**: Cache (5 min) → Langfuse → Hardcoded fallback

**Fallback locations**: `app/ai/graph/prompts/{agent}_agent.py`

**Log Messages**:
- Success: `✅ Fetched prompt from Langfuse: voya-xxx`
- Fallback: `⚠️ Using fallback prompt for: voya-xxx`

---

## Environment Variables

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PROMPT_LABEL=production
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Prompt not updating | Wait 5 min or restart backend |
| Fallback being used | Check `.env` credentials, prompt name (case-sensitive), network |
| Variables not replaced | Use `{{variable}}` in Langfuse (double braces) |

---

**Maintainer**: Voya AI Team | **Related Docs**: `CLAUDE.md`, `backend_python/CLAUDE.md`, `SUPERVISOR_SYSTEM_ARCHITECTURE.md`
