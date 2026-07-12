#!/usr/bin/env python3
"""Langfuse Trace Fetcher for Voya.

Fetches and analyzes Langfuse traces from staging or production.
Useful for understanding AI response variability for E2E test design.

Usage:
    # List recent traces (default: last 24h, limit 20)
    python langfuse_traces.py list

    # List traces with filters
    python langfuse_traces.py list --tag flight-agent --limit 50
    python langfuse_traces.py list --tag hotel-agent --days 7
    python langfuse_traces.py list --session-id <session-id>

    # Show full trace detail (with observations/generations)
    python langfuse_traces.py show <trace-id>

    # Export traces to JSON for analysis
    python langfuse_traces.py export --tag flight-agent --days 7 --output traces.json

    # Analyze AI response patterns (for E2E test design)
    python langfuse_traces.py analyze --tag flight-agent --days 7

    # Use production environment (default: staging)
    python langfuse_traces.py list --env prod

Credentials are resolved in order:
    1. Environment variables: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
    2. Secrets file: .local/secrets/langfuse_<env> (gitignored, for personal use)
"""

import argparse
import json
import os
import sys
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SECRETS_DIR = PROJECT_ROOT / ".local" / "secrets"


def load_env(env: str) -> dict:
    """Load Langfuse credentials from env vars or .local/secrets/langfuse_<env>."""
    # 1. Environment variables (works for CI and other developers)
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        return {
            "LANGFUSE_PUBLIC_KEY": os.environ["LANGFUSE_PUBLIC_KEY"],
            "LANGFUSE_SECRET_KEY": os.environ["LANGFUSE_SECRET_KEY"],
            "LANGFUSE_BASE_URL": os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
        }

    # 2. Secrets file (.local/secrets/langfuse_<env>)
    secrets_file = SECRETS_DIR / f"langfuse_{env}"
    if secrets_file.exists():
        config = {}
        for line in secrets_file.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()

        required = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
        missing = [k for k in required if k not in config]
        if missing:
            print(f"Error: {', '.join(missing)} not found in {secrets_file}", file=sys.stderr)
            sys.exit(1)

        config.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
        return config

    print(f"Error: No Langfuse credentials found for '{env}'.", file=sys.stderr)
    print(f"Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables,", file=sys.stderr)
    print(f"or create {secrets_file} with those values.", file=sys.stderr)
    sys.exit(1)


def api_request(config: dict, endpoint: str, params: dict | None = None) -> dict:
    """Make authenticated GET request to Langfuse API."""
    base_url = config["LANGFUSE_BASE_URL"].rstrip("/")
    url = f"{base_url}/api/public/{endpoint}"
    if params:
        # Filter out None values
        filtered = {k: v for k, v in params.items() if v is not None}
        if filtered:
            url += "?" + urlencode(filtered)

    credentials = f"{config['LANGFUSE_PUBLIC_KEY']}:{config['LANGFUSE_SECRET_KEY']}"
    auth = b64encode(credentials.encode()).decode()

    req = Request(url, headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    })

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"API Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def fetch_all_traces(config: dict, params: dict, max_pages: int = 10) -> list:
    """Fetch traces with pagination."""
    all_traces = []
    page = 1
    limit = params.get("limit", 50)

    while page <= max_pages:
        params["page"] = page
        params["limit"] = min(limit - len(all_traces), 100) if limit else 100
        if params["limit"] <= 0:
            break

        result = api_request(config, "traces", params)
        traces = result.get("data", [])
        if not traces:
            break

        all_traces.extend(traces)
        meta = result.get("meta", {})
        if page >= meta.get("totalPages", 1):
            break
        if limit and len(all_traces) >= limit:
            break

        page += 1

    return all_traces[:limit] if limit else all_traces


