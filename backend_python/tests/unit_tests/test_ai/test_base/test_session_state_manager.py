"""Unit tests for SessionStateManager."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.base.session_state import SessionType
from app.ai.base.session_state_manager import SessionStateManager


class TestSessionStateManagerSearchResults:
    """Tests for in-memory search results management."""

    def test_store_and_get_search_results(self) -> None:
        """Test storing and retrieving search results."""
        manager = SessionStateManager()
        results = {"flights": [{"id": 1}, {"id": 2}]}

        manager.store_search_results("chat_123", results)
        retrieved = manager.get_search_results("chat_123")

        assert retrieved == results

    def test_get_nonexistent_search_results(self) -> None:
        """Test getting search results for non-existent session."""
        manager = SessionStateManager()

        result = manager.get_search_results("nonexistent")

        assert result is None

    def test_clear_search_results(self) -> None:
        """Test clearing search results."""
        manager = SessionStateManager()
        manager.store_search_results("chat_123", {"flights": []})

        manager.clear_search_results("chat_123")

        assert manager.get_search_results("chat_123") is None

    def test_clear_nonexistent_search_results(self) -> None:
        """Test clearing non-existent search results doesn't raise."""
        manager = SessionStateManager()

        # Should not raise
        manager.clear_search_results("nonexistent")

    def test_has_search_results(self) -> None:
        """Test checking if search results exist."""
        manager = SessionStateManager()

        assert manager.has_search_results("chat_123") is False

        manager.store_search_results("chat_123", {"flights": []})

        assert manager.has_search_results("chat_123") is True

    def test_search_results_isolation(self) -> None:
        """Test that search results are isolated between sessions."""
        manager = SessionStateManager()

        manager.store_search_results("session_a", {"flights": [{"id": "a1"}]})
        manager.store_search_results("session_b", {"hotels": [{"id": "b1"}]})

        assert manager.get_search_results("session_a") == {"flights": [{"id": "a1"}]}
        assert manager.get_search_results("session_b") == {"hotels": [{"id": "b1"}]}


