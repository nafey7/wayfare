"""Migration 006: conversations collection + backfill from chats_python."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from pymongo.errors import OperationFailure

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "database"
    / "migrations"
    / "006_create_conversations_collection.py"
)


def _load_migration_006() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "migration_006_create_conversations_collection", _MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load 006_create_conversations_collection")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _AsyncCursor:
    """Turn a list into an async iterator for aggregate() cursor mocks."""

    def __init__(self, data: list[Any]) -> None:
        self._iter = iter(data)

    def __aiter__(self) -> "_AsyncCursor":
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iter)
        except StopIteration as err:  # pragma: no cover - handled by aiter contract
            raise StopAsyncIteration from err


def _async_iter(items: list[Any]) -> _AsyncCursor:
    return _AsyncCursor(items)


def _make_db(conv_coll: MagicMock, chats_coll: MagicMock) -> MagicMock:
    db = MagicMock()

    def getitem(name: str) -> MagicMock:
        if name == "conversations":
            return conv_coll
        if name == "chats_python":
            return chats_coll
        return MagicMock()

    db.__getitem__.side_effect = getitem
    return db


@pytest.mark.asyncio
async def test_006_up_creates_indexes_with_full_specs() -> None:
    """up() creates both conversations indexes with exact keys, names, and unique flag."""
    m006 = _load_migration_006()

    conv_coll = MagicMock()
    conv_coll.create_index = AsyncMock()
    conv_coll.find_one = AsyncMock(return_value=None)
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.aggregate = MagicMock(return_value=_async_iter([]))

    db = _make_db(conv_coll, chats_coll)

    await m006.up(db)

    assert conv_coll.create_index.await_count == 2
    awaited = conv_coll.create_index.await_args_list

    # Index 1: user/active/recency for sidebar list
    assert awaited[0].args[0] == [
        ("user_id", 1),
        ("is_deleted", 1),
        ("last_message_at", -1),
    ]
    assert awaited[0].kwargs == {
        "name": "user_active_conversations",
        "unique": False,
    }

    # Index 2: chat_id unique so the upsert/insert contract is safe
    assert awaited[1].args[0] == [("chat_id", 1)]
    assert awaited[1].kwargs == {
        "name": "chat_id_unique",
        "unique": True,
    }


@pytest.mark.asyncio
async def test_006_up_backfills_one_doc_per_distinct_chat() -> None:
    """Each aggregate group maps to exactly one insert with the expected shape."""
    m006 = _load_migration_006()

    user_a = ObjectId()
    user_b = ObjectId()

    groups = [
        {
            "_id": {"user_id": user_a, "chat_id": "chat-a"},
            "first_message_text": "Plan a trip to Paris",
            "last_message_at": "2026-04-10",
            "message_count": 4,
            "created_at": "2026-04-01",
        },
        {
            "_id": {"user_id": user_b, "chat_id": "chat-b"},
            "first_message_text": "Hotels in Rome",
            "last_message_at": "2026-04-12",
            "message_count": 2,
            "created_at": "2026-04-05",
        },
    ]

    conv_coll = MagicMock()
    conv_coll.create_index = AsyncMock()
    conv_coll.find_one = AsyncMock(return_value=None)  # Nothing pre-existing
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.aggregate = MagicMock(return_value=_async_iter(groups))

    db = _make_db(conv_coll, chats_coll)

    await m006.up(db)

    assert conv_coll.insert_one.await_count == 2
    inserted_a = conv_coll.insert_one.await_args_list[0].args[0]
    assert inserted_a["chat_id"] == "chat-a"
    assert inserted_a["user_id"] == user_a
    assert inserted_a["name"] == "Conversation"
    assert inserted_a["is_deleted"] is False
    assert inserted_a["message_count"] == 4
    assert inserted_a["last_message_preview"] == "Plan a trip to Paris"

    inserted_b = conv_coll.insert_one.await_args_list[1].args[0]
    assert inserted_b["chat_id"] == "chat-b"
    assert inserted_b["user_id"] == user_b


@pytest.mark.asyncio
async def test_006_up_is_idempotent_skips_existing_chat_ids() -> None:
    """Re-running against populated conversations must not re-insert."""
    m006 = _load_migration_006()

    groups = [
        {
            "_id": {"user_id": ObjectId(), "chat_id": "already-here"},
            "first_message_text": "Hi",
            "last_message_at": "2026-04-10",
            "message_count": 1,
            "created_at": "2026-04-10",
        },
    ]

    conv_coll = MagicMock()
    conv_coll.create_index = AsyncMock()
    conv_coll.find_one = AsyncMock(return_value={"_id": ObjectId()})  # pre-existing
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.aggregate = MagicMock(return_value=_async_iter(groups))

    db = _make_db(conv_coll, chats_coll)

    await m006.up(db)

    conv_coll.find_one.assert_awaited_once_with({"chat_id": "already-here"})
    conv_coll.insert_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_006_up_truncates_preview_to_100_chars() -> None:
    """Long first messages get sliced to 100 chars for last_message_preview."""
    m006 = _load_migration_006()

    long_text = "A" * 250
    groups = [
        {
            "_id": {"user_id": ObjectId(), "chat_id": "chat-long"},
            "first_message_text": long_text,
            "last_message_at": "2026-04-10",
            "message_count": 1,
            "created_at": "2026-04-10",
        },
    ]

    conv_coll = MagicMock()
    conv_coll.create_index = AsyncMock()
    conv_coll.find_one = AsyncMock(return_value=None)
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.aggregate = MagicMock(return_value=_async_iter(groups))

    db = _make_db(conv_coll, chats_coll)

    await m006.up(db)

    inserted = conv_coll.insert_one.await_args_list[0].args[0]
    assert len(inserted["last_message_preview"]) == 100


@pytest.mark.asyncio
async def test_006_up_pipeline_filters_status_and_authenticated_users() -> None:
    """Backfill must skip deleted messages and guest (user_id=None) chats."""
    m006 = _load_migration_006()

    conv_coll = MagicMock()
    conv_coll.create_index = AsyncMock()
    conv_coll.find_one = AsyncMock(return_value=None)
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.aggregate = MagicMock(return_value=_async_iter([]))

    db = _make_db(conv_coll, chats_coll)

    await m006.up(db)

    chats_coll.aggregate.assert_called_once()
    pipeline = chats_coll.aggregate.call_args.args[0]
    match_stage = pipeline[0]
    assert match_stage == {"$match": {"status": 10, "user_id": {"$ne": None}}}


@pytest.mark.asyncio
async def test_006_down_drops_both_indexes() -> None:
    """down() drops the indexes added by up()."""
    m006 = _load_migration_006()

    coll = MagicMock()
    coll.drop_index = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    await m006.down(db)

    db.__getitem__.assert_called_with("conversations")
    assert coll.drop_index.await_count == 2
    names = [c.args[0] for c in coll.drop_index.await_args_list]
    assert names == ["user_active_conversations", "chat_id_unique"]


@pytest.mark.asyncio
async def test_006_down_swallows_index_not_found_code_27() -> None:
    """down() tolerates missing indexes (re-run safety) via OperationFailure code 27."""
    m006 = _load_migration_006()

    coll = MagicMock()
    coll.drop_index = AsyncMock(
        side_effect=[
            OperationFailure("index not found", code=27),
            OperationFailure("index not found", code=27),
        ]
    )
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    # Must not raise
    await m006.down(db)

    assert coll.drop_index.await_count == 2


@pytest.mark.asyncio
async def test_006_down_swallows_index_not_found_via_message() -> None:
    """down() tolerates absent indexes when OperationFailure lacks code=27 but message hints it."""
    m006 = _load_migration_006()

    coll = MagicMock()
    coll.drop_index = AsyncMock(
        side_effect=[
            OperationFailure("index not found"),
            OperationFailure("index not found"),
        ]
    )
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    await m006.down(db)

    assert coll.drop_index.await_count == 2


@pytest.mark.asyncio
async def test_006_down_reraises_unexpected_operation_failure() -> None:
    """down() does NOT swallow unrelated OperationFailure (e.g. auth, shutdown)."""
    m006 = _load_migration_006()

    coll = MagicMock()
    coll.drop_index = AsyncMock(side_effect=OperationFailure("unauthorized", code=13))
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)

    with pytest.raises(OperationFailure):
        await m006.down(db)
