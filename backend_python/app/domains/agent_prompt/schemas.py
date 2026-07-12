"""Agent prompt schemas for API requests/responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class AgentPromptBase(BaseModel):
    """Base schema for agent prompts"""

    agent_name: str = Field(..., description="Name of the AI agent")
    goal: str = Field(..., description="Description of what this agent does")
    prompt_template: str = Field(..., description="The prompt template for this agent")
    is_active: bool = Field(
        default=True, description="Whether this prompt is currently active"
    )


class AgentPromptCreate(AgentPromptBase):
    """Schema for creating a new agent prompt"""

    pass


class AgentPromptUpdate(BaseModel):
    """Schema for updating an agent prompt"""

    goal: str | None = Field(None, description="Description of what this agent does")
    prompt_template: str | None = Field(
        None, description="The prompt template for this agent"
    )
    is_active: bool | None = Field(
        None, description="Whether this prompt is currently active"
    )


class AgentPromptResponse(AgentPromptBase):
    """Schema for agent prompt responses"""

    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When the prompt was created")
    updated_at: datetime = Field(..., description="When the prompt was last updated")
    created_by: str | None = Field(None, description="User who created this prompt")
    updated_by: str | None = Field(
        None, description="User who last updated this prompt"
    )

    class Config:
        from_attributes = True


class AgentPromptListResponse(BaseModel):
    """Schema for listing agent prompts"""

    prompts: list[AgentPromptResponse]
    total: int = Field(..., description="Total number of prompts")
