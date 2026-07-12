"""Migration 006: discounts collection indexes."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "006_discounts_collection_indexes.py"
)


def _load_migration_006():
    spec = importlib.util.spec_from_file_location(
        "migration_006_discounts_collection_indexes", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 006_discounts_collection_indexes")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_006_up_creates_all_indexes() -> None:
    m006 = _load_migration_006()
    coll = MagicMock()
    coll.create_index = AsyncMock()

    db = MagicMock()

    def getitem(name: str) -> MagicMock:
        if name == m006.DISCOUNTS_COLLECTION:
            return coll
        return MagicMock()

    db.__getitem__.side_effect = getitem

    await m006.up(db)

    assert coll.create_index.await_count == 4
    by_name = {
        c.kwargs.get("name"): (c.args[0], c.kwargs)
        for c in coll.create_index.await_args_list
    }
    assert by_name[m006.IDX_CODE_UNIQUE][0] == [("code", 1)]
    assert by_name[m006.IDX_CODE_UNIQUE][1].get("unique") is True

    assert by_name[m006.IDX_BATCH_STATUS][0] == [("batch_id", 1), ("status", 1)]
    assert by_name[m006.IDX_STATUS_RESERVATION_EXPIRES][0] == [
        ("status", 1),
        ("reservation_expires_at", 1),
    ]
    assert by_name[m006.IDX_USER_ID_SPARSE][0] == [("user_id", 1)]
    assert by_name[m006.IDX_USER_ID_SPARSE][1].get("sparse") is True


@pytest.mark.asyncio
async def test_006_down_drops_indexes_idempotent() -> None:
    m006 = _load_migration_006()
    coll = MagicMock()
    coll.drop_index = AsyncMock()

    db = MagicMock()

    def getitem(name: str) -> MagicMock:
        if name == m006.DISCOUNTS_COLLECTION:
            return coll
        return MagicMock()

    db.__getitem__.side_effect = getitem

    await m006.down(db)

    dropped = {c.args[0] for c in coll.drop_index.await_args_list}
    assert dropped == {
        m006.IDX_USER_ID_SPARSE,
        m006.IDX_STATUS_RESERVATION_EXPIRES,
        m006.IDX_BATCH_STATUS,
        m006.IDX_CODE_UNIQUE,
    }
