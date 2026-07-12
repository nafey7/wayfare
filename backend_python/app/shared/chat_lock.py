"""Distributed lock for chat requests using MongoDB.

Prevents race conditions when multiple messages arrive for the same chat_id
before the first message completes processing.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo import ReturnDocument

from app.database.connection import get_connection

logger = logging.getLogger(__name__)

# Lock TTL - automatically release lock after this time (safety mechanism)
LOCK_TTL_SECONDS = 300  # 5 minutes


class ChatLockError(Exception):
    """Raised when a chat lock cannot be acquired."""

    pass


class ChatLock:
    """MongoDB-based distributed lock for chat requests.

    Uses MongoDB's atomic findOneAndUpdate operation to ensure only one
    request can process a chat_id at a time.

    Usage:
        lock = ChatLock()
        try:
            async with lock.acquire(chat_id):
                # Process chat message
                await process_message(...)
        except ChatLockError:
            # Another request is already processing this chat_id
            return {"error": "Request already in progress"}
    """

    def __init__(self) -> None:
        """Initialize the chat lock."""
        self._collection_name = "chat_locks"

    async def _get_collection(self) -> Any:
        """Get MongoDB collection for locks."""
        db = get_connection().get_database()
        return db[self._collection_name]

    def acquire(self, chat_id: str) -> "ChatLockAcquirer":
        """Acquire a lock for the given chat_id.

        Args:
            chat_id: Chat conversation ID to lock

        Returns:
            Async context manager that acquires the lock on enter and releases on exit

        Usage:
            async with chat_lock.acquire(chat_id):
                # Process chat message
                await process_message(...)

        Raises:
            ChatLockError: If lock cannot be acquired (another request is processing)
        """
        return ChatLockAcquirer(self, chat_id)

    async def release(self, chat_id: str) -> None:
        """Manually release a lock (usually called by context manager).

        Args:
            chat_id: Chat conversation ID to unlock
        """
        collection = await self._get_collection()
        lock_key = f"chat_{chat_id}"
        await collection.delete_one({"_id": lock_key})
        logger.debug(f"Released chat lock for chat_id={chat_id}")


class ChatLockAcquirer:
    """Async context manager that acquires and releases chat locks."""

    def __init__(self, chat_lock: "ChatLock", chat_id: str) -> None:
        """Initialize lock acquirer.

        Args:
            chat_lock: ChatLock instance
            chat_id: Chat conversation ID to lock
        """
        self.chat_lock = chat_lock
        self.chat_id = chat_id
        self.lock_key: str | None = None
        self.collection: Any = None
        self.acquired = False

    async def __aenter__(self) -> "ChatLockAcquirer":
        """Enter context - acquire lock."""
        collection = await self.chat_lock._get_collection()
        lock_key = f"chat_{self.chat_id}"
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # Atomic: acquire lock if it doesn't exist or is expired
        result = await collection.find_one_and_update(
            filter={
                "_id": lock_key,
                "$or": [
                    {"expires_at": {"$lt": now}},  # Expired - can take over
                    {"expires_at": {"$exists": False}},  # Invalid doc
                ],
            },
            update={
                "$set": {
                    "chat_id": self.chat_id,
                    "acquired_at": now,
                    "expires_at": expires_at,
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        # If result is None, the filter didn't match (lock exists and is valid)
        if result is None:
            logger.warning(
                f"Chat lock already held for chat_id={self.chat_id} - request rejected"
            )
            raise ChatLockError(
                f"Another request is already processing chat_id={self.chat_id}"
            )

        logger.debug(f"Acquired chat lock for chat_id={self.chat_id}")
        self.collection = collection
        self.lock_key = lock_key
        self.acquired = True
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context - release lock."""
        if self.acquired and self.lock_key and self.collection is not None:
            await self.collection.delete_one({"_id": self.lock_key})
            logger.debug(f"Released chat lock: {self.lock_key}")
            self.acquired = False


class ChatLockContext:
    """Context manager for chat locks (deprecated - use ChatLockAcquirer)."""

    def __init__(self, collection: Any, lock_key: str) -> None:
        """Initialize lock context.

        Args:
            collection: MongoDB collection for locks
            lock_key: Lock document key
        """
        self.collection = collection
        self.lock_key = lock_key
        self.released = False

    async def __aenter__(self) -> "ChatLockContext":
        """Enter context - lock already acquired."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context - release lock."""
        if not self.released:
            await self.collection.delete_one({"_id": self.lock_key})
            self.released = True
            logger.debug(f"Released chat lock: {self.lock_key}")


# Singleton instance
_chat_lock: ChatLock | None = None


def get_chat_lock() -> ChatLock:
    """Get singleton ChatLock instance."""
    global _chat_lock
    if _chat_lock is None:
        _chat_lock = ChatLock()
    return _chat_lock
