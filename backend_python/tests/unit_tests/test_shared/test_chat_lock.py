"""Unit tests for the chat lock mechanism.

Tests cover:
- Successful lock acquisition and release (happy path)
- Lock already held rejection
- Expired lock cleanup
- Lock release on exception
- Race condition handling during acquisition
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.chat_lock import (
    LOCK_TTL_SECONDS,
    ChatLock,
    ChatLockError,
    get_chat_lock,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_collection():
    """Mock MongoDB collection for chat locks."""
    collection = MagicMock()
    collection.find_one_and_update = AsyncMock()
    collection.delete_one = AsyncMock()
    return collection


@pytest.fixture
def mock_db(mock_collection):
    """Mock database with chat_locks collection."""
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


@pytest.fixture
def chat_lock():
    """Create a ChatLock instance for testing."""
    return ChatLock()


@pytest.fixture
def chat_id():
    """Sample chat ID for testing."""
    return "test_chat_123"


# ==============================================================================
# TEST 1: Successful Lock Acquisition and Release (Happy Path)
# ==============================================================================


class TestSuccessfulLockAcquisition:
    """Tests for successful lock acquisition and release."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_successful_lock_acquisition_and_release(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that lock is successfully acquired and released."""
        # Setup: No existing lock - find_one_and_update will succeed (upsert)
        mock_get_connection.return_value.get_database.return_value = mock_db
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # Return a document when lock is acquired (upsert creates it)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Acquire lock
        async with chat_lock.acquire(chat_id) as acquirer:
            # Verify lock was acquired
            assert acquirer.acquired is True
            assert acquirer.lock_key == f"chat_{chat_id}"
            assert acquirer.chat_id == chat_id

            # Verify find_one_and_update was called
            assert mock_collection.find_one_and_update.called
            call_args = mock_collection.find_one_and_update.call_args

            # Verify filter structure
            filter_dict = call_args.kwargs["filter"]
            assert filter_dict["_id"] == f"chat_{chat_id}"
            assert "$or" in filter_dict

            # Verify update structure
            update_dict = call_args.kwargs["update"]
            assert "$set" in update_dict
            assert update_dict["$set"]["chat_id"] == chat_id
            assert "acquired_at" in update_dict["$set"]
            assert "expires_at" in update_dict["$set"]

            # Verify upsert and return_document
            assert call_args.kwargs["upsert"] is True
            from pymongo import ReturnDocument

            assert call_args.kwargs["return_document"] == ReturnDocument.AFTER

        # After context exit, verify lock was released
        mock_collection.delete_one.assert_called_once_with({"_id": f"chat_{chat_id}"})
        assert acquirer.acquired is False

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_document_structure(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that lock document has all required fields."""
        mock_get_connection.return_value.get_database.return_value = mock_db
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # Return a document when lock is acquired
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        async with chat_lock.acquire(chat_id):
            # Get the update operation that was called
            call_args = mock_collection.find_one_and_update.call_args
            update_dict = call_args.kwargs["update"]["$set"]

            # Verify all required fields are present in the update
            assert "chat_id" in update_dict
            assert "acquired_at" in update_dict
            assert "expires_at" in update_dict

            # Verify field types
            assert isinstance(update_dict["chat_id"], str)
            assert isinstance(update_dict["acquired_at"], datetime)
            assert isinstance(update_dict["expires_at"], datetime)

            # Verify timestamps are timezone-aware
            assert update_dict["acquired_at"].tzinfo is not None
            assert update_dict["expires_at"].tzinfo is not None


# ==============================================================================
# TEST 2: Lock Already Held Rejection
# ==============================================================================


class TestLockAlreadyHeld:
    """Tests for lock already held scenarios."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_already_held_raises_error(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that ChatLockError is raised when lock is already held."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Setup: Lock already exists and is still valid
        # find_one_and_update returns None when filter doesn't match (lock is valid)
        mock_collection.find_one_and_update.return_value = None

        # Attempt to acquire lock should raise ChatLockError
        with pytest.raises(ChatLockError) as exc_info:
            async with chat_lock.acquire(chat_id):
                pass

        # Verify error message
        assert chat_id in str(exc_info.value)
        assert "already processing" in str(exc_info.value).lower()

        # Verify find_one_and_update was called
        assert mock_collection.find_one_and_update.called

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_already_held_with_different_chat_ids(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
    ) -> None:
        """Test that locks for different chat_ids don't interfere."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        chat_id_1 = "chat_1"
        chat_id_2 = "chat_2"

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # First request for chat_id_1 should fail (lock already held)
        mock_collection.find_one_and_update.return_value = None
        with pytest.raises(ChatLockError):
            async with chat_lock.acquire(chat_id_1):
                pass

        # Second request for chat_id_2 should succeed (different lock)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id_2}",
            "chat_id": chat_id_2,
            "acquired_at": now,
            "expires_at": expires_at,
        }
        async with chat_lock.acquire(chat_id_2):
            assert True  # Lock acquired successfully

        # Verify different lock keys were used in find_one_and_update calls
        find_calls = mock_collection.find_one_and_update.call_args_list
        assert len(find_calls) >= 2
        # First call should check for chat_1, second for chat_2
        assert find_calls[0].kwargs["filter"]["_id"] == f"chat_{chat_id_1}"
        assert find_calls[1].kwargs["filter"]["_id"] == f"chat_{chat_id_2}"


# ==============================================================================
# TEST 3: Expired Lock Cleanup
# ==============================================================================


class TestExpiredLockCleanup:
    """Tests for expired lock cleanup."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_expired_lock_is_cleaned_up(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that expired locks are cleaned up and new lock can be acquired."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Setup: Lock exists but has expired
        # When filter matches (expired lock), find_one_and_update updates and returns the document
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # find_one_and_update returns the updated document (expired lock was overwritten)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Should be able to acquire lock (expired lock will be overwritten by find_one_and_update)
        async with chat_lock.acquire(chat_id) as acquirer:
            assert acquirer.acquired is True

            # Verify find_one_and_update was called (it handles expired lock cleanup)
            assert mock_collection.find_one_and_update.called

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_with_no_expires_at_is_cleaned_up(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that locks without expires_at field are treated as expired."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Setup: Lock exists but has no expires_at field (corrupted/invalid)
        # The filter matches when expires_at doesn't exist, so find_one_and_update will update it
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # find_one_and_update returns the updated document (invalid lock was overwritten)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Should be able to acquire lock (invalid lock will be overwritten by find_one_and_update)
        async with chat_lock.acquire(chat_id) as acquirer:
            assert acquirer.acquired is True

            # Verify find_one_and_update was called (it handles invalid lock cleanup)
            assert mock_collection.find_one_and_update.called


# ==============================================================================
# TEST 4: Lock Release on Exception
# ==============================================================================


class TestLockReleaseOnException:
    """Tests for lock release when exceptions occur."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_released_on_exception(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that lock is released even when an exception occurs."""
        mock_get_connection.return_value.get_database.return_value = mock_db
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Acquire lock and raise an exception inside the context
        with pytest.raises(ValueError, match="Test error"):
            async with chat_lock.acquire(chat_id) as acquirer:
                assert acquirer.acquired is True
                raise ValueError("Test error")

        # Verify lock was released despite the exception
        mock_collection.delete_one.assert_called_once_with({"_id": f"chat_{chat_id}"})
        assert acquirer.acquired is False

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_released_on_keyboard_interrupt(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that lock is released on KeyboardInterrupt."""
        mock_get_connection.return_value.get_database.return_value = mock_db
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Acquire lock and raise KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            async with chat_lock.acquire(chat_id) as acquirer:
                assert acquirer.acquired is True
                raise KeyboardInterrupt()

        # Verify lock was released
        mock_collection.delete_one.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_lock_not_released_if_not_acquired(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that lock is not released if acquisition failed."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Setup: Lock already held (find_one_and_update returns None)
        mock_collection.find_one_and_update.return_value = None

        # Attempt to acquire should fail
        try:
            async with chat_lock.acquire(chat_id):
                pass
        except ChatLockError:
            pass

        # Verify delete_one was never called (lock was never acquired)
        mock_collection.delete_one.assert_not_called()


# ==============================================================================
# TEST 5: Race Condition Handling
# ==============================================================================


class TestRaceConditionHandling:
    """Tests for race condition handling during lock acquisition."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_race_condition_duplicate_key_error(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test handling of race condition during concurrent acquisition.

        With find_one_and_update + upsert, the operation is atomic. If two
        processes try to acquire simultaneously, the first will succeed and
        the second will get None (lock already exists and is valid).
        """
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Simulate race condition: first call succeeds, second call finds lock already exists
        # (In real scenario, both would call find_one_and_update, but second one's filter
        # won't match because first one already created a valid lock)
        mock_collection.find_one_and_update.return_value = None

        # Should raise ChatLockError because lock was acquired by another request
        with pytest.raises(ChatLockError) as exc_info:
            async with chat_lock.acquire(chat_id):
                pass

        assert chat_id in str(exc_info.value)
        assert "already processing" in str(exc_info.value).lower()

        # Verify find_one_and_update was called
        assert mock_collection.find_one_and_update.called

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_race_condition_lock_expired_between_check_and_insert(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test handling when lock expires between attempts.

        With find_one_and_update, the filter checks if lock is expired.
        If expired, it will match and update the lock atomically.
        """
        mock_get_connection.return_value.get_database.return_value = mock_db

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LOCK_TTL_SECONDS)

        # find_one_and_update succeeds because filter matches (lock expired or doesn't exist)
        mock_collection.find_one_and_update.return_value = {
            "_id": f"chat_{chat_id}",
            "chat_id": chat_id,
            "acquired_at": now,
            "expires_at": expires_at,
        }

        # Should successfully acquire lock (atomic operation handles expired lock)
        async with chat_lock.acquire(chat_id) as acquirer:
            assert acquirer.acquired is True

            # Verify find_one_and_update was called
            assert mock_collection.find_one_and_update.called

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_race_condition_generic_exception_handling(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test handling of generic exceptions during find_one_and_update."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # find_one_and_update fails with generic exception
        generic_error = Exception("Database connection error")
        mock_collection.find_one_and_update.side_effect = generic_error

        # Should raise the original exception (not ChatLockError)
        with pytest.raises(Exception, match="Database connection error"):
            async with chat_lock.acquire(chat_id):
                pass


# ==============================================================================
# ADDITIONAL TESTS: Singleton and Utility Functions
# ==============================================================================


class TestChatLockSingleton:
    """Tests for singleton pattern."""

    def test_get_chat_lock_returns_singleton(self) -> None:
        """Test that get_chat_lock returns the same instance."""
        lock1 = get_chat_lock()
        lock2 = get_chat_lock()

        assert lock1 is lock2
        assert isinstance(lock1, ChatLock)

    def test_get_chat_lock_creates_new_instance_if_none(self) -> None:
        """Test that get_chat_lock creates instance if none exists."""
        # Reset singleton
        import app.shared.chat_lock as chat_lock_module

        chat_lock_module._chat_lock = None

        lock = get_chat_lock()
        assert isinstance(lock, ChatLock)
        assert chat_lock_module._chat_lock is lock


class TestChatLockManualRelease:
    """Tests for manual lock release."""

    @pytest.mark.asyncio
    @patch("app.shared.chat_lock.get_connection")
    async def test_manual_release_deletes_lock(
        self,
        mock_get_connection: MagicMock,
        mock_collection: MagicMock,
        mock_db: MagicMock,
        chat_lock: ChatLock,
        chat_id: str,
    ) -> None:
        """Test that manual release deletes the lock document."""
        mock_get_connection.return_value.get_database.return_value = mock_db

        # Manually release lock
        await chat_lock.release(chat_id)

        # Verify delete_one was called with correct lock key
        mock_collection.delete_one.assert_called_once_with({"_id": f"chat_{chat_id}"})
