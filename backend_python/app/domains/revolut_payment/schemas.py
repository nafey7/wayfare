"""Revolut payment domain schemas.

Maps Revolut Order concepts to PaymentIntent concepts for API consistency.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.shared.schemas import StrictModel

# ============================================================
# REQUEST SCHEMAS (API Input)
# ============================================================


class RevolutOrderCreateRequest(StrictModel):
    """Request to create Revolut order for flight or hotel booking.

    Maps to Stripe PaymentIntentCreateRequest for API consistency.
    For hotel: voya_booking_reference optional - backend generates nanoid format.
    For flight: voya_booking_reference required (from booking flow).
    """

    booking_amount: int = Field(..., description="Total booking amount in cents", gt=0)
    currency: str = Field(default="usd", description="Currency code (ISO 4217)")
    voya_booking_reference: str | None = Field(
        None,
        description="VOYA ref (required for flight; optional for hotel - backend generates nanoid)",
    )
    order_type: Literal["flight", "hotel"] = Field(
        default="flight",
        description="Booking type - flight uses airline metadata, hotel uses lodging",
    )
    voucher_redemption_id: str | None = Field(
        default=None,
        description="Optional discounts._id from /vouchers/apply; persisted on booking event when created",
    )
    carrier_type: Literal["GDS", "LCC"] | None = Field(
        default=None,
        description=(
            "Flight supplier channel from checkout. When LCC, skip PENDING GDS row after create-order "
            "(LCC uses pay-first + BOOKED event on /flights/book). Omit for hotel."
        ),
    )


class RevolutPayoutReleaseRequest(StrictModel):
    """Request to manually release payout to supplier (admin only)."""

    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    notes: str | None = Field(None, description="Admin notes for payout release")


# ============================================================
# RESPONSE SCHEMAS (API Output)
# ============================================================


class RevolutOrderCreateResponse(StrictModel):
    """Response with Revolut order details for frontend payment confirmation.

    Maps to Stripe PaymentIntentCreateResponse for API consistency.
    voya_booking_reference: For hotel, backend-generated nanoid; for flight, echo of request.
    """

    order_id: str = Field(..., description="Revolut order ID")
    public_order_id: str = Field(
        ..., description="Public order ID for Revolut Checkout SDK"
    )
    amount: int = Field(..., description="Total amount in cents")
    currency: str = Field(..., description="Currency code")
    platform_fee: int = Field(..., description="Platform fee (5%) in cents")
    supplier_amount: int = Field(
        ..., description="Amount to be paid out to supplier in cents"
    )
    public_key: str = Field(..., description="Revolut public key for frontend")
    voya_booking_reference: str = Field(
        ...,
        description="VOYA ref used in Revolut metadata - use for book API clientRef",
    )


class RevolutTransactionResponse(StrictModel):
    """Revolut transaction details response."""

    id: str = Field(..., description="MongoDB transaction ID")
    revolut_order_id: str = Field(..., description="Revolut order ID")
    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    amount: int = Field(..., description="Total amount in cents")
    currency: str = Field(..., description="Currency code")
    platform_fee: int = Field(..., description="Platform fee in cents")
    supplier_amount: int = Field(..., description="Supplier amount in cents")
    status: PaymentStatus = Field(..., description="Payment status")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    paid_at: datetime | None = Field(None, description="Payment completion timestamp")


class RevolutPayoutReleaseResponse(StrictModel):
    """Payout release confirmation response."""

    payout_id: str = Field(..., description="Revolut payout ID")
    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    amount: int = Field(..., description="Payout amount in cents")
    destination_account: str = Field(..., description="Destination Revolut merchant ID")
    status: PayoutStatus = Field(..., description="Payout status")
    created_at: datetime = Field(..., description="Payout creation timestamp")
    notes: str | None = Field(None, description="Admin notes")
