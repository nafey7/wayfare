"""Image proxy endpoint for external images to avoid CORS issues."""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/image")
async def proxy_image(
    url: str = Query(..., description="External image URL to proxy"),
) -> Response:
    """Proxy external images to avoid CORS issues.

    This endpoint fetches external images (like TripAdvisor images) and serves them
    to the frontend, bypassing CORS restrictions.
    """
    logger.debug(f"🖼️ [Proxy] Proxying image: {url}")

    # Parse URL to get hostname
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname or ""

        if not hostname:
            logger.warning(f"🖼️ [Proxy] Invalid URL - no hostname: {url}")
            raise HTTPException(
                status_code=400, detail="Invalid URL format - no hostname"
            )

    except ValueError as e:
        logger.warning(f"🖼️ [Proxy] Invalid URL format: {url}")
        raise HTTPException(status_code=400, detail="Invalid URL format") from e

    # Security check: Always block localhost/internal IPs to prevent SSRF attacks
    async def _is_internal_ip(hostname: str) -> bool:
        """Check if hostname resolves to internal/private IP address."""
        # Block localhost variations
        # "0.0.0.0" is checked as a string for SSRF protection, not for network binding
        if hostname in ["localhost", "127.0.0.1", "::1", "0.0.0.0"]:  # nosec B104
            return True

        # Block AWS metadata service
        if hostname == "169.254.169.254":
            return True

        # Try to parse as IP and check if it's private/internal
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # Not an IP address, resolve domain name to check resolved IPs
            try:
                # Resolve hostname to IP addresses to prevent DNS rebinding attacks
                # Use executor to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                resolved_ips = await loop.run_in_executor(
                    None, lambda: socket.gethostbyname_ex(hostname)[2]
                )
                for resolved_ip in resolved_ips:
                    try:
                        ip = ipaddress.ip_address(resolved_ip)
                        if ip.is_private or ip.is_loopback or ip.is_link_local:
                            logger.warning(
                                f"🖼️ [Proxy] Hostname {hostname} resolves to internal IP: {resolved_ip}"
                            )
                            return True
                    except ValueError:
                        continue
            except (socket.gaierror, socket.herror, OSError):
                # DNS resolution failed - block to be safe
                logger.warning(f"🖼️ [Proxy] Failed to resolve hostname: {hostname}")
                return True

        return False

    # Always block internal IPs regardless of allow_all flag
    if await _is_internal_ip(hostname):
        logger.warning(
            f"🖼️ [Proxy] Blocked internal IP/hostname: {hostname} (URL: {url})"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Internal IPs and localhost are not allowed for security reasons: {hostname}",
        )

    # Domain whitelist validation (only if allow_all is False)
    if not settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS:
        # Basic URL validation - allow common travel/image domains
        allowed_domains = [
            "dynamic-media-cdn.tripadvisor.com",
            "media-cdn.tripadvisor.com",
            "cf.bstatic.com",  # Booking.com images
            "photos.hotelbeds.com",  # HotelBeds hotel images
            "cdn.tourismcloudservice.com",  # Tourism Cloud Service CDN (no-image placeholders)
            "i.travelapi.com",  # TravelAPI/Amadeus hotel images
            "travelapi.com",  # TravelAPI base domain (for other subdomains)
            "images.unsplash.com",  # Unsplash images
            "www.planetware.com",  # PlanetWare travel images
            "hips.hearstapps.com",  # Hearst media images
            "www.studentuniverse.com",  # StudentUniverse travel images
            "dvna932ue33yp.cloudfront.net",  # CloudFront CDN
            "www.tatacapital.com",  # TataCapital travel images
            "towardsdatascience.com",  # TDS images
            "nowboarding.changiairport.com",  # Airport images
            "images.kiwi.com",  # Airline logos
        ]

        # Check if hostname matches any allowed domain (exact match or subdomain)
        domain_allowed = any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in allowed_domains
        )

        if not domain_allowed:
            logger.warning(
                f"🖼️ [Proxy] Blocked unauthorized domain (whitelist mode): {hostname} (URL: {url})"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Domain not allowed: {hostname}. Enable IMAGE_PROXY_ALLOW_ALL_DOMAINS=true to allow all external domains.",
            )
    else:
        logger.debug(
            f"🖼️ [Proxy] Allowing all external domains (allow_all mode): {hostname}"
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Get content type from original response
            content_type = response.headers.get("content-type", "image/jpeg")

            logger.debug(
                f"🖼️ [Proxy] Successfully proxied image: {len(response.content)} bytes"
            )
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "Access-Control-Allow-Origin": "*",
                },
            )

    except httpx.HTTPError as e:
        # logger.error(f"🖼️ [Proxy] Failed to fetch image {url}: {e}")
        raise HTTPException(
            status_code=502, detail="Failed to fetch external image"
        ) from e
    except Exception as e:
        logger.error(f"🖼️ [Proxy] Unexpected error proxying {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
