#!/usr/bin/env python3
"""
Fast HTTP API test runner for authentication flows.

This script runs integration tests against the live API server without
needing to start the frontend. Perfect for backend development.

Usage:
    python scripts/test_auth_api.py                    # Run all auth tests
    python scripts/test_auth_api.py --verbose          # Verbose output
    python scripts/test_auth_api.py --test=reset       # Run only password reset tests
    python scripts/test_auth_api.py --test=registration # Run only registration tests
    python scripts/test_auth_api.py --test=e2e         # Run only end-to-end tests
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest(test_filter: str | None = None, verbose: bool = False):
    """Run pytest with specified filters."""
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent

    cmd = ["python", "-m", "pytest"]

    # Test file path
    test_file = "tests/integration_tests/test_auth_flows.py"

    if test_filter:
        # Map friendly names to test classes/methods
        test_filters = {
            "registration": "TestRegistrationFlow",
            "reset": "TestPasswordResetFlow",
            "login": "TestLoginFlow",
            "session": "TestSessionManagement",
            "e2e": "TestEndToEndAuthFlow",
            "config": "TestConfigEndpoints",
        }

        if test_filter in test_filters:
            test_file += f"::{test_filters[test_filter]}"
        else:
            print(f"Unknown test filter: {test_filter}")
            print(f"Available filters: {', '.join(test_filters.keys())}")
            return 1

    cmd.append(test_file)

    # Add pytest options
    cmd.extend(
        [
            "-v" if verbose else "-q",
            "--tb=short",
            "--color=yes",
            "-x",  # Stop on first failure
        ]
    )

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {backend_dir}")
    print("-" * 50)

    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=backend_dir, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 130


def check_server():
    """Check if the API server is running."""
    import httpx

    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ API server is running")
            return True
        print(f"⚠️  API server returned status {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ API server is not accessible: {e}")
        print("💡 Make sure to run 'docker compose up -d' first")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run HTTP API tests for authentication flows"
    )
    parser.add_argument(
        "--test",
        choices=["registration", "reset", "login", "session", "e2e", "config"],
        help="Run specific test category",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-check", action="store_true", help="Skip server health check"
    )

    args = parser.parse_args()

    # Check if server is running (unless skipped)
    if not args.no_check:
        if not check_server():
            return 1
        print()

    # Run tests
    return run_pytest(args.test, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
