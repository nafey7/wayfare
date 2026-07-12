# Flight Features Documentation

This document provides technical details about the flight search and booking features implemented in the Voya platform.

## Post-Payment Booking Details Sync

After a successful flight payment, both LCC and GDS flows now redirect to the user-facing booking details page at `/flights/bookings/:bookingRef` instead of the legacy confirmation page.

### Current behavior

- `frontend-v2/src/features/flights/pages/PaymentPage.tsx` redirects successful LCC and GDS payments to the booking details route.
- `frontend-v2/src/features/flights/pages/FlightBookingDetailsPage.tsx` automatically calls `POST /api/flights/trip-details` on load.
- `backend_python/app/domains/flight/service.py` treats trip-details fetches as the canonical sync point for booking metadata.

### Synced booking fields

Whenever trip details are fetched successfully for a known VOYA booking reference, the booking event document is updated with the latest non-empty values for:

- `pnr`
- `ticket_status`
- `e_ticket_numbers`

For GDS ticketing, the backend performs a fresh trip-details fetch after `issue_tickets()` succeeds so the stored `ticket_status` and passenger e-ticket numbers reflect the post-ticketing supplier state rather than the pre-ticket snapshot.

### Ticket status history

The `ticket_status` scalar is kept for backward compatibility (latest value). In addition, a `ticket_status_history` array stores a chronological snapshot trail. Each time trip details returns a non-empty `ticket_status`, a new snapshot is appended with the current UTC time:

- **`ticket_status`**: Latest scalar value (backward-compatible)
- **`ticket_status_history`**: Append-only array of `{status, time}` snapshots

```json
{
  "ticket_status": "Cancelled",
  "ticket_status_history": [
    { "status": "TktInProcess", "time": "2026-03-18T10:12:01Z" },
    { "status": "Ticketed", "time": "2026-03-18T10:13:42Z" },
    { "status": "Cancelled", "time": "2026-03-20T08:41:11Z" }
  ]
}
```

This preserves the transition timeline for auditing and answers questions like: was this booking ticketed, later cancelled, and when did each observed status occur? The history is append-only; repeated fetches with the same status produce additional snapshots with different timestamps. The API response includes `ticket_status_history` in booking event responses.

## Passenger Count Validation

### Implementation Details

**Location**: `backend_python/app/domains/flight/schemas.py`
- Core validation: `FlightSearchRequest.validate_passenger_limits()` method (lines 298-334)
- Schema-level constraints: Field-level `ge=0` validation for all passenger counts
- Integration: Automatic validation on all flight search API endpoints

### Business Rules Enforced

1. **Maximum Passenger Limit**: Total passengers (adults + children + infants) ≤ 9 per booking
2. **Infant Travel Rules**:
   - Infants cannot exceed combined count of adults and children
   - At least one adult required when infants are present
   - Each infant must be accompanied by an adult or child
3. **Non-negative Counts**: All passenger counts must be ≥ 0
4. **Minimum Booking**: At least 1 passenger required for any flight search

### Valid Passenger Combinations (Examples)

```python
# Maximum passengers (total = 9)
{"adults": 5, "children": 3, "infants": 1}  # Valid: 5+3+1=9, infants≤adults+children
{"adults": 9, "children": 0, "infants": 0}  # Valid: All adults
{"adults": 4, "children": 4, "infants": 1}  # Valid: Mixed with infants

# Minimum passengers
{"adults": 1, "children": 0, "infants": 0}  # Valid: Single traveler

# Invalid combinations
{"adults": 6, "children": 3, "infants": 2}  # Invalid: Total=11 > 9
{"adults": 2, "children": 1, "infants": 4}  # Invalid: Infants(4) > Adults+Children(3)
{"adults": 0, "children": 5, "infants": 1}  # Invalid: Infants without adults
```

### Error Messages

Validation errors include detailed passenger count breakdown:
```
"Total passenger count cannot exceed 9. Current: 11 (Adults: 6, Children: 3, Infants: 2)"
"Infant count (4) cannot exceed combined Adults + Children count (3). Each infant must be accompanied by an adult or child."
"Infants (1) cannot travel without an accompanying adult. At least 1 adult is required."
```

### Testing

- 15 comprehensive unit tests in `tests/unit_tests/test_schemas/test_flight_search_request.py`
- Coverage includes: all valid combinations, boundary cases, error message validation, integration with other schema fields

