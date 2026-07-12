"""Unit tests for GDS ticket time limit alert service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

import pytest
from bson import ObjectId

from app.database.constants import BOOKING_EVENT_COLLECTION
from app.domains.booking_events.repository import (
    booking_event_already_alerted_for_ticket_time_limit,
    ticket_time_limit_alert_candidate_filter,
)
from app.domains.booking_events.ticket_time_limit_alert_service import (
    run_gds_ticket_time_limit_alerts,
)


class _AsyncIterator:
    """Async-iterable list for Motor cursor emulation."""

    def __init__(self, items: list) -> None:
        self._items = list(items)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._items):
            raise StopAsyncIteration
        val = self._items[self._i]
        self._i += 1
        return val


def _base_doc(
    *,
    oid: ObjectId | None = None,
    ticket_time_limit: datetime,
    warned_for: datetime | None = None,
    external_booking_reference: str = "EXT-1",
) -> dict:
    return {
        "_id": oid or ObjectId(),
        "user_id": ObjectId(),
        "voya_booking_reference": "VOYA-X",
        "external_booking_reference": external_booking_reference,
        "action": "BOOKED",
        "timestamp": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "event_type": "FLIGHT",
        "carrier_type": "GDS",
        "ticket_status": "TktInProcess",
        "ticket_time_limit": ticket_time_limit,
        "ticket_time_limit_warning_for": warned_for,
        "departure_airport_iata": "JFK",
    }


@pytest.mark.asyncio
async def test_ticket_time_limit_alert_candidate_filter_open_interval() -> None:
    now_utc = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    cutoff = now_utc + timedelta(hours=2)
    q = ticket_time_limit_alert_candidate_filter(now_utc, cutoff)
    assert q["event_type"] == "FLIGHT"
    assert q["carrier_type"] == "GDS"
    assert q["action"] == "BOOKED"
    assert q["ticket_time_limit"]["$gt"] == now_utc
    assert q["ticket_time_limit"]["$lt"] == cutoff
    assert q["ticket_status"] == {"$ne": "Ticketed"}


def test_booking_event_already_alerted_for_ticket_time_limit_true_when_matches() -> (
    None
):
    t = datetime(2026, 3, 18, 13, 0, 0, tzinfo=UTC)
    doc = {"ticket_time_limit": t, "ticket_time_limit_warning_for": t}
    assert booking_event_already_alerted_for_ticket_time_limit(doc) is True


def test_booking_event_already_alerted_for_ticket_time_limit_false_when_ttl_changed() -> (
    None
):
    t1 = datetime(2026, 3, 18, 13, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 3, 18, 14, 0, 0, tzinfo=UTC)
    doc = {"ticket_time_limit": t2, "ticket_time_limit_warning_for": t1}
    assert booking_event_already_alerted_for_ticket_time_limit(doc) is False


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_sends_slack_and_updates_dedupe_on_success(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15
    mock_notify.return_value = True

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(return_value={**doc, "_id": doc["_id"]})
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            assert name == BOOKING_EVENT_COLLECTION
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now
    )

    assert summary.candidates_found == 1
    assert summary.already_alerted_skipped == 0
    assert summary.eligible_rows_considered == 1
    assert summary.skipped_missing_external_ref == 0
    assert summary.alerts_sent == 1
    assert summary.slack_failures == 0
    mock_notify.assert_awaited_once()
    mock_slack_enabled.assert_called_once()
    mock_coll.find_one_and_update.assert_awaited_once()
    mock_coll.update_one.assert_awaited_once_with(
        {
            "_id": doc["_id"],
            "ticket_time_limit_warning_lease_id": ANY,
        },
        {
            "$set": {
                "ticket_time_limit_warning_sent_at": ANY,
                "ticket_time_limit_warning_for": ttl,
            },
            "$unset": {
                "ticket_time_limit_warning_lease_id": "",
                "ticket_time_limit_warning_lease_until": "",
            },
        },
    )


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_passes_departure_iata_from_route_legs_when_field_absent(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    """TTL Slack uses first hop from route_legs when departure_airport_iata is unset."""
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15
    mock_notify.return_value = True

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)
    del doc["departure_airport_iata"]
    doc["route_legs"] = [
        {
            "leg_index": 0,
            "departure_iata": "JFK",
            "arrival_iata": "LHR",
            "segment_count": 1,
            "segments": [
                {"departure_iata": "JFK", "arrival_iata": "LHR"},
            ],
        }
    ]

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(return_value={**doc, "_id": doc["_id"]})
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            assert name == BOOKING_EVENT_COLLECTION
            return mock_coll

    await run_gds_ticket_time_limit_alerts(_FakeDB(), dry_run=False, now_utc=fixed_now)

    mock_notify.assert_awaited_once()
    assert mock_notify.await_args.kwargs.get("departure_airport_iata") == "JFK"


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning"
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_skips_dedupe_when_already_warned_for_same_limit(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl, warned_for=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock()
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now
    )

    assert summary.candidates_found == 1
    assert summary.already_alerted_skipped == 1
    assert summary.eligible_rows_considered == 0
    assert summary.skipped_missing_external_ref == 0
    mock_notify.assert_not_called()
    mock_slack_enabled.assert_called_once()
    mock_coll.find_one_and_update.assert_not_called()
    mock_coll.update_one.assert_not_called()


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_limit_does_not_starve_valid_row_after_invalid(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    """--limit applies only after row validation; bad rows do not consume the cap."""
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15
    mock_notify.return_value = True

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    bad = _base_doc(ticket_time_limit=ttl, external_booking_reference="")
    good = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([bad, good])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(return_value={**good, "_id": good["_id"]})
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now, limit=1
    )

    assert summary.candidates_found == 2
    assert summary.skipped_missing_external_ref == 1
    assert summary.eligible_rows_considered == 1
    assert summary.alerts_sent == 1
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_limit_stops_after_cap_without_processing_further_eligible_rows(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    """When --limit N is reached, iteration stops (no extra claim/notify work)."""
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15
    mock_notify.return_value = True

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    d1 = _base_doc(ticket_time_limit=ttl)
    d2 = _base_doc(ticket_time_limit=ttl)
    d3 = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([d1, d2, d3])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(
        side_effect=[
            {**d1, "_id": d1["_id"]},
            {**d2, "_id": d2["_id"]},
        ]
    )
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now, limit=2
    )

    assert summary.candidates_found == 3
    assert summary.eligible_rows_considered == 2
    assert summary.alerts_sent == 2
    assert mock_notify.await_count == 2
    assert mock_coll.find_one_and_update.await_count == 2


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_skips_missing_external_ref_increments_counter(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl, external_booking_reference="")

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now
    )

    assert summary.eligible_rows_considered == 0
    assert summary.skipped_missing_external_ref == 1
    assert summary.alerts_sent == 0
    mock_notify.assert_not_called()


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_slack_failure_releases_lease(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15
    mock_notify.return_value = False

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(return_value={**doc, "_id": doc["_id"]})
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now
    )

    assert summary.alerts_sent == 0
    assert summary.slack_failures == 1
    mock_slack_enabled.assert_called_once()
    mock_coll.update_one.assert_awaited_once_with(
        {
            "_id": doc["_id"],
            "ticket_time_limit_warning_lease_id": ANY,
        },
        {
            "$unset": {
                "ticket_time_limit_warning_lease_id": "",
                "ticket_time_limit_warning_lease_until": "",
            }
        },
    )


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning",
    new_callable=AsyncMock,
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_claim_lost_skips_notify(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES = 15

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock(return_value=None)

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=False, now_utc=fixed_now
    )

    assert summary.alerts_sent == 0
    mock_notify.assert_not_called()
    mock_slack_enabled.assert_called_once()


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=True,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning"
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_dry_run_no_slack(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "production"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    summary = await run_gds_ticket_time_limit_alerts(
        _FakeDB(), dry_run=True, now_utc=fixed_now
    )

    assert summary.dry_run is True
    mock_notify.assert_not_called()
    mock_slack_enabled.assert_called_once()


@pytest.mark.asyncio
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.slack_webhook_notifications_enabled",
    return_value=False,
)
@patch(
    "app.domains.booking_events.ticket_time_limit_alert_service.notify_ticket_time_limit_warning"
)
@patch("app.domains.booking_events.ticket_time_limit_alert_service.settings")
async def test_run_non_production_skips_slack_and_dedupe(
    mock_settings,
    mock_notify,
    mock_slack_enabled,
) -> None:
    mock_settings.ENVIRONMENT = "staging"
    mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/X/Y/Z"
    mock_settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS = 2

    fixed_now = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    ttl = fixed_now + timedelta(hours=1)
    doc = _base_doc(ticket_time_limit=ttl)

    mock_coll = MagicMock()
    mock_cursor = Mock()
    mock_cursor.__aiter__ = lambda self: _AsyncIterator([doc])
    mock_coll.find = Mock(return_value=mock_cursor)
    mock_coll.find_one_and_update = AsyncMock()
    mock_coll.update_one = AsyncMock()

    class _FakeDB:
        def __getitem__(self, name: str):
            return mock_coll

    await run_gds_ticket_time_limit_alerts(_FakeDB(), dry_run=False, now_utc=fixed_now)

    mock_notify.assert_not_called()
    mock_slack_enabled.assert_called_once()
    mock_coll.find_one_and_update.assert_not_called()
    mock_coll.update_one.assert_not_called()
