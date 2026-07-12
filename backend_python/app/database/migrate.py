"""Lightweight async MongoDB migration runner.

Discovers migrations in app/database/migrations/, runs pending ones in order,
and records applied migrations in the _migrations collection.

Usage:
    python -m app.database.migrate [--dry-run]

Convention:
    - File names: NNN_description.py or YYYYMMDD_NNN_description.py
    - Each file must have: async def up(db) and optionally async def down(db)
    - Migrations must be idempotent (safe to run twice)
    - Do not import app.domains.* from migration modules (circular imports at load time;
      see backend_python/docs/MIGRATIONS.md "Imports in migration modules").
"""

import argparse
import importlib.util
import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.connection import (
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
)

logger = logging.getLogger(__name__)

MIGRATIONS_COLLECTION = "_migrations"
LOCK_COLLECTION = "_migration_lock"
LOCK_DOC_ID = "runner"
LOCK_TTL_SECONDS = 600  # 10 minutes; lock auto-expires if holder crashes
# Match: 001_desc or 20260224_001_desc (stem without .py)
MIGRATION_FILE_PATTERN = re.compile(r"^(\d{8}_)?(\d+)_([a-z0-9_]+)$", re.IGNORECASE)


def _migrations_dir() -> Path:
    """Return the migrations directory path."""
    return Path(__file__).resolve().parent / "migrations"


def _discover_migration_files() -> list[tuple[str, Path]]:
    """Discover migration files, return list of (name_stem, path) sorted by order."""
    migrations_dir = _migrations_dir()
    if not migrations_dir.exists():
        return []

    found: list[tuple[tuple[str, int, str], str, Path]] = []
    for path in migrations_dir.iterdir():
        if not path.is_file() or path.suffix != ".py":
            continue
        name = path.stem
        if name.startswith("_"):
            continue
        m = MIGRATION_FILE_PATTERN.match(name)
        if m:
            # (timestamp, seq, desc) for sorting; timestamp may be None
            ts = m.group(1) or ""
            seq = m.group(2)
            desc = m.group(3)
            sort_key = (ts, int(seq), desc)
            found.append((sort_key, name, path))

    found.sort(key=lambda x: x[0])
    return [(name, path) for _, name, path in found]


async def _get_applied_names(db) -> set[str]:
    """Return set of migration names already applied."""
    cursor = db[MIGRATIONS_COLLECTION].find({}, {"_id": 1})
    return {doc["_id"] async for doc in cursor}


async def _acquire_migration_lock(db) -> bool:
    """Acquire advisory lock. Returns True if acquired, False if another runner holds it."""
    lock_coll = db[LOCK_COLLECTION]
    await lock_coll.create_index(
        [("acquired_at", 1)],
        expireAfterSeconds=LOCK_TTL_SECONDS,
        name="ttl_idx",
    )
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=LOCK_TTL_SECONDS)
    try:
        result = await lock_coll.find_one_and_update(
            {
                "_id": LOCK_DOC_ID,
                "$or": [
                    {"acquired_at": {"$lt": cutoff}},
                    {"acquired_at": {"$exists": False}},
                ],
            },
            {"$set": {"acquired_at": now, "holder": str(os.getpid())}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result is not None
    except DuplicateKeyError:
        return False


async def _release_migration_lock(db) -> None:
    """Release advisory lock."""
    await db[LOCK_COLLECTION].delete_one({"_id": LOCK_DOC_ID})


def _load_migration_module(name: str, path: Path):
    """Load a migration module by path."""
    spec = importlib.util.spec_from_file_location(
        f"app.database.migrations.{name}", path, submodule_search_locations=[]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load migration {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def run_migrations(dry_run: bool = False) -> int:
    """Discover, run, and track migrations. Returns exit code (0 = success)."""
    migrations_dir = _migrations_dir()
    if not migrations_dir.exists():
        logger.info("No migrations directory found at %s", migrations_dir)
        return 0

    await connect_to_mongodb()
    try:
        db = get_connection().get_database()
        applied = await _get_applied_names(db)
        discovered = _discover_migration_files()
        pending = [(name, path) for name, path in discovered if name not in applied]

        if not pending:
            logger.info("No pending migrations")
            return 0

        if dry_run:
            logger.info("--dry-run: would run %d migration(s):", len(pending))
            for name, _ in pending:
                logger.info("  - %s", name)
            return 0

        if not await _acquire_migration_lock(db):
            logger.error(
                "Another migration runner holds the lock. Wait for it to finish or "
                "for the lock to expire (%d seconds).",
                LOCK_TTL_SECONDS,
            )
            return 1

        try:
            for name, path in pending:
                logger.info("Running migration: %s", name)
                mod = _load_migration_module(name, path)
                if not hasattr(mod, "up"):
                    logger.error("Migration %s has no 'up' function", name)
                    return 1
                try:
                    await mod.up(db)
                except Exception as e:
                    logger.exception("Migration %s failed: %s", name, e)
                    return 1
                await db[MIGRATIONS_COLLECTION].insert_one(
                    {"_id": name, "applied_at": datetime.now(UTC)}
                )
                logger.info("Applied: %s", name)

            return 0
        finally:
            await _release_migration_lock(db)
    finally:
        await disconnect_from_mongodb()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run MongoDB migrations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without executing",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    import asyncio

    return asyncio.run(run_migrations(dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
