---
name: chat
description: Chat with Voya AI on local/staging/prod. Send messages, run multi-turn conversations, test scenarios with assertions, collect timing. Use for testing chat flows, debugging AI responses, or running smoke tests.
allowed-tools: Bash(python3:*), Bash(python:*), Read, Glob
argument-hint: [environment] [message or scenario]
---

# Voya Chat CLI

@tools/chat/voya_chat.py

Chat with Voya's AI assistant from the command line. User request: $ARGUMENTS

## Two Testing Modes

### Mode 1: Scenario Runner (automated, repeatable)
Run pre-defined JSON scenarios with assertions. Good for regression tests and smoke tests.

### Mode 2: Exploratory Testing (intelligent, adaptive)
Send messages to Voya, interpret the response, decide what to send next. You (Claude Code) act as a conversational test agent: evaluate whether responses make sense, adapt follow-ups based on what Voya says, and spot UX issues no assertion could catch.

For exploratory testing, use `--json` output and parse the response to decide your next message. You can evaluate:
- Does the response answer the question asked?
- Did the AI remember context from previous turns?
- Are the search params in the response data correct for what was requested?
- Do the returned flights/hotels make sense (right route, reasonable prices)?
- Did the bot ask unnecessary follow-up questions when it had enough info?

## Tool Location

```bash
python3 tools/chat/voya_chat.py [options]
```

## Credential Resolution

Credentials are resolved in order:
1. CLI args: `--email` / `--password`
2. Environment variables: `VOYA_EMAIL`, `VOYA_PASSWORD`
3. Secrets file: `.local/secrets/chat_<env>` (gitignored)
4. Defaults: `testuser@example.com` / `Test123!` (local/staging only)
5. Interactive prompt (prod)

## Common Operations

### Send a single message

```bash
# Staging (default)
python3 tools/chat/voya_chat.py -m "search flights from london to paris"

# Production
python3 tools/chat/voya_chat.py --env prod -m "find hotels in Rome"

# JSON output (machine-readable, best for exploratory testing)
python3 tools/chat/voya_chat.py -m "hello" --json
```

### Multi-turn conversation

```bash
python3 tools/chat/voya_chat.py --env staging \
    -m "search flights" \
    -m "from amsterdam to barcelona" \
    -m "next week, 2 adults"
```

### Resume existing conversation

```bash
python3 tools/chat/voya_chat.py --env staging --chat-id <id> -m "change to 3 adults"
```

### Run a test scenario

```bash
# Run a specific scenario
python3 tools/chat/voya_chat.py --env staging --scenario greeting

# Run with full path
python3 tools/chat/voya_chat.py --env staging --scenario tools/chat/scenarios/flight_search_happy_path.json
```

### Interactive REPL

```bash
python3 tools/chat/voya_chat.py --env staging
```

REPL commands: `/new`, `/history`, `/conversations`, `/clear`, `/info`, `/timing`, `/raw`, `/last`, `/quit`

### Manage conversations

```bash
# List conversations
python3 tools/chat/voya_chat.py --env staging --conversations

# View history
python3 tools/chat/voya_chat.py --env staging --history --chat-id <id>

# Clear a chat
python3 tools/chat/voya_chat.py --env staging --clear --chat-id <id>
```

## Available Scenarios

Scenario files are in `tools/chat/scenarios/`:

| Scenario | Description | Steps |
|----------|-------------|-------|
| `greeting` | Basic greeting, expects "voya" in response | 1 |
| `flight_search_happy_path` | Full flight search with search param validation | 2 |
| `flight_search_incremental` | Flight search step-by-step with param assembly check | 5 |
| `hotel_search_happy_path` | Hotel search with date and adult count validation | 1 |
| `intent_switching` | Switch from flight to hotel, verify hotel params | 3 |
| `off_topic` | Non-travel queries handled gracefully | 2 |
| `flight_filter_smoke` | Combined filter: direct + airline + price | 1 |
| `flight_filter_edge_case` | Unrealistic filter, expects graceful "no results" | 1 |
| `sticky_session_flight` | Sticky intent with flight param validation | 5 |
| `sticky_session_hotel` | Sticky intent with hotel param validation | 4 |

## Scenario File Format

```json
{
  "name": "scenario_name",
  "description": "What this tests",
  "messages": [
    {
      "send": "Direct flights from London to New York next week 1 adult one way",
      "expect_type": "flight_search_results",
      "expect_has_data": true,
      "expect_search_params": {
        "journey_type": "OneWay",
        "direct_flight": 1,
        "passengers.adults": 1
      },
      "expect_min_results": 1,
      "max_time_ms": 60000
    }
  ]
}
```

**Response types:** `message`, `flight_search_results`, `hotel_search_results`, `itinerary_results`, `error`

**Intent names (API response):** `flight_conversation`, `hotel_conversation`, `create_itinerary`, `general_query`

Results are saved to `tools/chat/scenario_results/`.

## Argument Parsing Guide

Parse the user's request to determine:

1. **Environment** (default: staging): `local`, `staging`, `prod`
2. **Mode**: message (`-m`), scenario (`--scenario`), interactive, or management
3. **Message content**: What to send

Examples:
```
/chat hello                          -> -m "hello" on staging
/chat staging search flights to Rome -> --env staging -m "search flights to Rome"
/chat prod -m "hi" -m "hotels"       -> --env prod -m "hi" -m "hotels"
/chat scenario greeting              -> --scenario greeting on staging
/chat scenario flight_search staging -> --env staging --scenario flight_search_happy_path
/chat conversations                  -> --conversations on staging
```

## Workflow: Traces -> Chat Scenarios

This tool is part of a feedback loop with Langfuse traces (`/traces`). See `tools/README.md` for the full workflow.

1. Use `/traces` to analyze real user conversations (patterns, timing, edge cases)
2. Create scenario files based on observed patterns
3. Run scenarios with this tool to validate behavior
4. When scenarios fail, use `/traces` to investigate the root cause

## Output

Each response shows:
- AI message (green)
- Metadata: response type, intent, confidence, timing
- Structured data summary (flights/hotels) if present
- For search results: `data.search_params` shows what filters the AI sent to the search tool
- Session summary with avg/max/total timing
