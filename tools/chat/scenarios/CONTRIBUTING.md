# Chat-scenarios — contributing & loosening protocol

This suite is the **regression safety net** for the AI chat flow (issue #1053 P0.1). Every PR that touches `backend_python/app/ai/**`, `backend_python/app/domains/{chat,flight,hotel,airport}/**`, `tools/chat/**`, or `compose.test.yaml` runs all scenarios. A failure blocks the workflow.

## Scenario JSON shape

```json
{
  "name": "11.3_destination_only",
  "description": "Destination only — bot acknowledges and offers next step.",
  "messages": [
    {
      "send": "Plan a trip to Paris",
      "expect_type_in": ["ai_response", "message"],
      "max_time_ms": 30000,
      "expect_contains_any": ["help", "Paris", "trip", "next"],
      "expect_not_contains": ["paste your itinerary"]
    }
  ]
}
```

Assertions supported per step:

- `expect_type` / `expect_type_in` — response `type` field
- `expect_intent` — supervisor classification
- `max_time_ms` — latency guard
- `expect_contains_any` — at least one substring must appear in `ai_message`
- `expect_not_contains` — none of the listed substrings may appear
- `expect_has_suggestions` — boolean
- `expect_search_params` — dict subset match on data.search_params
- `expect_min_results` — minimum number of flights/hotels/days

## Loosening protocol (mandatory)

**Loosening** = relaxing an assertion so a behavior that *would* have failed yesterday *now* passes. Examples:

- Widening `expect_contains_any` (adding more synonyms / shorter substrings).
- Removing items from `expect_not_contains`.
- Raising `max_time_ms`.
- Adding more types to `expect_type_in`.
- Dropping an assertion entirely.

**Rule**: any loosening must be **documented in the scenario's `description` field** with a short justification, **in the same PR that loosens it**.

### Good example

```json
{
  "name": "13.8_locality_not_found",
  "description": "Hotel search with non-existent neighbourhood suggests available ones. NOTE: expect_contains_any temporarily removed — the hotel agent occasionally returns an empty ai_message on contradictory locality+city pairs (Waikiki Beach in Bangkok). Type + latency are still asserted as guard-rails; tracked for follow-up.",
  "messages": [
    {
      "send": "Hotels near Waikiki Beach in Bangkok, ...",
      "expect_type_in": ["hotel_search_results", "hotel_conversation"],
      "max_time_ms": 90000
    }
  ]
}
```

The description explains **what was relaxed**, **why**, and that there's a **follow-up**.

### Bad example

```json
{
  "name": "13.8_locality_not_found",
  "description": "Hotel search with non-existent neighbourhood suggests available ones",
  ...
}
```

If the assertions were loosened but the description still says the bot "suggests available ones", the description is now misleading. Reviewers can't tell what was relaxed.

## Pre-PR checklist for the author

- [ ] My scenario JSON's `description` field accurately describes what the test now verifies.
- [ ] If I loosened any assertion, the description has a `NOTE:` line explaining what + why.
- [ ] The PR description calls out scenario changes ("loosened N assertions because…").
- [ ] I ran the modified scenarios locally (`python tools/chat/voya_chat.py --env test --scenario <path>`) and they pass.

## Reviewer checklist

The chat-scenarios workflow auto-renders a **Scenario JSON changes in this PR** section in the workflow run summary. When reviewing:

1. Open the workflow run → check the **Summary** tab.
2. Scan the per-file diff section for any `expect_*` lines that *shrank*.
3. For each shrunk assertion, confirm the scenario's `description` explains it.
4. If a description was not updated, request changes.

## Recent precedent

PR #1037 (the `#1034` LLM-blind contract) ended up loosening 15 chat-scenario assertions at once. Each was legitimate, but reviewing all 15 in one go costs trust in the suite. This protocol exists so the next big behavior change doesn't repeat that pattern.

## Where scenarios live

```
tools/chat/scenarios/
  01_supervisor/
  02_flight_basic/
  ...
  11_itinerary_basic/
  13_hotel_filters/
  14_itinerary_dates/
  ...
  32_itinerary_regression/   # locked-down baseline — see "Regression suite" below
  debug/                     # ad-hoc / regression-from-bug scenarios
```

Add a new scenario in the directory that matches the behavior it tests (or `debug/` if it's a one-off regression).

## Regression suite (`32_itinerary_regression/`) — never loosen

This folder is the **locked baseline** for the itinerary flow (issue #1053 Phase 0). It contains 12 scenarios across four buckets:

- **Cold-turn** (R1–R3) — canonical "plan an N-day trip to X" shapes
- **Ambiguous** (R4–R6) — vague destinations / vibe-only inputs
- **Amend** (R7–R9) — post-generation modification requests
- **Partial input** (R10–R12) — missing origin / dates / destination

These exist specifically so Phase 2 (prompt softening, vague-destination support, day-targeted regen) can ship as a **known, documented behavior delta** against this baseline — not as a silent regression.

### Rule for this folder

**Loosening a regression scenario requires its own PR**, separate from the behavior change that motivated the loosening. The PR description must:

1. Reference the issue / PR that intentionally changes the underlying behavior
2. Quote the old assertion and the new assertion side-by-side
3. Explain why the previous behavior is no longer the desired baseline
4. Be reviewed and approved by a second engineer before merge

Inline `[TEMP LOOSENED PR#NNNN]` markers (as used in PR #1108 for 18 other scenarios) are **not** acceptable for this folder — they're a triage tool for the rest of the suite, not for the locked baseline.

### Why this matters

PR #1037 loosened 15 scenarios at once; PR #1108 loosened 18. Each was legitimate but reviewing in bulk costs trust. The regression suite is the small, hand-curated subset where we accept the higher process cost in exchange for a stable reference point for the next 6-month optimization arc.
