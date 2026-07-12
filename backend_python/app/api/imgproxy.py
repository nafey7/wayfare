"""imgproxy reverse proxy for local development.

In production, ALB routes /imgproxy/* directly to the imgproxy service.
For local development, this endpoint proxies requests to the imgproxy container.
"""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.core.config import settings

router = APIRouter()

# Use IMGPROXY_INTERNAL_URL for forwarding, fallback to http://imgproxy:8080
# Note: IMGPROXY_URL is for public URLs, this is for internal proxy forwarding
IMGPROXY_INTERNAL_URL = getattr(
    settings, "IMGPROXY_INTERNAL_URL", "http://imgproxy:8080"
)


@router.get("/{path:path}")
async def proxy_imgproxy(path: str, request: Request) -> Response:
    """Proxy requests to imgproxy container.

    This is only used in local development. In production, ALB routes
    /imgproxy/* directly to the imgproxy ECS service.
    """
    # Build the target URL
    target_url = f"{IMGPROXY_INTERNAL_URL}/{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Forward the request to imgproxy
        response = await client.get(
            target_url,
            headers={
                "Accept": request.headers.get("Accept", "image/*"),
            },
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "image/jpeg"),
            headers={
                "Cache-Control": response.headers.get(
                    "Cache-Control", "public, max-age=31536000"
                ),
            },
        )
