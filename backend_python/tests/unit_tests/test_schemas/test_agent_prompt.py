"""Unit tests for agent prompt schemas."""

import os

# Import schemas directly to avoid database dependencies in unit tests
import sys
from datetime import datetime

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../app"))

from domains.agent_prompt.schemas import (
    AgentPromptBase,
    AgentPromptCreate,
    AgentPromptListResponse,
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


def test_agent_prompt_base_empty_strings() -> None:
    """Test AgentPromptBase validation with empty strings."""
    data = {
        "agent_name": "",
        "goal": "",
        "prompt_template": "",
        "is_active": False,
    }

    # Empty strings should be accepted (business logic may handle validation)
    prompt = AgentPromptBase(**data)
    assert prompt.agent_name == ""
    assert prompt.goal == ""
    assert prompt.prompt_template == ""


# ==============================================================================
# AGENT PROMPT CREATE SCHEMA TESTS
# ==============================================================================


def test_agent_prompt_create_inherits_base() -> None:
    """Test AgentPromptCreate inherits all base functionality."""
    data = {
        "agent_name": "data_extractor",
        "goal": "Extract structured data from user messages",
        "prompt_template": "Extract flight data from: {message}",
        "is_active": True,
    }

    prompt = AgentPromptCreate(**data)

    assert prompt.agent_name == "data_extractor"
    assert prompt.goal == "Extract structured data from user messages"
    assert prompt.prompt_template == "Extract flight data from: {message}"
    assert prompt.is_active is True


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


def test_agent_prompt_update_partial_data() -> None:
    """Test AgentPromptUpdate with partial data."""
    data = {
        "goal": "Updated goal",
        "is_active": False,
    }

    prompt = AgentPromptUpdate(**data)

    assert prompt.goal == "Updated goal"
    assert prompt.prompt_template is None  # Not provided
    assert prompt.is_active is False


def test_agent_prompt_update_all_fields() -> None:
    """Test AgentPromptUpdate with all fields provided."""
    data = {
        "goal": "Updated goal for intent recognition",
        "prompt_template": "Updated template: {message}",
        "is_active": True,
    }

    prompt = AgentPromptUpdate(**data)

    assert prompt.goal == "Updated goal for intent recognition"
    assert prompt.prompt_template == "Updated template: {message}"
    assert prompt.is_active is True


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
# AGENT PROMPT RESPONSE SCHEMA TESTS
# ==============================================================================


def test_agent_prompt_response_with_metadata() -> None:
    """Test AgentPromptResponse includes all metadata fields."""
    now = datetime.utcnow()
    data = {
        "agent_name": "general_travel_handler",
        "goal": "Handle travel queries",
        "prompt_template": "Travel assistant: {message}",
        "is_active": True,
        "id": "507f1f77bcf86cd799439011",
        "created_at": now,
        "updated_at": now,
        "created_by": "admin@example.com",
        "updated_by": "admin@example.com",
    }

    prompt = AgentPromptResponse(**data)

    assert prompt.id == "507f1f77bcf86cd799439011"
    assert prompt.created_at == now
    assert prompt.updated_at == now
    assert prompt.created_by == "admin@example.com"
    assert prompt.updated_by == "admin@example.com"


def test_agent_prompt_response_optional_user_fields() -> None:
    """Test AgentPromptResponse with optional user fields as None."""
    now = datetime.utcnow()
    data = {
        "agent_name": "data_extractor",
        "goal": "Extract data",
        "prompt_template": "Extract: {message}",
        "is_active": False,
        "id": "507f1f77bcf86cd799439012",
        "created_at": now,
        "updated_at": now,
    }

    prompt = AgentPromptResponse(**data)

    assert prompt.created_by is None
    assert prompt.updated_by is None


def test_agent_prompt_response_field_name_consistency() -> None:
    """Test AgentPromptResponse uses correct field names."""
    now = datetime.utcnow()
    data = {
        "agent_name": "intent_recognizer",
        "goal": "Recognize intents",
        "prompt_template": "Classify: {message}",  # Correct field name
        "is_active": True,
        "id": "507f1f77bcf86cd799439013",
        "created_at": now,
        "updated_at": now,
    }

    prompt = AgentPromptResponse(**data)

    # Should have prompt_template field
    assert hasattr(prompt, "prompt_template")
    assert prompt.prompt_template == "Classify: {message}"

    # Should NOT have template field
    assert not hasattr(prompt, "template")


# ==============================================================================
# AGENT PROMPT LIST RESPONSE SCHEMA TESTS
# ==============================================================================


def test_agent_prompt_list_response_empty() -> None:
    """Test AgentPromptListResponse with empty list."""
    data = {
        "prompts": [],
        "total": 0,
    }

    response = AgentPromptListResponse(**data)

    assert response.prompts == []
    assert response.total == 0


def test_agent_prompt_list_response_with_prompts() -> None:
    """Test AgentPromptListResponse with prompt data."""
    now = datetime.utcnow()
    prompts_data = [
        {
            "agent_name": "general_travel_handler",
            "goal": "Handle travel queries",
            "prompt_template": "Travel: {message}",
            "is_active": True,
            "id": "507f1f77bcf86cd799439011",
            "created_at": now,
            "updated_at": now,
        },
        {
            "agent_name": "intent_recognizer",
            "goal": "Recognize intents",
            "prompt_template": "Intent: {message}",
            "is_active": False,
            "id": "507f1f77bcf86cd799439012",
            "created_at": now,
            "updated_at": now,
        },
    ]

    data = {
        "prompts": prompts_data,
        "total": 2,
    }

    response = AgentPromptListResponse(**data)

    assert len(response.prompts) == 2
    assert response.total == 2
    assert all(isinstance(p, AgentPromptResponse) for p in response.prompts)


def test_agent_prompt_list_response_total_mismatch() -> None:
    """Test AgentPromptListResponse handles total/list count mismatch."""
    now = datetime.utcnow()
    prompts_data = [
        {
            "agent_name": "data_extractor",
            "goal": "Extract data",
            "prompt_template": "Extract: {message}",
            "is_active": True,
            "id": "507f1f77bcf86cd799439013",
            "created_at": now,
            "updated_at": now,
        }
    ]

    data = {
        "prompts": prompts_data,
        "total": 5,  # Mismatch with actual list length
    }

    # Should still be valid - business logic can handle mismatch
    response = AgentPromptListResponse(**data)
    assert len(response.prompts) == 1
    assert response.total == 5


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


# ==============================================================================
# VALIDATION AND EDGE CASES
# ==============================================================================


def test_agent_prompt_with_special_characters() -> None:
    """Test schemas handle special characters in templates."""
    data = {
        "agent_name": "test_agent",
        "goal": "Test with special chars: !@#$%^&*()",
        "prompt_template": "Template with {message} and special chars: 中文 español 🎉",
        "is_active": True,
    }

    prompt = AgentPromptBase(**data)
    assert "🎉" in prompt.prompt_template
    assert "中文" in prompt.prompt_template


def test_agent_prompt_with_very_long_template() -> None:
    """Test schemas handle very long templates."""
    long_template = "A" * 10000 + " {message} " + "B" * 10000
    data = {
        "agent_name": "test_agent",
        "goal": "Test long template",
        "prompt_template": long_template,
        "is_active": True,
    }

    prompt = AgentPromptBase(**data)
    # Expected length: 10000 (A's) + 11 (" {message} ") + 10000 (B's) = 20011
    assert len(prompt.prompt_template) == 20011


def test_agent_prompt_with_json_in_template() -> None:
    """Test schemas handle JSON-like structures in templates."""
    template_with_json = """
    {
        "role": "assistant",
        "content": "User said: {message}",
        "metadata": {"agent": "test"}
    }
    """
    data = {
        "agent_name": "test_agent",
        "goal": "Test JSON template",
        "prompt_template": template_with_json,
        "is_active": True,
    }

    prompt = AgentPromptBase(**data)
    assert "{message}" in prompt.prompt_template
    assert '"role": "assistant"' in prompt.prompt_template
