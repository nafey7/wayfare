# Weekly Trace Review — Sessions b219ab9d & 3658c692

**Date**: 2026-05-04
**Issue**: #967 — Weekly Trace Review
**Sessions analyzed**: 2 of 12

---

## Session b219ab9d — Itinerary Context Loss & "Paste" UX Failure

### What Happened (Production, April 30 2026)

User generated a London itinerary in **session ac1007ca**, then opened a **new chat session** (b219ab9d) and asked to modify it.

| Turn | User | Voya | Problem |
|------|------|------|---------|
| 1 | "amend my itinerary for London, start at 10 am" | Asks for clarification (what to change?) | User already stated the change |
| 2 | "Yes" | Asks user to say "Start every day at 10 AM" | Making user repeat themselves |
| 3 | "I agreed with you to adjust every day" | "I'll adjust every day to start at 10 AM" | **Promises but never acts** — no tool call |
| 4 | "adjust and show me results" | **"Please paste the current itinerary here"** | Critical failure — asks user to paste AI's own output |
| 5 | "What do you mean paste itinerary? You just create it" | Asks for destination, days, activities | Still can't help |
| 6 | "Forget about it. Create me itinerary for London..." | Successfully generates new itinerary | User gave up and started over |

### Root Cause

The itinerary was generated in a different chat session. Our system correctly had no itinerary in session b219ab9d. However, the agent handled this situation poorly:
- Never told the user clearly that no itinerary exists in this session
- Went in circles for 4 turns instead of being direct
- Asked user to "paste" content — unacceptable for an AI assistant

### Fixes Applied

#### 1. Prompt: MODE 1 "no itinerary" handling (`itinerary_agent.py`)

Added rule to MODE 1: when user references amending/modifying an itinerary but none exists, tell them clearly in ONE message and offer to create a fresh one. Never ask to "paste" anything.

#### 2. Context hint: detect amend-without-itinerary (`supervisor_v2.py`)

Added pre-classification in `_format_context_for_agent()`: when `itinerary_generated=False` and user message contains amend/modify/adjust + itinerary keywords, inject a directive: "NO ITINERARY EXISTS in this session. Tell user clearly, offer to create a fresh one."

#### 3. Prompt: Time preference in modification_notes (`itinerary_agent.py`)

Added rule: scheduling preferences ("start at 10 AM") must be passed in `modification_notes` even on first generation. Previously the agent acknowledged the preference in text but never passed it to the generation tool.

#### 4. Prompt: Time-aware activity descriptions (`itinerary_agent.py`)

Added TIME PREFERENCES rule to `ITINERARY_GENERATION_PROMPT`: when user specifies a start time, include approximate timestamps in activity descriptions (e.g. "**10:00 AM** — Explore the British Museum..."). If no start time mentioned, no times shown.

### Verification

| Scenario | Result | Details |
|----------|--------|---------|
| `b219_amend_no_itinerary` | PASS (3/3) | "I don't have a previous itinerary" in first response, no "paste", creates fresh itinerary |
| `b219_itinerary_start_time` | PASS (3/3) | Generates with 10 AM, acknowledges 11 AM change request |
| `11_itinerary_basic` (8 scenarios) | PASS (8/8) | No regression |
| `12_itinerary_mods` (8 scenarios) | PASS (16/16) | No regression |

---

## Session 3658c692 — Maldives Airport Radius Too Small

### What Happened (Production, April 28 2026)

User searched flights from Chicago to Vaadhoo Island, Maldives. The system offered 5 nearby airports — all tiny domestic airports (Ifuru, Funadhoo, Maafaru, Madivaru, Dharavandhoo). **Malé International Airport (MLE)**, the only airport with international service, was missing from the list.

| Turn | User | Voya | Problem |
|------|------|------|---------|
| 1 | "search flights" | Asks for details | OK |
| 2 | "Chicago" | Sets origin | OK |
| 3 | "Vaadhoo Island, Maldives" | Offers 5 nearby airports (no MLE) | **MLE missing** |
| 4 | "1 June-August round trip 2 passengers" | Picks Ifuru (option 1), searches | "1" interpreted as airport selection |
| 5 | "Ifuru" | No flights found | Expected — no international flights to Ifuru |
| 6 | "Malé" | Treats as new destination, **loses dates and passengers** | Context loss on destination change |
| 7-9 | User provides details again | Still no flights found | User gives up |

### Root Cause

The `no_own_airport` fallback in `airport/service.py` used a **100km radius** with a **limit of 5**. Malé International Airport (MLE) is **159km** from Vaadhoo Island — outside the search radius. For island nations like the Maldives, all international flights go through one main hub which can be far from smaller islands.

### Fixes Applied

#### 1. Increased `no_own_airport` fallback radius (`airport/service.py`)

Changed `radius_km=100, limit=5` → `radius_km=250, limit=10` **only for the `no_own_airport` fallback path**. This does NOT affect normal city disambiguation (e.g. London → LHR/LGW/STN still uses the standard path).

- Vaadhoo Island → MLE now appears at position 9 (159km)
- Utrecht → AMS still appears first (34km), with 7 more options — all reasonable

#### 2. Increased tool-level cap (`airport.py`)

Changed `[:5]` → `[:10]` in the `no_own_airport` branch of `resolve_airport` to match the increased service limit.

### Remaining Issues (Not Fixed)

These are noted for future work but not addressed in this PR:

1. **Context loss on destination change (turns 6-7)**: When user changed destination from Ifuru to Malé, the flight agent lost previously provided dates and passengers. This is the same class of bug as the itinerary context loss — `shared_context` fields need to persist across destination changes within the same agent.

2. **No flights Chicago→Malé**: This may be a FlightLogic API data limitation. The 6-month search range (March–August) took 36.7s and still returned nothing.

### Verification

| Scenario | Result | Details |
|----------|--------|---------|
| `3658_maldives_airport_radius` | PASS (1/1) | "Male International Airport" now in response |
| `05_flight_airports` (6 scenarios) | PASS (6/6) | No regression |

---

## Files Changed

| File | Change |
|------|--------|
| `app/ai/graph/supervisor_v2.py` | Added itinerary summary storage, MODE 2 context injection, "no itinerary" detection for amend requests, auto-chain booking, search-after-origin directive, suggestions strip from chain_responses |
| `app/ai/graph/prompts/itinerary_agent.py` | Added MODE 1 no-itinerary rule, scheduling preferences in modification_notes, TIME PREFERENCES in generation prompt |
| `app/domains/airport/service.py` | Increased `no_own_airport` fallback radius from 100km→250km, limit 5→10 |
| `app/ai/graph/tools/airport.py` | Increased nearby airport display cap from 5→10 |

## Test Scenarios Added

| Scenario | File | Purpose |
|----------|------|---------|
| `b219_amend_no_itinerary` | `debug/b219_amend_no_itinerary.json` | Amend itinerary that doesn't exist → clear message, no "paste" |
| `b219_itinerary_start_time` | `debug/b219_itinerary_start_time.json` | Generate with 10 AM start, then change to 11 AM |
| `3658_maldives_airport_radius` | `debug/3658_maldives_airport_radius.json` | Vaadhoo Island shows MLE in nearby airports |

## Full Regression Results

| Suite | Scenarios | Steps | Result |
|-------|-----------|-------|--------|
| `debug` (new) | 3 | 7 | 3/3 PASS |
| `05_flight_airports` | 6 | 6 | 6/6 PASS |
| `11_itinerary_basic` | 8 | 8 | 8/8 PASS |
| `12_itinerary_mods` | 8 | 16 | 8/8 PASS |
| **Total** | **25** | **37** | **25/25 PASS** |
