"""Migration 009: compound index on booking_events for multi-stay group lookups."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "009_booking_events_multistay_parent_ref_index.py"
)


def _load_migration_009():
    spec = importlib.util.spec_from_file_location(
        "migration_009_booking_events_multistay_parent_ref_index", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 009_booking_events_multistay_parent_ref_index")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_009_up_creates_compound_index() -> None:
    m009 = _load_migration_009()
    coll = MagicMock()
    coll.create_index = AsyncMock()

    db = MagicMock()
    db.__getitem__.return_value = coll

    await m009.up(db)

    coll.create_index.assert_awaited_once()
    c = coll.create_index.await_args
    assert c.args[0] == [
        ("user_id", 1),
        ("event_type", 1),
        ("parent_voya_booking_reference", 1),
        ("timestamp", 1),
    ]
    assert c.kwargs.get("name") == m009.INDEX_NAME
    assert c.kwargs.get("sparse") is True
    assert c.kwargs.get("background") is True


@pytest.mark.asyncio
async def test_009_down_drops_index() -> None:
    m009 = _load_migration_009()
    coll = MagicMock()
    coll.drop_index = AsyncMock()
    db = MagicMock()
    db.__getitem__.return_value = coll

    await m009.down(db)

    coll.drop_index.assert_awaited_once_with(m009.INDEX_NAME)
