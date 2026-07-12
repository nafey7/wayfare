"""Migration 004: saved_itineraries indexes are idempotent and match repository helpers."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.errors import OperationFailure

from app.database.constants import SAVED_ITINERARIES_COLLECTION

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "004_saved_itineraries_indexes.py"
)


def _load_migration_004():
    spec = importlib.util.spec_from_file_location(
        "migration_004_saved_itineraries_indexes", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 004_saved_itineraries_indexes")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_004_up_creates_indexes_with_stable_names() -> None:
    """up() calls create_index twice with expected names (idempotent)."""
    m004 = _load_migration_004()
    coll = MagicMock()
    coll.create_index = AsyncMock()

    db = MagicMock()

    def getitem(name: str) -> MagicMock:
        if name == SAVED_ITINERARIES_COLLECTION:
            return coll
        return MagicMock()

    db.__getitem__.side_effect = getitem

    await m004.up(db)

    assert coll.create_index.await_count == 2
    awaited = coll.create_index.await_args_list

    assert awaited[0].args[0] == [("user_id", 1), ("created_at", -1)]
    assert awaited[0].kwargs == {"name": m004.INDEX_NAME_USER_CREATED}

    assert awaited[1].args[0] == [("user_id", 1), ("chat_id", 1)]
    assert awaited[1].kwargs == {
        "name": m004.INDEX_NAME_USER_CHAT_UNIQUE,
        "unique": True,
        "partialFilterExpression": {"chat_id": {"$type": "string"}},
    }


@pytest.mark.asyncio
async def test_004_down_drops_indexes_in_order() -> None:
    """down() drops uniq then user_created index names (success path)."""
    m004 = _load_migration_004()
    coll = AsyncMock()
    coll.drop_index = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    await m004.down(db)

    db.__getitem__.assert_called_with(SAVED_ITINERARIES_COLLECTION)
    assert coll.drop_index.await_count == 2
    assert coll.drop_index.await_args_list[0].args == (
        m004.INDEX_NAME_USER_CHAT_UNIQUE,
    )
    assert coll.drop_index.await_args_list[1].args == (m004.INDEX_NAME_USER_CREATED,)


@pytest.mark.asyncio
async def test_004_down_swallows_opfailure_27() -> None:
    """down() ignores OperationFailure when indexes are already absent (code 27)."""
    m004 = _load_migration_004()
    coll = AsyncMock()
    coll.drop_index = AsyncMock(
        side_effect=[
            OperationFailure("index not found", code=27),
            OperationFailure("index not found", code=27),
        ]
    )
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    await m004.down(db)

    assert coll.drop_index.await_count == 2
    assert coll.drop_index.await_args_list[0].args == (
        m004.INDEX_NAME_USER_CHAT_UNIQUE,
    )
    assert coll.drop_index.await_args_list[1].args == (m004.INDEX_NAME_USER_CREATED,)
