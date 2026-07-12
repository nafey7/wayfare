"""Common domain enums.

Cross-domain enums that are used by multiple domains.
These are fundamental business concepts that don't belong to a specific domain.
"""

from enum import StrEnum

# ==============================================================================
# AUTHENTICATION PROVIDER ENUMS
# ==============================================================================


class AuthProvider(StrEnum):
    """Authentication provider types.

    Moved from auth domain to common as it's used across multiple domains
    (user, auth, and potentially others).
    """

    LOCAL = "local"
    GOOGLE = "google"
    BOTH = "both"  # User can log in with multiple methods


# ==============================================================================
# PERSONAL INFORMATION ENUMS
# ==============================================================================


class GenderCode(StrEnum):
    """Standard gender codes based on ISO/IEC 5218.

    International standard for representing human gender in data processing.
    """

    NOT_SPECIFIED = "0"  # Not known/specified
    MALE = "1"  # Male
    FEMALE = "2"  # Female
    NOT_APPLICABLE = "9"  # Not applicable


# ==============================================================================
# TRAVEL INDUSTRY ENUMS
# ==============================================================================


class TravelTitle(StrEnum):
    """Common passenger titles used in travel industry.

    Note: This is not an ISO standard but industry convention.
    For a more comprehensive approach, consider using locale-specific
    title handling via babel or similar.
    """

    MR = "Mr"
    MRS = "Mrs"
    MS = "Ms"
    MISS = "Miss"
    MASTER = "Master"
    DR = "Dr"
    PROF = "Prof"
    REV = "Rev"
    SIR = "Sir"
    LADY = "Lady"
    LORD = "Lord"
