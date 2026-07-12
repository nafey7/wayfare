# Deferred Chat / Booking Improvements

Tracking issues identified during weekly trace review that are non-critical
and can be addressed in a future cycle. Each entry includes the source trace,
the symptom, the impact, and a sketch of the fix.

---

## 1. Token explosion across booking turns

**Source**: Session `e5cb8c14-81da-4f21-afad-d158a2a00038` (London → Funchal flight booking, 6 turns)

**Symptom**: Conversation history sent to the LLM grows linearly with each
turn. By turn 5–6 the supervisor is sending 18K+ input tokens per request.

| Turn | User input | Input tokens | Cost |
|------|-----------|-------------|------|
| 3 | `1 adult` | 15,111 | $0.0126 |
| 5 | `from stansted` | 18,829 | $0.0144 |
| 6 | `fromluton` | 18,295 | $0.0141 |

**Impact**: A 6-turn booking session burns ~$0.07 in LLM cost. At scale this
is meaningful — and the user perception is poor latency (each turn ~13–18s).

**Likely fix sketch**:
- Cache the latest flight search result by (route, dates, passengers) so
  airport-switching variants re-use the cached search instead of re-running
  the full agent loop.
- Trim conversation history sent to specialist agents when the previous
  result has been superseded (e.g. drop old `search_flights` tool messages
  once a new search is dispatched in the same chat).
- Compress old tool-result messages — replace large flight result payloads
  with a one-line summary after the next user turn.

**Priority**: Medium. Affects unit cost and perceived latency.

---

## 2. Switching origin airport within the same city should not re-run a full search

**Source**: Same session as #1 — user said "from gatwick", then "from
stansted", then "fromluton" in consecutive turns.

**Symptom**: Each `from <airport>` message triggered a full classify →
dispatch → `resolve_airport` → `parse_dates` → `search_flights` cycle, even
though the only thing changing was the origin airport (same destination,
same dates, same passengers).

**Impact**: Each switch costs another 13–18s and 15–19K tokens. The user
experience is sluggish — and the multi-airport comparison they're trying to
do (compare LGW vs STN vs LTN to FNC) should be a first-class feature, not a
side-effect of repeated full searches.

**Likely fix sketch**:
- When the user provides an airport refinement ("from <airport>", "via
  <airport>", "switch to <airport>"), recognize it as an origin-change
  modifier and re-run `search_flights` with the new IATA only. Skip
  classify, skip date parsing, skip role detection.
- Even better: when origin is a multi-airport city (London, NYC, Paris),
  surface all city-airport options in the first result with per-airport
  pricing. Avoids the user having to ask for each one separately.

**Priority**: Medium. Multi-airport cities are a common UX pattern — solving
it properly is a real win.

---

## Notes for triage

- Both items above are about the same booking session, which suggests this
  exact UX path (compare flights from each London airport to a leisure
  destination) is hitting the system's weakest seams at once.
- Neither is a correctness bug — searches return correct data and prices.
  The problem is cost / latency / no caching.
- These should be tackled together since the fixes overlap (a result cache
  helps both).
