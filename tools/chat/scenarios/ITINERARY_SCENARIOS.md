# Itinerary Agent Test Scenarios

**Total: 38 scenarios** (7 categories) | **Issue: #914**
**Agent:** Itinerary Planning Agent (LangGraph ReAct)
**Tools:** parse_dates, update_trip_info, generate_itinerary, estimate_budget, hand_back_to_supervisor

---

## 11_itinerary_basic — Core Generation (8 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 11.1 | Immediate Generation | All fields in one message → generates immediately | type: itinerary_results |
| 11.2 | Partial Asks Missing | Destination + duration only → asks departure date | contains: when, dates, departure |
| 11.3 | Destination Only | "Plan a trip to Paris" → asks dates/duration | contains: when, how long, dates |
| 11.4 | Duration Derives Return | "5-day trip starting May 30" → derives return, generates | type: itinerary_results |
| 11.5 | Vague Timing With Duration | "next week" + duration → parse_dates resolves, generates | type: itinerary_results |
| 11.6 | Default 1 Adult | No passengers → defaults to 1, does NOT ask | not_contains: how many, travelers |
| 11.7 | Multi-Pax Extraction | "2 adults 2 kids" → extracts, generates | type: itinerary_results |
| 11.8 | Interests Included | "food and culture trip" → generates with focus | contains: food, culture, restaurant |

---

## 12_itinerary_mods — Post-Generation Modifications (8 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 12.1 | Relaxed Modification | "make it more relaxed" → regenerates | type: itinerary_results |
| 12.2 | Add Activity | "add food tours" → regenerates with food | contains: food, culinary, tasting |
| 12.3 | Change Duration | "make it 5 days instead" → regenerates longer | contains: 5, extended |
| 12.4 | Text Reply Not Regen | "looks great, thanks!" → text reply only | type NOT: itinerary_results |
| 12.5 | Question About Plan | "what's the best thing on day 2?" → text reply | contains: day 2, recommend |
| 12.6 | Change to Luxury | "change to 5-star hotels" → regenerates luxury | contains: luxury, 5-star, premium |
| 12.7 | Change Pace | "make it more packed" → regenerates busy | contains: packed, activities |
| 12.8 | Add Food Interest | "add more food experiences" → regenerates food focus | contains: food, restaurant, culinary |

---

## 14_itinerary_dates — Date Handling (5 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 14.1 | Explicit Date Range | "May 10-15" → generates immediately | type: itinerary_results |
| 14.2 | Relative Dates | "next Friday for 3 days" → parse_dates resolves | type: itinerary_results |
| 14.3 | Season Reference | "cherry blossom season" → handles or asks dates | contains: cherry blossom, spring, March |
| 14.4 | Duration Only No Start | "4-day trip to Rome" → asks departure date | contains: when, departure, date |
| 14.5 | Long Weekend | "long weekend starting next Friday" → resolves | contains: Amsterdam, weekend, day |

---

## 15_itinerary_handback — Hand-back to Supervisor (4 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 15.1 | Book Everything | Generate → "book everything" → routes to flight+hotel | contains: flight, hotel, book |
| 15.2 | Book Flights | Generate → "book flights" → routes to flight agent | contains: flight, Amsterdam, Barcelona |
| 15.3 | Book Hotels | Generate → "find hotels" → routes to hotel agent | contains: hotel, Tokyo, room |
| 15.4 | Out-of-Scope | Generate → "visa for Bali?" → detour/answer | contains: visa, passport, Indonesia |

---

## 16_itinerary_destinations — Destination Resolution (4 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 16.1 | City Abbreviation | "NYC" → resolves to New York | contains: New York, NYC, Manhattan |
| 16.2 | Vague Destination | "beach vacation" → asks which city | contains: which, where, city |
| 16.3 | Country Name | "Japan" → picks city or asks which | contains: Tokyo, Kyoto, Japan |
| 16.4 | Destination + Purpose | "London for a conference" → trip planning | type: itinerary_results, contains: London |

