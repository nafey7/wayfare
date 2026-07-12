"""Security constants for the Voya application.

Centralized security configuration values that are shared across domains.
These defaults can be overridden via environment variables in core/config.py.
"""

# ================== AUTHENTICATION & JWT ==================
# JWT token configuration - industry standard practices
JWT_ALGORITHM = "HS256"  # HMAC-SHA256 for symmetric signing
JWT_ISSUER = "voya-api"
JWT_AUDIENCE = "voya-app"

# Token expiration times - balance security vs user experience
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Short-lived for security
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Longer-lived for convenience
OTP_EXPIRE_MINUTES = 5  # Quick expiry for OTP security


# ================== PASSWORD SECURITY ==================
# Password complexity requirements - NIST guidelines
MIN_PASSWORD_LENGTH = 8  # NIST minimum recommendation
MAX_PASSWORD_LENGTH = 128  # Prevent DoS attacks
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True

# Password history to prevent reuse
PASSWORD_HISTORY_COUNT = 3  # Remember last N passwords
PASSWORD_RESET_EXPIRE_HOURS = 1  # Quick expiry for security


# ================== ACCOUNT PROTECTION ==================
# Brute force protection
MAX_LOGIN_ATTEMPTS = 5  # Lock after 5 failed attempts
ACCOUNT_LOCKOUT_MINUTES = 30  # 30 min lockout period

# Session management
MAX_SESSIONS_PER_USER = 10  # Prevent session abuse
EMAIL_VERIFICATION_EXPIRE_DAYS = 7  # Week to verify email


# ================== RATE LIMITING ==================
# API rate limits to prevent abuse
LOGIN_RATE_LIMIT_PER_MINUTE = 5  # Stricter for auth endpoints
API_RATE_LIMIT_PER_MINUTE = 60  # General API usage
PASSWORD_RESET_RATE_LIMIT_PER_HOUR = 3  # Prevent email spam

# Places API - Text Search ~$32/1K requests (abuse vector)
PLACES_SEARCH_RATE_LIMIT_PER_MINUTE = 30  # search + image-url (both hit Text Search)
PLACES_PHOTO_RATE_LIMIT_PER_MINUTE = 100  # photo media (cheaper, higher volume)

# Guest public photo proxy (GET /api/public/places/photos/.../media) — always-on limits.
# Session cap (100) is sized so a dense itinerary (many days × activities × image slots)
# loads without hitting 429 under normal scrolling; tune using staging 429 metrics.
PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE = 40
PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION = 100
# POST /api/public/places/session-token — mint new guest JWT (separate from photo GET budget)
PUBLIC_PLACES_SESSION_TOKEN_REFRESH_PER_MINUTE = 30

# Public (guest) landing chat — per-IP sliding window (see public_chat_rate_limit.py)
PUBLIC_CHAT_MESSAGES_PER_MINUTE = 7
# Per guest session (X-Public-Chat-Session UUID), lifetime cap in-process (see public_chat_rate_limit.py)
PUBLIC_CHAT_MESSAGES_PER_SESSION = 20

# User chat input (POST /api/chat/message and POST /api/public/chat/message share ChatRequest)
MAX_CHAT_MESSAGE_LENGTH = 8000


# ================== WEB SECURITY ==================
# CSRF protection
CSRF_TOKEN_LENGTH = 32  # 256-bit entropy

# Secure cookie configuration
SESSION_COOKIE_SECURE = True  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS access
SESSION_COOKIE_SAMESITE = "lax"  # CSRF protection with usability
