"""Revolut payment domain constants."""

from app.core.config import settings

# MongoDB collection name (shared with Stripe transactions)
TRANSACTION_COLLECTION = "transactions"

# Platform fee percentage (5% - same as Stripe)
PLATFORM_FEE_PERCENTAGE = 0.05

# Revolut Merchant account ID (supplier account)
# Configurable via REVOLUT_MERCHANT_ID environment variable
REVOLUT_MERCHANT_ID: str | None = getattr(settings, "REVOLUT_MERCHANT_ID", None)
