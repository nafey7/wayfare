---
name: traces
description: Fetch and analyze Langfuse traces from staging/prod. List traces, show details, export data, analyze AI response patterns, list sessions. Use for debugging AI issues, understanding response variability, or investigating user conversations.
allowed-tools: Bash(python3:*), Bash(python:*), Read, Glob
argument-hint: [environment] [command] [filters]
---

# Langfuse Trace Analysis

@tools/langfuse/langfuse_traces.py

Fetch and analyze Langfuse traces from Voya staging/prod. User request: $ARGUMENTS

## Tool Location

```bash
python3 tools/langfuse/langfuse_traces.py [options] <command>
```

## Credential Resolution

Credentials are resolved in order:
1. Environment variables: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`
2. Secrets file: `.local/secrets/langfuse_<env>` (gitignored)

## Commands

### List traces

```bash
# Recent traces (last 24h, staging)
python3 tools/langfuse/langfuse_traces.py list

# Filter by tag
python3 tools/langfuse/langfuse_traces.py list --tag flight-agent --days 7

# Filter by user
python3 tools/langfuse/langfuse_traces.py list --user-id <id> --days 3

# Filter by session
python3 tools/langfuse/langfuse_traces.py list --session-id <id>

# Production
python3 tools/langfuse/langfuse_traces.py --env prod list --days 7 --limit 50
```

### Show trace details

```bash
# Basic trace info + LLM generations
python3 tools/langfuse/langfuse_traces.py show <trace-id>

# Verbose (include chains)
python3 tools/langfuse/langfuse_traces.py show <trace-id> -v
```

### Export traces

```bash
# Export to file
python3 tools/langfuse/langfuse_traces.py export --days 7 -o traces.json

# With full observation data (slower)
python3 tools/langfuse/langfuse_traces.py export --days 7 --include-observations -o traces_full.json

# Export specific tag
python3 tools/langfuse/langfuse_traces.py --env prod export --tag hotel-agent --days 3 -o hotel_traces.json
```

### Analyze response patterns

```bash
# Analyze for E2E test design
python3 tools/langfuse/langfuse_traces.py analyze --days 7

# Analyze specific agent
python3 tools/langfuse/langfuse_traces.py --env prod analyze --tag flight-agent --days 7
```

Shows: latency stats, cost stats, per-agent breakdown, sample conversations, response structure patterns (length, bullets, emoji, questions).

### List sessions

```bash
python3 tools/langfuse/langfuse_traces.py sessions --days 7
python3 tools/langfuse/langfuse_traces.py --env prod sessions --days 3
```

## Argument Parsing Guide

Parse the user's request to determine:

1. **Environment** (default: staging): `staging`, `prod`
2. **Command**: `list`, `show`, `export`, `analyze`, `sessions`
3. **Filters**: `--tag`, `--days`, `--user-id`, `--session-id`, `--limit`

Examples:
```
/traces                              -> list (staging, last 24h)
/traces prod list --days 7           -> list prod traces, 7 days
/traces show abc-123                 -> show trace detail
/traces analyze flight-agent         -> analyze --tag flight-agent
/traces prod sessions                -> sessions on prod
/traces export hotel-agent 7d        -> export --tag hotel-agent --days 7
/traces prod user <id> 3d            -> list --env prod --user-id <id> --days 3
```

## Workflow: Traces -> Chat Scenarios

This tool is part of a feedback loop with the Chat CLI (`/chat`). See `tools/README.md` for the full workflow.

1. **Analyze** traces to understand real user conversation patterns
2. **Design** chat test scenarios based on observed patterns (response types, timing, intents)
3. **Run** scenarios with `/chat` to validate behavior
4. **Investigate** failures by looking up specific traces

Example: After analyzing prod hotel traces and seeing 45s avg / 90s max latency, set `max_time_ms: 90000` in hotel scenario assertions.

## Common Tags

| Tag | Description |
|-----|-------------|
| `flight-agent` | Flight search/booking agent traces |
| `hotel-agent` | Hotel search/booking agent traces |
| `langgraph` | All LangGraph agent executions |
| `intent-recognition` | Intent classification traces |

## Output Format

- `list`: Table with ID, time, tags, latency, cost, user message
- `show`: Full trace detail with user input, AI response, LLM generations, scores
- `export`: JSON file with trace data (optionally including observations)
- `analyze`: Statistical summary with per-agent breakdown and E2E test observations
- `sessions`: Table with session ID, created time, trace count
