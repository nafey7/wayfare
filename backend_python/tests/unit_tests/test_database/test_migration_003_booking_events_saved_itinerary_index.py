"""Unit tests for migration 003_booking_events_saved_itinerary_index."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.errors import OperationFailure

from app.database.constants import BOOKING_EVENT_COLLECTION

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION_PATH = (
    _BACKEND_ROOT
    / "app"
    / "database"
    / "migrations"
    / "003_booking_events_saved_itinerary_index.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_003_saved_itinerary", _MIGRATION_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_migration_003_saved_itinerary_up_creates_named_index() -> None:
    """up() creates compound index on booking_events with expected name."""
    mod = _load_migration()
    mock_coll = AsyncMock()
    mock_coll.create_index = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.up(mock_db)

    mock_db.__getitem__.assert_called_with(BOOKING_EVENT_COLLECTION)
    mock_coll.create_index.assert_awaited_once()
    call = mock_coll.create_index.await_args
    assert call.args[0] == [("user_id", 1), ("saved_itinerary_id", 1)]
    assert call.kwargs["name"] == mod.INDEX_NAME


@pytest.mark.asyncio
async def test_migration_003_saved_itinerary_down_drops_index() -> None:
    """down() drops the migration index by name."""
    mod = _load_migration()
    mock_coll = AsyncMock()
    mock_coll.drop_index = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.down(mock_db)

    mock_coll.drop_index.assert_awaited_once_with(mod.INDEX_NAME)


@pytest.mark.asyncio
async def test_migration_003_saved_itinerary_down_swallows_opfailure_27() -> None:
    """down() ignores OperationFailure when index is already absent (MongoDB code 27)."""
    mod = _load_migration()
    mock_coll = AsyncMock()
    mock_coll.drop_index = AsyncMock(
        side_effect=OperationFailure("index not found", code=27)
    )
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.down(mock_db)

    mock_coll.drop_index.assert_awaited_once_with(mod.INDEX_NAME)
