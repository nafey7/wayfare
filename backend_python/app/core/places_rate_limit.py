"""Per-IP rate limiting for Places API endpoints.

Text Search costs ~$32/1K requests — rate limiting prevents abuse.
"""

import logging
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.security_constants import (
    PLACES_PHOTO_RATE_LIMIT_PER_MINUTE,
    PLACES_SEARCH_RATE_LIMIT_PER_MINUTE,
)

logger = logging.getLogger(__name__)

# IP -> deque of request timestamps (sliding 1-minute window)
# deque used for O(1) popleft() vs O(n) list.pop(0)
_search_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)
_photo_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)
_WINDOW_SECONDS = 60.0
_sweep_counter = 0
_SWEEP_EVERY = 500


def _get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For when behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP is the client when behind a single proxy
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _prune_old(timestamps: deque[float]) -> None:
    """Remove timestamps older than the window. O(1) per removal with deque."""
    cutoff = time.monotonic() - _WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.popleft()


def _maybe_sweep(timestamps: defaultdict[str, deque[float]]) -> None:
    """Evict stale IP entries every ~_SWEEP_EVERY calls. Prevents unbounded memory growth."""
    global _sweep_counter
    _sweep_counter += 1
    if _sweep_counter % _SWEEP_EVERY != 0:
        return
    cutoff = time.monotonic() - _WINDOW_SECONDS
    stale = [ip for ip, ts in timestamps.items() if not ts or ts[-1] < cutoff]
    for ip in stale:
        del timestamps[ip]


def check_places_search_rate_limit(request: Request) -> bool:
    """Check if request is within search/image-url rate limit. Returns False if over limit."""
    if not getattr(settings, "RATE_LIMIT_ENABLED", False):
        return True
    _maybe_sweep(_search_timestamps)
    ip = _get_client_ip(request)
    now = time.monotonic()
    _prune_old(_search_timestamps[ip])
    if len(_search_timestamps[ip]) >= PLACES_SEARCH_RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Places search rate limit exceeded for IP {ip}")
        return False
    if not _search_timestamps[ip]:
        del _search_timestamps[ip]
    _search_timestamps[ip].append(now)
    return True


def check_places_photo_rate_limit(request: Request) -> bool:
    """Check if request is within photo media rate limit. Returns False if over limit."""
    if not getattr(settings, "RATE_LIMIT_ENABLED", False):
        return True
    _maybe_sweep(_photo_timestamps)
    ip = _get_client_ip(request)
    now = time.monotonic()
    _prune_old(_photo_timestamps[ip])
    if len(_photo_timestamps[ip]) >= PLACES_PHOTO_RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Places photo rate limit exceeded for IP {ip}")
        return False
    if not _photo_timestamps[ip]:
        del _photo_timestamps[ip]
    _photo_timestamps[ip].append(now)
    return True
