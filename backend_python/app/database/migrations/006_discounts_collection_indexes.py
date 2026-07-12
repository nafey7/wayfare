"""Indexes for the ``discounts`` collection (G2A voucher / manual discount codes).

Idempotent: ``create_index`` with explicit names is safe to repeat.

Keep index **names** and key specs in sync with
``app.domains.discount.repository.DiscountRepository.ensure_indexes`` when changed.
"""

import logging

from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

DISCOUNTS_COLLECTION = "discounts"
IDX_CODE_UNIQUE = "discounts_code_1_unique"
IDX_BATCH_STATUS = "discounts_batch_id_1_status_1"
IDX_STATUS_RESERVATION_EXPIRES = "discounts_status_1_reservation_expires_at_1"
IDX_USER_ID_SPARSE = "discounts_user_id_1_sparse"


async def up(db):
    """Create indexes on discounts."""
    coll = db[DISCOUNTS_COLLECTION]

    await coll.create_index([("code", 1)], name=IDX_CODE_UNIQUE, unique=True)
    await coll.create_index(
        [("batch_id", 1), ("status", 1)],
        name=IDX_BATCH_STATUS,
    )
    await coll.create_index(
        [("status", 1), ("reservation_expires_at", 1)],
        name=IDX_STATUS_RESERVATION_EXPIRES,
    )
    await coll.create_index(
        [("user_id", 1)],
        name=IDX_USER_ID_SPARSE,
        sparse=True,
    )

    logger.info("Migration complete: discounts collection indexes")


async def down(db):
    """Drop discounts indexes (does not drop data)."""
    coll = db[DISCOUNTS_COLLECTION]
    for name in (
        IDX_USER_ID_SPARSE,
        IDX_STATUS_RESERVATION_EXPIRES,
        IDX_BATCH_STATUS,
        IDX_CODE_UNIQUE,
    ):
        try:
            await coll.drop_index(name)
        except OperationFailure as exc:
            if (
                getattr(exc, "code", None) != 27
                and "index not found" not in str(exc).lower()
            ):
                raise
            logger.debug("drop_index skipped for %s: %s", name, exc)
