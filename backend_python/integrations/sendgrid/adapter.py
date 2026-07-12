"""SendGrid adapter for converting between domain models and DTOs.

Maintains consistency with FlightLogic pattern using Request/Response.
Even though SendGrid is simpler, we keep the same architecture.
"""

from app.domains.email.schemas import EmailRequest, EmailResponse

from .dto import SendGridEmailRequest, SendGridEmailResponse


class SendGridAdapter:
    """Adapter for converting between domain models and SendGrid DTOs."""

    @staticmethod
    def to_sendgrid_request(email_request: EmailRequest) -> SendGridEmailRequest:
        """Convert domain EmailRequest to SendGrid DTO.

        Args:
            email_request: Business domain email request

        Returns:
            SendGrid-specific email request DTO
        """
        return SendGridEmailRequest(
            to_email=email_request.to_email,
            subject=email_request.subject,
            html_content=email_request.html_content,
            from_email=email_request.from_email,
            text_content=email_request.text_content,
        )

    @staticmethod
    def from_sendgrid_response(
        success: bool,
        status_code: int | None = None,
        message_id: str | None = None,
        error_message: str | None = None,
    ) -> EmailResponse:
        """Create domain EmailResponse from SendGrid result.

        Args:
            success: Whether email was sent successfully
            status_code: HTTP status code from SendGrid
            message_id: Message ID from SendGrid headers
            error_message: Error message if failed

        Returns:
            Business domain email response
        """
        # First create SendGrid DTO
        sendgrid_response = SendGridEmailResponse(
            success=success,
            provider="sendgrid",
            status_code=status_code,
            message_id=message_id,
            error_message=error_message,
        )

        # Then convert to domain model
        return EmailResponse(
            success=sendgrid_response.success,
            provider=sendgrid_response.provider,
            status_code=sendgrid_response.status_code,
            message_id=sendgrid_response.message_id,
            error_message=sendgrid_response.error_message,
        )