def fetch_observations(config: dict, trace_id: str) -> list:
    """Fetch all observations for a trace."""
    all_obs = []
    page = 1
    while True:
        result = api_request(config, "observations", {
            "traceId": trace_id,
            "page": page,
            "limit": 100,
        })
        obs = result.get("data", [])
        if not obs:
            break
        all_obs.extend(obs)
        meta = result.get("meta", {})
        if page >= meta.get("totalPages", 1):
            break
        page += 1
    return all_obs


# -- Formatting helpers -------------------------------------------------------

def format_timestamp(ts: str | None) -> str:
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return ts


def format_latency(latency: float | None) -> str:
    if latency is None:
        return "N/A"
    if latency < 1:
        return f"{latency * 1000:.0f}ms"
    return f"{latency:.1f}s"


def format_cost(cost: float | None) -> str:
    if cost is None or cost == 0:
        return "-"
    return f"${cost:.4f}"


def truncate(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def extract_user_message(trace: dict) -> str:
    """Extract the user's input message from a trace."""
    inp = trace.get("input", {})
    if isinstance(inp, dict):
        messages = inp.get("messages", [])
        for msg in messages:
            if msg.get("type") == "human":
                return msg.get("content", "")
    return str(inp)[:200] if inp else ""


def extract_ai_response(trace: dict) -> str:
    """Extract the AI's output message from a trace."""
    out = trace.get("output", {})
    if isinstance(out, dict):
        messages = out.get("messages", [])
        # Get the last AI message
        for msg in reversed(messages):
            if msg.get("type") == "ai":
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Content can be a list of parts
                    texts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            texts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            texts.append(part)
                    return " ".join(texts)
                return content
    return str(out)[:200] if out else ""


# -- Commands ------------------------------------------------------------------

def cmd_list(args, config):
    """List traces with optional filters."""
    params = {"limit": args.limit}

    if args.tag:
        params["tags"] = args.tag
    if args.user_id:
        params["userId"] = args.user_id
    if args.session_id:
        params["sessionId"] = args.session_id

    if args.days:
        from_time = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["fromTimestamp"] = from_time.isoformat()

    traces = fetch_all_traces(config, params)

    if not traces:
        print("No traces found.")
        return

    # Header
    print(f"\n{'ID':<36} {'Time':<22} {'Tags':<28} {'Latency':>8} {'Cost':>8}  {'User Message'}")
    print("-" * 140)

    for t in traces:
        tags = ", ".join(t.get("tags", []))
        user_msg = truncate(extract_user_message(t), 40)
        print(
            f"{t['id']:<36} "
            f"{format_timestamp(t.get('timestamp')):<22} "
            f"{truncate(tags, 26):<28} "
            f"{format_latency(t.get('latency')):>8} "
            f"{format_cost(t.get('totalCost')):>8}  "
            f"{user_msg}"
        )

    print(f"\nTotal: {len(traces)} traces")


def cmd_show(args, config):
    """Show detailed trace information."""
    trace = api_request(config, f"traces/{args.trace_id}")

    print(f"\n{'='*80}")
    print(f"Trace: {trace['id']}")
    print(f"{'='*80}")
    print(f"Time:      {format_timestamp(trace.get('timestamp'))}")
    print(f"Tags:      {', '.join(trace.get('tags', []))}")
    print(f"Session:   {trace.get('sessionId', 'N/A')}")
    print(f"User ID:   {trace.get('userId', 'N/A')}")
    print(f"Latency:   {format_latency(trace.get('latency'))}")
    print(f"Cost:      {format_cost(trace.get('totalCost'))}")
    print(f"Langfuse:  {config['LANGFUSE_BASE_URL']}/trace/{trace['id']}")

    # Input
    print(f"\n--- User Input ---")
    user_msg = extract_user_message(trace)
    print(user_msg or "(empty)")

    # Output
    print(f"\n--- AI Response ---")
    ai_resp = extract_ai_response(trace)
    print(ai_resp[:2000] if ai_resp else "(empty)")

    # Observations (generations only by default, all with --verbose)
    observations = fetch_observations(config, args.trace_id)
    generations = [o for o in observations if o.get("type") == "GENERATION"]

    if generations:
        print(f"\n--- LLM Generations ({len(generations)}) ---")
        for g in generations:
            print(f"\n  Model: {g.get('model', 'N/A')}")
            print(f"  Latency: {format_latency(g.get('latency'))}")
            usage = g.get("usage", {})
            print(f"  Tokens: {usage.get('input', 0)} in / {usage.get('output', 0)} out")
            print(f"  Cost: {format_cost(g.get('calculatedTotalCost'))}")
            if g.get("promptName"):
                print(f"  Prompt: {g['promptName']} v{g.get('promptVersion', '?')}")

    if args.verbose:
        chains = [o for o in observations if o.get("type") == "CHAIN"]
        if chains:
            print(f"\n--- Chains ({len(chains)}) ---")
            for c in chains:
                print(f"  {c.get('name', 'unnamed')}: {format_latency(c.get('latency'))}")

    # Scores
    scores = trace.get("scores", [])
    if scores:
        print(f"\n--- Scores ---")
        for s in scores:
            print(f"  {s.get('name', 'unnamed')}: {s.get('value')} ({s.get('comment', '')})")


def cmd_export(args, config):
    """Export traces to JSON."""
    params = {"limit": args.limit}

    if args.tag:
        params["tags"] = args.tag
    if args.days:
        from_time = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["fromTimestamp"] = from_time.isoformat()

    traces = fetch_all_traces(config, params)

    if args.include_observations:
        for i, trace in enumerate(traces):
            print(f"\rFetching observations... {i+1}/{len(traces)}", end="", file=sys.stderr)
            trace["_observations"] = fetch_observations(config, trace["id"])
        print(file=sys.stderr)

    output = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "environment": args.env,
        "filters": {
            "tag": args.tag,
            "days": args.days,
            "limit": args.limit,
        },
        "count": len(traces),
        "traces": traces,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output, indent=2, default=str))
        print(f"Exported {len(traces)} traces to {args.output}")
    else:
        print(json.dumps(output, indent=2, default=str))


