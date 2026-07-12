"""Unit tests for migration 008_set_myvoya_admin_role."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.constants import USERS_COLLECTION

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION_PATH = (
    _BACKEND_ROOT / "app" / "database" / "migrations" / "008_set_myvoya_admin_role.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_008_myvoya_admin", _MIGRATION_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _assert_update_many_filter(mock_coll, mod) -> None:
    """Filter must exclude admin/super_admin and match @myvoya.ai (see up())."""
    call = mock_coll.update_many.await_args
    find_filter = call.args[0]
    assert find_filter["email"] == {
        "$regex": mod.MYVOYA_EMAIL_REGEX,
        "$options": "i",
    }
    assert set(find_filter["role"]["$nin"]) == {"admin", "super_admin"}


@pytest.mark.asyncio
async def test_migration_008_up_sets_admin_for_myvoya_non_admin_users() -> None:
    """up() uses update_many with regex + $nin, sets role and updated_at."""
    mod = _load_migration()

    mock_coll = AsyncMock()
    mock_coll.update_many = AsyncMock(return_value=MagicMock(modified_count=2))
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.up(mock_db)

    mock_db.__getitem__.assert_called_with(USERS_COLLECTION)
    mock_coll.update_many.assert_awaited_once()
    _assert_update_many_filter(mock_coll, mod)

    call = mock_coll.update_many.await_args
    assert call.args[1]["$set"]["role"] == "admin"
    assert "updated_at" in call.args[1]["$set"]
    assert "updatedAt" not in call.args[1]["$set"]


@pytest.mark.asyncio
async def test_migration_008_up_skips_existing_admin_users() -> None:
    """up() when modified_count=0: proves filter shape is unchanged, not real DB $nin.

    MongoDB would exclude admin rows; this test only checks we still run update_many
    with the same regex + $nin (mock returns zero to simulate no documents matched).
    """
    mod = _load_migration()

    mock_coll = AsyncMock()
    mock_coll.update_many = AsyncMock(return_value=MagicMock(modified_count=0))
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    await mod.up(mock_db)

    mock_coll.update_many.assert_awaited_once()
    _assert_update_many_filter(mock_coll, mod)


@pytest.mark.asyncio
async def test_migration_008_down_is_noop() -> None:
    """down() should be a no-op and not raise."""
    mod = _load_migration()
    mock_db = MagicMock()
    await mod.down(mock_db)
    mock_db.__getitem__.assert_not_called()
