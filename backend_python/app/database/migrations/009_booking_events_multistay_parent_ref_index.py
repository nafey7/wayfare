"""Compound index on (user_id, event_type, parent_voya_booking_reference) for booking_events.

Supports the multi-stay group lookup in GET /api/hotels/multistay-booking-context
which filters by all three fields and sorts by timestamp.

Idempotent: create_index with the same name is a no-op when options match.
"""

import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "booking_events_user_type_parent_ref_1"


async def up(db):
    """Create compound index for multi-stay group lookups."""
    coll = db["booking_events"]
    await coll.create_index(
        [
            ("user_id", 1),
            ("event_type", 1),
            ("parent_voya_booking_reference", 1),
            ("timestamp", 1),
        ],
        name=INDEX_NAME,
        sparse=True,
        background=True,
    )
    logger.info("Migration complete: index %s on booking_events", INDEX_NAME)


async def down(db):
    """Drop index created by up."""
    coll = db["booking_events"]
    await coll.drop_index(INDEX_NAME)
