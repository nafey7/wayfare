"""Google Geocoding API service for city/country resolution.

This module provides geocoding utilities for resolving city names to countries,
handling ambiguous city names (e.g., "Utrecht" -> Netherlands or South Africa),
and providing disambiguation options to users.

Usage:
    from app.shared.geocoding import GeocodingService

    service = GeocodingService()
    results = await service.geocode_city("Utrecht")
    # Returns multiple results for disambiguation

    country = await service.get_country_from_city("Paris")
    # Returns "France" for unambiguous cities
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Google Geocoding API endpoint
GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Timeout for API requests (seconds)
API_TIMEOUT = 10.0

# Maximum retries for transient failures
MAX_RETRIES = 3


class GeocodingResult(BaseModel):
    """Result from geocoding a city name.

    Attributes:
        city: The city name as returned by Google
        country: Full country name (e.g., "Netherlands")
        country_code: ISO 3166-1 alpha-2 code (e.g., "NL")
        formatted_address: Full formatted address from Google
        lat: Latitude coordinate
        lng: Longitude coordinate
        result_types: Google place types (e.g., ["locality", "political"] or ["country", "political"])
    """

    city: str
    country: str
    country_code: str
    formatted_address: str
    lat: float
    lng: float
    result_types: list[str] = []


class GeocodingError(Exception):
    """Raised when geocoding operation fails."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or "GEOCODING_ERROR"
        super().__init__(self.message)


