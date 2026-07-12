"""Unit tests for UserService.create_user admin-role injection.

Verifies that @myvoya.ai signups receive role=admin at persistence time,
while other emails are unaffected and explicit roles are never overwritten.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.common import AuthProvider
from app.domains.user.enums import UserRole
from app.domains.user.schemas import UserCreateRequest
from app.domains.user.service import UserService


def _make_user_model(role: str = "user") -> MagicMock:
    model = MagicMock()
    model.role = role
    return model


@pytest.mark.asyncio
async def test_myvoya_email_gets_admin_role() -> None:
    """@myvoya.ai signup should persist role=admin."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model(role=user_dict.get("role", "user"))

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {"email": "team@myvoya.ai", "first_name": "Team", "last_name": "Voya"},
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert captured.get("role") == UserRole.ADMIN


@pytest.mark.asyncio
async def test_myvoya_email_case_insensitive_gets_admin_role() -> None:
    """TEAM@MYVOYA.AI (uppercase) should also receive role=admin."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model(role=user_dict.get("role", "user"))

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {
                "email": "TEAM@MYVOYA.AI",
                "first_name": "Team",
                "last_name": "Voya",
            },
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert captured.get("role") == UserRole.ADMIN


@pytest.mark.asyncio
async def test_myvoya_email_user_create_request_gets_admin_role() -> None:
    """UserCreateRequest path uses str(user_data.email); @myvoya.ai should get admin."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model(role=user_dict.get("role", "user"))

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            UserCreateRequest(
                email="team@myvoya.ai",
                first_name="Team",
                last_name="Voya",
            ),
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert captured.get("role") == UserRole.ADMIN


@pytest.mark.asyncio
async def test_myvoya_email_google_oauth_gets_admin_role() -> None:
    """@myvoya.ai created via Google OAuth should still receive role=admin at signup."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model(role=user_dict.get("role", "user"))

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {"email": "team@myvoya.ai", "first_name": "Team", "last_name": "Voya"},
            auth_provider=AuthProvider.GOOGLE,
            trigger_events=False,
        )

    assert captured.get("role") == UserRole.ADMIN


@pytest.mark.asyncio
async def test_multi_at_email_does_not_get_admin_role_injected() -> None:
    """Invalid multi-@ strings must not match the myvoya team rule via suffix alone."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model()

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {
                "email": "hacker@other@myvoya.ai",
                "first_name": "H",
                "last_name": "K",
            },
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert "role" not in captured


@pytest.mark.asyncio
async def test_non_myvoya_email_does_not_get_role_injected() -> None:
    """Non-@myvoya.ai signup should not have role injected by the service."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model()

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {
                "email": "user@notmyvoya.ai",
                "first_name": "Regular",
                "last_name": "User",
            },
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert "role" not in captured


@pytest.mark.asyncio
async def test_explicit_role_in_caller_dict_is_not_overwritten() -> None:
    """If caller already set a role in user_dict, service must not override it."""
    captured: dict = {}

    async def fake_create(user_dict):
        captured.update(user_dict)
        return _make_user_model(role=user_dict.get("role", "user"))

    with (
        patch(
            "app.domains.user.service.validators.validate_email_uniqueness",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.repository.create_user",
            side_effect=fake_create,
        ),
        patch(
            "app.domains.user.service.UserEventHandler.handle_user_created",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.user.service.UserPublic.from_model",
            return_value=MagicMock(),
        ),
    ):
        await UserService.create_user(
            {
                "email": "admin@myvoya.ai",
                "first_name": "Admin",
                "last_name": "User",
                "role": UserRole.SUPER_ADMIN,
            },
            auth_provider=AuthProvider.LOCAL,
            trigger_events=False,
        )

    assert captured.get("role") == UserRole.SUPER_ADMIN
