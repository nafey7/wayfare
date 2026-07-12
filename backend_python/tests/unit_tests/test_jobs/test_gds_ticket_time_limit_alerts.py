"""Unit tests for GDS ticket time limit alert ECS job entrypoint."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.booking_events.ticket_time_limit_alert_service import (
    TicketTimeLimitAlertRunSummary,
)


@pytest.mark.asyncio
async def test_gds_ticket_time_limit_job_async_main_success() -> None:
    """Job connects, runs alert service, disconnects, returns 0."""
    from app.jobs.gds_ticket_time_limit_alerts import _async_main

    summary = TicketTimeLimitAlertRunSummary(
        candidates_found=0,
        already_alerted_skipped=0,
        eligible_rows_considered=0,
        skipped_missing_external_ref=0,
        alerts_sent=0,
        slack_failures=0,
        dry_run=False,
    )
    with (
        patch.object(sys, "argv", ["python"]),
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.connect_to_mongodb",
            new=AsyncMock(),
        ),
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.disconnect_from_mongodb",
            new=AsyncMock(),
        ),
        patch("app.jobs.gds_ticket_time_limit_alerts.get_connection") as mock_get,
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.run_gds_ticket_time_limit_alerts",
            new=AsyncMock(return_value=summary),
        ) as mock_run,
    ):
        mock_get.return_value.get_database.return_value = MagicMock()
        exit_code = await _async_main()

    assert exit_code == 0
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_gds_ticket_time_limit_job_async_main_failure_returns_one() -> None:
    """Unhandled exception in run returns exit code 1."""
    from app.jobs.gds_ticket_time_limit_alerts import _async_main

    with (
        patch.object(sys, "argv", ["python"]),
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.connect_to_mongodb",
            new=AsyncMock(),
        ),
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.disconnect_from_mongodb",
            new=AsyncMock(),
        ),
        patch("app.jobs.gds_ticket_time_limit_alerts.get_connection") as mock_get,
        patch(
            "app.jobs.gds_ticket_time_limit_alerts.run_gds_ticket_time_limit_alerts",
            new=AsyncMock(side_effect=RuntimeError("db error")),
        ),
    ):
        mock_get.return_value.get_database.return_value = MagicMock()
        exit_code = await _async_main()

    assert exit_code == 1