### API Integration

- Validation automatically applied to `/flights/search` endpoint
- Returns HTTP 422 Unprocessable Entity for invalid passenger combinations
- Client-side validation should mirror these rules for better UX

## Multi-city (Circle) flights

### Request shape (`POST /api/flights/search`)

- Set `journey_type` to `Circle` (FlightLogic `journeyType: "Circle"`).
- Send **at least two** `origin_destination_info` legs, each with `departure_date`, `origin_airport`, `destination_airport` (IATA). Do **not** set `return_date` on legs (that field is for legacy or other flows; Circle uses one row per leg in the adapter).
- Legs must **connect**: for each pair of consecutive legs, the first leg’s destination IATA code must equal the second leg’s origin code.
- Leg dates must be **non-decreasing** (each leg’s `departure_date` on or after the previous leg’s).

`OneWay` requires exactly one leg; `Return` requires exactly two legs that form A→B and B→A.

### Backward compatibility (search request)

- **`RoundTrip`**: Accepted on `POST /api/flights/search` and normalized to `Return` before validation.
- **Deprecated Return shape**: A single `origin_destination_info` row with `return_date` on that row is **split server-side** into two O&D rows (outbound + inbound). A deprecation warning is logged; new clients should send **two** rows for Return. Monitor HTTP **422** rates if any client still sends invalid shapes after migration.

### Search response parsing

For Circle, FlightLogic typically returns **one** `OriginDestinationOptions` block with **multiple** `FlightSegment` entries in sequence (all sectors in one continuous option). The adapter builds **one** domain `FlightLeg` whose `flight_segments` list contains every segment. This differs from `Return`, where outbound and inbound are often split across two top-level option groups.

### Booking and revalidation

- Circle pricing uses a **single** `fare_source_code` for the whole itinerary. Do **not** send `return_fare_source_code` / inbound fare fields used for Indian domestic round-trip splits unless the supplier flow requires them for that product.
- Booking sessions created via `POST /api/flights/select` store `journey_type: "Circle"` and an `airport_codes_chain` when the validated itinerary is Circle.

## Flight Search Revalidation

### Overview

After receiving flight search results from FlightLogic, the backend **may** revalidate a configurable number of flights **in parallel** and remove fares that fail (`is_fare_available=False` or API errors). Whether that step runs at all is controlled by an environment flag (see below). This improves UX in production by not showing fares that are no longer bookable.

### Implementation Details

**Schema** (`backend_python/app/domains/flight/schemas.py`):
- `FlightSearchRequest.revalidate_flights_count: int | None` (0–10, default `None`)
- When omitted or `None`: no post-search revalidation (same as count 0 when the flag is on)
- When 0: no post-search revalidation
- When 1–10 and the flag is **on**: revalidate up to that many flights from filtered results (parallel `asyncio.gather`)
- When 1–10 and the flag is **off**: **no** FlightLogic revalidate calls and **no** removal of itineraries based on revalidation (results pass through unchanged for this step)

**Helper** (`backend_python/app/domains/flight/revalidation_filters.py`):
- `get_flight_ids_to_remove_after_revalidation()` – async helper used only when the flag is enabled
- Inputs: `session_id`, flights, passenger counts, `revalidate_flights_count`, revalidate callable
- Output: `set[str]` of `fare_source_code` to remove
- Implementation: all candidate calls dispatched in parallel via `asyncio.gather`
- Per-call timeout (`REVALIDATE_CALL_TIMEOUT_SECONDS = 5.0s`) and exception handling apply per candidate
- Note: The chat/per-category helper (`filter_category_flights_after_revalidation` → `_revalidate_fare_source_codes`) always runs in parallel and is **not** affected by this flag

**Service integration** (`backend_python/app/domains/flight/service.py`):
- After `filter_flight_results`, if `revalidate_flights_count` > 0 **and** `settings.FLIGHT_SEARCH_CONCURRENT_REVALIDATION` is true, calls the helper and filters out invalid fares (including multicity legs that use the same finalizer)
- If the flag is false but `revalidate_flights_count` > 0, logs `Flight search revalidation skipped` and does not call FlightLogic revalidate
- When revalidation runs, logs: `requested_count`, `candidates_count`, `removed_count`, `duration_ms`

