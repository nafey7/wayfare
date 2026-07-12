"""Payment domain enums."""

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Payment status states."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PayoutStatus(StrEnum):
    """Payout status states for supplier transfers."""

    SCHEDULED = "scheduled"
    IN_TRANSIT = "in_transit"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
