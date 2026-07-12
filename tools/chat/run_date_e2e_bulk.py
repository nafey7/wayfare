#!/usr/bin/env python3
"""Bulk E2E date parsing test through live chat agents.

Takes ALL date expressions from the benchmark dataset, wraps each into a
complete agent prompt (flight/hotel/itinerary), sends through the chat API,
and checks whether the agent successfully parsed the dates (search results
or valid conversation response vs. error/hang).

Usage:
    python run_date_e2e_bulk.py --env local
    python run_date_e2e_bulk.py --env local --category holidays
    python run_date_e2e_bulk.py --env local --agent flight
"""

import argparse
import json
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend_python"))

from tests.unit_tests.test_ai.test_graph.date_parsing_test_dataset import (  # noqa: E402
    ALL_TEST_CASES,
)

ENV_URLS = {
    "local": "http://localhost:8000",
    "staging": "https://staging.myvoya.ai",
}

# Templates that provide ALL required fields so the agent goes straight to search
FLIGHT_TEMPLATES = [
    "Round trip flights from London to Paris {date_expr}, 2 adults",
    "Flights from New York to Tokyo {date_expr}, 1 adult",
    "One way flight from Berlin to Barcelona {date_expr}, 2 adults",
]

HOTEL_TEMPLATES = [
    "Hotels in Paris {date_expr}, 2 adults",
    "Hotels in London {date_expr}, 2 adults 1 room",
    "Hotels in Barcelona {date_expr}, 1 adult",
]

ITINERARY_TEMPLATES = [
    "Plan a trip to Rome {date_expr} for 2 adults",
    "Plan a trip to Tokyo {date_expr} for 2 adults",
]

# Categories best tested through each agent
HOTEL_CATEGORIES = {"hotel_patterns", "night_count_no_start", "return_focused"}
ITINERARY_CATEGORIES = {"seasons", "regional_seasons"}
# Everything else goes through flight agent

# Response types that indicate successful date parsing
SUCCESS_TYPES = {
    "flight_search_results", "flight_conversation", "flight_date_range_results",
    "hotel_search_results", "hotel_conversation",
    "itinerary_results", "itinerary_conversation", "ai_response", "message",
    "create_itinerary", "planning_complete",
}

# Cases that are expected to fail (error cases, context-dependent, etc.)
EXPECTED_ERRORS = {
    "yes those dates", "that works", "confirmed", "sounds good", "perfect", "yes",
    "one week earlier", "actually make it the 15th",
    "February 30", "April 31", "last week",
    "a week after my arrival", "the night before departure", "3 days before the wedding",
    "no specific date yet", "haven't decided yet", "not sure about dates",
    "no wait, the week after", "sorry, the 15th not the 16th",
    "reading week",
}


def login(base_url: str, email: str = "testuser@example.com",
          password: str = "Test123!") -> str:  # noqa: S107
    """Login and return JWT token."""
    data = json.dumps({"email": email, "password": password}).encode()
    req = Request(f"{base_url}/api/auth/login", data=data,
                  headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=15)
    body = json.loads(resp.read())
    return body["access_token"]


def send_message(base_url: str, token: str, message: str,
                 chat_id: str | None = None) -> dict:
    """Send a chat message and return the response."""
    payload = {"message": message}
    if chat_id:
        payload["chat_id"] = chat_id
    data = json.dumps(payload).encode()
    req = Request(f"{base_url}/api/chat/message", data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    })
    resp = urlopen(req, timeout=120)
    return json.loads(resp.read())


def build_prompt(date_expr: str, destination: str | None, category: str) -> str:
    """Build a complete agent prompt from a date expression."""
    # Use destination from test case if provided
    dest = destination or "Paris"

    if category in HOTEL_CATEGORIES:
        template = random.choice(HOTEL_TEMPLATES)  # noqa: S311
        # For hotel, use destination from test if available
        prompt = template.replace("Paris", dest).replace("London", dest).replace("Barcelona", dest)
    elif category in ITINERARY_CATEGORIES:
        template = random.choice(ITINERARY_TEMPLATES)  # noqa: S311
        prompt = template.replace("Rome", dest).replace("Tokyo", dest)
    else:
        template = random.choice(FLIGHT_TEMPLATES)  # noqa: S311
        # Keep origin, swap destination
        if dest != "Paris":
            prompt = template.replace("Paris", dest).replace("Tokyo", dest).replace("Barcelona", dest)
        else:
            prompt = template

    return prompt.replace("{date_expr}", date_expr)


