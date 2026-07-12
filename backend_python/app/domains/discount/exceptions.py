"""Domain errors for voucher / discount operations."""


class DiscountDomainError(Exception):
    """Base class for discount domain errors."""


class VoucherNotFoundError(DiscountDomainError):
    """No voucher matches the given identifier or code."""


class VoucherAlreadyUsedError(DiscountDomainError):
    """Voucher was already redeemed or is otherwise not available."""


class VoucherExpiredError(DiscountDomainError):
    """Voucher or reservation TTL has expired."""


class VoucherReservedByOtherError(DiscountDomainError):
    """Another user holds an active reservation on this code."""


class VoucherAmountTooLowError(DiscountDomainError):
    """Booking total is below the voucher face value."""

    def __init__(self, booking_cents: int, voucher_cents: int) -> None:
        self.booking_cents = booking_cents
        self.voucher_cents = voucher_cents
        super().__init__(
            f"Booking total ${booking_cents / 100:.2f} is below voucher value "
            f"${voucher_cents / 100:.2f}; cannot apply partial"
        )


class VoucherCurrencyInvalidError(DiscountDomainError):
    """Non-USD currency was requested (platform is USD-only)."""


class VoucherInvalidStateError(DiscountDomainError):
    """Voucher is in an unexpected state for this operation."""


class VoucherReleaseConflictError(DiscountDomainError):
    """Release cannot complete (e.g. already redeemed)."""
