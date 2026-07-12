# Capabilities API for n8n Integration

This document describes the Capabilities API implementation that enables the n8n Itinerary Agent to use the backend's proven airport resolution, date parsing, and flight search capabilities.

---

## Table of Contents

- [Overview](#overview)
- [Why This Was Built](#why-this-was-built)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Response Status Types](#response-status-types)
- [Implementation Details](#implementation-details)
- [n8n Workflow Integration](#n8n-workflow-integration)
- [Testing](#testing)
- [File Changes Summary](#file-changes-summary)
- [Deployment Checklist](#deployment-checklist)

---

## Overview

The Capabilities API exposes backend functionality as HTTP endpoints that n8n can call during the `CREATE_ITINERARY` flow. Instead of n8n using Google Places API (incomplete data) and Gemini AI (non-deterministic) for airport resolution, it now calls the backend's proven services.

**Key Benefits:**
- **29,000+ airports** database vs limited Google Places data
- **Deterministic resolution** vs Gemini AI guessing
- **Consistent UX** across all travel intents (BOOK_FLIGHT, BOOK_HOTEL, CREATE_ITINERARY)
- **Early disambiguation** - airport options shown immediately, not at the end
- **Reduced API costs** - eliminates Google Places API calls for airport data

**Base URL:** `/api/itinerary/capabilities/`

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /resolve-location` | Resolve city/airport to IATA code(s) |
| `POST /parse-dates` | Convert natural language dates to ISO format |
| `POST /search-flights` | Search flights with curated results |
| `POST /search-hotels` | Hotel search (endpoint only, not integrated yet) |

---

## Why This Was Built

### Problem Statement

The n8n Itinerary Agent was handling airport resolution independently using:
1. **Google Places API** - Limited travel-specific data, doesn't know about airports
2. **Gemini AI** - Non-deterministic classification for airport ownership

This caused several issues:
- Cities without airports (Utrecht, Cambridge) were incorrectly handled
- Multi-airport cities (London, Paris) weren't properly disambiguated
- Users couldn't refine flight parameters after seeing results
- Different resolution logic between `BOOK_FLIGHT` (backend) and `CREATE_ITINERARY` (n8n)

### Solution

Expose the backend's existing LangGraph tools as HTTP endpoints:
- `AirportService.resolve()` → `/resolve-location`
- `parse_dates` tool → `/parse-dates`
- `search_flights` tool → `/search-flights`

Now n8n calls these endpoints and gets the same quality resolution as the direct chat flow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (AWS)                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              /api/itinerary/capabilities/                 │ │
│  │                                                           │ │
│  │   POST /resolve-location  (airport disambiguation)        │ │
│  │   POST /parse-dates       (natural language → ISO)        │ │
│  │   POST /search-flights    (curated flight search)         │ │
│  │   POST /search-hotels     (placeholder for future)        │ │
│  │                                                           │ │
│  │   Authentication: X-API-Key header                        │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                         │
│                      │ Reuses existing services                │
│                      ▼                                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              LangGraph Tools (unchanged)                  │ │
│  │   • AirportService (app/domains/airport/service.py)       │ │
│  │   • parse_dates (app/ai/graph/tools/dates.py)             │ │
│  │   • search_flights (app/ai/graph/tools/flights.py)        │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS + API Key
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                     n8n Cloud                                   │
│               (CREATE_ITINERARY workflow)                       │
│                                                                 │
│   Calls Capabilities API at any stage for:                      │
│   • Resolving airports (immediately when destination detected)  │
│   • Parsing dates                                               │
│   • Searching flights (when user confirms itinerary)            │
└─────────────────────────────────────────────────────────────────┘
```

### Folder Structure

```
backend_python/app/api/itinerary/
├── __init__.py          # Router setup
├── schemas.py           # 19 Pydantic models (request/response contracts)
└── capabilities.py      # 4 endpoint implementations
```

---

## API Reference

### 1. Resolve Location

Resolves a city name, airport code, or airport name to IATA code(s).

**Endpoint:** `POST /api/itinerary/capabilities/resolve-location`

**Request:**
```json
{
  "query": "London",
  "context": {
    "country_hint": "United Kingdom",
    "type": "airport"
  }
}
```

**Response (Multi-airport city):**
```json
{
  "status": "needs_user_choice",
  "all_options": [
    {"iata": "LHR", "name": "London Heathrow", "city": "London", "country": "GB"},
    {"iata": "LGW", "name": "London Gatwick", "city": "London", "country": "GB"},
    {"iata": "STN", "name": "London Stansted", "city": "London", "country": "GB"}
  ],
  "suggested_prompt": "London has multiple airports. Which do you prefer?..."
}
```

**Response (City without airport):**
```json
{
  "status": "no_own_airport",
  "original_city": "Utrecht",
  "nearest_airports": [
    {"iata": "AMS", "name": "Amsterdam Airport Schiphol", "distance_km": 35},
    {"iata": "RTM", "name": "Rotterdam Airport", "distance_km": 45}
  ],
  "suggested_prompt": "Utrecht doesn't have its own airport. Nearest options:..."
}
```

**Response (Single airport resolved):**
```json
{
  "status": "resolved",
  "location": {
    "iata": "AMS",
    "name": "Amsterdam Airport Schiphol",
    "city": "Amsterdam",
    "country": "NL"
  }
}
```

### 2. Parse Dates

Converts natural language date expressions to ISO format.

**Endpoint:** `POST /api/itinerary/capabilities/parse-dates`

**Request:**
```json
{
  "expression": "next Christmas for 2 weeks"
}
```

**Response:**
```json
{
  "status": "success",
  "departure_date": "2025-12-25",
  "return_date": "2026-01-08",
  "trip_days": 14,
  "journey_type": "Return",
  "parsed_from": "next Christmas for 2 weeks"
}
```

### 3. Search Flights

Searches for flights and returns curated results.

**Endpoint:** `POST /api/itinerary/capabilities/search-flights`

**Request:**
```json
{
  "origin_iata": "AMS",
  "destination_iata": "CDG",
  "departure_date": "2025-12-20",
  "return_date": "2025-12-27",
  "adults": 2,
  "children": 0,
  "infants": 0,
  "session_id": "itinerary_abc123"
}
```

**Response:**
```json
{
  "status": "success",
  "search_id": "FL_abc12345",
  "summary": {
    "total_found": 15,
    "direct_flights": 8,
    "price_range": {"min": 75, "max": 320, "currency": "EUR"}
  },
  "curated": {
    "cheapest": {
      "label": "Lowest Price",
      "flight": {
        "id": "FL001",
        "departure_time": "07:00",
        "arrival_time": "08:25",
        "duration": "1h 25m",
        "price": 75,
        "currency": "EUR",
        "airline": "easyJet",
        "stops": 0
      }
    },
    "fastest": {
      "label": "Fastest",
      "flight": { "..." }
    },
    "best_value": {
      "label": "Best Value",
      "flight": { "..." }
    }
  }
}
```

### 4. Search Hotels (Placeholder)

**Endpoint:** `POST /api/itinerary/capabilities/search-hotels`

> **Note:** This endpoint is created for future integration but currently returns a "not implemented" response.

---

## Authentication

All Capabilities API endpoints require authentication via the `X-API-Key` header.

**Header:** `X-API-Key: your-api-key`

**Configuration:**
- Backend: Set `N8N_CAPABILITIES_API_KEY` environment variable
- n8n: Configure HTTP Request nodes with the same key in `X-API-Key` header

**Development Mode:**
In development (`ENVIRONMENT=development`), if `N8N_CAPABILITIES_API_KEY` is not configured, requests are allowed without authentication.

**Implementation:**
```python
async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    # In development without key configured: allow access
    if settings.ENVIRONMENT == "development" and not settings.N8N_CAPABILITIES_API_KEY:
        return "dev-mode"

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    if x_api_key != settings.N8N_CAPABILITIES_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

---

## Response Status Types

### Location Resolution Status

| Status | Description | Response Fields |
|--------|-------------|-----------------|
| `resolved` | Single airport found | `location` |
| `needs_user_choice` | Multi-airport city (London, Paris) | `all_options`, `suggested_prompt` |
| `no_own_airport` | City has no airport (Utrecht) | `original_city`, `nearest_airports`, `suggested_prompt` |
| `needs_disambiguation` | Ambiguous query (Birmingham UK vs USA) | `disambiguation_type`, `options` |
| `not_found` | No airports found | `error` |

### General Status

| Status | Description |
|--------|-------------|
| `success` | Operation completed successfully |
| `error` | Operation failed |
| `no_results` | No results found (for search operations) |

---

## Implementation Details

### Lazy Imports

Services and tools are imported inside functions to avoid:
- Circular imports
- Premature service initialization
- Easier isolated testing

```python
@router.post("/resolve-location")
async def resolve_location(request: ResolveLocationRequest) -> ResolveLocationResponse:
    # Import inside function
    from app.domains.airport import get_airport_service
    service = get_airport_service()
    # ...
```

### No Own Airport Detection

To differentiate between multi-airport cities and cities without airports:

```python
# Compare query city with airport cities
query_lower = query.lower().strip()
has_own_airport = any(
    a.city.lower().strip() == query_lower for a in airports_list
)

if not has_own_airport:
    # These are nearby airports, not airports IN the city
    return ResolveLocationResponse(status=LocationStatus.NO_OWN_AIRPORT, ...)
else:
    # Multi-airport city
    return ResolveLocationResponse(status=LocationStatus.NEEDS_USER_CHOICE, ...)
```

### Bug Fixes Applied

**Bug 1: Country Filter**
- **Issue:** Airport filter compared `"FR"` (ISO code) with `"France"` (name) = no match
- **Fix:** Compare with both formats

```python
# Before
airports = [a for a in all_airports if a.country.lower() == geo_result.country.lower()]

# After
airports = [
    a for a in all_airports
    if (a.country.lower() == geo_result.country.lower()
        or a.country.lower() == geo_result.country_code.lower())
]
```

**Bug 2: Military Airport Filter**
- **Issue:** Utrecht showed military bases (Deelen Air Base, Gilze Rijen)
- **Fix:** Apply military filter to nearby airports

```python
military_terms = ["raf ", "afb ", "air force", "air base", "military"]
nearby_airports = [
    airport for airport, _ in nearby
    if not any(term in airport.name.lower() for term in military_terms)
]
```

---

## n8n Workflow Integration

### Nodes Created

| Node | Purpose |
|------|---------|
| Resolve Origin (Capabilities API) | HTTP Request to `/resolve-location` for origin |
| Resolve Destination (Capabilities API) | HTTP Request to `/resolve-location` for destination |
| Process Capabilities Response | JavaScript node processing API responses |

### Nodes Modified

| Node | Change |
|------|--------|
| Parse Extraction Result | Clear stale IATA when city changes |
| Process Airport Selection | Preserve `status` in `stillPending` |
| Validate Stage Progression | Fast-path to `availability_check` |
| Inject Airport Selection Message | Detect `no_own_airport` status |

### Nodes Removed

| Node | Reason |
|------|--------|
| Search Airports Near X (Google Places) | Replaced by Capabilities API |
| Gemini Airport Ownership | Replaced by Capabilities API |

### Critical Fixes

**Fix 1: Clear Stale IATA When City Changes**

When user changes destination (Geneva → London), clear the old IATA (GVA) so the system asks which London airport to use.

```javascript
// Parse Extraction Result node
const currentDestCity = String(currentData.destination || '').toLowerCase().trim();
const newDestCity = String(updatedData.destination || '').toLowerCase().trim();

if (currentDestCity && newDestCity && currentDestCity !== newDestCity && !extracted.destination_iata) {
  delete updatedData.destination_iata;
  delete updatedData.destination_tourist;
}
```

**Fix 2: Preserve Status in stillPending**

When there's a pending selection for origin after destination, preserve the status to show the correct message.

```javascript
// Process Airport Selection node
selectionResult.stillPending = {
  type: 'origin',
  status: alsoOrigin.status,  // Preserves 'no_own_airport' vs 'needs_user_choice'
  options: alsoOrigin.options,
  original_city: alsoOrigin.original_city
};
```

**Fix 3: Validate IATA Against API Response**

Don't trust existing IATA codes without verifying they're valid for the current city.

```javascript
// Process Capabilities Response node
function isIataValidForResponse(iata, apiResponse) {
  if (!iata || !apiResponse) return false;
  if (apiResponse.status === 'resolved' && apiResponse.location) {
    return apiResponse.location.iata === iata;
  }
  if (apiResponse.all_options?.length > 0) {
    return apiResponse.all_options.some(opt => opt.iata === iata);
  }
  if (apiResponse.nearest_airports?.length > 0) {
    return apiResponse.nearest_airports.some(apt => apt.iata === iata);
  }
  return false;
}
```

**Fix 4: Fast-Path to availability_check**

Skip directly to `availability_check` when user explicitly requests flight check and has all required data.

```javascript
// Validate Stage Progression node
if (wantsAvailability && current_stage !== 'availability_check') {
  const hasAvailRequired = availReqs.every(k => cd[k]);
  const hasIatas = cd.origin_iata?.length === 3 && cd.destination_iata?.length === 3;

  if (hasAvailRequired && hasIatas) {
    nextStage = 'availability_check';
    shouldAdvance = true;
  }
}
```

---

## Testing

### Unit Tests

```bash
cd backend_python

# Capabilities API tests (12 tests)
python -m pytest tests/unit_tests/test_api/test_itinerary_capabilities.py -v

# Airport service tests (25 tests)
python -m pytest tests/unit_tests/test_domains/test_airport_service.py -v

# Availability check refactoring tests (14 tests)
python -m pytest tests/unit_tests/test_domains/test_itinerary_availability_check.py -v
```

### Manual Testing with cURL

```bash
# Resolve Location (development mode - no API key)
curl -X POST http://localhost:8000/api/itinerary/capabilities/resolve-location \
  -H "Content-Type: application/json" \
  -d '{"query": "London"}'

# Parse Dates
curl -X POST http://localhost:8000/api/itinerary/capabilities/parse-dates \
  -H "Content-Type: application/json" \
  -d '{"expression": "next Christmas for 2 weeks"}'

# Search Flights (with API key)
curl -X POST http://localhost:8000/api/itinerary/capabilities/search-flights \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "origin_iata": "LHR",
    "destination_iata": "CDG",
    "departure_date": "2025-12-20",
    "return_date": "2025-12-27",
    "adults": 2
  }'
```

### Swagger UI

Endpoints available at: `http://localhost:8000/api/docs` under tag "Itinerary Capabilities"

---

## File Changes Summary

### New Files

| File | Description |
|------|-------------|
| `app/api/itinerary/__init__.py` | Router setup with `/capabilities` prefix |
| `app/api/itinerary/schemas.py` | 19 Pydantic models for request/response |
| `app/api/itinerary/capabilities.py` | 4 endpoint implementations (~600 lines) |
| `tests/unit_tests/test_api/test_itinerary_capabilities.py` | 12 unit tests |

### Modified Files

| File | Change |
|------|--------|
| `app/core/config.py` | Added `N8N_CAPABILITIES_API_KEY` setting |
| `app/api/__init__.py` | Router registration for itinerary endpoints |
| `app/domains/chat/service.py` | Refactored IATA handling, added `_is_valid_iata_code()` |
| `app/domains/airport/service.py` | Fixed country filter and military airport filter |
| `tests/unit_tests/test_domains/test_itinerary_availability_check.py` | 14 tests for IATA refactoring |

### Config Addition

```python
# app/core/config.py
N8N_CAPABILITIES_API_KEY: str | None = Field(
    default=None,
    description="API key for n8n to call Capabilities API endpoints. "
    "Used by /api/itinerary/capabilities/* endpoints for authentication.",
)
```

### Router Registration

```python
# app/api/__init__.py
from app.api.itinerary import itinerary_router

api_router.include_router(itinerary_router, prefix="/itinerary", tags=["Itinerary"])
```

### IATA Validation

```python
# app/domains/chat/service.py
def _is_valid_iata_code(code: str | None) -> bool:
    """Validate IATA airport code format (3 uppercase letters)."""
    if not code:
        return False
    return len(code) == 3 and code.isalpha() and code.isupper()
```

---

## Deployment Checklist

### Backend Deployment

1. **Create PR** with these files:
   - `app/api/itinerary/__init__.py` (new)
   - `app/api/itinerary/schemas.py` (new)
   - `app/api/itinerary/capabilities.py` (new)
   - `app/api/__init__.py` (modified)
   - `app/core/config.py` (modified)
   - `app/domains/chat/service.py` (modified)
   - `app/domains/airport/service.py` (modified)
   - `tests/unit_tests/test_api/test_itinerary_capabilities.py` (new)
   - `tests/unit_tests/test_domains/test_itinerary_availability_check.py` (modified)

2. **Do NOT include** (local/dev only):
   - `compose.dev.yaml`
   - `compose.test.yaml`
   - `PLAN_*.md` files
   - `Test_*.txt` files

3. **Deploy backend to staging**

4. **Configure environment variable:**
   ```
   N8N_CAPABILITIES_API_KEY=<secure-random-key>
   ```

### n8n Deployment

5. **Export updated workflow** from local n8n

6. **Import workflow to n8n Cloud** (staging)

7. **Configure n8n credential** with same API key

8. **Test E2E in staging:**
   - Utrecht (no own airport)
   - London (multi-airport)
   - Paris (multi-airport)
   - Destination change (Geneva → London)
   - "check flights" command

9. **Deploy to production**

---

## Impact Assessment

### Does this affect BOOK_FLIGHT?

**No.** Changes are specific to:
- `AirportService` (used by Capabilities API)
- `capabilities.py` (only for n8n/CREATE_ITINERARY)

BOOK_FLIGHT uses:
- `FlightFieldCollector` → Not modified
- `enhanced_flight_handler.py` → Not modified

### Does this affect BOOK_HOTEL?

**No.** Hotel flow uses different services.

### Does this affect LangGraph Agents?

**Minimal.** `AirportService` is used by LangGraph, but:
- Country filter fix is backward compatible
- Military filter is an improvement
- No LangGraph tests failed

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design overview
- [LANGGRAPH_ARCHITECTURE.md](LANGGRAPH_ARCHITECTURE.md) - LangGraph tools documentation
- [AIRPORT_RESOLUTION_ARCHITECTURE.md](AIRPORT_RESOLUTION_ARCHITECTURE.md) - Airport resolution details
- [ITINERARY_AVAILABILITY_CHECK_IMPLEMENTATION.md](ITINERARY_AVAILABILITY_CHECK_IMPLEMENTATION.md) - Availability check flow

---

**Implementation Completed:** December 2025
**Phases:** 1 (Backend API), 1.5 (Refactoring), 1.6 (Bug Fixes), 2 (n8n Integration), 2.5 (Critical Fixes)
**Pending:** Phase 3 (Production Deployment)
