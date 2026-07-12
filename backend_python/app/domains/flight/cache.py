"""In-memory cache for revalidate responses to persist between API requests."""

import logging
import time
from typing import Any, ClassVar

from app.domains.flight.schemas import AirlineListResponse

logger = logging.getLogger(__name__)


class RevalidateCache:
    """Simple in-memory cache for revalidate responses with TTL.

    Stores revalidate responses keyed by user_id + fare_source_code.
    Automatically expires entries after TTL (default 15 minutes).
    """

    # Class-level cache shared across all instances
    _cache: ClassVar[dict[str, dict[str, Any]]] = {}
    _default_ttl: ClassVar[int] = 900  # 15 minutes in seconds

    @classmethod
    def set(cls, user_id: str, fare_source_code: str, revalidate_response: Any) -> None:
        """Store revalidate response in cache.

        Args:
            user_id: User ID
            fare_source_code: Fare source code from the revalidate request
            revalidate_response: FlightRevalidateResponse object
        """
        cache_key = cls._make_key(user_id, fare_source_code)
        cls._cache[cache_key] = {
            "response": revalidate_response,
            "expires_at": time.time() + cls._default_ttl,
        }
        logger.debug(
            f"Cached revalidate response for {cache_key} (TTL: {cls._default_ttl}s)"
        )

    @classmethod
    def get(cls, user_id: str, fare_source_code: str) -> Any | None:
        """Retrieve revalidate response from cache.

        Args:
            user_id: User ID
            fare_source_code: Fare source code from the booking request

        Returns:
            FlightRevalidateResponse if found and not expired, None otherwise
        """
        cache_key = cls._make_key(user_id, fare_source_code)
        entry = cls._cache.get(cache_key)

        if not entry:
            logger.debug(f"Cache miss for {cache_key}")
            return None

        # Check if expired
        if time.time() > entry["expires_at"]:
            logger.debug(f"Cache expired for {cache_key}")
            del cls._cache[cache_key]
            return None

        logger.debug(f"Cache hit for {cache_key}")
        return entry["response"]

    @classmethod
    def clear_user(cls, user_id: str) -> None:
        """Clear all cache entries for a specific user.

        Args:
            user_id: User ID
        """
        keys_to_delete = [key for key in cls._cache if key.startswith(f"{user_id}:")]
        for key in keys_to_delete:
            del cls._cache[key]
        logger.debug(f"Cleared {len(keys_to_delete)} cache entries for user {user_id}")

    @classmethod
    def clear_expired(cls) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries cleared
        """
        current_time = time.time()
        keys_to_delete = [
            key
            for key, entry in cls._cache.items()
            if current_time > entry["expires_at"]
        ]

        for key in keys_to_delete:
            del cls._cache[key]

        if keys_to_delete:
            logger.debug(f"Cleared {len(keys_to_delete)} expired cache entries")

        return len(keys_to_delete)

    @classmethod
    def _make_key(cls, user_id: str, fare_source_code: str) -> str:
        """Create cache key from user_id and fare_source_code.

        Args:
            user_id: User ID
            fare_source_code: Fare source code

        Returns:
            Cache key string
        """
        # Truncate fare_source_code for cleaner logs (first 8 chars)
        truncated_code = fare_source_code[:8] if fare_source_code else "unknown"
        return f"{user_id}:{truncated_code}"


class AirportListCache:
    """In-memory cache for airport list from FlightLogic API.

    Airport list is relatively static (commercial airports don't change frequently),
    so we use a longer TTL (24 hours) to reduce API calls while keeping data fresh.

    This cache stores the complete airport list response keyed by a single
    global key since the airport list is the same for all users.
    """

    # Class-level cache shared across all instances
    _cache: ClassVar[dict[str, dict[str, Any]]] = {}
    _default_ttl: ClassVar[int] = 86400  # 24 hours in seconds
    _cache_key: ClassVar[str] = "airport_list"

    @classmethod
    def get(cls) -> Any | None:
        """Get cached airport list.

        Returns:
            AirportListResponse if found and not expired, None otherwise
        """
        entry = cls._cache.get(cls._cache_key)

        if not entry:
            logger.debug("Airport list cache miss")
            return None

        # Check if expired
        if time.time() > entry["expires_at"]:
            logger.debug("Airport list cache expired")
            del cls._cache[cls._cache_key]
            return None

        logger.debug("Airport list cache hit")
        return entry["response"]

    @classmethod
    def set(cls, airport_list_response: Any) -> None:
        """Store airport list in cache.

        Args:
            airport_list_response: AirportListResponse object
        """
        cls._cache[cls._cache_key] = {
            "response": airport_list_response,
            "expires_at": time.time() + cls._default_ttl,
        }
        airport_count = (
            len(airport_list_response.airports)
            if hasattr(airport_list_response, "airports")
            else 0
        )
        logger.info(
            f"Cached airport list with {airport_count} airports (TTL: {cls._default_ttl}s = 24h)"
        )

    @classmethod
    def clear(cls) -> None:
        """Clear the airport list cache."""
        if cls._cache_key in cls._cache:
            del cls._cache[cls._cache_key]
            logger.debug("Cleared airport list cache")

    @classmethod
    def is_expired(cls) -> bool:
        """Check if cached airport list is expired.

        Returns:
            True if expired or not cached, False if still valid
        """
        entry = cls._cache.get(cls._cache_key)
        if not entry:
            return True
        return time.time() > entry["expires_at"]


class AirlineListCache:
    """In-memory cache for airline list from FlightLogic API.

    Airline list is relatively static, so we use a longer TTL (24 hours)
    to reduce API calls while keeping data fresh for logo enrichment.
    """

    _cache: ClassVar[dict[str, dict[str, Any]]] = {}
    _default_ttl: ClassVar[int] = 86400  # 24 hours in seconds
    _cache_key: ClassVar[str] = "airline_list"

    @classmethod
    def get(cls) -> AirlineListResponse | None:
        """Get cached airline list.

        Returns:
            AirlineListResponse if found and not expired, None otherwise
        """
        entry = cls._cache.get(cls._cache_key)

        if not entry:
            logger.debug("Airline list cache miss")
            return None

        if time.time() > entry["expires_at"]:
            logger.debug("Airline list cache expired")
            del cls._cache[cls._cache_key]
            return None

        logger.debug("Airline list cache hit")
        return entry["response"]

    @classmethod
    def set(cls, airline_list_response: Any) -> None:
        """Store airline list in cache.

        Args:
            airline_list_response: AirlineListResponse object
        """
        cls._cache[cls._cache_key] = {
            "response": airline_list_response,
            "expires_at": time.time() + cls._default_ttl,
        }
        airline_count = (
            len(airline_list_response.airlines)
            if hasattr(airline_list_response, "airlines")
            else 0
        )
        logger.info(
            f"Cached airline list with {airline_count} airlines (TTL: {cls._default_ttl}s = 24h)"
        )

    @classmethod
    def clear(cls) -> None:
        """Clear the airline list cache."""
        if cls._cache_key in cls._cache:
            del cls._cache[cls._cache_key]
            logger.debug("Cleared airline list cache")

    @classmethod
    def is_expired(cls) -> bool:
        """Check if cached airline list is expired."""
        entry = cls._cache.get(cls._cache_key)
        if not entry:
            return True
        return time.time() > entry["expires_at"]
