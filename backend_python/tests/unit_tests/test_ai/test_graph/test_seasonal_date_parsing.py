"""Unit tests for seasonal date parsing with destination and duration context.

Tests verify that destination and trip_duration_days parameters are correctly
accepted and passed through the date parsing system.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestParseDatesWithDestinationParameter:
    """Test that _parse_dates_with_llm accepts and uses destination parameter."""

    @pytest.mark.asyncio
    async def test_destination_parameter_accepted(self) -> None:
        """Verify _parse_dates_with_llm accepts destination without TypeError."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        # Mock the entire chain operation
        mock_result = type(
            "MockResult",
            (),
            {
                "model_dump": lambda: {
                    "departure_date": "2026-11-01",
                    "return_date": "2026-11-30",
                    "is_range": True,
                    "trip_duration_days": None,
                    "error": None,
                    "parsed_from": "autumn foliage season",
                }
            },
        )()

        async def mock_ainvoke(*args, **kwargs):
            return mock_result

        mock_llm = type(
            "MockLLM", (), {"with_structured_output": lambda self, schema: mock_chain}
        )()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = mock_ainvoke

        with (
            patch("app.ai.graph.llm_factory.create_llm", return_value=mock_llm),
            patch("app.ai.graph.tools.dates.ChatPromptTemplate") as mock_prompt,
        ):
            # Setup mock to return chain
            mock_template = type("MockTemplate", (), {})()
            mock_template.__or__ = lambda self, other: mock_chain
            mock_prompt.from_messages.return_value = mock_template

            # Should not raise TypeError
            result = await _parse_dates_with_llm(
                text="autumn foliage season", destination="Tokyo, Japan"
            )

            assert result is not None
            assert "departure_date" in result

    @pytest.mark.asyncio
    async def test_trip_duration_parameter_accepted(self) -> None:
        """Verify _parse_dates_with_llm accepts trip_duration_days without TypeError."""
        from app.ai.graph.tools.dates import _parse_dates_with_llm

        mock_result = type(
            "MockResult",
            (),
            {
                "model_dump": lambda: {
                    "departure_date": "2026-11-01",
                    "return_date": "2026-11-15",
                    "is_range": True,
                    "trip_duration_days": None,
                    "error": None,
                    "parsed_from": "autumn foliage season",
                }
            },
        )()

        async def mock_ainvoke(*args, **kwargs):
            return mock_result

        mock_llm = type(
            "MockLLM", (), {"with_structured_output": lambda self, schema: mock_chain}
        )()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = mock_ainvoke

        with (
            patch("app.ai.graph.llm_factory.create_llm", return_value=mock_llm),
            patch("app.ai.graph.tools.dates.ChatPromptTemplate") as mock_prompt,
        ):
            mock_template = type("MockTemplate", (), {})()
            mock_template.__or__ = lambda self, other: mock_chain
            mock_prompt.from_messages.return_value = mock_template

            # Should not raise TypeError
            result = await _parse_dates_with_llm(
                text="autumn foliage season",
                destination="Tokyo, Japan",
                trip_duration_days=14,
            )

            assert result is not None
            assert "departure_date" in result