**Configuration** (`FLIGHT_SEARCH_CONCURRENT_REVALIDATION`):
- Default: `false` — **disables** post-search revalidation (no extra FlightLogic load; typical for local dev)
- Production: `true` — enables parallel post-search revalidation; set via Terraform `additional_environment_vars`
- Staging/Test: explicit `false` means post-search revalidation is off unless you set `true` for testing
- Rollback in prod: set env var to `"false"` and redeploy — search results will not be revalidated on the search path

### Selection Strategy

**Search endpoint** (FlightSearchPage): First N flights in `fare_itineraries` (outbound list) in response order. Uses `revalidate_flights_count` from request (e.g. 5).

**Chat recommendations** (per-category): Select top 8 per category, revalidate top 4, filter invalid, send top 3. Overlapping flights across categories revalidated once.

### Per-Category Revalidation (Chat)

For chat flight recommendations, revalidation runs **per category**:

| Stage | Count | Description |
|-------|-------|-------------|
| Select | 8 | Top 8 per category by criterion (price, duration, best-value score) |
| Revalidate | 4 | Top 4 of those 8 revalidated in parallel |
| Filter | — | Remove invalid fares from the 8 |
| Send | 3 | Top 3 valid flights per category sent to frontend |

**Helper** (`filter_category_flights_after_revalidation`):
- Inputs: `session_id`, categories dict, passenger counts, revalidate callable, `get_fare_source_code` adapter
- Overlap: Deduplicate by `fare_source_code` and revalidate each unique flight once
- Used by: `graph/tools/flights.py` (LangGraph), `enhanced_flight_handler.py`

### API Contract

- Request: `revalidate_flights_count?: number` (optional, 0–10)
- Frontend sends `revalidate_flights_count: 5` per product requirement
- Chat flows: Per-category revalidation (no `revalidate_flights_count` on search request)

### Chat and Graph Tool Integration

- `enhanced_flight_handler.py` and `graph/tools/flights.py` use per-category revalidation
- Search request: no `revalidate_flights_count` (revalidation done in AI layer)
- Top-3 category recommendations (cheapest, fastest, best value) are validity-aware

### Testing

- Schema: `tests/unit_tests/test_schemas/test_flight_search_request.py`
- Global helper: `tests/unit_tests/test_domains/test_flight/test_revalidation_filters.py` (`get_flight_ids_to_remove_after_revalidation`, `filter_category_flights_after_revalidation`)

## Smart Date Parsing (Issue #6)

### Implementation Details

**Location**: `backend_python/app/ai/flight_field_collector.py`
- Core logic: `_parse_date()` method (lines 1420-1512)
- Integrated in: `parse_message_for_fields()` and `parse_message_for_fields_async()`
- Relative dates ("tomorrow", "next week") unaffected

### Edge Cases Handled
- Leap years (Feb 29), year boundaries (Dec/Jan), explicit years preserved
- Context-aware for round trip return dates

### Testing
- 20 comprehensive unit tests in `tests/unit_tests/test_ai/test_smart_date_parsing.py`

## Relative Return Date Calculation (Issue #11)

### Implementation Details

**Location**: `backend_python/app/ai/flight_field_collector.py`
- Added `_convert_word_to_number()` function (lines 16-30) - Maps word numbers to digits
- Enhanced `_parse_relative_time()` patterns (lines 33-106) - Supports both digits and words
- New patterns: "returning X weeks", "back X weeks", "in X weeks"
- Integration: `enhanced_flight_handler.py` lines 177-235

### Word Number Support
```python
# Supported words: one, two, three, four, five, six, seven, eight, nine, ten, a, an
"two weeks later" → 14 days ✅
"three days later" → 3 days ✅
"a week later" → 7 days ✅
```

### Edge Cases Handled
- Return date validation (always after departure)
- Month and year boundaries (Oct → Nov, Dec → Jan)
- Mixed numeric and word expressions ("2 weeks" = "two weeks")
- Alternative phrasings without "later" suffix

### Testing
- 37 comprehensive unit tests in `tests/unit_tests/test_ai/test_relative_return_dates.py`
  - 29 original tests (core functionality)
  - 8 new tests (word number support)

### Related Documentation
See `ISSUE_11_IMPLEMENTATION_REPORT.md` for detailed analysis

## City-Wise Flight Search (frontend-v2)

