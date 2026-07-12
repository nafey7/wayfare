"""PDF generator for flight bookings and tickets using xhtml2pdf and Jinja2 templates."""

import logging
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.core.config import settings

from .schemas import EmailAttachment, PDFMetadata

if TYPE_CHECKING:
    from app.domains.flight.schemas import TripDetailsResponse

logger = logging.getLogger(__name__)


class FlightPDFGenerator:
    """Generate PDF documents for flight bookings and tickets using Jinja2 templates."""

    def __init__(self) -> None:
        # Setup Jinja2 environment for PDF templates
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def generate_booking_confirmation(
        self,
        trip_details: "TripDetailsResponse",
        voya_booking_reference: str,
        fare_type: str,
        override_pnr: str | None = None,
        cancellation_policy_text: str | None = None,
    ) -> tuple[bytes, PDFMetadata]:
        """Generate booking confirmation PDF.

        For LCC: Includes ticket numbers (already issued) - uses booking_lcc.html
        For GDS: No ticket numbers (payment required warning) - uses booking_gds.html

        Args:
            trip_details: Complete trip details from FlightLogic
            voya_booking_reference: VOYA booking reference (e.g., VOYA-2025-00001)
            fare_type: "WebFare" (LCC) or "Public"/"Private" (GDS)
            override_pnr: Optional PNR from booking response to override trip_details PNR
            cancellation_policy_text: Optional cancellation policy text from fare rules

        Returns:
            Tuple of (pdf_bytes, metadata)

        Raises:
            ValueError: If required trip_details fields are missing
        """
        logger.info(f"Generating booking confirmation PDF for {voya_booking_reference}")

        # Validate required trip details fields
        self._validate_trip_details(trip_details, voya_booking_reference)

        # Determine if tickets are issued based on fare_type
        # WebFare (LCC) = tickets issued immediately, Public/Private (GDS) = tickets issued after payment
        is_lcc = fare_type == "WebFare"
        has_tickets = is_lcc and any(p.e_ticket_number for p in trip_details.passengers)

        # Select appropriate template
        template_name = "booking_lcc.html" if has_tickets else "booking_gds.html"

        # Prepare context for template with optional PNR override
        context = self._build_booking_context(
            trip_details,
            voya_booking_reference,
            has_tickets,
            override_pnr,
            cancellation_policy_text,
        )

        # Render HTML from Jinja2 template
        html_content = self._render_template(template_name, context)

        # Generate PDF from HTML
        pdf_bytes = self._html_to_pdf(html_content)

        # Save to logs/pdfs/
        file_path = self._save_pdf(pdf_bytes, "booking", voya_booking_reference)

        # Create metadata
        metadata = PDFMetadata(
            voya_booking_reference=voya_booking_reference,
            external_reference=trip_details.external_booking_reference,
            pdf_type="booking",
            file_size_bytes=len(pdf_bytes),
            file_path=str(file_path) if file_path else None,
        )

        logger.info(
            f"Booking PDF generated: {len(pdf_bytes)} bytes",
            extra={
                "voya_booking_reference": voya_booking_reference,
                "has_tickets": has_tickets,
                "template": template_name,
            },
        )

        return pdf_bytes, metadata

    async def generate_ticket_document(
        self,
        trip_details: "TripDetailsResponse",
        ticket_numbers: list[str],
        voya_booking_reference: str,
    ) -> tuple[bytes, PDFMetadata]:
        """Generate e-ticket PDF (GDS only, after ticket issuance).

        Uses ticket.html template.

        Args:
            trip_details: Complete trip details with ticket numbers
            ticket_numbers: List of 13-digit IATA ticket numbers
            voya_booking_reference: VOYA booking reference

        Returns:
            Tuple of (pdf_bytes, metadata)
        """
        logger.info(f"Generating ticket PDF for {voya_booking_reference}")

        # Prepare context for template
        context = self._build_ticket_context(
            trip_details, voya_booking_reference, ticket_numbers
        )

        # Render HTML from Jinja2 template
        html_content = self._render_template("ticket.html", context)

        # Generate PDF from HTML
        pdf_bytes = self._html_to_pdf(html_content)

        # Save to logs/pdfs/
        file_path = self._save_pdf(pdf_bytes, "ticket", voya_booking_reference)

        # Create metadata
        metadata = PDFMetadata(
            voya_booking_reference=voya_booking_reference,
            external_reference=trip_details.external_booking_reference,
            pdf_type="ticket",
            file_size_bytes=len(pdf_bytes),
            file_path=str(file_path) if file_path else None,
        )

        logger.info(
            f"Ticket PDF generated: {len(pdf_bytes)} bytes",
            extra={
                "voya_booking_reference": voya_booking_reference,
                "ticket_count": len(ticket_numbers),
            },
        )

        return pdf_bytes, metadata

    def create_attachment(
        self, pdf_bytes: bytes, voya_booking_reference: str, pdf_type: str
    ) -> EmailAttachment:
        """Create email attachment from PDF bytes.

        Args:
            pdf_bytes: PDF content
            voya_booking_reference: VOYA booking reference
            pdf_type: "booking" or "ticket"

        Returns:
            EmailAttachment ready for email service
        """
        filename_prefix = "booking" if pdf_type == "booking" else "ticket"
        filename = f"{filename_prefix}_{voya_booking_reference}.pdf"

        return EmailAttachment(
            filename=filename, content=pdf_bytes, content_type="application/pdf"
        )

    # ============================================================
    # INTERNAL METHODS - Context Building
    # ============================================================

    def _build_booking_context(
        self,
        trip_details: "TripDetailsResponse",
        voya_booking_reference: str,
        has_tickets: bool,
        override_pnr: str | None = None,
        cancellation_policy_text: str | None = None,
    ) -> dict:
        """Build template context for booking confirmation PDF.

        Args:
            trip_details: Trip details from FlightLogic
            voya_booking_reference: VOYA booking reference
            has_tickets: Whether tickets are already issued
            override_pnr: Optional PNR to use instead of trip_details PNR (for GDS bookings)
            cancellation_policy_text: Optional cancellation policy text from fare rules
        """
        # Use override PNR if provided (from booking response), otherwise extract from segments
        # PNR is validated as required in _validate_trip_details
        pnr = override_pnr or trip_details.segments[0].airline_pnr.pnr_code

        # Extract fare breakdown from pricing
        currency = trip_details.pricing.fare_totals.total_fare.currency
        base_fare = f"{trip_details.pricing.fare_totals.base_fare.amount:.2f}"
        taxes = f"{trip_details.pricing.fare_totals.total_tax.amount:.2f}"
        total_fare = f"{trip_details.pricing.fare_totals.total_fare.amount:.2f}"

        context = {
            "generated_date": datetime.now().strftime("%d %B %Y, %H:%M"),
            "voya_booking_reference": voya_booking_reference,
            "pnr": pnr,
            "external_reference": trip_details.external_booking_reference,
            "booking_date": datetime.now().strftime("%d %B %Y"),
            "currency": currency,
            "base_fare": base_fare,
            "taxes": taxes,
            "total_fare": total_fare,
            "passengers": [],
            "segments": [],
            "fare_rules": [],
            "cancellation_policy_text": self._process_cancellation_policy_text(
                cancellation_policy_text
            ),
        }

        # Add payment deadline for GDS bookings
        if not has_tickets:
            context["payment_deadline"] = (
                "24 hours"  # TODO: Get actual deadline from trip_details
            )

        # Extract fare rules per passenger type from fare_breakdown
        if trip_details.fare_breakdown:
            for fare_item in trip_details.fare_breakdown:
                if fare_item.penalty_details:
                    # Format passenger type (e.g., "Adult", "Child", "Infant")
                    passenger_type = (
                        fare_item.passenger_type_info.passenger_type.value.capitalize()
                    )
                    passenger_count = fare_item.passenger_type_info.passenger_count

                    # Format cancellation fee
                    cancellation_fee = f"{fare_item.penalty_details.cancellation_penalty.currency} {fare_item.penalty_details.cancellation_penalty.amount:.2f}"

                    # Format change fee
                    change_fee = f"{fare_item.penalty_details.change_penalty.currency} {fare_item.penalty_details.change_penalty.amount:.2f}"

                    fare_rule = {
                        "passenger_type": passenger_type,
                        "passenger_count": passenger_count,
                        "is_cancellation_allowed": fare_item.penalty_details.is_cancellation_allowed,
                        "cancellation_fee": cancellation_fee,
                        "is_change_allowed": fare_item.penalty_details.is_change_allowed,
                        "change_fee": change_fee,
                    }
                    context["fare_rules"].append(fare_rule)

        # Process passengers
        for passenger in trip_details.passengers:
            # Handle date_of_birth - FlightLogic returns ISO string format
            # Date of birth is validated as required in _validate_trip_details
            dob = passenger.personal_info.date_of_birth
            if isinstance(dob, str):
                # Parse ISO format string (e.g., "1985-03-15T00:00:00")
                dob = datetime.fromisoformat(dob.replace("Z", "+00:00")).date()
            dob_formatted = dob.strftime("%d %B %Y")

            # Calculate passenger type based on age
            today = datetime.now().date()
            age = today.year - dob.year
            if (today.month, today.day) < (dob.month, dob.day):
                age -= 1

            if age < 2:
                passenger_type = "Infant"
            elif age < 12:
                passenger_type = "Child"
            else:
                passenger_type = "Adult"

            passenger_data = {
                "type": passenger_type,
                "title": passenger.personal_info.name.title or "Mr/Ms",
                "first_name": passenger.personal_info.name.first_name,
                "last_name": passenger.personal_info.name.last_name,
                "date_of_birth": dob_formatted,
            }

            # Add ticket number if available
            if passenger.e_ticket_number:
                passenger_data["ticket_number"] = passenger.e_ticket_number

            # Add passport info if available
            if (
                hasattr(passenger.personal_info, "passport")
                and passenger.personal_info.passport
            ):
                passenger_data["passport_number"] = (
                    passenger.personal_info.passport.number
                )
                passenger_data["passport_country"] = (
                    passenger.personal_info.passport.issuing_country
                )

            context["passengers"].append(passenger_data)

        # Process flight segments - detect return flights by tracking route direction changes
        # First pass: detect all leg boundaries
        # For round trips: Outbound (away from origin), Return (back towards origin)
        # Strategy: Track all visited airports and detect when we start moving back

        first_origin = trip_details.segments[0].departure_airport.iata_code

        # Find the furthest point (likely the turnaround for return journey)
        visited_airports = {first_origin}
        for seg in trip_details.segments:
            visited_airports.add(seg.departure_airport.iata_code)
            visited_airports.add(seg.arrival_airport.iata_code)

        leg_boundaries = [0]  # First segment always starts leg 0
        return_leg_started = False  # Track if we've already started the return leg

        for i in range(1, len(trip_details.segments)):
            prev_seg = trip_details.segments[i - 1]
            curr_seg = trip_details.segments[i]

            # Detect leg boundary by:
            # 1. Route discontinuity (current origin != previous destination)
            # 2. Direction reversal: First time we head back to an earlier airport (return leg start)
            route_discontinuity = (
                curr_seg.departure_airport.iata_code
                != prev_seg.arrival_airport.iata_code
            )

            # Check if current segment is going back to an airport from earlier in the journey
            # This indicates return leg start, but only mark it once
            going_back_to_earlier_airport = False
            if (
                i > 1 and not return_leg_started
            ):  # Only check if return hasn't started yet
                earlier_airports = {
                    trip_details.segments[j].arrival_airport.iata_code for j in range(i)
                }
                going_back_to_earlier_airport = (
                    curr_seg.arrival_airport.iata_code in earlier_airports
                )
                if going_back_to_earlier_airport:
                    return_leg_started = True

            if route_discontinuity or going_back_to_earlier_airport:
                leg_boundaries.append(i)

        # Determine if this is a round trip (has return flight)
        has_multiple_legs = len(leg_boundaries) > 1

        logger.info(
            f"Detected leg boundaries: {leg_boundaries} | has_multiple_legs={has_multiple_legs}",
            extra={"voya_booking_reference": voya_booking_reference},
        )

        # Second pass: build segment data with leg labels
        for idx, segment in enumerate(trip_details.segments):
            # Determine current leg index
            current_leg_idx = 0
            for boundary_idx, boundary in enumerate(leg_boundaries):
                if idx >= boundary:
                    current_leg_idx = boundary_idx

            # Determine leg type label - only show on first segment of each leg
            leg_type = None
            if idx in leg_boundaries:
                if current_leg_idx == 0 and has_multiple_legs:
                    leg_type = "Outbound Flight"
                elif current_leg_idx == 1:
                    leg_type = "Return Flight"
                elif current_leg_idx > 1:
                    leg_type = f"Flight Leg {current_leg_idx + 1}"

            logger.info(
                f"Segment {idx}: {segment.departure_airport.iata_code} -> {segment.arrival_airport.iata_code} | "
                f"leg_idx={current_leg_idx} | leg_type={leg_type} | is_boundary={idx in leg_boundaries}",
                extra={"voya_booking_reference": voya_booking_reference},
            )

            # Get airline name with proper fallback
            airline_name = None
            if segment.marketing_airline and segment.marketing_airline.airline_name:
                airline_name = segment.marketing_airline.airline_name

            # If no airline name, extract from formatted flight number (e.g., "FI451" -> "FI")
            if not airline_name and segment.marketing_flight_number:
                airline_code = segment.marketing_flight_number.airline_prefix
                if airline_code:
                    airline_name = airline_code

            # Final fallback
            if not airline_name:
                airline_name = "Unknown Airline"

            segment_data = {
                "leg_type": leg_type,
                "origin": segment.departure_airport.iata_code,
                "destination": segment.arrival_airport.iata_code,
                "origin_city": segment.departure_airport.city_name
                or segment.departure_airport.iata_code,
                "destination_city": segment.arrival_airport.city_name
                or segment.arrival_airport.iata_code,
                "airline": airline_name,
                "flight_number": segment.marketing_flight_number.formatted_number,
                "departure_date": segment.departure_datetime.value.strftime("%d %B %Y"),
                "departure_time": segment.departure_datetime.value.strftime("%H:%M"),
                "arrival_date": segment.arrival_datetime.value.strftime("%d %B %Y"),
                "arrival_time": segment.arrival_datetime.value.strftime("%H:%M"),
                "cabin_class": segment.cabin_class.value
                if segment.cabin_class
                else "Unknown",
                "duration": f"{segment.flight_duration.total_minutes // 60}h {segment.flight_duration.total_minutes % 60}m",
            }
            context["segments"].append(segment_data)

        return context

    def _build_ticket_context(
        self,
        trip_details: "TripDetailsResponse",
        voya_booking_reference: str,
        ticket_numbers: list[str],
    ) -> dict:
        """Build template context for e-ticket PDF."""
        # Reuse booking context as base
        context = self._build_booking_context(
            trip_details, voya_booking_reference, has_tickets=True
        )

        # Update with ticket-specific info
        context["issue_date"] = datetime.now().strftime("%d %B %Y")

        # Ensure all passengers have ticket numbers
        for i, passenger in enumerate(context["passengers"]):
            if i < len(ticket_numbers):
                passenger["ticket_number"] = ticket_numbers[i]

        return context

    # ============================================================
    # INTERNAL METHODS - Text Processing
    # ============================================================

    @staticmethod
    def _contains_html(text: str | None) -> bool:
        """Check if text contains HTML tags.

        Args:
            text: Text to check

        Returns:
            True if text contains HTML tags, False otherwise
        """
        if not text or not isinstance(text, str):
            return False
        # Check for HTML tags (basic pattern matching)
        html_tag_pattern = re.compile(r"<[^>]+>")
        return bool(html_tag_pattern.search(text))

    @staticmethod
    def _process_cancellation_policy_text(text: str | None) -> str | None:
        """Process cancellation policy text for display.

        If text contains HTML tags, returns as-is.
        If text is plain text, converts newlines to <br> tags.

        Args:
            text: Cancellation policy text

        Returns:
            Processed text ready for HTML rendering
        """
        if not text:
            return None

        if FlightPDFGenerator._contains_html(text):
            # Contains HTML - return as-is (will be rendered with | safe filter)
            return text

        # Plain text - convert newlines to <br> tags and escape HTML
        from html import escape

        escaped_text = escape(text)
        return escaped_text.replace("\n", "<br>")

    # ============================================================
    # INTERNAL METHODS - Template & PDF Generation
    # ============================================================

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render Jinja2 template with context.

        Args:
            template_name: Name of template file (e.g., "booking_lcc.html")
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

    # ============================================================
    # INTERNAL METHODS - Validation
    # ============================================================

    def _validate_trip_details(
        self, trip_details: "TripDetailsResponse", voya_booking_reference: str
    ) -> None:
        """Validate that all required trip_details fields are present for PDF generation.

        Args:
            trip_details: Trip details from FlightLogic API
            voya_booking_reference: VOYA booking reference for error context

        Raises:
            ValueError: If any required field is missing or invalid
        """
        missing_fields = []

        # Validate required top-level fields
        if not trip_details.external_booking_reference:
            missing_fields.append("external_booking_reference")

        # Validate passengers array
        if not trip_details.passengers:
            missing_fields.append("passengers (empty list)")
        else:
            # Validate each passenger has required personal info
            for idx, passenger in enumerate(trip_details.passengers):
                if not passenger.personal_info:
                    missing_fields.append(f"passengers[{idx}].personal_info")
                elif not passenger.personal_info.name:
                    missing_fields.append(f"passengers[{idx}].personal_info.name")
                else:
                    if not passenger.personal_info.name.first_name:
                        missing_fields.append(
                            f"passengers[{idx}].personal_info.name.first_name"
                        )
                    if not passenger.personal_info.name.last_name:
                        missing_fields.append(
                            f"passengers[{idx}].personal_info.name.last_name"
                        )

                # Validate required date of birth
                if not passenger.personal_info.date_of_birth:
                    missing_fields.append(
                        f"passengers[{idx}].personal_info.date_of_birth"
                    )

        # Validate segments array
        if not trip_details.segments:
            missing_fields.append("segments (empty list)")
        else:
            for idx, segment in enumerate(trip_details.segments):
                # Validate required segment fields
                if not segment.departure_datetime:
                    missing_fields.append(f"segments[{idx}].departure_datetime")
                if not segment.arrival_datetime:
                    missing_fields.append(f"segments[{idx}].arrival_datetime")
                if not segment.departure_airport:
                    missing_fields.append(f"segments[{idx}].departure_airport")
                elif not segment.departure_airport.iata_code:
                    missing_fields.append(
                        f"segments[{idx}].departure_airport.iata_code"
                    )
                if not segment.arrival_airport:
                    missing_fields.append(f"segments[{idx}].arrival_airport")
                elif not segment.arrival_airport.iata_code:
                    missing_fields.append(f"segments[{idx}].arrival_airport.iata_code")

                # Validate airline PNR (critical for check-in)
                if not segment.airline_pnr:
                    missing_fields.append(f"segments[{idx}].airline_pnr")
                elif not segment.airline_pnr.pnr_code:
                    missing_fields.append(f"segments[{idx}].airline_pnr.pnr_code")

                # Validate flight duration
                if not segment.flight_duration:
                    missing_fields.append(f"segments[{idx}].flight_duration")

                # Log warnings for optional fields
                if (
                    not segment.marketing_airline
                    or not segment.marketing_airline.airline_name
                ):
                    logger.warning(
                        f"Optional field missing: segments[{idx}].marketing_airline.airline_name",
                        extra={"voya_booking_reference": voya_booking_reference},
                    )
                if not segment.marketing_flight_number:
                    logger.warning(
                        f"Optional field missing: segments[{idx}].marketing_flight_number",
                        extra={"voya_booking_reference": voya_booking_reference},
                    )

        # Validate pricing
        if not trip_details.pricing:
            missing_fields.append("pricing")
        elif not trip_details.pricing.fare_totals:
            missing_fields.append("pricing.fare_totals")
        else:
            if not trip_details.pricing.fare_totals.base_fare:
                missing_fields.append("pricing.fare_totals.base_fare")
            if not trip_details.pricing.fare_totals.total_tax:
                missing_fields.append("pricing.fare_totals.total_tax")
            if not trip_details.pricing.fare_totals.total_fare:
                missing_fields.append("pricing.fare_totals.total_fare")
            elif not trip_details.pricing.fare_totals.total_fare.currency:
                missing_fields.append("pricing.fare_totals.total_fare.currency")

        # If any required fields are missing, raise error
        if missing_fields:
            error_msg = (
                f"Cannot generate PDF for {voya_booking_reference}: "
                f"Missing required fields from FlightLogic API: {', '.join(missing_fields)}"
            )
            logger.error(
                error_msg, extra={"voya_booking_reference": voya_booking_reference}
            )
            raise ValueError(error_msg)

        logger.info(
            f"Trip details validation passed for {voya_booking_reference}",
            extra={
                "voya_booking_reference": voya_booking_reference,
                "passenger_count": len(trip_details.passengers),
                "segment_count": len(trip_details.segments),
            },
        )
