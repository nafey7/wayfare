"""Agent prompt database models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentPrompt(BaseModel):
    """Model for storing AI agent prompts"""

    agent_name: str = Field(..., description="Name of the AI agent")
    goal: str = Field(..., description="Description of what this agent does")
    prompt_template: str = Field(..., description="The prompt template for this agent")
    is_active: bool = Field(
        default=True, description="Whether this prompt is currently active"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(None, description="User ID who created this prompt")
    updated_by: str | None = Field(
        None, description="User ID who last updated this prompt"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentPrompt":
        """Create from MongoDB dictionary"""
        return cls(**data)

    def __repr__(self) -> str:
        return f"AgentPrompt(agent_name={self.agent_name!r})"

    def __str__(self) -> str:
        return f"{self.agent_name}: {self.goal[:50]}..."
