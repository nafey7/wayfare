"""Test script for PDF generation - verifies templates and WeasyPrint integration."""
# ruff: noqa

import asyncio
from datetime import UTC, datetime
from pathlib import Path


# Mock flight data structures
class MockName:
    def __init__(self):
        self.title = "Mr"
        self.first_name = "John"
        self.last_name = "Doe"


class MockPersonalInfo:
    def __init__(self, has_ticket=False):
        self.name = MockName()
        self.date_of_birth = datetime(1990, 5, 15)


class MockPassenger:
    def __init__(self, has_ticket=False):
        self.personal_info = MockPersonalInfo()
        self.e_ticket_number = "074-1234567890" if has_ticket else None


class MockLocation:
    def __init__(self, code, city):
        self.iata_code = code
        self.city_name = city


class MockAirline:
    def __init__(self):
        self.name = "KLM Royal Dutch Airlines"


class MockSegment:
    def __init__(self):
        self.origin = MockLocation("AMS", "Amsterdam")
        self.destination = MockLocation("JFK", "New York")
        self.marketing_airline = MockAirline()
        self.flight_number = "KL641"
        self.departure_datetime = datetime.now(UTC).replace(hour=10, minute=30)
        self.arrival_datetime = datetime.now(UTC).replace(hour=13, minute=45)
        self.cabin_class = "Economy"
        self.duration = 495  # 8h 15min


class MockTripDetails:
    def __init__(self, has_tickets=False):
        self.external_booking_reference = "FL-ABC123"
        self.passengers = [
            MockPassenger(has_ticket=has_tickets),
            MockPassenger(has_ticket=has_tickets),
        ]
        self.segments = [MockSegment()]


async def test_pdf_generation():
    """Test PDF generation for all three templates."""
    from app.domains.email.attachments import FlightPDFGenerator

    print("Starting PDF Generation Tests\n")
    print("=" * 60)

    # Initialize generator
    generator = FlightPDFGenerator()
    print("[OK] PDF Generator initialized")

    # Test 1: LCC Booking (with tickets)
    print("\n[TEST 1] LCC Booking PDF (booking_lcc.html)")
    print("-" * 60)
    try:
        trip_details_lcc = MockTripDetails(has_tickets=True)
        pdf_bytes, metadata = await generator.generate_booking_confirmation(
            trip_details=trip_details_lcc,
            voya_booking_reference="VOYA-2025-00001",
            fare_type="WebFare",
        )

        print("[OK] PDF generated successfully")
        print(f"  - Size: {len(pdf_bytes)} bytes ({len(pdf_bytes) // 1024} KB)")
        print(f"  - Type: {metadata.pdf_type}")
        print(f"  - Saved to: {metadata.file_path}")
        print(f"  - Reference: {metadata.voya_booking_reference}")

        # Verify file exists
        if metadata.file_path and Path(metadata.file_path).exists():
            print("[OK] PDF file exists on disk")
        else:
            print("[ERROR] PDF file not found!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    # Test 2: GDS Booking (no tickets yet)
    print("\n[TEST 2] GDS Booking PDF (booking_gds.html)")
    print("-" * 60)
    try:
        trip_details_gds = MockTripDetails(has_tickets=False)
        pdf_bytes, metadata = await generator.generate_booking_confirmation(
            trip_details=trip_details_gds,
            voya_booking_reference="VOYA-2025-00002",
            fare_type="Public",
        )

        print("[OK] PDF generated successfully")
        print(f"  - Size: {len(pdf_bytes)} bytes ({len(pdf_bytes) // 1024} KB)")
        print(f"  - Type: {metadata.pdf_type}")
        print(f"  - Saved to: {metadata.file_path}")
        print(f"  - Reference: {metadata.voya_booking_reference}")

        if metadata.file_path and Path(metadata.file_path).exists():
            print("[OK] PDF file exists on disk")
        else:
            print("[ERROR] PDF file not found!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    # Test 3: E-Ticket (after ticket issuance)
    print("\n[TEST 3] E-Ticket PDF (ticket.html)")
    print("-" * 60)
    try:
        trip_details_ticket = MockTripDetails(has_tickets=True)
        ticket_numbers = ["074-1234567890", "074-0987654321"]

        pdf_bytes, metadata = await generator.generate_ticket_document(
            trip_details=trip_details_ticket,
            ticket_numbers=ticket_numbers,
            voya_booking_reference="VOYA-2025-00002",
        )

        print("[OK] PDF generated successfully")
        print(f"  - Size: {len(pdf_bytes)} bytes ({len(pdf_bytes) // 1024} KB)")
        print(f"  - Type: {metadata.pdf_type}")
        print(f"  - Saved to: {metadata.file_path}")
        print(f"  - Reference: {metadata.voya_booking_reference}")

        if metadata.file_path and Path(metadata.file_path).exists():
            print("[OK] PDF file exists on disk")
        else:
            print("[ERROR] PDF file not found!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    # Check PDF directory
    print("\n[PDF DIRECTORY] Contents")
    print("-" * 60)
    from app.core.config import settings

    pdf_dir = Path(settings.PDF_OUTPUT_DIR)

    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        print(f"[OK] PDF directory exists: {pdf_dir}")
        print(f"[OK] Total PDF files: {len(pdf_files)}")

        for pdf_file in pdf_files:
            size_kb = pdf_file.stat().st_size // 1024
            print(f"  - {pdf_file.name} ({size_kb} KB)")
    else:
        print(f"[ERROR] PDF directory does not exist: {pdf_dir}")

    print("\n" + "=" * 60)
    print("[COMPLETE] PDF Generation Tests Complete!")
    print("\n[NEXT STEPS]:")
    print("  1. Open the PDF files in logs/pdfs/ to verify content")
    print("  2. Check that templates render correctly")
    print("  3. Verify all data is displayed properly")


if __name__ == "__main__":
    # Run async test
    asyncio.run(test_pdf_generation())
