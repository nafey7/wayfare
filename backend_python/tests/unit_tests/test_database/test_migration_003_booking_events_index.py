"""Unit tests for migration 003_booking_events_ticket_time_limit_alert_index."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION_PATH = (
    _BACKEND_ROOT
    / "app"
    / "database"
    / "migrations"
    / "003_booking_events_ticket_time_limit_alert_index.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_003", _MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_migration_003_up_creates_named_index() -> None:
    """up() creates compound index on booking_events with expected name."""
    mod = _load_migration()
    mock_coll = AsyncMock()
    mock_coll.create_index = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.up(mock_db)

    mock_db.__getitem__.assert_called_with("booking_events")
    mock_coll.create_index.assert_awaited_once()
    call_kw = mock_coll.create_index.await_args
    assert call_kw[1]["name"] == mod.INDEX_NAME


@pytest.mark.asyncio
async def test_migration_003_down_drops_index() -> None:
    """down() drops the migration index by name."""
    mod = _load_migration()
    mock_coll = AsyncMock()
    mock_coll.drop_index = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.down(mock_db)

    mock_coll.drop_index.assert_awaited_once_with(mod.INDEX_NAME)
