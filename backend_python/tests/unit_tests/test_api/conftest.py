"""Shared fixtures for ``tests/unit_tests/test_api``."""

from datetime import datetime

import pytest

from app.domains.user.schemas import UserPublic


@pytest.fixture
def fake_user_public() -> UserPublic:
    """Minimal ``UserPublic`` for auth-gated route tests.

    Uses ``model_construct`` to skip validation — these tests only need the
    dependency override to resolve to a user-shaped object, not a fully
    validated one.
    """
    return UserPublic.model_construct(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="A",
        last_name="B",
        role="user",
        status="active",
        email_verified=True,
        is_tester=False,
        discount_eligible=False,
        auth_provider="local",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_login=None,
        mobile=None,
        profile_image=None,
        timezone=None,
        address=None,
    )