---

## 18_itinerary_context — Cross-Agent Data (3 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 18.1 | Has Origin | "from Amsterdam to Paris" → origin in response | contains: Amsterdam, Paris |
| 18.2 | Response Has Dates | Full fields → response has data | has_data: true |
| 18.3 | Structured Data | Generated itinerary has structured data | has_data: true |

---

## 19_itinerary_preferences — Inline Preferences & Interests (6 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 19.1 | Food & Culture | "food and culture trip to Barcelona" | contains: food, restaurant, culture, museum |
| 19.2 | Adventure | "adventure trip to Queenstown" | contains: adventure, hiking, bungee |
| 19.3 | Luxury | "luxury 5-star trip to Dubai" | contains: luxury, 5-star, fine dining |
| 19.4 | Budget-Friendly | "budget-friendly trip to Bangkok" | contains: budget, affordable, street food |
| 19.5 | Family Trip | "family trip to Orlando, 2 adults 2 kids" | contains: family, kids, theme park, Disney |
| 19.6 | Nightlife | "nightlife trip to Berlin" | contains: nightlife, bar, club, evening |

---

## Coverage Matrix

| Feature | Scenario(s) | Tool Tested |
|---------|-------------|-------------|
| Immediate generation (all fields) | 11.1, 11.4, 11.7, 14.1 | parse_dates, update_trip_info, generate_itinerary |
| Missing field collection | 11.2, 11.3, 14.4 | — (prompt logic) |
| Duration → return date derivation | 11.4, 11.5, 14.2 | parse_dates |
| Default 1 adult (no ask) | 11.6 | — (prompt rule) |
| Multi-pax extraction | 11.7, 19.5 | update_trip_info |
| Interest extraction | 11.8, 19.1-19.6 | generate_itinerary (interests param) |
| Post-gen modification | 12.1-12.3, 12.6-12.8 | generate_itinerary (modification_notes) |
| Text reply (no regen) | 12.4, 12.5 | — (MODE 2 prompt rule) |
| Luxury/budget preferences | 12.6, 19.3, 19.4 | generate_itinerary |
| Pace changes | 12.7 | generate_itinerary (modification_notes) |
| Explicit date range | 14.1 | parse_dates |
| Relative dates | 14.2, 14.5 | parse_dates |
| Seasonal references | 14.3 | parse_dates |
| Book everything → handback | 15.1 | hand_back_to_supervisor |
| Book flights → handback | 15.2 | hand_back_to_supervisor |
| Book hotels → handback | 15.3 | hand_back_to_supervisor |
| Out-of-scope detour | 15.4 | hand_back_to_supervisor |
| City abbreviations (NYC) | 16.1 | generate_itinerary |
| Vague destination | 16.2 | — (prompt rule) |
| Country → city resolution | 16.3 | — (prompt rule) |
| Destination + purpose | 16.4 | generate_itinerary |
| Origin in response | 18.1 | update_trip_info |
| Structured data validation | 18.2, 18.3 | generate_itinerary |
| Family activities | 19.5 | generate_itinerary |
| Nightlife focus | 19.6 | generate_itinerary |

---

## Not Yet Covered (Future)

| Feature | Why Excluded |
|---------|-------------|
| Profile-based preferences (travel_style from DB) | Test user has no preferences seeded; requires DB setup |
| Budget estimation (estimate_budget tool) | Rarely triggered in single-turn; needs multi-turn sequence |
| Multi-city itinerary ("Paris then Rome") | Complex multi-turn; high LLM non-determinism |
| Itinerary enrichment (Google Places images) | Async fire-and-forget; not observable via chat response text |
| Cross-agent param validation (flight agent receives correct dates) | Requires 3+ turn scenario; flaky with LLM |

**Total: 38 scenarios (18 single-step + 20 multi-step = 58 steps)**
