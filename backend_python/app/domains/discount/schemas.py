"""API and service schemas for discount / voucher flows."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from app.domains.discount.constants import MAX_BATCH_SIZE
from app.shared.schemas import StrictModel


class VoucherBatchSource(StrEnum):
    """Preferred batch provenance values for reporting and filters.

    Any other short label (e.g. ``G2A_batch``, ``MySource``) is accepted as a plain
    string; use this enum when you want stable, documented channels.
    """

    G2A = "g2a"
    MANUAL = "manual"
    INTERNAL = "internal"


class VoucherApplyRequest(StrictModel):
    """POST /api/vouchers/apply body."""

    code: str = Field(min_length=1, max_length=64)
    voya_booking_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional; linkage is via booking_events.voucher_redemption_id after the row exists.",
    )
    amount_cents: int = Field(ge=0)
    booking_type: Literal["flight", "hotel"] | None = Field(
        None,
        description="Optional label for clients; apply rules are identical for flight and hotel today.",
    )
    currency: Literal["usd", "USD"] | None = None


class VoucherApplyResponse(StrictModel):
    """Successful apply: reservation created or idempotent hit."""

    redemption_id: str
    code: str
    discount_cents: int
    new_total_cents: int
    currency: Literal["usd"] = "usd"
    reservation_expires_at: datetime = Field(
        ...,
        description=(
            "When the reservation hold ends (TTL from apply). "
            "This is not the voucher's natural catalog expiry; see admin voucher doc "
            "``expires_at`` if present."
        ),
    )


class VoucherReleaseRequest(StrictModel):
    """POST /api/vouchers/release body."""

    redemption_id: str = Field(min_length=1)
    reason: str | None = Field(None, max_length=500)


class VoucherReleaseResponse(StrictModel):
    released: bool = True


class VoucherBatchCreateRequest(StrictModel):
    """POST /api/admin/discounts/batches — USD-only; no currency field."""

    count: int = Field(ge=1, le=MAX_BATCH_SIZE)
    amount_cents: int = Field(ge=1)
    source: Annotated[
        VoucherBatchSource | str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Provenance: use ``g2a``, ``manual``, or ``internal``, or any custom "
                "label (e.g. G2A_batch). Keep values stable per channel for filtering."
            ),
        ),
    ]
    prefix: str | None = Field(None, min_length=2, max_length=16)
    expires_at: datetime | None = None


class VoucherBatchCreateResponse(StrictModel):
    batch_id: str
    count: int
    total_amount_cents: int
    currency: Literal["USD"] = "USD"
    created_at: datetime
    sample_codes: list[str]


class VoucherDocResponse(StrictModel):
    """Single discount document for admin APIs.

    Codes are plaintext by design for admin review and CSV export. Keep access logging
    for admin routes tight (response bodies may include full codes).
    """

    id: str
    code: str
    amount_cents: int
    currency: str
    status: str
    source: str
    batch_id: str
    created_at: datetime
    created_by_admin_id: str | None
    expires_at: datetime | None
    reserved_by_user_id: str | None
    reservation_expires_at: datetime | None
    redeemed_at: datetime | None
    user_id: str | None


class AdminDiscountListResponse(StrictModel):
    items: list[VoucherDocResponse]
    total: int
    limit: int
    offset: int


class AdminBatchSummary(StrictModel):
    batch_id: str
    total: int
    used: int
    reserved: int
    active: int
    expired: int
    disabled: int
    source: str
    created_at: datetime | None
    total_amount_cents: int | None


class AdminBatchListResponse(StrictModel):
    batches: list[AdminBatchSummary]


class AdminBatchDetailResponse(StrictModel):
    batch_id: str
    source: str
    created_at: datetime | None
    summary: AdminBatchSummary
    codes: list[VoucherDocResponse]
    total_codes: int
    limit: int
    offset: int
