"""Unit tests for Slack booking error notifications."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.slack_notify import (
    notify_booking_error,
    notify_ticket_time_limit_warning,
    slack_incoming_webhook_configured,
    slack_webhook_notifications_enabled,
)


@pytest.mark.asyncio
async def test_notify_booking_error_no_op_when_not_production() -> None:
    """When ENVIRONMENT is not production, no HTTP request is made."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "development"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock()
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error(
                "Flight Booking API", "FlightLogic error: fare expired"
            )
        post_mock.assert_not_called()


@pytest.mark.asyncio
async def test_notify_booking_error_no_op_when_webhook_url_unset() -> None:
    """When SLACK_WEBHOOK_URL is not set, no HTTP request is made (production)."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = None
        post_mock = AsyncMock()
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error(
                "Flight Booking API", "FlightLogic error: fare expired"
            )
        post_mock.assert_not_called()


@pytest.mark.asyncio
async def test_notify_booking_error_no_op_when_webhook_url_empty_string() -> None:
    """When SLACK_WEBHOOK_URL is empty string, no HTTP request is made (production)."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = ""
        post_mock = AsyncMock()
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error("Hotel Booking API", "Rate no longer available")
        post_mock.assert_not_called()


@pytest.mark.asyncio
async def test_notify_booking_error_posts_json_with_text() -> None:
    """When ENVIRONMENT=production and SLACK_WEBHOOK_URL is set, POST is called."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock(return_value=MagicMock(status_code=200))
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error(
                "Flight Ticket Order API",
                "FlightLogic API error (502): Ticket issuance failed",
            )
        post_mock.assert_called_once()
        call_kw = post_mock.call_args[1]
        assert call_kw["headers"]["Content-Type"] == "application/json"
        payload = call_kw["json"]
        assert "text" in payload
        assert "Flight Ticket Order API" in payload["text"]
        assert "FlightLogic API error (502)" in payload["text"]


@pytest.mark.asyncio
async def test_notify_booking_error_includes_context_when_provided() -> None:
    """Optional context is included in the message (no PII)."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock(return_value=MagicMock(status_code=200))
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error(
                "Flight Booking API",
                "Booking creation failed: session expired",
                context={"flight_session_id": "sess_abc123"},
            )
        payload = post_mock.call_args[1]["json"]
        assert "flight_session_id=sess_abc123" in payload["text"]


@pytest.mark.asyncio
async def test_notify_booking_error_does_not_raise_on_http_error() -> None:
    """Slack notification failures are logged but do not raise."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock(side_effect=Exception("Network error"))
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await notify_booking_error("Flight Booking API", "Some error")
    # No exception raised


@pytest.mark.asyncio
async def test_notify_ticket_time_limit_warning_no_op_when_not_production() -> None:
    """Ticket time limit warning: no HTTP when not production."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "development"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock()
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            out = await notify_ticket_time_limit_warning(
                voya_booking_reference="VOYA-A",
                external_booking_reference="EXT-1",
                ticket_status="TktInProcess",
                ticket_time_limit_utc=datetime(2026, 3, 18, 14, 0, 0, tzinfo=UTC),
                minutes_remaining=45,
                departure_airport_iata="JFK",
            )
        post_mock.assert_not_called()
        assert out is False


@pytest.mark.asyncio
async def test_notify_ticket_time_limit_warning_posts_in_production() -> None:
    """Ticket time limit warning: POST with expected fields in production."""
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
        post_mock = AsyncMock(return_value=MagicMock(status_code=200))
        with patch("app.shared.slack_notify.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = post_mock
            out = await notify_ticket_time_limit_warning(
                voya_booking_reference="VOYA-A",
                external_booking_reference="EXT-1",
                ticket_status="TktInProcess",
                ticket_time_limit_utc=datetime(2026, 3, 18, 14, 0, 0, tzinfo=UTC),
                minutes_remaining=73,
                departure_airport_iata="JFK",
            )
        assert out is True
        payload = post_mock.call_args[1]["json"]
        assert "GDS Ticket Time Limit Alert" in payload["text"]
        assert "VOYA-A" in payload["text"]
        assert "EXT-1" in payload["text"]
        assert "73" in payload["text"]
        assert "JFK" in payload["text"]


def test_slack_incoming_webhook_configured_false_when_empty() -> None:
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.SLACK_WEBHOOK_URL = None
        assert slack_incoming_webhook_configured() is False
        mock_settings.SLACK_WEBHOOK_URL = ""
        assert slack_incoming_webhook_configured() is False


def test_slack_webhook_notifications_enabled_requires_prod_and_url() -> None:
    with patch("app.shared.slack_notify.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/x"
        assert slack_webhook_notifications_enabled() is True
        mock_settings.ENVIRONMENT = "staging"
        assert slack_webhook_notifications_enabled() is False
        mock_settings.ENVIRONMENT = "production"
        mock_settings.SLACK_WEBHOOK_URL = None
        assert slack_webhook_notifications_enabled() is False
