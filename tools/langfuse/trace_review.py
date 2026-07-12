#!/usr/bin/env python3
"""Langfuse Trace Data Collector for Voya (Production).

Fetches production traces, computes per-agent metrics, and outputs
structured JSON for Claude to analyze and generate a report.

Usage:
    python trace_review.py --days 7
    python trace_review.py --days 7 -o /tmp/traces.json
    python trace_review.py --days 7 --min-messages 3

Credentials:
    - Langfuse: .local/secrets/langfuse_prod > env vars > backend_python/.env
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from review_lib.fetcher import (
    build_score_lookup,
    enrich_traces_with_observations,
    fetch_scores_for_period,
    fetch_traces_for_period,
    group_traces_by_session,
    load_config,
)
from review_lib.metrics import compute_agent_metrics, compute_overall_metrics
from review_lib.session_analyzer import _mask_email, analyze_sessions


def build_output(days: int, min_messages: int) -> dict:
    """Fetch all data and return structured dict for Claude to analyze."""

    # 1. Load credentials
    print("Loading production credentials...", file=sys.stderr)
    config = load_config()
    langfuse_base_url = config["LANGFUSE_BASE_URL"].rstrip("/")

    # 2. Fetch traces + scores
    print(f"Fetching traces for the last {days} days...", file=sys.stderr)
    traces = fetch_traces_for_period(config, days)
    print(f"  Found {len(traces)} traces", file=sys.stderr)

    if not traces:
        return {"error": "No traces found for the specified period."}

    print("Fetching feedback scores...", file=sys.stderr)
    scores = fetch_scores_for_period(config, days)
    print(f"  Found {len(scores)} feedback scores", file=sys.stderr)

    # 3. Build lookups + group
    score_lookup = build_score_lookup(scores)
    sessions = group_traces_by_session(traces)
    print(f"  {len(sessions)} sessions identified", file=sys.stderr)

    # 4. Compute quantitative metrics
    print("Computing metrics...", file=sys.stderr)
    agent_metrics = compute_agent_metrics(traces, score_lookup)

    now = datetime.now(timezone.utc)
    period_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")
    overall = compute_overall_metrics(
        traces, agent_metrics, sessions, period_start, period_end
    )

    # 5. Build session health objects
    print("Analyzing sessions...", file=sys.stderr)
    all_sessions, _ = analyze_sessions(sessions, score_lookup, langfuse_base_url)

    # 6. Enrich sessions with 3+ messages with observations (tool calls etc.)
    reviewable = [s for s in all_sessions if s.trace_count >= min_messages]
    if reviewable:
        print(
            f"Fetching trace observations for {len(reviewable)} sessions "
            f"({min_messages}+ messages)...",
            file=sys.stderr,
        )
        enrich_traces_with_observations(config, reviewable)

    skipped = len(all_sessions) - len(reviewable)
    if skipped:
        print(f"  Skipping {skipped} sessions with <{min_messages} messages", file=sys.stderr)

    # 7. Build JSON output
    output = {
        "generated_at": now.isoformat(),
        "period_days": days,
        "period_start": period_start,
        "period_end": period_end,
        "langfuse_base_url": langfuse_base_url,
        "summary": {
            "total_traces": overall.total_traces,
            "total_sessions": overall.total_sessions,
            "unique_users": overall.unique_users,
            "success_rate_pct": round(overall.overall_success_rate, 1),
            "error_rate_pct": round(overall.overall_error_rate, 1),
            "total_cost_usd": round(overall.total_cost, 4),
        },
        "agent_metrics": {
            name: {
                "total_traces": m.total_traces,
                "error_count": m.error_count,
                "success_rate_pct": round(m.success_rate, 1),
                "latency_p50_s": round(m.latency_p50, 2),
                "latency_p95_s": round(m.latency_p95, 2),
                "latency_max_s": round(m.latency_max, 2),
                "total_cost_usd": round(m.total_cost, 4),
                "feedback_positive": m.feedback_positive,
                "feedback_negative": m.feedback_negative,
            }
            for name, m in agent_metrics.items()
        },
        "sessions": [],
    }

    for s in all_sessions:
        session_data = {
            "session_id": s.session_id,
            "session_url": f"{langfuse_base_url}/sessions/{s.session_id}",
            "user_email": _mask_email(s.user_email),
            "user_id": s.user_id[:8] + "..." if s.user_id else None,
            "trace_count": s.trace_count,
            "total_latency_s": round(s.total_latency, 1),
            "agents_used": s.agents_used,
            "error_count": s.error_count,
            "completed_action": s.completed_action,
            "frustration_score": round(s.frustration_score, 2),
            "flags": s.flags,
            "reviewed": s.trace_count >= min_messages,
            "conversation": [],
        }

        for t in s.traces:
            turn = {
                "trace_id": t.trace_id,
                "langfuse_url": t.langfuse_url,
                "timestamp": t.timestamp,
                "agent": t.agent,
                "latency_s": round(t.latency, 1) if t.latency else None,
                "cost_usd": round(t.cost, 6) if t.cost else None,
                "is_error": t.is_error,
                "has_negative_feedback": t.has_negative_feedback,
                "user_message": t.user_message,
                "ai_response": t.ai_response,
            }
            # Include observations (tool calls, LLM internals) if available
            if t._observations:
                turn["observations"] = [
                    {
                        "type": obs.get("type"),
                        "name": obs.get("name"),
                        "model": obs.get("model"),
                        "input": str(obs.get("input", ""))[:300],
                        "output": str(obs.get("output", ""))[:300],
                    }
                    for obs in t._observations[:8]
                ]
            session_data["conversation"].append(turn)

        output["sessions"].append(session_data)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Langfuse trace data for Claude to analyze",
    )
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--min-messages", type=int, default=3,
                        help="Min messages per session to include observations (default: 3)")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    data = build_output(args.days, args.min_messages)

    if "error" in data:
        print(f"Error: {data['error']}", file=sys.stderr)
        sys.exit(1)

    json_output = json.dumps(data, indent=2, default=str)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json_output, encoding="utf-8")
        print(f"\nData saved to: {args.output}", file=sys.stderr)
        print(
            f"Sessions: {data['summary']['total_sessions']} | "
            f"Traces: {data['summary']['total_traces']} | "
            f"Reviewable: {sum(1 for s in data['sessions'] if s['reviewed'])}",
            file=sys.stderr,
        )
    else:
        print(json_output)


if __name__ == "__main__":
    main()
