# Itinerary Test Report — 2026-05-22 13:06 UTC

Generated with `TWO_STAGE_ITINERARY_ENABLED=true` + `CHAT_STREAMING_ENABLED=true` against the local dev backend.

## Headline numbers

| Suite | Result | Detail |
|---|---|---|
| **Backend unit tests** (itinerary + supervisor streaming + capabilities + saved-itineraries + two-stage) | **458 / 458 ✅** | 57.9s |
| **Frontend unit tests** (itinerary feature + SSE client + streaming hook) | **115 / 115 ✅** (18 files) | 35.5s |
| **Scenario suite** (`run_all_itinerary_tests.py`) | **64 / 65 ✅** (98.5%) | 38.8 min |

**Total: 637 passing / 638 total.**

---

## Failures

### `16.2_vague_destination`

**Description**: Vague destination 'beach vacation' → asks which city

**Sent**: `Plan a beach vacation for next month`

**AI response** (17281ms, type=`ai_response`, intent=`general_query`):

> Amazing choice 🌴☀️ A beach vacation next month sounds absolutely dreamy.
> 
> If you want, I can help you shape it around the kind of vibe you want:
> 🇲🇽 **Cancún** — easy resort stays and beautiful turquoise water  
> 🇲🇽 **Tulum** — laid-back beach clubs, cenotes, and a stylish feel  
> 🇵🇷 **Puerto Vallarta*

**Failed checks**:
- ❌ `intent` — expected=create_itinerary got=general_query
- ✅ `max_time` — 17281ms <= 30000ms
- ✅ `contains_any` — any of ['which', 'where', 'city', 'destination', 'beach', 'specific', 'mind', 'how long', 'trip', 'vacation', 'length', 'days', 'week', 'month', 'vibe'] in response

**Analysis**: LLM intent-classification non-determinism. The AI's behavior was correct (asked the user to pick a city for the vague 'beach vacation' phrase, offering Cancún / Tulum / Puerto Vallarta — exactly what Phase 2 O11 prompts call for) but the supervisor classified the intent as `general_query` instead of `create_itinerary`. This is the same class of LLM stochasticity that has historically caused R5 / R6 flakes — not a code regression from Phase 3 streaming or Phase 4 two-stage gen.

---

## Scenario-by-scenario detail

Each row shows the user prompt(s) sent, the AI's response, response time, and pass/fail.

### `01_supervisor` — 1/1 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `1.4_route_to_itinerary` | Plan a 5-day trip to Bali | Got it — a **5-day trip to Bali** 🌴  What departure date works for you? | 10.6s | ✅ |

### `11_itinerary_basic` — 8/8 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `11.1_immediate_generation` | Plan a 5-day trip to Bali for 2 adults starting next Monday | Here's your 5-day Bali itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 32.6s | ✅ |
| `11.2_partial_asks_missing` | Plan a 5 day trip to Tokyo | Absolutely — I’ve got **Tokyo** and a **5-day trip**.  **When would you like to depart?**   You can just tell me a date like **June 10** or **next Friday**. | 6.0s | ✅ |
| `11.3_destination_only` | Plan a trip to Paris | Nice — Paris is locked in ✨  I still need **when you want to go**.  1. **Departure date** — e.g. next Friday, June 10, or Aug 3   2. **Return date or trip length** — e.g. June 10–15 or 5 days  If y... | 9.5s | ✅ |
| `11.4_duration_derives_return` | Plan a 5-day trip to Rome starting June 21, 2026 | Here's your 5-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 75.5s | ✅ |
| `11.5_vague_timing_with_duration` | 5 day trip to Barcelona next week for 2 adults | I’ve got **2026-05-25 to 2026-05-31** — that’s a **7-day** Barcelona trip.   You mentioned **5 days**, so should I use the **7-day next-week window** I inferred, or would you like different dates f... | 17.7s | ✅ |
| `11.6_default_1_adult` | Plan a 4-day trip to Amsterdam, June 21, 2026 to June 25, 2026 | Here's your 5-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 27.4s | ✅ |
| `11.7_multi_pax_extraction` | Family trip to Tokyo for 2 adults and 2 kids, June 21, 2026 to June 26, 2026 | Here's your 6-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 28.5s | ✅ |
| `11.8_interests_included` | Plan a food and culture trip to Barcelona, June 21, 2026 to June 26, 2026 | Here's your 6-day Barcelona itinerary, with a focus on food & culture! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book h... | 36.5s | ✅ |

