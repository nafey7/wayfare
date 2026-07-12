"""Authentication domain constants.

Domain-specific constants for authentication logic.
Security constants have been moved to core/security_constants.py.
"""

# ==============================================================================
# SESSION SETTINGS
# ==============================================================================

REMEMBER_ME_DURATION_DAYS = 30


# ==============================================================================
# OAUTH SETTINGS
# ==============================================================================

# OAuth security
OAUTH_STATE_LENGTH = 32
OAUTH_NONCE_LENGTH = 32

# OAuth callback paths
GOOGLE_CALLBACK_PATH = "/auth/google/callback"
FACEBOOK_CALLBACK_PATH = "/auth/facebook/callback"