def main():
    parser = argparse.ArgumentParser(description="Bulk E2E date parsing test")
    parser.add_argument("--env", default="local", choices=["local", "staging"])
    parser.add_argument("--category", help="Run only this category")
    parser.add_argument("--agent", choices=["flight", "hotel", "itinerary"],
                        help="Force all tests through one agent type")
    parser.add_argument("--limit", type=int, help="Max tests to run")
    args = parser.parse_args()

    base_url = ENV_URLS[args.env]
    print(f"Logging in to {args.env} ({base_url})...")
    token = login(base_url)
    print("Logged in as testuser@example.com\n")

    # Collect test cases
    cases = []
    for cat_name, cat_cases in ALL_TEST_CASES.items():
        if args.category and cat_name != args.category:
            continue
        for text, dest, expected in cat_cases:
            # Skip cases that are expected to error (no date to parse)
            if text in EXPECTED_ERRORS:
                continue
            if expected.get("error") is True:
                continue
            cases.append((cat_name, text, dest, expected))

    if args.limit:
        cases = cases[:args.limit]

    total = len(cases)
    print(f"Running {total} date expressions through chat agents\n")
    print("=" * 70)

    passed = 0
    failed = 0
    errors = []
    category_stats: dict[str, dict] = {}

    for _i, (cat, text, dest, _expected) in enumerate(cases):
        # Build prompt based on agent type
        if args.agent == "hotel":
            effective_cat = "hotel_patterns"
        elif args.agent == "itinerary":
            effective_cat = "seasons"
        elif args.agent == "flight":
            effective_cat = "standard_formats"
        else:
            effective_cat = cat

        prompt = build_prompt(text, dest, effective_cat)

        # Track per-category stats
        if cat not in category_stats:
            category_stats[cat] = {"passed": 0, "failed": 0, "total": 0}
        category_stats[cat]["total"] += 1

        try:
            start = time.monotonic()
            resp = send_message(base_url, token, prompt)
            elapsed = time.monotonic() - start

            resp_type = resp.get("type", "unknown")
            resp_msg = resp.get("message", "")[:100]

            # Check success: got a valid response type (not a generic error)
            is_success = resp_type in SUCCESS_TYPES

            if is_success:
                passed += 1
                category_stats[cat]["passed"] += 1
                status = "\033[32mPASS\033[0m"
            else:
                failed += 1
                category_stats[cat]["failed"] += 1
                status = "\033[31mFAIL\033[0m"
                errors.append({
                    "category": cat,
                    "input": text,
                    "prompt": prompt,
                    "response_type": resp_type,
                    "message": resp_msg,
                })

            dest_str = f" (dest={dest})" if dest else ""
            print(f"  [{status}] [{cat}] '{text}'{dest_str} -> {resp_type} ({elapsed:.1f}s)")

        except Exception as e:
            failed += 1
            category_stats[cat]["failed"] += 1
            print(f"  [\033[31mERROR\033[0m] [{cat}] '{text}' -> {e}")
            errors.append({
                "category": cat,
                "input": text,
                "prompt": prompt,
                "error": str(e),
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total:  {total}")
    print(f"  Passed: {passed} ({100*passed/total:.1f}%)")
    print(f"  Failed: {failed} ({100*failed/total:.1f}%)")
    print()
    print(f"  {'Category':<30} {'Pass':>5} {'Fail':>5} {'Rate':>7}")
    print(f"  {'-'*30} {'-'*5} {'-'*5} {'-'*7}")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        rate = 100 * s["passed"] / s["total"] if s["total"] else 0
        print(f"  {cat:<30} {s['passed']:>5} {s['failed']:>5} {rate:>6.1f}%")

    if errors:
        print(f"\nFailed cases ({len(errors)}):")
        for e in errors:
            print(f"  [{e['category']}] '{e['input']}' -> {e.get('response_type', e.get('error', '?'))}")

    # Save report
    report_dir = SCRIPT_DIR / "scenario_results"
    report_dir.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"date_e2e_bulk_{args.env}_{ts}.json"
    report = {
        "env": args.env,
        "timestamp": ts,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(100 * passed / total, 1) if total else 0,
        "category_stats": category_stats,
        "failures": errors,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
