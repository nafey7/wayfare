"""Airport domain for comprehensive airport resolution.

This module provides two approaches to airport resolution:

1. **New (Recommended)**: AirportService with structured disambiguation
   - Use `get_airport_service()` to get the singleton service
   - Returns `AirportResolution` objects with clear status and options
   - Integrates with GeocodingService for city disambiguation

2. **Legacy**: airport_resolver module-level singleton
   - Kept for backward compatibility
   - Will be deprecated in Phase 2 of #149

Usage (New):
    from app.domains.airport import get_airport_service, AirportResolution

    service = get_airport_service()
    result = await service.resolve("Birmingham")

    if result.status == "needs_disambiguation":
        print(result.suggested_prompt)

Usage (Legacy):
    from app.domains.airport import airport_resolver

    code = await airport_resolver.resolve_airport("London")
"""

# Legacy export (backward compatibility)
from app.domains.airport.airport_resolver import airport_resolver

# New models
from app.domains.airport.models import (
    Airport,
    AirportOption,
    AirportResolution,
    DisambiguationType,
    ResolveContext,
)

# New repository and service
from app.domains.airport.repository import AirportRepository
from app.domains.airport.service import AirportService

# Singleton service instance
_service: AirportService | None = None


def get_airport_service() -> AirportService:
    """Get the singleton AirportService instance.

    Creates the service on first call with default dependencies:
    - AirportRepository (loads mwgg/Airports data)
    - GeocodingService (Google Geocoding API)

    Returns:
        AirportService instance

    Example:
        service = get_airport_service()
        result = await service.resolve("Venice")
    """
    global _service
    if _service is None:
        from app.shared.geocoding import GeocodingService

        repository = AirportRepository()
        geocoding = GeocodingService()
        _service = AirportService(repository, geocoding)
    return _service


def reset_airport_service() -> None:
    """Reset the singleton service (for testing)."""
    global _service
    _service = None


__all__ = [
    "Airport",
    "AirportOption",
    "AirportRepository",
    "AirportResolution",
    "AirportService",
    "DisambiguationType",
    "ResolveContext",
    "airport_resolver",  # Legacy API (backward compatibility)
    "get_airport_service",
    "reset_airport_service",
]
