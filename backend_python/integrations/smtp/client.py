"""SMTP email client implementation for MailHog and other SMTP providers."""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.domains.common import EmailStr
from app.domains.email.schemas import EmailRequest, EmailResponse

logger = logging.getLogger(__name__)


class SMTPClient:
    """SMTP email client for MailHog and other SMTP servers."""

    def __init__(
        self,
        host: str,
        port: int,
        from_email: EmailStr | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
        use_ssl: bool = False,
    ) -> None:
        """Initialize SMTP client.

        Args:
            host: SMTP server hostname
            port: SMTP server port
            from_email: Default sender email address
            username: SMTP username (optional for MailHog)
            password: SMTP password (optional for MailHog)
            use_tls: Use STARTTLS encryption
            use_ssl: Use SSL encryption
        """
        self.host = host
        self.port = port
        self.from_email = from_email
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    def test_connection(self) -> bool:
        """Test SMTP connection before sending emails.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing SMTP connection to {self.host}:{self.port}")

            # Connect to SMTP server with timeout
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)

            try:
                # Start TLS if requested
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                # Login if credentials provided
                if self.username and self.password:
                    server.login(self.username, self.password)

                logger.info(
                    f"SMTP connection test successful to {self.host}:{self.port}"
                )
                return True

            finally:
                server.quit()

        except Exception as e:
            logger.error(f"SMTP connection test failed to {self.host}:{self.port}: {e}")
            return False

    def send_email(
        self, email_request: EmailRequest, attachments: list | None = None
    ) -> EmailResponse:
        """Send email via SMTP with optional attachments.

        Args:
            email_request: Email request with recipient, subject, and content
            attachments: Optional list of EmailAttachment objects (PDFs, etc.)

        Returns:
            EmailResponse with success status and details
        """
        try:
            # Create message (use mixed for attachments)
            msg = MIMEMultipart("mixed" if attachments else "alternative")
            msg["From"] = str(self.from_email or email_request.to_email)
            msg["To"] = str(email_request.to_email)
            msg["Subject"] = email_request.subject

            # Create alternative part for text/html content
            if attachments:
                alt_part = MIMEMultipart("alternative")
                msg.attach(alt_part)
            else:
                alt_part = msg

            # Add text content
            if email_request.text_content:
                text_part = MIMEText(email_request.text_content, "plain", "utf-8")
                alt_part.attach(text_part)

            # Add HTML content
            if email_request.html_content:
                html_part = MIMEText(email_request.html_content, "html", "utf-8")
                alt_part.attach(html_part)

            # Add attachments (e.g., PDFs)
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(attachment.content, _subtype="pdf")
                    part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=attachment.filename,
                    )
                    msg.attach(part)
                logger.info(f"Added {len(attachments)} attachment(s) to email")

            # Connect to SMTP server
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port)
            else:
                server = smtplib.SMTP(self.host, self.port)

            try:
                # Enable debug output for development
                server.set_debuglevel(0)

                # Start TLS if requested
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                # Login if credentials provided
                if self.username and self.password:
                    server.login(self.username, self.password)

                # Send email
                server.send_message(msg)

                logger.info(
                    f"Email sent successfully to {email_request.to_email} "
                    f"via SMTP ({self.host}:{self.port})"
                )

                return EmailResponse(
                    success=True,
                    status_code=250,  # Standard SMTP success code
                    provider="SMTP",
                    message_id=None,  # SMTP doesn't provide message ID like SendGrid
                )

            finally:
                server.quit()

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e!s}"
            logger.error(
                f"Failed to send email to {email_request.to_email}: {error_msg}"
            )

            return EmailResponse(
                success=False,
                status_code=500,
                provider="SMTP",
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Unexpected error: {e!s}"
            logger.error(
                f"Failed to send email to {email_request.to_email}: {error_msg}"
            )

            return EmailResponse(
                success=False,
                status_code=500,
                provider="SMTP",
                error_message=error_msg,
            )
