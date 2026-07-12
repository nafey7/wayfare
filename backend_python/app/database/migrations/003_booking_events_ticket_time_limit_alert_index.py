"""Compound index for GDS ticket time limit hourly alert query on booking_events.

Idempotent: create_index with a fixed name is safe to run multiple times.
"""

import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "gds_ticket_time_limit_alert_lookup"


async def up(db):
    """Create index supporting FLIGHT + GDS + BOOKED + ticket_time_limit window scans."""
    coll = db["booking_events"]
    await coll.create_index(
        [
            ("event_type", 1),
            ("carrier_type", 1),
            ("action", 1),
            ("ticket_time_limit", 1),
        ],
        name=INDEX_NAME,
    )
    logger.info("Created index %s on booking_events", INDEX_NAME)


async def down(db):
    """Drop the alert lookup index."""
    coll = db["booking_events"]
    await coll.drop_index(INDEX_NAME)
    logger.info("Dropped index %s on booking_events", INDEX_NAME)