class GeocodingService:
    """Google Geocoding API wrapper for city/country resolution.

    This service handles:
    - City to country resolution for hotel searches
    - Disambiguation when multiple locations match a city name
    - Graceful fallback when API is unavailable

    Example:
        >>> service = GeocodingService()
        >>> results = await service.geocode_city("Birmingham")
        >>> # Returns results for both Birmingham, UK and Birmingham, USA
        >>> for r in results:
        ...     print(f"{r.city}, {r.country}")
        Birmingham, United Kingdom
        Birmingham, United States
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the geocoding service.

        Args:
            api_key: Google API key. If not provided, loads from settings.
        """
        from app.core.config import settings

        self.api_key = api_key or settings.GOOGLE_API_KEY
        if not self.api_key:
            logger.warning(
                "GOOGLE_API_KEY not configured - geocoding will be unavailable"
            )

    async def geocode_city(self, city: str) -> list[GeocodingResult]:
        """Geocode a city name to get location details.

        Returns multiple results when the city name is ambiguous
        (e.g., "Utrecht" exists in Netherlands and South Africa).

        Args:
            city: City name to geocode (e.g., "Utrecht", "Paris, France")

        Returns:
            List of GeocodingResult objects, sorted by relevance.
            Empty list if no results found or API unavailable.

        Example:
            >>> results = await service.geocode_city("Cambridge")
            >>> len(results)  # Multiple matches
            2
            >>> results[0].country
            'United Kingdom'
            >>> results[1].country
            'United States'
        """
        if not self.api_key:
            logger.warning("Geocoding unavailable - no API key configured")
            return []

        params = {
            "address": city,
            "key": self.api_key,
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                    response = await client.get(GEOCODING_API_URL, params=params)
                    response.raise_for_status()
                    data = response.json()

                results = await self._parse_geocoding_response(data, city)
                logger.info(
                    f"Geocoding '{city}' returned {len(results)} result(s): "
                    f"{[f'{r.city}, {r.country}' for r in results]}"
                )
                return results

            except httpx.TimeoutException:
                logger.warning(
                    f"Geocoding timeout for '{city}' (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                if attempt == MAX_RETRIES - 1:
                    return []

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Geocoding HTTP error for '{city}': {e.response.status_code}"
                )
                return []

            except Exception as e:
                logger.error(f"Geocoding error for '{city}': {e}")
                return []

        return []

    async def get_country_from_city(self, city: str) -> str | None:
        """Get the country name for a city.

        Convenience method that returns the country from the first (most relevant)
        geocoding result. Use geocode_city() when disambiguation is needed.

        Args:
            city: City name to look up

        Returns:
            Country name (e.g., "France") or None if not found
        """
        results = await self.geocode_city(city)
        if results:
            return results[0].country
        return None

    async def get_country_code_from_city(self, city: str) -> str | None:
        """Get the ISO country code for a city.

        Args:
            city: City name to look up

        Returns:
            ISO 3166-1 alpha-2 country code (e.g., "FR") or None if not found
        """
        results = await self.geocode_city(city)
        if results:
            return results[0].country_code
        return None

    async def _parse_geocoding_response(
        self, data: dict[str, Any], original_query: str
    ) -> list[GeocodingResult]:
        """Parse Google Geocoding API response into GeocodingResult objects.

        Args:
            data: Raw API response
            original_query: Original search query for logging

        Returns:
            List of parsed GeocodingResult objects
        """
        status = data.get("status", "UNKNOWN")

        if status == "ZERO_RESULTS":
            logger.info(f"No geocoding results for '{original_query}'")
            return []

        if status != "OK":
            logger.warning(
                f"Geocoding API returned status '{status}' for '{original_query}'"
            )
            return []

        results: list[GeocodingResult] = []

        for item in data.get("results", []):
            try:
                result = self._parse_single_result(item)
                if result:
                    # If the result is a POI/landmark (not a locality) and the
                    # "city" is actually a state/region, reverse-geocode the
                    # coordinates to find the real nearest city.
                    result = await self._refine_city_if_needed(result)
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse geocoding result: {e}")
                continue

        # Limit to top 5 results (Google returns most relevant first)
        # No deduplication - same-country cities can be important (e.g., Springfield MO vs MA)
        max_results = 5
        limited_results = results[:max_results]

        logger.debug(
            f"Geocoded '{original_query}' to {len(limited_results)} result(s) (limited from {len(results)})"
        )
        return limited_results

    async def get_location_types(self, query: str) -> list[str]:
        """Return the top-level ``types`` array from the first geocode result.

        Bypasses the ``geocode_city`` city/country parser (which filters out
        results that don't have BOTH a locality AND a country) so callers
        can deterministically tell a country query ("US") from a city
        query ("New York"). Used by the itinerary trip extractor to
        decide whether an origin needs a follow-up "which city?" question.

        Returns:
            Top-level ``types`` of ``results[0]`` (e.g. ``["country", "political"]``
            for "US", ``["locality", "political"]`` for "Tokyo"). Empty list
            on geocoding failure / no results / no API key — safe default
            for the caller to interpret as "couldn't determine".
        """
        if not self.api_key or not query.strip():
            return []

        params = {"address": query, "key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.get(GEOCODING_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            logger.warning("get_location_types failed for %r", query, exc_info=True)
            return []

        if data.get("status") != "OK":
            return []
        results = data.get("results") or []
        if not results:
            return []
        types = results[0].get("types") or []
        return list(types) if isinstance(types, list) else []

    def _parse_single_result(self, item: dict[str, Any]) -> GeocodingResult | None:
        """Parse a single result from the API response.

        Args:
            item: Single result item from API response

        Returns:
            GeocodingResult or None if parsing fails
        """
        address_components = item.get("address_components", [])
        geometry = item.get("geometry", {})
        location = geometry.get("location", {})

        # Extract city and country from address components
        city = ""
        country = ""
        country_code = ""

        for component in address_components:
            types = component.get("types", [])

            # City can be in different types depending on the location
            if "locality" in types:
                city = component.get("long_name", "")
            elif "administrative_area_level_1" in types and not city:
                # Fallback to admin area if no locality
                city = component.get("long_name", "")
            elif "postal_town" in types and not city:
                # UK uses postal_town
                city = component.get("long_name", "")

            if "country" in types:
                country = component.get("long_name", "")
                country_code = component.get("short_name", "")

        if not city or not country:
            return None

        return GeocodingResult(
            city=city,
            country=country,
            country_code=country_code,
            formatted_address=item.get("formatted_address", ""),
            lat=location.get("lat", 0.0),
            lng=location.get("lng", 0.0),
            result_types=item.get("types", []),
        )

    async def _refine_city_if_needed(self, result: GeocodingResult) -> GeocodingResult:
        """Refine city name via reverse geocoding when the forward geocode returned a
        state/region instead of a real city.

        This happens for POI/landmark queries like "Walt Disney World" where Google
        Geocoding has no ``locality`` component — the fallback picks up
        ``administrative_area_level_1`` (e.g. "Florida") which is too broad for
        hotel search APIs that need a city.

        When the result types do NOT include ``locality`` (i.e. it's a landmark,
        establishment, etc.), we reverse-geocode the coordinates to find the
        nearest city.  The original lat/lng (the landmark's position) are kept so
        that ``nearby_location`` proximity sorting still works.
        """
        # Only refine when the forward result is NOT already a city
        is_locality = "locality" in result.result_types
        if is_locality:
            return result

        # Reverse geocode: ask for the nearest locality at these coordinates
        params = {
            "latlng": f"{result.lat},{result.lng}",
            "result_type": "locality",
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.get(GEOCODING_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "OK":
                return result

            items = data.get("results", [])
            if not items:
                return result

            reverse_result = self._parse_single_result(items[0])
            if not reverse_result or not reverse_result.city:
                return result

            logger.info(
                f"Refined city from '{result.city}' to '{reverse_result.city}' "
                f"via reverse geocode at ({result.lat}, {result.lng})"
            )

            # Keep the original landmark coordinates for nearby sorting,
            # but use the real city/country from reverse geocode
            return GeocodingResult(
                city=reverse_result.city,
                country=reverse_result.country,
                country_code=reverse_result.country_code,
                formatted_address=result.formatted_address,
                lat=result.lat,  # Keep landmark coords
                lng=result.lng,  # Keep landmark coords
                result_types=result.result_types,  # Keep original types
            )

        except Exception as e:
            logger.warning(f"Reverse geocode refinement failed: {e}")
            return result

    def format_disambiguation_options(self, results: list[GeocodingResult]) -> str:
        """Format multiple geocoding results as user-friendly options.

        Args:
            results: List of geocoding results to format

        Returns:
            Formatted string for user display

        Example:
            >>> options = service.format_disambiguation_options(results)
            >>> print(options)
            Did you mean:
            1. Utrecht, Netherlands
            2. Utrecht, South Africa
        """
        if not results:
            return ""

        if len(results) == 1:
            return f"{results[0].city}, {results[0].country}"

        lines = ["Did you mean:"]
        for i, result in enumerate(results, 1):
            # Use formatted_address for more detail (includes state/region)
            lines.append(f"{i}. {result.formatted_address}")

        return "\n".join(lines)


# Module-level convenience functions
async def geocode_city(city: str) -> list[GeocodingResult]:
    """Geocode a city name (convenience function).

    Args:
        city: City name to geocode

    Returns:
        List of GeocodingResult objects
    """
    service = GeocodingService()
    return await service.geocode_city(city)


async def get_country_from_city(city: str) -> str | None:
    """Get country from city name (convenience function).

    Args:
        city: City name to look up

    Returns:
        Country name or None
    """
    service = GeocodingService()
    return await service.get_country_from_city(city)


__all__ = [
    "GeocodingError",
    "GeocodingResult",
    "GeocodingService",
    "geocode_city",
    "get_country_from_city",
]
