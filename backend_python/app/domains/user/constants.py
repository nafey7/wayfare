"""User domain constants.

Domain-specific constants for user management.
Security constants have been moved to core/security_constants.py.
"""

from app.domains.common.types import normalize_email

from .enums import UserRole

# Default role for new users
DEFAULT_USER_ROLE = UserRole.USER

# Email domain that automatically receives admin role on signup
MYVOYA_ADMIN_EMAIL_SUFFIX = "@myvoya.ai"


def is_myvoya_team_admin_email(email: str) -> bool:
    """True for exactly one @ and domain myvoya.ai (rejects multiple-@ strings)."""
    normalized = normalize_email(email)
    if normalized.count("@") != 1:
        return False
    return normalized.endswith(MYVOYA_ADMIN_EMAIL_SUFFIX)


# ==============================================================================
# PROFILE VALIDATION
# ==============================================================================

# Age constraints
MIN_AGE = 13  # Minimum age requirement (COPPA compliance)
MAX_AGE = 120

# Username constraints
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30
USERNAME_REGEX = r"^[a-zA-Z0-9_-]+$"

# Phone number validation
MIN_PHONE_DIGITS = 7  # Minimum digits after country code
MAX_PHONE_DIGITS = 15  # Maximum total digits including country code


# ==============================================================================
# PROFILE SETTINGS
# ==============================================================================

# Profile image
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
MAX_IMAGE_SIZE_MB = 10

# Localization
DEFAULT_TIMEZONE = "UTC"
DEFAULT_LANGUAGE = "en"  # ISO 639-1 code for English


# ==============================================================================
# USER PREFERENCES
# ==============================================================================

# Travel preferences
MAX_SAVED_DESTINATIONS = 10
MAX_TRAVEL_COMPANIONS = 20


# ==============================================================================
# SEARCH & PAGINATION
# ==============================================================================

DEFAULT_USER_SEARCH_LIMIT = 20
MAX_USER_SEARCH_LIMIT = 100
