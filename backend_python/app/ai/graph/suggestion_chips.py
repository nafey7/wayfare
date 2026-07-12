"""Parse and extract follow-up suggestion chips from agent responses.

Agents append a ``[SUGGESTIONS]...[/SUGGESTIONS]`` tag at the end of their
response text.  This module strips the tag from the visible message and
returns the suggestions as a list of dicts matching the frontend
``ChatSuggestion`` type (``{title, command}``).
"""

from __future__ import annotations

import re

SUGGESTIONS_PATTERN: re.Pattern[str] = re.compile(
    r"\[SUGGESTIONS\](.*?)\[/SUGGESTIONS\]\s*$",
    re.DOTALL,
)

MAX_SUGGESTIONS = 3


def parse_suggestions(message: str) -> tuple[str, list[dict[str, str]]]:
    """Parse ``[SUGGESTIONS]`` tag from an agent response message.

    Args:
        message: Raw agent response text, potentially ending with a
            ``[SUGGESTIONS]...[/SUGGESTIONS]`` block.

    Returns:
        A 2-tuple of ``(cleaned_message, suggestions)`` where
        *cleaned_message* has the tag stripped and *suggestions* is a
        list of ``{"title": "...", "command": "..."}`` dicts (max 3).
        If no tag is found the original message and an empty list are
        returned.
    """
    if not message:
        return message, []

    match = SUGGESTIONS_PATTERN.search(message)
    if not match:
        return message, []

    raw = match.group(1).strip()
    cleaned = message[: match.start()].rstrip()

    suggestions: list[dict[str, str]] = []
    for part in raw.split("|"):
        text = part.strip()
        if text:
            suggestions.append({"title": text, "command": text})

    return cleaned, suggestions[:MAX_SUGGESTIONS]