def cmd_analyze(args, config):
    """Analyze AI response patterns for E2E test design.

    Groups traces by user input similarity and shows response variability.
    """
    params = {"limit": args.limit}

    if args.tag:
        params["tags"] = args.tag
    if args.days:
        from_time = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["fromTimestamp"] = from_time.isoformat()

    print(f"Fetching traces...", file=sys.stderr)
    traces = fetch_all_traces(config, params)

    if not traces:
        print("No traces found.")
        return

    # Group by tag
    by_tag = {}
    for t in traces:
        for tag in t.get("tags", []):
            if tag != "langgraph":
                by_tag.setdefault(tag, []).append(t)

    print(f"\n{'='*80}")
    print(f"AI Response Analysis ({len(traces)} traces, last {args.days} days)")
    print(f"{'='*80}")

    # Overall stats
    latencies = [t["latency"] for t in traces if t.get("latency")]
    costs = [t["totalCost"] for t in traces if t.get("totalCost")]

    if latencies:
        print(f"\nLatency:  min={min(latencies):.1f}s  avg={sum(latencies)/len(latencies):.1f}s  max={max(latencies):.1f}s")
    if costs:
        print(f"Cost:     min=${min(costs):.4f}  avg=${sum(costs)/len(costs):.4f}  max=${max(costs):.4f}")

    # Per-agent analysis
    for tag, tag_traces in sorted(by_tag.items()):
        print(f"\n--- {tag} ({len(tag_traces)} traces) ---")

        tag_latencies = [t["latency"] for t in tag_traces if t.get("latency")]
        if tag_latencies:
            print(f"  Latency: avg={sum(tag_latencies)/len(tag_latencies):.1f}s  max={max(tag_latencies):.1f}s")

        # Show input/output pairs
        print(f"\n  Sample conversations:")
        for t in tag_traces[:5]:
            user_msg = truncate(extract_user_message(t), 60)
            ai_resp = truncate(extract_ai_response(t), 80)
            print(f"    User: {user_msg}")
            print(f"    AI:   {ai_resp}")
            print(f"    (latency: {format_latency(t.get('latency'))}, cost: {format_cost(t.get('totalCost'))})")
            print()

    # Response structure patterns (for E2E assertions)
    print(f"\n{'='*80}")
    print("E2E Test Observations")
    print(f"{'='*80}")
    print()
    print("Response patterns to assert on (structural, not content):")
    for tag, tag_traces in sorted(by_tag.items()):
        responses = [extract_ai_response(t) for t in tag_traces if extract_ai_response(t)]
        if not responses:
            continue
        avg_len = sum(len(r) for r in responses) / len(responses)
        min_len = min(len(r) for r in responses)
        max_len = max(len(r) for r in responses)
        print(f"  {tag}:")
        print(f"    Response length: min={min_len} avg={avg_len:.0f} max={max_len} chars")

        # Check for common structural patterns
        has_bullet = sum(1 for r in responses if "- " in r or "* " in r)
        has_emoji = sum(1 for r in responses if any(ord(c) > 0x1F600 for c in r))
        has_question = sum(1 for r in responses if "?" in r)
        print(f"    Contains bullets: {has_bullet}/{len(responses)}")
        print(f"    Contains emoji: {has_emoji}/{len(responses)}")
        print(f"    Contains question: {has_question}/{len(responses)}")
        print()


