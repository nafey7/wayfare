"""PDF generator for GDS bookings using revalidate response and booking request data."""

import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.core.config import settings

from .schemas import PDFMetadata

if TYPE_CHECKING:
    from app.domains.flight.schemas import (
        FlightBookingRequest,
        FlightRevalidateResponse,
    )

logger = logging.getLogger(__name__)


async def generate_booking_pdf_from_context(
    revalidate_response: "FlightRevalidateResponse",
    booking_request: "FlightBookingRequest",
    voya_booking_reference: str,
) -> tuple[bytes, PDFMetadata]:
    """Generate booking confirmation PDF from revalidate response and booking request.

    Used for GDS bookings where full trip_details is not yet available.

    Args:
        revalidate_response: FlightRevalidateResponse with fare itinerary details
        booking_request: FlightBookingRequest with passenger information
        voya_booking_reference: VOYA booking reference (e.g., VOYA-FQJUJ89DMK)

    Returns:
        Tuple of (pdf_bytes, metadata)
    """
    logger.info(f"Generating GDS booking PDF from context for {voya_booking_reference}")

    # Setup Jinja2 environment
    template_dir = Path(__file__).parent / "templates"
    jinja_env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Extract flight itinerary from revalidate response
    fare_itinerary = (
        revalidate_response.validated_fare_itineraries[0]
        if revalidate_response.validated_fare_itineraries
        else None
    )
    if not fare_itinerary:
        raise ValueError("No fare itinerary found in revalidate response")

    # Build context for PDF template
    context = _build_context_from_booking_data(
        fare_itinerary=fare_itinerary,
        booking_request=booking_request,
        voya_booking_reference=voya_booking_reference,
    )

    # Render HTML from Jinja2 template (use GDS template - no tickets yet)
    template = jinja_env.get_template("booking_gds.html")
    html_content = template.render(**context)

    # Generate PDF from HTML
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_content.encode("utf-8")), dest=pdf_buffer)

    if pisa_status.err:
        raise ValueError(f"PDF generation failed with {pisa_status.err} errors")

    pdf_bytes = pdf_buffer.getvalue()

    # Save to logs/pdfs/
    file_path = _save_pdf(pdf_bytes, voya_booking_reference)

    # Create metadata
    metadata = PDFMetadata(
        voya_booking_reference=voya_booking_reference,
        external_reference=None,  # Not available yet
        pdf_type="booking",
        file_size_bytes=len(pdf_bytes),
        file_path=str(file_path) if file_path else None,
    )

    logger.info(f"GDS booking PDF generated from context: {len(pdf_bytes)} bytes")

    return pdf_bytes, metadata


