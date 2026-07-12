"""Migration 005: chats_python (chat_id, status) index."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "005_chats_python_chat_id_status_index.py"
)


def _load_migration_005():
    spec = importlib.util.spec_from_file_location(
        "migration_005_chats_python_chat_id_status_index", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 005_chats_python_chat_id_status_index")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_005_up_creates_index_with_expected_keys() -> None:
    """up() calls create_index with (chat_id, status) and fixed name."""
    m005 = _load_migration_005()
    coll = MagicMock()
    coll.create_index = AsyncMock()

    db = MagicMock()

    def getitem(name: str) -> MagicMock:
        if name == m005.CHATS_PYTHON_COLLECTION:
            return coll
        return MagicMock()

    db.__getitem__.side_effect = getitem

    await m005.up(db)

    coll.create_index.assert_awaited_once()
    args, kwargs = coll.create_index.call_args
    assert args[0] == [("chat_id", 1), ("status", 1)]
    assert kwargs.get("name") == m005.INDEX_NAME
