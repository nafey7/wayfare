"""Simple script to generate sample PDFs without complex imports."""

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa


def generate_pdf_from_html(html_content: str) -> bytes:
    """Convert HTML to PDF using xhtml2pdf."""
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(src=html_content, dest=pdf_buffer, encoding="UTF-8")

    if pisa_status.err:
        raise Exception(f"PDF generation failed with error code: {pisa_status.err}")

    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes


def save_pdf(pdf_bytes: bytes, filename: str) -> Path:
    """Save PDF to logs/pdfs/ directory."""
    pdf_dir = Path(__file__).parent / "logs" / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = pdf_dir / f"{filename}_{timestamp}.pdf"
    file_path.write_bytes(pdf_bytes)

    return file_path


def generate_sample_pdfs():
    """Generate all three PDF types for visual inspection."""

    print("Generating sample PDFs...\n")

    # Setup Jinja2
    template_dir = (
        Path(__file__).parent
        / "app"
        / "domains"
        / "email"
        / "attachments"
        / "templates"
    )
    jinja_env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    # Sample data for LCC booking (with tickets)
    lcc_context = {
        "generated_date": datetime.now().strftime("%d %B %Y, %H:%M"),
        "voya_booking_reference": "VOYA-2025-00001",
        "pnr": "ABC123",
        "external_reference": "FL123456",
        "booking_date": datetime.now().strftime("%d %B %Y"),
        "currency": "EUR",
        "base_fare": "350.00",
        "taxes": "89.50",
        "total_fare": "439.50",
        "passengers": [
            {
                "title": "Mr",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "15 May 1990",
                "ticket_number": "1234567890123",
                "passport_number": "P1234567",
                "passport_country": "NLD",
            },
            {
                "title": "Mrs",
                "first_name": "Jane",
                "last_name": "Doe",
                "date_of_birth": "20 August 1992",
                "ticket_number": "1234567890124",
                "passport_number": "P7654321",
                "passport_country": "NLD",
            },
        ],
        "segments": [
            {
                "origin": "AMS",
                "destination": "BCN",
                "origin_city": "Amsterdam",
                "destination_city": "Barcelona",
                "airline": "KLM Royal Dutch Airlines",
                "flight_number": "1234",
                "departure_date": (datetime.now() + timedelta(days=30)).strftime(
                    "%d %B %Y"
                ),
                "departure_time": "10:00",
                "arrival_date": (datetime.now() + timedelta(days=30)).strftime(
                    "%d %B %Y"
                ),
                "arrival_time": "12:00",
                "cabin_class": "Economy",
                "duration": "2h 0m",
            },
            {
                "origin": "BCN",
                "destination": "AMS",
                "origin_city": "Barcelona",
                "destination_city": "Amsterdam",
                "airline": "KLM Royal Dutch Airlines",
                "flight_number": "5678",
                "departure_date": (datetime.now() + timedelta(days=37)).strftime(
                    "%d %B %Y"
                ),
                "departure_time": "15:00",
                "arrival_date": (datetime.now() + timedelta(days=37)).strftime(
                    "%d %B %Y"
                ),
                "arrival_time": "17:00",
                "cabin_class": "Economy",
                "duration": "2h 0m",
            },
        ],
    }

    # Sample data for GDS booking (no tickets)
    gds_context = {
        "generated_date": datetime.now().strftime("%d %B %Y, %H:%M"),
        "voya_booking_reference": "VOYA-2025-00002",
        "pnr": "XYZ789",
        "external_reference": "FL789012",
        "booking_date": datetime.now().strftime("%d %B %Y"),
        "payment_deadline": "24 hours",
        "currency": "EUR",
        "base_fare": "3800.00",
        "taxes": "650.00",
        "total_fare": "4450.00",
        "passengers": [
            {
                "title": "Ms",
                "first_name": "Sarah",
                "last_name": "Smith",
                "date_of_birth": "10 March 1995",
                "passport_number": "N1234567",
                "passport_country": "USA",
            },
        ],
        "segments": [
            {
                "origin": "LHR",
                "destination": "JFK",
                "origin_city": "London",
                "destination_city": "New York",
                "airline": "British Airways",
                "flight_number": "117",
                "departure_date": (datetime.now() + timedelta(days=45)).strftime(
                    "%d %B %Y"
                ),
                "departure_time": "09:30",
                "arrival_date": (datetime.now() + timedelta(days=45)).strftime(
                    "%d %B %Y"
                ),
                "arrival_time": "17:30",
                "cabin_class": "Business",
                "duration": "8h 0m",
            },
        ],
    }

    # Sample data for ticket (after GDS payment)
    ticket_context = {
        **gds_context,
        "issue_date": datetime.now().strftime("%d %B %Y"),
        "passengers": [
            {
                "title": "Ms",
                "first_name": "Sarah",
                "last_name": "Smith",
                "date_of_birth": "10 March 1995",
                "ticket_number": "9876543210123",
                "passport_number": "N1234567",
                "passport_country": "USA",
                "passport_expiry": "15 June 2030",
            },
        ],
        "segments": [
            {
                "origin": "LHR",
                "destination": "JFK",
                "origin_city": "London",
                "destination_city": "New York",
                "airline": "British Airways",
                "flight_number": "117",
                "departure_date": (datetime.now() + timedelta(days=45)).strftime(
                    "%d %B %Y"
                ),
                "departure_time": "09:30",
                "arrival_date": (datetime.now() + timedelta(days=45)).strftime(
                    "%d %B %Y"
                ),
                "arrival_time": "17:30",
                "cabin_class": "Business",
                "booking_class": "J",
                "duration": "8h 0m",
                "baggage_allowance": "2 pieces, 32kg each",
            },
        ],
    }

    # Generate LCC PDF
    print("Generating LCC booking PDF (with tickets)...")
    lcc_template = jinja_env.get_template("booking_lcc.html")
    lcc_html = lcc_template.render(**lcc_context)
    lcc_pdf = generate_pdf_from_html(lcc_html)
    lcc_path = save_pdf(lcc_pdf, "booking_VOYA-2025-00001")
    print(f"OK - LCC PDF: {len(lcc_pdf)} bytes")
    print(f"   Saved to: {lcc_path}\n")

    # Generate GDS PDF
    print("Generating GDS booking PDF (payment required)...")
    gds_template = jinja_env.get_template("booking_gds.html")
    gds_html = gds_template.render(**gds_context)
    gds_pdf = generate_pdf_from_html(gds_html)
    gds_path = save_pdf(gds_pdf, "booking_VOYA-2025-00002")
    print(f"OK - GDS PDF: {len(gds_pdf)} bytes")
    print(f"   Saved to: {gds_path}\n")

    # Generate Ticket PDF
    print("Generating e-ticket PDF (after payment)...")
    ticket_template = jinja_env.get_template("ticket.html")
    ticket_html = ticket_template.render(**ticket_context)
    ticket_pdf = generate_pdf_from_html(ticket_html)
    ticket_path = save_pdf(ticket_pdf, "ticket_VOYA-2025-00002")
    print(f"OK - Ticket PDF: {len(ticket_pdf)} bytes")
    print(f"   Saved to: {ticket_path}\n")

    print("=" * 70)
    print(f"All PDFs saved in: {lcc_path.parent}")
    print("=" * 70)
    print("\nAll PDFs generated successfully! You can now view them.")


if __name__ == "__main__":
    generate_sample_pdfs()