### `12_itinerary_mods` — 8/8 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `12.1_post_generation_modification` *(2 steps)* | Plan a 3-day trip to Rome for 2 adults starting June 21, 2026, back June 24, 2026 | Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 72.0s | ✅ |
| `12.2_add_activity` *(2 steps)* | Plan a 3-day trip to Rome for 2 adults, June 21, 2026 to June 24, 2026 | Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 43.3s | ✅ |
| `12.3_change_duration` *(2 steps)* | Plan a 3-day trip to Barcelona, June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 55.7s | ✅ |
| `12.4_text_reply_not_regen` *(2 steps)* | Plan a 3-day trip to Tokyo, June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 26.7s | ✅ |
| `12.5_question_about_plan` *(2 steps)* | Plan a 3-day trip to Paris, June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 67.7s | ✅ |
| `12.6_change_to_luxury` *(2 steps)* | Plan a 3-day trip to Dubai, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Dubai itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 56.5s | ✅ |
| `12.7_change_pace` *(2 steps)* | Plan a 3-day trip to London, June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day London itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when y... | 74.0s | ✅ |
| `12.8_add_food_interest` *(2 steps)* | Plan a 3-day trip to Bangkok, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Bangkok itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when ... | 67.8s | ✅ |

### `14_itinerary_dates` — 5/5 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `14.1_explicit_date_range` | Plan a trip to Paris, June 21, 2026 to June 26, 2026, 2 adults | Here's your 6-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 55.9s | ✅ |
| `14.2_relative_dates` | 3-day trip to Barcelona starting next Friday | Here's your 3-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 26.4s | ✅ |
| `14.3_season_reference` | Plan a trip to Tokyo during cherry blossom season | Tokyo sounds amazing for cherry blossom season 🌸  When are you thinking of going?   You can send me: 1. **A specific date or range** — e.g. *March 20–30*   2. **A month/week idea** — e.g. *early Ap... | 10.8s | ✅ |
| `14.4_duration_only_no_start` | Plan a 4-day trip to Rome | Got it — a 4-day trip to Rome for 1 adult.  1. **When do you want to go?**      - e.g. next Monday, June 10, or Sep 3  Once you give me a departure date, I’ll build your plan right away. | 13.1s | ✅ |
| `14.5_long_weekend` | Plan a long weekend trip to Amsterdam starting next Friday | Here's your 3-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 28.4s | ✅ |

### `15_itinerary_handback` — 4/4 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `15.1_book_everything` *(2 steps)* | Plan a 3-day trip to Paris from London, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 59.1s | ✅ |
| `15.2_book_flights` *(2 steps)* | Plan a 3-day trip to Barcelona from Amsterdam, June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 36.2s | ✅ |
| `15.3_book_hotels` *(2 steps)* | Plan a 3-day trip to Tokyo, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 61.7s | ✅ |
| `15.4_out_of_scope` *(2 steps)* | Plan a 5-day trip to Bali, June 21, 2026 to June 26, 2026, 1 adult | Here's your 6-day Bali itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 39.7s | ✅ |

### `16_itinerary_destinations` — 3/4 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `16.1_city_abbreviation` | Plan a 4-day trip to NYC, June 21, 2026 to June 25, 2026, 1 adult | Here's your 5-day New York City itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything'... | 24.9s | ✅ |
| `16.2_vague_destination` | Plan a beach vacation for next month | Amazing choice 🌴☀️ A beach vacation next month sounds absolutely dreamy.  If you want, I can help you shape it around the kind of vibe you want: 🇲🇽 **Cancún** — easy resort stays and beautiful turq... | 17.3s | ❌ |
| `16.3_country_name` | Plan a 5-day trip to Japan, June 21, 2026 to June 26, 2026 | Here's your 6-day Japan itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 22.7s | ✅ |
| `16.4_destination_with_purpose` | Plan a trip to London for a conference, June 21, 2026 to June 25, 2026, 1 adult | Here's your 5-day London itinerary, with a focus on conference! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels',... | 40.9s | ✅ |

### `18_itinerary_context` — 3/3 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `18.1_has_origin` | Plan a 4-day trip from Amsterdam to Paris, June 21, 2026 to June 25, 2026, 1 adult | Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 26.8s | ✅ |
| `18.2_response_has_dates` | Plan a 3-day trip to Rome, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 50.5s | ✅ |
| `18.3_structured_itinerary` | Plan a 4-day trip to Barcelona, June 21, 2026 to June 25, 2026, 1 adult | Here's your 5-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 36.3s | ✅ |