def _build_context_from_booking_data(
    fare_itinerary: Any,
    booking_request: "FlightBookingRequest",
    voya_booking_reference: str,
) -> dict[str, Any]:
    """Build template context from revalidate and booking data.

    Maps data to match the structure expected by booking_gds.html template.
    """

    # Current datetime for generated_date and booking_date
    now = datetime.now()
    generated_date = now.strftime("%d %B %Y, %H:%M")
    booking_date = now.strftime("%d %B %Y, %H:%M")

    # Payment deadline: 24 hours from now
    payment_deadline_dt = now + timedelta(hours=24)
    payment_deadline = payment_deadline_dt.strftime("%d %B %Y, %H:%M")

    # Extract PNR - note: for GDS bookings PNR is not available until after ticketing
    # We use a placeholder for now
    pnr = "PENDING"  # PNR will be assigned after payment and ticketing

    # Extract pricing from ValidatedFareItinerary
    pricing = fare_itinerary.updated_pricing.validated_fare_totals
    currency = pricing.total_fare.currency
    base_fare = f"{float(pricing.base_fare.amount):.2f}"
    taxes = f"{float(pricing.total_tax.amount):.2f}"
    total_fare = f"{float(pricing.total_fare.amount):.2f}"

    # Extract passengers from booking request - format for template
    passengers = []

    if booking_request.passenger_groups.adults:
        for adult in booking_request.passenger_groups.adults:
            name = adult.personal_info.name
            passenger_data = {
                "type": "Adult",
                "title": getattr(name, "title", "Mr"),
                "first_name": getattr(name, "first_name", ""),
                "last_name": getattr(name, "last_name", ""),
                "date_of_birth": adult.personal_info.date_of_birth
                if adult.personal_info.date_of_birth
                else "Not provided",
            }

            # Add passport info if available
            if adult.travel_documents and adult.travel_documents.passport_number:
                passenger_data["passport_number"] = (
                    adult.travel_documents.passport_number
                )
                passenger_data["passport_country"] = (
                    adult.travel_documents.passport_country or "Not specified"
                )

            passengers.append(passenger_data)

    if booking_request.passenger_groups.children:
        for child in booking_request.passenger_groups.children:
            name = child.personal_info.name
            passenger_data = {
                "type": "Child",
                "title": getattr(name, "title", "Miss"),
                "first_name": getattr(name, "first_name", ""),
                "last_name": getattr(name, "last_name", ""),
                "date_of_birth": child.personal_info.date_of_birth
                if child.personal_info.date_of_birth
                else "Not provided",
            }

            if child.travel_documents and child.travel_documents.passport_number:
                passenger_data["passport_number"] = (
                    child.travel_documents.passport_number
                )
                passenger_data["passport_country"] = (
                    child.travel_documents.passport_country or "Not specified"
                )

            passengers.append(passenger_data)

    if booking_request.passenger_groups.infants:
        for infant in booking_request.passenger_groups.infants:
            name = infant.personal_info.name
            passenger_data = {
                "type": "Infant",
                "title": getattr(name, "title", "Miss"),
                "first_name": getattr(name, "first_name", ""),
                "last_name": getattr(name, "last_name", ""),
                "date_of_birth": infant.personal_info.date_of_birth
                if infant.personal_info.date_of_birth
                else "Not provided",
            }

            if infant.travel_documents and infant.travel_documents.passport_number:
                passenger_data["passport_number"] = (
                    infant.travel_documents.passport_number
                )
                passenger_data["passport_country"] = (
                    infant.travel_documents.passport_country or "Not specified"
                )

            passengers.append(passenger_data)

    # Extract flight segments - format for template (template expects "segments" not "flight_segments")
    # IMPORTANT: Process ALL flight legs (outbound + return for round trips)
    segments = []
    total_legs = len(fare_itinerary.flight_legs)

    for leg_idx, flight_leg in enumerate(fare_itinerary.flight_legs):
        # Determine leg type for display
        leg_type = None
        if total_legs > 1:
            # Multi-leg journey (Return or Circle)
            if leg_idx == 0:
                leg_type = "Outbound Flight"
            elif leg_idx == 1:
                leg_type = "Return Flight"
            else:
                leg_type = f"Flight Leg {leg_idx + 1}"
        # For single leg (OneWay), leg_type stays None and won't be displayed

        for segment_idx, segment in enumerate(flight_leg.flight_segments):
            # Get airline name with fallback
            airline_name = "Unknown Airline"
            if segment.marketing_airline and segment.marketing_airline.airline_name:
                airline_name = segment.marketing_airline.airline_name
            elif segment.marketing_airline and segment.marketing_airline.iata_code:
                airline_name = segment.marketing_airline.iata_code

            # Get flight number with fallback
            flight_number = "N/A"
            if segment.marketing_flight_number:
                if hasattr(segment.marketing_flight_number, "formatted_number"):
                    flight_number = segment.marketing_flight_number.formatted_number
                elif hasattr(segment.marketing_flight_number, "flight_number"):
                    flight_number = segment.marketing_flight_number.flight_number

            # Format datetime objects
            dep_dt = (
                segment.departure_datetime.value if segment.departure_datetime else now
            )
            arr_dt = segment.arrival_datetime.value if segment.arrival_datetime else now

            segment_data = {
                "leg_type": leg_type
                if segment_idx == 0
                else None,  # Only show leg header on first segment of leg
                "origin": segment.departure_airport.iata_code,
                "destination": segment.arrival_airport.iata_code,
                "origin_city": segment.departure_airport.city_name
                or segment.departure_airport.iata_code,
                "destination_city": segment.arrival_airport.city_name
                or segment.arrival_airport.iata_code,
                "airline": airline_name,
                "flight_number": flight_number,
                "departure_date": dep_dt.strftime("%d %B %Y"),
                "departure_time": dep_dt.strftime("%H:%M"),
                "arrival_date": arr_dt.strftime("%d %B %Y"),
                "arrival_time": arr_dt.strftime("%H:%M"),
                "cabin_class": segment.cabin_class.value
                if segment.cabin_class
                else "Economy",
                "duration": f"{segment.flight_duration.total_minutes // 60}h {segment.flight_duration.total_minutes % 60}m"
                if segment.flight_duration
                else "N/A",
            }
            segments.append(segment_data)

    # Build complete context matching booking_gds.html template expectations
    return {
        "generated_date": generated_date,
        "voya_booking_reference": voya_booking_reference,
        "pnr": pnr,
        "external_reference": None,  # Not available yet for GDS
        "booking_date": booking_date,
        "payment_deadline": payment_deadline,
        "currency": currency,
        "base_fare": base_fare,
        "taxes": taxes,
        "total_fare": total_fare,
        "passengers": passengers,
        "segments": segments,  # Template expects "segments" not "flight_segments"
        "fare_rules": [],  # Not available in revalidate response - will show placeholder message
    }


def _save_pdf(pdf_bytes: bytes, voya_booking_reference: str) -> Path | None:
    """Save PDF to logs/pdfs/ directory."""
    try:
        # Create directory if doesn't exist
        pdf_dir = Path(settings.PDF_OUTPUT_DIR)
        pdf_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"booking_{voya_booking_reference}_{timestamp}.pdf"
        file_path = pdf_dir / filename

        # Save PDF
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"PDF saved: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to save PDF: {e}")
        return None
