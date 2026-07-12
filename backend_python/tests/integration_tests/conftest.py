"""Integration test configuration and fixtures."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator

import httpx
import pytest

from app.database.connection import _db_connection as db_manager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def setup_database():
    """Set up test database connection."""
    if not db_manager._is_connected:
        await db_manager.connect()
    # Don't disconnect here as other tests might still need it


@pytest.fixture
async def http_client(setup_database) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing."""
    # When running inside Docker container, use internal service name
    # When running locally, use localhost
    import os

    if os.path.exists("/.dockerenv"):  # Running inside Docker
        base_url = "http://127.0.0.1:80"  # Internal container port
    else:
        base_url = "http://localhost:8000"  # External host port

    async with httpx.AsyncClient(
        base_url=base_url, timeout=30.0, follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
async def clean_test_users():
    """Clean up test users before and after tests."""
    test_emails = [
        "test@example.com",
        "test-user@example.com",
        "reset-test@example.com",
        "api-test@example.com",
        "e2e-test@example.com",
        "reg-token-test@example.com",
        "complete-reg-flow@example.com",
    ]

    # Ensure database is connected
    if not db_manager._is_connected:
        await db_manager.connect()

    # Clean up before test
    collection = db_manager.get_collection("users")
    await collection.delete_many({"email": {"$in": test_emails}})

    yield test_emails

    # Clean up after test - suppress any exceptions during cleanup
    with contextlib.suppress(Exception):
        await collection.delete_many({"email": {"$in": test_emails}})


class APITestHelper:
    """Helper class for API testing."""

    @staticmethod
    def assert_success_response(response: httpx.Response, expected_status: int = 200):
        """Assert successful API response."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )
        return response.json()

    @staticmethod
    def assert_error_response(
        response: httpx.Response,
        expected_status: int,
        expected_detail: str | None = None,
    ):
        """Assert error API response."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )

        if expected_detail:
            json_response = response.json()
            detail = json_response.get("detail", "").lower()
            assert expected_detail.lower() in detail, (
                f"Expected '{expected_detail}' in error detail: {json_response}"
            )

        return response.json()

    @staticmethod
    async def get_user_reset_token(email: str) -> str | None:
        """Get password reset token from database for testing."""
        collection = db_manager.get_collection("users")
        user = await collection.find_one({"email": email})
        return user.get("password_reset_token") if user else None

    @staticmethod
    async def get_user_registration_token(email: str) -> str | None:
        """Get email verification token (registration token) from database for testing."""
        collection = db_manager.get_collection("users")
        user = await collection.find_one({"email": email})
        return user.get("email_verification_token") if user else None


@pytest.fixture
def api_helper():
    """Provide API test helper."""
    return APITestHelper()
