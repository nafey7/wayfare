from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.domains.agent_prompt.schemas import (
    AgentPromptCreate,
    AgentPromptResponse,
    AgentPromptUpdate,
)
from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_admin() -> UserPublic:
    """Mock admin user for testing."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_agent_prompt_response() -> AgentPromptResponse:
    """Mock agent prompt response for testing."""
    now = datetime.utcnow()
    return AgentPromptResponse(
        agent_name="general_travel_handler",
        goal="Handle general travel queries with AI-powered responses",
        prompt_template="You are MyVoya, a helpful AI travel assistant. User: {message}",
        is_active=True,
        id="507f1f77bcf86cd799439012",
        created_at=now,
        updated_at=now,
        created_by="admin@example.com",
        updated_by="admin@example.com",
    )


@pytest.fixture
def mock_update_data() -> AgentPromptUpdate:
    """Mock update data for testing."""
    return AgentPromptUpdate(
        goal="Updated goal for travel handling",
        prompt_template="Updated template: You are MyVoya. User says: {message}",
        is_active=False,
    )


@pytest.fixture
def mock_create_data() -> AgentPromptCreate:
    """Mock create data for testing."""
    return AgentPromptCreate(
        agent_name="test_agent",
        goal="Test agent for unit testing",
        prompt_template="Test template: {message}",
        is_active=True,
    )


# ==============================================================================
# GET AGENT PROMPT ENDPOINT TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_get_agent_prompt_success(
    mock_admin: UserPublic, mock_agent_prompt_response: AgentPromptResponse
) -> None:
    """Test successfully getting an agent prompt."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
    ):
        mock_get.return_value = mock_agent_prompt_response

        # Import and call the endpoint function directly
        from app.api.admin import get_agent_prompt

        result = await get_agent_prompt("general_travel_handler", mock_admin)

        assert result == mock_agent_prompt_response
        mock_get.assert_called_once_with("general_travel_handler")


@pytest.mark.asyncio
async def test_get_agent_prompt_not_found(mock_admin: UserPublic) -> None:
    """Test getting an agent prompt that doesn't exist."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
    ):
        mock_get.return_value = None

        from app.api.admin import get_agent_prompt

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_prompt("nonexistent_agent", mock_admin)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "No prompt found for agent: nonexistent_agent" in str(
            exc_info.value.detail
        )


@pytest.mark.asyncio
async def test_get_agent_prompt_service_error(mock_admin: UserPublic) -> None:
    """Test getting an agent prompt when service throws an error."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
    ):
        mock_get.side_effect = Exception("Database connection failed")

        from app.api.admin import get_agent_prompt

        with pytest.raises(Exception, match="Database connection failed"):
            await get_agent_prompt("general_travel_handler", mock_admin)


# ==============================================================================
# CREATE AGENT PROMPT ENDPOINT TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_agent_prompt_success(
    mock_admin: UserPublic,
    mock_create_data: AgentPromptCreate,
    mock_agent_prompt_response: AgentPromptResponse,
) -> None:
    """Test successfully creating an agent prompt."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.create_prompt", new_callable=AsyncMock
        ) as mock_create,
    ):
        mock_create.return_value = mock_agent_prompt_response

        from app.api.admin import create_agent_prompt

        result = await create_agent_prompt(mock_create_data, mock_admin)

        assert result == mock_agent_prompt_response
        mock_create.assert_called_once_with(mock_create_data, mock_admin.id)


@pytest.mark.asyncio
async def test_create_agent_prompt_service_error(
    mock_admin: UserPublic, mock_create_data: AgentPromptCreate
) -> None:
    """Test creating an agent prompt when service fails."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.create_prompt", new_callable=AsyncMock
        ) as mock_create,
    ):
        mock_create.side_effect = Exception("Failed to create prompt")

        from app.api.admin import create_agent_prompt

        with pytest.raises(Exception, match="Failed to create prompt"):
            await create_agent_prompt(mock_create_data, mock_admin)


