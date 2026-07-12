"""Unit tests for itinerary generation prompt rules.

Verifies that the ITINERARY_GENERATION_PROMPT contains proper
arrival/departure day handling so itineraries don't conflict
with actual flight times shown later.

Run with: pytest tests/unit_tests/test_ai/test_itinerary_prompt.py -v
"""

from app.ai.graph.prompts.itinerary_agent import ITINERARY_GENERATION_PROMPT


class TestItineraryPromptArrivalDepartureRules:
    """Ensure the prompt instructs the LLM to keep Day 1 and Last Day time-agnostic."""

    def test_prompt_has_arrival_day_rules(self):
        """Day 1 must be treated as an arrival day with no morning sightseeing."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "day 1 is arrival" in prompt
        assert "no morning sightseeing" in prompt

    def test_prompt_has_departure_day_rules(self):
        """Last day must be treated as a departure day."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "last day is departure" in prompt
        assert "morning activity + departure" in prompt

    def test_prompt_forbids_specific_flight_times(self):
        """Prompt must instruct LLM to never mention specific flight times."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "never mention specific flight times" in prompt

    def test_prompt_forbids_tbd_placeholder_text(self):
        """Prompt must ban 'TBD' and placeholder text from user-facing output."""
        prompt = ITINERARY_GENERATION_PROMPT
        assert '"TBD"' in prompt

    def test_day1_uses_travel_arrival(self):
        """Day 1 should reference arrival."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "arrival" in prompt
        assert "arrive in {destination}" in prompt

    def test_last_day_uses_departure(self):
        """Last day should schedule departure."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "departure" in prompt
        assert "last day is departure" in prompt

    def test_origin_not_provided_handling(self):
        """Prompt must handle 'not provided' origin gracefully."""
        prompt = ITINERARY_GENERATION_PROMPT.lower()
        assert "not provided" in prompt
        assert 'origin "not provided"' in prompt

    def test_middle_days_have_three_activities(self):
        """Middle days should have Morning, Afternoon, Evening activities."""
        prompt = ITINERARY_GENERATION_PROMPT
        assert "Middle days" in prompt
        assert "Morning, Afternoon, Evening" in prompt
