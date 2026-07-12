"""Run every itinerary-related scenario in the suite + smartness scenarios that
exercise the itinerary flow. Outputs structured JSONs into scenario_results/ for
the report generator to pick up.

Folders included (all `*.json` in each):
- 11_itinerary_basic
- 12_itinerary_mods
- 14_itinerary_dates
- 15_itinerary_handback
- 16_itinerary_destinations
- 18_itinerary_context
- 19_itinerary_preferences
- 30_itinerary_phase0_regression
- 32_itinerary_regression
- 01_supervisor/1.4_route_to_itinerary.json
- 20_memory_in_chat/{A1, A2, A4}.json     (smartness — itinerary→flight/hotel)
- 25_detour_resume/F2_visa_mid_itinerary.json
- debug/b219_*.json
"""

import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIO_ROOT = SCRIPT_DIR / "scenarios"
VOYA_CHAT = SCRIPT_DIR / "voya_chat.py"

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

EXTRA_SCENARIOS = [
    "01_supervisor/1.4_route_to_itinerary.json",
    "20_memory_in_chat/A1_pax_carry_itinerary_to_flight.json",
    "20_memory_in_chat/A2_dates_carry_itinerary_to_hotel.json",
    "20_memory_in_chat/A4_dietary_constraint_carry.json",
    "25_detour_resume/F2_visa_mid_itinerary.json",
    "debug/b219_amend_no_itinerary.json",
    "debug/b219_itinerary_start_time.json",
]

scenarios: list[Path] = []
for folder in ITINERARY_FOLDERS:
    folder_path = SCENARIO_ROOT / folder
    if not folder_path.exists():
        continue
    for f in sorted(folder_path.glob("*.json")):
        scenarios.append(f)

for rel in EXTRA_SCENARIOS:
    p = SCENARIO_ROOT / rel
    if p.exists():
        scenarios.append(p)

total = len(scenarios)
print(f"Running {total} itinerary-related scenarios against local backend\n", flush=True)

env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
started = time.monotonic()
passed = 0
failed = 0
failed_names: list[str] = []
run_tag = time.strftime("%Y%m%d_%H%M%S")
print(f"Run tag (timestamp prefix to grep result files later): {run_tag}\n", flush=True)

for idx, scenario in enumerate(scenarios, 1):
    rel = scenario.relative_to(SCENARIO_ROOT)
    t0 = time.monotonic()
    print(f"[{idx}/{total}] {rel}", flush=True)
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
        timeout=900,
        env=env,
    )
    elapsed = time.monotonic() - t0
    if proc.returncode == 0:
        passed += 1
        status = "PASS"
    else:
        failed += 1
        failed_names.append(str(rel))
        status = "FAIL"
    last = ""
    for line in reversed((proc.stdout or "").strip().splitlines()):
        if line.strip():
            last = line.strip()
            break
    print(f"    -> {status} ({elapsed:.1f}s) {last[:120]}", flush=True)

elapsed_total = time.monotonic() - started
print(
    f"\nDone: {passed}/{total} passed in {elapsed_total/60:.1f} min",
    flush=True,
)
if failed_names:
    print("\nFailed:", flush=True)
    for n in failed_names:
        print(f"  - {n}", flush=True)
    sys.exit(1)
