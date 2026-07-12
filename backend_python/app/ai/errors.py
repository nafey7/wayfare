"""Centralized error classification for the chat / agent pipeline (AI-CHAT-010).

Every exception that flows through the supervisor, sub-agents, or tools should
be classified here. The classifier maps the exception to one of six
``ErrorClass`` values, picks a user-facing message tied to the actual failure
mode (not a bare "I encountered an error" placeholder), and decides whether
the call is safe to retry.

Why centralized
---------------
Production trace evidence (per AI-CHAT-010 spec): the same opaque error
returned 7 consecutive times on one user message. The user retried, retried,
retried, gave up. Voya never told them the underlying failure class —
could have been a content-policy rejection, a bad date, a quota exhaust,
or a transient network blip. The user had no signal to choose between
"try again" / "rephrase" / "give up".

This module gives every exception a stable identity + a useful user message
so that signal is finally available.

Retry policy
------------
ONLY ``transient_llm`` and ``transient_api`` are retried. Retrying the
deterministic classes (``validation`` / ``content_policy`` / ``quota``)
would compound the production-evidence case — the request would fail
identically every attempt, just burning more time and tokens.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Tenacity sleep schedule (seconds), per class. Tighter than the spec's
# 1->2->4 because user-perceived latency on the chat path matters. LLM
# rate-limits are slower to lift than API blips, so longer waits for
# transient_llm than transient_api.
_BACKOFF_SECONDS: dict[str, tuple[float, ...]] = {
    "transient_llm": (1.0, 2.0),  # 1s, then 2s — max 2 retries after the original call
    "transient_api": (0.5, 1.0),  # 0.5s, then 1s
}

# Threshold for the "consecutive errors" Slack alert + user-facing reset offer.
CONSECUTIVE_ERROR_ALERT_THRESHOLD = 3

# Hard cap on how many failing chats we track in-process. A persistently
# erroring (e.g. abandoned guest, runaway client) session never calls the
# success-path resetter, so without an upper bound the dict would grow
# unbounded over the process lifetime. ``dict`` preserves insertion order,
# so eviction is FIFO — effectively least-recently-recorded.
_MAX_TRACKED_ERROR_SESSIONS = 500

# Process-local rolling buffer of recent errors per chat_id. FIFO-evicted
# when ``_MAX_TRACKED_ERROR_SESSIONS`` is reached. Multi-instance deployments
# track independently per-instance which is fine for an alert signal (worst
# case: multiple alerts; never a missed alert).
_CONSECUTIVE_ERRORS: dict[str, tuple[int, list[str]]] = {}


def _evict_stale_error_sessions() -> None:
    """Cap ``_CONSECUTIVE_ERRORS`` size, dropping oldest entries first.

    Called from :func:`record_error_for_session` after a new entry is added.
    Eviction is FIFO via ``dict`` insertion order — a session that hasn't
    erred in a long time falls out first, which is exactly what we want.
    """
    overflow = len(_CONSECUTIVE_ERRORS) - _MAX_TRACKED_ERROR_SESSIONS
    if overflow <= 0:
        return
    # Materialise the oldest N keys before mutating the dict.
    stale = list(_CONSECUTIVE_ERRORS.keys())[:overflow]
    for chat_id in stale:
        _CONSECUTIVE_ERRORS.pop(chat_id, None)


def record_error_for_session(chat_id: str, error_class: str) -> tuple[int, list[str]]:
    """Increment the consecutive-error counter for ``chat_id``.

    Returns:
        Tuple of (new count, rolling buffer of recent classes max-3).
    """
    count, buf = _CONSECUTIVE_ERRORS.get(chat_id, (0, []))
    count += 1
    buf.append(error_class)
    # Keep the buffer the same length as the alert threshold so the Slack
    # payload always shows the exact N classes that triggered it. If anyone
    # bumps the threshold to dampen noise, the alert evidence follows.
    if len(buf) > CONSECUTIVE_ERROR_ALERT_THRESHOLD:
        buf = buf[-CONSECUTIVE_ERROR_ALERT_THRESHOLD:]
    _CONSECUTIVE_ERRORS[chat_id] = (count, buf)
    _evict_stale_error_sessions()
    return count, buf


def reset_error_count_for_session(chat_id: str) -> None:
    """Reset the consecutive-error counter for ``chat_id`` (on success)."""
    _CONSECUTIVE_ERRORS.pop(chat_id, None)


def get_error_count_for_session(chat_id: str) -> int:
    """Return the current consecutive-error count for ``chat_id``, or 0."""
    return _CONSECUTIVE_ERRORS.get(chat_id, (0, []))[0]


class ErrorClass(StrEnum):
    """Stable error categories for telemetry + user messaging.

    Use these as identifiers in Langfuse / Sentry tags; the string values
    are part of the cross-system contract.
    """

    TRANSIENT_LLM = "transient_llm"
    """OpenAI 429 / 502 / 503 / timeout. Backoff + retry."""

    TRANSIENT_API = "transient_api"
    """FlightLogic / Google API 5xx, network blip. Backoff + retry."""

    VALIDATION = "validation"
    """User-supplied data didn't pass our or the API's validation
    (bad date, ISO-2 country mismatch, malformed input). Don't retry."""

    CONTENT_POLICY = "content_policy"
    """OpenAI content policy rejection. Don't retry — same input fails
    identically. User must rephrase."""

    QUOTA = "quota"
    """OpenAI org / API key quota exhausted, or auth revoked. Don't retry —
    needs engineering intervention. Slack alert."""

    UNKNOWN = "unknown"
    """Uncategorised exception. Don't retry blindly. Sentry will pick it up;
    user gets a generic-but-honest message."""


