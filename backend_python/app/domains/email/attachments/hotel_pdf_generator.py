"""PDF generator for hotel bookings using xhtml2pdf and Jinja2 templates."""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.core.config import settings

from .schemas import EmailAttachment, PDFMetadata

logger = logging.getLogger(__name__)


class HotelPDFGenerator:
    """Generate PDF documents for hotel bookings using Jinja2 templates."""

    def __init__(self) -> None:
        # Setup Jinja2 environment for PDF templates
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def generate_booking_confirmation(
        self,
        booking_details: dict[str, Any],
        voya_booking_reference: str,
        cancellation_policy: str | None = None,
    ) -> tuple[bytes, PDFMetadata]:
        """Generate hotel booking confirmation PDF.

        Args:
            booking_details: Hotel booking details dict from FlightLogic API
            voya_booking_reference: VOYA booking reference (e.g., VOYA-HOTEL-2025-00001)
            cancellation_policy: Optional cancellation policy text

        Returns:
            Tuple of (pdf_bytes, metadata)

        Raises:
            ValueError: If required booking_details fields are missing
        """
        logger.info(
            f"Generating hotel booking confirmation PDF for {voya_booking_reference}"
        )

        # Use fallback when hotel_name is missing (e.g. API didn't return it)
        if not booking_details.get("hotel_name") and not booking_details.get(
            "hotelName"
        ):
            booking_details = {**booking_details, "hotel_name": "Your Hotel"}
            logger.warning(
                "PDF generator: hotel_name missing, using fallback 'Your Hotel'"
            )

        # Build context for template
        context = self._build_booking_context(
            booking_details, voya_booking_reference, cancellation_policy
        )

        # Render HTML from Jinja2 template
        html_content = self._render_template("booking_hotel.html", context)

        # Generate PDF from HTML
        pdf_bytes = self._html_to_pdf(html_content)

        # Save to logs/pdfs/
        file_path = self._save_pdf(pdf_bytes, "booking", voya_booking_reference)

        # Create metadata
        metadata = PDFMetadata(
            voya_booking_reference=voya_booking_reference,
            external_reference=booking_details.get("supplier_confirmation_num"),
            pdf_type="booking",
            file_size_bytes=len(pdf_bytes),
            file_path=str(file_path) if file_path else None,
        )

        logger.info(
            f"Hotel booking PDF generated: {len(pdf_bytes)} bytes",
            extra={
                "voya_booking_reference": voya_booking_reference,
                "template": "booking_hotel.html",
            },
        )

        return pdf_bytes, metadata

    def create_attachment(
        self, pdf_bytes: bytes, voya_booking_reference: str
    ) -> EmailAttachment:
        """Create email attachment from PDF bytes.

        Args:
            pdf_bytes: PDF content
            voya_booking_reference: VOYA booking reference

        Returns:
            EmailAttachment ready for email service
        """
        filename = f"booking_{voya_booking_reference}.pdf"

        return EmailAttachment(
            filename=filename, content=pdf_bytes, content_type="application/pdf"
        )

    # ============================================================
    # INTERNAL METHODS - Context Building
    # ============================================================

    def _build_booking_context(
        self,
        booking_details: dict[str, Any],
        voya_booking_reference: str,
        cancellation_policy: str | None = None,
    ) -> dict[str, Any]:
        """Build template context for hotel booking confirmation PDF.

        Args:
            booking_details: Booking details dict from FlightLogic API
            voya_booking_reference: VOYA booking reference
            cancellation_policy: Optional cancellation policy text
        """
        # Extract cancellation policy from booking_details if not provided
        if not cancellation_policy:
            cancellation_policy = (
                booking_details.get("cancellation_policy")
                or booking_details.get("cancellationPolicy")
                or None
            )

        # Extract dates
        check_in = booking_details.get("check_in") or booking_details.get("checkIn")
        check_out = booking_details.get("check_out") or booking_details.get("checkOut")

        # Format dates
        check_in_date = "N/A"
        check_out_date = "N/A"
        if check_in:
            try:
                check_in_dt = (
                    datetime.fromisoformat(check_in.replace("Z", "+00:00"))
                    if isinstance(check_in, str)
                    else check_in
                )
                check_in_date = check_in_dt.strftime("%d %B %Y")
            except Exception:
                check_in_date = str(check_in)

        if check_out:
            try:
                check_out_dt = (
                    datetime.fromisoformat(check_out.replace("Z", "+00:00"))
                    if isinstance(check_out, str)
                    else check_out
                )
                check_out_date = check_out_dt.strftime("%d %B %Y")
            except Exception:
                check_out_date = str(check_out)

        # Calculate nights
        nights = 0
        if check_in and check_out:
            try:
                check_in_dt = (
                    datetime.fromisoformat(check_in.replace("Z", "+00:00"))
                    if isinstance(check_in, str)
                    else check_in
                )
                check_out_dt = (
                    datetime.fromisoformat(check_out.replace("Z", "+00:00"))
                    if isinstance(check_out, str)
                    else check_out
                )
                nights = (check_out_dt - check_in_dt).days
            except Exception:
                nights = 0

        # Extract pricing
        total_price = booking_details.get("total_price") or booking_details.get(
            "NetPrice"
        )
        if total_price:
            try:
                total_price = float(total_price)
            except (ValueError, TypeError):
                total_price = 0.0
        else:
            total_price = 0.0

        currency = booking_details.get("currency") or "USD"

        # Extract guests
        guests = booking_details.get("guests", [])
        rooms = booking_details.get("rooms", [])

        # Format guests for template
        formatted_guests = []
        for guest in guests:
            formatted_guests.append(
                {
                    "title": guest.get("title", ""),
                    "first_name": guest.get("first_name") or guest.get("firstName", ""),
                    "last_name": guest.get("last_name") or guest.get("lastName", ""),
                    "is_child": guest.get("is_child") or guest.get("isChild", False),
                    "age": guest.get("age"),
                    "room_number": guest.get("room_number") or guest.get("roomNumber"),
                }
            )

        return {
            "generated_date": datetime.now().strftime("%d %B %Y, %H:%M"),
            "voya_booking_reference": voya_booking_reference,
            "supplier_confirmation_num": booking_details.get(
                "supplier_confirmation_num"
            )
            or booking_details.get("supplierConfirmationNum")
            or "N/A",
            "reference_num": booking_details.get("reference_num")
            or booking_details.get("referenceNum")
            or "N/A",
            "booking_date": datetime.now().strftime("%d %B %Y"),
            "hotel_name": booking_details.get("hotel_name")
            or booking_details.get("hotelName")
            or "Hotel",
            "hotel_address": booking_details.get("address") or "",
            "hotel_city": booking_details.get("city") or "",
            "hotel_rating": booking_details.get("hotel_rating")
            or booking_details.get("hotelRating")
            or 0,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "nights": nights,
            "currency": currency,
            "total_price": f"{total_price:.2f}",
            "guests": formatted_guests,
            "rooms": rooms,
            "cancellation_policy": cancellation_policy,
        }

    # ============================================================
    # INTERNAL METHODS - Template & PDF Generation
    # ============================================================

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render Jinja2 template with context.

        Args:
            template_name: Name of template file (e.g., "booking_hotel.html")
            context: Template context data

        Returns:
            Rendered HTML string
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise

    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF using xhtml2pdf.

        Args:
            html_content: HTML string to convert

        Returns:
            PDF as bytes
        """
        # Create BytesIO buffer for PDF output
        pdf_buffer = BytesIO()

        # Generate PDF using xhtml2pdf
        pisa_status = pisa.CreatePDF(
            src=html_content, dest=pdf_buffer, encoding="UTF-8"
        )

        # Check for errors
        if pisa_status.err:
            logger.error(f"xhtml2pdf error: {pisa_status.err}")
            raise Exception(f"PDF generation failed with error code: {pisa_status.err}")

        # Get PDF bytes
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()

        return pdf_bytes

    def _save_pdf(self, pdf_bytes: bytes, pdf_type: str, reference: str) -> Path | None:
        """Save PDF to logs/pdfs/ directory.

        Args:
            pdf_bytes: PDF content as bytes
            pdf_type: "booking" or "ticket"
            reference: VOYA booking reference

        Returns:
            Path to saved PDF file or None if save failed
        """
        try:
            # Create directory if doesn't exist
            pdf_dir = Path(settings.PDF_OUTPUT_DIR)
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Create filename: {type}_{reference}_{timestamp}.pdf
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pdf_type}_{reference}_{timestamp}.pdf"
            file_path = pdf_dir / filename

            # Save PDF
            file_path.write_bytes(pdf_bytes)

            logger.info(
                f"PDF saved: {filename}",
                extra={
                    "pdf_type": pdf_type,
                    "reference": reference,
                    "size_kb": len(pdf_bytes) // 1024,
                    "path": str(file_path),
                },
            )

            return file_path

        except Exception as e:
            logger.error(f"Failed to save PDF {pdf_type}_{reference}: {e}")
            return None
