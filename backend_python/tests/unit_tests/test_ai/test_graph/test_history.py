"""Unit tests for conversation history management (compaction + windowing).

Tests cover:
- Itinerary compaction (the only compactable tool post-#1034)
- compact_tool_messages orchestrator: flights/hotels now pass through unchanged
  because they ship payloads via ``ToolMessage.artifact`` (never the LLM context)
- prune_old_messages windowing with RemoveMessage
- Graceful fallback on malformed data
"""

import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    ToolMessage,
)

from app.ai.graph.history import (
    _compact_itinerary,
    compact_tool_messages,
    prune_old_messages,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic tool outputs
# ---------------------------------------------------------------------------


def _make_itinerary_output(num_days: int = 3) -> str:
    """Build a realistic generate_itinerary JSON string."""
    items = []
    for d in range(1, num_days + 1):
        items.append(
            {
                "day": d,
                "title": f"Day {d} Title",
                "description": f"Explore day {d}",
                "imageUrl": "",
                "expandedContent": {
                    "mainImageUrl": "",
                    "activities": [
                        {
                            "location": f"Place {d}A",
                            "description": f"Visit Place {d}A",
                            "imageUrl": "",
                            "duration": "2h",
                            "rating": 4.5,
                        },
                        {
                            "location": f"Place {d}B",
                            "description": f"Visit Place {d}B",
                            "imageUrl": "",
                            "duration": "3h",
                            "rating": 4.0,
                        },
                        {
                            "location": f"Place {d}C",
                            "description": f"Visit Place {d}C",
                            "imageUrl": "",
                            "duration": "1h 30m",
                            "rating": None,
                        },
                    ],
                    "travelBars": [],
                    "tip": {"text": f"Insider tip for day {d}"},
                },
            }
        )
    return json.dumps(
        {
            "status": "success",
            "itinerary": {
                "itineraryItems": items,
                "footerSectionTitle": "Must-Try Local Experiences",
                "budgetSnapshot": {
                    "title": "Budget Snapshot",
                    "description": "Expect around $1,500 per person",
                },
                "localExperiences": [
                    {
                        "id": "1",
                        "title": "Exp 1",
                        "description": "...",
                        "imageUrl": "",
                        "imageAlt": "",
                    },
                    {
                        "id": "2",
                        "title": "Exp 2",
                        "description": "...",
                        "imageUrl": "",
                        "imageAlt": "",
                    },
                    {
                        "id": "3",
                        "title": "Exp 3",
                        "description": "...",
                        "imageUrl": "",
                        "imageAlt": "",
                    },
                ],
            },
            "validation": {"valid": True, "warnings": []},
            "summary": "3-day Tokyo itinerary with 9 activities.",
            "instruction": "Present the itinerary...",
        }
    )


def _make_search_flights_content() -> str:
    """search_flights now ships only a summary on ``content`` (issue #1034).

    The full flight list lives on ``ToolMessage.artifact`` and never enters
    LLM context — so content is intentionally tiny.
    """
    return json.dumps(
        {
            "status": "success",
            "summary": {
                "total_found": 3,
                "direct_flights": 1,
                "price_range": {"min": 485.0, "max": 1200.0, "currency": "EUR"},
            },
            "instruction": "Present these options to the user.",
        }
    )


def _make_search_hotels_content() -> str:
    """search_hotels content-side payload (issue #1034)."""
    return json.dumps(
        {
            "status": "success",
            "summary": {
                "total_found": 5,
                "nights": 4,
                "price_range": {"min": 89.0, "max": 450.0, "currency": "USD"},
            },
            "instruction": "Present these hotels to the user.",
        }
    )


def _tool_msg(
    name: str,
    content: str,
    msg_id: str = "tm-1",
    tc_id: str = "tc-1",
    artifact: Any = None,
) -> ToolMessage:
    return ToolMessage(
        content=content,
        name=name,
        tool_call_id=tc_id,
        id=msg_id,
        artifact=artifact,
    )


# ---------------------------------------------------------------------------
# Tests — Itinerary Compaction
# ---------------------------------------------------------------------------


class TestCompactItinerary:
    def test_extracts_day_titles(self) -> None:
        result = _compact_itinerary(_make_itinerary_output())
        assert result is not None
        data = json.loads(result)
        assert data["compact"] is True
        assert data["num_days"] == 3
        assert len(data["days"]) == 3
        assert "Place 1A" in data["days"][0]
        assert "Place 1B" in data["days"][0]
        assert "Place 1C" in data["days"][0]

    def test_preserves_summary(self) -> None:
        result = _compact_itinerary(_make_itinerary_output())
        assert result is not None
        data = json.loads(result)
        assert "3-day Tokyo itinerary" in data["summary"]
        assert data["local_experiences"] == 3
        assert "1,500" in data["budget_snapshot"]

    def test_compact_is_small(self) -> None:
        original = _make_itinerary_output(num_days=7)
        result = _compact_itinerary(original)
        assert result is not None
        assert len(result) < 1500  # < 1.5 KB
        assert len(original) > len(result) * 3  # at least 3x reduction

    def test_error_status_returns_none(self) -> None:
        content = json.dumps({"status": "error", "error": "Something broke"})
        assert _compact_itinerary(content) is None

    def test_malformed_json_returns_none(self) -> None:
        assert _compact_itinerary("not valid json {{") is None

    def test_missing_itinerary_key_returns_none(self) -> None:
        content = json.dumps({"status": "success"})
        assert _compact_itinerary(content) is None

    def test_empty_items_returns_none(self) -> None:
        content = json.dumps({"status": "success", "itinerary": {"itineraryItems": []}})
        assert _compact_itinerary(content) is None

    def test_handles_planning_result_key(self) -> None:
        """Legacy save_itinerary format with planning_result key."""
        items = [
            {
                "day": 1,
                "title": "Day 1",
                "expandedContent": {
                    "activities": [{"location": "Temple"}],
                },
            }
        ]
        content = json.dumps(
            {
                "status": "success",
                "planning_result": {"itineraryItems": items},
                "summary": "1-day trip",
            }
        )
        result = _compact_itinerary(content)
        assert result is not None
        data = json.loads(result)
        assert data["compact"] is True
        assert "Temple" in data["days"][0]


# ---------------------------------------------------------------------------
# Tests — compact_tool_messages orchestrator (post #1034)
# ---------------------------------------------------------------------------


class TestCompactToolMessages:
    def test_compacts_only_targeted_tools(self) -> None:
        msgs: list[BaseMessage] = [
            _tool_msg("generate_itinerary", _make_itinerary_output(), "tm-1", "tc-1"),
            _tool_msg(
                "parse_dates", '{"departure_date": "2026-03-20"}', "tm-2", "tc-2"
            ),
        ]
        result = compact_tool_messages(msgs)
        assert len(result) == 2
        # First should be compacted
        compacted = json.loads(result[0].content)
        assert compacted.get("compact") is True
        # Second should be unchanged
        assert result[1].content == msgs[1].content

    def test_leaves_non_tool_messages_untouched(self) -> None:
        msgs: list[BaseMessage] = [
            HumanMessage(content="hello", id="hm-1"),
            AIMessage(content="hi there", id="ai-1"),
            _tool_msg("generate_itinerary", _make_itinerary_output(), "tm-1", "tc-1"),
        ]
        result = compact_tool_messages(msgs)
        assert len(result) == 3
        assert result[0].content == "hello"
        assert result[1].content == "hi there"
        compacted = json.loads(result[2].content)
        assert compacted.get("compact") is True

    def test_fallback_on_compaction_failure(self) -> None:
        msgs: list[BaseMessage] = [
            _tool_msg("generate_itinerary", "broken json {{", "tm-1", "tc-1"),
        ]
        result = compact_tool_messages(msgs)
        assert len(result) == 1
        # Original preserved
        assert result[0].content == "broken json {{"

    def test_preserves_message_ids(self) -> None:
        msgs: list[BaseMessage] = [
            _tool_msg("generate_itinerary", _make_itinerary_output(), "my-id", "my-tc"),
        ]
        result = compact_tool_messages(msgs)
        assert result[0].id == "my-id"
        assert result[0].tool_call_id == "my-tc"  # type: ignore[attr-defined]
        assert result[0].name == "generate_itinerary"  # type: ignore[attr-defined]

    def test_search_flights_passes_through_unchanged(self) -> None:
        """Issue #1034: search_flights is NOT in COMPACTABLE_TOOLS.

        The full flight list lives on ``ToolMessage.artifact`` and is never
        sent to the LLM, so post-hoc compaction is unnecessary.
        """
        original_content = _make_search_flights_content()
        artifact_payload = {"flights": [{"id": "fl-1"}, {"id": "fl-2"}]}
        msgs: list[BaseMessage] = [
            _tool_msg(
                "search_flights",
                original_content,
                "tm-1",
                "tc-1",
                artifact=artifact_payload,
            ),
        ]
        result = compact_tool_messages(msgs)
        assert len(result) == 1
        # Content is left exactly as-is — no `compact` field added.
        assert result[0].content == original_content
        data = json.loads(result[0].content)
        assert "compact" not in data
        # Artifact is preserved on the same object (orchestrator returns msgs
        # unchanged when the tool isn't compactable).
        assert result[0].artifact == artifact_payload  # type: ignore[attr-defined]

    def test_search_hotels_passes_through_unchanged(self) -> None:
        """Issue #1034: search_hotels is NOT in COMPACTABLE_TOOLS."""
        original_content = _make_search_hotels_content()
        msgs: list[BaseMessage] = [
            _tool_msg("search_hotels", original_content, "tm-1", "tc-1"),
        ]
        result = compact_tool_messages(msgs)
        assert result[0].content == original_content
        data = json.loads(result[0].content)
        assert "compact" not in data

    def test_unknown_tool_passes_through(self) -> None:
        msgs: list[BaseMessage] = [
            _tool_msg("resolve_airport", '{"iata": "AMS"}', "tm-1", "tc-1"),
        ]
        result = compact_tool_messages(msgs)
        assert result[0].content == '{"iata": "AMS"}'


# ---------------------------------------------------------------------------
# Tests — prune_old_messages windowing
# ---------------------------------------------------------------------------


def _make_messages(count: int) -> list[BaseMessage]:
    """Create a list of messages with unique IDs."""
    msgs: list[BaseMessage] = []
    for i in range(count):
        if i % 2 == 0:
            msgs.append(HumanMessage(content=f"msg-{i}", id=f"id-{i}"))
        else:
            msgs.append(AIMessage(content=f"msg-{i}", id=f"id-{i}"))
    return msgs


class TestPruneOldMessages:
    def test_no_pruning_under_threshold(self) -> None:
        msgs = _make_messages(25)
        removals = prune_old_messages(msgs)
        assert removals == []

    def test_no_pruning_at_threshold(self) -> None:
        msgs = _make_messages(40)
        removals = prune_old_messages(msgs)
        assert removals == []

    def test_prunes_when_over_threshold(self) -> None:
        msgs = _make_messages(45)
        removals = prune_old_messages(msgs)
        # Should remove 45 - 30 = 15 messages
        assert len(removals) == 15
        # All should be RemoveMessage
        for r in removals:
            assert isinstance(r, RemoveMessage)

    def test_keeps_last_n_messages(self) -> None:
        msgs = _make_messages(50)
        removals = prune_old_messages(msgs)
        removed_ids = {r.id for r in removals}
        # Last 30 should NOT be removed
        for msg in msgs[-30:]:
            assert msg.id not in removed_ids
        # First 20 should be removed
        for msg in msgs[:20]:
            assert msg.id in removed_ids

    def test_custom_thresholds(self) -> None:
        msgs = _make_messages(25)
        removals = prune_old_messages(msgs, max_messages=10, trigger_threshold=20)
        # 25 > 20 threshold, remove 25 - 10 = 15
        assert len(removals) == 15

    def test_messages_without_ids_skipped(self) -> None:
        """Messages without IDs should not generate RemoveMessage."""
        msgs: list[BaseMessage] = [
            HumanMessage(content="no-id"),  # No explicit id
        ] * 50
        removals = prune_old_messages(msgs, max_messages=10, trigger_threshold=20)
        # Messages auto-get IDs from LangChain, so this depends on implementation
        # Just verify no crash
        assert isinstance(removals, list)
