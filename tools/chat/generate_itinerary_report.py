"""Generate a comprehensive markdown report from the latest itinerary scenario
results.

For each scenario:
- What was sent (user message)
- What the AI replied (full text)
- Which assertions passed / failed
- Timing
- Why the scenario passed or failed

Output: docs/ITINERARY_TEST_REPORT.md
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SCENARIO_ROOT = SCRIPT_DIR / "scenarios"
RESULTS_DIR = SCRIPT_DIR / "scenario_results"
OUTPUT = PROJECT_ROOT / "docs" / "ITINERARY_TEST_REPORT.md"

ITINERARY_FOLDERS = [
    "11_itinerary_basic",
    "12_itinerary_mods",
    "14_itinerary_dates",
    "15_itinerary_handback",
    "16_itinerary_destinations",
    "18_itinerary_context",
    "19_itinerary_preferences",
    "30_itinerary_phase0_regression",
    "32_itinerary_regression",
]
EXTRA_SCENARIO_RELS = [
    "01_supervisor/1.4_route_to_itinerary.json",
    "20_memory_in_chat/A1_pax_carry_itinerary_to_flight.json",
    "20_memory_in_chat/A2_dates_carry_itinerary_to_hotel.json",
    "20_memory_in_chat/A4_dietary_constraint_carry.json",
    "25_detour_resume/F2_visa_mid_itinerary.json",
    "debug/b219_amend_no_itinerary.json",
    "debug/b219_itinerary_start_time.json",
]


def collect_target_scenarios() -> dict[str, Path]:
    """Map scenario `name` (as in the JSON's "name" field) → file path."""
    target: dict[str, Path] = {}
    for folder in ITINERARY_FOLDERS:
        for p in sorted((SCENARIO_ROOT / folder).glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                target[data.get("name", p.stem)] = p
            except Exception:
                continue
    for rel in EXTRA_SCENARIO_RELS:
        p = SCENARIO_ROOT / rel
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            target[data.get("name", p.stem)] = p
        except Exception:
            continue
    return target


def load_latest_result(scenario_name: str) -> dict | None:
    """Return the newest result JSON for the given scenario name."""
    pattern = re.compile(
        rf"^{re.escape(scenario_name)}_(?:local|test|staging|prod)_(\d{{8}}_\d{{6}})\.json$"
    )
    candidates: list[tuple[str, Path]] = []
    for f in RESULTS_DIR.glob(f"{scenario_name}_*.json"):
        m = pattern.match(f.name)
        if m:
            candidates.append((m.group(1), f))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    try:
        return json.loads(candidates[0][1].read_text(encoding="utf-8"))
    except Exception:
        return None


def scenario_folder(path: Path) -> str:
    return path.parent.name


def step_passed(step: dict) -> bool:
    if "passed" in step:
        return bool(step["passed"])
    checks = step.get("checks") or step.get("assertions") or []
    for c in checks:
        if isinstance(c, dict) and not c.get("passed", c.get("ok", True)):
            return False
    return True


def scenario_passed(result: dict) -> bool:
    steps = result.get("steps", [])
    return bool(steps) and all(step_passed(s) for s in steps)


def short(s: str, n: int = 600) -> str:
    s = (s or "").strip().replace("\r\n", "\n")
    if len(s) > n:
        return s[:n] + " …"
    return s


def render_step(step: dict) -> list[str]:
    out: list[str] = []
    sent = (step.get("send") or step.get("message") or "").strip()
    ai = step.get("ai_message") or step.get("message") or ""
    resp_type = step.get("type")
    intent = step.get("intent")
    t_ms = step.get("response_time_ms")
    t_str = f"{t_ms / 1000:.1f}s" if isinstance(t_ms, (int, float)) else "?"
    icon = "✓" if step_passed(step) else "✗"
    out.append(f"**Turn {step.get('step', '?')}** [{icon} {t_str}]")
    out.append(f"> **User:** {short(sent, 400)}")
    if ai:
        out.append(f"> **Bot:** {short(ai, 800)}")
    meta_bits: list[str] = []
    if resp_type:
        meta_bits.append(f"type=`{resp_type}`")
    if intent:
        meta_bits.append(f"intent=`{intent}`")
    if meta_bits:
        out.append(f"> _meta:_ {' · '.join(meta_bits)}")
    checks = step.get("checks") or []
    if checks:
        out.append(">")
        out.append("> Assertions:")
        for c in checks:
            if not isinstance(c, dict):
                continue
            ok = c.get("passed", c.get("ok", True))
            mark = "✅" if ok else "❌"
            detail = c.get("detail") or c.get("message") or ""
            out.append(f"> - {mark} **{c.get('name', '?')}**: {detail}")
    return out


def main() -> None:
    targets = collect_target_scenarios()
    print(f"Looking for results for {len(targets)} scenarios…", file=sys.stderr)

    by_folder: dict[str, list[tuple[str, Path, dict | None]]] = defaultdict(list)
    for name, path in sorted(targets.items()):
        result = load_latest_result(name)
        by_folder[scenario_folder(path)].append((name, path, result))

    total = sum(len(v) for v in by_folder.values())
    have_results = sum(1 for v in by_folder.values() for (_, _, r) in v if r)
    passed = sum(
        1
        for v in by_folder.values()
        for (_, _, r) in v
        if r and scenario_passed(r)
    )
    failed = sum(
        1
        for v in by_folder.values()
        for (_, _, r) in v
        if r and not scenario_passed(r)
    )
    missing = total - have_results

    # ---- Document ----
    L: list[str] = []
    L.append("# Itinerary Test Report")
    L.append("")
    L.append("Auto-generated from the latest result JSON per scenario in "
             "`tools/chat/scenario_results/`.")
    L.append("")
    L.append("## Headline")
    L.append("")
    L.append(f"- **Scenarios in scope:** {total}")
    L.append(f"- **Results available:** {have_results}")
    L.append(f"- **Passed:** {passed}")
    L.append(f"- **Failed:** {failed}")
    if missing:
        L.append(f"- **Missing results:** {missing} (no result JSON found yet)")
    pass_rate = f"{(passed / have_results * 100):.0f}%" if have_results else "—"
    L.append(f"- **Pass rate (of those with results):** {pass_rate}")
    L.append("")

    # ---- Per-folder summary table ----
    L.append("## Per-Folder Summary")
    L.append("")
    L.append("| Folder | Scenarios | Passed | Failed | Missing | Pass rate |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for folder, rows in sorted(by_folder.items()):
        fpassed = sum(1 for (_, _, r) in rows if r and scenario_passed(r))
        ffailed = sum(1 for (_, _, r) in rows if r and not scenario_passed(r))
        fmissing = sum(1 for (_, _, r) in rows if not r)
        denom = fpassed + ffailed
        rate = f"{(fpassed / denom * 100):.0f}%" if denom else "—"
        L.append(f"| `{folder}/` | {len(rows)} | {fpassed} | {ffailed} | {fmissing} | {rate} |")
    L.append("")

    # ---- Failure-only quick list ----
    failures = [
        (folder, name, result)
        for folder, rows in by_folder.items()
        for (name, _, result) in rows
        if result and not scenario_passed(result)
    ]
    if failures:
        L.append("## Failures (quick list)")
        L.append("")
        for folder, name, _ in failures:
            L.append(f"- `{folder}/` **{name}**")
        L.append("")

    # ---- Per-scenario detail ----
    L.append("## Per-Scenario Detail")
    L.append("")
    for folder, rows in sorted(by_folder.items()):
        L.append(f"### `{folder}/`")
        L.append("")
        for name, path, result in rows:
            if result is None:
                L.append(f"#### ⏳ MISSING — `{name}`")
                L.append("")
                L.append(f"_No result JSON found for `{path.name}` yet (run still in progress, or scenario didn't execute)._")
                L.append("")
                continue
            ok = scenario_passed(result)
            badge = "✅ PASS" if ok else "❌ FAIL"
            desc = (result.get("description") or "").strip()
            L.append(f"#### {badge} — `{name}`")
            if desc:
                L.append(f"_{desc}_")
            L.append("")
            steps = result.get("steps", [])
            timing_total = result.get("total_time_ms")
            if isinstance(timing_total, (int, float)):
                L.append(f"_Total time: {timing_total/1000:.1f}s · {len(steps)} turn(s)_")
                L.append("")
            for step in steps:
                L.extend(render_step(step))
                L.append("")
            # Why it failed
            if not ok:
                why: list[str] = []
                for step in steps:
                    for c in step.get("checks") or []:
                        if isinstance(c, dict) and not c.get("passed", c.get("ok", True)):
                            why.append(
                                f"Turn {step.get('step')} — `{c.get('name')}`: "
                                f"{c.get('detail') or c.get('message') or '(no detail)'}"
                            )
                if why:
                    L.append("**Why it failed:**")
                    for w in why:
                        L.append(f"- {w}")
                    L.append("")
            L.append("---")
            L.append("")

    # ---- Themes / observations placeholder ----
    L.append("## Themes & Observations")
    L.append("")
    L.append("_(Add after reviewing the per-scenario detail. Common patterns to look for:_")
    L.append("_- Search/itinerary tools fired vs not_")
    L.append("_- Capability disclosure intercepts that shouldn't fire_")
    L.append("_- Date-parsing or destination-resolution failures_")
    L.append("_- Re-asking for fields already in shared_context_")
    L.append("_- Latency outliers)_")
    L.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
