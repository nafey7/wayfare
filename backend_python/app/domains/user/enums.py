"""User domain enums.

Business value enums specific to user management and profiles.
"""

from enum import Enum, StrEnum

# ==============================================================================
# USER STATUS & ROLES
# ==============================================================================


class UserStatus(int, Enum):
    """User account status values."""

    ACTIVE = 1  # User can access the system
    INACTIVE = 2  # User exists but cannot login
    DELETED = 3  # Soft deleted - user marked as deleted
    SUSPENDED = 4  # Temporarily suspended account
    BANNED = 5  # Permanently banned - violation of terms


class UserRole(StrEnum):
    """User role types."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Note: Removed unused enums - NotificationPreference, CommunicationChannel,
# PrivacyLevel, AccountVisibility
# These were planned for future user preference features but never implemented
