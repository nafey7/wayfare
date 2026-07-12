"""Revolut payment domain enums.

Reuses the same enums as Stripe payment domain for consistency.
"""

from app.domains.payment.enums import PaymentStatus, PayoutStatus

__all__ = ["PaymentStatus", "PayoutStatus"]
