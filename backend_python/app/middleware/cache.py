"""Cache control middleware for setting appropriate Cache-Control headers."""

from collections.abc import Awaitable, Callable
from typing import ClassVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware to set Cache-Control headers based on request path.

    Static assets get long cache times, dynamic routes get no caching.
    CloudFlare and browsers will respect these headers.
    """

    # Paths that should be cached (prefix -> max-age in seconds)
    CACHE_PATHS: ClassVar[dict[str, int]] = {
        "/static/": 31536000,  # 1 year - React bundles have hashed filenames
        "/dev/": 3600,  # 1 hour - dev tools don't change often
    }

    # Paths that should explicitly not be cached
    NO_CACHE_PATHS: ClassVar[tuple[str, ...]] = (
        "/api/",
        "/auth/",
        "/chat/",
        "/webhooks/",
        "/health",
        "/agents/",
    )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        path = request.url.path

        # Skip if response already has Cache-Control
        if "cache-control" in response.headers:
            return response

        # Check for cacheable static paths
        for prefix, max_age in self.CACHE_PATHS.items():
            if path.startswith(prefix):
                response.headers["Cache-Control"] = f"public, max-age={max_age}"
                return response

        # Root path (index.html) - 1 hour cache, purged on deploy
        if path == "/":
            response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
            return response

        # Explicitly no-cache for API routes
        for prefix in self.NO_CACHE_PATHS:
            if path.startswith(prefix):
                response.headers["Cache-Control"] = "no-store"
                return response

        return response
