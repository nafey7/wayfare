"""PII verification schemas - request/verify OTP, PII view token."""

from pydantic import Field

from app.shared.schemas import StrictModel


class PiiVerificationRequestResponse(StrictModel):
    """Response from POST /pii-verification/request - contains challenge_id."""

    challenge_id: str = Field(..., description="Challenge ID to use in verify call")
    masked_email: str = Field(
        ..., description="Masked email where OTP was sent (e.g. j***@gmail.com)"
    )


class PiiVerificationVerifyRequest(StrictModel):
    """Request body for POST /pii-verification/verify."""

    challenge_id: str = Field(
        ..., min_length=1, description="Challenge ID from request"
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


class PiiVerificationVerifyResponse(StrictModel):
    """Response from POST /pii-verification/verify - contains short-lived PII view token."""

    pii_view_token: str = Field(
        ..., description="JWT to pass in X-PII-View-Token header"
    )
    expires_in_seconds: int = Field(..., description="Token validity in seconds")
