"""PII verification domain - Email OTP for step-up verification before viewing passport.

Used when users request to view sensitive passport details in the profile Travel Details section.
"""

from .schemas import (
    PiiVerificationRequestResponse,
    PiiVerificationVerifyRequest,
    PiiVerificationVerifyResponse,
)
from .service import (
    request_pii_verification,
    verify_pii_otp,
)

__all__ = [
    "PiiVerificationRequestResponse",
    "PiiVerificationVerifyRequest",
    "PiiVerificationVerifyResponse",
    "request_pii_verification",
    "verify_pii_otp",
]
