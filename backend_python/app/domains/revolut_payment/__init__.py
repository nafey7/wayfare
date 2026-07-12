"""Revolut payment domain - Revolut payment integration for flight bookings."""

from app.domains.revolut_payment.constants import (
    PLATFORM_FEE_PERCENTAGE,
    REVOLUT_MERCHANT_ID,
    TRANSACTION_COLLECTION,
)
from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.domains.revolut_payment.events import PaymentEventHandler
from app.domains.revolut_payment.exceptions import (
    RevolutOrderCreationError,
    RevolutPaymentError,
    RevolutPaymentValidationError,
    RevolutPayoutError,
    RevolutPayoutReleaseError,
)
from app.domains.revolut_payment.repository import RevolutPaymentRepository
from app.domains.revolut_payment.schemas import (
    RevolutOrderCreateRequest,
    RevolutOrderCreateResponse,
    RevolutPayoutReleaseRequest,
    RevolutPayoutReleaseResponse,
    RevolutTransactionResponse,
)
from app.domains.revolut_payment.service import RevolutPaymentService
from app.domains.revolut_payment.webhook_service import RevolutWebhookService

__all__ = [
    "PLATFORM_FEE_PERCENTAGE",
    "REVOLUT_MERCHANT_ID",
    # Constants
    "TRANSACTION_COLLECTION",
    # Events
    "PaymentEventHandler",
    # Enums
    "PaymentStatus",
    "PayoutStatus",
    # Schemas
    "RevolutOrderCreateRequest",
    "RevolutOrderCreateResponse",
    "RevolutOrderCreationError",
    # Exceptions
    "RevolutPaymentError",
    # Repository
    "RevolutPaymentRepository",
    # Service
    "RevolutPaymentService",
    "RevolutPaymentValidationError",
    "RevolutPayoutError",
    "RevolutPayoutReleaseError",
    "RevolutPayoutReleaseRequest",
    "RevolutPayoutReleaseResponse",
    "RevolutTransactionResponse",
    # Webhook Service
    "RevolutWebhookService",
]
