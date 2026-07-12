# Itinerary Flow — Optimization Analysis

**Date**: 2026-05-15
**Last verified**: 2026-05-21 — Phases 0, 1, 2 shipped + Phase 3 O5/O4 shipped; O2 / O7 / O14 deferred as follow-up tickets
**Branch**: `1053-task-optimize-itinerary-flow-phase-0-eval-harness-phase-1-feplumbing-wins`
**Status**: Implementation log — phases 0–2 + partial 3 landed on branch 1053; this doc tracks done vs deferred
**Scope**: The chat-driven `create_itinerary` flow specifically. Cross-cutting AI optimizations (model right-sizing, prompt caching, streaming, FlightLogic cache, generic parallel tool calls, rule-based pre-classifier) are intentionally **out of scope** — they are already covered in `docs/AI_OPTIMIZATION_PLAN.md`.

---

## Executive summary

The itinerary critical path on a cold "Plan a 5-day trip to Paris next week" turn runs **~36–70 seconds**, dominated by **one** structured-output LLM call (~25–45 s) inside `generate_itinerary`. Another **~5–10 s of serial small-LLM time** is stacked in front of that big call (supervisor classify → `pre_resolve_trip` extraction → itinerary agent's first ReAct turn), all before the heavy generation even starts.

Beyond raw latency, the flow is **restrictive in ways that come from the prompt, not the architecture**. A 228-line itinerary agent prompt (~6,800 tokens) gates aggressively on dates, destinations, travelers, and regeneration requests in a way that forces multi-turn collection even when the user is being decisive.

Several optimizations are itinerary-specific (not covered by the existing cross-cutting plan) and stack cleanly into a **5-phase rollout** (Phase 0 = eval harness, Phases 1–4 = the optimizations). Shipping Phases 1–3 brings *perceived* time-to-first-card from ~30 s to ~6 s and unblocks UX issues. Phase 4 attacks the heavy LLM call directly.

The plan's architectural shape was cross-validated against 2026 multi-agent best practices (see §10): the **pre-resolve / side-search / stitcher** pattern matches Google Research's published trip-planner architecture and Microsoft Research's **PASTE — speculative tool execution**; the two-stage gen proposal (O1) maps to **Skeleton-of-Thought** (Microsoft Research / ICLR 2024).

---

## 1. Latency budget — cold turn walkthrough

User message: **"Plan a 5-day trip to Paris next week"** (no prior `shared_context.trip`).

| # | Step | File:line | ~Latency | Critical path? |
|---|---|---|---|---|
| 1 | Supervisor intent classification (LLM) | `supervisor_v2.py:1507` (calls `_classify_intent_with_llm` ~L1850) | ~1–2 s | ✅ serial |
| 2 | `_route_to_agent` → `pre_resolve_trip` (no `destination_iata + departure_date` yet) | `supervisor_v2.py:2043-2067` | <1 ms | ✅ |
| 3 | `pre_resolve_trip`: extraction LLM (`tool_trip_extraction` → falls back to supervisor model) | `itinerary_trip_extractor.py:99-130` | ~2–3 s | ✅ serial |
| 4 | parse_dates LLM + resolve_airport ×2 (parallel) | `itinerary_trip_extractor.py:226-246` | ~2–3 s | ✅ (bounded by parse_dates) |
| 5 | `dispatch_itinerary`: user prefs fetch (Mongo) | `supervisor_v2.py:2274-2300` | ~50–150 ms | ✅ |
| 6 | **`kick_off_side_searches` — FlightLogic + hotel search (asyncio tasks, hidden behind LLM)** | `itinerary_orchestrator.py:101-150`, dispatched at `supervisor_v2.py:2319` | ~3–6 s wall, **hidden** | bg |
| 7 | Itinerary agent ReAct loop — ≥2 LLM turns: `update_trip_info` call, then `generate_itinerary` call | `itinerary_graph.py:114-133`, invoked at `supervisor_v2.py:2322` | ~7–15 s | ✅ serial |
| 8 | **`generate_itinerary` tool LLM — structured output (5-day schema, ~6,800-token system prompt)** | `tools/itinerary.py:264-311`, model = `tool_itinerary` (`llm_factory.py:65`) | **~25–45 s** | ✅✅ |
| 9 | `enrich_itinerary` — ~30 Google Places photo fetches + travel-bar routes | `tools/itinerary.py:629-631`, `enrichment.py:39-159` | ~1.5–3 s | ✅ |
| 10 | Final agent turn — short confirmation text | inner agent | ~1–2 s | ✅ |
| 11 | `await await_side_searches` (mostly already done) → `stitch_itinerary` → destination geocode | `supervisor_v2.py:2350`, `itinerary_stitcher.py:68`, `:2376` | <500 ms | ✅ |

**Critical-path estimate: ~36–70 s p50/p95.**

### Observations

- Steps **1 + 3 + 4** are *three serial small-LLM calls* burning **~5–8 s** before step 8 even starts. Each does a narrow job; none of them produces user-facing output.
- Step **8** is the single biggest lever — one ~25–45 s structured-output call. Anything that reduces or parallelizes this call dominates ROI.
- Step **6** (side-searches) is well placed: it runs concurrently with steps 7+8 inside the LLM budget. But it could fire **~5 s earlier** — see §4 #5.
- Step **9** (~30 photo fetches) is on the critical path but adds little user value vs. lazy-loading — see §4 #6.

---

## 2. Restrictiveness audit (prompt-driven)

`prompts/itinerary_agent.py` (**now 277 lines** — was 228 on 2026-05-15; rough estimate ~8,300 tokens at current size) is where most of the friction lives. The worst offenders, with quoted lines:

### 2.1 Hard date gate

`itinerary_agent.py:188-192`:

> "**Dates MUST come from parse_dates** — you CANNOT call generate_itinerary until you have YYYY-MM-DD departure_date AND return_date from a parse_dates tool result… generate_itinerary will FAIL without properly parsed dates."

Reinforced by a runtime guard at `tools/itinerary.py:527-542` (`block_dateless_generation`) set whenever the user gave a duration but no anchor (`supervisor_v2.py:2302-2313`).

**Effect**: *"Plan a 4-day trip to Rome"* cannot complete in one turn even when the user clearly wants flexibility. They must answer "when?" before seeing anything.

### 2.2 Ambiguous-date forced confirmation

`itinerary_agent.py:85-97`:

> "If parse_dates returned dates from an ambiguous expression like 'next week' … you MUST send a plain TEXT message asking the user to confirm the inferred dates BEFORE calling generate_itinerary."

Plus `dates.py:843-845` tool-level: *"Do NOT generate the itinerary yet."*

**Effect**: User who said "next week" *meant* "any reasonable next-week dates" — but the flow forces a confirmation turn anyway.

### 2.3 Vague-destination block

`itinerary_agent.py:195-199`:

> "Destination must be a real city name only — never pass vague phrases like 'Mexican beach resort' or 'European city break'…"

Scenario `tools/chat/scenarios/16_itinerary_destinations/16.2_vague_destination.json` expects the bot to suggest one. The prompt elsewhere at `:94-96` allows suggestions, but `:195-199` overrides.

### 2.4 No traveler ask, period

`itinerary_agent.py:193-194`:

> "**Travelers**: Default to 1 adult if not mentioned. NEVER ask for travelers — just use the default."

**Effect**: Family / group discovery is structurally impossible — a 4-adult family always gets a solo plan.

### 2.5 MODE 1 must start with tools

`itinerary_agent.py:154`:

> "Your FIRST action must be calling tools — NEVER respond with text before trying tools."

**Effect**: Removes the option to ask a single clarifying question even when the message is genuinely ambiguous.

### 2.6 Regenerate gate too narrow

`itinerary_agent.py:142-147`:

> "Call generate_itinerary with modification_notes ONLY when the user names a CONCRETE plan change… If it doesn't → respond with text."

**Effect**: "Make it cooler" / "switch it up" → text reply only, no regen. The MODE 2 acknowledgement list at `:128-133` is 11 enumerated phrases.

### 2.7 Block-dateless short-circuit at wrong layer

`tools/itinerary.py:528-542`: even if the LLM tries to fill a sensible default date, the tool hard-rejects with *"Ask ONLY for the departure date — do NOT pick one yourself."*

This duplicates the prompt gate at a code layer where the rejection can't be softened or contextualized.

### 2.8 No client-side routing/distance

`itinerary_agent.py:127`:

> "Route/distance requests → you cannot calculate routes. Ask for a specific city name."

"How far is Versailles from Paris?" → redirect, not answer.

---

## 3. Flexibility gaps (real user requests that don't work well)

| Scenario | Current behavior | Root cause |
|---|---|---|
| One-way trips | Hotel side-search silently skipped → no hotel card | `_HOTEL_REQUIRED` at `itinerary_orchestrator.py:38` requires `return_date`. Comment at `:32-37` already concedes this is a known follow-up. |
| Partial input ("plan 3 days in Tokyo, I'll add origin later") | Works, but flight rail silently dropped | `_FLIGHT_REQUIRED` at `:31` needs origin IATA |
| Open-jaw / multi-city in itinerary context | Not handled | `kick_off_side_searches` is single-pair only |
| Saved-itinerary amend | Regenerates from scratch instead of patching | `process_itinerary_messages` only sees current-dispatch artifact (`itinerary_graph.py:396`) |
| Accessibility / dietary / mobility / budget hints | Never extracted | Only `adults/children/infants/interests` flow into `generate_itinerary` (`tools/itinerary.py:432`) |
| Vague dates ("sometime in summer", "long weekend") | Goes to ambiguous-date confirmation turn | `dates.py:37-43, 715-727` + §2.2 forced confirmation |
| Vague destinations ("somewhere warm", "Europe") | Refuses → asks for a specific city | §2.3 prompt gate |
| Mid-trip "make it cooler" | Text reply, no regen | §2.6 gate |

---

## 4. Itinerary-specific optimization wins

Ordered by ROI / effort. Skipping anything already covered in `AI_OPTIMIZATION_PLAN.md`.

### 🔥 Big swings (latency)

#### O1 — Two-stage generation

Split step 8. Fast model emits **day skeleton** (titles + budget + experiences) in one call (~5 s). Flagship model fills `activities[]` per day in 5 **parallel** calls (~5 s wall). Schema already separated at `tools/itinerary.py:213-217`.

**Impact**: step 8 ~25–45 s → **~10 s p50**.

#### O2 — Skeleton streaming to FE ⏸ DEFERRED 2026-05-21

Emit `itineraryItems` titles + `expandedContent` shells first, then stream activities as they fill in. Pairs perfectly with O1. `ItineraryDetailsComponent.tsx` already separates expansion state — the FE surface is ready.

**Impact**: TTFB ~30 s → **~5–7 s** with progressive reveal.

**Status (2026-05-21)**: ⏸ Deferred. Real scope is **4 coordinated pieces**, not just a backend change:

1. New SSE endpoint `/api/chat/message/stream` in `chat.py` (FastAPI `StreamingResponse` + `text/event-stream`)
2. `chat_service.process_message_streaming()` wrapping `graph.astream(stream_mode=["updates", "messages"])`
3. **Partial-JSON streaming inside `_generate_itinerary_with_llm`** via `llm.with_structured_output(StructuredItineraryResult).astream()` + LangChain `JsonOutputParser` (yields incrementally-complete day arrays)
4. FE EventSource subscriber, new Redux state for "pending" vs "populated" days, partial-render support in `ItineraryDetailsComponent.tsx`

Pieces 1+2 without 3+4 = shelfware (no consumer). Piece 3 without 4 = backend emits the right events but user still sees one chunk. The full UX win lands only when all 4 ship together. Filed as standalone Phase 3 O2 ticket — FE coordination required.

**Transport decision (research, 2026-05-21)**: **SSE wins for our stack**. LangGraph's `astream()` (5 stream modes: values/updates/messages/custom/debug) is async-iterator-shaped → maps cleanly to FastAPI `StreamingResponse` with `media_type="text/event-stream"`. OpenAI Structured Outputs streaming + LangChain `JsonOutputParser` natively yield partial dicts as tokens arrive — exactly what piece 3 needs, no custom JSON parser required. WebSocket would add transport upgrade + sticky-session config + manual reconnection logic without buying anything for our unidirectional shape (chat is fundamentally request/response; only the response side needs streaming). Sources captured during research: LangGraph streaming docs, LangChain partial-JSON discussion #27911, OpenAI Structured Outputs streaming docs, production guides on FastAPI + LangGraph + SSE.

#### O3 — Cache structured itineraries

Cache `generate_itinerary` output keyed by `(destination, duration_days, prefs_fingerprint, season_bucket)`. `saved_itineraries` collection already exists; drop in a read-through cache layer. Even **10% hit rate** saves ~25 s on the hot path.

#### O4 — Regex fast-path for `pre_resolve_trip` ✅ SHIPPED 2026-05-21

`^(plan a |i want a )?\d+[- ]?day(s)? (trip )?(in|to) [A-Z][a-z]+( from [A-Z][a-z]+)?$` covers ~30% of cold-turn shapes. Skip the extraction LLM (`itinerary_trip_extractor.py:99`) entirely on match.

**Status (2026-05-21)**: ✅ Done. `_FAST_PATH_REGEX` in `itinerary_trip_extractor.py` + `_try_fast_path()` helper. On match, returns a `TripParamsExtraction` directly (destination + duration via `"N days"` date expression + optional origin) and `extract_and_resolve()` skips the LLM call. Post-match Title-Case validation prevents the destination chain from consuming connector words ("Tokyo in June" — "in" is lowercase so destination stops at "Tokyo" and the whole regex then fails to anchor at `$`, deferring to LLM) and from matching vague phrases ("somewhere warm" — lowercase 's' fails). 16 unit tests (`TestFastPathRegex` + `TestExtractAndResolveFastPath`) covering canonical shapes, negative cases (extra date info, vague phrasing, multi-city, no duration, no destination), Title-Case validation, region-destination passthrough (gate catches it downstream), and end-to-end "LLM not called on fast-path match".

**Impact**: −2–3 s on covered turns.

#### O5 — Fire side-searches earlier ✅ SHIPPED 2026-05-21

Today: kicked off at `supervisor_v2.py:2319`, after prefs fetch, just before the agent LLM.
Better: fire inside `pre_resolve_trip` the moment IATA + dates resolve (`itinerary_trip_extractor.py:255`).

**Status (2026-05-21)**: ✅ Done. `pre_resolve_trip` now pre-fires the flight + hotel side-searches the moment the merged trip context has IATA + dates, stashes the asyncio tasks in `itinerary_orchestrator._PENDING_SIDE_SEARCHES` keyed by `chat_id`, and `dispatch_itinerary` pops + reuses them (falls back to firing-on-the-spot when nothing was pre-stashed, e.g. cold path where pre_resolve_trip skipped). Non-itinerary dispatchers (`dispatch_flight` / `dispatch_hotel` / `dispatch_general`) call `clear_pending_side_searches` so stale tasks get cancelled if the user pivots mid-turn. 4 unit tests in `TestPreFiredSideSearchesStash` (stash/pop, cancel-on-clear, no-op for unknown chat, overwrite-cancels-previous).

**Impact**: +3–5 s of extra concurrency (side-searches mostly done before the agent LLM even starts).

### 🛠 Plumbing wins

#### O6 — Defer `enrich_itinerary` ✅ SHIPPED 2026-05-21 (refined to "cap at 1s")

Move ~30 Google Places photo lookups + travel-bar routes out of the response critical path into a post-response background task. FE already has empty-imageUrl fallbacks.

**Status (2026-05-21)**: ✅ Done — refined from full-defer to cap-at-1s via `asyncio.wait_for(enrich_itinerary(...), timeout=1.0)`. Full deferral needed FE coordination + new persistence path (out of Phase 1 scope); the 1s cap is the minimal-viable win: fast-network enrichment still lands, slow Google API calls get cancelled. FE handles empty `imageUrl` + empty `travelBars` gracefully (`ConnectorPill` checks `hasConnector` before render). New test `test_enrichment_timeout_does_not_block_response` simulates a 2.5s slow enricher and asserts the tool returns in <2s with `status="success"`.

**Impact**: −1.5 to −3 s on slow-network turns; no change when network is fast.

#### O7 — Drop `update_trip_info` from the ReAct loop ⏸ DEFERRED 2026-05-21

Its outputs are re-extracted from `generate_itinerary` tool args anyway (`itinerary_graph.py:522-579`). The tool exists only for cross-agent context propagation — write straight to `shared_context` after `generate_itinerary` returns.

**Status (2026-05-21)**: ⏸ Deferred. Scope analysis showed the tool does **6 jobs**, not the 1 the original doc claimed: (1) city name normalization with diacritics, (2) inline `parse_dates`, (3) state-aware swap-to-return-date per #1014, (4) auto-derive `return_date` from `departure_date + trip_duration_days`, (5) returns "complete vs missing" signal to the agent, (6) rejects `return_date ≤ departure_date` (also #1014). Cross-agent context propagation is just one of those 6. Removing the ReAct turn cleanly needs all 6 to move elsewhere (`parse_dates` / `generate_itinerary`). Real refactor (~3-4 files + #1014 regression risk) — not a Phase 1 plumbing win. Smallest-viable variant: drop the prompt rule that MANDATES the call when duration is known, and teach `generate_itinerary` to auto-derive `return_date` from `num_days`. Either approach needs its own ticket.

**Impact**: −1 LLM turn (~2–4 s).

#### O8 — Inline `estimate_budget` into the itinerary call ✅ SHIPPED 2026-05-21

`BudgetSnapshot` is already part of `StructuredItineraryResult` (`tools/itinerary.py:213-217`). The standalone tool exists but is *discouraged* by the prompt itself (`itinerary_agent.py:184-185`). Delete it; the structured output already includes budget.

**Status (2026-05-21)**: ✅ Done. Removed the `estimate_budget` smart tool + `EstimateBudgetInput` schema + `BudgetCategory`/`BudgetResult` Pydantic models + `_estimate_budget_with_llm` + `_validate_budget` + `_get_budget_llm` + `_budget_llm` / `_budget_lock` module globals + `get_estimate_budget_tool_prompt` from `prompt_management.py` + the `ESTIMATE_BUDGET_TOOL_PROMPT` Langfuse fallback string + the 2 prompt rules referencing it (`itinerary_agent.py:184-185` + 2 places in `itinerary_graph.py` cross-agent extractor). Tool count limit on the itinerary engine dropped from 12 → 10. Existing `BudgetSnapshot` (used inside `StructuredItineraryResult`) preserved. Tests in `TestEstimateBudgetTool` + `test_validate_budget_*` removed; net −95 LOC of dead-or-discouraged code.

### 🧠 Prompt / behavior softening

#### O9 — Soften the hard date gate ✅ SHIPPED 2026-05-21 (Option B — candidate ranges)

When user provides duration but no anchor, generate with a "placeholder dates" badge instead of refusing. Replace the hard `block_dateless_generation` (`tools/itinerary.py:528`) with a structured flag on the response: `dates_are_placeholder: true` → FE shows a one-click "Pick exact dates" CTA on the day cards.

**This is the single biggest UX unlock**, but it's a product call. See §6 open questions.

**Status (2026-05-21)**: ✅ Done — implemented as **Option B** per product call (suggest 3 candidate date ranges instead of generating with placeholder dates). When the user gives a duration without an anchor date (*"5-day trip to Bali"*), the agent now offers 3 concrete date windows (near / mid / slightly-later) and lets the user pick a number or give their own dates. Pure prompt change — `block_dateless_generation` tool guard stays in place as a backstop. R11 regression scenario updated with `[PHASE 2 BASELINE UPDATE]` marker.

#### O10 — Trim the prompt to ~80–100 lines ✅ SHIPPED 2026-05-21 (177 lines, -36%; target was aspirational)

Push edge-case handling to tool docstrings. Hard targets:
- Drop MODE 2 acknowledgements (11 phrases at `:128-133`)
- Move ARRIVAL/DEPARTURE rules into `generate_itinerary`'s own prompt (that's where they actually apply)
- Move "no paste, no share" hard rule into a trailing system message added only on amend-style turns

