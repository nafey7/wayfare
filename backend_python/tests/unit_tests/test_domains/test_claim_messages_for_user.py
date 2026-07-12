"""Tests for ``claim_messages_for_user`` (guest chat claim repository)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.chat.repository import claim_messages_for_user
from app.domains.chat.schemas import (
    CLAIM_DEFAULT_MAX_AGE_MINUTES,
    CLAIM_MESSAGE_CAP,
    ClaimOutcomeStatus,
)

USER_ID = "507f1f77bcf86cd799439011"
USER_OID = ObjectId(USER_ID)
OTHER_USER_OID = ObjectId("507f191e810c19729de860ea")
CHAT_ID = "550e8400-e29b-41d4-a716-446655440000"
FINGERPRINT = "guest-session-uuid"


def _guest_msg(text: str = "hi", created_at: datetime | None = None) -> dict:
    return {
        "_id": ObjectId(),
        "chat_id": CHAT_ID,
        "fingerprint": FINGERPRINT,
        "status": 10,
        "content": {"text": text},
        "created_at": created_at or datetime.now(UTC),
    }


def _owned_msg(owner: ObjectId, text: str = "owned") -> dict:
    return {
        "_id": ObjectId(),
        "chat_id": CHAT_ID,
        "user_id": owner,
        "status": 10,
        "content": {"text": text},
        "created_at": datetime.now(UTC),
    }


def _mock_db(
    *, chats_docs: list[dict], conv_doc: dict | None = None
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Build a mock database returning the given chat docs."""
    chats_coll = MagicMock()
    chats_coll.find = MagicMock(
        return_value=MagicMock(to_list=AsyncMock(return_value=list(chats_docs)))
    )
    # find_one returns last (for preview) — return the most recent guest/owned doc.
    chats_coll.find_one = AsyncMock(return_value=chats_docs[-1] if chats_docs else None)
    chats_coll.update_many = AsyncMock(
        return_value=MagicMock(
            modified_count=len([d for d in chats_docs if "fingerprint" in d])
        )
    )

    conv_coll = MagicMock()
    conv_coll.update_one = AsyncMock(return_value=MagicMock())
    conv_coll.find_one = AsyncMock(return_value=conv_doc)

    db = MagicMock()

    def getitem(_self: MagicMock, name: str) -> MagicMock:
        if name == "chats_python":
            return chats_coll
        if name == "conversations":
            return conv_coll
        return MagicMock()

    type(db).__getitem__ = getitem  # type: ignore[method-assign]
    return db, chats_coll, conv_coll


@pytest.mark.asyncio
async def test_claim_happy_path() -> None:
    docs = [_guest_msg("one"), _guest_msg("two"), _guest_msg("three")]
    db, chats_coll, conv_coll = _mock_db(chats_docs=docs)

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.CLAIMED
    assert outcome.chat_id == CHAT_ID
    chats_coll.update_many.assert_awaited_once()
    conv_coll.update_one.assert_awaited_once()
    call_args = conv_coll.update_one.await_args
    update_doc = call_args[0][1]
    assert update_doc["$set"]["user_id"] == USER_OID
    assert update_doc["$set"]["message_count"] == 3


@pytest.mark.asyncio
async def test_claim_idempotent_already_owned() -> None:
    docs = [_owned_msg(USER_OID), _owned_msg(USER_OID)]
    db, chats_coll, _conv_coll = _mock_db(chats_docs=docs)

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.ALREADY_CLAIMED
    chats_coll.update_many.assert_not_called()


@pytest.mark.asyncio
async def test_claim_fingerprint_mismatch() -> None:
    bad = _guest_msg()
    bad["fingerprint"] = "different-uuid"
    db, chats_coll, _ = _mock_db(chats_docs=[_guest_msg(), bad])

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.REJECTED_FINGERPRINT_MISMATCH
    chats_coll.update_many.assert_not_called()


@pytest.mark.asyncio
async def test_claim_owned_by_other_user() -> None:
    docs = [_guest_msg(), _owned_msg(OTHER_USER_OID)]
    db, chats_coll, _ = _mock_db(chats_docs=docs)

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.REJECTED_OWNED_BY_OTHER_USER
    chats_coll.update_many.assert_not_called()


@pytest.mark.asyncio
async def test_claim_too_old() -> None:
    old = _guest_msg(created_at=datetime.now(UTC) - timedelta(days=10))
    db, chats_coll, _ = _mock_db(chats_docs=[old])

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.REJECTED_TOO_OLD
    chats_coll.update_many.assert_not_called()


@pytest.mark.asyncio
async def test_claim_too_large() -> None:
    docs = [_guest_msg(f"m{i}") for i in range(5)]
    db, chats_coll, _ = _mock_db(chats_docs=docs)

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=3,
        )

    assert outcome.status == ClaimOutcomeStatus.REJECTED_TOO_LARGE
    chats_coll.update_many.assert_not_called()


@pytest.mark.asyncio
async def test_claim_nothing_to_claim_when_no_messages() -> None:
    db, chats_coll, _ = _mock_db(chats_docs=[])

    async def get_db() -> MagicMock:
        return db

    with patch("app.domains.chat.repository.get_database", side_effect=get_db):
        outcome = await claim_messages_for_user(
            chat_id=CHAT_ID,
            fingerprint=FINGERPRINT,
            user_id=USER_ID,
            max_age_minutes=CLAIM_DEFAULT_MAX_AGE_MINUTES,
            message_cap=CLAIM_MESSAGE_CAP,
        )

    assert outcome.status == ClaimOutcomeStatus.NOTHING_TO_CLAIM
    chats_coll.update_many.assert_not_called()
