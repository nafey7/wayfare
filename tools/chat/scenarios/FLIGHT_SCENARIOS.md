# Flight Agent Test Scenarios

**Total: 30 scenarios** (9 categories) | **Issue: #895**
**Agent:** Flight Booking Agent (LangGraph ReAct)
**Tools:** resolve_airport, parse_dates, search_flights, find_nearby_airports, hand_back_to_supervisor

---

## 02_flight_basic — Basic Flight Search (7 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 2.1 | One-Way Asks All | Origin+dest only → asks missing fields (dates, pax, trip type) | contains: date, passenger, adult |
| 2.2 | Round-Trip All Fields | All 5 fields + date range → immediate search, no trip type Q | type: flight_search_results, not_contains: "one-way or round" |
| 2.4 | Solo Traveler Shorthand | "just me" = 1 adult | type_in: flight_search_results |
| 2.5 | Contextual Origin Question | Destination only → asks for origin | contains: flying from, where, origin |
| 2.6 | All Fields One Message | Multi-pax + all fields → immediate search | type_in: flight_search_results, not_contains: "one-way or round" |
| 2.7 | Explicit One-Way | "one way" keyword → no trip type question | not_contains: "round trip" |
| 2.8 | Explicit Round-Trip | "round trip" + single date → asks return date, not trip type | contains: return, come back |

---

## 03_flight_multicity — Multi-City Flights (2 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 3.1 | Basic Multi-City | 3-leg trip (LDN→PAR→ROM→LDN) + 2 adults | type_in: multicity/flight_search_results/conversation, contains: London, Paris, Rome |
| 3.2 | Multi-City IATA Codes | IATA codes only (LHR→CDG→FCO) | type_in: multicity/flight_search_results/conversation, contains: London, Paris, Rome |

---

## 04_flight_dates — Date Parsing (5 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 4.2 | Date Range Auto Round-Trip | Two dates → auto round-trip, no trip type question | type: flight_search_results, has_data: true |
| 4.3 | Month Only Asks Specific | "in July" → asks for specific dates | contains: specific, departure date |
| 4.4 | Departure Window Flexible | "anytime in June" → date-range search or asks | type_in: flight_search_results/date_range/conversation |
| 4.6 | Weekend Reference | "next weekend" → searches or confirms dates | type_in: flight_search_results/conversation |
| 4.8 | Date With Duration | "May 29 for a week" → auto round-trip | type_in: flight_search_results/conversation |

---

## 05_flight_airports — Airport Resolution (6 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 5.3 | Country Name (Japan) | "Japan" → suggests popular airports (NRT, HND, KIX) | contains: tokyo, narita, haneda, osaka |
| 5.5 | Airports Near | "airports near San Luis Obispo" | contains: airport, nearby, nearest |
| 5.6 | Disambiguation | "London to New York" → may show airport options | contains: JFK, Newark, London, New York |
| 5.7 | Same Origin/Destination | "London to London" → error, asks different city | contains: same, different, cannot |
| 5.8 | Country as Destination | "London to Spain" → asks which city in Spain | contains: city, which, Spain |
| 5.9 | Small/Regional Airport | "Inverness to Barcelona" → results or nearby suggestion | contains: results or nearby airports |

---

## 06_flight_filters — Search Filters (10 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 6.1 | Price Budget | "under 300 euros" → price_max filter | type_in: flight_search_results |
| 6.2 | Cabin Business | "business class" → cabin_class=business | contains: business |
| 6.3 | Direct Only | "direct flights" → max_stops=0 | contains: direct, non-stop |
| 6.4 | Airline Preference | "One way KLM flights" → preferred_airline=KL, KLM-only results | contains: KLM |
| 6.5 | Max Stops | "maximum 1 stop" → max_stops=1 | contains: stop |
| 6.6 | Morning Departure | "morning flights" → departure_time_preference | contains: morning, AM |
| 6.7 | Duration Limit | "under 5 hours" → max_outbound_duration=5 | contains: hour, duration |
| 6.8 | Cabin First | "first class" → cabin_class=first | contains: first |
| 6.9 | Combined Filters | "direct business class" → both filters | contains: business, direct |
| 6.10 | Price Range | "between 200 and 400" → price_min + price_max | type_in: flight_search_results |

