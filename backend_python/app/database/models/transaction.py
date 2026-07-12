"""Transaction model for MongoDB - Payment transaction logging."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.database.types import PyObjectId
from app.domains.payment.constants import FLIGHTLOGIC_STRIPE_ACCOUNT_ID
from app.domains.payment.enums import PaymentStatus, PayoutStatus

# Payment provider type
PaymentProvider = Literal["stripe", "revolut"]


class TransactionModel(BaseModel):
    """MongoDB transaction log for flight booking payments.

    This model stores all payment transactions including Stripe payment intent IDs,
    Revolut order IDs, amounts, platform fees, and payout information.
    Supports both Stripe and Revolut payment providers.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # MongoDB _id field
    id: PyObjectId | None = Field(default=None, alias="_id")

    # Payment provider
    payment_provider: PaymentProvider = Field(
        default="stripe",
        description="Payment provider: 'stripe' or 'revolut'",
    )

    # Stripe identifiers (nullable for Revolut transactions)
    stripe_payment_intent_id: str | None = Field(
        None,
        description="Stripe payment intent ID (pi_xxx) - nullable for backward compatibility and Revolut transactions",
    )
    stripe_charge_id: str | None = Field(
        None, description="Stripe charge ID (from webhook)"
    )
    stripe_transfer_id: str | None = Field(
        None, description="Stripe transfer ID for supplier payout"
    )
    refund_id: str | None = Field(None, description="Stripe refund ID if refunded")

    # Revolut identifiers (nullable for Stripe transactions)
    revolut_order_id: str | None = Field(
        None, description="Revolut order ID - nullable for Stripe transactions"
    )
    revolut_payout_id: str | None = Field(
        None,
        description="Revolut payout ID for supplier payout - nullable for Stripe transactions",
    )

    # Booking reference
    voya_booking_reference: str = Field(
        ..., description="VOYA-XXXXXXXXXX booking reference"
    )

    # User
    user_id: PyObjectId | None = Field(None, description="User who made payment")

    # Amounts (in cents)
    amount: int = Field(..., description="Total amount charged in cents")
    currency: str = Field(default="usd", description="Currency code (ISO 4217)")
    platform_fee: int = Field(..., description="Platform fee (5%) in cents")
    supplier_amount: int = Field(
        ..., description="Amount transferred to supplier in cents"
    )

    # Stripe Connect
    destination_account_id: str = Field(
        default=FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
        description="FlightLogic Stripe Connect account ID",
    )

    # Status tracking
    status: PaymentStatus = Field(..., description="Payment status")
    payout_status: PayoutStatus | None = Field(
        None, description="Payout status to supplier"
    )
    booking_created: bool = Field(
        default=False,
        description="Whether this payment has been used to create a booking",
    )

    # Timestamps
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    paid_at: datetime | None = Field(None, description="Payment completion timestamp")
    refunded_at: datetime | None = Field(None, description="Refund timestamp")
    payout_released_at: datetime | None = Field(
        None, description="Payout release timestamp"
    )

    # Admin tracking for manual payouts
    payout_released_by: str | None = Field(
        None, description="Admin user ID who released payout"
    )
    payout_notes: str | None = Field(None, description="Admin notes for payout")
