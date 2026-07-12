# Flight Filter Test Prompts

**Purpose**: QA testing for all flight filters available in the chat interface.
**How to test**: Enter each prompt into the chat. Verify results match the expected outcome.
**Source**: Curated from manual QA testing (2026-01-26), adapted for Chat CLI automation.

**Usage with Chat CLI**:
```bash
# Run a single prompt
python3 tools/chat/voya_chat.py --env staging -m "Direct flights from London to Paris tomorrow one way" --json

# Run the smoke test scenario
python3 tools/chat/voya_chat.py --env staging --scenario flight_filter_smoke
```

---

## 1. Cabin Class Filter

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 1.1 | `Flights from London to Dubai tomorrow one way economy` | Results in Economy class |
| 1.2 | `Business class flights from London to New York next Monday` | Results in Business class |
| 1.3 | `Premium economy flights from London to Sydney next week one way` | Results in Premium Economy class |
| 1.4 | `First class flights from London to Paris tomorrow` | Results in First class |
| 1.5 | `I want to fly business from Manchester to Dubai on 20th March` | Results in Business class |

---

## 2. Direct Flight / Max Stops Filter

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 2.1 | `Direct flights from London to Paris tomorrow one way` | Only direct flights (no stops) |
| 2.2 | `Non-stop flights from London to New York next week` | Only direct flights (no stops) |
| 2.3 | `Flights from London to Bangkok with max 1 stop tomorrow` | Flights with 0 or 1 stop only |
| 2.4 | `London to Tokyo max 1 stopover next Monday one way` | Flights with 0 or 1 stop only |
| 2.5 | `Flights from London to Sydney with no more than 2 stops` | Flights with 0, 1, or 2 stops only |

---

## 3. Price Filter

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 3.1 | `Flights from London to Paris tomorrow under $200` | Only flights priced <= $200 (or message if none found) |
| 3.2 | `Cheap flights from London to Amsterdam tomorrow, budget $100` | Only flights <= $100 |
| 3.3 | `Flights from London to Madrid costing less than 150 dollars` | Only flights <= $150 |
| 3.4 | `Flights from London to Rome tomorrow over $300` | Only flights >= $300 |
| 3.5 | `Flights from London to Barcelona between $100 and $300` | Only flights $100-$300 |
| 3.6 | `Show me flights from London to Lisbon priced between 150 and 400 dollars tomorrow` | Only flights $150-$400 |

---

## 4. Preferred Airline Filter

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 4.1 | `British Airways flights from London to Paris tomorrow one way` | Only BA flights shown |
| 4.2 | `I want to fly easyJet from London to Dubai next week` | Only easyJet flights shown |
| 4.3 | `Air France flights London to Frankfurt tomorrow` | Only AF flights shown |
| 4.4 | `Air France flights from London to Paris tomorrow` | Only AF flights shown |
| 4.5 | `KLM flights from London to Amsterdam tomorrow one way` | Only KL flights shown |
| 4.6 | `Fly with Ryanair from London to Madrid tomorrow` | Only FR flights shown |

---

## 5. Outbound Duration Filter

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 5.1 | `Flights from London to Paris under 2 hours tomorrow one way` | Only outbound <= 120 min |
| 5.2 | `London to Amsterdam max 1.5 hour flight tomorrow` | Only outbound <= 90 min |
| 5.3 | `Flights from London to Madrid shorter than 3 hours tomorrow` | Only outbound <= 180 min |
| 5.4 | `London to Paris tomorrow, max 90 minute flight` | Only outbound <= 90 min |
| 5.5 | `Flights under 2.5 hours from London to Berlin tomorrow` | Only outbound <= 150 min |
| 5.6 | `London to Dubai tomorrow flights less than 7 hours` | Only outbound <= 420 min |

---

## 6. Inbound Duration Filter (Round Trips)

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 6.1 | `Return flights London to Paris next Monday returning Friday, max 2 hour return flight` | Only inbound <= 120 min |
| 6.2 | `London to Amsterdam return next week, inbound under 2 hours` | Only inbound <= 120 min |
| 6.3 | `Round trip London to Barcelona departing Monday returning Thursday, max 3 hours each way` | Both outbound <= 180 min AND inbound <= 180 min |
| 6.4 | `Return flights London to Rome next week, flights under 3 hours each direction` | Both legs <= 180 min |

---

