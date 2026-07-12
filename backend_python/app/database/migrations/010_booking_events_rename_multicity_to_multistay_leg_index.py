"""Rename multicity_leg_index -> multistay_leg_index on booking_events documents.

Resolves the field-name asymmetry between HotelBookingRequest (multistay_leg_index)
and the persisted booking event (previously multicity_leg_index). Both flight and hotel
booking events now use the same name.

Idempotent: $rename on a field that no longer exists is a no-op; $unset on a missing
field is also a no-op.
"""

import logging

logger = logging.getLogger(__name__)


async def up(db) -> None:
    """Rename multicity_leg_index -> multistay_leg_index on all matching documents."""
    coll = db["booking_events"]
    result = await coll.update_many(
        {"multicity_leg_index": {"$exists": True}},
        {"$rename": {"multicity_leg_index": "multistay_leg_index"}},
    )
    logger.info(
        "Migration complete: renamed multicity_leg_index -> multistay_leg_index "
        "on %d booking_events documents",
        result.modified_count,
    )


async def down(db) -> None:
    """Rename multistay_leg_index -> multicity_leg_index (undo)."""
    coll = db["booking_events"]
    result = await coll.update_many(
        {"multistay_leg_index": {"$exists": True}},
        {"$rename": {"multistay_leg_index": "multicity_leg_index"}},
    )
    logger.info(
        "Migration rollback: renamed multistay_leg_index -> multicity_leg_index "
        "on %d booking_events documents",
        result.modified_count,
    )
