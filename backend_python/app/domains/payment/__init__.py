"""Payment domain - Stripe payment integration for flight bookings."""

# NOTE: Do not eagerly import webhook_service here — it imports BookingService from
# app.domains.bookings, while bookings.service imports this package (e.g. PaymentStatus),
# which would cause a circular import. PaymentWebhookService is exposed via __getattr__.

from app.domains.payment.constants import (
    FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
    PLATFORM_FEE_PERCENTAGE,
    TRANSACTION_COLLECTION,
)
from app.domains.payment.enums import PaymentStatus, PayoutStatus
from app.domains.payment.events import PaymentEventHandler
from app.domains.payment.exceptions import (
    PaymentError,
    PaymentIntentCreationError,
    PaymentValidationError,
    PayoutError,
    PayoutReleaseError,
)
from app.domains.payment.repository import PaymentRepository
from app.domains.payment.schemas import (
    BookingExpiryCheckRequest,
    BookingExpiryCheckResponse,
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PayoutReleaseRequest,
    PayoutReleaseResponse,
    TransactionResponse,
)
from app.domains.payment.service import PaymentService


def __getattr__(name: str):
    if name == "PaymentWebhookService":
        from app.domains.payment.webhook_service import PaymentWebhookService

        return PaymentWebhookService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Constants
    "FLIGHTLOGIC_STRIPE_ACCOUNT_ID",
    "PLATFORM_FEE_PERCENTAGE",
    "TRANSACTION_COLLECTION",
    # Schemas
    "BookingExpiryCheckRequest",
    "BookingExpiryCheckResponse",
    # Exceptions
    "PaymentError",
    # Events
    "PaymentEventHandler",
    "PaymentIntentCreateRequest",
    "PaymentIntentCreateResponse",
    "PaymentIntentCreationError",
    # Repository
    "PaymentRepository",
    # Service
    "PaymentService",
    # Enums
    "PaymentStatus",
    "PaymentValidationError",
    # WebhookService
    "PaymentWebhookService",
    "PayoutError",
    "PayoutReleaseError",
    "PayoutReleaseRequest",
    "PayoutReleaseResponse",
    "PayoutStatus",
    "TransactionResponse",
]
