"""Per-IP rate limiting for public (guest) chat.

Guest chat is unauthenticated — rate limiting reduces abuse and cost.

**Scaling note:** Limits are tracked in an in-memory ``defaultdict`` per process. Multiple ECS
tasks each apply the limit independently (effective budget scales ~linearly with task count).
This is acceptable for single-task or low-traffic setups. Before running many parallel tasks,
replace with a shared store (e.g. Redis / ElastiCache) so limits are global per client IP.

**Concurrency:** Mutations to the global limiter state run under ``threading.Lock``. FastAPI
handles requests on a single event loop per worker process; the lock protects against rare
``run_in_threadpool`` / multi-threaded access and documents intent if the deployment model
changes.

**Operational backlog (before high traffic or many ECS tasks):**

- Monitor HTTP 429 responses and LLM cost from ``/api/public/chat/message``; spikes may indicate
  the need for a shared limiter or stricter ``PUBLIC_CHAT_MESSAGES_PER_MINUTE``.
- Implement a distributed limiter (Redis / ElastiCache + atomic counters or sliding window) so
  the effective per-IP budget does not multiply by task count.
"""

import logging
import threading
import time
from collections import OrderedDict, defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.privacy_logging import log_bucket
from app.core.security_constants import (
    PUBLIC_CHAT_MESSAGES_PER_MINUTE,
    PUBLIC_CHAT_MESSAGES_PER_SESSION,
)

logger = logging.getLogger(__name__)

# Cap unique IPs tracked so memory cannot grow without bound under distributed junk traffic.
_MAX_TRACKED_UNIQUE_IPS = 50_000
# Cap guest session entries (LRU by last message) so memory cannot grow without bound.
_MAX_TRACKED_GUEST_SESSIONS = 50_000
_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)
_timestamps_lock = threading.Lock()

# Per guest session (``X-Public-Chat-Session`` UUID): total messages allowed for that session lifetime.
_session_message_lock = threading.Lock()
_session_message_counts: OrderedDict[str, int] = OrderedDict()
_WINDOW_SECONDS = 60.0
_sweep_counter = 0
_SWEEP_EVERY = 500


def _effective_limit() -> int:
    return int(
        getattr(
            settings, "PUBLIC_CHAT_MESSAGES_PER_MINUTE", PUBLIC_CHAT_MESSAGES_PER_MINUTE
        )
    )


def _get_client_ip(request: Request) -> str:
    """Resolve client IP for rate limiting.

    When ``settings.TRUST_X_FORWARDED_FOR`` is True (e.g. behind ALB/nginx), we trust headers set
    by the edge proxy only. The leftmost ``X-Forwarded-For`` value is often client-controlled;
    the rightmost is typically appended last by the trusted proxy (e.g. ALB). ``X-Real-IP`` is
    used when present (single value from nginx and similar). If a proxy forwards multiple
    comma-separated addresses, we use the last segment (same rationale as ``X-Forwarded-For``).

    When ``TRUST_X_FORWARDED_FOR`` is False, forwarded headers are ignored so clients cannot pick
    their rate-limit bucket.
    """
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


def _prune_old(timestamps: deque[float]) -> None:
    cutoff = time.monotonic() - _WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.popleft()


def _maybe_sweep(timestamps: defaultdict[str, deque[float]]) -> None:
    global _sweep_counter
    _sweep_counter += 1
    if _sweep_counter % _SWEEP_EVERY != 0:
        return
    cutoff = time.monotonic() - _WINDOW_SECONDS
    stale = [ip for ip, ts in timestamps.items() if not ts or ts[-1] < cutoff]
    for ip in stale:
        del timestamps[ip]


def _evict_if_over_capacity(timestamps: defaultdict[str, deque[float]]) -> None:
    """Drop least-recently-active IPs until under the cap (best-effort memory bound)."""
    while len(timestamps) > _MAX_TRACKED_UNIQUE_IPS:
        oldest_ip = min(
            timestamps.keys(),
            key=lambda k: timestamps[k][-1] if timestamps[k] else 0.0,
        )
        del timestamps[oldest_ip]


def check_public_chat_rate_limit(request: Request) -> bool:
    """Return True if request is within limit, False if rate limit exceeded.

    When this returns True, a per-IP window slot is consumed immediately (before the route
    handler runs). Failed responses (e.g. HTTP 500) still count — usual tradeoff to cap
    cost and abuse from retries.
    """
    if not getattr(settings, "RATE_LIMIT_ENABLED", False):
        return True
    with _timestamps_lock:
        _maybe_sweep(_timestamps)
        ip = _get_client_ip(request)
        now = time.monotonic()
        limit = _effective_limit()
        _prune_old(_timestamps[ip])
        if len(_timestamps[ip]) >= limit:
            ip_bucket = log_bucket(ip)
            logger.debug(
                "public_chat.rate_limit_blocked ip_bucket=%s limit=%s window_s=%s in_window=%s",
                ip_bucket,
                limit,
                int(_WINDOW_SECONDS),
                len(_timestamps[ip]),
            )
            logger.warning(
                "public_chat.rate_limit_exceeded ip_bucket=%s",
                ip_bucket,
            )
            return False
        _timestamps[ip].append(now)
        _evict_if_over_capacity(_timestamps)
    return True


def _effective_session_message_limit() -> int:
    return int(
        getattr(
            settings,
            "PUBLIC_CHAT_MESSAGES_PER_SESSION",
            PUBLIC_CHAT_MESSAGES_PER_SESSION,
        )
    )


def _evict_session_counts_if_over_capacity() -> None:
    """Drop least-recently-used sessions until under the cap (best-effort memory bound)."""
    while len(_session_message_counts) > _MAX_TRACKED_GUEST_SESSIONS:
        _session_message_counts.popitem(last=False)


def check_public_chat_session_message_limit(session_id: str) -> bool:
    """Return True if this session may send another message; False if per-session cap is reached."""
    limit = _effective_session_message_limit()
    with _session_message_lock:
        n = _session_message_counts.get(session_id, 0)
        if n >= limit:
            return False
        if session_id in _session_message_counts:
            del _session_message_counts[session_id]
        _session_message_counts[session_id] = n + 1
        _evict_session_counts_if_over_capacity()
        return True


def clear_public_chat_session_message_counts_for_tests() -> None:
    """Reset per-session counters (unit tests only)."""
    with _session_message_lock:
        _session_message_counts.clear()
