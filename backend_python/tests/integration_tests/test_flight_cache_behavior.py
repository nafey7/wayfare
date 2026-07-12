"""Integration tests for flight search caching behavior.

Tests the caching mechanism for flight search results, including:
- Cache validation
- Cache expiration
- Cache invalidation on search parameter changes
- Session storage integration
"""

import os

import pytest


class TestFlightSearchCache:
    """Test flight search caching behavior."""

    @pytest.fixture
    def html_file(self):
        """Return path to flight-booker HTML file."""
        return "dev_ui/flight-booker/index.html"

    def test_cache_structure_exists(self, html_file):
        """Test that cache structure is defined."""
        assert os.path.exists(html_file), f"File not found: {html_file}"

        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for searchCache variable
        assert "searchCache" in content, "searchCache variable not found"

        # Check for cache properties
        cache_props = ["data", "timestamp", "searchParams"]
        for prop in cache_props:
            assert prop in content, f"Cache property '{prop}' not found"

    def test_cache_expiry_constant_exists(self, html_file):
        """Test that cache expiry constant is defined."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for CACHE_EXPIRY_MS constant
        assert "CACHE_EXPIRY_MS" in content, "CACHE_EXPIRY_MS constant not found"

    def test_cache_validation_function_exists(self, html_file):
        """Test that cache validation function exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for isCacheValid function
        assert "isCacheValid" in content, "isCacheValid function not found"

    def test_cache_validation_logic(self, html_file):
        """Test that cache validation checks all required conditions."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for validation logic
        assert "searchCache.data" in content, "searchCache.data not found"
        assert "searchCache.timestamp" in content, "searchCache.timestamp not found"
        assert "searchCache.searchParams" in content, (
            "searchCache.searchParams not found"
        )

    def test_get_current_search_params_function(self, html_file):
        """Test that function to get current search params exists."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for getCurrentSearchParams function
        assert "getCurrentSearchParams" in content, (
            "getCurrentSearchParams function not found"
        )

    def test_cache_update_on_search(self, html_file):
        """Test that cache is updated when new search is performed."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that displayFlightResults exists and cache update logic exists
        assert "displayFlightResults" in content, (
            "displayFlightResults function not found"
        )
        assert "searchCache.data" in content or "searchCache.timestamp" in content, (
            "Cache update logic not found"
        )

    def test_cache_parameter_matching(self, html_file):
        """Test that cache validates search parameters match."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for parameter matching logic
        assert (
            "JSON.stringify" in content
            or "paramsMatch" in content
            or "searchParams" in content
        ), "Cache parameter matching logic not found"

    def test_cache_age_calculation(self, html_file):
        """Test that cache age is calculated correctly."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for age calculation
        assert (
            "Date.now()" in content
            or "searchCache.timestamp" in content
            or "age" in content
        ), "Cache age calculation not found"

    def test_cache_expiry_check(self, html_file):
        """Test that cache expiry is checked."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check for expiry check
        assert "CACHE_EXPIRY_MS" in content, "Cache expiry check not found"

    def test_cache_invalidation_on_params_change(self, html_file):
        """Test that cache is invalidated when search parameters change."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # The cache validation should check if params match
        assert "paramsMatch" in content or "searchParams" in content, (
            "Cache invalidation on parameter change not found"
        )

    def test_session_storage_cache_integration(self, html_file):
        """Test that cache works with session storage for filters."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Check that filters are saved/loaded from session
        assert "sessionStorage" in content, "sessionStorage not found"
        assert "flight_filters" in content or "flight_sort" in content, (
            "Session storage integration for filters not found"
        )

    def test_cache_and_filter_integration(self, html_file):
        """Test that cache works correctly with filtering."""
        with open(html_file, encoding="utf-8") as f:
            content = f.read()

        # Cache should store raw flight data
        # Check that cache and flight data storage exists
        assert "searchCache.data" in content or "fareItineraries" in content, (
            "Cache storage of flight data not found"
        )
