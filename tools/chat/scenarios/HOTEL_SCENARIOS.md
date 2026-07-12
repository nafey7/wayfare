# Hotel Agent Test Scenarios

**Total: 28 scenarios** (6 categories) | **Last Run: 2026-04-27** | **Result: 28/28 PASS (local)**
**Agent:** Hotel Booking Agent (LangGraph ReAct)
**Tools:** resolve_city, parse_dates, search_hotels, select_hotel, hand_back_to_supervisor

---

## 09_hotel_basic — Basic Hotel Search (6 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 9.1 | Asks Missing Fields | City-only → asks for dates + guests | contains: check-in, guest, hotel |
| 9.3 | Relative Dates Confirm | "next weekend" parsed, no re-ask | not_contains: "exact dates" |
| 9.4 | All Fields Immediate | All 4 fields → immediate search | type_in: hotel_search_results |
| 9.5 | Missing Dates Only | City + guests → asks for dates | contains: check-in, date, night |
| 9.6 | Missing Guests Only | City + dates → asks for guests | contains: guest, adult, how many |
| 9.7 | Children and Rooms | Multi-room + children → search | type_in: hotel_search_results |

---

## 10_hotel_dates — Hotel Date Parsing (3 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 10.1 | Weekend Dates | "next weekend" → correct dates | type_in: hotel_search_results/conversation |
| 10.2 | Duration Nights | "for 3 nights" → checkin + 3 | type_in: hotel_search_results |
| 10.3 | Night Semantics | "Friday and Saturday night" = 2 nights | not_contains: "exact dates" |

---

## 13_hotel_filters — Hotel Search Filters (12 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 13.1 | Price Budget | Under $100/night → no results (mock) | contains: no hotels, range, adjust |
| 13.2 | Star Rating | 5-star filter → only 5-star hotels | contains: 5-star, Atlantis, Burj |
| 13.3 | Amenity Pool | Pool filter → only pool hotels | contains: Pool, Mandarin |
| 13.4 | Refundable Only | Refundable filter → all refundable | contains: Refundable, Montmartre, Le Marais |
| 13.5 | Locality Neighbourhood | Montmartre, Paris → name-match filter | contains: Montmartre, Arts |
| 13.6 | Property Type | Resort filter → no Resort type (mock) | contains: Resort, property type |
| 13.7 | Budget Higher | Under $2500 → all Paris hotels pass | contains: Montmartre, Le Marais, Plaza |
| 13.8 | Locality Not Found (Bangkok) | Waikiki Beach in Bangkok → suggest real areas | contains: Riverside, Siam, Silom |
| 13.9 | Locality Silom Bangkok | Silom area → Lub d Bangkok Silom | contains: Silom, Lub d |
| 13.10 | Locality Shinjuku Tokyo | Shinjuku → resolves as separate city (Google quirk) | contains: Shinjuku |
| 13.11 | Locality Covent Garden London | Covent Garden → The Savoy | contains: Savoy, Covent Garden |
| 13.12 | Locality Not Found Paris | Bastille → proximity fallback finds Le Marais | contains: Montmartre, Le Marais, Champs |

---

## 14_hotel_city — City Resolution (3 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 14.1 | Simple City | Unambiguous city resolves immediately | type_in: hotel_search_results |
| 14.2 | Disambiguation | Ambiguous city auto-resolves (Google Geocoding) | contains: Birmingham |
| 14.3 | City Not Found | Invalid city → helpful error | contains: couldn't find, check spelling |

---

## 16_hotel_handback — Agent Hand-back (1 scenario, 2 steps)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 16.1 | Flight During Hotel | Switch from hotel to flight mid-conversation | Step 1: hotel_conversation, Step 2: flight fields |

---

## 19_hotel_results — Search Results Validation (2 scenarios)

| # | Scenario | What it tests | Key assertions |
|---|----------|---------------|----------------|
| 19.1 | Results Have Data | Search returns structured data | has_data: true |
| 19.2 | Results Min Count | Paris returns hotel results | contains: Montmartre, Le Marais, Plaza |

---

## Summary Table

