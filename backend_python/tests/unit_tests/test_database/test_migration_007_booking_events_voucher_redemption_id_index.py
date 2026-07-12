"""Migration 007: sparse index on booking_events.voucher_redemption_id."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "007_booking_events_voucher_redemption_id_index.py"
)


def _load_migration_007():
    spec = importlib.util.spec_from_file_location(
        "migration_007_booking_events_voucher_redemption_id_index", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 007_booking_events_voucher_redemption_id_index")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_007_up_creates_sparse_index() -> None:
    m007 = _load_migration_007()
    coll = MagicMock()
    coll.create_index = AsyncMock()

    db = MagicMock()
    db.__getitem__.return_value = coll

    await m007.up(db)

    coll.create_index.assert_awaited_once()
    c = coll.create_index.await_args
    assert c.args[0] == [("voucher_redemption_id", 1)]
    assert c.kwargs.get("name") == m007.INDEX_NAME
    assert c.kwargs.get("sparse") is True
    assert c.kwargs.get("background") is True


@pytest.mark.asyncio
async def test_007_down_drops_index() -> None:
    m007 = _load_migration_007()
    coll = MagicMock()
    coll.drop_index = AsyncMock()
    db = MagicMock()
    db.__getitem__.return_value = coll

    await m007.down(db)

    coll.drop_index.assert_awaited_once_with(m007.INDEX_NAME)