When users select **"City (Any)"** in the flight search autocomplete (for cities with multiple airports, e.g. London, Paris, New York), the search returns flights from/to **all airports in that city**, not just a single airport. This matches the behavior of `backend_python/dev_ui/flight-booker`.

### How It Works

1. **AirportAutocomplete**: Cities with multiple airports show a "City (Any)" option. It uses the first airport's IATA as a representative code for the API.
2. **Search request**: `city_wise_search_origin` and `city_wise_search_destination` are set to `true` when the user selects a City (Any) option.
3. **Backend**: The FlightLogic adapter expands the search to all airports in the origin/destination city when these flags are true.

### Key Files

- `frontend-v2/src/features/flights/components/AirportAutocomplete.tsx` – City (Any) options with representative IATA
- `frontend-v2/src/features/flights/pages/FlightSearchPage.tsx` – `buildSearchRequest` sets city-wise flags from `fromAirport`/`toAirport.isCityOption`
- `frontend-v2/src/features/flights/utils/resolveAirport.ts` – `resolveToIata()` derives IATA and city-wise from selected airport option

### URL Serialization

Search params (including `fromAirport`/`toAirport` with `isCityOption`) are serialized to the `?q=` URL param, so back/forward navigation preserves city-wise search behavior.

## GDS Ticket Issuance (Trip Details Gate)

For GDS (Private/Public fare) bookings, the ticket order API is always preceded by a trip details call. The `ticket_status` from trip details gates the ticket order: if the booking is already `Ticketed` or `Cancelled`, the ticket order API is not called (avoids errors and saves API quota). See `docs/FLIGHT_BOOKING_FLOW.md` (GDS Ticket Issuance Flow) and `PLAN_GDS_TICKET_STATUS_GATE` for full details.

## Differentiated Flight Search Results (Issue #8)

### Implementation Details

**Location**: `backend_python/app/ai/flight_summary_generator.py`
- Core methods: `_get_top_recommendations()`, `_find_fastest_flight()`, `_find_best_value_flight()`
- See `docs/TROUBLESHOOTING.md` for edge cases and monitoring guidance

### Curation Algorithm

The system provides 3 distinct options:

