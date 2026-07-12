"""GDS flight bookings: ticket time limit approaching — query, Slack, dedupe."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from bson import ObjectId

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.database.flight_route import departure_iata_from_route_legs_raw
from app.domains.booking_events.repository import (
    booking_event_already_alerted_for_ticket_time_limit,
    booking_events_collection,
    claim_booking_event_for_ticket_time_limit_alert,
    finalize_ticket_time_limit_alert_success,
    normalize_utc,
    release_ticket_time_limit_alert_lease,
    ticket_time_limit_alert_candidate_filter,
)
from app.shared.slack_notify import (
    notify_ticket_time_limit_warning,
    slack_incoming_webhook_configured,
    slack_webhook_notifications_enabled,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketTimeLimitAlertRunSummary:
    """Counts from a single hourly GDS ticket time limit alert run.

    ``eligible_rows_considered`` counts rows that passed validation (valid
    ``ticket_time_limit``, ``_id``, ``external_booking_reference``) and were
    subject to ``--limit`` (incremented only for those rows, so invalid rows do
    not consume the cap). It is not the number of Slack attempts.
    ``skipped_missing_external_ref`` counts rows dropped because
    ``external_booking_reference`` was missing or invalid.
    """

    candidates_found: int
    already_alerted_skipped: int
    eligible_rows_considered: int
    skipped_missing_external_ref: int
    alerts_sent: int
    slack_failures: int
    dry_run: bool


def _minutes_remaining(now_utc: datetime, ticket_time_limit: datetime) -> int:
    delta = normalize_utc(ticket_time_limit) - normalize_utc(now_utc)
    return max(0, int(delta.total_seconds() // 60))


async def run_gds_ticket_time_limit_alerts(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    now_utc: datetime | None = None,
) -> TicketTimeLimitAlertRunSummary:
    """Find GDS bookings expiring within the configured window; Slack + dedupe with lease.

    At-least-once Slack delivery: if the process dies after the webhook returns
    success but before ``finalize_ticket_time_limit_alert_success`` runs, a
    later run may post a duplicate for the same booking. A longer
    ``GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES`` reduces how often a concurrent
    run can claim the same row before finalize completes.
    """
    now_utc = datetime.now(UTC) if now_utc is None else normalize_utc(now_utc)
    window = timedelta(hours=settings.GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS)
    cutoff_utc = now_utc + window
    coll = booking_events_collection(db)
    query = ticket_time_limit_alert_candidate_filter(now_utc, cutoff_utc)

    candidates_found = 0
    already_alerted_skipped = 0
    eligible_handled = 0
    skipped_missing_external_ref = 0
    alerts_sent = 0
    slack_failures = 0

    send_slack = slack_webhook_notifications_enabled()
    if not send_slack and not dry_run:
        logger.info(
            "GDS ticket time limit job: Slack disabled (env=%s, webhook configured=%s); "
            "no messages sent, dedupe not updated",
            settings.ENVIRONMENT,
            slack_incoming_webhook_configured(),
        )

    cursor = coll.find(query)
    async for doc in cursor:
        candidates_found += 1
        if booking_event_already_alerted_for_ticket_time_limit(
            cast("dict[str, Any]", doc)
        ):
            already_alerted_skipped += 1
            continue

        ttl = doc.get("ticket_time_limit")
        if ttl is None or not isinstance(ttl, datetime):
            continue
        oid = doc.get("_id")
        if not isinstance(oid, ObjectId):
            continue

        ext_ref = doc.get("external_booking_reference")
        if not ext_ref or not isinstance(ext_ref, str):
            skipped_missing_external_ref += 1
            logger.warning(
                "Skipping booking event %s: missing external_booking_reference",
                oid,
            )
            continue

        if limit is not None and eligible_handled >= limit:
            break
        eligible_handled += 1

        voya_ref = doc.get("voya_booking_reference")
        voya_ref_s = voya_ref if isinstance(voya_ref, str) else None
        ticket_status = doc.get("ticket_status")
        ticket_status_s = ticket_status if isinstance(ticket_status, str) else None
        dep = doc.get("departure_airport_iata")
        dep_s = dep if isinstance(dep, str) and dep.strip() else None
        if dep_s is None:
            dep_s = departure_iata_from_route_legs_raw(doc.get("route_legs"))
        mins = _minutes_remaining(now_utc, ttl)

        if dry_run:
            logger.info(
                "DRY-RUN would alert: voya=%s external=%s minutes=%s",
                voya_ref_s,
                ext_ref,
                mins,
            )
            continue

        if not send_slack:
            continue

        lease_delta = timedelta(
            minutes=settings.GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES
        )
        lease_id = uuid.uuid4().hex
        lease_until = now_utc + lease_delta
        claimed = await claim_booking_event_for_ticket_time_limit_alert(
            coll,
            oid=oid,
            now_utc=now_utc,
            cutoff_utc=cutoff_utc,
            lease_id=lease_id,
            lease_until=lease_until,
        )
        if claimed is None:
            logger.debug(
                "Ticket time limit alert skipped (lease held or no longer eligible): %s",
                oid,
            )
            continue

        ok = await notify_ticket_time_limit_warning(
            voya_booking_reference=voya_ref_s,
            external_booking_reference=ext_ref,
            ticket_status=ticket_status_s,
            ticket_time_limit_utc=ttl,
            minutes_remaining=mins,
            departure_airport_iata=dep_s,
        )
        if ok:
            alerts_sent += 1
            sent_at = datetime.now(UTC)
            await finalize_ticket_time_limit_alert_success(
                coll,
                oid=oid,
                lease_id=lease_id,
                ticket_time_limit=ttl,
                sent_at=sent_at,
            )
        else:
            slack_failures += 1
            logger.warning(
                "Slack ticket time limit alert failed for external_ref=%s",
                ext_ref,
            )
            await release_ticket_time_limit_alert_lease(
                coll,
                oid=oid,
                lease_id=lease_id,
            )

    return TicketTimeLimitAlertRunSummary(
        candidates_found=candidates_found,
        already_alerted_skipped=already_alerted_skipped,
        eligible_rows_considered=eligible_handled,
        skipped_missing_external_ref=skipped_missing_external_ref,
        alerts_sent=alerts_sent,
        slack_failures=slack_failures,
        dry_run=dry_run,
    )
