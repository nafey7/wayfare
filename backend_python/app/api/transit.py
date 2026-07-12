"""Transit routes API endpoints.

Thin API layer that delegates to transit domain service.
All request/response logging happens automatically via LoggingMiddleware.
Business logic logging happens in TransitService.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.transit import (
    TransitRouteRequest,
    TransitRouteResponse,
)
from app.domains.transit.exceptions import (
    TransitRouteError,
    TransitValidationError,
)
from app.domains.transit.service import TransitService, get_transit_service

router = APIRouter(prefix="/transit", tags=["Transit"])
logger = logging.getLogger(__name__)


@router.post("/routes", response_model=TransitRouteResponse)
async def compute_routes(
    request: TransitRouteRequest,
    service: TransitService = Depends(get_transit_service),
) -> TransitRouteResponse:
    """Compute transit routes between origin and destination.

    Uses Google Maps Platform Routes API to find transit routes.

    Args:
        request: Transit route request with origin, destination, and preferences
        service: Transit service instance (injected)

    Returns:
        TransitRouteResponse with available routes

    Raises:
        HTTPException: 400 for validation errors, 503 for service errors
    """
    # Log the received request for debugging
    logger.debug("✅ [TRANSIT API] Endpoint handler called successfully!")

    try:
        return await service.compute_routes(request)
    except TransitValidationError as e:
        logger.error(f"❌ [TRANSIT API] Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except TransitRouteError as e:
        logger.error(f"❌ [TRANSIT API] Route error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        logger.error(f"❌ [TRANSIT API] Value error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(
            f"❌ [TRANSIT API] Unexpected error: {type(e).__name__}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e
