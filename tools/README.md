# Tools

**CLI tools for testing, debugging, and observability. Not part of the MyVoya application.**

**New here?** Start with [docs/CHAT_TESTING_OVERVIEW.md](docs/CHAT_TESTING_OVERVIEW.md) for a high-level explanation of why and when to test the chat.

**Full methodology:** See [docs/CHAT_TESTING_METHODOLOGY.md](docs/CHAT_TESTING_METHODOLOGY.md) for the detailed 5-phase testing and observability methodology.

## Chat Testing Workflow

The Langfuse trace tool and Chat CLI work together in a feedback loop: **observe real conversations, understand patterns, build test scenarios, validate behavior.**

### Step 1: Observe real user behavior with Langfuse

Start by analyzing how users actually interact with the chat on staging or production.

```bash
# What are people searching for? How long are responses taking?
python3 tools/langfuse/langfuse_traces.py --env prod analyze --days 7

# Focus on a specific agent (flights, hotels)
python3 tools/langfuse/langfuse_traces.py --env prod analyze --tag hotel-agent --days 7

# Dig into a specific user session to see the full conversation
python3 tools/langfuse/langfuse_traces.py --env prod list --session-id <session-id>
python3 tools/langfuse/langfuse_traces.py --env prod show <trace-id>
```

**What to look for:**
- Common conversation patterns (how users phrase flight/hotel searches)
- Multi-turn flows (do users provide all info at once, or piece by piece?)
- Edge cases that cause errors or slow responses
- Response time outliers (which queries take >30s?)
- Intent switches (user starts with flights, pivots to hotels)

### Step 2: Design test scenarios from real patterns

Turn what you observed into scenario files. The `analyze` command shows response type distribution, latency ranges, and structural patterns that inform your assertions.

```bash
# Example: Langfuse shows hotel searches averaging 45s with max 90s
# -> Set max_time_ms: 90000 for hotel search steps

# Example: Langfuse shows users often say "book a flight" then give details incrementally
# -> Create a multi-step scenario that mirrors this pattern
```

Create a scenario file in `tools/chat/scenarios/`:

```json
{
  "name": "hotel_search_from_traces",
  "description": "Mirrors common hotel search pattern observed in prod Langfuse traces",
  "messages": [
    {
      "send": "I need a hotel in Barcelona",
      "expect_type": "message",
      "max_time_ms": 15000
    },
    {
      "send": "next weekend for 2 adults",
      "expect_type": "hotel_search_results",
      "expect_has_data": true,
      "max_time_ms": 90000
    }
  ]
}
```

### Step 3: Run scenarios against staging/prod

```bash
# Run a single scenario
python3 tools/chat/voya_chat.py --env staging --scenario hotel_search_from_traces

# Run all scenarios
for f in tools/chat/scenarios/*.json; do
  python3 tools/chat/voya_chat.py --env staging --scenario "$f"
done

# Quick manual exploration when you spot something odd
python3 tools/chat/voya_chat.py --env staging -m "I need a hotel in Paris for tonight"
```

### Step 4: Investigate failures

When a scenario fails or a user reports an issue:

```bash
# Check Langfuse for the user's actual conversation
python3 tools/langfuse/langfuse_traces.py --env prod list --user-id <id> --days 3

# Look at the specific trace to see what the AI did
python3 tools/langfuse/langfuse_traces.py --env prod show <trace-id> -v

# Reproduce it with the chat CLI
python3 tools/chat/voya_chat.py --env staging -m "exact message the user sent"

# If it's a regression, add it as a scenario so it doesn't happen again
```

### Putting it all together

```
Langfuse traces (real users)           Chat CLI (testing)
         |                                    |
    analyze patterns ──────────> design scenarios
         |                                    |
    investigate failures <────── run scenarios & find bugs
         |                                    |
    verify fix deployed ──────> re-run scenarios to confirm
```

The pre-built scenarios in `chat/scenarios/` were created from this process. As the chat evolves, keep the cycle going: observe, build scenarios, test, fix, verify.

