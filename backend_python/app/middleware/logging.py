"""API request/response logging middleware.

Provides automatic logging for all HTTP requests with:
- Request/response timing
- HTTP status codes
- Client information
- Smart log levels based on status codes
- Route-based logger selection (flights, hotels, vs backend)
"""

import time
from typing import ClassVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    get_backend_logger,
    get_flights_logger,
    get_hotels_logger,
    get_places_logger,
)

# Use route-specific loggers
flights_logger = get_flights_logger()
hotels_logger = get_hotels_logger()
places_logger = get_places_logger()
backend_logger = get_backend_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests and responses with structured data.

    Automatically captures:
    - Request method and path
    - Response status code
    - Request duration in milliseconds
    - Client IP and user agent

    Log levels:
    - 2xx responses: INFO
    - 4xx responses: WARNING
    - 5xx responses: ERROR
    - Exceptions: ERROR with stack trace
    """

    # Paths to skip logging (high-frequency, low-value endpoints)
    SKIP_PATHS: ClassVar[set[str]] = {
        "/docs",
        "/openapi.json",
        "/redoc",
        "/health",
        "/ping",
        "/api/proxy/image",  # Image proxy endpoint - too many requests
        "/api/places/photos/",  # Place photo media - high frequency when loading images
    }

    def _get_logger(self, path: str):
        """Select appropriate logger based on request path.

        Routes:
        - /api/flights/* -> flights_logger -> /ecs/voya-flights
        - /api/hotels/* -> hotels_logger -> /ecs/{environment}-voya-hotels
        - /api/places/* -> places_logger -> /ecs/voya-places
        - All other paths -> backend_logger -> /ecs/voya-backend
        """
        if path.startswith("/api/flights/"):
            return flights_logger
        if path.startswith("/api/hotels/"):
            return hotels_logger
        if path.startswith("/api/places/"):
            return places_logger
        return backend_logger

    async def dispatch(self, request: Request, call_next):
        """Process request with logging."""

        # Skip logging for documentation and health check endpoints
        if any(request.url.path.startswith(p) for p in LoggingMiddleware.SKIP_PATHS):
            return await call_next(request)

        # Select logger based on route
        logger = self._get_logger(request.url.path)

        # Start timing
        start_time = time.time()

        # Extract request information
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }

        # Optional: Add query params for GET requests
        if request.method == "GET" and request.query_params:
            request_info["query_params"] = str(request.query_params)

        # Log request entry
        logger.info(f"→ {request.method} {request.url.path}", extra=request_info)

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Build response info
            response_info = {
                **request_info,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

            # Log based on status code
            if response.status_code >= 500:
                # Server errors - ERROR level
                logger.error(
                    f"← {request.method} {request.url.path} | {response.status_code} | {duration_ms}ms",
                    extra=response_info,
                )
            elif response.status_code >= 400:
                # Client errors - WARNING level
                logger.warning(
                    f"← {request.method} {request.url.path} | {response.status_code} | {duration_ms}ms",
                    extra=response_info,
                )
            else:
                # Success - INFO level
                logger.info(
                    f"← {request.method} {request.url.path} | {response.status_code} | {duration_ms}ms",
                    extra=response_info,
                )

            return response

        except Exception as e:
            # Unhandled exception
            duration_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"✗ {request.method} {request.url.path} | Exception | {duration_ms}ms | {str(e)[:100]}",
                extra={
                    **request_info,
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise
