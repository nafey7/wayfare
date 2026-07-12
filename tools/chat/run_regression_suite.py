"""Run the 12 itinerary regression scenarios sequentially.

Issue #1053 Phase 0 verification: confirm the locked-baseline scenarios pass
against the current backend before they enter CI as a hard gate.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = SCRIPT_DIR / "scenarios" / "32_itinerary_regression"
VOYA_CHAT = SCRIPT_DIR / "voya_chat.py"

scenarios = sorted(SCENARIO_DIR.glob("R*.json"))
total = len(scenarios)
print(f"Running {total} regression scenarios against local backend\n", flush=True)

env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
started = time.monotonic()
passed = 0
failed = 0
failed_names: list[str] = []

for idx, scenario in enumerate(scenarios, 1):
    t0 = time.monotonic()
    print(f"[{idx}/{total}] {scenario.name}", flush=True)
    proc = subprocess.run(
        [
            sys.executable,
            str(VOYA_CHAT),
            "--env", "local",
            "--scenario", str(scenario),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        env=env,
    )
    elapsed = time.monotonic() - t0
    if proc.returncode == 0:
        passed += 1
        status = "PASS"
    else:
        failed += 1
        failed_names.append(scenario.name)
        status = "FAIL"
    last = ""
    for line in reversed((proc.stdout or "").strip().splitlines()):
        if line.strip():
            last = line.strip()
            break
    print(f"    -> {status} ({elapsed:.1f}s) {last[:120]}", flush=True)

elapsed_total = time.monotonic() - started
print(f"\nDone: {passed}/{total} passed in {elapsed_total/60:.1f} min", flush=True)
if failed_names:
    print("\nFailed:", flush=True)
    for n in failed_names:
        print(f"  - {n}", flush=True)
    sys.exit(1)
