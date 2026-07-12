"""Email domain business models.

These are the business-level models for email operations.
They are provider-agnostic and represent our domain logic.
"""

from pydantic import ConfigDict, EmailStr, Field

from app.shared.schemas import StrictModel


class EmailSpec(StrictModel):
    """Email specification with content and metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1)
    body_content: str = Field(
        ..., min_length=1
    )  # HTML fragment for email body (e.g. "<p>Welcome!</p>")
    button_url: str | None = Field(None)
    button_text: str = Field(..., min_length=1)
    button_color: str = Field(..., min_length=1)
    email_type_name: str = Field(..., min_length=1)


class RenderedEmail(StrictModel):
    """Rendered email ready to send."""

    spec: EmailSpec  # Original specification
    rendered_html: str = Field(
        ..., min_length=1
    )  # Full HTML email with template (<!DOCTYPE html>...)
    rendered_text: str = Field(..., min_length=1)  # Plain text version of email


class EmailRequest(StrictModel):
    """Request to send an email via provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    to_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    html_content: str = Field(..., min_length=1)
    from_email: EmailStr | None = None  # None means use provider's default
    text_content: str | None = None


class EmailResponse(StrictModel):
    """Response from email provider after sending."""

    success: bool
    provider: str
    status_code: int | None = None
    message_id: str | None = None
    error_message: str | None = None
