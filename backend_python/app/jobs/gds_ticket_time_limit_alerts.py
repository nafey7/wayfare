"""Hourly job: Slack alerts for GDS flight bookings nearing ticket time limit.

Run:
    python -m app.jobs.gds_ticket_time_limit_alerts [--dry-run] [--limit N]

Intended to be triggered by AWS EventBridge Scheduler (one ECS task per run), not in-process cron.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.database.connection import (
    connect_to_mongodb,
    disconnect_from_mongodb,
    get_connection,
)
from app.domains.booking_events.ticket_time_limit_alert_service import (
    run_gds_ticket_time_limit_alerts,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GDS ticket time limit Slack alerts (booking_events query)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Log candidates only; do not send Slack or update dedupe fields",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max number of eligible bookings to process (after dedupe)",
    )
    return p.parse_args()


async def _async_main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    await connect_to_mongodb()
    try:
        conn = get_connection()
        db = conn.get_database()
        summary = await run_gds_ticket_time_limit_alerts(
            db,
            dry_run=args.dry_run,
            limit=args.limit,
        )
        logger.info(
            "GDS ticket time limit alert run complete: candidates_found=%s "
            "already_alerted_skipped=%s eligible_rows_considered=%s "
            "skipped_missing_external_ref=%s alerts_sent=%s "
            "slack_failures=%s dry_run=%s",
            summary.candidates_found,
            summary.already_alerted_skipped,
            summary.eligible_rows_considered,
            summary.skipped_missing_external_ref,
            summary.alerts_sent,
            summary.slack_failures,
            summary.dry_run,
        )
    except Exception:
        logger.exception("GDS ticket time limit alert job failed")
        return 1
    finally:
        await disconnect_from_mongodb()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
