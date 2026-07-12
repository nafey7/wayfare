"""Constants for manual discount / G2A voucher codes."""

from enum import StrEnum

DISCOUNT_COLLECTION = "discounts"
DISCOUNT_CODE_PREFIX = "VOYA"
# Also exposed to the client as `voucher_reservation_ttl_minutes` on GET /api/config.
RESERVATION_TTL_MINUTES = 15
MAX_BATCH_SIZE = 10_000
BATCH_INSERT_MAX_ATTEMPTS = 5
# Uppercase letters and digits excluding ambiguous 0, O, 1, I
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # pragma: allowlist secret
CODE_BLOCK_LEN = 4


class VoucherStatus(StrEnum):
    """Lifecycle state for a discount document."""

    ACTIVE = "active"
    RESERVED = "reserved"
    USED = "used"
    EXPIRED = "expired"
    DISABLED = "disabled"
