"""Test script to generate sample PDFs for visual inspection."""
# ruff: noqa

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to allow direct imports
sys.path.insert(0, str(Path(__file__).parent))

# Direct imports to avoid circular dependencies
from app.domains.email.attachments.pdf_generator import FlightPDFGenerator


async def generate_sample_pdfs():
    """Generate sample PDFs for both LCC and GDS bookings."""

    print("🎨 Generating sample PDFs...")

    # Create PDF generator
    pdf_gen = FlightPDFGenerator()

    # Create sample trip details for LCC (with tickets)
    lcc_trip = TripDetailsResponse(
        external_booking_reference="FL123456",
        passengers=[
            PassengerInfo(
                personal_info=PersonalInfo(
                    name=NameInfo(title="Mr", first_name="John", last_name="Doe"),
                    date_of_birth=datetime(1990, 5, 15).date(),
                ),
                e_ticket_number="1234567890123",
            ),
            PassengerInfo(
                personal_info=PersonalInfo(
                    name=NameInfo(title="Mrs", first_name="Jane", last_name="Doe"),
                    date_of_birth=datetime(1992, 8, 20).date(),
                ),
                e_ticket_number="1234567890124",
            ),
        ],
        segments=[
            FlightSegment(
                origin=LocationInfo(
                    iata_code="AMS", city_name="Amsterdam", country_code="NL"
                ),
                destination=LocationInfo(
                    iata_code="BCN", city_name="Barcelona", country_code="ES"
                ),
                marketing_airline=AirlineInfo(
                    iata_code="KL", name="KLM Royal Dutch Airlines"
                ),
                flight_number="1234",
                departure_datetime=datetime.now() + timedelta(days=30),
                arrival_datetime=datetime.now() + timedelta(days=30, hours=2),
                cabin_class="Economy",
                duration=120,
            ),
            FlightSegment(
                origin=LocationInfo(
                    iata_code="BCN", city_name="Barcelona", country_code="ES"
                ),
                destination=LocationInfo(
                    iata_code="AMS", city_name="Amsterdam", country_code="NL"
                ),
                marketing_airline=AirlineInfo(
                    iata_code="KL", name="KLM Royal Dutch Airlines"
                ),
                flight_number="5678",
                departure_datetime=datetime.now() + timedelta(days=37),
                arrival_datetime=datetime.now() + timedelta(days=37, hours=2),
                cabin_class="Economy",
                duration=120,
            ),
        ],
    )

    # Create sample trip details for GDS (no tickets yet)
    gds_trip = TripDetailsResponse(
        external_booking_reference="FL789012",
        passengers=[
            PassengerInfo(
                personal_info=PersonalInfo(
                    name=NameInfo(title="Ms", first_name="Sarah", last_name="Smith"),
                    date_of_birth=datetime(1995, 3, 10).date(),
                ),
            ),
        ],
        segments=[
            FlightSegment(
                origin=LocationInfo(
                    iata_code="LHR", city_name="London", country_code="GB"
                ),
                destination=LocationInfo(
                    iata_code="JFK", city_name="New York", country_code="US"
                ),
                marketing_airline=AirlineInfo(iata_code="BA", name="British Airways"),
                flight_number="117",
                departure_datetime=datetime.now() + timedelta(days=45),
                arrival_datetime=datetime.now() + timedelta(days=45, hours=8),
                cabin_class="Business",
                duration=480,
            ),
        ],
    )

    # Generate LCC booking PDF (with tickets)
    print("\n📄 Generating LCC booking PDF (with tickets)...")
    lcc_pdf_bytes, lcc_metadata = await pdf_gen.generate_booking_confirmation(
        trip_details=lcc_trip,
        voya_booking_reference="VOYA-2025-00001",
        fare_type="WebFare",
    )
    print(f"✅ LCC PDF generated: {lcc_metadata.file_size_bytes} bytes")
    print(f"   Saved to: {lcc_metadata.file_path}")

    # Generate GDS booking PDF (no tickets)
    print("\n📄 Generating GDS booking PDF (payment required)...")
    gds_pdf_bytes, gds_metadata = await pdf_gen.generate_booking_confirmation(
        trip_details=gds_trip,
        voya_booking_reference="VOYA-2025-00002",
        fare_type="Public",
    )
    print(f"✅ GDS PDF generated: {gds_metadata.file_size_bytes} bytes")
    print(f"   Saved to: {gds_metadata.file_path}")

    # Generate e-ticket PDF (separate ticket issuance)
    print("\n📄 Generating e-ticket PDF (after payment)...")
    ticket_pdf_bytes, ticket_metadata = await pdf_gen.generate_ticket_document(
        trip_details=gds_trip,
        ticket_numbers=["9876543210123"],
        voya_booking_reference="VOYA-2025-00002",
    )
    print(f"✅ Ticket PDF generated: {ticket_metadata.file_size_bytes} bytes")
    print(f"   Saved to: {ticket_metadata.file_path}")

    print("\n" + "=" * 60)
    print(
        "📁 PDFs saved in: C:\\Users\\marij\\dev\\MyVoya\\backend_python\\logs\\pdfs\\"
    )
    print("=" * 60)
    print("\n✨ All PDFs generated successfully! You can now view them.")


if __name__ == "__main__":
    asyncio.run(generate_sample_pdfs())
