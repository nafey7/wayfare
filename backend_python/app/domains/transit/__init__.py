"""Transit routes domain package.

Clean domain-driven design for transit route operations using Google Maps Routes API.
"""

from .exceptions import (
    TransitDomainError,
    TransitRouteError,
    TransitValidationError,
)
from .schemas import (
    RouteTravelMode,
    TransitRouteRequest,
    TransitRouteResponse,
)

__all__ = [
    "RouteTravelMode",
    "TransitDomainError",
    "TransitRouteError",
    "TransitRouteRequest",
    "TransitRouteResponse",
    "TransitValidationError",
]

# TransitService NOT imported here - used via dependency injection
# Import directly from app.domains.transit.service where needed
