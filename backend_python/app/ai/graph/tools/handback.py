"""Hand-back tool for sub-agents to return control to the Supervisor.

When an agent determines the user's message is outside its domain,
it calls this tool to signal the Supervisor to re-classify intent.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HandBackInput(BaseModel):
    """Input schema for hand_back_to_supervisor."""

    reason: str = Field(
        description="Why you're handing back. Examples: "
        "'User asking about hotels', 'User wants travel advice'"
    )
    is_detour: bool = Field(
        default=False,
        description="Set to True if this is a contextual side question (weather, visa, tips) "
        "and the user should return to the current booking/planning after it's answered. "
        "Set to False for real topic changes (switching from flights to hotels).",
    )


# #1133 follow-up: reject hand-back reasons that indicate the agent is bailing
# on a clarifying question (missing field, ambiguous destination, etc.). The
# itinerary prompt's "Required Fields" rule already says to ASK the user for
# missing fields in the SAME numbered message — but the LLM sometimes bypasses
# that and hand-backs anyway, which routes the user through ``general`` and
# breaks previous-agent affinity. This pattern matches the reason strings the
# LLM actually emits in these cases (observed in CloudWatch + manual testing).
#
# False-positive risk: an out-of-scope detour reason that happens to contain
# one of these words ("user wants to specify a different airport") — the rule
# below is conservative (REQUIRES context like "need", "missing", "specific
# city", "ask the user", "clarif") to avoid blocking legitimate hand-backs.
_INVALID_HANDBACK_REASON_PATTERN = re.compile(
    r"\b(?:"
    r"missing\s+(?:origin|destination|city|airport|date|passenger|field)"
    r"|need(?:\s+a)?\s+(?:specific|particular|valid)\s+(?:city|airport|origin|destination|date)"
    r"|specific\s+(?:us|uk|country)?\s*city\s+(?:origin|required|needed)"
    r"|origin\s+is\s+(?:country|country-level)"
    r"|ask\s+the\s+user\s+(?:for|which|to\s+provide|to\s+specify)"
    r"|clarif(?:y|ication)\s+(?:needed|required|on)"
    # ``which X`` only counts as a bail-out when paired with an
    # agent-intent verb ("ask … which city", "need to know which airport").
    # The bare phrase "which city" alone would wrongly reject legitimate
    # detour reasons like "User asking which airport is closer to downtown"
    # — those describe the user's question, not the agent's bail.
    r"|(?:ask\s+(?:the\s+user\s+)?(?:for\s+)?|need\s+to\s+know\s+)which\s+(?:city|airport|date)"
    r"|need\s+to\s+(?:ask|know|confirm)"
    r"|country[-\s]level\s+only"
    r")\b",
    re.IGNORECASE,
)


@tool("hand_back_to_supervisor", args_schema=HandBackInput)
async def hand_back_to_supervisor(
    reason: str, is_detour: bool = False
) -> dict[str, Any]:
    """Call this when the user's message is NOT related to your domain.

    The Supervisor will re-classify the user's intent and route to the
    appropriate specialist agent.

    Do NOT call this for:
    - Follow-up questions about your domain
    - Clarifying questions (dates, passengers, preferences)
    - Short replies ("yes", "option 1", "2 adults")
    - Modifications ("change the dates", "try a different airport")
    - Missing required fields — ASK the user instead, never hand back
    """
    # #1133 follow-up: catch the "I can't ask the user, I'll hand back instead"
    # antipattern. The supervisor would then route through ``general`` and the
    # user's reply (e.g. "LAX") gets re-classified as a fresh flight intent —
    # breaking the itinerary flow. Reject the hand-back and tell the agent to
    # ask the user directly.
    if _INVALID_HANDBACK_REASON_PATTERN.search(reason or ""):
        logger.info(
            "hand_back_to_supervisor: rejected invalid reason %r — agent must "
            "ask the user instead of handing back for missing fields",
            reason,
        )
        return {
            "status": "error",
            "error": (
                f"Invalid hand-back reason: {reason!r}. Missing or ambiguous "
                "required fields are NOT a reason to hand back — the user is "
                "still on your trip-planning flow. ASK the user for the "
                "missing field in your next message, combining all missing "
                "fields in ONE numbered question."
            ),
            "instruction": (
                "Do NOT call hand_back_to_supervisor again with this reason. "
                "Send a TEXT message to the user asking for the missing or "
                "ambiguous field directly (e.g. 'Which city of the US are you "
                "flying from? Common options: JFK/EWR (NYC), LAX, ORD, "
                "SFO...'). Combine all missing fields in ONE numbered "
                "question so the user answers everything at once."
            ),
        }

    return {
        "status": "hand_back",
        "reason": reason,
        "is_detour": is_detour,
        "instruction": "Handing back to supervisor for re-routing.",
    }