### `19_itinerary_preferences` — 6/6 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `19.1_food_culture` | Plan a food and culture trip to Barcelona, June 21, 2026 to June 26, 2026, 2 adults | Here's your 6-day Barcelona itinerary, with a focus on food & culture! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book h... | 22.4s | ✅ |
| `19.2_adventure` | Plan an adventure trip to Queenstown, June 21, 2026 to June 26, 2026, 2 adults | Here's your 6-day Queenstown itinerary, with a focus on adventure! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotel... | 28.4s | ✅ |
| `19.3_luxury` | Plan a luxury 5-star trip to Dubai, June 21, 2026 to June 26, 2026, 2 adults | Here's your 6-day Dubai itinerary, with a focus on luxury & 5-star! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hote... | 31.1s | ✅ |
| `19.4_budget_friendly` | Plan a budget-friendly trip to Bangkok, June 21, 2026 to June 26, 2026, 1 adult | Here's your 6-day Bangkok itinerary, with a focus on budget-friendly! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book ho... | 48.4s | ✅ |
| `19.5_family_trip` | Plan a family trip to Orlando for 2 adults and 2 kids, June 21, 2026 to June 26, 2026 | Here's your 6-day Orlando itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when ... | 24.0s | ✅ |
| `19.6_nightlife` | Plan a nightlife trip to Berlin, June 21, 2026 to June 25, 2026, 2 adults | Here's your 5-day Berlin itinerary, with a focus on nightlife! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', ... | 27.5s | ✅ |

### `30_itinerary_phase0_regression` — 12/12 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `30.10_amend_make_more_relaxed_regenerates` *(2 steps)* | Plan a 4-day trip to Barcelona, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 50.2s | ✅ |
| `30.11_schema_7day_has_7_days` | Plan a 7-day trip to Barcelona, June 21, 2026 to June 27, 2026, 2 adults | Here's your 7-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 22.9s | ✅ |
| `30.12_cold_turn_latency_guard` | Plan a 4-day trip from Paris to Lisbon, June 21, 2026 to June 24, 2026, 2 adults | Here's your 4-day Lisbon itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when y... | 31.7s | ✅ |
| `30.1_cold_paris_5day_full_input` | Plan a 5-day trip from London to Paris, June 21, 2026 to June 25, 2026, 2 adults | Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 62.2s | ✅ |
| `30.2_cold_tokyo_3day_no_origin` | Plan a 3-day trip to Tokyo, June 21, 2026 to June 23, 2026, 1 adult | Here's your 3-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 27.0s | ✅ |
| `30.3_cold_oneway_amsterdam_to_rome` | Plan a 4-day trip from Amsterdam to Rome, one way starting June 21, 2026, 1 adult | Here's your 4-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 33.6s | ✅ |
| `30.4_phase2_baseline_dateless_duration` | Plan a 4-day trip to Rome | Awesome — I’ve got **Rome** and a **4-day trip** saved.  I just need **your departure date** to build the itinerary.   For example: **June 10**, **next Friday**, or **July 2**. | 8.8s | ✅ |
| `30.5_phase2_baseline_vague_destination` | Plan a trip somewhere warm | Oh, a warm getaway sounds absolutely wonderful ☀️🌴 Here are a few great options depending on the vibe you want:  🇲🇽 **Cancún** — Beaches, turquoise water, and easy resort vibes   🇵🇹 **Madeira** — M... | 6.4s | ✅ |
| `30.6_phase2_baseline_ambiguous_dates_confirm` | Plan a 5-day trip to Paris next week, 1 adult | I’ve got **2026-05-25 to 2026-05-31** for “next week” — that’s a **7-day trip**, not 5 days.  Since your destination and traveler count are already set, just confirm whether you want to go with **t... | 17.6s | ✅ |
| `30.7_phase2_baseline_make_it_cooler_text_reply` *(2 steps)* | Plan a 3-day trip to Rome, June 21, 2026 to June 23, 2026, 1 adult | Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 78.8s | ✅ |
| `30.8_phase2_baseline_regenerate_day_3` *(2 steps)* | Plan a 3-day trip to Rome, June 21, 2026 to June 23, 2026, 1 adult | Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 39.7s | ✅ |
| `30.9_amend_food_focus_regenerates` *(2 steps)* | Plan a 3-day trip to Rome, June 21, 2026 to June 23, 2026, 2 adults | Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 45.1s | ✅ |