def cmd_sessions(args, config):
    """List recent sessions with their traces."""
    params = {"limit": args.limit}
    if args.days:
        from_time = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["fromTimestamp"] = from_time.isoformat()

    result = api_request(config, "sessions", params)
    sessions = result.get("data", [])

    if not sessions:
        print("No sessions found.")
        return

    print(f"\n{'Session ID':<40} {'Created':<22} {'Traces':>6}")
    print("-" * 72)

    for s in sessions:
        trace_count = len(s.get("traces", []))
        print(
            f"{s['id']:<40} "
            f"{format_timestamp(s.get('createdAt')):<22} "
            f"{trace_count:>6}"
        )

    print(f"\nTotal: {len(sessions)} sessions")


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and analyze Langfuse traces from Voya staging/prod",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--env", default="staging", choices=["staging", "prod"],
                        help="Environment (default: staging)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List recent traces")
    p_list.add_argument("--tag", help="Filter by tag (e.g. flight-agent, hotel-agent)")
    p_list.add_argument("--user-id", help="Filter by user ID")
    p_list.add_argument("--session-id", help="Filter by session ID")
    p_list.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    p_list.add_argument("--limit", type=int, default=20, help="Max traces to return (default: 20)")

    # show
    p_show = subparsers.add_parser("show", help="Show detailed trace")
    p_show.add_argument("trace_id", help="Trace ID to show")
    p_show.add_argument("--verbose", "-v", action="store_true", help="Show all observations")

    # export
    p_export = subparsers.add_parser("export", help="Export traces to JSON")
    p_export.add_argument("--tag", help="Filter by tag")
    p_export.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    p_export.add_argument("--limit", type=int, default=100, help="Max traces (default: 100)")
    p_export.add_argument("--output", "-o", help="Output file (default: stdout)")
    p_export.add_argument("--include-observations", action="store_true",
                          help="Include full observations per trace (slower)")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze response patterns for E2E")
    p_analyze.add_argument("--tag", help="Filter by tag")
    p_analyze.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    p_analyze.add_argument("--limit", type=int, default=100, help="Max traces (default: 100)")

    # sessions
    p_sessions = subparsers.add_parser("sessions", help="List recent sessions")
    p_sessions.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    p_sessions.add_argument("--limit", type=int, default=20, help="Max sessions (default: 20)")

    args = parser.parse_args()
    config = load_env(args.env)

    commands = {
        "list": cmd_list,
        "show": cmd_show,
        "export": cmd_export,
        "analyze": cmd_analyze,
        "sessions": cmd_sessions,
    }

    commands[args.command](args, config)


if __name__ == "__main__":
    main()
