"""Mail domain constants."""

from typing import Final

# NOTE: Email configuration has been moved to app/core/config.py
# The following settings should now be set in .env:
# - SENDGRID_FROM_EMAIL (e.g., noreply@voya.travel)
# - EMAIL_FOOTER_TEXT (e.g., © 2025 Voya Travel. All rights reserved.)
# - DEV_EMAIL_RECIPIENT (e.g., dev@myvoya.ai for testing)
# - FRONTEND_URL (e.g., http://localhost:3000 or https://myvoya.ai)
# - API_TESTER_BASE_URL (e.g., http://localhost:8000/dev/api-tester.html)

# SendGrid API constants - These don't change based on environment
SUCCESS_STATUS_CODES: Final[list[int]] = [200, 201, 202]

DEV_EMAIL_RECIPIENT: Final[str] = (
    "test@example.com"  # MailHog-compatible test email for development
)

# URL configuration
FRONTEND_URL_LOCAL: Final[str] = "http://localhost:3000"
FRONTEND_URL_PRODUCTION: Final[str] = "https://www.myvoya.ai"
API_TESTER_BASE_URL: Final[str] = "http://localhost:8000/dev/api-tester.html"

# UI Colors - Hex values for UIButtonColor enum (from email.enums)
BUTTON_COLOR_HEX_VALUES: Final[dict[str, str]] = {
    "green": "#4CAF50",
    "orange": "#FF9800",
    "red": "#FF5722",
    "blue": "#007bff",
    "yellow": "#ffc107",
    "gray": "#6c757d",
}
DEFAULT_BUTTON_COLOR: Final[str] = "green"  # References UIButtonColor enum value

# Default greetings
DEFAULT_GREETING_WITH_NAME: Final[str] = "Hi {first_name},"
DEFAULT_GREETING_WITHOUT_NAME: Final[str] = "Hi there,"

# Time limits
DEFAULT_TICKET_TIME_LIMIT: Final[str] = "24 hours"
PASSWORD_RESET_LINK_EXPIRY_HOURS: Final[int] = 24
CHECKIN_WINDOW_HOURS: Final[str] = "24-48 hours"
AIRPORT_ARRIVAL_TIME_HOURS: Final[int] = 2

# Business rule limits
MAX_EMAIL_RECIPIENTS: Final[int] = 50
MAX_SUBJECT_LENGTH: Final[int] = 200
MAX_EMAIL_SIZE_MB: Final[int] = 10
MIN_TIME_BETWEEN_EMAILS_SECONDS: Final[int] = 5
MAX_EMAILS_PER_USER_PER_DAY: Final[int] = 100
