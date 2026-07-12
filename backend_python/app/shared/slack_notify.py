"""Slack notifications for booking and ticket API errors.

Sends structured messages to a Slack channel via Incoming Webhook when
flight booking, issue_ticket, or hotel booking APIs fail. Error messages
from client APIs (e.g. FlightLogic) are included so the team can react quickly.

This module is the canonical utility for all booking/ticket/API-related Slack
notifications. For new cases: import notify_booking_error and call with
api_name, error_message, and optional context (no PII; use IDs like UniqueID).

Operational warnings (e.g. GDS ticket time limit) use notify_ticket_time_limit_warning.

Requires SLACK_WEBHOOK_URL and ENVIRONMENT=production. In non-production, all calls are no-ops.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Timeout for webhook POST (seconds)
_WEBHOOK_TIMEOUT = 10.0


def slack_incoming_webhook_configured() -> bool:
    """True when SLACK_WEBHOOK_URL is a non-empty string."""
    url = settings.SLACK_WEBHOOK_URL
    return bool(url and str(url).strip())


def slack_webhook_notifications_enabled() -> bool:
    """True when production and a Slack webhook URL is configured (same gate for all Slack webhooks)."""
    return settings.ENVIRONMENT == "production" and slack_incoming_webhook_configured()


def _build_message(
    api_name: str,
    error_message: str,
    context: dict[str, Any] | None,
    *,
    title: str = "Booking / Ticket API Error",
) -> str:
    """Build a single Slack text block (no PII)."""
    lines = [
        f":warning: *{title}*",
        f"*API*: `{api_name}`",
        f"*Error*: {error_message}",
    ]
    if context:
        safe = {k: str(v) for k, v in context.items() if v is not None}
        if safe:
            lines.append("*Context*: " + ", ".join(f"{k}={v}" for k, v in safe.items()))
    return "\n".join(lines)


async def notify_booking_error(
    api_name: str,
    error_message: str,
    context: dict[str, Any] | None = None,
    *,
    title: str = "Booking / Ticket API Error",
) -> None:
    """Send a booking/ticket API error to Slack via webhook.

    Uses Slack Incoming Webhook format: POST JSON with "text" field.
    Only sends when ENVIRONMENT=production and SLACK_WEBHOOK_URL is set; otherwise no-op.

    Args:
        api_name: Display name for the failing API (e.g. "Flight Booking API", "Flight Ticket Order API", "Hotel Booking API").
        error_message: Error message from the backend/client API (e.g. FlightLogic).
        context: Optional safe key-value context for tracing (e.g. flight_session_id, UniqueID, sessionId; no PII).
        title: Optional custom heading (default: "Booking / Ticket API Error").
    """
    if not slack_webhook_notifications_enabled():
        logger.debug(
            "Slack notification skipped: not production or SLACK_WEBHOOK_URL unset "
            "(api=%s, env=%s)",
            api_name,
            settings.ENVIRONMENT,
        )
        return
    url = settings.SLACK_WEBHOOK_URL
    text = _build_message(api_name, error_message, context, title=title)
    payload: dict[str, str] = {"text": text}
    logger.debug("Sending Slack notification for api=%s", api_name)
    try:
        async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                logger.debug("Slack notification sent for api=%s", api_name)
            else:
                logger.warning(
                    "Slack webhook returned %s: %s",
                    resp.status_code,
                    resp.text[:200] if resp.text else "",
                )
    except Exception as e:
        logger.warning("Failed to send Slack notification: %s", e, exc_info=False)


def _format_ticket_time_limit_utc(dt: datetime) -> str:
    """Format a datetime as ISO-8601 UTC with Z suffix (no PII)."""
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_ticket_time_limit_warning_message(
    *,
    voya_booking_reference: str | None,
    external_booking_reference: str,
    ticket_status: str | None,
    ticket_time_limit_utc: datetime,
    minutes_remaining: int,
    departure_airport_iata: str | None,
) -> str:
    lines = [
        ":warning: *GDS Ticket Time Limit Alert*",
        f"*Booking*: `{voya_booking_reference or 'N/A'}`",
        f"*External Ref*: `{external_booking_reference}`",
        f"*Ticket Status*: `{ticket_status or 'N/A'}`",
        f"*Ticket Time Limit (UTC)*: `{_format_ticket_time_limit_utc(ticket_time_limit_utc)}`",
        f"*Minutes Remaining*: `{minutes_remaining}`",
        f"*Departure Airport*: `{departure_airport_iata or 'N/A'}`",
    ]
    return "\n".join(lines)


async def notify_ticket_time_limit_warning(
    *,
    voya_booking_reference: str | None,
    external_booking_reference: str,
    ticket_status: str | None,
    ticket_time_limit_utc: datetime,
    minutes_remaining: int,
    departure_airport_iata: str | None,
) -> bool:
    """Send a GDS ticket time limit warning to Slack via webhook.

    Uses the same production-only and webhook guards as notify_booking_error.

    Returns:
        True if a message was POSTed and the response status was 200.
        False if skipped (non-production / no webhook) or on failure.
    """
    if not slack_webhook_notifications_enabled():
        logger.debug(
            "Slack ticket time limit alert skipped: not production or "
            "SLACK_WEBHOOK_URL unset (env=%s)",
            settings.ENVIRONMENT,
        )
        return False
    url = settings.SLACK_WEBHOOK_URL
    text = _build_ticket_time_limit_warning_message(
        voya_booking_reference=voya_booking_reference,
        external_booking_reference=external_booking_reference,
        ticket_status=ticket_status,
        ticket_time_limit_utc=ticket_time_limit_utc,
        minutes_remaining=minutes_remaining,
        departure_airport_iata=departure_airport_iata,
    )
    payload: dict[str, str] = {"text": text}
    try:
        async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                logger.debug(
                    "Slack ticket time limit alert sent (external_ref=%s)",
                    external_booking_reference,
                )
                return True
            logger.warning(
                "Slack ticket time limit webhook returned %s: %s",
                resp.status_code,
                resp.text[:200] if resp.text else "",
            )
            return False
    except Exception as e:
        logger.warning(
            "Failed to send Slack ticket time limit alert: %s", e, exc_info=False
        )
        return False
