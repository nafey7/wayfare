"""Payment domain schemas."""

from datetime import datetime

from pydantic import Field

from app.domains.payment.enums import PaymentStatus, PayoutStatus
from app.shared.schemas import StrictModel

# ============================================================
# REQUEST SCHEMAS (API Input)
# ============================================================


class PaymentIntentCreateRequest(StrictModel):
    """Request to create payment intent for booking."""

    booking_amount: int = Field(..., description="Total booking amount in cents", gt=0)
    currency: str = Field(default="usd", description="Currency code (ISO 4217)")
    voya_booking_reference: str = Field(
        ..., description="VOYA booking reference (VOYA-XXXXXXXXXX)"
    )
    booking_type: str = Field(
        default="flight",
        description="Type of booking: 'flight' (5% fee) or 'hotel' (10.5% fee)",
    )


class PayoutReleaseRequest(StrictModel):
    """Request to manually release payout to supplier (admin only)."""

    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    notes: str | None = Field(None, description="Admin notes for payout release")


# ============================================================
# RESPONSE SCHEMAS (API Output)
# ============================================================


class PaymentIntentCreateResponse(StrictModel):
    """Response with Stripe client_secret for frontend payment confirmation."""

    payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    client_secret: str = Field(
        ..., description="Client secret for Stripe.js confirmation"
    )
    amount: int = Field(..., description="Total amount in cents")
    currency: str = Field(..., description="Currency code")
    platform_fee: int = Field(
        ..., description="Platform fee in cents (5% for flights, 10.5% for hotels)"
    )
    supplier_amount: int = Field(
        ..., description="Amount transferred to supplier in cents"
    )
    publishable_key: str = Field(..., description="Stripe publishable key for frontend")


class TransactionResponse(StrictModel):
    """Transaction details response."""

    id: str = Field(..., description="MongoDB transaction ID")
    stripe_payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    amount: int = Field(..., description="Total amount in cents")
    currency: str = Field(..., description="Currency code")
    platform_fee: int = Field(..., description="Platform fee in cents")
    supplier_amount: int = Field(..., description="Supplier amount in cents")
    status: PaymentStatus = Field(..., description="Payment status")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    paid_at: datetime | None = Field(None, description="Payment completion timestamp")


class PayoutReleaseResponse(StrictModel):
    """Payout release confirmation response."""

    transfer_id: str = Field(..., description="Stripe transfer ID")
    voya_booking_reference: str = Field(..., description="VOYA-XXXXXXXXXX reference")
    amount: int = Field(..., description="Payout amount in cents")
    destination_account: str = Field(..., description="Destination Stripe account ID")
    status: PayoutStatus = Field(..., description="Payout status")
    created_at: datetime = Field(..., description="Payout creation timestamp")
    notes: str | None = Field(None, description="Admin notes")


class BookingExpiryCheckRequest(StrictModel):
    """Request to check if booking has expired before payment confirmation."""

    voya_booking_reference: str = Field(
        ..., description="VOYA booking reference (VOYA-XXXXXXXXXX)"
    )


class BookingExpiryCheckResponse(StrictModel):
    """Response indicating if booking is still valid for payment."""

    is_valid: bool = Field(
        ..., description="True if booking is still valid for payment"
    )
    ticket_time_limit: datetime | None = Field(
        None, description="Ticket time limit in UTC (if applicable)"
    )
    time_remaining_seconds: int | None = Field(
        None, description="Seconds remaining until expiry (if applicable)"
    )
    message: str | None = Field(
        None, description="Error message if booking has expired"
    )
