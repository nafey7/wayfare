"""Unit tests for AuthService.refresh_access_token method."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from app.database.models.session import SessionModel
from app.domains.auth import AuthService

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_session():
    """Create a mock session model."""
    user_id = ObjectId()
    session_id = ObjectId()
    now = datetime.now(UTC)

    return SessionModel(
        id=session_id,
        user_id=user_id,
        refresh_token="valid-refresh-token-123",
        refresh_token_expires=now + timedelta(days=30),
        status=1,  # ACTIVE
        created_at=now,
        last_activity=now,
    )


@pytest.fixture
def expired_session():
    """Create an expired session model."""
    user_id = ObjectId()
    session_id = ObjectId()
    now = datetime.now(UTC)

    return SessionModel(
        id=session_id,
        user_id=user_id,
        refresh_token="expired-refresh-token",
        refresh_token_expires=now - timedelta(days=1),  # Expired
        status=1,
        created_at=now - timedelta(days=31),
        last_activity=now - timedelta(days=1),
    )


# ==============================================================================
# UNIT TESTS FOR refresh_access_token
# ==============================================================================


class TestRefreshAccessToken:
    """Test AuthService.refresh_access_token method."""

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.update_refresh_token")
    @patch("app.domains.auth.service.auth_repo.update_session_activity")
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    @patch("app.domains.auth.service.AuthEventHandler.handle_token_refreshed")
    async def test_refresh_access_token_success(
        self,
        mock_handle_event: AsyncMock,
        mock_get_session: AsyncMock,
        mock_update_activity: AsyncMock,
        mock_update_refresh: AsyncMock,
        mock_session: SessionModel,
    ):
        """Test successful token refresh with valid refresh token."""
        # Setup mocks
        mock_get_session.return_value = mock_session
        mock_update_activity.return_value = True
        mock_update_refresh.return_value = True
        mock_handle_event.return_value = None

        # Call the method
        result = await AuthService.refresh_access_token("valid-refresh-token-123")

        # Verify result
        assert result is not None
        access_token, refresh_token = result
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 0
        assert len(refresh_token) > 0

        # Verify repository calls
        mock_get_session.assert_called_once_with("valid-refresh-token-123")
        mock_update_activity.assert_called_once_with(str(mock_session.id))
        mock_update_refresh.assert_called_once()

        # Verify refresh token was updated (check it's a new token)
        call_args = mock_update_refresh.call_args
        assert call_args[0][0] == str(mock_session.id)
        new_refresh_token = call_args[0][1]
        assert new_refresh_token != "valid-refresh-token-123"  # Should be different

        # Verify event handler was called
        mock_handle_event.assert_called_once_with(
            user_id=str(mock_session.user_id),
            session_id=str(mock_session.id),
        )

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    async def test_refresh_access_token_invalid_token(
        self,
        mock_get_session: AsyncMock,
    ):
        """Test refresh with invalid refresh token (session not found)."""
        # Setup mock - session not found
        mock_get_session.return_value = None

        # Call the method
        result = await AuthService.refresh_access_token("invalid-refresh-token")

        # Verify result
        assert result is None

        # Verify repository was called
        mock_get_session.assert_called_once_with("invalid-refresh-token")

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    async def test_refresh_access_token_expired_session(
        self,
        mock_get_session: AsyncMock,
        expired_session: SessionModel,
    ):
        """Test refresh with expired refresh token."""
        # Setup mock - expired session (repository should filter this, but test edge case)
        mock_get_session.return_value = None  # Repository filters expired sessions

        # Call the method
        result = await AuthService.refresh_access_token("expired-refresh-token")

        # Verify result
        assert result is None

        # Verify repository was called
        mock_get_session.assert_called_once_with("expired-refresh-token")

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.update_refresh_token")
    @patch("app.domains.auth.service.auth_repo.update_session_activity")
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    async def test_refresh_access_token_missing_user_id(
        self,
        mock_get_session: AsyncMock,
        mock_update_activity: AsyncMock,
        mock_update_refresh: AsyncMock,
    ):
        """Test refresh when session has no user_id."""
        # Create session without user_id
        session_id = ObjectId()
        session_without_user = SessionModel(
            id=session_id,
            user_id=None,  # Missing user_id
            refresh_token="token-without-user",
            refresh_token_expires=datetime.now(UTC) + timedelta(days=30),
            status=1,
        )

        mock_get_session.return_value = session_without_user
        mock_update_activity.return_value = True

        # Call the method
        result = await AuthService.refresh_access_token("token-without-user")

        # Verify result is None (user_id required)
        assert result is None

        # Verify update_refresh_token was NOT called
        mock_update_refresh.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.update_refresh_token")
    @patch("app.domains.auth.service.auth_repo.update_session_activity")
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    async def test_refresh_access_token_missing_session_id(
        self,
        mock_get_session: AsyncMock,
        mock_update_activity: AsyncMock,
        mock_update_refresh: AsyncMock,
    ):
        """Test refresh when session has no id."""
        # Create session without id
        user_id = ObjectId()
        session_without_id = SessionModel(
            id=None,  # Missing session id
            user_id=user_id,
            refresh_token="token-without-session-id",
            refresh_token_expires=datetime.now(UTC) + timedelta(days=30),
            status=1,
        )

        mock_get_session.return_value = session_without_id
        mock_update_activity.return_value = True

        # Call the method
        result = await AuthService.refresh_access_token("token-without-session-id")

        # Verify result is None (session_id required)
        assert result is None

        # Verify update_refresh_token was NOT called
        mock_update_refresh.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.update_refresh_token")
    @patch("app.domains.auth.service.auth_repo.update_session_activity")
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    @patch("app.domains.auth.service.AuthEventHandler.handle_token_refreshed")
    async def test_refresh_access_token_update_failure(
        self,
        mock_handle_event: AsyncMock,
        mock_get_session: AsyncMock,
        mock_update_activity: AsyncMock,
        mock_update_refresh: AsyncMock,
        mock_session: SessionModel,
    ):
        """Test refresh when token update fails - should return None if DB update fails."""
        # Setup mocks
        mock_get_session.return_value = mock_session
        mock_update_activity.return_value = True
        mock_update_refresh.return_value = False  # Update failed
        mock_handle_event.return_value = None

        # Call the method
        result = await AuthService.refresh_access_token("valid-refresh-token-123")

        # If DB update fails, return None (tokens not persisted)
        assert result is None

        # Verify repository methods were called
        mock_get_session.assert_called_once()
        mock_update_activity.assert_called_once()
        mock_update_refresh.assert_called_once()

        # Event handler should NOT be called if update failed
        mock_handle_event.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.domains.auth.service.auth_repo.update_refresh_token")
    @patch("app.domains.auth.service.auth_repo.update_session_activity")
    @patch("app.domains.auth.service.auth_repo.get_session_by_refresh_token")
    @patch("app.domains.auth.service.AuthEventHandler.handle_token_refreshed")
    async def test_refresh_access_token_generates_new_tokens(
        self,
        mock_handle_event: AsyncMock,
        mock_get_session: AsyncMock,
        mock_update_activity: AsyncMock,
        mock_update_refresh: AsyncMock,
        mock_session: SessionModel,
    ):
        """Test that refresh generates new refresh tokens (access tokens may be same if generated at same second)."""
        # Setup mocks
        mock_get_session.return_value = mock_session
        mock_update_activity.return_value = True
        mock_update_refresh.return_value = True
        mock_handle_event.return_value = None

        # Call the method twice with same refresh token
        result1 = await AuthService.refresh_access_token("valid-refresh-token-123")
        result2 = await AuthService.refresh_access_token("valid-refresh-token-123")

        # Verify both calls succeeded
        assert result1 is not None
        assert result2 is not None

        access_token1, refresh_token1 = result1
        access_token2, refresh_token2 = result2

        # Refresh tokens should always be different (random generation)
        assert refresh_token1 != refresh_token2, "Refresh tokens should be different"

        # Verify refresh token was updated twice with different values
        assert mock_update_refresh.call_count == 2
        first_new_token = mock_update_refresh.call_args_list[0][0][1]
        second_new_token = mock_update_refresh.call_args_list[1][0][1]
        assert first_new_token != second_new_token, (
            "Repository should receive different refresh tokens"
        )

        # Access tokens may be the same if generated in the same second (JWT is deterministic)
        # But they should be valid JWT tokens
        assert len(access_token1) > 0
        assert len(access_token2) > 0
