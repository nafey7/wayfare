"""Benchmark test runner for date parsing.

Runs all test cases from date_parsing_test_dataset.py against the live
parse_dates LLM pipeline and reports pass/fail per category.

Usage:
    cd backend_python
    pytest tests/unit_tests/test_ai/test_graph/test_date_parsing_benchmark.py -v -s --timeout=300

    # Run a single category:
    pytest ... -k "standard_formats"

    # Generate report only (no pytest overhead):
    python -m tests.unit_tests.test_ai.test_graph.test_date_parsing_benchmark

Requires a running LLM backend (env vars for GEMINI_API_KEY or equivalent).
Reference date is fixed to 2026-04-20 for deterministic expectations.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from tests.unit_tests.test_ai.test_graph.date_parsing_test_dataset import (
    ALL_TEST_CASES,
    TOTAL_TEST_CASES,
)

logger = logging.getLogger(__name__)

REFERENCE_DATE = "2026-04-20"

# Tolerance for approximate date matching (days). Seasonal/holiday dates
# may legitimately differ by a few days depending on the LLM's knowledge.
FUZZY_TOLERANCE_DAYS = 5

# Categories where dates are approximate (seasons, holidays, events, etc.)
FUZZY_CATEGORIES = {
    "seasons",
    "holidays",
    "school_breaks",
    "events",
    "regional_seasons",
    "weekend_references",
    "business_travel",
    "conference_events",
    "natural_hedging",
    "relative_to_date",
    "international",
    "australia_nz",
    "india_holidays",
    "middle_east",
    "southeast_asia_holidays",
    "european_holidays",
    "latin_american",
    "african_holidays",
    "year_spanning",
    "corrections",
}


def _dates_match(expected: str, actual: str, fuzzy: bool = False) -> bool:
    """Check if two date strings match, optionally with fuzzy tolerance."""
    if expected == actual:
        return True
    if not fuzzy:
        return False
    try:
        e = datetime.strptime(expected, "%Y-%m-%d")
        a = datetime.strptime(actual, "%Y-%m-%d")
        return abs((e - a).days) <= FUZZY_TOLERANCE_DAYS
    except (ValueError, TypeError):
        return False


def _check_result(
    expected: dict, actual: dict, fuzzy: bool = False
) -> tuple[bool, list[str]]:
    """Check if actual result matches expected fields.

    Returns (passed, list_of_failure_reasons).
    """
    failures = []

    for key, expected_val in expected.items():
        actual_val = actual.get(key)

        # Special handling for "error": True means we expect an error string
        if key == "error" and expected_val is True:
            if not actual_val:
                failures.append(f"  {key}: expected an error, got None")
            continue

        # None means "should be set to something, value varies by current date"
        if expected_val is None:
            if actual_val is None:
                failures.append(f"  {key}: expected a value, got None")
            continue

        # Date fields get fuzzy matching in approximate categories
        if key in ("departure_date", "return_date") and isinstance(expected_val, str):
            if actual_val is None:
                failures.append(f"  {key}: expected {expected_val}, got None")
            elif not _dates_match(expected_val, actual_val, fuzzy=fuzzy):
                failures.append(f"  {key}: expected {expected_val}, got {actual_val}")
            continue

        # Boolean and int fields: exact match
        if actual_val != expected_val:
            failures.append(f"  {key}: expected {expected_val}, got {actual_val}")

    return (len(failures) == 0, failures)


async def _run_single_test(
    text: str, destination: str | None, expected: dict, fuzzy: bool = False
) -> dict:
    """Run a single date parsing test case."""
    from app.ai.graph.tools.dates import _parse_dates_with_llm, _validate_parsed_dates

    start = time.monotonic()
    try:
        raw = await asyncio.wait_for(
            _parse_dates_with_llm(
                text, reference_date=REFERENCE_DATE, destination=destination
            ),
            timeout=60,
        )
        result = _validate_parsed_dates(raw)
        elapsed = time.monotonic() - start
        passed, failures = _check_result(expected, result, fuzzy=fuzzy)
        return {
            "input": text,
            "destination": destination,
            "expected": expected,
            "actual": result,
            "passed": passed,
            "failures": failures,
            "elapsed_s": round(elapsed, 2),
            "error": None,
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "input": text,
            "destination": destination,
            "expected": expected,
            "actual": None,
            "passed": False,
            "failures": [f"  Exception: {e}"],
            "elapsed_s": round(elapsed, 2),
            "error": str(e),
        }


async def run_category(category: str, cases: list) -> dict:
    """Run all test cases in a category sequentially."""
    fuzzy = category in FUZZY_CATEGORIES
    results = []
    for text, destination, expected in cases:
        r = await _run_single_test(text, destination, expected, fuzzy=fuzzy)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"  [{status}] {text!r}" + (f" (dest={destination})" if destination else "")
        )
        if not r["passed"]:
            for f in r["failures"]:
                print(f"    {f}")
    passed = sum(1 for r in results if r["passed"])
    return {
        "category": category,
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": round(passed / len(cases) * 100, 1) if cases else 0,
        "results": results,
    }


async def run_all_categories() -> dict:
    """Run all categories and produce a summary report."""
    print(f"\n{'=' * 70}")
    print(f"  DATE PARSING BENCHMARK — {TOTAL_TEST_CASES} test cases")
    print(f"  Reference date: {REFERENCE_DATE}")
    print(f"{'=' * 70}\n")

    all_results = {}
    total_passed = 0
    total_failed = 0
    start = time.monotonic()

    for category, cases in ALL_TEST_CASES.items():
        print(f"\n--- {category.upper()} ({len(cases)} cases) ---")
        cat_result = await run_category(category, cases)
        all_results[category] = cat_result
        total_passed += cat_result["passed"]
        total_failed += cat_result["failed"]

    elapsed = time.monotonic() - start
    total = total_passed + total_failed

    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total:  {total}")
    print(f"  Passed: {total_passed} ({round(total_passed / total * 100, 1)}%)")
    print(f"  Failed: {total_failed} ({round(total_failed / total * 100, 1)}%)")
    print(f"  Time:   {round(elapsed, 1)}s")
    print()
    print(f"  {'Category':<25} {'Pass':>5} {'Fail':>5} {'Rate':>7}")
    print(f"  {'-' * 25} {'-' * 5} {'-' * 5} {'-' * 7}")
    for cat, res in all_results.items():
        print(
            f"  {cat:<25} {res['passed']:>5} {res['failed']:>5} {res['pass_rate']:>6}%"
        )
    print(f"{'=' * 70}\n")

    return {
        "reference_date": REFERENCE_DATE,
        "total": total,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": round(total_passed / total * 100, 1) if total else 0,
        "elapsed_s": round(elapsed, 1),
        "categories": all_results,
    }


# ---------------------------------------------------------------------------
# Pytest parametrized tests (one test per category)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("category", list(ALL_TEST_CASES.keys()))
async def test_date_parsing_category(category: str):
    """Run date parsing benchmark for a single category."""
    cases = ALL_TEST_CASES[category]
    result = await run_category(category, cases)

    # Report failures in pytest output
    if result["failed"] > 0:
        failed_cases = [r for r in result["results"] if not r["passed"]]
        failure_report = f"\n{category}: {result['failed']}/{result['total']} failed:\n"
        for fc in failed_cases:
            failure_report += f"  Input: {fc['input']!r}\n"
            for f in fc["failures"]:
                failure_report += f"    {f}\n"
        # Don't assert — this is a benchmark, not a strict pass/fail test.
        # Log failures but let the suite complete so we get the full picture.
        print(failure_report)

    # Store result for reporting
    print(
        f"\n{category}: {result['passed']}/{result['total']} passed ({result['pass_rate']}%)"
    )


# ---------------------------------------------------------------------------
# Standalone runner (python -m ...)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Add backend_python to path
    backend_dir = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(backend_dir))

    logging.basicConfig(level=logging.WARNING)

    report = asyncio.run(run_all_categories())

    # Save JSON report
    report_path = Path(__file__).parent / "date_parsing_benchmark_report.json"
    # Strip full result details for concise JSON
    summary = {
        "reference_date": report["reference_date"],
        "total": report["total"],
        "passed": report["passed"],
        "failed": report["failed"],
        "pass_rate": report["pass_rate"],
        "elapsed_s": report["elapsed_s"],
        "categories": {
            cat: {
                "total": data["total"],
                "passed": data["passed"],
                "failed": data["failed"],
                "pass_rate": data["pass_rate"],
                "failed_cases": [
                    {
                        "input": r["input"],
                        "destination": r["destination"],
                        "expected": r["expected"],
                        "actual": {
                            k: v
                            for k, v in (r["actual"] or {}).items()
                            if k
                            in (
                                "departure_date",
                                "return_date",
                                "is_range",
                                "trip_duration_days",
                                "error",
                                "is_departure_window",
                                "departure_window_start",
                                "departure_window_end",
                            )
                        },
                        "failures": r["failures"],
                    }
                    for r in data["results"]
                    if not r["passed"]
                ],
            }
            for cat, data in report["categories"].items()
        },
    }
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Report saved to: {report_path}")
