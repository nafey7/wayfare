"""SendGrid email client implementation."""

import base64
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from app.domains.common import EmailStr
from app.domains.email.schemas import EmailRequest, EmailResponse

from .adapter import SendGridAdapter

logger = logging.getLogger(__name__)


class SendGridClient:
    """SendGrid email client."""

    def __init__(self, api_key: str, from_email: EmailStr | None = None) -> None:
        """Initialize SendGrid client with API key and optional sender.

        Args:
            api_key: SendGrid API key
            from_email: Default sender email address (optional)
        """
        if not api_key:
            raise ValueError("SendGrid API key is required")

        self._client = SendGridAPIClient(api_key)
        self._from_email = from_email

    def set_default_sender(self, from_email: EmailStr) -> None:
        """Set default sender email address.

        Args:
            from_email: Default sender email address
        """
        self._from_email = from_email

    def send_email(
        self, email_request: EmailRequest, attachments: list | None = None
    ) -> EmailResponse:
        """Send email via SendGrid with optional attachments.

        Args:
            email_request: Email request to send (domain model)
            attachments: Optional list of EmailAttachment objects (PDFs, etc.)

        Returns:
            EmailResponse with result (domain model)
        """
        logger.info(f"📧 [SendGrid] Starting send_email for: {email_request.to_email}")
        logger.info(f"📧 [SendGrid] Subject: {email_request.subject}")
        logger.info(f"📧 [SendGrid] API key configured: {bool(self._client.api_key)}")
        logger.info(f"📧 [SendGrid] Default from_email: {self._from_email}")
        if attachments:
            logger.info(f"📧 [SendGrid] Attachments: {len(attachments)} file(s)")

        try:
            # Convert domain model to SendGrid DTO
            logger.info("📧 [SendGrid] Converting to SendGrid request...")
            sendgrid_request = SendGridAdapter.to_sendgrid_request(email_request)
            logger.info("📧 [SendGrid] Conversion successful")

            # Use default sender if not specified
            from_email = sendgrid_request.from_email or self._from_email
            logger.info(f"📧 [SendGrid] Using from_email: {from_email}")

            if not from_email:
                logger.error("📧 [SendGrid] ❌ No sender email address specified")
                return SendGridAdapter.from_sendgrid_response(
                    success=False, error_message="No sender email address specified"
                )

            # Create SendGrid API mail object
            logger.info("📧 [SendGrid] Creating Mail object...")
            mail = Mail(
                from_email=str(from_email),
                to_emails=str(sendgrid_request.to_email),
                subject=sendgrid_request.subject,
                html_content=sendgrid_request.html_content,
                plain_text_content=sendgrid_request.text_content,
            )

            # Add attachments (e.g., PDFs)
            if attachments:
                for attachment in attachments:
                    # Encode PDF bytes to base64
                    encoded_content = base64.b64encode(attachment.content).decode()

                    sendgrid_attachment = Attachment(
                        FileContent(encoded_content),
                        FileName(attachment.filename),
                        FileType(attachment.content_type),
                        Disposition("attachment"),
                    )
                    mail.add_attachment(sendgrid_attachment)
                logger.info(
                    f"📧 [SendGrid] Added {len(attachments)} attachment(s) to email"
                )

            # Disable click tracking for authentication emails to prevent URL rewriting
            # This stops SendGrid from changing app.myvoya.ai to url6597.myvoya.ai
            from sendgrid.helpers.mail import ClickTracking

            mail.tracking_settings = ClickTracking(enable=False)

            logger.info(
                "📧 [SendGrid] Mail object created with click tracking DISABLED"
            )
            logger.info(
                "📧 [SendGrid] This prevents URL rewriting from app.myvoya.ai to url6597.myvoya.ai"
            )

            # Send via SendGrid API
            logger.info("📧 [SendGrid] Calling SendGrid API...")
            response = self._client.send(mail)
            logger.info(
                f"📧 [SendGrid] SendGrid API response received - Status: {response.status_code}"
            )

            # Check success
            success = 200 <= response.status_code < 300
            logger.info(
                f"📧 [SendGrid] Success determination: {success} (status: {response.status_code})"
            )

            if success:
                message_id = response.headers.get("X-Message-Id")
                logger.info(
                    f"📧 [SendGrid] ✅ Email sent successfully to {sendgrid_request.to_email}, message_id: {message_id}"
                )
            else:
                logger.error(
                    f"📧 [SendGrid] ❌ Failed to send email to {sendgrid_request.to_email}, status: {response.status_code}"
                )
                logger.error(f"📧 [SendGrid] Response body: {response.body}")
                logger.error(
                    f"📧 [SendGrid] Response headers: {dict(response.headers)}"
                )

            # Convert response back to domain model via adapter
            email_response = SendGridAdapter.from_sendgrid_response(
                success=success,
                status_code=response.status_code,
                message_id=response.headers.get("X-Message-Id") if success else None,
                error_message=(
                    None
                    if success
                    else f"SendGrid returned status {response.status_code}: {response.body}"
                ),
            )

            logger.info(
                f"📧 [SendGrid] Returning EmailResponse: success={email_response.success}"
            )
            return email_response

        except Exception as e:
            logger.error(f"📧 [SendGrid] ❌ Exception during send: {e}", exc_info=True)
            return SendGridAdapter.from_sendgrid_response(
                success=False, error_message=str(e)
            )
