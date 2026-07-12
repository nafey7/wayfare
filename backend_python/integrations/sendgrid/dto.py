"""SendGrid API Data Transfer Objects (DTOs).

These models match the SendGrid API structure.
They should only be used within the SendGrid integration.
Convert to domain models before returning to the application.
"""

from pydantic import BaseModel, EmailStr, Field


class SendGridEmailRequest(BaseModel):
    """SendGrid API email request format."""

    to_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    html_content: str = Field(..., min_length=1)
    from_email: EmailStr | None = None
    text_content: str | None = None

    class Config:
        str_strip_whitespace = True


class SendGridEmailResponse(BaseModel):
    """SendGrid API email response format."""

    success: bool
    provider: str = "sendgrid"
    status_code: int | None = None
    message_id: str | None = None
    error_message: str | None = None