## 7. Combined Filters

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 7.1 | `Direct Business class flights from London to New York next Monday` | Direct only + Business class |
| 7.2 | `British Airways business class from London to New York next week` | BA only + Business class |
| 7.3 | `Direct flights from London to Paris under $200 tomorrow` | Direct only + price <= $200 |
| 7.4 | `Flights from London to Paris under 2 hours under $300 tomorrow` | Outbound <= 120 min + price <= $300 |
| 7.5 | `British Airways flights from London to Paris under 2 hours tomorrow` | BA only + outbound <= 120 min |
| 7.6 | `Direct British Airways flights under $500 from London to New York next week` | Direct + BA + price <= $500 |
| 7.7 | `Business class direct flights under $1000 from London to Dubai next Monday` | Business + direct + price <= $1000 |
| 7.8 | `London to Paris tomorrow max 1 stop under $200 economy` | Max 1 stop + price <= $200 + Economy |

---

## 8. Edge Cases and Negative Tests

| # | Prompt | Expected Outcome |
|---|--------|-----------------|
| 8.1 | `London to Paris tomorrow one way max 30 minute flight` | No flights found (unrealistic) + helpful message |
| 8.2 | `London to New York direct tomorrow` | No direct flights message (transatlantic) OR direct flights if available |
| 8.3 | `Flights under $50 from London to New York next week` | No flights message (price too low) |
| 8.4 | `Concorde flights from London to Paris` | No flights or ignore unknown airline |
| 8.5 | `Flights from London to Paris next week` then follow-up: `show only British Airways` | Re-search with BA filter applied |
| 8.6 | `London to Paris tomorrow 2 adults business class` | Business class for 2 adults |
| 8.7 | `Flights from London to Paris in 90 minutes or less tomorrow` | Outbound <= 90 min (1.5 hours) |
| 8.8 | `Round trip London to Paris next Monday return Friday under 1 hour each way` | No flights (Paris is ~1h25 min) + helpful message |

---

## 9. "See Full Results" Button Verification

For each filter test that returns results, click the **"Click to see full results"** button and verify:

| # | What to verify |
|---|---------------|
| 9.1 | **Cabin class**: Flight-booker loads with correct cabin class pre-selected |
| 9.2 | **Direct flight**: Flight-booker loads with "Direct only" checkbox checked |
| 9.3 | **Max stops**: Flight-booker URL contains `max_stops=N` and slider is pre-set |
| 9.4 | **Price filter**: Flight-booker URL contains `price_min` / `price_max` and sliders are pre-set |
| 9.5 | **Preferred airline**: Flight-booker URL contains `preferred_airline=XX` and that airline's checkbox is auto-checked |
| 9.6 | **Outbound duration**: Flight-booker URL contains `max_outbound_duration=N` and slider is pre-set |
| 9.7 | **Inbound duration**: Flight-booker URL contains `max_inbound_duration=N` and slider is pre-set |
| 9.8 | **No filter loss**: All chat filters are preserved in the flight-booker URL |
| 9.9 | **Result count**: Flight-booker shows "X out of 30" (total from API), not "X out of X" (confirming client-side filter) |

---

## 10. Quick Smoke Test (Priority Order)

Run these first for a fast pass/fail check:

1. `Direct flights from London to Paris tomorrow one way` -> Direct only
2. `British Airways flights from London to Paris tomorrow` -> BA only
3. `Flights under $300 from London to Amsterdam tomorrow` -> Price <= $300
4. `Flights from London to Paris under 2 hours tomorrow` -> Outbound <= 120 min
5. `Business class London to New York next Monday` -> Business class
6. `Direct BA flights under $500 from London to New York next week` -> Combined

**Automated scenario**: `python3 tools/chat/voya_chat.py --scenario flight_filter_smoke`

---

## Test Summary

| Category | Count | Automatable |
|----------|-------|-------------|
| Cabin class | 5 | Yes (expect_type) |
| Direct/stops | 5 | Yes (expect_type) |
| Price | 6 | Partial (can't verify price filtering) |
| Airline | 6 | Partial (expect_contains airline name) |
| Outbound duration | 6 | Partial (can't verify duration filtering) |
| Inbound duration | 4 | Partial |
| Combined | 8 | Partial |
| Edge cases | 8 | Partial (some expect no results) |
| UI verification | 9 | No (requires browser) |
| Smoke test | 6 | Yes (scenario file) |
| **Total** | **63** | |

**Note**: Full filter verification (correct prices, durations, airlines in results) requires inspecting the response data structure. The scenario runner can verify that a search completes successfully (`expect_type: flight_search_results`) and contains expected keywords (`expect_contains`), but cannot validate the actual filter application. Use the Langfuse trace detail view to verify filter parameters were passed to the FlightLogic API correctly.
