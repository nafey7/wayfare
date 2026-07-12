"""Unit tests for PII verification API endpoints."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


@pytest.fixture
def current_user() -> UserPublic:
    """Authenticated user with email."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="John",
        last_name="Doe",
        profile_image=None,
        mobile=None,
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestPiiVerificationRequest:
    """Tests for POST /me/pii-verification/request."""

    @patch("app.api.user.request_pii_verification")
    async def test_request_returns_challenge_and_masked_email(
        self, mock_request: AsyncMock, current_user: UserPublic
    ) -> None:
        from app.api.user import pii_verification_request

        mock_request.return_value = MagicMock(
            challenge_id="ch123",
            masked_email="u***@example.com",
        )

        result = await pii_verification_request(current_user)

        assert result.challenge_id == "ch123"
        assert result.masked_email == "u***@example.com"

    @patch("app.api.user.request_pii_verification")
    async def test_request_no_email_returns_400(self, mock_request: AsyncMock) -> None:
        from app.api.user import pii_verification_request

        user_no_email = SimpleNamespace(email=None)

        with pytest.raises(HTTPException) as exc_info:
            await pii_verification_request(user_no_email)

        assert exc_info.value.status_code == 400
        assert "No email" in exc_info.value.detail
        mock_request.assert_not_called()

    @patch("app.api.user.request_pii_verification")
    async def test_request_rate_limited_returns_429(
        self, mock_request: AsyncMock, current_user: UserPublic
    ) -> None:
        from app.api.user import pii_verification_request

        mock_request.side_effect = ValueError(
            "Too many verification requests. Try again in 5 minutes."
        )

        with pytest.raises(HTTPException) as exc_info:
            await pii_verification_request(current_user)

        assert exc_info.value.status_code == 429
        assert "Too many" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
class TestPiiVerificationVerify:
    """Tests for POST /me/pii-verification/verify."""

    @patch("app.api.user.verify_pii_otp")
    async def test_verify_returns_token(
        self, mock_verify: AsyncMock, current_user: UserPublic
    ) -> None:
        from app.api.user import pii_verification_verify
        from app.domains.pii_verification.schemas import PiiVerificationVerifyRequest

        mock_verify.return_value = MagicMock(
            pii_view_token="eyJ...",
            expires_in_seconds=120,
        )

        request = PiiVerificationVerifyRequest(challenge_id="ch123", code="123456")
        result = await pii_verification_verify(request, current_user)

        assert result.pii_view_token == "eyJ..."
        assert result.expires_in_seconds == 120

    @patch("app.api.user.verify_pii_otp")
    async def test_verify_failure_returns_400(
        self, mock_verify: AsyncMock, current_user: UserPublic
    ) -> None:
        from app.api.user import pii_verification_verify
        from app.domains.pii_verification.schemas import PiiVerificationVerifyRequest

        mock_verify.side_effect = ValueError("Incorrect code. 4 attempt(s) remaining.")

        request = PiiVerificationVerifyRequest(challenge_id="ch123", code="999999")

        with pytest.raises(HTTPException) as exc_info:
            await pii_verification_verify(request, current_user)

        assert exc_info.value.status_code == 400
        assert "Incorrect code" in exc_info.value.detail