@dataclass(frozen=True, slots=True)
class ClassifiedError:
    """Result of classifying an exception.

    Args:
        cls: The :class:`ErrorClass` value.
        user_message: What we show in the chat UI. Tied to ``cls``, not the
            raw exception. Safe to surface verbatim.
        log_detail: A short technical summary for the CloudWatch line —
            includes the original exception type + a snippet of its
            message. Never surfaced to users.
        is_retryable: True iff this class is safe to retry. Maps 1:1 with
            ``cls in {TRANSIENT_LLM, TRANSIENT_API}``.
    """

    cls: ErrorClass
    user_message: str
    log_detail: str
    is_retryable: bool


# User-facing copy. Kept in one place so a copy-writer can edit without
# touching the classifier logic. One sentence + one actionable hint each.
_USER_MESSAGES: dict[ErrorClass, str] = {
    ErrorClass.TRANSIENT_LLM: (
        "Our AI is a bit busy right now — give me a moment and try again."
    ),
    ErrorClass.TRANSIENT_API: (
        "Our travel-data partner is slow right now. Try again in a few seconds?"
    ),
    ErrorClass.VALIDATION: (
        "I couldn't read part of that request — could you rephrase it? "
        "For dates, 'June 15-20' or 'next Tuesday' work well."
    ),
    ErrorClass.CONTENT_POLICY: (
        "I couldn't process that as written. Try rephrasing — I'm here to "
        "help with travel planning."
    ),
    ErrorClass.QUOTA: (
        "We've hit our daily AI quota and engineering has been notified. "
        "Try again in a little while."
    ),
    ErrorClass.UNKNOWN: (
        "Something unexpected happened. Tell me what you were trying to do "
        "and I'll try a different approach."
    ),
}


# Map known exception class names → ErrorClass. Lookup by ``type(exc).__name__``
# (not isinstance) so we don't have to import every provider's exception type
# at module load. Falls through to ``UNKNOWN`` for anything unrecognised.
_EXCEPTION_NAME_TO_CLASS: dict[str, ErrorClass] = {
    # ----- OpenAI SDK exceptions -----
    "RateLimitError": ErrorClass.TRANSIENT_LLM,
    "APITimeoutError": ErrorClass.TRANSIENT_LLM,
    "InternalServerError": ErrorClass.TRANSIENT_LLM,
    "APIConnectionError": ErrorClass.TRANSIENT_LLM,
    "BadRequestError": ErrorClass.VALIDATION,
    "ContentPolicyViolationError": ErrorClass.CONTENT_POLICY,
    "AuthenticationError": ErrorClass.QUOTA,
    "PermissionDeniedError": ErrorClass.QUOTA,
    # ----- Google GenAI / Gemini -----
    "ResourceExhausted": ErrorClass.QUOTA,
    "DeadlineExceeded": ErrorClass.TRANSIENT_LLM,
    "ServiceUnavailable": ErrorClass.TRANSIENT_LLM,
    # ----- httpx (used by FlightLogic + Google integrations) -----
    "TimeoutException": ErrorClass.TRANSIENT_API,
    "ConnectError": ErrorClass.TRANSIENT_API,
    "ReadTimeout": ErrorClass.TRANSIENT_API,
    "WriteTimeout": ErrorClass.TRANSIENT_API,
    # ----- Voya FlightLogic / domain exceptions -----
    # Search "found no results" is validation-ish (user's params didn't match
    # available inventory) — retrying won't change anything.
    "FlightSearchError": ErrorClass.VALIDATION,
    "HotelSearchError": ErrorClass.VALIDATION,
    "FlightValidationError": ErrorClass.VALIDATION,
    "FlightBookingError": ErrorClass.VALIDATION,
    "HotelBookingError": ErrorClass.VALIDATION,
    "HotelRateError": ErrorClass.VALIDATION,
    "FlightBookingSupplierSyncError": ErrorClass.TRANSIENT_API,
    # FlightApiError is the FlightLogic HTTP error wrapper — classify by
    # status code if available (handled in classify_exception below).
    # ----- Python builtins -----
    "TimeoutError": ErrorClass.TRANSIENT_API,
    "ConnectionError": ErrorClass.TRANSIENT_API,
    "ValueError": ErrorClass.VALIDATION,
    "TypeError": ErrorClass.VALIDATION,
    # ----- Pydantic -----
    "ValidationError": ErrorClass.VALIDATION,
}


