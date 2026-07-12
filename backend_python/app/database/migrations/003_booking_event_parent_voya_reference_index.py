"""Sparse index on parent_voya_booking_reference for multicity group queries.

Idempotent: create_index with same name is a no-op when options match.
"""

import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "idx_booking_events_parent_voya_booking_reference"


async def up(db):
    """Create sparse index on parent_voya_booking_reference."""
    coll = db["booking_events"]
    await coll.create_index(
        [("parent_voya_booking_reference", 1)],
        name=INDEX_NAME,
        sparse=True,
        background=True,
    )
    logger.info("Migration complete: index %s on booking_events", INDEX_NAME)


async def down(db):
    """Drop index created by up."""
    coll = db["booking_events"]
    await coll.drop_index(INDEX_NAME)
