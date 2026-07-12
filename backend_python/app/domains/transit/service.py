"""Transit routes service - clean domain service following flight/hotel service patterns."""

import logging

from fastapi import Depends

from app.domains.auth.dependencies import get_current_user
from app.domains.transit.exceptions import TransitRouteError, TransitValidationError
from app.domains.transit.schemas import TransitRouteRequest, TransitRouteResponse

from ..user import UserPublic

logger = logging.getLogger(__name__)


class TransitService:
    """Instance-based transit service with user context."""

    def __init__(self, current_user: UserPublic | None = None) -> None:
        """Initialize transit service with user context."""
        # Lazy import to avoid circular dependency
        from integrations.googlemaps import get_googlemaps_client

        self.current_user = current_user
        self.client = get_googlemaps_client()

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _get_base_log_context(self) -> dict[str, str]:
        """Get base logging context shared across all operations.

        Returns:
            Base context with user_id (if authenticated)
        """
        context = {}
        if self.current_user:
            context["user_id"] = str(self.current_user.id)
        return context

    # ============================================================
    # ROUTE OPERATIONS
    # ============================================================

    async def compute_routes(
        self, request: TransitRouteRequest
    ) -> TransitRouteResponse:
        """Compute transit routes between origin and destination.

        Args:
            request: Transit route request with origin, destination, and preferences

        Returns:
            TransitRouteResponse with available routes

        Raises:
            TransitRouteError: If route computation fails
            TransitValidationError: If request validation fails
        """
        # Build location strings for logging
        origin_str = (
            request.origin.address
            if request.origin.address
            else f"{request.origin.lat_lng.latitude:.4f}, {request.origin.lat_lng.longitude:.4f}"
            if request.origin.lat_lng
            else "N/A"
        )
        destination_str = (
            request.destination.address
            if request.destination.address
            else f"{request.destination.lat_lng.latitude:.4f}, {request.destination.lat_lng.longitude:.4f}"
            if request.destination.lat_lng
            else "N/A"
        )

        log_context = {
            **self._get_base_log_context(),
            "origin": origin_str,
            "destination": destination_str,
        }

        logger.info(
            f"Computing transit routes: {origin_str} → {destination_str}",
            extra=log_context,
        )

        try:
            # Make API call via Google Maps client
            response = await self.client.compute_routes(request)

            logger.info(
                f"Transit routes computed successfully: {len(response.routes)} route(s) found",
                extra={**log_context, "route_count": len(response.routes)},
            )

            return response

        except TransitValidationError:
            raise
        except TransitRouteError:
            raise
        except Exception as e:
            logger.error(f"Transit route computation failed: {e!s}", exc_info=True)
            raise TransitRouteError(reason=str(e)) from e


def get_transit_service(
    current_user: UserPublic | None = Depends(get_current_user(required=False)),
) -> TransitService:
    """Get transit service instance with optional user context.

    FastAPI dependency that automatically injects the current user if authenticated.

    Args:
        current_user: Current authenticated user (optional, injected via dependency)

    Returns:
        TransitService instance
    """
    logger.debug(
        f"🔍 [DEPENDENCY] get_transit_service called with user: {current_user}"
    )
    service = TransitService(current_user=current_user)
    logger.debug(f"🔍 [DEPENDENCY] TransitService instance created: {service}")
    return service