| # | Scenario | Group | City | Filter |
|---|----------|-------|------|--------|
| 1 | 9.1 Asks Missing Fields | basic | Dubai | — |
| 2 | 9.3 Relative Dates Confirm | basic | Tokyo | — |
| 3 | 9.4 All Fields Immediate | basic | London | — |
| 4 | 9.5 Missing Dates Only | basic | Barcelona | — |
| 5 | 9.6 Missing Guests Only | basic | Rome | — |
| 6 | 9.7 Children and Rooms | basic | Paris | — |
| 7 | 10.1 Weekend Dates | dates | Tokyo | — |
| 8 | 10.2 Duration Nights | dates | Berlin | — |
| 9 | 10.3 Night Semantics | dates | Amsterdam | — |
| 10 | 13.1 Price Budget | filters | Madrid | price_max |
| 11 | 13.2 Star Rating | filters | Dubai | min_rating=5 |
| 12 | 13.3 Amenity Pool | filters | Bangkok | required_facilities=[pool] |
| 13 | 13.4 Refundable Only | filters | Paris | refundable_only |
| 14 | 13.5 Locality Neighbourhood | filters | Paris | locality=Montmartre |
| 15 | 13.6 Property Type | filters | Bali | property_types=[Resort] |
| 16 | 13.7 Budget Higher | filters | Paris | price_max=2500 |
| 17 | 13.8 Locality Not Found | filters | Bangkok | locality=Waikiki Beach |
| 18 | 13.9 Locality Silom | filters | Bangkok | locality=Silom |
| 19 | 13.10 Locality Shinjuku | filters | Tokyo | locality=Shinjuku |
| 20 | 13.11 Locality Covent Garden | filters | London | locality=Covent Garden |
| 21 | 13.12 Locality Not Found Paris | filters | Paris | locality=Bastille |
| 22 | 14.1 Simple City | city | Tokyo | — |
| 23 | 14.2 Disambiguation | city | Birmingham | — |
| 24 | 14.3 City Not Found | city | Xyzzyville | — |
| 25 | 16.1 Flight During Hotel | handback | Paris | — |
| 26 | 19.1 Results Have Data | results | London | — |
| 27 | 19.2 Results Min Count | results | Paris | — |

**Total: 28 scenarios (27 rows + 16.1 has 2 steps = 29 steps)**

---

## Coverage Matrix

| Feature | Scenario(s) | Tool Tested | Status |
|---------|-------------|-------------|--------|
| Missing field collection | 9.1, 9.5, 9.6 | — (prompt logic) | PASS |
| All fields → immediate search | 9.4, 14.1 | resolve_city, parse_dates, search_hotels | PASS |
| Relative dates | 9.3, 10.1, 10.3 | parse_dates | PASS |
| Duration dates | 10.2 | parse_dates | PASS |
| Night semantics | 10.3 | parse_dates | PASS |
| Multi-room + children | 9.7 | search_hotels | PASS |
| Price filter | 13.1, 13.7 | search_hotels (price_max) | PASS |
| Star rating filter | 13.2 | search_hotels (min_rating) | PASS |
| Amenity filter | 13.3 | search_hotels (required_facilities) | PASS |
| Refundable filter | 13.4 | search_hotels (refundable_only) | PASS |
| Locality name-match | 13.5, 13.9, 13.11 | search_hotels (locality) | PASS |
| Locality not-found + suggestions | 13.8, 13.12 | search_hotels (locality fallback) | PASS |
| Locality proximity fallback | 13.12 | search_hotels (geocode + radius) | PASS |
| Locality Google quirk | 13.10 | resolve_city (Shinjuku as city) | PASS |
| Property type filter | 13.6 | search_hotels (property_types) | PASS |
| City resolution | 14.1 | resolve_city | PASS |
| City disambiguation | 14.2 | resolve_city | PASS |
| City not found | 14.3 | resolve_city | PASS |
| Hand-back to supervisor | 16.1 | hand_back_to_supervisor | PASS |
| Structured data validation | 19.1 | search_hotels | PASS |
| Result count validation | 19.2 | search_hotels | PASS |

## Not Yet Covered (Future)

| Feature | Why Excluded |
|---------|-------------|
| select_hotel (booking redirect) | Multi-step flow, depends on search succeeding first — flaky |
| "from [city]" origin distinction | Non-deterministic disambiguation — previously deleted as flaky |
| Flexible dates (departure window) | Complex assertion on is_departure_window flag |
| Children age validation | Edge case, hard to assert reliably |
| Cross-agent context sharing | Tested indirectly via 16.1 hand-back |
