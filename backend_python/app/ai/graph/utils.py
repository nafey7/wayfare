"""Shared utility functions for LangGraph agents."""

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

# Single source of truth for the hand-back tool name
HAND_BACK_TOOL_NAME = "hand_back_to_supervisor"


def extract_text_content(content: Any) -> str:
    """Extract text content from Gemini response (handles both string and list formats).

    Different Gemini models return content in different formats:
    - Gemini 2.0 Flash: "text message"
    - Gemini 2.5 Pro: [{'type': 'text', 'text': 'message', 'extras': {...}}]

    Args:
        content: Message content from AIMessage

    Returns:
        Extracted text string

    Example:
        >>> extract_text_content("Hello world")
        'Hello world'
        >>> extract_text_content([{'type': 'text', 'text': 'Hello', 'extras': {}}])
        'Hello'
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list) and len(content) > 0:
        first_item = content[0]
        # create_react_agent format: [{'type': 'text', 'text': '...'}]
        if isinstance(first_item, dict) and "text" in first_item:
            return first_item["text"]
        # create_agent format: ['text string', {'type': 'text', 'text': '...'}]
        if isinstance(first_item, str):
            return first_item

    # Fallback: convert to string
    return str(content)


def detect_hand_back_tool(messages: list[Any]) -> dict[str, Any] | None:
    """Detect if hand_back_to_supervisor was called in messages.

    Scans messages in reverse for a ToolMessage from hand_back_to_supervisor
    with status "hand_back".

    Args:
        messages: List of LangChain messages from graph result

    Returns:
        Tool result dict if hand_back found, None otherwise
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == HAND_BACK_TOOL_NAME:
            try:
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                result = json.loads(content)
                if result.get("status") == "hand_back":
                    # Ensure is_detour is always present (defaults to False)
                    result.setdefault("is_detour", False)
                    return result
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def extract_last_ai_message(messages: list[Any]) -> str:
    """Extract text content from the last AIMessage in a message list.

    Scans messages in reverse and returns the text from the first AIMessage
    found.  Returns empty string if no AIMessage exists.

    Args:
        messages: List of LangChain messages

    Returns:
        Extracted text string, or "" if not found
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return extract_text_content(msg.content)
    return ""


def build_hand_back_response(
    messages: list[Any],
    hand_back: dict[str, Any],
    message_id: str = "",
) -> dict[str, Any]:
    """Build a standard hand-back response dict.

    Shared by all agent process_*_messages functions when hand_back_to_supervisor
    is detected.

    Args:
        messages: Full message list (to extract last AI message)
        hand_back: Parsed hand_back tool result from detect_hand_back_tool()
        message_id: Message ID for feedback correlation

    Returns:
        Response dict with type="hand_back"
    """
    return {
        "message": extract_last_ai_message(messages),
        "type": "hand_back",
        "signal": "hand_back",
        "reason": hand_back.get("reason", ""),
        "is_detour": hand_back.get("is_detour", False),
        "message_id": message_id,
    }
