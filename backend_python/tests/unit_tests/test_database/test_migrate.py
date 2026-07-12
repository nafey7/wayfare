"""Unit tests for the MongoDB migration runner."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import DuplicateKeyError

from app.database.migrate import (
    MIGRATION_FILE_PATTERN,
    _acquire_migration_lock,
    _discover_migration_files,
    _get_applied_names,
    run_migrations,
)

# ==============================================================================
# Migration file pattern
# ==============================================================================


@pytest.mark.parametrize(
    ("name", "matches"),
    [
        ("001_add_field", True),
        ("002_set_myvoya_admin_role", True),
        ("20260224_001_description", True),
        ("123_add_field", True),
        ("invalid", False),
        ("no_number", False),
        ("001", False),
    ],
)
def test_migration_file_pattern(name: str, matches: bool) -> None:
    """Migration filename pattern matches expected stems (without .py)."""
    result = bool(MIGRATION_FILE_PATTERN.match(name))
    assert result == matches


# ==============================================================================
# Discovery
# ==============================================================================


def test_discover_migration_files_empty_dir(tmp_path: Path) -> None:
    """Empty migrations dir returns no files."""
    with patch("app.database.migrate._migrations_dir", return_value=tmp_path):
        found = _discover_migration_files()
    assert found == []


def test_discover_migration_files_orders_by_sequence(tmp_path: Path) -> None:
    """Migration files are ordered by sequence number."""
    (tmp_path / "002_second.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )
    (tmp_path / "001_first.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )
    (tmp_path / "003_third.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )
    with patch("app.database.migrate._migrations_dir", return_value=tmp_path):
        found = _discover_migration_files()
    names = [n for n, _ in found]
    assert names == ["001_first", "002_second", "003_third"]


def test_discover_migration_files_ignores_non_matching(tmp_path: Path) -> None:
    """Non-matching files are ignored."""
    (tmp_path / "001_valid.py").write_text("async def up(db): pass")
    (tmp_path / "invalid.py").write_text("# ignored")
    (tmp_path / "_private.py").write_text("# ignored")
    (tmp_path / "readme.txt").write_text("ignored")
    with patch("app.database.migrate._migrations_dir", return_value=tmp_path):
        found = _discover_migration_files()
    assert len(found) == 1
    assert found[0][0] == "001_valid"


# ==============================================================================
# _acquire_migration_lock
# ==============================================================================


@pytest.mark.asyncio
async def test_acquire_migration_lock_duplicate_key_returns_false() -> None:
    """When find_one_and_update raises DuplicateKeyError (lock held), returns False."""
    mock_lock_coll = AsyncMock()
    mock_lock_coll.create_index = AsyncMock()
    mock_lock_coll.find_one_and_update = AsyncMock(
        side_effect=DuplicateKeyError("duplicate key", code=11000, details={})
    )
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_lock_coll)

    result = await _acquire_migration_lock(mock_db)

    assert result is False


# ==============================================================================
# Applied names
# ==============================================================================


@pytest.mark.asyncio
async def test_get_applied_names() -> None:
    """Applied migrations are returned as a set."""
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = iter(
        [{"_id": "001_first"}, {"_id": "002_second"}]
    )
    mock_coll = AsyncMock()
    mock_coll.find = MagicMock(return_value=mock_cursor)
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    result = await _get_applied_names(mock_db)

    assert result == {"001_first", "002_second"}


# ==============================================================================
# run_migrations
# ==============================================================================


@pytest.mark.asyncio
async def test_run_migrations_no_pending(tmp_path: Path) -> None:
    """When all migrations are applied, returns 0 without running."""
    (tmp_path / "001_applied.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )

    async def mock_applied(*args: object, **kwargs: object) -> set[str]:
        return {"001_applied"}

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch("app.database.migrate._get_applied_names", side_effect=mock_applied),
    ):
        mock_db = MagicMock()
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=False)

    assert exit_code == 0


@pytest.mark.asyncio
async def test_run_migrations_dry_run(tmp_path: Path) -> None:
    """Dry run lists pending migrations without executing."""
    (tmp_path / "001_pending.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch(
            "app.database.migrate._get_applied_names", new=AsyncMock(return_value=set())
        ),
        patch("app.database.migrate._load_migration_module") as mock_load,
    ):
        mock_db = MagicMock()
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=True)

    assert exit_code == 0
    mock_load.assert_not_called()


@pytest.mark.asyncio
async def test_run_migrations_executes_and_records(tmp_path: Path) -> None:
    """Pending migration is executed and recorded on success."""
    (tmp_path / "001_test.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )

    mock_migrations = MagicMock()
    mock_migrations.insert_one = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = (
        lambda self, name: mock_migrations if name == "_migrations" else MagicMock()
    )

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch(
            "app.database.migrate._get_applied_names", new=AsyncMock(return_value=set())
        ),
        patch(
            "app.database.migrate._acquire_migration_lock",
            new=AsyncMock(return_value=True),
        ),
        patch("app.database.migrate._release_migration_lock", new=AsyncMock()),
    ):
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=False)

    assert exit_code == 0
    mock_migrations.insert_one.assert_called_once()
    call_args = mock_migrations.insert_one.call_args[0][0]
    assert call_args["_id"] == "001_test"
    assert "applied_at" in call_args


@pytest.mark.asyncio
async def test_run_migrations_fails_on_error(tmp_path: Path) -> None:
    """Migration failure returns 1 and does not record."""
    (tmp_path / "001_fail.py").write_text(
        "async def up(db): raise RuntimeError('boom')\nasync def down(db): pass"
    )

    mock_migrations = MagicMock()
    mock_migrations.insert_one = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = (
        lambda self, name: mock_migrations if name == "_migrations" else MagicMock()
    )

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch(
            "app.database.migrate._get_applied_names", new=AsyncMock(return_value=set())
        ),
        patch(
            "app.database.migrate._acquire_migration_lock",
            new=AsyncMock(return_value=True),
        ),
        patch("app.database.migrate._release_migration_lock", new=AsyncMock()),
    ):
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=False)

    assert exit_code == 1
    mock_migrations.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_run_migrations_lock_held_returns_1(tmp_path: Path) -> None:
    """When another runner holds the lock, returns 1 without loading or executing."""
    (tmp_path / "001_pending.py").write_text(
        "async def up(db): pass\nasync def down(db): pass"
    )

    mock_migrations = MagicMock()
    mock_migrations.insert_one = AsyncMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = (
        lambda self, name: mock_migrations if name == "_migrations" else MagicMock()
    )

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch(
            "app.database.migrate._get_applied_names", new=AsyncMock(return_value=set())
        ),
        patch(
            "app.database.migrate._acquire_migration_lock",
            new=AsyncMock(return_value=False),
        ),
        patch("app.database.migrate._load_migration_module") as mock_load,
    ):
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=False)

    assert exit_code == 1
    mock_load.assert_not_called()
    mock_migrations.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_run_migrations_no_up_function_fails(tmp_path: Path) -> None:
    """Migration without up() function returns 1."""
    (tmp_path / "001_no_up.py").write_text("async def down(db): pass")

    mock_db = MagicMock()

    with (
        patch("app.database.migrate.connect_to_mongodb", new=AsyncMock()),
        patch("app.database.migrate.disconnect_from_mongodb", new=AsyncMock()),
        patch("app.database.migrate.get_connection") as mock_get_conn,
        patch("app.database.migrate._migrations_dir", return_value=tmp_path),
        patch(
            "app.database.migrate._get_applied_names", new=AsyncMock(return_value=set())
        ),
        patch(
            "app.database.migrate._acquire_migration_lock",
            new=AsyncMock(return_value=True),
        ),
        patch("app.database.migrate._release_migration_lock", new=AsyncMock()),
    ):
        mock_get_conn.return_value.get_database.return_value = mock_db
        exit_code = await run_migrations(dry_run=False)

    assert exit_code == 1
