"""Configuration for unit tests - no database needed."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Import flight fixtures to make them available


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock database for unit tests."""
    db = MagicMock()
    db.users = AsyncMock()
    db.sessions = AsyncMock()
    return db


@pytest.fixture
def mock_settings(monkeypatch: Any) -> Callable[[str, Any], None]:
    """Mock settings for testing."""

    def _mock_setting(key: str, value: Any) -> None:
        monkeypatch.setattr(f"app.core.config.settings.{key}", value)

    return _mock_setting


@pytest.fixture
def client() -> TestClient:
    """Create test client for API testing."""
    from app.main import app

    return TestClient(app)
