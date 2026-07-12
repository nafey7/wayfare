"""Sparse index on voucher_redemption_id for booking_events (voucher lookup by redemption id).

Speeds queries that filter by non-empty ``voucher_redemption_id`` and sort by ``timestamp``.

Idempotent: create_index with same name is a no-op when options match.
"""

import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "booking_events_voucher_redemption_id_1_sparse"


async def up(db):
    """Create sparse index on voucher_redemption_id."""
    coll = db["booking_events"]
    await coll.create_index(
        [("voucher_redemption_id", 1)],
        name=INDEX_NAME,
        sparse=True,
        background=True,
    )
    logger.info("Migration complete: index %s on booking_events", INDEX_NAME)


async def down(db):
    """Drop index created by up."""
    coll = db["booking_events"]
    await coll.drop_index(INDEX_NAME)
