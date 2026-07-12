# Chat Testing & Observability Methodology

A systematic approach to understanding, testing, and improving Voya's AI chat using the full observability stack.

**Looking for a shorter overview?** See [CHAT_TESTING_OVERVIEW.md](CHAT_TESTING_OVERVIEW.md) for the high-level why and when.

## The Core Idea

Every chat message flows through multiple systems. By observing at each layer, we build a complete picture: what the user experienced, what the AI decided, what the infrastructure did, and what broke along the way.

```
User types message
    |
    v
CloudFlare ──── traffic volume, status codes, firewall, cache
    |
    v
ALB ──────────── response times, connection counts, timeouts
    |
    v
ECS Container ── CPU, memory, scaling
    |
    v
FastAPI ────────── CloudWatch logs (if routing works), Sentry errors
    |
    v
LangGraph Agent ── Langfuse traces (LLM calls, tool chains, latency breakdown)
    |
    v
External APIs ──── FlightLogic, Google Geocoding, Langfuse prompts
    |
    v
Response to user
```

Each layer answers different questions. The methodology connects them.

## The Five Phases

```
1. OBSERVE          2. DESIGN           3. EXECUTE          4. ANALYZE          5. CONNECT
real user           test cases          chat sessions       each layer          cross-reference
behavior            from patterns       against env         independently       all layers
(Langfuse)          (scenarios)         (Chat CLI)          (5 tools)           (correlate)
    |                   |                   |                   |                   |
    +----> feeds ------>+----> feeds ------>+----> feeds ------>+----> feeds ------>+
                                                                                   |
    <────────────────── new issues and patterns feed back ─────────────────────────+
```

---

## Phase 1: Observe Real User Behavior

**Goal:** Understand how users actually interact with the chat, not how we imagine they do.

**Primary tool:** Langfuse (`tools/langfuse/langfuse_traces.py`)

### What to look for

| Pattern | How to Find It | Why It Matters |
|---------|---------------|----------------|
| Common phrasings | `analyze --days 7` | Users don't say "search flights AMS to BCN", they say "i wanna go to barcelona" |
| Multi-turn patterns | `list --session-id <id>` | Do users give all info at once, or one piece per turn? |
| Intent switches | Filter traces by session, look for agent changes | "actually, find me hotels instead" is common |
| Slow responses | `analyze --tag flight-agent` | Which queries consistently take >30s? |
| Error patterns | `show <trace-id> -v` on failed conversations | What did the AI do just before the error? |
| Conversation length | `sessions` command | How many turns do real conversations take? |

### Example workflow

```bash
# Weekly overview: what agents are being used, how fast are they?
python3 tools/langfuse/langfuse_traces.py analyze --days 7

# Focus on a slow agent
python3 tools/langfuse/langfuse_traces.py analyze --tag hotel-agent --days 7

# Dig into a specific session to see the full user journey
python3 tools/langfuse/langfuse_traces.py list --session-id <id>
python3 tools/langfuse/langfuse_traces.py show <trace-id> -v
```

### What you get

- Distribution of agent types (flight vs hotel vs general vs itinerary)
- Latency ranges per agent (avg, p95, max)
- Cost per conversation
- Common conversation structures (incremental vs all-at-once)
- Edge cases real users hit that you wouldn't think to test

---

## Phase 2: Design Test Cases

**Goal:** Turn observations into reproducible test conversations.

### Categories to cover

Draw from both Langfuse observations and creative edge cases:

**From real user patterns (Langfuse-driven):**
- Happy paths that match the most common conversation patterns
- The exact phrasings users actually use (typos, slang, abbreviations)
- Multi-turn flows at the length real conversations actually reach
- Intent switches you saw in real sessions

