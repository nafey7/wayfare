"""In-memory cache for hotel search sessions and room rates.

FlightLogic Hotel API sessions expire after 20 minutes.
This cache stores search responses to allow room rate lookups and bookings.
"""

import logging
import time
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class HotelSessionCache:
    """Simple in-memory cache for hotel search sessions with TTL.

    Stores hotel search responses keyed by user_id + session_id.
    Automatically expires entries after TTL (default 20 minutes per FlightLogic API).
    """

    # Class-level cache shared across all instances
    _cache: ClassVar[dict[str, dict[str, Any]]] = {}
    _default_ttl: ClassVar[int] = (
        1200  # 20 minutes in seconds (FlightLogic session TTL)
    )

    @classmethod
    def set(cls, user_id: str, session_id: str, search_response: Any) -> None:
        """Store hotel search response in cache.

        Args:
            user_id: User ID
            session_id: FlightLogic session ID from the search response
            search_response: HotelSearchResponse object
        """
        cache_key = cls._make_key(user_id, session_id)
        cls._cache[cache_key] = {
            "response": search_response,
            "expires_at": time.time() + cls._default_ttl,
        }
        logger.debug(
            f"Cached hotel search response for {cache_key} (TTL: {cls._default_ttl}s)"
        )

    @classmethod
    def get(cls, user_id: str, session_id: str) -> Any | None:
        """Retrieve hotel search response from cache.

        Args:
            user_id: User ID
            session_id: FlightLogic session ID from the booking request

        Returns:
            HotelSearchResponse if found and not expired, None otherwise
        """
        cache_key = cls._make_key(user_id, session_id)
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
    def _make_key(cls, user_id: str, session_id: str) -> str:
        """Create cache key from user_id and session_id.

        Args:
            user_id: User ID
            session_id: FlightLogic session ID

        Returns:
            Cache key string
        """
        # Truncate session_id for cleaner logs (first 12 chars)
        truncated_session = session_id[:12] if session_id else "unknown"
        return f"{user_id}:{truncated_session}"
