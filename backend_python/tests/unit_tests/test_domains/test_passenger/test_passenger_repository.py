"""Unit tests for passenger repository update behavior."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.passenger.repository import update_passenger
from app.domains.passenger.schemas import PassengerUpdate


@pytest.mark.asyncio
async def test_update_passenger_uses_unset_for_explicit_nulls():
    """Explicit null fields are cleared via $unset."""
    mock_coll = AsyncMock()
    mock_coll.find_one.return_value = {"title": "Mr", "date_of_birth": "1990-01-15"}
    mock_coll.find_one_and_update.return_value = None
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with patch(
        "app.domains.passenger.repository.get_database",
        new=AsyncMock(return_value=mock_db),
    ):
        await update_passenger(
            "507f1f77bcf86cd799439022",  # pragma: allowlist secret
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            PassengerUpdate(email=None, passport_number=None),
        )

    assert mock_coll.find_one_and_update.await_count == 1
    _, kwargs = mock_coll.find_one_and_update.await_args
    update_doc = mock_coll.find_one_and_update.await_args.args[1]
    assert "$unset" in update_doc
    assert update_doc["$unset"]["email"] == ""
    assert update_doc["$unset"]["passport_number"] == ""
    assert "updated_at" in update_doc["$set"]
    assert kwargs["return_document"] is True


@pytest.mark.asyncio
async def test_update_passenger_encrypts_sensitive_fields():
    """Sensitive fields in $set are encrypted before writing."""
    mock_coll = AsyncMock()
    mock_coll.find_one.return_value = {"title": "Mr", "date_of_birth": "1990-01-15"}
    mock_coll.find_one_and_update.return_value = None
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with (
        patch(
            "app.domains.passenger.repository.get_database",
            new=AsyncMock(return_value=mock_db),
        ),
        patch(
            "app.domains.passenger.repository.encrypt_field",
            return_value="encrypted-value",
        ),
    ):
        await update_passenger(
            "507f1f77bcf86cd799439022",  # pragma: allowlist secret
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            PassengerUpdate(passport_number="AB1234567"),  # pragma: allowlist secret
        )

    update_doc = mock_coll.find_one_and_update.await_args.args[1]
    assert update_doc["$set"]["passport_number"] == "encrypted-value"
