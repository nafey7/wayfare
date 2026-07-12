"""Unit tests for the save_travel_context tool.

Tests cover:
- Saving individual fields (destination, dates, travelers, interests)
- Saving all fields together
- Null/empty fields excluded from saved data
- Return format (saved_fields, data, instruction)
"""

import pytest

from app.ai.graph.tools.travel_context import save_travel_context


class TestSaveTravelContext:
    """Tests for the save_travel_context tool."""

    @pytest.mark.asyncio
    async def test_save_destination_only(self) -> None:
        """Saves just destination when only destination provided."""
        result = await save_travel_context.ainvoke({"destination": "Dubai"})

        assert result["status"] == "saved"
        assert result["saved_fields"] == ["destination"]
        assert result["data"]["destination"] == "Dubai"
        assert "dates" not in result["data"]

    @pytest.mark.asyncio
    async def test_save_all_fields(self) -> None:
        """Saves all fields when all provided."""
        result = await save_travel_context.ainvoke(
            {
                "destination": "Tokyo",
                "dates": "next Friday for 5 days",
                "travelers": "2 adults",
                "interests": "food, culture",
            }
        )

        assert result["status"] == "saved"
        assert set(result["saved_fields"]) == {
            "destination",
            "dates",
            "travelers",
            "interests",
        }
        assert result["data"]["destination"] == "Tokyo"
        assert result["data"]["dates"] == "next Friday for 5 days"
        assert result["data"]["travelers"] == "2 adults"
        assert result["data"]["interests"] == "food, culture"

    @pytest.mark.asyncio
    async def test_save_empty_fields_excluded(self) -> None:
        """Null fields not included in saved data."""
        result = await save_travel_context.ainvoke(
            {"destination": "Paris", "dates": None, "travelers": None}
        )

        assert result["saved_fields"] == ["destination"]
        assert "dates" not in result["data"]
        assert "travelers" not in result["data"]

    @pytest.mark.asyncio
    async def test_returns_saved_fields_list(self) -> None:
        """saved_fields matches the keys that were actually provided."""
        result = await save_travel_context.ainvoke(
            {"destination": "Bali", "interests": "beaches"}
        )

        assert sorted(result["saved_fields"]) == ["destination", "interests"]

    @pytest.mark.asyncio
    async def test_instruction_says_dont_tell_user(self) -> None:
        """Instruction tells agent not to mention saving to user."""
        result = await save_travel_context.ainvoke({"destination": "Rome"})

        assert "do NOT tell the user" in result["instruction"]

    @pytest.mark.asyncio
    async def test_save_no_fields_returns_empty(self) -> None:
        """When no fields provided, saved_fields is empty."""
        result = await save_travel_context.ainvoke({})

        assert result["status"] == "saved"
        assert result["saved_fields"] == []
        assert result["data"] == {}