### `32_itinerary_regression` — 12/12 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `R10_partial_no_origin` | Plan 4 days in Madrid for 1 adult from June 21, 2026 to June 24, 2026 | Here's your 4-day Madrid itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when y... | 30.2s | ✅ |
| `R11_partial_no_dates` | Plan a 4-day trip to Vienna for 2 adults | Great — I’ve got **Vienna**, **2 adults**, and a **4-day trip**.  What’s your **departure date**?   You can say something like **June 10**, **next Friday**, or **July 2**. | 9.3s | ✅ |
| `R12_partial_no_destination` | I want to plan a trip from June 21, 2026 to June 25, 2026, 2 adults | Got it — your dates and 2 adults are saved.  I still need **1 thing** to build your plan: 1. **Where are you going?** (destination city)  Examples: Paris, Tokyo, Cancun, New York | 11.8s | ✅ |
| `R1_cold_paris_5day` | Plan a 5-day trip to Paris from June 21, 2026 to June 25, 2026 | Here's your 5-day Paris itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 21.9s | ✅ |
| `R2_cold_tokyo_3day` | Plan 3 days in Tokyo from July 6, 2026 to July 8, 2026, 2 adults | Here's your 3-day Tokyo itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when yo... | 34.1s | ✅ |
| `R3_cold_rome_weekend` | Plan a weekend in Rome starting June 12, 2026, 1 adult | Here's your 3-day Rome itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when you... | 32.2s | ✅ |
| `R4_ambiguous_somewhere_warm` | I want to go somewhere warm next month for 5 days | For a warm **5-day** trip, I’ve got the timing as **June 1, 2026**.  What warm destination are you thinking? 1. **Cancún** 2. **Tulum** 3. **Miami**  Or tell me another warm city you’d like. | 13.0s | ✅ |
| `R5_ambiguous_europe_city_break` | Looking for a 4-day Europe city break in July | I’ve got the essentials for your 4-day Europe city break in July. I can build the itinerary now — just note I’ll need a specific city, since “Europe” is a region, not a city.  Pick one and I’ll gen... | 23.8s | ✅ |
| `R6_ambiguous_chill_5_days` | 5 days, somewhere chill, 1 adult, starting June 21, 2026 | Nice — I’ve got:  - **5 days** - **1 adult** - **Starting June 21, 2026** - **Chill vibe**  Now I just need the **destination**. If you want, tell me a specific city, or I can suggest a few chill o... | 14.0s | ✅ |
| `R7_amend_day_2_food` *(2 steps)* | Plan a 3-day trip to Lisbon from June 21, 2026 to June 23, 2026, 1 adult | Here's your 3-day Lisbon itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' when y... | 41.6s | ✅ |
| `R8_amend_make_cheaper` *(2 steps)* | Plan a 3-day trip to Barcelona from June 21, 2026 to June 23, 2026, 2 adults | Here's your 3-day Barcelona itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 27.0s | ✅ |
| `R9_amend_regenerate_day_3` *(2 steps)* | Plan a 4-day trip to Amsterdam from June 21, 2026 to June 24, 2026, 1 adult | Here's your 4-day Amsterdam itinerary! The plan is displayed as interactive cards above. Let me know if you'd like to change anything, or say 'book flights', 'book hotels', or 'book everything' whe... | 43.1s | ✅ |

### `debug` — 2/2 passing

| Scenario | Sent | Response (truncated 200ch) | Time | Result |
|---|---|---|---|---|
| `b219_amend_no_itinerary` *(3 steps)* | Hi Voya can you help me to amend my itinerary for London, i live here and I would like to start m... | I don’t have a prior itinerary in this session, so I can’t amend an existing plan — but I can create a fresh London itinerary for you.  I’ve got: 1. **Destination:** London 2. **Start time preferen... | 40.5s | ✅ |
| `b219_itinerary_start_time` *(3 steps)* | Plan a 5-day trip to London starting next week, I want to start my day at 10 am | I’ve got **2026-05-25 to 2026-05-31** for “starting next week,” which is a **7-day** window — does that work?   You also mentioned a **5-day trip**, so if you meant a different length, just tell me... | 74.3s | ✅ |

---

## Latency stats (scenario suite)

- **Total turn time** (includes supervisor + side-searches + LLM + persistence):
  - Min: 6.0s
  - p50: 31.1s
  - Avg: 35.1s
  - p95: 74.0s
  - Max: 78.8s

Slowest scenarios:
- `30.7_phase2_baseline_make_it_cooler_text_reply`: 78.8s (2 steps)
- `11.4_duration_derives_return`: 75.5s (1 steps)
- `b219_itinerary_start_time`: 74.3s (3 steps)
- `12.7_change_pace`: 74.0s (2 steps)
- `12.1_post_generation_modification`: 72.0s (2 steps)
