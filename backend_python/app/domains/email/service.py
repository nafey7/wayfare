"""Email service - ultra simplified version using email builders."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar, Optional

if TYPE_CHECKING:
    from integrations.sendgrid import SendGridClient

from app.core.config import settings
from app.domains.common import EmailStr

from .attachments import EmailAttachment, FlightPDFGenerator
from .builder import build_email

# Direct import - no abstraction needed for single provider
from .enums import EmailType

# Removed email permissions - rate limiting simplified
from .schemas import EmailRequest, EmailSpec
from .validators import validate_email_subject, validate_recipient_count

logger = logging.getLogger(__name__)


class EmailService:
    """Ultra-simplified email service using builders."""

    # Class-level caching
    _rate_limit_cache: ClassVar[dict[str, dict[str, Any]]] = {}
    _sendgrid_client: ClassVar[Optional["SendGridClient"]] = None
    _smtp_client: ClassVar[Optional[Any]] = None

    # ============================================================
    # PUBLIC API
    # ============================================================

    @classmethod
    async def send_email(
        cls,
        email_type: EmailType,
        recipient_email: str | EmailStr,
        context: dict[str, Any],
        attachments: list | None = None,
        revalidate_response: Any | None = None,
        booking_request: Any | None = None,
        trip_details: Any | None = None,
    ) -> bool:
        """Send email based on type and context.

        All email-specific logic is in email_builders.
        This method just:
        1. Gets the email data from the builder
        2. Auto-generates PDF attachment for booking/ticket emails if trip_details provided
        3. Sends it

        Args:
            email_type: Type of email to send
            recipient_email: Email address of recipient
            context: Template context data
            attachments: Optional list of EmailAttachment objects
            revalidate_response: Optional FlightRevalidateResponse with fare itinerary
            booking_request: Optional FlightBookingRequest with passenger information
            trip_details: Optional TripDetailsResponse for auto-generating PDFs (after ticketing)
        """
        logger.info(
            f"📬 [EmailService] Starting email send: type={email_type}, recipient={recipient_email}"
        )
        logger.info(f"📬 [EmailService] Context keys: {list(context.keys())}")
        logger.info(
            f"📬 [EmailService] trip_details={trip_details is not None}, revalidate_response={revalidate_response is not None}, booking_request={booking_request is not None}"
        )

        try:
            # Auto-generate PDF attachment for booking/ticket emails
            if email_type in [EmailType.BOOKING_CONFIRMATION, EmailType.TICKET_ISSUED]:
                pdf_attachment = None

                # Check if this is a hotel booking
                booking_details = context.get("booking_details", {})
                is_hotel_booking = (
                    "hotel_id" in booking_details
                    or "check_in" in booking_details
                    or "hotel_name" in booking_details
                )

                # For booking confirmation: handle hotels vs flights
                if email_type == EmailType.BOOKING_CONFIRMATION:
                    if is_hotel_booking:
                        # Hotel booking - use hotel PDF generator
                        logger.info("📎 [PDF] Generating hotel booking PDF")
                        pdf_attachment = await cls._generate_hotel_booking_pdf(
                            context, booking_details
                        )
                    elif trip_details:
                        logger.info("📎 [PDF] Generating PDF from trip_details (LCC)")
                        pdf_attachment = await cls._generate_booking_pdf(
                            email_type, context, trip_details
                        )
                    elif revalidate_response and booking_request:
                        logger.info(
                            "📎 [PDF] Generating PDF from revalidate + booking request (GDS)"
                        )
                        pdf_attachment = await cls._generate_booking_pdf_from_context(
                            context, revalidate_response, booking_request
                        )
                    else:
                        logger.warning(
                            f"📎 [PDF] No data available for PDF generation - trip_details={trip_details is not None}, revalidate={revalidate_response is not None}, booking={booking_request is not None}"
                        )

                # For ticket issuance: always use trip_details
                elif email_type == EmailType.TICKET_ISSUED and trip_details:
                    logger.info("📎 [PDF] Generating e-ticket PDF from trip_details")
                    pdf_attachment = await cls._generate_booking_pdf(
                        email_type, context, trip_details
                    )

                if pdf_attachment:
                    attachments = attachments or []
                    attachments.append(pdf_attachment)
                    logger.info(
                        f"📎 [PDF] PDF attachment added: {pdf_attachment.filename}"
                    )
                else:
                    logger.warning("📎 [PDF] Failed to generate PDF attachment")

            # Build complete email with template and data
            logger.info(
                f"📬 [EmailService] Building email template for type: {email_type}"
            )
            rendered_email = build_email(
                email_type,
                recipient_email,
                context,
                revalidate_response=revalidate_response,
                booking_request=booking_request,
                trip_details=trip_details,
            )

            if not rendered_email:
                logger.error(
                    f"📬 [EmailService] ❌ Failed to build email for type: {email_type}"
                )
                return False

            logger.info(
                f"📬 [EmailService] ✅ Email template built successfully for type: {email_type}"
            )
            logger.info(
                f"📬 [EmailService] Email subject: {rendered_email.spec.subject}"
            )

            # Send the email
            logger.info(
                f"📬 [EmailService] Calling _send method for: {recipient_email}"
            )
            send_result = cls._send(
                recipient_email=recipient_email,
                email_spec=rendered_email.spec,
                html_content=rendered_email.rendered_html,
                text_content=rendered_email.rendered_text,
                attachments=attachments,
            )

            logger.info(
                f"📬 [EmailService] _send method result: {send_result} for {recipient_email}"
            )
            return send_result

        except ValueError as e:
            logger.error(f"📬 [EmailService] ❌ Validation error for {email_type}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"📬 [EmailService] ❌ Failed to send {email_type} email to {recipient_email}: {e}",
                exc_info=True,
            )
            return False

    @classmethod
    async def _generate_booking_pdf_from_context(
        cls,
        context: dict[str, Any],
        revalidate_response: Any,
        booking_request: Any,
    ) -> EmailAttachment | None:
        """Generate booking confirmation PDF from revalidate response and booking request.

        Used for GDS bookings where trip_details is not yet available.

        Args:
            context: Email context with voya_booking_reference
            revalidate_response: FlightRevalidateResponse with fare itinerary
            booking_request: FlightBookingRequest with passenger information

        Returns:
            EmailAttachment with PDF or None if generation failed
        """
        try:
            from .attachments.pdf_generator_from_context import (
                generate_booking_pdf_from_context,
            )

            voya_booking_reference = context.get("voya_booking_reference")
            if not voya_booking_reference:
                logger.error("📎 [PDF] No voya_booking_reference in context")
                return None

            # Generate PDF from revalidate + booking context
            pdf_bytes, metadata = await generate_booking_pdf_from_context(
                revalidate_response=revalidate_response,
                booking_request=booking_request,
                voya_booking_reference=voya_booking_reference,
            )

            filename = f"booking_{voya_booking_reference}.pdf"
            logger.info(
                f"📎 [PDF] Generated booking PDF from context: {metadata.file_path}"
            )

            return EmailAttachment(
                filename=filename, content=pdf_bytes, content_type="application/pdf"
            )

        except Exception as e:
            logger.error(
                f"📎 [PDF] Failed to generate PDF from context: {e}", exc_info=True
            )
            return None

    @classmethod
    async def _generate_booking_pdf(
        cls,
        email_type: EmailType,
        context: dict[str, Any],
        trip_details: Any,
    ) -> EmailAttachment | None:
        """Generate PDF attachment for booking/ticket emails.

        Args:
            email_type: BOOKING_CONFIRMATION or TICKET_ISSUED
            context: Email context with voya_booking_reference
            trip_details: TripDetailsResponse object from FlightLogic

        Returns:
            EmailAttachment with PDF or None if generation failed
        """
        try:
            pdf_generator = FlightPDFGenerator()
            voya_booking_reference = context.get("voya_booking_reference")

            if not voya_booking_reference:
                logger.error("📎 [PDF] No voya_booking_reference in context")
                return None

            if email_type == EmailType.BOOKING_CONFIRMATION:
                # Generate booking confirmation PDF
                fare_type = getattr(trip_details, "fare_type", "WebFare")

                # Extract PNR from booking response if available (for GDS bookings)
                booking_response_pnr = context.get("booking_response_pnr")

                # Cancellation policy is NOT included in PDF attachments for both GDS and LCC
                # (it's included in email body only, not in PDF attachment)
                pdf_bytes, metadata = await pdf_generator.generate_booking_confirmation(
                    trip_details=trip_details,
                    voya_booking_reference=voya_booking_reference,
                    fare_type=fare_type,
                    override_pnr=booking_response_pnr,  # Use PNR from booking response if available
                    cancellation_policy_text=None,  # Never include in PDF - only in email body
                )
                filename = f"booking_{voya_booking_reference}.pdf"

            elif email_type == EmailType.TICKET_ISSUED:
                # Generate e-ticket PDF
                ticket_numbers = context.get("ticket_numbers", [])
                pdf_bytes, metadata = await pdf_generator.generate_ticket_document(
                    trip_details=trip_details,
                    ticket_numbers=ticket_numbers,
                    voya_booking_reference=voya_booking_reference,
                )
                filename = f"ticket_{voya_booking_reference}.pdf"

            else:
                logger.error(f"📎 [PDF] Unsupported email type: {email_type}")
                return None

            logger.info(
                f"📎 [PDF] Generated {metadata.pdf_type} PDF: {metadata.file_path}"
            )

            return EmailAttachment(
                filename=filename, content=pdf_bytes, content_type="application/pdf"
            )

        except Exception as e:
            logger.error(f"📎 [PDF] Failed to generate PDF: {e}", exc_info=True)
            return None

    @classmethod
    async def _generate_hotel_booking_pdf(
        cls,
        context: dict[str, Any],
        booking_details: dict[str, Any],
    ) -> EmailAttachment | None:
        """Generate PDF attachment for hotel booking emails.

        Args:
            context: Email context with voya_booking_reference
            booking_details: Hotel booking details dict

        Returns:
            EmailAttachment with PDF or None if generation failed
        """
        try:
            from app.domains.email.attachments.hotel_pdf_generator import (
                HotelPDFGenerator,
            )

            pdf_generator = HotelPDFGenerator()
            voya_booking_reference = context.get("voya_booking_reference")

            if not voya_booking_reference:
                logger.error("📎 [PDF] No voya_booking_reference in context")
                return None

            # Extract cancellation policy from context or booking_details
            cancellation_policy = (
                context.get("cancellation_policy")
                or booking_details.get("cancellation_policy")
                or booking_details.get("cancellationPolicy")
            )

            pdf_bytes, metadata = await pdf_generator.generate_booking_confirmation(
                booking_details=booking_details,
                voya_booking_reference=voya_booking_reference,
                cancellation_policy=cancellation_policy,
            )

            logger.info(f"📎 [PDF] Generated hotel booking PDF: {metadata.file_path}")

            return pdf_generator.create_attachment(pdf_bytes, voya_booking_reference)

        except Exception as e:
            logger.error(f"📎 [PDF] Failed to generate hotel PDF: {e}", exc_info=True)
            return None

    # ============================================================
    # CORE SENDING LOGIC
    # ============================================================

    @classmethod
    def _send(
        cls,
        recipient_email: str | EmailStr,
        email_spec: EmailSpec,
        html_content: str,
        text_content: str,
        attachments: list | None = None,
    ) -> bool:
        """Send email with given data and optional attachments."""
        logger.info(f"📤 [Send] Starting _send method for: {recipient_email}")
        logger.info(f"📤 [Send] Email type: {email_spec.email_type_name}")
        logger.info(f"📤 [Send] USE_MAILHOG: {settings.USE_MAILHOG}")
        logger.info(
            f"📤 [Send] SENDGRID_API_KEY configured: {bool(settings.SENDGRID_API_KEY)}"
        )

        # Handle debug mode - log but don't override recipient for testing
        if settings.DEBUG:
            logger.info(
                f"📤 [Send] [DEV MODE] Sending {email_spec.email_type_name} email to {recipient_email}"
            )
            # Don't override recipient in development - use actual email for testing

        # Handle debug mode - redirect to dev email if configured
        #        if settings.DEBUG and hasattr(settings, 'DEV_EMAIL_RECIPIENT') and settings.DEV_EMAIL_RECIPIENT:
        #            logger.info(f"[DEV MODE] Redirecting {email_spec.email_type_name} email to {settings.DEV_EMAIL_RECIPIENT}")
        #            recipient_email = settings.DEV_EMAIL_RECIPIENT

        # Validation
        logger.info("📤 [Send] Validating email subject...")
        if not validate_email_subject(email_spec.subject):
            logger.warning(f"📤 [Send] ❌ Invalid subject: {email_spec.subject[:50]}")
            return False

        logger.info("📤 [Send] Validating recipient...")
        if not validate_recipient_count([str(recipient_email)]):
            logger.warning(f"📤 [Send] ❌ Invalid recipient: {recipient_email}")
            return False

        # Rate limiting
        logger.info("📤 [Send] Checking rate limits...")
        if not cls._check_rate_limit(str(recipient_email)):
            logger.warning(f"📤 [Send] ❌ Rate limit exceeded for: {recipient_email}")
            return False

        # Initialize email client based on configuration
        logger.info("📤 [Send] Initializing email client...")
        if not cls._initialize_email_client():
            logger.error("📤 [Send] ❌ Failed to initialize email client")
            return False

        # Create email request (from_email handled by SendGrid)
        logger.info("📤 [Send] Creating email request...")
        email_request = EmailRequest(
            to_email=recipient_email,
            subject=email_spec.subject,
            html_content=html_content,
            text_content=text_content,
        )
        logger.info(
            f"📤 [Send] Email request created: to={recipient_email}, subject='{email_spec.subject}'"
        )

        # Send via configured email provider with attachments
        logger.info("📤 [Send] Determining email provider...")
        if settings.USE_MAILHOG and cls._smtp_client:
            logger.info("📤 [Send] Using SMTP client (MailHog)")
            result = cls._smtp_client.send_email(email_request, attachments=attachments)
        elif cls._sendgrid_client:
            logger.info("📤 [Send] Using SendGrid client")
            result = cls._sendgrid_client.send_email(
                email_request, attachments=attachments
            )
        else:
            logger.error("📤 [Send] ❌ No email client initialized")
            return False

        logger.info(
            f"📤 [Send] Provider response - Success: {result.success}, Status: {result.status_code}"
        )

        if not result.success:
            logger.error(
                f"📤 [Send] ❌ {result.provider} error: {result.error_message or result.status_code} "
                f"for {email_spec.email_type_name}"
            )
            return False

        logger.info(
            f"📤 [Send] ✅ {email_spec.email_type_name} email sent to {recipient_email} via {result.provider}, "
            f"status: {result.status_code}"
        )
        return True

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @classmethod
    def _initialize_email_client(cls) -> bool:
        """Initialize email client based on configuration."""
        if settings.USE_MAILHOG:
            return cls._initialize_smtp_client()
        return cls._initialize_sendgrid_client()

    @classmethod
    def _initialize_smtp_client(cls) -> bool:
        """Initialize SMTP client for MailHog."""
        try:
            # Import here to avoid circular import
            from integrations.smtp import SMTPClient

            # Log configuration details for debugging
            logger.info("Initializing SMTP client with:")
            logger.info(f"  Host: {settings.MAILHOG_HOST}")
            logger.info(f"  Port: {settings.MAILHOG_PORT}")
            logger.info(f"  From Email: {settings.SENDGRID_FROM_EMAIL}")
            logger.info(f"  USE_MAILHOG: {settings.USE_MAILHOG}")

            cls._smtp_client = SMTPClient(
                host=settings.MAILHOG_HOST,
                port=settings.MAILHOG_PORT,
                from_email=settings.SENDGRID_FROM_EMAIL,  # Reuse from_email setting
                # MailHog doesn't require authentication
                username=None,
                password=None,
                use_tls=False,
                use_ssl=False,
            )

            # Test connection before marking as successful
            if cls._smtp_client.test_connection():
                logger.info(
                    f"SMTP client initialized and tested successfully for MailHog ({settings.MAILHOG_HOST}:{settings.MAILHOG_PORT})"
                )
                return True
            logger.error("SMTP client initialization failed - connection test failed")
            return False

        except Exception as e:
            logger.error(f"Failed to initialize SMTP client: {e}")
            return False

    @classmethod
    def _initialize_sendgrid_client(cls) -> bool:
        """Initialize SendGrid client."""
        logger.info("🔧 [Init] Initializing SendGrid client...")
        logger.info(
            f"🔧 [Init] SENDGRID_API_KEY configured: {bool(settings.SENDGRID_API_KEY)}"
        )
        logger.info(f"🔧 [Init] SENDGRID_FROM_EMAIL: {settings.SENDGRID_FROM_EMAIL}")

        if not settings.SENDGRID_API_KEY:
            logger.error("🔧 [Init] ❌ SendGrid API key not configured")
            return False

        try:
            # Import here to avoid circular import
            from integrations.sendgrid import SendGridClient

            logger.info("🔧 [Init] Creating SendGrid client instance...")
            cls._sendgrid_client = SendGridClient(
                api_key=settings.SENDGRID_API_KEY,
                from_email=settings.SENDGRID_FROM_EMAIL,
            )
            logger.info("🔧 [Init] ✅ SendGrid client initialized successfully")
            return True
        except Exception as e:
            logger.error(
                f"🔧 [Init] ❌ Failed to initialize SendGrid: {e}", exc_info=True
            )
            return False

    @classmethod
    def _check_rate_limit(cls, email: str) -> bool:
        """Check email rate limits."""
        now = datetime.now(UTC)

        if email not in cls._rate_limit_cache:
            cls._rate_limit_cache[email] = {
                "last_email_time": None,
                "daily_count": 0,
                "daily_reset": now.date(),
            }

        cache = cls._rate_limit_cache[email]

        # Reset daily counter if new day
        if cache["daily_reset"] < now.date():
            cache["daily_count"] = 0
            cache["daily_reset"] = now.date()

        # Simplified rate limiting - just track counts
        if cache["daily_count"] >= 100:  # Simple daily limit
            logger.warning(f"Daily email limit reached for {email}")
            return False

        cache["last_email_time"] = now
        cache["daily_count"] += 1
        return True
