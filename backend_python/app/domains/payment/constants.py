"""Payment domain constants."""

from app.core.config import settings

# MongoDB collection name
TRANSACTION_COLLECTION = "transactions"

# Platform fee percentages
# Flights: 5% platform fee
FLIGHTS_PLATFORM_FEE_PERCENTAGE = 0.05
# Hotels: 10.5% commission
HOTELS_PLATFORM_FEE_PERCENTAGE = 0.105

# Default platform fee (for backward compatibility, defaults to flights)
PLATFORM_FEE_PERCENTAGE = FLIGHTS_PLATFORM_FEE_PERCENTAGE

# Voya's main Stripe account (platform account)
VOYA_STRIPE_PLATFORM_ACCOUNT_ID = "acct_1Rdy3TPD9V3ngpza"

# Voya's test Connect account (for simulating supplier in development)
VOYA_STRIPE_TEST_CONNECT_ACCOUNT_ID = "acct_1RnLvfPOhOFPCIcC"

# FlightLogic Stripe Connect account ID
# Configurable via FLIGHTLOGIC_STRIPE_ACCOUNT_ID environment variable
# Falls back to test Connect account if not configured
FLIGHTLOGIC_STRIPE_ACCOUNT_ID = (
    settings.FLIGHTLOGIC_STRIPE_ACCOUNT_ID or VOYA_STRIPE_TEST_CONNECT_ACCOUNT_ID
)
