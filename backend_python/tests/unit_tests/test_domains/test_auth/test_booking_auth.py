"""Unit tests for booking token exchange (authenticated email links)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.domains.auth.booking_auth import exchange_booking_token


def _make_booking_token(user_id: str, exp_offset_days: int = 60) -> str:
    """Build a valid booking_auth JWT with exp ~2 months ahead."""
    from app.core.config import settings

    now = datetime.now(UTC)
    exp = now + timedelta(days=exp_offset_days)
    payload = {
        "user_id": user_id,
        "type": "booking_auth",
        "exp": exp.timestamp(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


class TestExchangeBookingTokenCurrentUserMismatch:
    """Test 403 when logged-in user does not match token user."""

    @pytest.mark.asyncio
    async def test_returns_403_when_current_user_differs_from_token_user(self):
        """Token for user_a used while logged in as user_b returns 403."""
        token = _make_booking_token("user_a")

        with pytest.raises(HTTPException) as exc_info:
            await exchange_booking_token(token, current_user_id="user_b")

        assert exc_info.value.status_code == 403
        assert "different account" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_returns_403_when_current_user_id_string_mismatch(self):
        """Token user_id and current_user_id compared as strings (e.g. ObjectId vs str)."""
        token = _make_booking_token("507f1f77bcf86cd799439011")

        with pytest.raises(HTTPException) as exc_info:
            await exchange_booking_token(
                token, current_user_id="507f1f77bcf86cd799439012"
            )

        assert exc_info.value.status_code == 403


class TestExchangeBookingTokenCurrentUserMatch:
    """Test success when current user matches token or no current user."""

    @pytest.mark.asyncio
    @patch("app.domains.auth.booking_auth.AuthService.create_session")
    @patch("app.domains.auth.booking_auth.UserService.get_user_public")
    async def test_success_when_current_user_matches_token_user(
        self, mock_get_user: AsyncMock, mock_create_session: AsyncMock
    ):
        """When current_user_id equals token user_id, exchange succeeds."""
        token = _make_booking_token("user_same")
        mock_user = MagicMock()
        mock_user.id = "user_same"
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_session.id = "sess_123"
        mock_create_session.return_value = (
            mock_session,
            "access_token_xyz",
            "refresh_token_xyz",
        )

        result = await exchange_booking_token(token, current_user_id="user_same")

        assert result["access_token"] == "access_token_xyz"
        assert result["refresh_token"] == "refresh_token_xyz"
        assert result["user_id"] == "user_same"
        mock_get_user.assert_called_once_with("user_same")
        mock_create_session.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.auth.booking_auth.AuthService.create_session")
    @patch("app.domains.auth.booking_auth.UserService.get_user_public")
    async def test_success_when_no_current_user(
        self, mock_get_user: AsyncMock, mock_create_session: AsyncMock
    ):
        """When current_user_id is None (anonymous click), exchange succeeds."""
        token = _make_booking_token("user_email_link")
        mock_user = MagicMock()
        mock_user.id = "user_email_link"
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_session.id = "sess_456"
        mock_create_session.return_value = (
            mock_session,
            "access_abc",
            "refresh_abc",
        )

        result = await exchange_booking_token(token, current_user_id=None)

        assert result["access_token"] == "access_abc"
        assert result["user_id"] == "user_email_link"
        mock_get_user.assert_called_once_with("user_email_link")
        mock_create_session.assert_called_once()
