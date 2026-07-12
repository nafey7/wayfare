"""Standalone unit tests for agent prompt schemas without database dependencies."""

import os

# Import the schema file directly
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../app/domains/agent_prompt")
)

from schemas import (
    AgentPromptBase,
    AgentPromptCreate,
    AgentPromptResponse,
    AgentPromptUpdate,
)

# ==============================================================================
# AGENT PROMPT BASE SCHEMA TESTS
# ==============================================================================


def test_agent_prompt_base_valid_data() -> None:
    """Test AgentPromptBase with valid data."""
    data = {
        "agent_name": "general_travel_handler",
        "goal": "Handle general travel queries with AI-powered responses",
        "prompt_template": "You are MyVoya, a helpful AI travel assistant. User: {message}",
        "is_active": True,
    }

    prompt = AgentPromptBase(**data)

    assert prompt.agent_name == "general_travel_handler"
    assert prompt.goal == "Handle general travel queries with AI-powered responses"
    assert (
        prompt.prompt_template
        == "You are MyVoya, a helpful AI travel assistant. User: {message}"
    )
    assert prompt.is_active is True


def test_agent_prompt_base_default_active() -> None:
    """Test AgentPromptBase defaults is_active to True."""
    data = {
        "agent_name": "intent_recognizer",
        "goal": "Classify user messages into intents",
        "prompt_template": "Classify this message: {message}",
    }

    prompt = AgentPromptBase(**data)
    assert prompt.is_active is True


def test_agent_prompt_base_missing_required_fields() -> None:
    """Test AgentPromptBase validation with missing required fields."""
    with pytest.raises(ValidationError) as exc_info:
        AgentPromptBase()

    errors = exc_info.value.errors()
    error_fields = [error["loc"][0] for error in errors]

    assert "agent_name" in error_fields
    assert "goal" in error_fields
    assert "prompt_template" in error_fields


# ==============================================================================
# AGENT PROMPT UPDATE SCHEMA TESTS
# ==============================================================================


def test_agent_prompt_update_all_optional() -> None:
    """Test AgentPromptUpdate with all fields optional."""
    # Should allow empty update
    prompt = AgentPromptUpdate()

    assert prompt.goal is None
    assert prompt.prompt_template is None
    assert prompt.is_active is None


def test_agent_prompt_update_field_name_consistency() -> None:
    """Test that AgentPromptUpdate uses correct field names (catches field name bugs)."""
    data = {
        "goal": "Test goal",
        "prompt_template": "Test template: {message}",  # This is the correct field name
        "is_active": False,
    }

    prompt = AgentPromptUpdate(**data)

    # These should work - if they fail, there's a field name mismatch
    assert hasattr(prompt, "prompt_template")
    assert prompt.prompt_template == "Test template: {message}"

    # This should NOT work - if it does, there's a field name inconsistency
    assert not hasattr(prompt, "template")


# ==============================================================================
# FIELD NAME REGRESSION TESTS
# ==============================================================================


def test_schema_field_names_consistency() -> None:
    """Regression test to ensure field name consistency across schemas."""
    # This test specifically catches the bug we had where frontend sent
    # 'template' but backend expected 'prompt_template'

    # Test that all schemas use 'prompt_template', not 'template'
    base_fields = set(AgentPromptBase.model_fields.keys())
    create_fields = set(AgentPromptCreate.model_fields.keys())
    update_fields = set(AgentPromptUpdate.model_fields.keys())
    response_fields = set(AgentPromptResponse.model_fields.keys())

    # All schemas should use 'prompt_template'
    assert "prompt_template" in base_fields
    assert "prompt_template" in create_fields  # Inherits from base
    assert "prompt_template" in update_fields
    assert "prompt_template" in response_fields  # Inherits from base

    # None should use 'template'
    assert "template" not in base_fields
    assert "template" not in create_fields
    assert "template" not in update_fields
    assert "template" not in response_fields


def test_update_schema_accepts_frontend_data() -> None:
    """Test that update schema accepts data format sent by frontend."""
    # This simulates the exact data structure sent by the frontend
    frontend_data = {
        "goal": "Updated goal from frontend",
        "prompt_template": "Updated template from frontend: {message}",  # Frontend sends this key
        "is_active": True,
    }

    # This should work without field name errors
    prompt = AgentPromptUpdate(**frontend_data)

    assert prompt.goal == "Updated goal from frontend"
    assert prompt.prompt_template == "Updated template from frontend: {message}"
    assert prompt.is_active is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
