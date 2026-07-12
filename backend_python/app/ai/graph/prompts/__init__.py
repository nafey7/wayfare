"""Prompt templates for LangGraph agents."""

from app.ai.graph.prompts.flight_agent import FLIGHT_SYSTEM_PROMPT
from app.ai.graph.prompts.general_agent import GENERAL_AGENT_PROMPT
from app.ai.graph.prompts.hotel_agent import HOTEL_SYSTEM_PROMPT
from app.ai.graph.prompts.itinerary_agent import (
    ITINERARY_AGENT_PROMPT,
    ITINERARY_GENERATION_PROMPT,
)
from app.ai.graph.prompts.shared import SUGGESTIONS_RULE
from app.ai.graph.prompts.supervisor_v2_agent import SUPERVISOR_V2_PROMPT

__all__ = [
    "FLIGHT_SYSTEM_PROMPT",
    "GENERAL_AGENT_PROMPT",
    "HOTEL_SYSTEM_PROMPT",
    "ITINERARY_AGENT_PROMPT",
    "ITINERARY_GENERATION_PROMPT",
    "SUGGESTIONS_RULE",
    "SUPERVISOR_V2_PROMPT",
]
