"""Unit tests for booking_events ticket time limit alert repository helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from pymongo import ReturnDocument

from app.domains.booking_events.repository import (
    claim_booking_event_for_ticket_time_limit_alert,
    finalize_ticket_time_limit_alert_success,
    release_ticket_time_limit_alert_lease,
    ticket_time_limit_alert_claim_filter,
)


@pytest.mark.asyncio
async def test_claim_booking_event_for_ticket_time_limit_alert_delegates_to_find_one_and_update() -> (
    None
):
    oid = ObjectId()
    now_utc = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    cutoff = now_utc + timedelta(hours=2)
    lease_id = "lease-abc"
    lease_until = now_utc + timedelta(minutes=15)
    updated = {"_id": oid, "ticket_time_limit_warning_lease_id": lease_id}

    coll = AsyncMock()
    coll.find_one_and_update = AsyncMock(return_value=updated)

    out = await claim_booking_event_for_ticket_time_limit_alert(
        coll,
        oid=oid,
        now_utc=now_utc,
        cutoff_utc=cutoff,
        lease_id=lease_id,
        lease_until=lease_until,
    )

    assert out == updated
    coll.find_one_and_update.assert_awaited_once()
    call = coll.find_one_and_update.await_args
    assert call[0][0] == ticket_time_limit_alert_claim_filter(oid, now_utc, cutoff)
    assert call[0][1] == {
        "$set": {
            "ticket_time_limit_warning_lease_id": lease_id,
            "ticket_time_limit_warning_lease_until": lease_until,
        }
    }
    assert call[1]["return_document"] == ReturnDocument.AFTER


@pytest.mark.asyncio
async def test_finalize_ticket_time_limit_alert_success_update_shape() -> None:
    oid = ObjectId()
    lease_id = "lease-xyz"
    ticket_time_limit = datetime(2026, 3, 18, 14, 0, 0, tzinfo=UTC)
    sent_at = datetime(2026, 3, 18, 12, 30, 0, tzinfo=UTC)

    coll = AsyncMock()
    await finalize_ticket_time_limit_alert_success(
        coll,
        oid=oid,
        lease_id=lease_id,
        ticket_time_limit=ticket_time_limit,
        sent_at=sent_at,
    )

    coll.update_one.assert_awaited_once_with(
        {"_id": oid, "ticket_time_limit_warning_lease_id": lease_id},
        {
            "$set": {
                "ticket_time_limit_warning_sent_at": sent_at,
                "ticket_time_limit_warning_for": ticket_time_limit,
            },
            "$unset": {
                "ticket_time_limit_warning_lease_id": "",
                "ticket_time_limit_warning_lease_until": "",
            },
        },
    )


@pytest.mark.asyncio
async def test_release_ticket_time_limit_alert_lease_update_shape() -> None:
    oid = ObjectId()
    lease_id = "lease-rel"

    coll = AsyncMock()
    await release_ticket_time_limit_alert_lease(coll, oid=oid, lease_id=lease_id)

    coll.update_one.assert_awaited_once_with(
        {"_id": oid, "ticket_time_limit_warning_lease_id": lease_id},
        {
            "$unset": {
                "ticket_time_limit_warning_lease_id": "",
                "ticket_time_limit_warning_lease_until": "",
            }
        },
    )


def test_ticket_time_limit_alert_claim_filter_includes_id_and_window() -> None:
    oid = ObjectId()
    now_utc = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
    cutoff = now_utc + timedelta(hours=2)
    flt = ticket_time_limit_alert_claim_filter(oid, now_utc, cutoff)
    assert flt["_id"] == oid
    assert flt["ticket_time_limit"]["$gt"] == now_utc
    assert flt["ticket_time_limit"]["$lt"] == cutoff
