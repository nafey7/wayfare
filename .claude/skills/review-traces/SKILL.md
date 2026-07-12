---
name: review-traces
description: Run automated weekly review of production Langfuse traces. Fetches trace data, analyzes sessions for issues, and generates a detailed report.
allowed-tools: Bash(python*), Bash(python3*), Read, Glob, Bash(gh issue create*)
argument-hint: [--days N] [--output path]
---

# Automated Trace Review

## Step 1 — Fetch trace data

```bash
cd tools/langfuse && python trace_review.py --days 7 -o /tmp/traces.json
```

This produces a JSON file with all sessions, conversations, and metrics.

## Step 2 — Read the data

Read `/tmp/traces.json` and understand:
- `summary` — overall stats (traces, sessions, cost, error rate)
- `agent_metrics` — per-agent latency, cost, error counts
- `sessions` — each session with full `conversation` (user messages + AI responses)
  - Only sessions where `reviewed: true` have enough messages to analyze (3+)
  - Sessions with `reviewed: false` (1-2 messages) — note them in the overview but skip deep analysis

## Step 3 — Analyze sessions

For each session where `reviewed: true`, analyze TWO dimensions:

### A) Conversion Analysis (primary business metric)

A **conversion** = user received a meaningful result matching their intent:
- `flight_search_results` — real flight options displayed
- `hotel_search_results` — real hotel options displayed
- `itinerary_results` — real itinerary with actionable items
- **Text itinerary/trip plan** — if the user asked for an itinerary or trip plan and received one, this IS a conversion (the itinerary agent fulfilled their intent)

**NOT a conversion:**
- User asked for flights or hotels but only received a text plan with no actual search results
- "No flights found" responses (search attempted but failed to return results)
- System gathering requirements but never reaching a search

For each session ask: **Did the user see real search results? If not, what blocked it?**

**Conversion blockers:**
- `search_failed_no_recovery` — Search returned nothing, system offered no alternatives (different airports, dates, connecting routes)
- `requirements_loop` — System kept asking for info user couldn't provide, without offering flexible search or inspiration mode
- `text_plan_without_search` — System gave text advice/itinerary but never triggered actual flight/hotel search
- `context_loss` — System forgot user info, forced restart, derailed path to conversion
- `capability_refusal` — System said "I can only do X" instead of breaking task into convertible steps
- `wrong_intent` — System misunderstood user and took wrong action entirely
- `user_abandoned_early` — User left before providing enough info (not a system issue)

### B) Quality Analysis (user experience)

Also check for these experience issues even in sessions that DID convert:

**Context Loss** — System asked for information the user already provided
**No Alternatives Offered** — No flights/hotels found, system only said "try different dates" without suggesting connecting routes, nearby airports, or alternatives
**Capability Gap** — System refused a multi-step task instead of helping step-by-step
**Irrelevant / Incoherent Response** — System responded with something unrelated to user's ask
**Conversation Loop** — User stuck repeating themselves without progress

### What is NOT an issue:
- System asking for genuinely missing required info (dates, passengers, destination) not yet provided — this is the normal path to conversion
- Slightly slow but correct responses that lead to results
- User abandoning after seeing results (post-conversion, not a failure)

### For each session, determine:
- `converted`: yes / no
- `conversion_blocker` (if not converted): one of the blockers above, or `none`
- `severity`: high / medium / low / none
- `root_cause`: context_loss / no_alternatives_offered / capability_gap / irrelevant_response / conversation_dead_end / incoherent_response / none (can overlap with blocker)
- `suggested_fix`: specific actionable engineering change
- Which specific turns had issues and why (with `langfuse_url` for each)

## Step 4 — Write the report

Format as markdown:

```markdown
# Voya AI Weekly Trace Review
**Period**: {period_start} → {period_end} ({days} days)
**Generated**: {date}

## Summary
| Metric | Value |
| --- | --- |
| Total Traces | ... |
| Total Sessions | ... |
| Unique Users | ... |
| API Success Rate | ...% |
| **Conversion Rate** | **X/Y reviewed sessions (Z%)** |
| Total LLM Cost | $... |
| Sessions Reviewed | ... |
| Sessions Converted | ... |
| Sessions with Issues | ... |

## Conversion Funnel
| Stage | Count | Notes |
| --- | ---: | --- |
| Total sessions | ... | |
| Reviewed (3+ msgs) | ... | |
| Converted (saw results) | ... | flight/hotel/itinerary results shown |
| Not converted | ... | |
| → search_failed_no_recovery | ... | searched but no results, no alternatives |
| → requirements_loop | ... | stuck asking for info |
| → text_plan_without_search | ... | gave advice, never searched |
| → context_loss | ... | forgot info, derailed |
| → capability_refusal | ... | refused multi-step task |
| → user_abandoned_early | ... | left before enough info |

## Agent Performance
| Agent | Traces | Success Rate | Errors | p50 Latency | p95 Latency | Max Latency | Cost | Feedback +/- |
| ...   | ...    | ...          | ...    | ...         | ...         | ...         | ...  | ...          |

## Issues Found ({N} sessions)

### High Severity
#### Session `{id[:16]}...` — {user_email} — {trace_count} messages
**Converted**: No — `{conversion_blocker}`
**Root Cause**: {root_cause}
**Summary**: {what user wanted, what blocked conversion, outcome}
**Suggested Fix**: {specific engineering action to improve conversion}

**Problematic Turns:**
| Turn | Trace | User Said | System Did | Issue | Link |
| ...  | ...   | ...       | ...        | ...   | ...  |

[View full session]({session_url})

---

### Medium Severity
...

### No Issues / Converted
(List sessions that successfully showed search results — brief note on what worked)

## All Sessions Overview
| # | Session | User | Messages | Converted | Blocker | Quality Issues | Link |
| ... |

## Top Conversion Improvement Actions
1. {biggest conversion blocker across sessions} — blocked X conversions. {specific fix}
2. ...

## Top Quality Improvement Actions
1. {most common quality issue across sessions} — affects X sessions. {specific fix}
2. ...
```

## Step 5 — Create GitHub Issue (in CI) or save report (local)

**In GitHub Actions (CI):**
```bash
gh issue create \
  --title "Weekly Trace Review — $(date +%Y-%m-%d) (7d)" \
  --label "trace-review,automated" \
  --body "$(cat /tmp/report.md)"
```

**Locally:**
Save to `reports/trace_review_YYYYMMDD_7d.md`
