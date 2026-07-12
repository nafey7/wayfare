"""Mail domain package.

Clean domain-driven design for email operations."""

# Constants are now in core.config - no longer imported here

# Enums
from .enums import EmailType

# Email Templates and Data
from .schemas import EmailSpec

# Service (Main API)
from .service import EmailService

# Validators
from .validators import validate_email_subject, validate_recipient_count


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService


__all__ = [
    # Service
    "EmailService",
    "EmailSpec",
    # Types
    "EmailType",
    "get_email_service",
    # Validators
    "validate_email_subject",
    "validate_recipient_count",
]
