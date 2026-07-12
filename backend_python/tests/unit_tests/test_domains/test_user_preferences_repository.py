"""Unit tests for user preferences repository."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.user_preferences.repository import get_preferences, upsert_preferences


@pytest.mark.asyncio
async def test_get_preferences_returns_document_exists_false_when_no_doc():
    """get_preferences returns document_exists=False when no MongoDB document exists."""
    mock_coll = AsyncMock()
    mock_coll.find_one.return_value = None
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with patch(
        "app.domains.user_preferences.repository.get_database",
        new=AsyncMock(return_value=mock_db),
    ):
        result = await get_preferences(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
        )

    assert result.document_exists is False
    assert result.flights.seat_preference is None
    assert result.flights.preferred_airlines == []


@pytest.mark.asyncio
async def test_upsert_preferences_creates_document_when_none_exists():
    """Upsert creates document when no MongoDB document exists (find_one returns None)."""
    mock_coll = AsyncMock()
    mock_coll.find_one.return_value = None  # No existing document
    mock_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with patch(
        "app.domains.user_preferences.repository.get_database",
        new=AsyncMock(return_value=mock_db),
    ):
        result = await upsert_preferences(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            {"flights": {"seat_preference": "window"}},
        )

    mock_coll.find_one.assert_called_once()
    mock_coll.update_one.assert_called_once()
    _, kwargs = mock_coll.update_one.await_args
    assert kwargs["upsert"] is True
    assert result.document_exists is True
    assert result.flights.seat_preference == "window"
