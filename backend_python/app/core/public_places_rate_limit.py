"""Always-on rate limits for guest Places photo proxy (public endpoint).

Per-IP sliding window and per-session lifetime cap. Not gated by RATE_LIMIT_ENABLED.

In-memory capacity (very high thresholds): when tracking dicts exceed limits, eviction
is **LRU-style** for all buckets — drop the entry with the **stalest recent activity**:
  - Per-IP photo and session-token **refresh** windows: evict the IP whose deque has
    the oldest *last* timestamp (``timestamps[k][-1]``).
  - Per-session photo counts: evict the ``session_id`` with the smallest ``last_seen``
    monotonic time (least recently updated).

This matches the intent of shedding cold entries under memory pressure; it is not FIFO
insertion order for sessions (``OrderedDict`` only preserves update order for LRU-ish
touch behavior inside ``record_public_places_session_photo_success``).

Periodic IP sweeps (``_maybe_sweep_ips``) share a single counter across both IP buckets
(photo vs session-token refresh), so sweep timing is approximate rather than strictly
per-bucket.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict, defaultdict, deque
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from starlette.requests import Request
from app.core.security_constants import (
    PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE,
    PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION,
    PUBLIC_PLACES_SESSION_TOKEN_REFRESH_PER_MINUTE,
)

logger = logging.getLogger(__name__)

_ip_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)
_ip_lock = threading.Lock()
_session_counts: OrderedDict[str, tuple[int, float]] = OrderedDict()
_session_lock = threading.Lock()

# Per-IP sliding window for POST /api/public/places/session-token (mint refresh)
_refresh_ip_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)
_refresh_ip_lock = threading.Lock()

_WINDOW_SECONDS = 60.0
_sweep_counter = 0
_SWEEP_EVERY = 500
_MAX_TRACKED_IPS = 50_000
_MAX_TRACKED_SESSIONS = 50_000
_SESSION_STALE_SECONDS = 86400.0 * 2


def get_trusted_request_client_ip(request: Request) -> str:
    """Same client IP resolution as public_chat_rate_limit (must match token binding)."""
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            segments = [p.strip() for p in real_ip.split(",") if p.strip()]
            if segments:
                return segments[-1]
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[-1]
    if request.client:
        return request.client.host
    return "unknown"


def _prune_ip_window(timestamps: deque[float]) -> None:
    cutoff = time.monotonic() - _WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.popleft()


def _maybe_sweep_ips(timestamps: defaultdict[str, deque[float]]) -> None:
    global _sweep_counter
    _sweep_counter += 1
    if _sweep_counter % _SWEEP_EVERY != 0:
        return
    cutoff = time.monotonic() - _WINDOW_SECONDS
    stale = [ip for ip, ts in timestamps.items() if not ts or ts[-1] < cutoff]
    for ip in stale:
        del timestamps[ip]


def _evict_ips_if_over_capacity(timestamps: defaultdict[str, deque[float]]) -> None:
    while len(timestamps) > _MAX_TRACKED_IPS:
        oldest_ip = min(
            timestamps.keys(),
            key=lambda k: timestamps[k][-1] if timestamps[k] else 0.0,
        )
        del timestamps[oldest_ip]


def _check_ip_allowed(request: Request) -> bool:
    with _ip_lock:
        _maybe_sweep_ips(_ip_timestamps)
        ip = get_trusted_request_client_ip(request)
        now = time.monotonic()
        limit = int(
            getattr(
                settings,
                "PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE",
                PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE,
            )
        )
        _prune_ip_window(_ip_timestamps[ip])
        if len(_ip_timestamps[ip]) >= limit:
            logger.warning(
                "public_places rate limit exceeded (ip) ip_bucket=%s", ip[:16]
            )
            return False
        _ip_timestamps[ip].append(now)
        _evict_ips_if_over_capacity(_ip_timestamps)
    return True


def _effective_session_cap() -> int:
    return int(
        getattr(
            settings,
            "PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION",
            PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION,
        )
    )


def _sweep_stale_sessions() -> None:
    now = time.monotonic()
    stale_ids = [
        sid
        for sid, (_, last_seen) in _session_counts.items()
        if now - last_seen > _SESSION_STALE_SECONDS
    ]
    for sid in stale_ids:
        del _session_counts[sid]


def _evict_sessions_if_over_capacity() -> None:
    """Evict the least-recently-seen session (by last_seen), aligned with IP bucket eviction."""
    while len(_session_counts) > _MAX_TRACKED_SESSIONS:
        oldest_sid = min(_session_counts.keys(), key=lambda k: _session_counts[k][1])
        del _session_counts[oldest_sid]


def check_public_places_session_quota(session_id: str) -> bool:
    """Return True if session is under the lifetime photo cap (does not increment)."""
    cap = _effective_session_cap()
    with _session_lock:
        _sweep_stale_sessions()
        entry = _session_counts.get(session_id)
        count = entry[0] if entry else 0
        if count >= cap:
            logger.warning(
                "public_places session photo cap reached session_prefix=%s",
                session_id[:8],
            )
            return False
        return True


def record_public_places_session_photo_success(session_id: str) -> None:
    """Increment per-session photo count after a successful image response."""
    now = time.monotonic()
    with _session_lock:
        count, _ = _session_counts.get(session_id, (0, now))
        if session_id in _session_counts:
            del _session_counts[session_id]
        _session_counts[session_id] = (count + 1, now)
        _evict_sessions_if_over_capacity()


def _evict_refresh_ips_if_over_capacity(
    timestamps: defaultdict[str, deque[float]],
) -> None:
    while len(timestamps) > _MAX_TRACKED_IPS:
        oldest_ip = min(
            timestamps.keys(),
            key=lambda k: timestamps[k][-1] if timestamps[k] else 0.0,
        )
        del timestamps[oldest_ip]


def check_public_places_session_token_refresh_rate_limit(request: Request) -> bool:
    """Sliding-window per-IP limit for minting a new guest Places session JWT."""
    with _refresh_ip_lock:
        _maybe_sweep_ips(_refresh_ip_timestamps)
        ip = get_trusted_request_client_ip(request)
        now = time.monotonic()
        limit = int(
            getattr(
                settings,
                "PUBLIC_PLACES_SESSION_TOKEN_REFRESH_PER_MINUTE",
                PUBLIC_PLACES_SESSION_TOKEN_REFRESH_PER_MINUTE,
            )
        )
        _prune_ip_window(_refresh_ip_timestamps[ip])
        if len(_refresh_ip_timestamps[ip]) >= limit:
            logger.warning(
                "public_places session-token refresh rate limit exceeded ip_bucket=%s",
                ip[:16],
            )
            return False
        _refresh_ip_timestamps[ip].append(now)
        _evict_refresh_ips_if_over_capacity(_refresh_ip_timestamps)
    return True


def check_public_places_rate_limit(request: Request, session_id: str) -> bool:
    """Return False if per-session quota or IP window blocks the request.

    Session quota is checked first so a capped guest does not consume IP slots.
    """
    if not check_public_places_session_quota(session_id):
        return False
    return _check_ip_allowed(request)


def clear_public_places_rate_limit_state_for_tests() -> None:
    """Reset in-memory state (unit tests only)."""
    with _ip_lock:
        _ip_timestamps.clear()
    with _refresh_ip_lock:
        _refresh_ip_timestamps.clear()
    with _session_lock:
        _session_counts.clear()
