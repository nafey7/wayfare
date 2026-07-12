"""Unit tests for get_airline_list and AirlineListCache."""

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.domains.flight.cache import AirlineListCache
from app.domains.flight.schemas import (
    AirlineListItem,
    AirlineListRequest,
    AirlineListResponse,
)
from app.domains.flight.service import FlightService


@pytest.fixture(autouse=True)
def clear_airline_cache():
    """Clear airline list cache before and after each test."""
    AirlineListCache.clear()
    yield
    AirlineListCache.clear()


def create_airline_response(count: int = 3) -> AirlineListResponse:
    """Create mock AirlineListResponse with given airline count."""
    airlines = [
        AirlineListItem(
            iata_code=f"A{i}",
            name=f"Airline {i}",
            logo_url=f"https://example.com/airlines/A{i}.gif",
        )
        for i in range(count)
    ]
    return AirlineListResponse(airlines=airlines)


class TestAirlineListCache:
    """Tests for AirlineListCache."""

    def test_get_returns_none_when_empty(self):
        """Test get() returns None when cache is empty."""
        assert AirlineListCache.get() is None

    def test_get_returns_none_when_expired(self):
        """Test get() returns None when cache entry is expired."""
        response = create_airline_response()
        AirlineListCache.set(response)
        # Manually expire by mutating cache entry
        entry = AirlineListCache._cache[AirlineListCache._cache_key]
        entry["expires_at"] = time.time() - 1
        assert AirlineListCache.get() is None

    def test_set_stores_response_with_correct_ttl(self):
        """Test set() stores response and get() returns it before expiry."""
        response = create_airline_response(5)
        AirlineListCache.set(response)
        cached = AirlineListCache.get()
        assert cached is not None
        assert len(cached.airlines) == 5
        assert cached.airlines[0].iata_code == "A0"

    def test_clear_removes_entry(self):
        """Test clear() removes cache entry."""
        response = create_airline_response()
        AirlineListCache.set(response)
        assert AirlineListCache.get() is not None
        AirlineListCache.clear()
        assert AirlineListCache.get() is None

    def test_is_expired_returns_true_when_empty(self):
        """Test is_expired() returns True when no cache entry."""
        assert AirlineListCache.is_expired() is True

    def test_is_expired_returns_false_when_valid(self):
        """Test is_expired() returns False when cache has valid entry."""
        AirlineListCache.set(create_airline_response())
        assert AirlineListCache.is_expired() is False


class TestGetAirlineList:
    """Tests for FlightService.get_airline_list."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_no_api_call(self):
        """Test cache hit returns cached response without API call."""
        response = create_airline_response(4)
        AirlineListCache.set(response)

        service = FlightService(current_user=None)
        service.client = MagicMock()
        service.client.get_airline_list = AsyncMock()

        result = await service.get_airline_list(AirlineListRequest())

        assert result == response
        assert len(result.airlines) == 4
        service.client.get_airline_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_api_and_caches(self):
        """Test cache miss calls API and caches response."""
        response = create_airline_response(3)
        service = FlightService(current_user=None)
        service.client = MagicMock()
        service.client.get_airline_list = AsyncMock(return_value=response)

        result = await service.get_airline_list(AirlineListRequest())

        assert result == response
        service.client.get_airline_list.assert_called_once()
        cached = AirlineListCache.get()
        assert cached == response

    @pytest.mark.asyncio
    async def test_api_error_propagates(self):
        """Test API error propagates (not swallowed)."""
        service = FlightService(current_user=None)
        service.client = MagicMock()
        service.client.get_airline_list = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock()
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await service.get_airline_list(AirlineListRequest())