---

## 07_flight_after — Post-Search Actions (2 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 7.1 | Booking Redirect | Search → "book cheapest" → BOOK NOW redirect | Step 2 contains: book now, flight card |
| 7.2 | Book Without Search | "book me a flight" with no search → collects info | contains: where, passenger, destination |

---

## 08_flight_passengers — Passenger Types (3 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 8.1 | Children With Ages | "2 adults and 1 child age 8" | type_in: flight_search_results |
| 8.2 | Infant | "2 adults 1 infant" | type_in: flight_search_results |
| 8.3 | Group Travel | "4 adults" | type_in: flight_search_results |

---

## 17_flight_handback — Agent Hand-back (1 scenario, 2 steps)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 17.1 | Hotel During Flight | Switch from flight to hotel mid-conversation | Step 1: flight fields, Step 2: hotel fields |

---

## 20_flight_results — Search Results Validation (2 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 20.1 | Results Have Data | Search returns structured data | has_data: true |
| 20.2 | Results Contain Airlines | Results include mock airline names | contains: British Airways, Ryanair, KLM |

---

## Coverage Matrix

| Feature | Scenario(s) | Tool Tested |
|---------|-------------|-------------|
| Missing field collection | 2.1, 2.5, 7.2 | — (prompt logic) |
| All fields → immediate search | 2.2, 2.6, 4.2 | resolve_airport, parse_dates, search_flights |
| Solo traveler shorthand | 2.4 | search_flights |
| Trip type auto-detection | 2.2, 2.6, 4.2 | parse_dates (two dates → round-trip) |
| Explicit one-way | 2.7 | search_flights |
| Explicit round-trip + single date | 2.8 | parse_dates, prompt logic |
| Multi-city trip | 3.1, 3.2 | resolve_airport, search_flights (segments) |
| Date range auto round-trip | 4.2 | parse_dates |
| Month-only date | 4.3 | parse_dates |
| Departure window | 4.4 | parse_dates, search_flights (date range) |
| Weekend reference | 4.6 | parse_dates |
| Duration-based dates | 4.8 | parse_dates |
| Country name → airport suggestions | 5.3, 5.8 | resolve_airport |
| Nearby airports | 5.5 | find_nearby_airports |
| Airport disambiguation | 5.6 | resolve_airport |
| Origin = destination guard | 5.7 | prompt logic |
| Country as destination | 5.8 | resolve_airport (country mismatch) |
| Small/regional airport | 5.9 | resolve_airport, search_flights |
| Price budget filter | 6.1 | search_flights (price_max) |
| Cabin class (business) | 6.2 | search_flights (cabin_class) |
| Direct flights only | 6.3 | search_flights (max_stops=0) |
| Airline preference | 6.4 | search_flights (preferred_airline=KL) |
| Max stops filter | 6.5 | search_flights (max_stops) |
| Morning departure | 6.6 | search_flights (departure_time_preference) |
| Duration limit | 6.7 | search_flights (max_outbound_duration) |
| First class | 6.8 | search_flights (cabin_class) |
| Combined filters | 6.9 | search_flights (multiple filters) |
| Price range (min+max) | 6.10 | search_flights (price_min + price_max) |
| Booking redirect | 7.1 | prompt logic (post-search) |
| Book without search | 7.2 | prompt logic |
| Children with ages | 8.1 | search_flights (children) |
| Infant passenger | 8.2 | search_flights (infants) |
| Group travel | 8.3 | search_flights (adults=4) |
| Hand-back to supervisor | 17.1 | hand_back_to_supervisor |
| Structured data validation | 20.1 | search_flights |
| Result content validation | 20.2 | search_flights |

---

## Not Yet Covered (Future)

| Feature | Why Excluded |
|---------|-------------|
| True no-results (unsupported route) | Mock FlightLogic API returns results for any valid IATA pair |
| Premium economy cabin | Lower priority, same mechanism as business/first |
| Arrival time preference | Same mechanism as departure time preference |
| Inbound duration filter | Round-trip specific, same mechanism as outbound |
| Multi-step field collection | Multi-turn conversations are flaky with LLM non-determinism |

**Total: 30 scenarios (28 single-step + 1 multi-step = 30 steps + 1 extra = 31 steps)**