**Status (2026-05-21)**: ✅ Done — prompt cut from **278 → 177 lines (-36%)**. Removed dead `ESTIMATE_BUDGET_TOOL_PROMPT`, dropped verbose worked-example pseudocode, collapsed the 11-phrase MODE 2 acknowledgement list into a one-line summary, trimmed the 6-line "🚫 HARD RULE — DO NOT ASK USER TO PASTE" block into a single sentence, consolidated repeated "use existing context / don't re-ask" rules. **Did NOT hit the doc's 80-100 line aspirational target** — getting to 80-100 requires moving rules into tool docstrings (a structural rework), which is its own ticket. 177 lines is the responsible stopping point for this phase.

**Impact**: −5–6K tokens per turn (prompt is now 277 lines vs 80–100 target — gap widened since the original analysis) → faster TTFT, better cache hit potential.

#### O11 — Allow vague destinations with confirmation chip ✅ SHIPPED 2026-05-21 (prompt + tool gate)

Let the model suggest a specific city ("Cancún", "Lisbon") with a one-click confirmation chip rather than refusing. Prompt tweak only.

**Status (2026-05-21)**: ✅ Done. Prompt now instructs the agent to suggest 2-3 specific cities when given a vague phrase (*"For Mexican beach: Cancún 🏖️, Tulum, or Puerto Vallarta — which one?"*). **Backed by a deterministic tool-level gate** (`block_region_destination` in `tools/itinerary.py` — mirrors the existing `block_country_only_origin` pattern from #1105) that refuses `generate_itinerary(destination="Europe")` and similar at the tool layer. The gate has its own `KNOWN_REGIONS` frozenset (35 entries: continents + sub-regions like *the Caribbean, Southeast Asia, Scandinavia*) and 5 unit tests in `TestGenerateItineraryRegionDestinationGate`. Without the gate the prompt rule was non-deterministic — the LLM ignored it ~1/3 of runs and produced nonsense like a "4-day Europe itinerary" (R5/R6 caught this). With the gate, the bug is impossible. Phase 2 O11 prompt also hardened with an explicit forbidden-region list + reference to the tool gate. R4/R5/R6 baseline-updated.

#### O12 — Allow `regenerate day 3` ✅ SHIPPED 2026-05-21

Prompt tweak at `:144`: add day-targeted regens to MODE 2 trigger phrases.

**Status (2026-05-21)**: ✅ Done. The MODE 2 regen-trigger list now includes day-targeted phrases (*"regenerate day 3"*, *"redo day 2 with more food"*, *"change day 4 to focus on shopping"*) AND vibe shifts (*"make it cooler"*, *"switch it up"*, *"more adventurous"*) in addition to the original concrete-change list. R9 + 30.7 regression scenarios baseline-updated.

### 🎁 FE quick wins (no backend work)

#### O13 — Recommended-flights / hotels rails inline below the day plan ✅ SHIPPED

**Status (verified 2026-05-21):** ✅ Done. Shipped in PR #1038 (merged 2026-05-14, one day before this doc was written). `InlineFlightCard.tsx` and `InlineHotelCard.tsx` exist under `frontend-v2/src/features/itinerary/components/` and render inside `ItineraryDetailsComponent.tsx` (~lines 258–270). Data wired via `hydrateItinerarySideSearches.ts:104-167` and applied at `applySuccessfulChatResponse.ts:232-233`.

**Original intent (kept for record):** Backend ships `data.flights[]` / `data.hotels[]`; FE Redux already hydrated; needed an inline rail UI inside the day-plan view to surface 5+ flight / hotel options without leaving the itinerary view.

#### O14 — Lazy-load activity hero images ⏸ DEFERRED 2026-05-21

Pairs with O6. FE fetches `/api/places/image-url` on viewport entry. Removes ~1.5–3 s from cold-turn critical path.

**Status (2026-05-21)**: ⏸ Deferred. Value shrunk after O6 was refined from "full defer" to "cap at 1s" — most fast-network users now get populated `imageUrl` inline; O14's lazy-load only covers the long-tail when the O6 timeout fires. Cost-benefit: ~3–4 hours of FE work (new `ActivityImageWithLazyLoad` component following `HotelImageWithFallback` pattern, `IntersectionObserver`, touch 4 itinerary components, Storybook stories + `play` assertions per Voya conventions). Defer in favor of Phase 4 (bigger latency wins). Alternative tiny version (5 min): add `loading="lazy"` to existing `<img>` tags for browser-native lazy-load — doesn't help with empty `imageUrl` cases though, so most of the value is gated on the proper implementation.

---

## 5. Phased rollout plan

| Phase | Focus | Items | Est. effort | Expected impact | Status |
|---|---|---|---|---|---|
| **Phase 0 — Eval harness** | Lock down baseline behavior + regression-gate every later phase | See §5.0 below | 2–3 days | Catches regressions automatically; unblocks Phase 2's intentional behavior change | ✅ Shipped 2026-05-21 |
| **Phase 1 — FE + plumbing wins** | Surfaces the data we already have; removes wasted LLM turns | ~~O13~~ (✅ shipped PR #1038), ~~O6~~ ✅, ⏸ O7, ~~O8~~ ✅, ⏸ O14 | 2–3 days | ~5–8 s off critical path | ✅ Mostly shipped 2026-05-21 (O6, O8); O7 + O14 deferred |
| **Phase 2 — Prompt / behavior softening** | Less restrictive, more flexible | ~~O9~~ (b) ✅, ~~O10~~ ✅, ~~O11~~ ✅, ~~O12~~ ✅, plus baseline updates | 2–3 days | UX unlock; no latency change | ✅ Shipped 2026-05-21 |
| **Phase 3 — Skeleton streaming + early kick-off** | Drastic TTFB improvement | ~~O5~~ ✅, ~~O4~~ ✅, ⏸ O2 | 4–5 days | TTFB ~30 s → ~6 s **(partial — O2 deferred)** | ⚠️ Backend wins shipped 2026-05-21 (O4, O5); O2 deferred — needs FE coordination |
| **Phase 4 — Two-stage generation + cache** | Attack the heavy LLM call directly | O1, O3 | 1–2 weeks | step 8 ~25 s → ~10 s p50 | ⏸ Not started |

**Compounded outcome if all phases ship**: cold-turn perceived time-to-first-card drops from ~30 s to **~6 s**; full itinerary done in **~15–20 s p50** (vs ~36–70 s today); flow accepts vague/partial inputs gracefully.

### 5.0 Phase 0 — Eval harness (regression safety net)

Phase 2 is *intentional behavior change* — softening the date gate, allowing vague destinations, allowing day-targeted regens. The risk isn't breaking a specific test; it's silently regressing some other behavior we cared about.

Recent precedent: PR #1037 (the `#1034` LLM-blind contract) ended up loosening 15 chat-scenario assertions in one go. Each was legitimate, but reviewing 15-at-once costs trust in the suite. An eval harness wired into CI lets every subsequent phase ship a *delta* against a frozen baseline.

**What it includes**:

1. **Promote the chat-scenarios suite to a hard CI gate** — already runs in CI; today it's effectively warn-only because the suite was loosened to accept new behavior. Lock baselines + require explicit, documented loosening on each change.
2. **Add a small `pytest`-style regression suite** specifically for the itinerary flow:
   - 3 cold-turn shapes ("Plan a 5-day trip to Paris next week" / "Plan 3 days in Tokyo" / "Plan a weekend in Rome")
   - 3 ambiguous shapes ("somewhere warm", "Europe city break", "5 days, somewhere chill")
   - 3 amend shapes ("change day 2 to focus on food", "make it cheaper", "regenerate day 3")
   - 3 partial-input shapes (no origin, no dates, no destination)
   - Assert: response `type`, key data fields, latency under guard threshold
3. **Wire LangSmith offline-eval** on the `generate_itinerary` tool specifically — score outputs on (a) schema validity, (b) day-count match, (c) activity-count-per-day match, (d) reference any concrete details (city name, dates).
4. **Cost-per-turn + tokens-per-turn metric in Langfuse** — minimal, just a custom tag on the dispatch span. Surfaces the ROI of Phase 4 caching when it ships.

**Acceptance criteria for Phase 0**:

- All 12 itinerary regression scenarios pass on `main`
- Chat-scenarios CI is a hard gate (not warn-only)
- A `cost_per_turn_usd` tag visible on every itinerary turn trace in Langfuse

**Progress (as of 2026-05-21, branch `1053-...`):**

- ✅ Chat-scenarios hard CI gate — `chat-scenarios.yml` exits 1 on any failure (line 137–139), auto-surfaces JSON diffs in the step summary, and references `tools/chat/scenarios/CONTRIBUTING.md` for the loosening protocol. Verified via direct read of workflow file.
- ✅ LangSmith offline-eval on `generate_itinerary` — `backend_python/app/ai/evaluation/itinerary_evaluators.py` implements all 4 evaluators (schema validity, day count, activity count per day, concrete details). Tested in `tests/unit_tests/test_ai/test_evaluation/test_itinerary_evaluators.py`.
- ✅ Cost-per-turn Langfuse tag — `TokenUsageCollector` (`cost_tracking.py:74`) wired into `traced_observation` (`tracing.py`); on every turn exit, `tokens_per_turn` and `cost_per_turn_usd` are submitted as Langfuse NUMERIC scores via `client.create_score()`. Failure is best-effort-swallowed so chat responses are never affected. Covered by 15 unit tests in `tests/unit_tests/test_ai/test_graph/test_cost_tracking.py`.
- ✅ 12-scenario itinerary regression suite — `tools/chat/scenarios/32_itinerary_regression/` (R1–R12) covering cold-turn (3), ambiguous (3), amend (3), partial-input (3). Locked-baseline policy in `CONTRIBUTING.md` — loosening requires its own dedicated PR, separate from the behavior change that motivated it. Inline `[TEMP LOOSENED]` markers are not acceptable for this folder.

**Phase 0 is complete.** Subsequent phases ship deltas against this baseline.

**Industry citation**: Anthropic's *Demystifying evals for AI agents* — *"once evals exist, you get baselines and regression tests for free: latency, token usage, cost per task, and error rates can be tracked on a static bank of tasks"*. ([Anthropic](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), [Promptfoo LangGraph guide](https://www.promptfoo.dev/docs/guides/evaluate-langgraph/))

**Items deliberately out of scope for Phase 0** (each gets its own track or is parked):

- *Hallucination guardrails on flight/hotel data* — not needed; the stitcher injects real FlightLogic data into the response, the LLM never generates flight numbers / hotel names.
- *Circuit-breaker / template fallback* — defer until we see real timeout incidents.
- *Cross-session personalization memory* — separate long-term-memory project, not part of this plan.

### 5.1 Phase 1 — FE + plumbing wins (✅ partial, 2026-05-21)

**Shipped this branch:**

- ✅ **O6** — Cap `enrich_itinerary` at 1s (refined from full-defer to wait_for-with-timeout)
- ✅ **O8** — Removed `estimate_budget` tool (-95 LOC of dead code; tool count limit 12→10)

**Deferred — follow-up tickets needed:**

- ⏸ **O7** — Drop `update_trip_info` from ReAct loop. Real refactor (6 jobs to migrate, #1014 regression risk).
- ⏸ **O14** — Lazy-load activity hero images on FE. Value shrunk after O6 refinement; 3-4 hrs FE work for the long-tail case only.

### 5.2 Phase 2 — Prompt softening (✅ shipped 2026-05-21)

**All 4 doc-defined items shipped + a follow-up:**

- ✅ **O9b** — Suggest 3 candidate date ranges (Option B per product call)
- ✅ **O10** — Prompt trimmed 278 → 177 lines (-36%); aspirational 80-100 target needs structural rework (future ticket)
- ✅ **O11** — Vague-destination suggestions + new `block_region_destination` tool gate (deterministic safety net)
- ✅ **O12** — Day-targeted regenerate + vibe shifts
- ✅ **R4/R5/R6/R9/R11/30.7** — regression scenario baseline updates per CONTRIBUTING.md

### 5.3 Phase 3 — Skeleton streaming + early kick-off (⚠️ partial, 2026-05-21)

**Shipped this branch:**

- ✅ **O5** — Fire side-searches earlier (inside `pre_resolve_trip`). Module-level stash + pop + cancel-on-pivot. 4 new orchestrator tests.
- ✅ **O4** — Regex fast-path for `pre_resolve_trip`. Title-Case validation prevents connector-word capture (`"Tokyo in June"` correctly defers to LLM). 16 new extractor tests.

**Deferred — follow-up ticket needed (the big one):**

- ⏸ **O2** — Skeleton streaming SSE. Requires 4 coordinated pieces (backend endpoint, ChatService streaming method, partial-JSON streaming via JsonOutputParser, FE EventSource + Redux partial-day state). Without FE coordination it's shelfware. **Transport decision (research, 2026-05-21): SSE wins for our stack** — LangGraph's `astream()` + FastAPI `StreamingResponse` + OpenAI Structured Outputs partial-JSON is the canonical pattern; WebSocket buys nothing for a unidirectional response shape.

### 5.4 Phase 4 — Two-stage generation + cache (⏸ not started)

- ⏸ **O1** — Two-stage generation (Skeleton-of-Thought pattern). Fast model emits day skeleton in parallel; flagship fills activities per day. Attacks the heavy 25-45s LLM call directly. Pairs with O2 (the skeleton structure is exactly what O2 needs to stream).
- ⏸ **O3** — Cache structured itineraries keyed by `(destination, duration_days, prefs_fingerprint, season_bucket)`. Even 10% hit rate saves ~25s.

---

## 6. Open product / scope questions

Before opening a GitHub issue, a few calls to make:

1. **Phase 1 + Phase 2 as one issue, or split?**
   Suggestion: Phase 1 + Phase 2 together — both are low-risk and need no new infra. Phase 3 and Phase 4 as follow-up issues.

2. **Acceptance criteria style?**
   - Latency-based: p50 / p95 targets per phase
   - Behavior-based: scenario suite passes + manual QA list
   - Mixed (recommended): behavior for Phase 1/2, latency for Phase 3/4

3. **Hard date gate softening (O9) — product call**.
   Generating with placeholder dates is a behavior change. Two options:
   - **(a) Placeholder dates with a "Pick exact dates" CTA on the response** — bot generates immediately; user picks dates later via a chip click; flight/hotel side-searches re-fire with actual dates.
   - **(b) Keep the gate but suggest 3 candidate date ranges** — "I can plan for {June 10-14}, {June 17-21}, or {June 24-28} — pick one or tell me your preferred dates."
   Option (a) is the unlock. Option (b) is safer.

4. **Streaming target for O2 — SSE or WebSocket?**
   This is a cross-cutting decision (chat send/receive plumbing is shared with flight + hotel flows). `AI_OPTIMIZATION_PLAN.md` P0.4 already recommends WebSocket. Aligning is cleaner.

5. **Cache invalidation policy for O3.**
   Trip-level cache is safe (places don't change daily). What invalidates? Prefs change? Suggest: cache TTL of 7 days + invalidate on user prefs save.

---

## 7. Key file:line index

> Line numbers refreshed against current code on 2026-05-21. Items marked *(was X)* moved since the original analysis.

- Supervisor routing: `supervisor_v2.py:2043-2067`
- Pre-resolve detour: `supervisor_v2.py:2608-2658`, `itinerary_trip_extractor.py:107-138` *(was `:99-130`; shifted +8)*
- User prefs fetch: `supervisor_v2.py:2343-2388` *(was `:2274-2300`; shifted +69)*
- Side-search kick-off: `supervisor_v2.py:2406` → `itinerary_orchestrator.py:101-150` *(was `:2319`)*
- Itinerary agent prompt (the long one): `prompts/itinerary_agent.py:69-277` — **now 277 lines (was 228 — got longer, not shorter)**
- Heavy LLM call: `tools/itinerary.py:264-311` (model `tool_itinerary`, `llm_factory.py:65`)
- Block-dateless guard: `tools/itinerary.py:527-542` + `supervisor_v2.py:2377-2388` *(supervisor flag was `:2302-2313`)*
- "Do NOT generate yet" tool message: `dates.py:998, 1018` *(was `:843-845` single message; now split for amend-vs-cold)*
- Enrichment latency tail: `tools/itinerary.py:629-631`, `enrichment.py:39-159`
- Stitcher (pure Python): `itinerary_stitcher.py:68-133`
- FE hydration (rails data ingest): `frontend-v2/src/features/chat/utils/hydrateItinerarySideSearches.ts:104-167`, applied at `applySuccessfulChatResponse.ts:232-233`
- FE itinerary render: `frontend-v2/src/features/itinerary/components/ItineraryDetailsComponent.tsx` — renders `InlineFlightCard` / `InlineHotelCard` at lines ~258–270 ✅ *(rails shipped in PR #1038 on 2026-05-14)*

---

## 8. Out of scope (covered elsewhere)

The following recommendations from `docs/AI_OPTIMIZATION_PLAN.md` also benefit the itinerary flow and should be tracked separately:

- **P0.1** Model right-sizing (supervisor / general / dates → `gpt-5.4-nano`)
- **P0.2** Rule-based pre-classifier in supervisor
- **P0.3** Prompt ordering for OpenAI auto-caching
- **P0.4** WebSocket streaming
- **P1.1** Two-level FlightLogic result cache
- **P1.2** Parallel flight + hotel inside itinerary (this is partially done via the #1038 side-search orchestrator; can still be deepened)
- **P1.3** Local date parser fallback (would also kill the §2.2 ambiguous-date forced confirmation turn)

If these P0/P1 items ship alongside Phases 1–4, **compounded cold-turn latency could approach ~10–12 s p50** with the same flexibility gains.

---

## 9. Industry validation (cross-checked vs. 2026 best practices)

This plan was cross-validated against published 2026 sources. Headline: the three biggest architectural bets are each backed by named, peer-reviewed patterns from major labs.

| Voya pattern | Industry name | Verdict | Source |
|---|---|---|---|
| **Pre-resolve trip** (extract IATA/dates before LLM) | "Deterministic-first / hybrid LLM-plus-optimization" | ✅ Standard | [Google Research — Optimizing LLM-based trip planning](https://research.google/blog/optimizing-llm-based-trip-planning/) |
| **Side-search orchestrator** (`asyncio.create_task` during LLM thinking) | **PASTE — speculative tool execution** | ✅ Standard | [Microsoft Research / arXiv 2603.18897](https://arxiv.org/abs/2603.18897) — reports 48.5 % task-completion-time reduction |
| **Two-stage generation** (O1) | **Skeleton-of-Thought** (ICLR 2024) | ✅ Standard | [Microsoft Research / Tsinghua](https://www.microsoft.com/en-us/research/blog/skeleton-of-thought-parallel-decoding-speeds-up-and-improves-llm-output/), [arXiv 2307.15337](https://arxiv.org/abs/2307.15337) — up to 2.39× speedup on black-box APIs |
| **Pure-Python stitcher** | "LLM suggests + optimizer finalizes" | ✅ Standard | [Google Research](https://research.google/blog/optimizing-llm-based-trip-planning/) — matches Gemini trip planner exactly |
| **Progressive disclosure on ambiguous inputs (O9, O11)** | **LFAG — Listing Formal Answers with Guidable Disambiguation** | ⚠️ Emerging | [ACL Anthology 2025](https://aclanthology.org/2025.emnlp-main.482/) |
| **Day-targeted regen (O12)** | RFC 6902 JSON-patch for LLM outputs | ⚠️ Emerging | [JSON Whisperer — arXiv 2510.04717](https://arxiv.org/html/2510.04717v1) — 31 % token savings vs full regen |
| **Domain-keyed result cache (O3)** | Semantic / domain-keyed cache | ✅ Standard | [Maxim AI](https://www.getmaxim.ai/articles/how-to-optimize-llm-cost-and-latency-with-semantic-caching/), [ScyllaDB](https://www.scylladb.com/2025/11/24/cut-llm-costs-and-latency-with-scylladb-semantic-caching/) |
| **Tool consolidation (O7, O8)** | "Redundant tool calls" anti-pattern fix | ✅ Standard | [Agent anti-patterns part 2](https://achan2013.medium.com/ai-agent-anti-patterns-part-2-tooling-observability-and-scale-traps-in-enterprise-agents-42a451ea84ec), [AWO meta-tools — arXiv 2601.22037](https://arxiv.org/html/2601.22037v2) |
| **Partial JSON streaming (O2)** | OpenAI Structured Outputs streaming | ✅ Standard | [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs) |

**Travel-industry case studies** confirm the phasing shape (FE + plumbing first, engine work in parallel):

- **Google Gemini trip planner** — hybrid LLM + DP/local-search optimizer. Closest published analog to Voya's pre-resolve + stitcher.
- **Booking.com AI Trip Planner** (OpenAI case study) — 10-week rollout, two parallel workstreams ("Experience" + "Engine"). ([OpenAI](https://openai.com/index/booking-com/), [Booking Product](https://medium.com/booking-product/8-weeks-to-innovation-lessons-from-building-booking-coms-ai-trip-planner-94adbf138748))
- **Kayak AI Mode** (Oct 2025), **Expedia Trip Matching** (June 2025) — both shipped agentic flows; no public latency targets, but our target after Phase 3 (~6 s perceived TTFB, ~15–20 s p50 full) would be competitive.

**Deliberately deferred** (each has its own track or is parked):

- *Hallucination guardrails on flight/hotel data* — non-issue; FlightLogic data is injected by the stitcher, the LLM never generates flight numbers / hotel names.
- *Circuit-breaker / template fallback* — defer until we see real timeout incidents.
- *Cross-session personalization memory* (Mem0-style) — separate long-term-memory project.

---

## 10. Follow-up tickets — what's still on the table (2026-05-21 snapshot)

| ID | What | Phase | Status | Estimated effort | Why deferred |
|---|---|---|---|---|---|
| **O7** | Drop `update_trip_info` from ReAct loop — migrate its 6 jobs (state-aware date swap #1014, city normalization, auto-derive return, completion signal, etc.) to `parse_dates` / `generate_itinerary` | Phase 1 | ⏸ Deferred | ~3–4 days + #1014 regression coverage | Real refactor, not the "1 LLM turn deletion" the doc claimed. 6 jobs to migrate. |
| **O14** | Lazy-load activity hero images on FE — `IntersectionObserver` + `useLazyGetPlaceImageUrlQuery` mirroring `HotelImageWithFallback` pattern | Phase 1 | ⏸ Deferred | ~3–4 hrs FE | Value shrunk after O6 was refined to "cap at 1s" — only helps the long-tail slow-network case |
| **O10 part 2** | Trim itinerary prompt from 177 → 80–100 lines (the doc's original aspirational target) — requires moving rules into tool docstrings (structural rework) | Phase 2 | ⏸ Deferred | ~1 day | Got -36% in this branch; rest needs proper rule-migration plan |
| **O2** | Skeleton streaming SSE — 4 coordinated pieces (backend endpoint, ChatService streaming method, partial-JSON via `JsonOutputParser`, FE EventSource + Redux pending-day state). Transport: SSE (see §5.3 research) | Phase 3 | ⏸ Deferred | ~2–3 days + FE coord | The biggest single win in the whole plan — but needs full FE coordination to land usefully |
| **O1** | Two-stage generation (Skeleton-of-Thought). Fast model emits day skeleton; flagship fills activities per-day in parallel | Phase 4 | ⏸ Not started | ~1–2 weeks | Attacks the heavy 25–45 s LLM call directly. Pairs with O2 — the skeleton structure is exactly what O2 streams |
| **O3** | Cache structured itineraries by `(destination, duration_days, prefs_fingerprint, season_bucket)`. Use `saved_itineraries` collection as cache backing | Phase 4 | ⏸ Not started | ~3–5 days | Even 10% hit rate saves ~25 s on the hot path |

### Compounded outcome IF all follow-ups ship

| Metric | Today (post O5+O4) | After O2 | After O1 | After O3 (10% hit) |
|---|---|---|---|---|
| Cold-turn perceived TTFB | ~25–30 s | **~6–8 s** | ~6–8 s (already streamed) | ~6–8 s |
| Full itinerary done (p50) | ~30–40 s | ~30–40 s | **~15–20 s** | ~5 s on cache hit |
| Cache-miss case dominant cost | `generate_itinerary` LLM (~25–45 s) | streams progressively | drops to ~10 s p50 | unchanged |

### Recommended sequencing for the next 4 weeks

1. **Week 1**: O2 backend (pieces 1+2+3 of the 4-piece breakdown above) — establishes the SSE contract
2. **Week 2**: O2 FE (piece 4) — partial-day rendering + EventSource subscriber + Redux pending state. Net: skeleton streaming UX live.
3. **Week 3**: O1 — two-stage generation. Big win, but requires the streaming surface from O2 to land first.
4. **Week 4**: O3 — itinerary cache. Cheap & high-leverage once O1 is in.

O7 and O14 sit on their own tracks — they're optional polish, not blockers.