# ==============================================================================
# UPDATE AGENT PROMPT ENDPOINT TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_update_agent_prompt_success(
    mock_admin: UserPublic,
    mock_update_data: AgentPromptUpdate,
    mock_agent_prompt_response: AgentPromptResponse,
) -> None:
    """Test successfully updating an agent prompt with comprehensive logging."""
    current_prompt = AgentPromptResponse(
        agent_name="general_travel_handler",
        goal="Old goal",
        prompt_template="Old template: {message}",
        is_active=True,
        id="507f1f77bcf86cd799439012",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("logging.getLogger") as mock_get_logger,
    ):
        # Setup mocks
        mock_get.return_value = current_prompt
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        result = await update_agent_prompt(
            "general_travel_handler", mock_update_data, mock_admin
        )

        # Verify result
        assert result == mock_agent_prompt_response

        # Verify service calls
        mock_get.assert_called_once_with("general_travel_handler")
        mock_update.assert_called_once_with(
            "general_travel_handler", mock_update_data, mock_admin.id
        )

        # Verify logging behavior
        assert mock_logger.info.call_count >= 8  # Should have multiple info logs

        # Check specific log messages
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(
            "Admin admin@example.com updating prompt for agent: general_travel_handler"
            in log
            for log in log_calls
        )
        assert any(
            f"Current prompt for {current_prompt.agent_name}" in log
            for log in log_calls
        )


@pytest.mark.asyncio
async def test_update_agent_prompt_not_found(
    mock_admin: UserPublic, mock_update_data: AgentPromptUpdate
) -> None:
    """Test updating an agent prompt that doesn't exist."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None
        mock_update.return_value = None
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        with pytest.raises(HTTPException) as exc_info:
            await update_agent_prompt("nonexistent_agent", mock_update_data, mock_admin)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "No prompt found for agent: nonexistent_agent" in str(
            exc_info.value.detail
        )

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_log = mock_logger.error.call_args[0][0]
        assert (
            "❌ [Prompt Update] Failed to update prompt for agent: nonexistent_agent"
            in error_log
        )


@pytest.mark.asyncio
async def test_update_agent_prompt_get_current_fails(
    mock_admin: UserPublic,
    mock_update_data: AgentPromptUpdate,
    mock_agent_prompt_response: AgentPromptResponse,
) -> None:
    """Test updating when getting current prompt fails but update still succeeds."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger") as mock_get_agents_logger,
        patch("logging.getLogger") as mock_get_logger,
    ):
        # Setup mocks - get current fails but update succeeds
        mock_get.side_effect = Exception("Database error getting current")
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_agents_logger = MagicMock()
        mock_get_agents_logger.return_value = mock_agents_logger

        from app.api.admin import update_agent_prompt

        result = await update_agent_prompt(
            "general_travel_handler", mock_update_data, mock_admin
        )

        # Should still succeed
        assert result == mock_agent_prompt_response

        # Verify warning logged for get failure
        mock_logger.warning.assert_called_once()
        warning_log = mock_logger.warning.call_args[0][0]
        assert "Could not fetch current prompt" in warning_log


