"""Root test configuration.

This file runs BEFORE any other conftest.py files are loaded.
We use pytest_configure to set environment variables before app modules are imported.
"""

import os
import sys
import urllib.request
from unittest.mock import MagicMock

# Stub sentry_sdk so app.domains.auth.dependencies can load (not in all Docker images)
if "sentry_sdk" not in sys.modules:
    sys.modules["sentry_sdk"] = MagicMock()


def pytest_configure(config):
    """Configure mock server BEFORE any other imports.

    This hook runs very early in pytest startup, before other conftest files are loaded.
    We set environment variables here so that when app modules are imported,
    they pick up the mock server configuration.
    """
    # Only configure for integration tests in ai directory
    # Check if we're running AI integration tests
    if not _should_configure_mock(config):
        return

    # Check if mock server is available and set env vars
    _configure_mock_server_if_available()


def _should_configure_mock(config):
    """Check if we should configure the mock server based on test selection."""
    # Get the test paths being collected
    args = config.args if hasattr(config, "args") else []

    # Configure mock if running AI integration tests
    for arg in args:
        if "integration_tests/ai" in arg or "integration_tests\\ai" in arg:
            return True

    # Also configure if no specific path (running all tests)
    return not args


def _configure_mock_server_if_available():
    """Set environment variables for mock server if it's running."""
    # Check both ports: 8002 (dev compose), 8004 (test compose)
    for port in [8002, 8004]:
        url = f"http://localhost:{port}"
        try:
            req = urllib.request.Request(f"{url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    mock_api_url = f"{url}/api/aeroVE5"
                    mock_hotel_url = f"{url}/api/hotel-api-v6"
                    # Set environment variables BEFORE any app imports
                    # Must set FLIGHTS_API_BASE_URL as it takes precedence over API_URL
                    os.environ["FLIGHTLOGIC_FLIGHTS_API_BASE_URL"] = mock_api_url
                    os.environ["FLIGHTLOGIC_HOTELS_API_BASE_URL"] = mock_hotel_url
                    os.environ["FLIGHTLOGIC_API_URL"] = mock_api_url
                    os.environ["FLIGHTLOGIC_API_KEY"] = (
                        "mock-api-key-test"  # pragma: allowlist secret
                    )
                    os.environ["FLIGHTLOGIC_USER_ID"] = "test_user"
                    os.environ["FLIGHTLOGIC_PASSWORD"] = "test_password"  # noqa: S105  # pragma: allowlist secret
                    os.environ["FLIGHTLOGIC_ACCESS_TYPE"] = "Test"
                    print(f"\n✅ Mock server detected at {url}")
                    return
        except Exception:  # noqa: S112 - Expected, try next port silently
            continue
    print("\n⚠️  Mock server not running")
