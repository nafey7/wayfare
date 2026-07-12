#!/usr/bin/env python3
"""Generate a markdown report from scenario_results/*.json files.

Reads every result JSON written today (or matching --since), aggregates
pass/fail counts, and produces a detailed report with per-scenario:
  - Description
  - Each step's query, AI response, expected checks, and pass/fail reason
  - Timing
  - Failure analysis grouped by category
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "scenario_results"


def collect_results(env: str, since_iso: str) -> list[dict]:
    """Collect per-scenario JSON results matching env, newer than since_iso."""
    since_dt = datetime.fromisoformat(since_iso)
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)
    results = []
    for p in RESULTS_DIR.glob(f"*_{env}_*.json"):
        if p.name.startswith("_aggregate_"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        ts = data.get("timestamp", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= since_dt:
            data["_path"] = str(p)
            data["_dt"] = dt
            results.append(data)
    results.sort(key=lambda d: d["_dt"])
    return results


_CATEGORY_NAMES = {
    "0": "00_routing_bulk",
    "1": "01_supervisor",
    "2": "02_flight_basic",
    "3": "03_flight_multicity",
    "4": "04_flight_dates",
    "5": "05_flight_airports",
    "6": "06_flight_filters",
    "7": "07_flight_after",
    "8": "08_flight_passengers",
    "9": "09_hotel_basic",
    "10": "10_hotel_dates",
    "11": "11_itinerary_basic",
    "12": "12_itinerary_mods",
    "13": "13_hotel_filters",
    "14": "14_hotel_or_itinerary",
    "15": "15_general_or_handback",
    "16": "16_hotel_or_itinerary_dest",
    "17": "17_cross_or_handback",
    "18": "18_date_edge_or_context",
    "19": "19_results_or_preferences",
    "20": "20_flight_results",
}


def categorize_scenario(result: dict) -> str:
    """Map scenario name (e.g. '2.1_one_way_asks_all') to category dir.

    Uses the leading number before the dot (e.g. '2' → '02_flight_basic').
    Special-cases the debug/ directory.
    """
    name = result.get("scenario", "")
    if not name:
        return "other"
    # Debug scenarios start with letters / numbers like "73993_venice_..."
    if name.startswith("3658") or name.startswith("73993") or name.startswith("b219"):
        return "debug"
    # Standard format: "<num>.<sub>_..." (e.g. "2.1_..." or "13.10_...")
    head = name.split("_", 1)[0]
    if "." in head:
        major = head.split(".")[0]
        return _CATEGORY_NAMES.get(major, f"unknown_{major}")
    return "other"


def format_check(check: dict) -> str:
    icon = "✅" if check["passed"] else "❌"
    return f"{icon} **{check['name']}**: {check['detail']}"


def format_step(step: dict) -> str:
    parts = []
    parts.append(f"**Query**: `{step['send']}`")
    msg = (step.get("ai_message") or "").strip()
    if not msg:
        msg = "_(no message text — type=" + (step.get("type") or "unknown") + ")_"
    parts.append(f"**AI**:\n```\n{msg[:500]}{'…' if len(msg) > 500 else ''}\n```")
    parts.append(f"**Type**: `{step.get('type')}` · **Intent**: `{step.get('intent')}` · **Time**: {step['response_time_ms']:.0f}ms")
    checks = step.get("checks", [])
    if checks:
        parts.append("**Checks**:")
        for c in checks:
            parts.append(f"- {format_check(c)}")
    return "\n\n".join(parts)


def render(results: list[dict], output: Path, env: str) -> None:
    total_passed = sum(r.get("passed", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    total_steps = total_passed + total_failed
    scenarios_pass = [r for r in results if r.get("failed", 0) == 0]
    scenarios_fail = [r for r in results if r.get("failed", 0) > 0]
    total_scenarios = len(results)

    if total_steps:
        step_rate = total_passed / total_steps * 100
    else:
        step_rate = 0.0
    if total_scenarios:
        scenario_rate = len(scenarios_pass) / total_scenarios * 100
    else:
        scenario_rate = 0.0

    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_category[categorize_scenario(r)].append(r)

    lines: list[str] = []
    lines.append(f"# Voya Chat Scenario Test Report — `{env}`")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Total scenarios**: {total_scenarios}")
    lines.append("")
    lines.append("## Overall results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Scenarios run | {total_scenarios} |")
    lines.append(f"| Scenarios fully passing | {len(scenarios_pass)} ({scenario_rate:.1f}%) |")
    lines.append(f"| Scenarios with at least one failure | {len(scenarios_fail)} |")
    lines.append(f"| Total step assertions | {total_steps} |")
    lines.append(f"| Steps passed | {total_passed} ({step_rate:.1f}%) |")
    lines.append(f"| Steps failed | {total_failed} |")
    lines.append("")

    # Latency distribution
    avg_times = [r.get("avg_time_ms", 0) for r in results if r.get("avg_time_ms")]
    if avg_times:
        avg_times_sorted = sorted(avg_times)
        n = len(avg_times_sorted)
        p50 = avg_times_sorted[n // 2]
        p95 = avg_times_sorted[int(n * 0.95)]
        lines.append("## Latency (per-step)")
        lines.append("")
        lines.append(f"- Median (p50): **{p50:.0f}ms**")
        lines.append(f"- p95: **{p95:.0f}ms**")
        lines.append(f"- Max: **{max(avg_times):.0f}ms** ({next(r['scenario'] for r in results if r.get('avg_time_ms') == max(avg_times))})")
        lines.append("")

    # Per-category summary
    lines.append("## By category")
    lines.append("")
    lines.append("| Category | Total | Passing | Failing | Pass rate |")
    lines.append("|---|---|---|---|---|")
    for cat in sorted(by_category):
        cat_results = by_category[cat]
        cat_pass = sum(1 for r in cat_results if r.get("failed", 0) == 0)
        cat_fail = len(cat_results) - cat_pass
        rate = cat_pass / len(cat_results) * 100 if cat_results else 0
        lines.append(f"| `{cat}` | {len(cat_results)} | {cat_pass} | {cat_fail} | {rate:.0f}% |")
    lines.append("")

    # Failures section first (most actionable)
    if scenarios_fail:
        lines.append("## ❌ Failures — detailed analysis")
        lines.append("")
        lines.append(f"_{len(scenarios_fail)} scenario(s) had at least one failed assertion._")
        lines.append("")
        for r in scenarios_fail:
            lines.append(f"### {r['scenario']}")
            lines.append("")
            lines.append(f"_{r.get('description', '')}_")
            lines.append("")
            lines.append(f"**Steps**: {r['passed']} passed / {r['failed']} failed · **avg time**: {r.get('avg_time_ms', 0):.0f}ms · **chat_id**: `{r.get('chat_id', '?')}`")
            lines.append("")
            for step in r.get("steps", []):
                step_status = "✅" if step.get("passed") else "❌"
                lines.append(f"#### {step_status} Step {step['step']}")
                lines.append("")
                lines.append(format_step(step))
                lines.append("")
            lines.append("---")
            lines.append("")

    # Passing scenarios — condensed
    lines.append("## ✅ Passing scenarios — condensed view")
    lines.append("")
    lines.append("| Scenario | Steps | Avg ms | Max ms | Description |")
    lines.append("|---|---|---|---|---|")
    for r in scenarios_pass:
        lines.append(
            f"| `{r['scenario']}` | {r['passed']} | {r.get('avg_time_ms', 0):.0f} | "
            f"{r.get('max_time_ms', 0):.0f} | {r.get('description', '')[:80]} |"
        )
    lines.append("")

    # All scenarios full detail
    lines.append("## 📋 All scenarios — full detail")
    lines.append("")
    lines.append("<details><summary>Click to expand — every query and AI response</summary>")
    lines.append("")
    for r in results:
        status = "✅ PASS" if r.get("failed", 0) == 0 else "❌ FAIL"
        lines.append(f"### {status} · {r['scenario']}")
        lines.append("")
        lines.append(f"_{r.get('description', '')}_")
        lines.append("")
        for step in r.get("steps", []):
            step_status = "✅" if step.get("passed") else "❌"
            lines.append(f"**{step_status} Step {step['step']}** ({step['response_time_ms']:.0f}ms)")
            lines.append("")
            lines.append(format_step(step))
            lines.append("")
        lines.append("")
    lines.append("</details>")
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {output}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="local")
    p.add_argument("--since", required=True, help="ISO timestamp (UTC) — only include results newer than this")
    p.add_argument("--out", default="docs/CHAT_SCENARIO_REPORT.md")
    args = p.parse_args()
    results = collect_results(args.env, args.since)
    if not results:
        print("No results found.")
        return
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render(results, out_path, args.env)
    print(f"Total results: {len(results)}")


if __name__ == "__main__":
    main()