1. **💵 LOWEST PRICE** - Absolute cheapest flight regardless of other factors
2. **⚡ FASTEST** - Shortest total travel time (including connections and layovers)
3. **⭐ BEST VALUE** - Flight with the lowest penalty score (price + duration balance and time-of-day penalties). See [Best Value (Best Flights) Scoring](#best-value-best-flights-scoring) for the exact formula.

### Smart Deduplication Examples

*Example 1: All Different Options*
```
Option 1 - LOWEST PRICE 💵
  $299, 8h, 1 stop, departs 6:00 AM

Option 2 - FASTEST ⚡
  $450, 5.5h, direct, departs 10:00 AM

Option 3 - BEST VALUE ⭐
  $350, 6h, 1 stop, departs 11:00 AM
```

*Example 2: Smart Deduplication*
```
When cheapest = fastest:

Option 1 - LOWEST PRICE + FASTEST 💵⚡
  $299, 5h, direct, departs 10:00 AM

Option 2 - BEST VALUE ⭐
  $350, 6h, 1 stop, departs 11:00 AM

(Only 2 options shown - no unnecessary duplication)
```

## Best Value (Best Flights) Scoring

The **Best** flight in chat search results is the one with the **lowest penalty score**, combining normalized price, normalized duration, and time-of-day penalties. This replaces the previous formula (`price + duration_minutes * 0.5`).

### Formula

```
S = (Price_norm × 0.60) + (Duration_norm × 0.40) + Time_Penalty
```

- **Lower score = better.** The flight with the smallest S is chosen as Best Value.
- **Price_norm** and **Duration_norm** are in [0, 1]; **Time_Penalty** is a non-negative sum of flat modifiers.

### Normalization

Price and duration are normalized **per search result set** (over all flights in that response) so they are comparable:

```
Normalized_Value = (Current_Value - Min_Value) / (Max_Value - Min_Value)
```

- **Edge case:** If `Min_Value == Max_Value` (e.g. all flights have the same price), `Normalized_Value = 0` to avoid division by zero.

### Weights

| Factor    | Weight | Constant in code   |
|----------|--------|--------------------|
| Price    | 0.60   | `WEIGHT_PRICE`     |
| Duration | 0.40   | `WEIGHT_DURATION`  |

Weights sum to 1.0 so the base score (without time penalty) stays in [0, 1].

### Time penalties (red-eye / late-night)

Times are interpreted in **local time** (departure/arrival at the airport). A time is considered **red-eye or late-night** if the hour is in **23:00–07:00** (i.e. hour 23, 0, 1, 2, 3, 4, 5, or 6).

| Condition                         | Penalty (outbound leg) | Penalty (return leg, if present) |
|----------------------------------|------------------------|----------------------------------|
| Departure in 23:00–07:00         | +0.15                  | +0.10                            |
| Arrival in 23:00–07:00           | +0.15                  | +0.10                            |

- Outbound: +0.15 for red-eye departure, +0.15 for late-night arrival (up to +0.30 if both).
- Return leg: +0.10 for each (up to +0.20 if both). Return penalties apply only when return times are provided.

### Implementation details

| Location | Role |
|----------|------|
| `backend_python/app/ai/flight_scoring.py` | Core logic: `compute_penalty_score()`, `sort_flights_by_best_value()`, `hour_from_datetime()`, `hour_from_time_str()`. Constants: `WEIGHT_PRICE`, `WEIGHT_DURATION`, `TIME_PENALTY_*`. |
| `backend_python/app/ai/enhanced_flight_handler.py` | Uses `sort_flights_by_best_value()` to order flights and build Best Value category in `_build_category_arrays()`. |
| `backend_python/app/ai/graph/tools/flights.py` | LangGraph flight tool uses `sort_flights_by_best_value()` for chat-based search results. |

### Edge cases and invalid inputs

- **Invalid inputs** (e.g. negative price, infinite price/duration): `compute_penalty_score()` returns `float('inf')` so the flight sorts last.
- **Min == max** for price or duration: normalized component is 0 (no division by zero).

### Testing

- Unit tests: `backend_python/tests/unit_tests/test_ai/test_flight_scoring.py`
- Covers: weights, normalization (including min == max), outbound and return time penalties, `hour_from_time_str`, `sort_flights_by_best_value`, invalid inputs sorting last.

## Enhanced Date Range Parsing & Field Validation (2025-09-23)

### Problems Solved
1. Date ranges like "anytime between 11 and 15 Oct" weren't being recognized
2. Flight results weren't showing departure dates with calendar symbols
3. Field validation failing with date objects causing runtime errors
4. Various deployment and authentication token errors

### Implementation Details

#### Date Range Parsing Integration
- **Location**: `app/ai/flight_field_collector.py`
- Integrated `_parse_date_range()` as first step in both sync and async field extraction
- Enhanced regex patterns for origin/destination with combined "X to Y" pattern
- Added support for "Month X-Y" formats (Oct 12-14) alongside existing patterns
- Smart parsing priority: date ranges → relative time → standard date parsing

#### Enhanced Flight Results Display
- **Location**: `app/ai/flight_summary_generator.py`
- Added calendar symbols (📅) and departure dates to flight options
- Enhanced route information display with proper date formatting
- Improved user experience with clear departure date visibility

#### Robust Field Validation
- **Location**: `app/ai/flight_field_collector.py:_validate_future_date()`
- Enhanced to handle date objects, strings, and dictionaries seamlessly
- Proper validation for date range dictionaries with start/end date checks
- Comprehensive error handling for various input types and edge cases

#### Exception Handling Improvements
- **Location**: `app/api/auth.py`, `app/main.py`
- Added InvalidTokenError handlers to `complete_registration` and other auth endpoints
- Global exception handler for InvalidTokenError with user-friendly messages
- Fixed UnboundLocalError in flight handlers by proper variable initialization

#### Origin/Destination Extraction Enhancement
- **Location**: `app/ai/flight_field_collector.py`
- Improved combined regex pattern for "X to Y" format recognition
- Better handling of complex airport names and mixed city/code formats
- Enhanced extraction reliability with trailing context handling

### Testing Coverage
- **Location**: `tests/unit_tests/test_ai/`
- Comprehensive unit tests for field validation improvements
- Date range parsing tests covering various formats and edge cases
- Exception handling tests for auth endpoints and global handlers
- Origin/destination extraction pattern validation tests

## Multi-Airport City Preference Flow (Issue #12)

### Overview
When users search for flights involving cities with multiple airports, the system now asks for the user's airport preference **before** executing the search. This ensures search results match the user's actual travel needs and location convenience.

### User Experience

**Example Flow**:
```
User: "flights from London to New York on October 15"

System: "London has multiple airports with flights to New York: LHR (Heathrow),
         LGW (Gatwick), and STN (Stansted). Do you have a preference?
         Or shall I search for the best results across all airports?"

User: "LHR please"  OR  "all airports"

System: [Executes search with selected preference]
```

### Supported Cities
50+ major cities with multiple airports, including:
- **London**: LHR, LGW, STN, LCY, LTN
- **New York**: JFK, LGA, EWR
- **Paris**: CDG, ORY, BVA
- **Tokyo**: NRT, HND
- **Los Angeles**: LAX, BUR, LGB, ONT, SNA
- **Milan**: MXP, LIN, BGY
- And many more...

### Implementation Details

#### Files Modified
1. **`app/domains/airport/airport_resolver.py`**
   - Added `get_city_airports()` method - Returns all airports for a city with full details
   - Added `get_airports_by_city_name()` - Convenience method returning only IATA codes

2. **`app/ai/flight_field_collector.py`**
   - Added `get_city_airports()` wrapper method for airport resolution

3. **`app/ai/enhanced_flight_handler.py`**
   - `_detect_multi_airport_scenarios()` - Detects origin/destination multi-airport situations
   - `_ask_airport_preference()` - Generates user-friendly preference questions
   - `_format_airport_list()` - Formats airport lists (e.g., "LHR (Heathrow), LGW (Gatwick)")
   - `_parse_airport_selection()` - Parses user's airport preference response
   - `_handle_airport_preference_response()` - Handles preference and triggers search
   - Integration in `handle_booking_conversation()` (steps 7.5 and 7.6)

#### Detection Logic
1. After all required fields collected (origin, destination, dates, passengers)
2. Check if origin city has multiple airports
3. Check if destination city has multiple airports
4. If detected: Ask for preference before search
5. If single airport: Skip preference, proceed to search

#### User Response Patterns Supported
- **Specific airport**: "LHR", "use Heathrow", "JFK please"
- **All airports**: "all airports", "best results", "search all", "any", "no preference"
- **Unclear**: "maybe", "not sure", "which is better?" → Triggers clarification

#### Session State
- `waiting_for_airport_selection`: Tracks which preference is needed (origin/destination)
- `available_airports`: List of airports user can choose from
- `airport_preference_context`: Full detection result for handling "both" scenarios
- `airport_preference_mode`: "SPECIFIC" or "ALL_AIRPORTS"

### Edge Cases Handled

1. **Single Airport Cities** - Automatically skips preference question (e.g., Amsterdam, Dubai)
2. **Both Multi-Airport** - Asks for origin first, then destination
3. **Invalid Selection** - Asks for clarification with valid options
4. **Unclear Response** - Re-presents options and asks for clear choice

### Testing
**Test File**: `tests/unit_tests/test_ai/test_multi_airport_flow.py`

**Coverage**:
- Multi-airport detection (origin, destination, both, single)
- Airport list formatting
- User selection parsing (codes, names, "all", unclear)
- Full flow integration scenarios
- Airport resolver methods

### Future Enhancements
1. **Connectivity Analysis** - Only suggest airports with equivalent minimum stops
2. **Parallel Multi-Airport Search** - Search all airports when user selects "all"
3. **Smart Defaults** - Learn user preferences over time
4. **Price Preview** - Show estimated price ranges per airport

### Troubleshooting

**Issue**: System not detecting multiple airports
- **Check**: City name spelling, database has multiple airports for city
- **Logs**: Look for "Multi-airport origin detected" or "Multi-airport destination detected"

**Issue**: User preference not respected
- **Check**: Logs show "User selected {code} for {scenario}"
- **Verify**: `collected["origin"]` or `collected["destination"]` updated correctly

**Issue**: Parser not recognizing selection
- **Check**: Airport code is in `available_airports` list
- **Solution**: Add common name variations to `airport_name_map`

## Known Limitations

- **All-in-one messages**: Field extraction may require follow-up questions (~60% accuracy)
  - Example: "London to JFK Oct 15" may extract destination as "JFK Oct" (separate field extraction issue)
  - **Workaround**: Question-answer flow has ~95% accuracy and always works correctly
- **Recommendation**: For complex bookings, let chatbot ask questions step-by-step for best results
