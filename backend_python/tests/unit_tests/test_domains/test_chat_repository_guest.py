"""Guest (public) chat persistence on chats_python."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.chat.enums import MessageSender
from app.domains.chat.repository import create_message, guest_session_may_use_chat_id


@pytest.mark.asyncio
async def test_create_message_guest_stores_fingerprint_not_user_id() -> None:
    mock_coll = MagicMock()
    mock_coll.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id="507f1f77bcf86cd799439011")
    )

    async def get_db() -> MagicMock:
        db = MagicMock()

        def getitem(_self: MagicMock, name: str) -> MagicMock:
            if name == "chats_python":
                return mock_coll
            return MagicMock()

        type(db).__getitem__ = getitem  # type: ignore[method-assign]
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        await create_message(
            content={"text": "hello"},
            chat_id="550e8400-e29b-41d4-a716-446655440000",
            sender=MessageSender.USER,
            user_id=None,
            guest_fingerprint="guest-session-uuid",
        )

    doc = mock_coll.insert_one.call_args[0][0]
    assert doc["fingerprint"] == "guest-session-uuid"
    assert "user_id" not in doc


@pytest.mark.asyncio
async def test_guest_session_may_use_chat_id_allows_when_no_messages() -> None:
    mock_coll = MagicMock()
    mock_coll.find_one = AsyncMock(return_value=None)

    async def get_db() -> MagicMock:
        db = MagicMock()

        def getitem(_self: MagicMock, name: str) -> MagicMock:
            if name == "chats_python":
                return mock_coll
            return MagicMock()

        type(db).__getitem__ = getitem  # type: ignore[method-assign]
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        ok = await guest_session_may_use_chat_id(
            "550e8400-e29b-41d4-a716-446655440000",
            "guest-session-uuid",
        )
    assert ok is True


@pytest.mark.asyncio
async def test_guest_session_may_use_chat_id_denies_authenticated_chat() -> None:
    mock_coll = MagicMock()
    mock_coll.find_one = AsyncMock(return_value={"user_id": "507f1f77bcf86cd799439011"})

    async def get_db() -> MagicMock:
        db = MagicMock()

        def getitem(_self: MagicMock, name: str) -> MagicMock:
            if name == "chats_python":
                return mock_coll
            return MagicMock()

        type(db).__getitem__ = getitem  # type: ignore[method-assign]
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        ok = await guest_session_may_use_chat_id(
            "550e8400-e29b-41d4-a716-446655440000",
            "guest-session-uuid",
        )
    assert ok is False


@pytest.mark.asyncio
async def test_guest_session_may_use_chat_id_requires_fingerprint_match() -> None:
    mock_coll = MagicMock()
    mock_coll.find_one = AsyncMock(
        return_value={
            "user_id": None,
            "fingerprint": "expected-fp",
        }
    )

    async def get_db() -> MagicMock:
        db = MagicMock()

        def getitem(_self: MagicMock, name: str) -> MagicMock:
            if name == "chats_python":
                return mock_coll
            return MagicMock()

        type(db).__getitem__ = getitem  # type: ignore[method-assign]
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        ok_wrong = await guest_session_may_use_chat_id(
            "550e8400-e29b-41d4-a716-446655440000",
            "other-fp",
        )
        ok_right = await guest_session_may_use_chat_id(
            "550e8400-e29b-41d4-a716-446655440000",
            "expected-fp",
        )
    assert ok_wrong is False
    assert ok_right is True


@pytest.mark.asyncio
async def test_create_message_rejects_missing_actor() -> None:
    with pytest.raises(ValueError, match="Exactly one of"):
        await create_message(
            content={"text": "x"},
            chat_id="c",
            sender=MessageSender.USER,
            user_id=None,
            guest_fingerprint=None,
        )
