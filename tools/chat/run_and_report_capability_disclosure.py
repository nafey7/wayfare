"""Run all 31_capability_disclosure scenarios and build a detailed Markdown report.

The report shows, per scenario:
- Pass/fail summary
- Each step's user input
- Each step's AI response (verbatim)
- Each assertion's result (PASS/FAIL with the expected vs got)

Why a custom script (not reuse run_smartness_suite.py): that script lives on
the 1053 branch and isn't on this branch yet. This one is small and focused.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = REPO_ROOT / "tools/chat/scenarios/31_capability_disclosure"
RESULTS_DIR = REPO_ROOT / "tools/chat/scenario_results"
REPORT_PATH = REPO_ROOT / "reports/capability_disclosure_run.md"
ENV = "local"

SCENARIO_FILES = sorted(SCEN_DIR.glob("*.json"))


def run_one(scenario_path: Path) -> Path | None:
    """Run voya_chat.py against the scenario, return the path to the result JSON."""
    timestamp_marker = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    print(f"  [{timestamp_marker}] running {scenario_path.name} ...")
    cmd = [
        sys.executable,
        "tools/chat/voya_chat.py",
        "--env",
        ENV,
        "--scenario",
        str(scenario_path.relative_to(REPO_ROOT).as_posix()),
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={"PYTHONIOENCODING": "utf-8", **dict(__import__("os").environ)},
        timeout=600,
    )
    if proc.returncode != 0:
        print(f"    voya_chat.py exit={proc.returncode}")
        print(f"    stderr tail: {proc.stderr[-400:]}")
    # Find the freshest result JSON for this scenario.
    stem = scenario_path.stem
    candidates = sorted(RESULTS_DIR.glob(f"{stem}_{ENV}_*.json"))
    if not candidates:
        print(f"    NO RESULT JSON FOUND for {stem}")
        return None
    return candidates[-1]


def fmt_check(check: dict) -> str:
    """One-line markdown summary of a check dict."""
    name = check.get("name", "?")
    ok = check.get("passed", False)
    detail = check.get("detail", "")
    badge = "✅ PASS" if ok else "❌ FAIL"
    return f"  - {badge} **{name}**: {detail}"


def render_step(step_idx: int, step: dict) -> list[str]:
    out: list[str] = []
    user_msg = step.get("send", "")
    ai_msg = step.get("ai_message", "")
    rtype = step.get("type", "?")
    intent = step.get("intent", "?")
    confidence = step.get("confidence", "—")
    rtime = step.get("response_time_ms", "?")
    out.append(f"### Step {step_idx + 1}")
    out.append("")
    out.append(f"**👤 You:** {user_msg}")
    out.append("")
    out.append(f"**🤖 Voya:** {ai_msg.strip()}")
    out.append("")
    out.append(
        f"_metadata: type=`{rtype}`, intent=`{intent}`, "
        f"confidence={confidence}, response_time={rtime}ms_"
    )
    out.append("")
    checks = step.get("checks") or []
    if checks:
        out.append("**Assertions:**")
        for c in checks:
            out.append(fmt_check(c))
    out.append("")
    return out


def main() -> int:
    print(f"Running {len(SCENARIO_FILES)} scenarios against env={ENV}...")
    results: list[dict] = []
    for sp in SCENARIO_FILES:
        rj = run_one(sp)
        if rj is None:
            continue
        with open(rj, encoding="utf-8") as f:
            data = json.load(f)
        results.append(data)

    # ---- Build the markdown report ----
    pass_count = sum(1 for r in results if r.get("failed", 0) == 0)
    fail_count = len(results) - pass_count
    total_steps = sum(len(r.get("steps") or []) for r in results)
    total_step_passes = sum(
        sum(1 for s in r.get("steps") or [] if s.get("passed", False))
        for r in results
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# AI-CHAT-013 Capability Disclosure — Scenario Run Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(UTC).isoformat()}Z")
    lines.append(f"**Environment:** `{ENV}`")
    lines.append(f"**Scenarios run:** {len(results)} of {len(SCENARIO_FILES)}")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"| Metric | Value |\n|---|---|\n"
        f"| Scenarios PASS | **{pass_count} / {len(results)}** |\n"
        f"| Scenarios FAIL | {fail_count} |\n"
        f"| Total steps | {total_steps} |\n"
        f"| Step-level passes | {total_step_passes} |"
    )
    lines.append("")
    lines.append("## Summary table")
    lines.append("")
    lines.append("| # | Scenario | Steps | Result | avg ms |")
    lines.append("|---|---|---:|---|---:|")
    for r in results:
        steps = r.get("steps") or []
        avg_ms = r.get("avg_time_ms", "?")
        verdict = "✅ PASS" if r.get("failed", 0) == 0 else "❌ FAIL"
        passed = sum(1 for s in steps if s.get("passed", False))
        lines.append(
            f"| {r.get('scenario', '?')} | {r.get('description', '')[:80]} | "
            f"{passed}/{len(steps)} | {verdict} | {avg_ms} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Per-scenario detail")
    lines.append("")
    for r in results:
        lines.append(
            f"## {r.get('scenario', '?')} — "
            f"{'✅ PASS' if r.get('failed', 0) == 0 else '❌ FAIL'}"
        )
        lines.append("")
        lines.append(f"_{r.get('description', '')}_")
        lines.append("")
        lines.append(f"- **chat_id:** `{r.get('chat_id', '?')}`")
        lines.append(f"- **timestamp:** {r.get('timestamp', '?')}")
        lines.append(
            f"- **timing:** avg={r.get('avg_time_ms', '?')}ms "
            f"max={r.get('max_time_ms', '?')}ms "
            f"total={r.get('total_time_ms', '?')}ms"
        )
        lines.append("")
        for i, step in enumerate(r.get("steps") or []):
            lines.extend(render_step(i, step))
        lines.append("---")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Scenarios PASS {pass_count} / {len(results)}, FAIL {fail_count}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
