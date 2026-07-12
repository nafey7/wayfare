"""MongoDB access for GDS ticket time limit alert job (booking_events)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pymongo import ReturnDocument

if TYPE_CHECKING:
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.database.constants import BOOKING_EVENT_COLLECTION


def booking_events_collection(
    db: AsyncIOMotorDatabase[Any],
) -> AsyncIOMotorCollection[Any]:
    return db[BOOKING_EVENT_COLLECTION]


def normalize_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def ticket_limits_equal(a: datetime | None, b: datetime | None) -> bool:
    if a is None or b is None:
        return False
    return normalize_utc(a) == normalize_utc(b)


def booking_event_already_alerted_for_ticket_time_limit(doc: dict[str, Any]) -> bool:
    """True when we already recorded a Slack warning for the current ticket_time_limit."""
    ttl = doc.get("ticket_time_limit")
    warned_for = doc.get("ticket_time_limit_warning_for")
    if ttl is None or not isinstance(ttl, datetime):
        return False
    if warned_for is None or not isinstance(warned_for, datetime):
        return False
    return ticket_limits_equal(warned_for, ttl)


def ticket_time_limit_alert_candidate_filter(
    now_utc: datetime, cutoff_utc: datetime
) -> dict[str, Any]:
    """Mongo filter for GDS flight BOOKED rows with ticket_time_limit in (now, cutoff)."""
    return {
        "event_type": "FLIGHT",
        "carrier_type": "GDS",
        "action": "BOOKED",
        "ticket_time_limit": {"$gt": now_utc, "$lt": cutoff_utc},
        "ticket_status": {"$ne": "Ticketed"},
        "$or": [
            {"date_tickets_issued": None},
            {"date_tickets_issued": {"$exists": False}},
        ],
    }


def ticket_time_limit_alert_claim_filter(
    oid: ObjectId,
    now_utc: datetime,
    cutoff_utc: datetime,
) -> dict[str, Any]:
    """Filter for atomic claim: in candidate window, dedupe not satisfied, lease free or expired."""
    return {
        "_id": oid,
        "event_type": "FLIGHT",
        "carrier_type": "GDS",
        "action": "BOOKED",
        "ticket_time_limit": {"$gt": now_utc, "$lt": cutoff_utc},
        "ticket_status": {"$ne": "Ticketed"},
        "$and": [
            {
                "$or": [
                    {"date_tickets_issued": None},
                    {"date_tickets_issued": {"$exists": False}},
                ]
            },
            {
                "$expr": {
                    "$or": [
                        {
                            "$eq": [
                                {"$ifNull": ["$ticket_time_limit_warning_for", None]},
                                None,
                            ]
                        },
                        {
                            "$ne": [
                                "$ticket_time_limit_warning_for",
                                "$ticket_time_limit",
                            ]
                        },
                    ]
                }
            },
            {
                "$or": [
                    {"ticket_time_limit_warning_lease_until": {"$exists": False}},
                    {"ticket_time_limit_warning_lease_until": None},
                    {"ticket_time_limit_warning_lease_until": {"$lt": now_utc}},
                ]
            },
        ],
    }


async def claim_booking_event_for_ticket_time_limit_alert(
    coll: AsyncIOMotorCollection[Any],
    *,
    oid: ObjectId,
    now_utc: datetime,
    cutoff_utc: datetime,
    lease_id: str,
    lease_until: datetime,
) -> dict[str, Any] | None:
    """Atomically set lease fields if the row is eligible; returns updated doc or None."""
    return await coll.find_one_and_update(
        ticket_time_limit_alert_claim_filter(oid, now_utc, cutoff_utc),
        {
            "$set": {
                "ticket_time_limit_warning_lease_id": lease_id,
                "ticket_time_limit_warning_lease_until": lease_until,
            }
        },
        return_document=ReturnDocument.AFTER,
    )


async def finalize_ticket_time_limit_alert_success(
    coll: AsyncIOMotorCollection[Any],
    *,
    oid: ObjectId,
    lease_id: str,
    ticket_time_limit: datetime,
    sent_at: datetime,
) -> None:
    """Persist dedupe after Slack success and clear lease.

    Not atomic with the HTTP POST: a crash after Slack returns 200 but before
    this update can allow a later job run to send a second alert for the same
    deadline until the lease blocks re-claim or dedupe fields are written.
    """
    await coll.update_one(
        {
            "_id": oid,
            "ticket_time_limit_warning_lease_id": lease_id,
        },
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


async def release_ticket_time_limit_alert_lease(
    coll: AsyncIOMotorCollection[Any],
    *,
    oid: ObjectId,
    lease_id: str,
) -> None:
    """Clear lease after Slack failure so another run can retry."""
    await coll.update_one(
        {"_id": oid, "ticket_time_limit_warning_lease_id": lease_id},
        {
            "$unset": {
                "ticket_time_limit_warning_lease_id": "",
                "ticket_time_limit_warning_lease_until": "",
            }
        },
    )
