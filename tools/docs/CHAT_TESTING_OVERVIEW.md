# Why We Test the Chat (And How)

## The Problem

Voya's AI chat is a black box to most debugging tools. A user types "flights to Barcelona" and either gets results in 8 seconds or stares at a spinner for 60 seconds before a timeout. When things go wrong, the question is always: **where did the time go, and what broke?**

The answer lives in 6 different systems. No single tool shows the full picture:

- The user sees a timeout, but **CloudFlare** shows it was a 504
- The 504 means the **ALB** hit its 60-second idle timeout
- **Langfuse** shows the request took 71 seconds because the AI made 6 LLM calls plus a FlightLogic API search
- **Sentry** caught a silent extraction error during that request
- **CloudWatch** shows CPU was fine, so it wasn't a resource problem
- The **chat response** looked correct to the user on the retry, but was actually missing 2 of 5 flight options

Each tool answers one question. The methodology connects them all.

## Who This Is For

- **Developers** investigating chat bugs or latency issues
- **QA** running structured test sessions before releases
- **Claude Code agents** executing automated or exploratory test sessions
- **Anyone** who needs to understand why a specific chat conversation behaved the way it did

## Two Ways to Test

There are two complementary testing modes. Both use the Chat CLI under the hood.

### Mode 1: Scenario Runner (automated, repeatable)

Pre-defined JSON scenarios with built-in assertions. Run them, get a pass/fail report.

```bash
python3 tools/chat/voya_chat.py --env staging --scenario flight_search_happy_path
```

The scenario sends a fixed sequence of messages and checks each response against assertions: response type, intent, timing, search parameters, result counts. This is good for **regression testing** and **smoke tests**, things that should always work and need to be checked quickly.

Scenarios are deterministic on the input side (same messages every time) but the AI responses vary. The assertions are designed to be flexible enough to handle variation while still catching real bugs.

### Mode 2: Exploratory Testing (intelligent, adaptive)

Claude Code acts as a conversational test agent. It sends a message to Voya, reads the response, evaluates whether it makes sense, and decides what to send next, just like a human tester would, but faster and more systematic.

```
User: "Run an exploratory test session on staging, focus on hotel booking edge cases"

Claude Code:
1. Sends "I need a hotel in Barcelona for next weekend"
2. Reads Voya's response, sees it asks for number of guests
3. Sends "3 adults and a baby" (tests infant handling)
4. Reads response, notices it only collected 3 adults and ignored the infant
5. Flags this as a UX issue
6. Tries a different phrasing: "3 adults 1 infant under 2"
7. Checks if the response now includes the infant
8. Moves on to test date edge cases...
```

This is powerful because Claude Code can:
- **Evaluate semantic correctness** (not just string matching, but "does this response make sense given what I asked?")
- **Adapt to unexpected behavior** (if the bot asks a surprising follow-up question, Claude Code can engage with it)
- **Test multi-turn context retention** (ask for flights, get results, then say "which is cheapest?" and verify the bot remembers the context)
- **Spot UX issues** that no assertion could catch ("the bot asked for my destination twice" or "the response contradicts what it said 2 turns ago")
- **Cross-reference with observability tools** after the conversation (look up the Langfuse trace to see what happened internally, check Sentry for errors)

Both modes feed into the same observability analysis: after testing, check Langfuse traces, Sentry errors, CloudFlare metrics, and CloudWatch logs for the test window.

## The Approach in 30 Seconds

```
1. OBSERVE  →  2. DESIGN  →  3. EXECUTE  →  4. ANALYZE  →  5. CONNECT
 (Langfuse)    (scenarios)    (Chat CLI)     (6 tools)     (correlate)
```

1. **Observe** real user conversations via Langfuse traces to understand actual usage patterns
2. **Design** test messages from those patterns (plus edge cases, regressions, stress tests)
3. **Execute** test conversations against staging or production using the Chat CLI
4. **Analyze** each observability layer independently (Sentry, Langfuse, CloudFlare, CloudWatch logs, CloudWatch metrics)
5. **Connect** findings across layers to get the full story

The cycle repeats: new issues found in step 5 feed back into step 2 as new test cases.

## What We've Built

### Tools

| Tool | What It Does | Location |
|------|-------------|----------|
| **Chat CLI** | Send messages, run scenarios, collect timing | `tools/chat/voya_chat.py` |
| **Langfuse CLI** | Fetch and analyze AI traces | `tools/langfuse/langfuse_traces.py` |
| **Sentry** | Query application errors | MCP integration |
| **CloudFlare** | Traffic analytics, firewall events | `/cloudflare` skill |
| **CloudWatch** | Backend logs, ALB/ECS metrics | `/logs` skill + AWS CLI |

### Test Assets

| Asset | What It Contains | Location |
|-------|-----------------|----------|
| **Scenarios** (10) | Automated multi-step tests with assertions | `tools/chat/scenarios/` |
| **Flight filter prompts** (63) | Cabin class, stops, price, airline, duration tests | `tools/chat/test_prompts/flight_filters.md` |
| **Intent recognition prompts** (82) | Intent classification, sticky sessions, switching | `tools/chat/test_prompts/intent_recognition.md` |

### Output

Test sessions produce two types of reports:

- **UX report**: What the user experienced, categorized by severity (critical/high/medium/low)
- **Observability report**: What happened under the hood, cross-referencing all layers

Reports and detailed test results are saved to `tools/chat/test_reports/` (gitignored, regenerated each session).

## When to Run Tests

| Trigger | Mode | What to Run | Why |
|---------|------|------------|-----|
| **Before a release** | Scenarios | All scenarios on staging | Catch regressions before they reach users |
| **After deploying to production** | Scenarios | Greeting + happy path on prod | Smoke test the deploy |
| **Investigating a bug report** | Exploratory | Reproduce the issue, try variations | Isolate the problem with adaptive follow-ups |
| **After changing AI prompts** | Both | Scenarios for regressions, exploratory for side effects | Prompt changes can have unexpected effects |
| **Weekly health check** | Both | Scenarios + Langfuse analyze + Sentry scan | Catch slow degradation before users notice |
| **Testing a new feature** | Exploratory | Claude Code tests the feature conversationally | More coverage than pre-defined scenarios can provide |

## Quick Start

```bash
# Mode 1: Run a pre-defined scenario
python3 tools/chat/voya_chat.py --env staging --scenario greeting

# Mode 1: Run all scenarios
for f in tools/chat/scenarios/*.json; do
  python3 tools/chat/voya_chat.py --env staging --scenario "$f"
done

# Mode 2: Send an exploratory message (Claude Code interprets the response)
python3 tools/chat/voya_chat.py --env staging -m "flights from Amsterdam to Barcelona next Monday, 1 adult" --json

# Observability: Check what the AI has been doing this week
python3 tools/langfuse/langfuse_traces.py --env prod analyze --days 7
```

## Further Reading

- **[Full Methodology](CHAT_TESTING_METHODOLOGY.md)**: Detailed 5-phase guide with commands, correlation techniques, and tool reference
- **[tools README](../README.md)**: Tool setup, credentials, scenario format, all available scenarios and assertion types
- **[Summarization Latency Analysis](../chat/test_reports/2026-03-13_summarization_latency_analysis.md)**: Example deep-dive showing how the methodology identified a 3.8x performance issue