_RETRYABLE_CLASSES = frozenset({ErrorClass.TRANSIENT_LLM, ErrorClass.TRANSIENT_API})


def _flight_api_error_class(exc: BaseException) -> ErrorClass:
    """``FlightApiError`` carries a ``status_code`` attribute — classify by it.

    5xx = transient API outage (retry). 4xx = validation (caller-side; the
    request itself won't succeed on retry). 401/403 = quota / auth revoked.
    """
    status = getattr(exc, "status_code", None)
    # Belt-and-braces: a non-int status_code (odd subclass, pickle round-trip)
    # would make the chained 4xx/5xx comparisons TypeError. The classifier
    # contract promises "never raises" — bail to UNKNOWN cleanly instead.
    if not isinstance(status, int):
        return ErrorClass.UNKNOWN
    if status in (401, 403):
        return ErrorClass.QUOTA
    if 400 <= status < 500:
        return ErrorClass.VALIDATION
    if 500 <= status < 600:
        return ErrorClass.TRANSIENT_API
    return ErrorClass.UNKNOWN


def classify_exception(exc: BaseException) -> ClassifiedError:
    """Classify any exception into a :class:`ClassifiedError`.

    Resolution order:
    1. ``FlightApiError`` special case (route by ``status_code``).
    2. Exact match on ``type(exc).__name__`` against the known map.
    3. ``UNKNOWN`` fallback.

    Args:
        exc: Any exception. Never raises.

    Returns:
        A :class:`ClassifiedError` with the user message, log detail,
        and retryability flag already filled in.
    """
    name = type(exc).__name__

    if name == "FlightApiError":
        cls = _flight_api_error_class(exc)
    else:
        cls = _EXCEPTION_NAME_TO_CLASS.get(name, ErrorClass.UNKNOWN)

    # log_detail is for CloudWatch lines — short, sanitised, never to user.
    detail = f"{name}: {str(exc)[:200]}" if str(exc) else name

    return ClassifiedError(
        cls=cls,
        user_message=_USER_MESSAGES[cls],
        log_detail=detail,
        is_retryable=cls in _RETRYABLE_CLASSES,
    )


def get_backoff_schedule(cls: ErrorClass) -> tuple[float, ...]:
    """Return the per-class retry sleep schedule.

    Empty tuple means no retries (deterministic failures). Otherwise the
    tuple gives the sleep before each retry attempt in seconds.
    """
    return _BACKOFF_SECONDS.get(cls.value, ())


# ---------------------------------------------------------------------------
# Slack alert helper for the "3+ consecutive errors" pattern.
# ---------------------------------------------------------------------------


async def post_consecutive_error_alert(
    *,
    chat_id: str,
    user_id: str | None,
    consecutive_count: int,
    recent_error_classes: Sequence[str],
    latest_user_message: str | None = None,
) -> None:
    """Post a Slack alert when a chat session hits N consecutive errors.

    Fire-and-forget: any failure (no webhook configured, network error,
    Slack rate limit) is logged and swallowed — we never let alert
    plumbing break the chat path.

    Args:
        chat_id: The chat that's failing repeatedly. Required for
            ops triage.
        user_id: User identifier if known. ``None`` for guest sessions.
        consecutive_count: How many in a row. Should be >= the alert
            threshold (3 by default).
        recent_error_classes: The last 3 error_class values from state's
            ``last_error_classes`` rolling buffer.
        latest_user_message: Snippet of the message that triggered the
            most recent error, for repro context. Truncated to 200 chars.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        # No webhook configured (local dev / staging without ops setup) —
        # just log and move on. CloudWatch still has the signal.
        logger.warning(
            "consecutive_error_threshold_hit chat_id=%s count=%d classes=%s "
            "(no SLACK_WEBHOOK_URL set, skipping alert)",
            chat_id,
            consecutive_count,
            list(recent_error_classes),
        )
        return

    # Build the payload. Plain-text "text" field works for any Slack
    # webhook config; richer attachments can be added later.
    snippet = (latest_user_message or "")[:200].replace("\n", " ")
    payload = {
        "text": (
            f":rotating_light: *Voya chat — {consecutive_count} consecutive errors* "
            f"in chat `{chat_id}`\n"
            f"• user_id: `{user_id or 'guest'}`\n"
            f"• recent error classes: `{' -> '.join(recent_error_classes) or 'unknown'}`\n"
            f"• latest user message: `{snippet}`"
        ),
    }

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                logger.warning(
                    "Slack alert returned non-2xx: %d %s",
                    response.status_code,
                    response.text[:200],
                )
    except Exception:
        # Never let alerting break the request path.
        logger.warning("Failed to post Slack consecutive-error alert", exc_info=True)


__all__ = [
    "CONSECUTIVE_ERROR_ALERT_THRESHOLD",
    "ClassifiedError",
    "ErrorClass",
    "classify_exception",
    "get_backoff_schedule",
    "get_error_count_for_session",
    "post_consecutive_error_alert",
    "record_error_for_session",
    "reset_error_count_for_session",
]
