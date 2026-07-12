"""Supervisor-level conversation history management.

Provides two complementary strategies for keeping the V2 supervisor's
checkpoint messages bounded:

1. **Tool result compaction** — replaces large ToolMessages (itineraries,
   flight/hotel search results) with compact summaries.  The full data
   has already been extracted by ``process_*_messages()`` for the frontend
   before compaction runs.

2. **Message windowing** — emits ``RemoveMessage`` objects when the
   checkpoint exceeds a size threshold so the oldest messages are pruned.

Both strategies have **zero LLM cost** — they are pure Python operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import BaseMessage, RemoveMessage, ToolMessage

from app.ai.graph.constants import (
    COMPACTABLE_TOOLS,
    MAX_MESSAGES_IN_CHECKPOINT,
    PRUNE_TRIGGER_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compact_tool_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Replace large ToolMessages with compact summaries.

    Targets tool names listed in ``COMPACTABLE_TOOLS``.  Non-ToolMessages
    and small tools pass through unchanged.  On compaction failure for any
    individual message the original is kept (graceful fallback).

    Args:
        messages: New messages produced by an inner agent (``new_msgs``).

    Returns:
        New list with large ToolMessages replaced by compact versions.
        Message ``id`` and ``tool_call_id`` are preserved for LangGraph
        consistency.
    """
    result: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name in COMPACTABLE_TOOLS:
            compacted = _try_compact(msg)
            result.append(compacted if compacted is not None else msg)
        else:
            result.append(msg)
    return result


def prune_old_messages(
    all_messages: list[BaseMessage],
    max_messages: int = MAX_MESSAGES_IN_CHECKPOINT,
    trigger_threshold: int = PRUNE_TRIGGER_THRESHOLD,
) -> list[RemoveMessage]:
    """Generate ``RemoveMessage`` objects for messages exceeding the window.

    Only triggers when the total message count exceeds *trigger_threshold*
    (default 40) to avoid pruning on every dispatch when hovering near the
    limit.

    Args:
        all_messages: Full message list from ``state["messages"]``.
        max_messages: How many messages to keep (default 30).
        trigger_threshold: Prune only when count exceeds this (default 40).

    Returns:
        List of ``RemoveMessage`` objects for the oldest messages, or an
        empty list if under the threshold.
    """
    if len(all_messages) <= trigger_threshold:
        return []

    to_remove = all_messages[: len(all_messages) - max_messages]
    removals: list[RemoveMessage] = []
    for msg in to_remove:
        msg_id = getattr(msg, "id", None)
        if msg_id is not None:
            removals.append(RemoveMessage(id=msg_id))
    return removals


# ---------------------------------------------------------------------------
# Internal — per-tool compaction
# ---------------------------------------------------------------------------

_COMPACT_INSTRUCTION_SUFFIX = (
    "Full results already delivered to user. "
    "Use this summary for context on follow-up requests."
)

_COMPACTORS: dict[str, Any] = {}  # populated below


def _try_compact(msg: ToolMessage) -> ToolMessage | None:
    """Attempt to compact a single ToolMessage.

    Returns a new ``ToolMessage`` with compacted ``content`` on success,
    or ``None`` on failure (caller keeps the original).
    """
    if msg.name is None:
        return None
    compactor = _COMPACTORS.get(msg.name)
    if compactor is None:
        return None
    try:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        compacted_content = compactor(content)
        if compacted_content is None:
            return None
        return ToolMessage(
            content=compacted_content,
            name=msg.name,
            tool_call_id=msg.tool_call_id,
            id=msg.id,
        )
    except Exception:
        logger.debug(
            "Compaction failed for tool=%s, keeping original", msg.name, exc_info=True
        )
        return None


# -- Itinerary ---------------------------------------------------------------


def _compact_itinerary(content: str) -> str | None:
    """Compact ``generate_itinerary`` tool output.

    Extracts day titles with activity names and preserves the existing
    summary.  Works for both ``generate_itinerary`` format
    (``{"itinerary": {...}}``) and legacy ``save_itinerary`` format
    (``{"planning_result": {...}}``).
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if data.get("status") != "success":
        return None  # keep errors intact for debugging

    itinerary = data.get("itinerary") or data.get("planning_result")
    if not itinerary or not isinstance(itinerary, dict):
        return None

    items = itinerary.get("itineraryItems", [])
    if not items:
        return None

    days: list[str] = []
    for item in items:
        day_num = item.get("day", "?")
        title = item.get("title", "")
        activities: list[str] = []
        expanded = item.get("expandedContent") or {}
        for act in expanded.get("activities", []):
            loc = act.get("location", "")
            if loc:
                activities.append(loc)
        activity_str = ", ".join(activities) if activities else title
        days.append(f"Day {day_num}: {activity_str}")

    local_exp = itinerary.get("localExperiences", [])
    budget_snap = itinerary.get("budgetSnapshot") or {}

    compact = {
        "compact": True,
        "status": "success",
        "days": days,
        "num_days": len(items),
        "local_experiences": len(local_exp),
        "budget_snapshot": budget_snap.get("description", ""),
        "summary": data.get("summary", ""),
        "instruction": _COMPACT_INSTRUCTION_SUFFIX,
    }
    return json.dumps(compact)


# -- Flights -----------------------------------------------------------------


# -- Registry ----------------------------------------------------------------
# Issue #1034: ``search_flights`` and ``search_hotels`` were removed from the
# registry \u2014 they use ``response_format="content_and_artifact"`` so the LLM
# never receives the heavy payload to begin with; no post-hoc compaction needed.

_COMPACTORS = {
    "generate_itinerary": _compact_itinerary,
}
