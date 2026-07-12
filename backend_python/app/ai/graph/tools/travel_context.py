"""Tool for the general agent to save travel context.

When the general agent identifies travel-relevant details (destination,
dates, travelers, preferences) from the conversation, it calls this tool
to persist them in shared_context so downstream agents (flight, hotel,
itinerary) can use them without re-asking.
"""

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SaveTravelContextInput(BaseModel):
    """Input schema for save_travel_context."""

    destination: str | None = Field(
        default=None,
        description=(
            "Destination city or country the user mentioned "
            "(e.g., 'Dubai', 'Japan', 'Paris'). "
            "Set when the user expresses interest in a specific place."
        ),
    )
    dates: str | None = Field(
        default=None,
        description=(
            "Travel dates or timeframe mentioned by the user "
            "(e.g., 'next Friday for 5 days', 'in October', 'next month'). "
            "Store as the user said it — do NOT parse into YYYY-MM-DD."
        ),
    )
    travelers: str | None = Field(
        default=None,
        description=(
            "Number/type of travelers mentioned "
            "(e.g., '2 adults', 'family of 4', 'just me', 'couple'). "
        ),
    )
    interests: str | None = Field(
        default=None,
        description=(
            "Travel interests or preferences mentioned "
            "(e.g., 'beaches', 'food', 'adventure', 'luxury', 'budget'). "
        ),
    )


@tool("save_travel_context", args_schema=SaveTravelContextInput)
def save_travel_context(
    destination: str | None = None,
    dates: str | None = None,
    travelers: str | None = None,
    interests: str | None = None,
) -> dict[str, Any]:
    """Save travel details mentioned in conversation for use by other agents.

    Call this when the user mentions a destination, dates, travelers, or
    travel preferences during general conversation. This ensures other
    agents (flight, hotel, itinerary) know what the user wants without
    re-asking.

    Only call with fields the user actually mentioned — leave others as null.
    """
    saved: dict[str, Any] = {}
    if destination:
        saved["destination"] = destination
    if dates:
        saved["dates"] = dates
    if travelers:
        saved["travelers"] = travelers
    if interests:
        saved["interests"] = interests

    logger.info("save_travel_context: saved=%s", saved)

    return {
        "status": "saved",
        "saved_fields": list(saved.keys()),
        "data": saved,
        "instruction": (
            "Context saved. Continue the conversation naturally — "
            "do NOT tell the user you saved anything."
        ),
    }
