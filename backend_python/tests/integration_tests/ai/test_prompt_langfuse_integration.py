"""Integration tests for Langfuse prompt management.

These tests require:
- LANGFUSE_ENABLED=true
- Valid LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY
- Prompts created in Langfuse dashboard

Run with: pytest tests/integration_tests/ai/test_prompt_langfuse_integration.py -v -m integration
"""

import pytest

from app.ai.graph.flight_graph import get_flight_graph
from app.ai.graph.hotel_graph import get_hotel_graph
from app.ai.graph.supervisor_v2 import get_supervisor_v2_graph
from app.ai.prompt_management import (
    get_flight_prompt,
    get_hotel_prompt,
    get_supervisor_v2_prompt,
    invalidate_prompt_cache,
)
from app.core.config import settings


def langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured."""
    return (
        settings.LANGFUSE_ENABLED
        and settings.LANGFUSE_SECRET_KEY is not None
        and settings.LANGFUSE_PUBLIC_KEY is not None
    )


# Skip all tests if Langfuse not configured
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not langfuse_enabled(),
        reason="Langfuse not enabled or API keys not configured",
    ),
]


class TestLangfuseIntegration:
    """Test integration with real Langfuse instance."""

    def setup_method(self):
        """Clear cache before each test."""
        invalidate_prompt_cache()

    @pytest.mark.integration
    def test_fetch_all_prompts_from_langfuse(self):
        """Test fetching all three prompts from Langfuse."""
        flight = get_flight_prompt()
        hotel = get_hotel_prompt()
        supervisor = get_supervisor_v2_prompt()

        # All prompts should be fetched successfully
        assert len(flight) > 100
        assert len(hotel) > 100
        assert len(supervisor) > 100

        # Should not have template variables
        assert "{{current_date}}" not in flight
        assert "{{current_date}}" not in hotel
        assert "{{current_date}}" not in supervisor

    @pytest.mark.integration
    def test_graphs_initialize_with_langfuse_prompts(self):
        """Test all graphs initialize successfully with Langfuse prompts."""
        flight_graph = get_flight_graph()
        hotel_graph = get_hotel_graph()
        supervisor_graph = get_supervisor_v2_graph()

        # If graphs initialize without error, prompts loaded successfully
        assert flight_graph is not None
        assert hotel_graph is not None
        assert supervisor_graph is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_conversation_works_with_langfuse_prompts(self):
        """Test conversation flow works with Langfuse prompts.

        Note: This test is skipped in CI due to Gemini API IP restrictions.
        Langfuse prompt loading is verified in other tests.
        """
        pytest.skip("Skipped due to Gemini API IP restrictions in CI environment")

    @pytest.mark.integration
    def test_caching_works_with_real_langfuse(self):
        """Test caching reduces actual Langfuse API calls."""
        import time

        # First fetch
        get_flight_prompt()

        # Second fetch - should be cached and instant
        start = time.time()
        get_flight_prompt()
        duration = time.time() - start

        # Cached fetch should be very fast
        assert duration < 0.01  # 10 milliseconds
