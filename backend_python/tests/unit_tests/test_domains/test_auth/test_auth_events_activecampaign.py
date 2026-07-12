"""Unit tests for the ActiveCampaign sync hook in auth event handlers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.auth.events import (
    AuthEventHandler,
    _background_tasks,
    _spawn_background,
    _sync_to_activecampaign,
)
from app.domains.user import UserNotFoundError


def _make_user(
    email: str = "new@example.com",
    first_name: str | None = "Alice",
    last_name: str | None = "Smith",
) -> MagicMock:
    user = MagicMock()
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    return user


@pytest.mark.asyncio
async def test_sync_noop_when_client_disabled() -> None:
    """When integration is not configured, no user lookup or HTTP call happens."""
    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(return_value=_make_user())

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=None,
        ) as mock_get_client,
        patch("app.domains.user.UserService", user_service),
    ):
        await _sync_to_activecampaign("user-123")

    mock_get_client.assert_called_once()
    user_service.get_user_public.assert_not_called()


@pytest.mark.asyncio
async def test_sync_calls_create_contact_with_user_fields() -> None:
    """When enabled, sync looks up the user and forwards email + name."""
    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(return_value=_make_user())

    fake_client = MagicMock()
    fake_client.create_contact = AsyncMock()

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=fake_client,
        ),
        patch("app.domains.user.UserService", user_service),
    ):
        await _sync_to_activecampaign("user-123")

    fake_client.create_contact.assert_awaited_once_with(
        email="new@example.com",
        first_name="Alice",
        last_name="Smith",
    )


@pytest.mark.asyncio
async def test_sync_skips_when_user_not_found() -> None:
    """If the user was deleted between signup and sync, skip quietly."""
    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(
        side_effect=UserNotFoundError("User gone-user not found")
    )

    fake_client = MagicMock()
    fake_client.create_contact = AsyncMock()

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=fake_client,
        ),
        patch("app.domains.user.UserService", user_service),
    ):
        await _sync_to_activecampaign("gone-user")

    fake_client.create_contact.assert_not_called()


@pytest.mark.asyncio
async def test_sync_skips_when_user_has_no_email() -> None:
    """Defensive: if the user somehow has no email, skip rather than POST."""
    user = MagicMock()
    user.email = ""
    user.first_name = "Alice"
    user.last_name = "Smith"

    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(return_value=user)

    fake_client = MagicMock()
    fake_client.create_contact = AsyncMock()

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=fake_client,
        ),
        patch("app.domains.user.UserService", user_service),
    ):
        await _sync_to_activecampaign("user-123")

    fake_client.create_contact.assert_not_called()


@pytest.mark.asyncio
async def test_sync_swallows_client_exceptions() -> None:
    """Any exception from the client is caught and does not propagate."""
    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(return_value=_make_user())

    fake_client = MagicMock()
    fake_client.create_contact = AsyncMock(side_effect=RuntimeError("AC is down"))

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=fake_client,
        ),
        patch("app.domains.user.UserService", user_service),
    ):
        # Must not raise — signup cannot fail because of AC.
        await _sync_to_activecampaign("user-123")


@pytest.mark.asyncio
async def test_sync_swallows_lookup_exceptions() -> None:
    """Exceptions thrown by UserService are also caught."""
    user_service = MagicMock()
    user_service.get_user_public = AsyncMock(side_effect=RuntimeError("db down"))

    fake_client = MagicMock()
    fake_client.create_contact = AsyncMock()

    with (
        patch(
            "integrations.activecampaign.get_activecampaign_client",
            return_value=fake_client,
        ),
        patch("app.domains.user.UserService", user_service),
    ):
        await _sync_to_activecampaign("user-123")

    fake_client.create_contact.assert_not_called()


@pytest.mark.asyncio
async def test_handle_registration_started_schedules_sync_as_background() -> None:
    """Sync must be scheduled as a detached task, not awaited inline — a
    slow AC cannot block the signup HTTP response."""
    spawned: list[tuple[str, object]] = []

    def fake_spawn(coro: object, *, name: str) -> None:
        spawned.append((name, coro))
        # Close the coroutine so pytest doesn't warn about un-awaited coroutines.
        if hasattr(coro, "close"):
            coro.close()

    with patch("app.domains.auth.events._spawn_background", side_effect=fake_spawn):
        await AuthEventHandler.handle_registration_started(
            user_id="user-123", email="alice@example.com"
        )

    assert len(spawned) == 1
    assert spawned[0][0] == "ac-sync-started-user-123"


@pytest.mark.asyncio
async def test_handle_registration_completed_schedules_sync_as_background() -> None:
    """Covers the Google OAuth path where only `completed` fires for new users."""
    spawned: list[tuple[str, object]] = []

    def fake_spawn(coro: object, *, name: str) -> None:
        spawned.append((name, coro))
        if hasattr(coro, "close"):
            coro.close()

    with (
        patch("app.domains.auth.events._spawn_background", side_effect=fake_spawn),
        patch(
            "app.domains.user.UserService.get_user_public",
            new=AsyncMock(return_value=None),
        ),
    ):
        await AuthEventHandler.handle_registration_completed(
            user_id="user-123", provider="google"
        )

    assert len(spawned) == 1
    assert spawned[0][0] == "ac-sync-completed-user-123"


@pytest.mark.asyncio
async def test_spawn_background_runs_and_self_cleans() -> None:
    """Detached task must execute AND be strongly referenced until done,
    then removed from the tracking set — otherwise Python GC can drop the
    task mid-flight."""
    ran = asyncio.Event()

    async def work() -> None:
        ran.set()

    _spawn_background(work(), name="test-ac-task")
    # The task is tracked immediately so GC can't collect it.
    assert any(t.get_name() == "test-ac-task" for t in _background_tasks)
    # The loop runs it and the done-callback removes it.
    await asyncio.wait_for(ran.wait(), timeout=1.0)
    await asyncio.sleep(0)  # yield so the done-callback fires
    assert not any(t.get_name() == "test-ac-task" for t in _background_tasks)


@pytest.mark.asyncio
async def test_handler_returns_before_sync_completes() -> None:
    """End-to-end: the handler must return even if the AC sync is still
    running (or hanging)."""
    # Slow coroutine that takes longer than we're willing to wait for the
    # handler call. If the handler awaits the sync, the assert below will
    # fail because handler_done won't be set until sync_done is.
    sync_started = asyncio.Event()
    allow_sync_finish = asyncio.Event()

    async def slow_sync(_user_id: str) -> None:
        sync_started.set()
        await allow_sync_finish.wait()

    with patch("app.domains.auth.events._sync_to_activecampaign", new=slow_sync):
        # The handler should return while the sync is still blocked.
        await asyncio.wait_for(
            AuthEventHandler.handle_registration_started(
                user_id="user-race", email="x@y.com"
            ),
            timeout=0.5,
        )
        # Sync should have been scheduled and started, but not completed.
        await asyncio.wait_for(sync_started.wait(), timeout=0.5)

    # Let the background task finish so it doesn't hang around.
    allow_sync_finish.set()
    await asyncio.sleep(0)