class TestSessionStateManagerGetState:
    """Tests for get_state method."""

    @pytest.mark.asyncio
    async def test_get_state_returns_none_when_not_found(self) -> None:
        """Test get_state returns None when session doesn't exist."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await manager.get_state("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_returns_session_state(self) -> None:
        """Test get_state returns SessionState when found."""
        manager = SessionStateManager()
        mock_data = {
            "data": {
                "session_id": "chat_123",
                "user_id": "user_456",
                "session_type": "flight",
                "collected": {"origin": "LHR"},
                "waiting_for_field": None,
                "waiting_for_airport_selection": None,
                "pending_date_range": None,
                "pending_disambiguation": None,
                "last_question": None,
                "booking_stage": None,
                "selected_option_index": None,
                "context": {},
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.get_session",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await manager.get_state("chat_123")

        assert result is not None
        assert result.session_id == "chat_123"
        assert result.collected["origin"] == "LHR"

    @pytest.mark.asyncio
    async def test_get_state_handles_invalid_data(self) -> None:
        """Test get_state returns None for invalid data."""
        manager = SessionStateManager()
        mock_data = {"data": {"invalid": "data"}}

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.get_session",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await manager.get_state("chat_123")

        assert result is None


class TestSessionStateManagerCreateState:
    """Tests for create_state method."""

    @pytest.mark.asyncio
    async def test_create_state(self) -> None:
        """Test creating new session state."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.store_session",
            new_callable=AsyncMock,
        ) as mock_store:
            result = await manager.create_state(
                session_id="chat_123",
                user_id="user_456",
                session_type=SessionType.FLIGHT,
            )

        assert result.session_id == "chat_123"
        assert result.user_id == "user_456"
        assert result.session_type == SessionType.FLIGHT
        mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_state_with_custom_ttl(self) -> None:
        """Test creating state with custom TTL."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.store_session",
            new_callable=AsyncMock,
        ) as mock_store:
            await manager.create_state(
                session_id="chat_123",
                user_id="user_456",
                session_type=SessionType.HOTEL,
                ttl_hours=5,
            )

        call_kwargs = mock_store.call_args.kwargs
        assert call_kwargs["ttl_hours"] == 5


class TestSessionStateManagerGetOrCreateState:
    """Tests for get_or_create_state method."""

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self) -> None:
        """Test get_or_create returns existing state."""
        manager = SessionStateManager()
        mock_data = {
            "data": {
                "session_id": "chat_123",
                "user_id": "user_456",
                "session_type": "flight",
                "collected": {"origin": "LHR"},
                "waiting_for_field": None,
                "waiting_for_airport_selection": None,
                "pending_date_range": None,
                "pending_disambiguation": None,
                "last_question": None,
                "booking_stage": None,
                "selected_option_index": None,
                "context": {},
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.get_session",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = await manager.get_or_create_state(
                session_id="chat_123",
                user_id="user_456",
                session_type=SessionType.FLIGHT,
            )

        assert result.collected["origin"] == "LHR"

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self) -> None:
        """Test get_or_create creates new state when not found."""
        manager = SessionStateManager()

        with (
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.get_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.store_session",
                new_callable=AsyncMock,
            ) as mock_store,
        ):
            result = await manager.get_or_create_state(
                session_id="chat_123",
                user_id="user_456",
                session_type=SessionType.FLIGHT,
            )

        assert result.session_id == "chat_123"
        assert result.collected == {}
        mock_store.assert_called_once()


class TestSessionStateManagerUpdateState:
    """Tests for update_state method."""

    @pytest.mark.asyncio
    async def test_update_state(self) -> None:
        """Test updating session state."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.update_session_data",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            result = await manager.update_state(
                session_id="chat_123",
                collected={"origin": "LHR"},
                waiting_for_field="destination",
            )

        assert result is True
        # Check the call was made with correct session_id and updates dict
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == "chat_123"  # session_id
        updates = call_args[0][1]  # updates dict
        assert updates["collected"] == {"origin": "LHR"}
        assert updates["waiting_for_field"] == "destination"
        assert "updated_at" in updates

    @pytest.mark.asyncio
    async def test_update_state_returns_false_on_failure(self) -> None:
        """Test update_state returns False on failure."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.update_session_data",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await manager.update_state(
                session_id="chat_123",
                collected={"origin": "LHR"},
            )

        assert result is False


class TestSessionStateManagerUpdateCollected:
    """Tests for update_collected method."""

    @pytest.mark.asyncio
    async def test_update_collected_merges_fields(self) -> None:
        """Test update_collected merges new fields with existing."""
        manager = SessionStateManager()
        mock_data = {
            "data": {
                "session_id": "chat_123",
                "user_id": "user_456",
                "session_type": "flight",
                "collected": {"origin": "LHR"},
                "waiting_for_field": None,
                "waiting_for_airport_selection": None,
                "pending_date_range": None,
                "pending_disambiguation": None,
                "last_question": None,
                "booking_stage": None,
                "selected_option_index": None,
                "context": {},
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

        with (
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.get_session",
                new_callable=AsyncMock,
                return_value=mock_data,
            ),
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.update_session_data",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_update,
        ):
            result = await manager.update_collected(
                session_id="chat_123",
                destination="CDG",
            )

        assert result is True
        # Check the call was made with correct session_id and updates dict
        call_args = mock_update.call_args
        assert call_args[0][0] == "chat_123"  # session_id
        updates = call_args[0][1]  # updates dict
        # Should contain both existing and new fields
        assert updates["collected"]["origin"] == "LHR"
        assert updates["collected"]["destination"] == "CDG"

    @pytest.mark.asyncio
    async def test_update_collected_filters_none(self) -> None:
        """Test update_collected filters out None values."""
        manager = SessionStateManager()
        mock_data = {
            "data": {
                "session_id": "chat_123",
                "user_id": "user_456",
                "session_type": "flight",
                "collected": {"origin": "LHR"},
                "waiting_for_field": None,
                "waiting_for_airport_selection": None,
                "pending_date_range": None,
                "pending_disambiguation": None,
                "last_question": None,
                "booking_stage": None,
                "selected_option_index": None,
                "context": {},
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

        with (
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.get_session",
                new_callable=AsyncMock,
                return_value=mock_data,
            ),
            patch(
                "app.ai.base.session_state_manager.BookingSessionService.update_session_data",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_update,
        ):
            await manager.update_collected(
                session_id="chat_123",
                destination="CDG",
                return_date=None,  # Should be filtered out
            )

        # Check the call was made with correct session_id and updates dict
        call_args = mock_update.call_args
        updates = call_args[0][1]  # updates dict
        assert "return_date" not in updates["collected"]

    @pytest.mark.asyncio
    async def test_update_collected_returns_false_when_session_not_found(self) -> None:
        """Test update_collected returns False when session doesn't exist."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await manager.update_collected(
                session_id="nonexistent",
                destination="CDG",
            )

        assert result is False


class TestSessionStateManagerDeleteState:
    """Tests for delete_state method."""

    @pytest.mark.asyncio
    async def test_delete_state(self) -> None:
        """Test deleting session state."""
        manager = SessionStateManager()
        manager.store_search_results("chat_123", {"flights": []})

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.delete_session",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            result = await manager.delete_state("chat_123")

        assert result is True
        mock_delete.assert_called_once_with("chat_123")
        # Search results should also be cleared
        assert manager.get_search_results("chat_123") is None

    @pytest.mark.asyncio
    async def test_delete_state_returns_false_on_failure(self) -> None:
        """Test delete_state returns False on failure."""
        manager = SessionStateManager()

        with patch(
            "app.ai.base.session_state_manager.BookingSessionService.delete_session",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await manager.delete_state("chat_123")

        assert result is False
