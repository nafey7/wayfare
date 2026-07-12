"""Tests for the chat-service in-memory dedup cache.

The cache short-circuits identical messages sent for the same chat_id within
DEDUPE_WINDOW_SECONDS so repeated submissions don't run the full LangGraph
pipeline. Covers:
  - Identical resend within window → True
  - Same chat, different message → False
  - Same message, different chat → False
  - Same message after window expires → False
  - Cleanup loop runs once cache exceeds threshold (no infinite growth)
  - Concurrent calls are serialized (no race in cleanup)
"""

import asyncio
from unittest.mock import patch

import pytest

from app.domains.chat import service as chat_service


@pytest.fixture(autouse=True)
def _reset_cache():
    """Each test starts with a clean cache."""
    chat_service._recent_messages.clear()
    yield
    chat_service._recent_messages.clear()


@pytest.mark.asyncio
async def test_first_send_is_not_a_duplicate():
    assert (await chat_service._is_duplicate_resend("chat-A", "Hello")) is False
    assert "chat-A" in chat_service._recent_messages


@pytest.mark.asyncio
async def test_identical_resend_within_window_is_duplicate():
    await chat_service._is_duplicate_resend("chat-A", "Hello")
    assert (await chat_service._is_duplicate_resend("chat-A", "Hello")) is True


@pytest.mark.asyncio
async def test_same_chat_different_message_is_not_duplicate():
    await chat_service._is_duplicate_resend("chat-A", "Hello")
    assert (await chat_service._is_duplicate_resend("chat-A", "World")) is False


@pytest.mark.asyncio
async def test_same_message_different_chat_is_not_duplicate():
    await chat_service._is_duplicate_resend("chat-A", "Hello")
    assert (await chat_service._is_duplicate_resend("chat-B", "Hello")) is False


@pytest.mark.asyncio
async def test_resend_after_window_expires_is_not_duplicate():
    """Mock time so the second call falls outside the dedupe window."""
    base_time = 1000.0

    with patch("app.domains.chat.service.time") as mock_time:
        mock_time.monotonic.return_value = base_time
        await chat_service._is_duplicate_resend("chat-A", "Hello")

        # Advance past the dedupe window
        mock_time.monotonic.return_value = (
            base_time + chat_service._DEDUPE_WINDOW_SECONDS + 0.1
        )
        assert (await chat_service._is_duplicate_resend("chat-A", "Hello")) is False


@pytest.mark.asyncio
async def test_resend_at_window_boundary_is_not_duplicate():
    """Exactly at the dedupe window cutoff, the message is no longer a duplicate.

    The condition is `(now - last_ts) < _DEDUPE_WINDOW_SECONDS` (strictly less),
    so equal-to-window is treated as fresh.
    """
    base_time = 1000.0
    with patch("app.domains.chat.service.time") as mock_time:
        mock_time.monotonic.return_value = base_time
        await chat_service._is_duplicate_resend("chat-A", "Hello")
        mock_time.monotonic.return_value = (
            base_time + chat_service._DEDUPE_WINDOW_SECONDS
        )
        assert (await chat_service._is_duplicate_resend("chat-A", "Hello")) is False


@pytest.mark.asyncio
async def test_cleanup_runs_once_cache_exceeds_threshold():
    """When the cache grows past the cleanup threshold, old entries are pruned."""
    # Fill the cache with old entries
    base_time = 1000.0
    threshold = chat_service._DEDUPE_CLEANUP_THRESHOLD
    cleanup_ttl = chat_service._DEDUPE_CLEANUP_TTL_SECONDS

    with patch("app.domains.chat.service.time") as mock_time:
        # Insert threshold + 1 stale entries (older than cleanup TTL)
        mock_time.monotonic.return_value = base_time
        for i in range(threshold + 1):
            await chat_service._is_duplicate_resend(f"old-chat-{i}", "msg")

        # Advance past the cleanup TTL
        mock_time.monotonic.return_value = base_time + cleanup_ttl + 1.0

        # One more call triggers cleanup since cache size > threshold
        await chat_service._is_duplicate_resend("new-chat", "msg")

        # All "old-chat-*" entries should be removed (stale), only new-chat remains
        remaining_keys = [
            k for k in chat_service._recent_messages if k.startswith("old-chat-")
        ]
        assert remaining_keys == [], (
            f"Cleanup should have pruned stale entries, got {len(remaining_keys)}"
        )
        assert "new-chat" in chat_service._recent_messages


@pytest.mark.asyncio
async def test_cleanup_does_not_remove_recent_entries():
    """Entries within the cleanup TTL must survive the cleanup pass."""
    base_time = 1000.0
    threshold = chat_service._DEDUPE_CLEANUP_THRESHOLD

    with patch("app.domains.chat.service.time") as mock_time:
        # Insert threshold stale entries
        mock_time.monotonic.return_value = base_time
        for i in range(threshold):
            await chat_service._is_duplicate_resend(f"old-{i}", "msg")

        # Advance only slightly (still within cleanup TTL)
        mock_time.monotonic.return_value = base_time + 5.0
        # Insert a fresh entry to trigger cleanup
        await chat_service._is_duplicate_resend("fresh", "msg")

        # All entries should still be present (none stale yet)
        assert len(chat_service._recent_messages) > threshold


@pytest.mark.asyncio
async def test_concurrent_calls_serialized_through_lock():
    """Concurrent _is_duplicate_resend calls don't race on the cleanup path.

    Fires N calls in parallel with asyncio.gather; the cache should end up
    consistent regardless of scheduling.
    """
    n = 50
    results = await asyncio.gather(
        *[chat_service._is_duplicate_resend(f"chat-{i}", "msg") for i in range(n)]
    )
    # All N first-time sends → no duplicates
    assert all(r is False for r in results)
    assert len(chat_service._recent_messages) == n


@pytest.mark.asyncio
async def test_concurrent_identical_resends_one_succeeds_others_dedup():
    """Two concurrent identical resends to the same chat: first sets cache, others see duplicate."""
    n = 10
    results = await asyncio.gather(
        *[chat_service._is_duplicate_resend("same-chat", "same-msg") for _ in range(n)]
    )
    # Exactly one is False (the first to acquire the lock), rest are True
    assert results.count(False) == 1
    assert results.count(True) == n - 1