**From creative exploration (tester-driven):**
- Edge cases: empty messages, very long messages, IATA codes, DD/MM dates
- Corrections: change destination, dates, passengers mid-conversation
- Ambiguity: "yes", "1", "the cheapest one", "same dates"
- Context retention: "same city", references to previous results
- Informal input: "2 ppl", "next weeek", "barelona"
- Stress: parallel requests, long-haul complex routes, multi-room hotels
- Regression tests: previously fixed bugs (PR #522 "now" parsing, etc.)

### Test prompt libraries

Curated prompt libraries in `tools/chat/test_prompts/` provide structured sets of test messages with expected outcomes. These are the raw material for both ad-hoc testing and scenario creation.

| Library | Prompts | Coverage |
|---------|---------|----------|
| [flight_filters.md](../chat/test_prompts/flight_filters.md) | 63 | Cabin class, stops, price, airline, duration, combined filters, edge cases |
| [intent_recognition.md](../chat/test_prompts/intent_recognition.md) | 82 | flight_conversation/hotel_conversation/create_itinerary classification, sticky sessions, intent switching |

**How to use prompt libraries:**

1. **Manual testing**: Pick prompts from the tables and run them via Chat CLI or the web UI
2. **Agent-driven testing**: When Claude Code runs a test session (Phase 3), it picks from these libraries to construct realistic, varied test messages
3. **Scenario creation**: Convert high-value prompts into scenario JSON files for automated regression testing
4. **Coverage tracking**: Mark pass/fail against each prompt to identify systematic gaps

**Adding new libraries**: When a new feature area needs testing (e.g., hotel filters, booking flows), create a new markdown file in `test_prompts/` following the same table format with prompt, expected outcome, and notes.

### Scenario files vs ad-hoc messages

**Use scenario files** (`tools/chat/scenarios/*.json`) for:
- Repeatable regression tests
- Happy paths that should always work
- Smoke tests before/after deployments
- Multi-turn flows where message order matters (sticky sessions, corrections)

**Use ad-hoc messages** (`-m "message"`) for:
- Exploratory testing, trying new edge cases
- Reproducing specific user issues from Langfuse
- One-off investigations
- Running prompts from the test prompt libraries

**Use test prompt libraries** (`tools/chat/test_prompts/`) for:
- Systematic coverage of a feature area
- Designing new scenarios
- Training new testers on what to look for

### Writing effective test messages

```
BAD:  "search flights from Amsterdam to London on April 20 2026 for 2 adults one way"
      (too clean, gives the AI everything it needs in perfect format)

GOOD: "i need to get to london from amsterdam around april 20ish, me and my wife"
      (realistic: informal, implied passenger count, vague date)

GOOD: "AMS to LHR 20/04 2 pax"
      (realistic: IATA codes, DD/MM European format, abbreviations)
```

---

## Phase 3: Execute Chat Sessions

**Goal:** Run conversations and collect responses, timing, and metadata.

**Primary tool:** Chat CLI (`tools/chat/voya_chat.py`)

There are two testing modes. Use both.

### Mode 1: Scenario Runner (automated, repeatable)

Pre-defined JSON scenarios with assertions. Sends a fixed sequence of messages and checks each response. Good for regression tests, smoke tests, and CI.

```bash
# Run a single scenario
python3 tools/chat/voya_chat.py --env prod --scenario flight_search_happy_path

# Run all scenarios
for f in tools/chat/scenarios/*.json; do
  python3 tools/chat/voya_chat.py --env staging --scenario "$f"
done
```

Scenarios can validate response type, intent, timing, search parameters (did the AI send the right filters?), and result counts (did we actually get flights back?). See the [README](../README.md#scenario-file-format) for all assertion types.

### Mode 2: Exploratory Testing (intelligent, adaptive)

Claude Code acts as a conversational test agent. It sends a message to Voya, reads and interprets the response, then decides what to send next, adapting in real time.

This is more powerful than scenarios because Claude Code can:
- **Evaluate semantic correctness**: not "does the type equal X" but "does this response make sense given what I asked?"
- **Adapt to the conversation**: if Voya asks a surprising follow-up, engage with it instead of failing an assertion
- **Test context retention**: get results, then ask "which is cheapest?" or "same dates but from London instead"
- **Spot UX issues**: "the bot asked for my destination twice", "the response contradicts what it said 2 turns ago", "it ignored my cabin class preference"
- **Validate result quality**: look at the actual flights/hotels returned, not just whether data exists
- **Cross-reference after the conversation**: look up the Langfuse trace, check Sentry for silent errors

**How to run exploratory tests:**

```bash
# Single message, JSON output for parsing
python3 tools/chat/voya_chat.py --env prod -m "flights BCN to Tokyo May 15, 1 adult one way" --json

# Multi-turn conversation
python3 tools/chat/voya_chat.py --env prod \
  -m "I want to fly somewhere warm" \
  -m "how about Barcelona?" \
  -m "from Amsterdam, next week, just me"

# Continue an existing conversation (note chat_id from previous output)
python3 tools/chat/voya_chat.py --env prod --chat-id <id> -m "actually I meant Barcelona"

# Parallel execution (load + route variety)
for route in "AMS to BCN" "LHR to NRT" "CDG to JFK"; do
  python3 tools/chat/voya_chat.py --env prod -m "flights $route May 1, 1 adult one way" --json &
done
wait
```

**What to evaluate in each response (exploratory mode):**
- Did the bot understand the request? Or did it ask for info already provided?
- Are the search params in `data.search_params` correct? (origin, destination, dates, passengers, filters)
- Do the returned flights/hotels make sense? (right route, reasonable prices, correct cabin class)
- Is the response time acceptable for this type of request?
- Did it maintain context from previous turns?

### What to record

For each conversation, note:
- **chat_id** and **message_id** (for Langfuse/Sentry correlation)
- **Response time** per turn
- **Response type** (`message`, `flight_search_results`, `hotel_search_results`, `itinerary_results`, `error`)
- **Intent** recognized
- **Search params sent to tool** (origin, destination, dates, passengers, filters). Verify the AI extracted the right values from the user message.
- **Result quality** (how many flights/hotels returned? Do they match what was requested?)
- **UX observations** (did the bot understand? did it ask unnecessary questions? did it lose context?)

### Validating search correctness (beyond "did results appear?")

The scenario runner supports deep assertions on search parameters and result counts. This catches bugs where the AI misinterprets a filter or silently drops a parameter:

```json
{
  "send": "Direct BA flights under $500, London to New York, next week, 1 adult, one way",
  "expect_type": "flight_search_results",
  "expect_search_params": {
    "journey_type": "OneWay",
    "direct_flight": 1,
    "passengers.adults": 1
  },
  "expect_min_results": 1,
  "max_time_ms": 60000
}
```

**What `expect_search_params` checks:** Partial match on the `data.search_params` object in the API response. This is the actual parameter dict the LangGraph agent passed to the `search_flights` or `search_hotels` tool. It catches: wrong origin/destination, dropped date, incorrect passenger count, ignored cabin class or direct-only filter, missing price cap, etc.

**What `expect_min_results` checks:** Counts unique flights (by `sequence_number`) or hotels (by `hotel_code`) across all categories. Catches empty-result bugs where the search technically "succeeded" but returned nothing.

See [tools/README.md](../README.md#scenario-file-format) for the full assertion reference with all available search param keys.

---

## Phase 4: Analyze Each Observability Layer

After running chat sessions, query each observability tool for the test window. Each reveals different things.

### 4a. Sentry (Application Errors)

**What it shows:** Exceptions, handled errors, logging noise, error frequency and trends.

**Query via MCP:**
```
mcp__sentry__search_events: "errors in production from the last 30 minutes"
mcp__sentry__search_issues: "unresolved issues in production this week"
mcp__sentry__get_issue_details: specific issue deep dive
```

**Key questions:**
- Did any errors fire during our test messages?
- Are there errors on every request (like OTel context detach) vs intermittent?
- Are errors real bugs or logging noise?
- How long has each issue been occurring? (first_seen date)
- How many users are affected?

**Correlation:** Sentry events include `langfuse_trace_id` and `langfuse_message_id` tags, directly linking to Langfuse traces.

### 4b. Langfuse (AI Agent Behavior)

**What it shows:** What the LLM did, which tools it called, how long each step took, token costs.

**Query via CLI:**
```bash
python3 tools/langfuse/langfuse_traces.py list --limit 20
python3 tools/langfuse/langfuse_traces.py show <trace-id> -v
python3 tools/langfuse/langfuse_traces.py analyze --days 1
```

**Key questions:**
- How many LLM calls per request? (more = slower)
- Where is the time spent? (FlightLogic API vs LLM vs summarization)
- Did SummarizationMiddleware trigger? (adds 10-20s in long conversations)
- Which agent handled the request? (flight-agent, hotel-agent, general-agent, supervisor-graph)
- Did any tool calls fail silently?

**Correlation:** Trace IDs appear in Sentry error events. Session IDs match chat_ids from the CLI tool.

### 4c. CloudFlare (Edge/CDN Layer)

**What it shows:** Total traffic, HTTP status codes, firewall events, cache behavior.

**Query via MCP or `/cloudflare` skill:**
```
# Traffic and status codes per minute
# Firewall events (was our test traffic challenged?)
# Cache hit rates
```

**Key questions:**
- How many 504/502 errors occurred? At what times?
- Was any test traffic blocked by the WAF?
- What's the ratio of successful vs failed requests?

**Correlation:** 504 timestamps correlate with slow Langfuse traces and ALB timeout metrics.

### 4d. CloudWatch Logs (Application Logs)

**What it shows:** Backend log output, stack traces, request processing details.

**Query via `/logs` skill or AWS CLI:**
```bash
# Search for errors in the test window
AWS_PROFILE=voya-admin aws logs filter-log-events \
  --log-group-name "/ecs/production-voya-backend" \
  --start-time <epoch_ms> --end-time <epoch_ms> \
  --filter-pattern "ERROR OR Exception OR Traceback"
```

**Key questions:**
- Are there errors not captured by Sentry?
- Which log groups are actually receiving data? (log routing health check)
- Are there slow queries or connection issues visible in logs?

**Caveat:** As of March 2026, 6 of 8 production log groups are empty due to a log routing misconfiguration. Sentry is more reliable for error detection.

### 4e. CloudWatch Metrics (Infrastructure)

**What it shows:** ALB response times, ECS CPU/memory, request counts, active connections.

**Query via AWS CLI:**
```bash
# ALB target response time
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime --statistics Average Maximum ...

# ECS resource usage
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name CPUUtilization --statistics Average Maximum ...
```

**Key questions:**
- What was the average and max response time during the test?
- Did any requests exceed the ALB idle timeout (60s)?
- Was the infrastructure under resource pressure? (CPU, memory)
- How many 5xx errors did the ALB report?

---

## Phase 5: Connect Everything

This is where the real insight comes from. Each tool gives you a piece; connecting them gives you the full story.

### Correlation techniques

**1. UX issue -> Langfuse trace -> root cause**

You observe a UX problem in the chat:
```
User: "actually I meant Barcelona not Paris"
Bot:  504 Gateway Timeout
```

Find the Langfuse trace for that message (by timestamp or message_id):
```
Trace b56f65bd: 71.1s total
  - 6 LLM calls (extra re-processing for destination change)
  - SummarizationMiddleware: 24.1s (3 passes!)
  - FlightLogic re-search: 32.4s
```

Now you know: the 504 happened because the destination change triggered summarization (24s) + a fresh FlightLogic search (32s), totaling 71s which exceeds the 60s ALB timeout.

**2. Sentry error -> chat message -> user impact**

Sentry shows `Failed to extract flight info: Unterminated string` at 10:45:00.

Cross-reference with chat sessions running at that time:
- BCN→NRT search at 10:44:50 (complex long-haul route)
- The search returned results, but were they complete?

Check Langfuse for the trace: the Gemini output was truncated, so 2 of 5 flight options were lost. Users got results, but incomplete ones.

**3. CloudFlare 504 -> ALB timeout -> Langfuse trace duration**

CloudFlare logged a 504 at 10:33.
ALB metrics show a request exceeding 60s at 10:33.
Langfuse shows a hotel-agent trace at 10:33 taking 90s (FlightLogic hotel API: 45s, LLM calls: 30s, summarization: 15s).

The chain: user searched for hotels -> hotel-agent took 90s -> ALB timed out at 60s -> CloudFlare returned 504. The backend completed the work, but the user never saw the result.

**4. Silent error detection**

Compare what the user saw (chat responses) with what Sentry recorded.
The user got flight results and was happy, but Sentry shows `PYTHON-FASTAPI-33` fired during that request.
The extraction partially failed, meaning the user got 3 options instead of 5.
This is invisible to the user but visible through the Sentry/Langfuse combination.

### The connection matrix

| Question | Primary Tool | Supporting Tools |
|----------|-------------|-----------------|
| What did the user experience? | Chat CLI | - |
| What did the AI decide? | Langfuse | - |
| Did any errors occur? | Sentry | CloudWatch logs |
| Where was time spent? | Langfuse | ALB metrics |
| Was it an infrastructure issue? | CloudWatch metrics | CloudFlare |
| Was it an external API issue? | Langfuse (tool chain timing) | Sentry (API error logs) |
| Was the user blocked? | CloudFlare (firewall) | - |
| Is this a new or recurring issue? | Sentry (first_seen, occurrences) | - |
| How many users are affected? | Sentry (users_impacted) | Langfuse (session counts) |
| What exactly broke? | Sentry (stacktrace) | Langfuse (trace detail) |

---

## Running a Complete Test Session

Here's the full workflow end-to-end, as practiced on March 13, 2026:

### 1. Preparation

- Note the current time (for querying observability tools later)
- Decide target environment (staging for safe testing, prod for real-world validation)
- Consider scaling: if testing on prod, ensure enough ECS containers for the load

### 2. Execute chat sessions

Run a mix of:
- Happy paths (greetings, flight search, hotel search)
- Edge cases (typos, DD/MM dates, IATA codes, informal language)
- Multi-turn flows (incremental info, corrections, context retention)
- Regression tests (previously fixed bugs)
- Stress cases (complex routes, parallel requests)

Save chat_ids and message_ids from JSON output for later correlation.

### 3. Immediate Sentry check

Right after running chats (Sentry ingests within seconds):

```
mcp__sentry__search_events: "errors in production from the last 30 minutes"
```

This gives immediate feedback on what errors our messages triggered.

### 4. Langfuse analysis

Wait a few minutes for Langfuse ingestion, then:

```bash
python3 tools/langfuse/langfuse_traces.py list --limit 30
python3 tools/langfuse/langfuse_traces.py analyze --days 1
```

Deep dive on slow or interesting traces.

### 5. Infrastructure check

Query CloudFlare, CloudWatch logs, and CloudWatch metrics for the test window. Look for 504s, 502s, resource pressure, log anomalies.

### 6. Write up findings

Create two reports:
- **UX report** (`test_reports/YYYY-MM-DD_<env>_chat_ux.md`): What the user experienced, categorized by test type, with issues ranked by severity.
- **Observability report** (`test_reports/YYYY-MM-DD_<env>_observability.md`): What happened under the hood, cross-referencing all 5 tools.

### 7. Reproduce and confirm

For each discovered issue, send targeted messages to reproduce, then immediately check Sentry to confirm. This validates that:
- The issue is real (not a one-off)
- You understand the trigger conditions
- You can reproduce it on demand (essential for fixing)

---

## Tool Quick Reference

| Tool | Access | What It Shows | Latency |
|------|--------|--------------|---------|
| Chat CLI | `tools/chat/voya_chat.py` | User-facing behavior | Real-time |
| Langfuse | `tools/langfuse/langfuse_traces.py` | AI agent decisions, LLM calls, timing | ~2-5 min delay |
| Sentry | MCP (`mcp__sentry__*`) | Application errors, stacktraces | ~10 sec delay |
| CloudFlare | MCP or `/cloudflare` skill | Edge traffic, status codes, firewall | ~1-2 min delay |
| CloudWatch Logs | `/logs` skill or AWS CLI | Application log output | ~30 sec delay |
| CloudWatch Metrics | AWS CLI | ALB, ECS resource metrics | ~5 min delay |

---

## Available Scenarios

| Scenario | Steps | What It Tests |
|----------|-------|--------------|
| `greeting` | 1 | Basic greeting, expects "voya" in response |
| `flight_search_happy_path` | 2 | Complete flight search in 2 turns |
| `flight_search_incremental` | 5 | Step-by-step flight search (origin, dest, dates, pax) |
| `hotel_search_happy_path` | 1 | Hotel search single message |
| `intent_switching` | 3 | Flight to hotel switch mid-conversation |
| `off_topic` | 2 | Non-travel queries |
| `flight_filter_smoke` | 1 | Combined filter: direct + airline + price in one message |
| `flight_filter_edge_case` | 1 | Unrealistic filter (30-min flight), expects graceful handling |
| `sticky_session_flight` | 5 | Sticky intent: flight booking with ambiguous follow-ups |
| `sticky_session_hotel` | 4 | Sticky intent: hotel booking with ambiguous follow-ups |

**Run all scenarios** for a quick regression check:
```bash
for s in greeting flight_search_happy_path hotel_search_happy_path intent_switching flight_filter_smoke sticky_session_flight sticky_session_hotel; do
  echo "--- $s ---"
  python3 tools/chat/voya_chat.py --env staging --scenario $s
done
```

---

## Test Prompt Libraries

Reference libraries with curated test messages organized by feature area. Located in `tools/chat/test_prompts/`.

| Library | File | Prompts | Coverage |
|---------|------|---------|----------|
| Flight Filters | [flight_filters.md](../chat/test_prompts/flight_filters.md) | 63 | Cabin class, stops, price, airline, duration, combined, edge cases, smoke tests |
| Intent Recognition | [intent_recognition.md](../chat/test_prompts/intent_recognition.md) | 82 | flight_conversation/hotel_conversation/create_itinerary, sticky sessions, intent switching, negatives |

These libraries are the source material for designing new scenarios and for Claude Code agents to draw from during exploratory test sessions.

---

## Example Reports

Reports from the March 13, 2026 test sessions:

**Session 1** (10:25-11:45 UTC, ~20 conversations):
- [UX Test Report](../chat/test_reports/2026-03-13_prod_chat_ux.md) - 7 UX issues
- [Observability Report](../chat/test_reports/2026-03-13_prod_observability.md) - Full infrastructure analysis

**Session 2** (12:00-12:13 UTC, ~33 conversations via 5 parallel agents):
- [UX Test Report](../chat/test_reports/2026-03-13_prod_chat_ux_session2.md) - 31 UX issues (2 critical, 3 high, 14 medium, 12 low)
- [Observability Report](../chat/test_reports/2026-03-13_prod_observability_session2.md) - Cross-layer correlation with Sentry, Langfuse, CloudFlare, CloudWatch

**Deep Dives**:
- [SummarizationMiddleware Latency Analysis](../chat/test_reports/2026-03-13_summarization_latency_analysis.md) - Controlled A/B experiment proving SummarizationMiddleware overhead, V1 vs V2 comparison, Flash vs Pro model mismatch finding

---

*Methodology developed March 13, 2026 during initial production chat testing sessions.*
*Tools: tools/chat/, tools/langfuse/, Sentry MCP, CloudFlare MCP, AWS CLI*
