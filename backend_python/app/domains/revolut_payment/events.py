"""Revolut payment domain event handlers - simple and clean.

Reuses PaymentEventHandler from Stripe domain for consistency.
"""

from app.domains.payment.events import PaymentEventHandler

__all__ = ["PaymentEventHandler"]
