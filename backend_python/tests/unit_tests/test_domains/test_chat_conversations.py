"""Unit tests for multi-conversation repository and service methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.chat.repository import (
    CONVERSATIONS_COLLECTION,
    create_conversation,
    get_or_create_chat_conversation,
    list_user_conversations,
    rename_conversation,
    soft_delete_conversation,
    update_conversation_on_message,
    user_owns_conversation,
)
from app.domains.chat.schemas import (
    ConversationListResponse,
    ConversationMeta,
    CreateConversationRequest,
    RenameConversationRequest,
)

USER_ID = "507f1f77bcf86cd799439011"
CHAT_ID = "550e8400-e29b-41d4-a716-446655440000"


def _make_db_mock(conv_coll: MagicMock, chats_coll: MagicMock | None = None):
    """Helper: build a mock database with collection routing."""

    async def get_db() -> MagicMock:
        db = MagicMock()

        def getitem(_self: MagicMock, name: str) -> MagicMock:
            if name == CONVERSATIONS_COLLECTION:
                return conv_coll
            if name == "chats_python" and chats_coll is not None:
                return chats_coll
            return MagicMock()

        type(db).__getitem__ = getitem  # type: ignore[method-assign]
        return db

    return get_db


# ---------------------------------------------------------------------------
# Repository: create_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_conversation_inserts_doc() -> None:
    conv_coll = MagicMock()
    conv_coll.insert_one = AsyncMock()

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        doc = await create_conversation(USER_ID, name="Trip to Paris")

    assert doc["name"] == "Trip to Paris"
    assert doc["user_id"] == ObjectId(USER_ID)
    assert doc["is_deleted"] is False
    assert doc["message_count"] == 0
    assert "chat_id" in doc
    conv_coll.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_conversation_default_name() -> None:
    conv_coll = MagicMock()
    conv_coll.insert_one = AsyncMock()

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        doc = await create_conversation(USER_ID)

    assert doc["name"] == "New conversation"


# ---------------------------------------------------------------------------
# Repository: list_user_conversations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_user_conversations_returns_items_and_total() -> None:
    now = datetime.now(UTC)
    docs = [
        {"chat_id": "c1", "name": "Chat 1", "message_count": 5, "last_message_at": now},
        {"chat_id": "c2", "name": "Chat 2", "message_count": 2, "last_message_at": now},
    ]

    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=docs)

    conv_coll = MagicMock()
    conv_coll.find = MagicMock(return_value=cursor)
    conv_coll.count_documents = AsyncMock(return_value=2)

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        items, total = await list_user_conversations(USER_ID, limit=50, offset=0)

    assert total == 2
    assert len(items) == 2
    assert items[0]["chat_id"] == "c1"


@pytest.mark.asyncio
async def test_list_user_conversations_empty() -> None:
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])

    conv_coll = MagicMock()
    conv_coll.find = MagicMock(return_value=cursor)
    conv_coll.count_documents = AsyncMock(return_value=0)

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        items, total = await list_user_conversations(USER_ID)

    assert total == 0
    assert items == []


# ---------------------------------------------------------------------------
# Repository: rename_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rename_conversation_success() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        result = await rename_conversation(CHAT_ID, USER_ID, "New Name")

    assert result is True
    call_args = conv_coll.update_one.call_args
    assert call_args[0][0]["chat_id"] == CHAT_ID
    assert call_args[0][1]["$set"]["name"] == "New Name"


@pytest.mark.asyncio
async def test_rename_conversation_not_found() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=0))

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        result = await rename_conversation(CHAT_ID, USER_ID, "New Name")

    assert result is False


@pytest.mark.asyncio
async def test_rename_conversation_truncates_long_name() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    long_name = "A" * 100

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        await rename_conversation(CHAT_ID, USER_ID, long_name)

    call_args = conv_coll.update_one.call_args
    assert len(call_args[0][1]["$set"]["name"]) == 50


# ---------------------------------------------------------------------------
# Repository: soft_delete_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_conversation_success() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        result = await soft_delete_conversation(CHAT_ID, USER_ID)

    assert result is True
    call_args = conv_coll.update_one.call_args
    assert call_args[0][1]["$set"]["is_deleted"] is True


@pytest.mark.asyncio
async def test_soft_delete_conversation_not_found() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock(modified_count=0))

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        result = await soft_delete_conversation(CHAT_ID, USER_ID)

    assert result is False


# ---------------------------------------------------------------------------
# Repository: update_conversation_on_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_conversation_on_message_increments_count() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock()

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        await update_conversation_on_message(CHAT_ID, "Hello world")

    call_args = conv_coll.update_one.call_args
    assert call_args[0][0] == {"chat_id": CHAT_ID}
    assert call_args[0][1]["$inc"]["message_count"] == 1
    assert call_args[0][1]["$set"]["last_message_preview"] == "Hello world"


@pytest.mark.asyncio
async def test_update_conversation_on_message_truncates_preview() -> None:
    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock()

    long_msg = "X" * 200

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        await update_conversation_on_message(CHAT_ID, long_msg)

    call_args = conv_coll.update_one.call_args
    assert len(call_args[0][1]["$set"]["last_message_preview"]) == 100


# ---------------------------------------------------------------------------
# Repository: get_or_create_chat_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_conversation() -> None:
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value={"chat_id": CHAT_ID})

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        result = await get_or_create_chat_conversation(USER_ID)

    assert result == CHAT_ID


@pytest.mark.asyncio
async def test_get_or_create_falls_back_to_legacy() -> None:
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value=None)

    chats_coll = MagicMock()
    chats_coll.find_one = AsyncMock(
        return_value={"chat_id": "legacy-chat-id", "status": 10}
    )

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll, chats_coll),
    ):
        result = await get_or_create_chat_conversation(USER_ID)

    assert result == "legacy-chat-id"


@pytest.mark.asyncio
async def test_get_or_create_creates_new_when_nothing_exists() -> None:
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value=None)
    conv_coll.insert_one = AsyncMock()

    chats_coll = MagicMock()
    chats_coll.find_one = AsyncMock(return_value=None)

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll, chats_coll),
    ):
        result = await get_or_create_chat_conversation(USER_ID)

    assert isinstance(result, str)
    assert len(result) == 36  # UUID format
    conv_coll.insert_one.assert_awaited_once()


# ---------------------------------------------------------------------------
# Repository: user_owns_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_owns_conversation_true_when_conversation_doc_exists() -> None:
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value={"_id": ObjectId()})

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll),
    ):
        assert await user_owns_conversation(CHAT_ID, USER_ID) is True

    call_args = conv_coll.find_one.call_args
    assert call_args[0][0]["chat_id"] == CHAT_ID
    assert call_args[0][0]["user_id"] == ObjectId(USER_ID)
    assert call_args[0][0]["is_deleted"] is False


@pytest.mark.asyncio
async def test_user_owns_conversation_false_when_neither_exists() -> None:
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value=None)

    chats_coll = MagicMock()
    chats_coll.find_one = AsyncMock(return_value=None)

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll, chats_coll),
    ):
        assert await user_owns_conversation(CHAT_ID, USER_ID) is False


@pytest.mark.asyncio
async def test_user_owns_conversation_true_via_legacy_chats_python() -> None:
    """Legacy conversations without a conversations doc still resolve by chats_python."""
    conv_coll = MagicMock()
    conv_coll.find_one = AsyncMock(return_value=None)

    chats_coll = MagicMock()
    chats_coll.find_one = AsyncMock(return_value={"_id": ObjectId()})

    with patch(
        "app.domains.chat.repository.get_database",
        side_effect=_make_db_mock(conv_coll, chats_coll),
    ):
        assert await user_owns_conversation(CHAT_ID, USER_ID) is True

    call_args = chats_coll.find_one.call_args
    assert call_args[0][0]["chat_id"] == CHAT_ID
    assert call_args[0][0]["user_id"] == ObjectId(USER_ID)
    assert call_args[0][0]["status"] == 10


# ---------------------------------------------------------------------------
# Schemas: validation
# ---------------------------------------------------------------------------


def test_rename_request_validates_min_length() -> None:
    with pytest.raises(Exception):
        RenameConversationRequest(name="")


def test_rename_request_validates_max_length() -> None:
    with pytest.raises(Exception):
        RenameConversationRequest(name="A" * 51)


def test_rename_request_strips_whitespace() -> None:
    req = RenameConversationRequest(name="  Trip to Paris  ")
    assert req.name == "Trip to Paris"


def test_create_request_allows_none_name() -> None:
    req = CreateConversationRequest()
    assert req.name is None


def test_create_request_validates_max_length() -> None:
    with pytest.raises(Exception):
        CreateConversationRequest(name="A" * 51)


def test_conversation_meta_defaults() -> None:
    meta = ConversationMeta(chat_id="c1", name="Test")
    assert meta.message_count == 0
    assert meta.last_message_preview == ""
    assert meta.last_message_at is None


def test_conversation_list_response_has_more() -> None:
    resp = ConversationListResponse(
        conversations=[],
        total=100,
        has_more=True,
    )
    assert resp.has_more is True
    assert resp.total == 100


# ---------------------------------------------------------------------------
# Service: _auto_name_conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_name_conversation_calls_llm_and_renames() -> None:
    from app.domains.chat.service import ChatService

    svc = ChatService()

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Paris Trip Planning"))

    with (
        patch(
            "app.domains.chat.service.repository.rename_conversation",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_rename,
        patch(
            "app.ai.graph.llm_factory.create_llm",
            return_value=mock_llm,
        ),
    ):
        name = await svc._auto_name_conversation(
            CHAT_ID, USER_ID, "I want to go to Paris"
        )

    assert name == "Paris Trip Planning"
    mock_rename.assert_awaited_once_with(CHAT_ID, USER_ID, "Paris Trip Planning")


@pytest.mark.asyncio
async def test_auto_name_conversation_returns_none_on_error() -> None:
    from app.domains.chat.service import ChatService

    svc = ChatService()

    with patch(
        "app.ai.graph.llm_factory.create_llm",
        side_effect=RuntimeError("API down"),
    ):
        name = await svc._auto_name_conversation(CHAT_ID, USER_ID, "hello")

    assert name is None


@pytest.mark.asyncio
async def test_auto_name_conversation_strips_quotes() -> None:
    from app.domains.chat.service import ChatService

    svc = ChatService()

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='"Flight to Rome"'))

    with (
        patch(
            "app.domains.chat.service.repository.rename_conversation",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.ai.graph.llm_factory.create_llm",
            return_value=mock_llm,
        ),
    ):
        name = await svc._auto_name_conversation(
            CHAT_ID, USER_ID, "Book flight to Rome"
        )

    assert name == "Flight to Rome"