@pytest.mark.asyncio
async def test_update_agent_prompt_partial_update(
    mock_admin: UserPublic, mock_agent_prompt_response: AgentPromptResponse
) -> None:
    """Test updating with partial data (only some fields)."""
    partial_update = AgentPromptUpdate(
        goal="Only updating the goal",
        # prompt_template and is_active not provided
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger"),
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None  # No current prompt
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        result = await update_agent_prompt("test_agent", partial_update, mock_admin)

        assert result == mock_agent_prompt_response
        mock_update.assert_called_once_with("test_agent", partial_update, mock_admin.id)

        # Check that None values are logged properly
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Template (first 200 chars): None..." in log for log in log_calls)


@pytest.mark.asyncio
async def test_update_agent_prompt_field_name_consistency(
    mock_admin: UserPublic, mock_agent_prompt_response: AgentPromptResponse
) -> None:
    """Test that update endpoint correctly handles prompt_template field name."""
    # This is a regression test for the field name mismatch bug
    update_data = AgentPromptUpdate(
        goal="Test goal",
        prompt_template="Test template: {message}",  # Use correct field name
        is_active=True,
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger"),
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        # This should NOT raise AttributeError about 'template' field
        result = await update_agent_prompt("test_agent", update_data, mock_admin)

        assert result == mock_agent_prompt_response

        # Verify the correct field name is accessed in logging
        # Should access prompt_template, not template
        assert hasattr(update_data, "prompt_template")
        assert not hasattr(update_data, "template")


# ==============================================================================
# LOGGING VERIFICATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_update_agent_prompt_comprehensive_logging(
    mock_admin: UserPublic,
    mock_update_data: AgentPromptUpdate,
    mock_agent_prompt_response: AgentPromptResponse,
) -> None:
    """Test that all required logging occurs during prompt update."""
    current_prompt = AgentPromptResponse(
        agent_name="general_travel_handler",
        goal="Current goal",
        prompt_template="Current template: {message}"
        * 10,  # Make it longer than 200 chars
        is_active=True,
        id="507f1f77bcf86cd799439012",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger") as mock_get_agents_logger,
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = current_prompt
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_agents_logger = MagicMock()
        mock_get_agents_logger.return_value = mock_agents_logger

        from app.api.admin import update_agent_prompt

        await update_agent_prompt(
            "general_travel_handler", mock_update_data, mock_admin
        )

        # Verify comprehensive logging occurred
        log_messages = [call.args[0] for call in mock_logger.info.call_args_list]

        # Check for key log message types
        assert any(
            "Admin admin@example.com updating prompt" in msg for msg in log_messages
        )
        assert any(
            "Current prompt for general_travel_handler" in msg for msg in log_messages
        )
        assert any("New data for general_travel_handler" in msg for msg in log_messages)
        assert any("Successfully updated prompt" in msg for msg in log_messages)
        assert any(
            "Final state for general_travel_handler" in msg for msg in log_messages
        )

        # Check template truncation in logging (first 200 chars)
        template_logs = [
            msg for msg in log_messages if "Template (first 200 chars)" in msg
        ]
        assert len(template_logs) >= 1

        # Verify agents logger was called
        mock_agents_logger.info.assert_called_once()
        agents_log = mock_agents_logger.info.call_args[0][0]
        assert "🔄 PROMPT_UPDATE" in agents_log
        assert mock_agent_prompt_response.goal in agents_log


# ==============================================================================
# ERROR HANDLING AND EDGE CASES
# ==============================================================================


@pytest.mark.asyncio
async def test_update_agent_prompt_with_empty_template(
    mock_admin: UserPublic, mock_agent_prompt_response: AgentPromptResponse
) -> None:
    """Test updating with empty template."""
    empty_template_update = AgentPromptUpdate(
        goal="Test goal",
        prompt_template="",  # Empty template
        is_active=True,
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger"),
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        result = await update_agent_prompt(
            "test_agent", empty_template_update, mock_admin
        )

        assert result == mock_agent_prompt_response

        # Check logging handles empty template correctly
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        # Should not crash when accessing empty template for logging
        assert any("Template (first 200 chars):" in log for log in log_calls)


@pytest.mark.asyncio
async def test_update_agent_prompt_service_exception(
    mock_admin: UserPublic, mock_update_data: AgentPromptUpdate
) -> None:
    """Test handling when update service raises an exception."""
    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None
        mock_update.side_effect = Exception("Service update failed")
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        with pytest.raises(Exception, match="Service update failed"):
            await update_agent_prompt("test_agent", mock_update_data, mock_admin)


@pytest.mark.asyncio
async def test_update_agent_prompt_none_fields_logging(
    mock_admin: UserPublic, mock_agent_prompt_response: AgentPromptResponse
) -> None:
    """Test that logging handles None values gracefully."""
    update_with_nones = AgentPromptUpdate(
        goal=None,  # All fields None
        prompt_template=None,
        is_active=None,
    )

    with (
        patch("app.api.admin.require_admin", return_value=mock_admin),
        patch(
            "app.api.admin.agent_prompt_service.get_prompt_by_agent",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.api.admin.agent_prompt_service.update_prompt", new_callable=AsyncMock
        ) as mock_update,
        patch("app.core.logging.get_agents_logger"),
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_get.return_value = None
        mock_update.return_value = mock_agent_prompt_response
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from app.api.admin import update_agent_prompt

        result = await update_agent_prompt("test_agent", update_with_nones, mock_admin)

        assert result == mock_agent_prompt_response

        # Verify logging doesn't crash with None values
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Template (first 200 chars): None..." in log for log in log_calls)