---

## Contents

### `/chat/` - Voya Chat CLI

Interactive and scripted chat client for testing Voya's AI assistant against any environment.

**Features:**
- Send single or multi-turn messages with timing collection
- Interactive REPL with conversation management
- Run test scenarios with assertions (response type, intent, timing, content)
- JSON output for scripting/CI integration
- Resume conversations by chat_id

**Quick start:**
```bash
# Interactive chat on staging
python3 tools/chat/voya_chat.py --env staging

# Send a message
python3 tools/chat/voya_chat.py -m "search flights from london to paris"

# Run a test scenario
python3 tools/chat/voya_chat.py --scenario greeting

# Multi-turn with timing
python3 tools/chat/voya_chat.py -m "find hotels in Rome" -m "April 10 to 15, 2 adults"
```

**Credentials:** Resolved from CLI args > `VOYA_EMAIL`/`VOYA_PASSWORD` env vars > `.local/secrets/chat_<env>` > defaults (testuser on local/staging).

**Scenarios:** Pre-built test scenarios in `chat/scenarios/`. See [scenario format](#scenario-file-format) below.

### `/langfuse/` - Langfuse Trace Analysis

Fetch and analyze Langfuse traces from staging or production for debugging and E2E test design.

**Features:**
- List, filter, and show traces with full detail
- Export traces to JSON (with optional observation data)
- Analyze AI response patterns per agent (latency, cost, structure)
- List sessions

**Quick start:**
```bash
# List recent traces
python3 tools/langfuse/langfuse_traces.py list

# Show trace detail
python3 tools/langfuse/langfuse_traces.py show <trace-id>

# Analyze response patterns
python3 tools/langfuse/langfuse_traces.py --env prod analyze --tag flight-agent --days 7

# Export traces
python3 tools/langfuse/langfuse_traces.py export --days 7 -o traces.json
```

**Credentials:** Resolved from `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` env vars > `.local/secrets/langfuse_<env>`.

### `/docs/` - Vendor Documentation

FlightLogic API documentation, field definitions, and schema diagrams.

### `/extern/` - External API Specs

Raw API specifications from third-party providers (FlightLogic).

### `/scripts/` - Build Scripts

PowerShell build automation for Windows developers.

## Access & Credential Setup

Several dev tools require external credentials. Each tool resolves credentials from multiple sources (CLI args, env vars, secrets files). See the tool-specific sections below for details.

### AWS (`/logs` skill)

The `/logs` skill reads CloudWatch Logs using the `voya-agent` AWS CLI profile.

**1. Create an IAM user (or role) with the following policy:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ListLogGroups",
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups"
            ],
            "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:*"
        },
        {
            "Sid": "ReadVoyaLogs",
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:GetLogEvents",
                "logs:FilterLogEvents",
                "logs:StartLiveTail",
                "logs:StopLiveTail"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/ecs/*voya*",
                "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/ecs/*voya*:*"
            ]
        }
    ]
}
```

`DescribeLogGroups` needs broad resource access (list operation), while the actual log reading is scoped to Voya log groups only.

**2. Configure the AWS CLI profile:**

```bash
aws configure --profile voya-agent
# AWS Access Key ID: <from IAM>
# AWS Secret Access Key: <from IAM>
# Default region name: us-east-1
# Default output format: json
```

**3. Verify access:**

```bash
AWS_PROFILE=voya-agent aws logs describe-log-groups \
  --log-group-name-prefix /ecs/production-voya \
  --query 'logGroups[].logGroupName' --output text
```

### CloudFlare (`/cloudflare` skill)

The `/cloudflare` skill uses a CloudFlare API token stored in `.local/secrets/cloudflare_token`.

**1. Create an API token at [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens):**

Use "Create Custom Token" with these permissions (read-only):

| Permission | Access | Required for |
|------------|--------|--------------|
| Zone - DNS | Read | Listing DNS records |
| Zone - Page Rules | Read | Listing page rules |
| Zone - Zone Settings | Read | Viewing zone configuration |
| Zone - Analytics | Read | Traffic analytics and firewall events (GraphQL) |

**Zone scope:** Include - Specific zone - `myvoya.ai`

This gives full observability without the ability to change anything. For elevated access (DNS edits, cache purges), create a separate token with additional permissions and store it at `.local/secrets/cloudflare_token_admin`.

**2. Save the token:**

```bash
mkdir -p .local/secrets
echo "your-token-here" > .local/secrets/cloudflare_token
```

The `.local/` directory is gitignored. Never commit tokens.

**3. Verify access:**

```bash
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $(cat .local/secrets/cloudflare_token)" | jq '.result'
```

### Langfuse (`/traces` skill)

Langfuse traces are accessed via API keys from [cloud.langfuse.com](https://cloud.langfuse.com).

**Using secrets files (recommended):**

```bash
cat > .local/secrets/langfuse_staging << 'EOF'
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
EOF

# Repeat for prod if needed:
cat > .local/secrets/langfuse_prod << 'EOF'
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
EOF
```

**Using environment variables:**

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
```

### Chat CLI (`/chat` skill)

The chat CLI authenticates against the Voya API with email/password.

**Using secrets files (recommended):**

```bash
cat > .local/secrets/chat_staging << 'EOF'
EMAIL=you@myvoya.ai
PASSWORD=yourpassword
EOF
```

**Using environment variables:**

```bash
export VOYA_EMAIL=you@example.com
export VOYA_PASSWORD=yourpassword
```

**Defaults:** On local/staging, falls back to `testuser@example.com` / `Test123!`. Production requires explicit credentials.

### Sentry (MCP plugin)

Sentry error monitoring is available via the Claude Code marketplace plugin (`getsentry/sentry-for-claude`). It authenticates through Claude's built-in OAuth flow, not project-level config.

**Setup:**

1. Install the plugin: `/install-plugin sentry` (or accept when prompted)
2. Authenticate when prompted (opens browser for Sentry OAuth)

**Organization:** `voya-ai-inc` (region: `us.sentry.io`)

**Projects:**

| Project | Platform | Covers |
|---------|----------|--------|
| `python-fastapi` | Python | Backend API |
| `javascript-react` | JavaScript | Frontend (main app) |
| `javascript-flight-booker` | JavaScript | Flight booking flow |
| `javascript-hotel-booker` | JavaScript | Hotel booking flow |

**Available operations:** Search issues, get issue details, search events/aggregations, analyze issues with Seer (AI root cause analysis), view traces, manage issue status/assignment. All read-only by default (issue status updates require explicit action).

**Example usage in Claude Code:**
```
"Show me unresolved Sentry issues from the last 24h"
"How many errors in python-fastapi today?"
"Analyze PYTHON-FASTAPI-123 with Seer"
```

No secrets file or API token needed. Credentials are managed by the Claude Code plugin system.

## Claude Code Skills

These tools are available as Claude Code skills:
- `/chat` - Chat with Voya AI (send messages, run scenarios, manage conversations)
- `/traces` - Fetch and analyze Langfuse traces
- `/logs` - Check AWS CloudWatch logs (production, staging)
- `/cloudflare` - DNS, analytics, cache, security for myvoya.ai

## Scenario File Format

Test scenarios are JSON files in `chat/scenarios/`:

```json
{
  "name": "scenario_name",
  "description": "What this scenario tests",
  "messages": [
    {
      "send": "Direct flights from London to New York next week one way 1 adult",
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

**Available assertions:**

| Field | Type | Description |
|-------|------|-------------|
| `expect_type` | string | Response type: `message`, `flight_search_results`, `hotel_search_results`, `itinerary_results`, `error` |
| `expect_intent` | string | Expected intent (from API `intent_name` field, see mapping below) |
| `expect_has_data` | bool | Whether response should contain structured data |
| `expect_contains` | string | Case-insensitive substring match in AI message |
| `expect_search_params` | object | Partial match on `data.search_params` (or `collected_params` mid-conversation). Supports dot notation for nested keys (e.g. `passengers.adults`). Case-insensitive for string values. |
| `expect_min_results` | int | Minimum number of unique flights/hotels across all categories |
| `max_time_ms` | int | Maximum acceptable response time in milliseconds |

**Search params available for flight assertions:**

| Key | Type | Example | Notes |
|-----|------|---------|-------|
| `origin` | string | `"London"` / `"LHR"` | City name or IATA code (depends on query) |
| `destination` | string | `"Barcelona"` / `"BCN"` | City name or IATA code |
| `departure_date` | string | `"2026-04-20"` | ISO format |
| `return_date` | string | `"2026-04-25"` | ISO format, null for one-way |
| `journey_type` | string | `"OneWay"` / `"RoundTrip"` | |
| `passengers.adults` | int | `2` | Dot notation for nested |
| `passengers.children` | int | `0` | |
| `cabin_class` | string | `"Economy"` / `"Business"` | |
| `direct_flight` | int | `1` | 1 = direct only, 0 = any |
| `price_max` | number | `500` | Max price filter |
| `preferred_airline` | string | `"BA"` | IATA airline code |

**Search params available for hotel assertions:**

| Key | Type | Example |
|-----|------|---------|
| `city` | string | `"Paris"` |
| `checkin` | string | `"2026-04-20"` |
| `checkout` | string | `"2026-04-25"` |
| `adults` | int | `2` |
| `rooms` | int | `1` |

**Intent name mapping** (intent recognizer internal name -> API `intent_name` field):

| Internal | API Response (`intent_name`) |
|----------|------------------------------|
| BOOK_FLIGHT | `flight_conversation` |
| BOOK_HOTEL | `hotel_conversation` |
| CREATE_ITINERARY | `create_itinerary` |
| GENERAL_QUERY | `general_query` |

The test prompt libraries use the internal names (for documenting recognizer behavior). Scenario assertions must use the API response names.

**Pre-built scenarios:**

| File | Description | Steps |
|------|-------------|-------|
| `greeting.json` | Basic greeting, expects "voya" in response | 1 |
| `flight_search_happy_path.json` | Complete flight search in 2 messages | 2 |
| `flight_search_incremental.json` | Flight search providing details one at a time | 5 |
| `hotel_search_happy_path.json` | Hotel search in a single message | 1 |
| `intent_switching.json` | Switch from flight to hotel intent mid-conversation | 3 |
| `off_topic.json` | Non-travel queries handled gracefully | 2 |
| `flight_filter_smoke.json` | Combined filter: direct + airline + price in one message | 1 |
| `flight_filter_edge_case.json` | Unrealistic filter, expects graceful "no results" handling | 1 |
| `sticky_session_flight.json` | Sticky intent: flight booking with ambiguous follow-ups | 5 |
| `sticky_session_hotel.json` | Sticky intent: hotel booking with ambiguous follow-ups | 4 |

Results are written to `chat/scenario_results/` (gitignored).

## Test Prompt Libraries

Curated prompt collections for systematic testing, located in `chat/test_prompts/`:

| Library | Prompts | Coverage |
|---------|---------|----------|
| [flight_filters.md](chat/test_prompts/flight_filters.md) | 63 | Cabin class, stops, price, airline, duration, combined filters, edge cases |
| [intent_recognition.md](chat/test_prompts/intent_recognition.md) | 82 | flight_conversation/hotel_conversation/create_itinerary, sticky sessions, intent switching |

These libraries provide structured test messages with expected outcomes. Use them for manual testing, as source material for new scenarios, or as a prompt pool for Claude Code test agents. See [CHAT_TESTING_METHODOLOGY.md](docs/CHAT_TESTING_METHODOLOGY.md) for how they fit into the 5-phase workflow.
