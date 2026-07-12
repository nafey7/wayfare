"""Motor data access for discounts / vouchers."""

import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.database.connection import get_connection
from app.domains.discount.constants import (
    DISCOUNT_COLLECTION,
    VoucherStatus,
)
from app.domains.discount.models import DiscountDoc

logger = logging.getLogger(__name__)

# Keep in sync with app.database.migrations.006_discounts_collection_indexes
IDX_CODE_UNIQUE = "discounts_code_1_unique"
IDX_BATCH_STATUS = "discounts_batch_id_1_status_1"
IDX_STATUS_RESERVATION_EXPIRES = "discounts_status_1_reservation_expires_at_1"
IDX_USER_ID_SPARSE = "discounts_user_id_1_sparse"


class DiscountRepository:
    """MongoDB access for the discounts collection."""

    def __init__(self, collection: AsyncIOMotorCollection | None = None) -> None:
        self._collection = collection

    def collection(self) -> AsyncIOMotorCollection:
        if self._collection is not None:
            return self._collection
        return get_connection().get_database()[DISCOUNT_COLLECTION]

    async def ensure_indexes(self) -> None:
        """Ensure indexes exist (dev convenience; production uses migration 006)."""
        coll = self.collection()
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

    async def find_by_code(self, code: str) -> DiscountDoc | None:
        doc = await self.collection().find_one({"code": code})
        return DiscountDoc.from_dict(doc) if doc else None

    async def find_by_id(self, doc_id: str) -> DiscountDoc | None:
        try:
            oid = ObjectId(doc_id)
        except InvalidId:
            return None
        doc = await self.collection().find_one({"_id": oid})
        return DiscountDoc.from_dict(doc) if doc else None

    async def try_reserve_code(
        self,
        *,
        code: str,
        user_id: str,
        reservation_expires_at: datetime,
        now: datetime,
    ) -> DiscountDoc | None:
        """Transition active (or stale reserved) → reserved; returns doc after update or None.

        Booking linkage is on ``booking_events.voucher_redemption_id`` (this row's _id), not on the discount doc.
        """
        coll = self.collection()
        not_expired = [
            {"expires_at": {"$exists": False}},
            {"expires_at": None},
            {"expires_at": {"$gt": now}},
        ]
        filt: dict[str, Any] = {
            "code": code,
            "$or": [
                {"status": VoucherStatus.ACTIVE, "$or": not_expired},
                {
                    "status": VoucherStatus.RESERVED,
                    "reservation_expires_at": {"$lt": now},
                },
            ],
        }
        update = {
            "$set": {
                "status": VoucherStatus.RESERVED,
                "reserved_by_user_id": user_id,
                "reservation_expires_at": reservation_expires_at,
            }
        }
        doc = await coll.find_one_and_update(
            filt,
            update,
            return_document=ReturnDocument.AFTER,
        )
        return DiscountDoc.from_dict(doc) if doc else None

    async def mark_expired_if_needed(self, code: str, *, now: datetime) -> bool:
        """Flip active codes past expires_at to expired (best-effort).

        Returns True if a document was modified. False means no row matched (e.g. race:
        status changed between read and update).
        """
        result = await self.collection().update_one(
            {
                "code": code,
                "status": VoucherStatus.ACTIVE,
                "expires_at": {"$lte": now},
            },
            {"$set": {"status": VoucherStatus.EXPIRED}},
        )
        return bool(getattr(result, "modified_count", 0))

    async def release_reservation(
        self,
        *,
        doc_id: ObjectId,
        user_id: str,
    ) -> DiscountDoc | None:
        """reserved → active for the owning user."""
        coll = self.collection()
        doc = await coll.find_one_and_update(
            {
                "_id": doc_id,
                "status": VoucherStatus.RESERVED,
                "reserved_by_user_id": user_id,
            },
            {
                "$set": {"status": VoucherStatus.ACTIVE},
                "$unset": {
                    "reserved_by_user_id": "",
                    "reserved_for_booking_reference": "",
                    "booking_reference": "",
                    "reservation_expires_at": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        return DiscountDoc.from_dict(doc) if doc else None

    async def disable_code(self, doc_id: ObjectId) -> DiscountDoc | None:
        coll = self.collection()
        doc = await coll.find_one_and_update(
            {
                "_id": doc_id,
                "status": {"$in": [VoucherStatus.ACTIVE, VoucherStatus.RESERVED]},
            },
            {
                "$set": {"status": VoucherStatus.DISABLED},
                "$unset": {
                    "reserved_by_user_id": "",
                    "reserved_for_booking_reference": "",
                    "booking_reference": "",
                    "reservation_expires_at": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        return DiscountDoc.from_dict(doc) if doc else None

    async def redeem_reserved_by_redemption_id(
        self,
        *,
        redemption_id: str,
        now: datetime,
    ) -> DiscountDoc | None:
        """Transition RESERVED → USED by ``discounts`` document id (idempotent if already used)."""
        try:
            oid = ObjectId(redemption_id)
        except InvalidId:
            logger.info(
                "[G2A voucher] redeem_reserved_by_redemption_id: invalid ObjectId string"
            )
            return None
        coll = self.collection()
        already = await coll.find_one({"_id": oid, "status": VoucherStatus.USED})
        if already:
            logger.info(
                "[G2A voucher] redeem idempotent: discount already status=%s _id=…%s",
                VoucherStatus.USED,
                str(oid)[-6:],
            )
            return DiscountDoc.from_dict(already)

        doc = await coll.find_one_and_update(
            {"_id": oid, "status": VoucherStatus.RESERVED},
            [
                {
                    "$set": {
                        "status": VoucherStatus.USED,
                        "redeemed_at": now,
                        "user_id": "$reserved_by_user_id",
                    }
                },
                {
                    "$unset": [
                        "reserved_by_user_id",
                        "reservation_expires_at",
                        "reserved_for_booking_reference",
                        "booking_reference",
                    ]
                },
            ],
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            snap = await coll.find_one(
                {"_id": oid},
                projection={"status": 1, "reservation_expires_at": 1},
            )
            logger.warning(
                "[G2A voucher] RESERVED→USED update matched 0 rows: _id=…%s "
                "current_status=%s res_expires=%s (need RESERVED; check TTL or prior release)",
                str(oid)[-6:],
                snap.get("status") if snap else None,
                snap.get("reservation_expires_at") if snap else None,
            )
        return DiscountDoc.from_dict(doc) if doc else None

    async def expire_stale_reservations(self, *, now: datetime) -> int:
        """Clear reservations past TTL back to active. Returns modified count (best-effort)."""
        result = await self.collection().update_many(
            {
                "status": VoucherStatus.RESERVED,
                "reservation_expires_at": {"$lt": now},
            },
            {
                "$set": {"status": VoucherStatus.ACTIVE},
                "$unset": {
                    "reserved_by_user_id": "",
                    "reserved_for_booking_reference": "",
                    "booking_reference": "",
                    "reservation_expires_at": "",
                },
            },
        )
        return int(getattr(result, "modified_count", 0) or 0)

    async def insert_many_raw(self, docs: list[dict[str, Any]]) -> None:
        """Insert documents; raises BulkWriteError on duplicate key."""
        if not docs:
            return
        await self.collection().insert_many(docs, ordered=False)

    async def delete_many_by_batch(self, batch_id: str) -> int:
        result = await self.collection().delete_many({"batch_id": batch_id})
        return int(getattr(result, "deleted_count", 0) or 0)

    async def count_codes_for_batch(self, batch_id: str) -> int:
        return int(await self.collection().count_documents({"batch_id": batch_id}))

    async def list_discounts(
        self,
        *,
        status: str | None,
        batch_id: str | None,
        source: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DiscountDoc], int]:
        coll = self.collection()
        filt: dict[str, Any] = {}
        if status:
            filt["status"] = status
        if batch_id:
            filt["batch_id"] = batch_id
        if source:
            filt["source"] = source
        if search:
            filt["code"] = {"$regex": re.escape(search), "$options": "i"}

        total = await coll.count_documents(filt)
        cursor = coll.find(filt).sort("created_at", -1).skip(offset).limit(limit)
        items: list[DiscountDoc] = []
        async for raw in cursor:
            items.append(DiscountDoc.from_dict(raw))
        return items, total

    async def aggregate_batch_summaries(
        self, *, batch_id: str | None = None
    ) -> list[dict[str, Any]]:
        coll = self.collection()
        if batch_id:
            pre_match: dict[str, Any] = {"batch_id": batch_id}
        else:
            pre_match = {"batch_id": {"$exists": True, "$ne": ""}}
        pipeline: list[dict[str, Any]] = [
            {"$match": pre_match},
            {
                "$group": {
                    "_id": "$batch_id",
                    "total": {"$sum": 1},
                    "used": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", VoucherStatus.USED]}, 1, 0]
                        }
                    },
                    "reserved": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$status", VoucherStatus.RESERVED]},
                                1,
                                0,
                            ]
                        }
                    },
                    "active": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$status", VoucherStatus.ACTIVE]},
                                1,
                                0,
                            ]
                        }
                    },
                    "expired": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$status", VoucherStatus.EXPIRED]},
                                1,
                                0,
                            ]
                        }
                    },
                    "disabled": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$status", VoucherStatus.DISABLED]},
                                1,
                                0,
                            ]
                        }
                    },
                    "created_at": {"$max": "$created_at"},
                    "source": {"$first": "$source"},
                    "total_amount_cents": {"$sum": "$amount_cents"},
                }
            },
            {"$sort": {"created_at": -1}},
        ]
        raw = await coll.aggregate(pipeline).to_list(length=None)
        return cast("list[dict[str, Any]]", raw)

    async def list_codes_in_batch(
        self,
        batch_id: str,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DiscountDoc], int]:
        coll = self.collection()
        filt: dict[str, Any] = {"batch_id": batch_id}
        if status:
            filt["status"] = status
        total = await coll.count_documents(filt)
        cursor = coll.find(filt).sort("code", 1).skip(offset).limit(limit)
        items: list[DiscountDoc] = []
        async for raw in cursor:
            items.append(DiscountDoc.from_dict(raw))
        return items, total

    async def iter_codes_in_batch_csv(self, batch_id: str) -> AsyncIterator[str]:
        """Yield one code per iteration (no header)."""
        coll = self.collection()
        cursor = coll.find(
            {"batch_id": batch_id},
            projection={"code": 1, "_id": 0},
        ).sort("code", 1)
        async for doc in cursor:
            if "code" in doc:
                yield str(doc["code"])


discount_repository = DiscountRepository()
