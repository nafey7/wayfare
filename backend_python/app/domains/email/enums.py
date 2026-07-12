"""Email domain enums.

Business value enums specific to email and communication operations.
"""

from enum import StrEnum

# ==============================================================================
# EMAIL TYPE & STATUS ENUMS
# ==============================================================================


class EmailType(StrEnum):
    """Email type enumeration for all system emails."""

    # Authentication & Account emails
    WELCOME = "welcome"
    PII_VERIFICATION_OTP = "pii_verification_otp"
    EMAIL_VERIFIED = "email_verified"
    PASSWORD_RESET = "password_reset"  # noqa: S105 # nosec B105 - Email template identifier
    PASSWORD_CHANGED = "password_changed"  # noqa: S105 # nosec B105 - Email template identifier
    REGISTRATION_SETUP = "registration_setup"
    PROFILE_UPDATED = "profile_updated"

    # Account status emails
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_REACTIVATED = "account_reactivated"
    ACCOUNT_BANNED = "account_banned"

    # Booking emails
    BOOKING_CONFIRMATION = "booking_confirmation"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    TICKET_ISSUED = "ticket_issued"
    BOOKING_CANCELLED = "booking_cancelled"


# Note: Removed unused enums - EmailStatus, EmailPriority, EmailTemplate,
# ContentFormat, DeliveryChannel, TrackingEvent
# These were planned for future features but never implemented


# ==============================================================================
# UI ELEMENTS - Email template UI components
# ==============================================================================


class UIButtonColor(StrEnum):
    """UI button color options used in email templates."""

    GREEN = "green"
    ORANGE = "orange"
    RED = "red"
    BLUE = "blue"
    YELLOW = "yellow"
    GRAY = "gray"
