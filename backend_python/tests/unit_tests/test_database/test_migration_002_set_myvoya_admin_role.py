"""Unit tests for migration 002_set_myvoya_admin_role."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.database.constants import USERS_COLLECTION

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION_PATH = (
    _BACKEND_ROOT / "app" / "database" / "migrations" / "002_set_myvoya_admin_role.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_002_myvoya_admin", _MIGRATION_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _AsyncIterator:
    """Async-iterable list for Motor cursor emulation."""

    def __init__(self, items: list) -> None:
        self._items = list(items)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._items):
            raise StopAsyncIteration
        val = self._items[self._i]
        self._i += 1
        return val


@pytest.mark.asyncio
async def test_migration_002_up_sets_admin_for_myvoya_non_admin_users() -> None:
    """up() finds only non-admin @myvoya.ai users and sets role to admin via update_one."""
    mod = _load_migration()
    user_id = ObjectId()
    doc = {"_id": user_id, "email": "team@myvoya.ai", "role": "user"}

    mock_coll = AsyncMock()
    mock_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_coll.find = MagicMock(return_value=_AsyncIterator([doc]))
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.up(mock_db)

    mock_db.__getitem__.assert_called_with(USERS_COLLECTION)
    find_filter = mock_coll.find.call_args[0][0]
    assert find_filter["email"] == {
        "$regex": mod.MYVOYA_EMAIL_REGEX,
        "$options": "i",
    }
    assert set(find_filter["role"]["$nin"]) == {"admin", "super_admin"}

    mock_coll.update_one.assert_awaited_once()
    call = mock_coll.update_one.await_args
    assert call.args[0] == {"_id": user_id}
    assert call.args[1]["$set"]["role"] == "admin"
    assert "updatedAt" in call.args[1]["$set"]
