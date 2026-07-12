"""MongoDB document shape for the discounts collection."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.domains.discount.time_utils import ensure_utc_aware


class DiscountDoc:
    """In-memory representation of a discounts collection document."""

    def __init__(
        self,
        *,
        id: str | None,
        code: str,
        amount_cents: int,
        currency: str,
        status: str,
        source: str,
        batch_id: str,
        created_at: datetime,
        created_by_admin_id: str | None,
        expires_at: datetime | None,
        reserved_by_user_id: str | None,
        reservation_expires_at: datetime | None,
        redeemed_at: datetime | None,
        user_id: str | None,
    ) -> None:
        self.id = id
        self.code = code
        self.amount_cents = amount_cents
        self.currency = currency
        self.status = status
        self.source = source
        self.batch_id = batch_id
        self.created_at = created_at
        self.created_by_admin_id = created_by_admin_id
        self.expires_at = expires_at
        self.reserved_by_user_id = reserved_by_user_id
        self.reservation_expires_at = reservation_expires_at
        self.redeemed_at = redeemed_at
        self.user_id = user_id

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DiscountDoc":
        """Build from a MongoDB document dict."""
        _id = data.get("_id")
        id_str: str | None = str(_id) if _id is not None else None

        return cls(
            id=id_str,
            code=str(data["code"]),
            amount_cents=int(data["amount_cents"]),
            currency=str(data.get("currency") or "USD"),
            status=str(data["status"]),
            source=str(data.get("source") or ""),
            batch_id=str(data.get("batch_id") or ""),
            created_at=ensure_utc_aware(data["created_at"]) or data["created_at"],
            created_by_admin_id=(
                str(data["created_by_admin_id"])
                if data.get("created_by_admin_id") is not None
                else None
            ),
            expires_at=ensure_utc_aware(data.get("expires_at")),
            reserved_by_user_id=(
                str(data["reserved_by_user_id"])
                if data.get("reserved_by_user_id") is not None
                else None
            ),
            reservation_expires_at=ensure_utc_aware(data.get("reservation_expires_at")),
            redeemed_at=ensure_utc_aware(data.get("redeemed_at")),
            user_id=str(data["user_id"]) if data.get("user_id") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for MongoDB insert/update (excludes _id when None)."""
        doc: dict[str, Any] = {
            "code": self.code,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "status": self.status,
            "source": self.source,
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "created_by_admin_id": self.created_by_admin_id,
            "expires_at": self.expires_at,
            "reserved_by_user_id": self.reserved_by_user_id,
            "reservation_expires_at": self.reservation_expires_at,
            "redeemed_at": self.redeemed_at,
            "user_id": self.user_id,
        }
        if self.id is not None:
            doc["_id"] = ObjectId(self.id)
        return doc
