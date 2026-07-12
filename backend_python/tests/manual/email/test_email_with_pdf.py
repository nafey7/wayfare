"""Test script for email with PDF attachment - verifies complete flow."""
# ruff: noqa

import asyncio
from datetime import UTC, datetime

from app.domains.email import EmailService, EmailType


# Mock classes from test_pdf_generation.py
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
        self.fare_type = type(
            "obj", (object,), {"value": "WebFare" if has_tickets else "Public"}
        )()


async def test_email_with_pdf():
    """Test sending email with PDF attachment via EmailService."""
    print("[START] Testing Email Service with PDF Attachment\n")
    print("=" * 70)

    # Test 1: GDS Booking Email (no tickets, payment required)
    print("\n[TEST 1] GDS Booking Email with PDF")
    print("-" * 70)
    try:
        trip_details_gds = MockTripDetails(has_tickets=False)

        result = await EmailService.send_email(
            email_type=EmailType.BOOKING_CONFIRMATION,
            recipient_email="test@example.com",
            context={
                "user_name": "John",
                "tickets_issued": False,
                "voya_booking_reference": "VOYA-2025-00001",
                "external_booking_reference": "FL-GDS-12345",
                "booking_details": {},
            },
            trip_details=trip_details_gds,
        )

        print(f"[RESULT] Email send result: {result}")
        print("[INFO] Expected: booking_gds.html PDF should be generated and attached")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    # Test 2: LCC Booking Email (with tickets)
    print("\n[TEST 2] LCC Booking Email with PDF")
    print("-" * 70)
    try:
        trip_details_lcc = MockTripDetails(has_tickets=True)

        result = await EmailService.send_email(
            email_type=EmailType.BOOKING_CONFIRMATION,
            recipient_email="test@example.com",
            context={
                "user_name": "John",
                "tickets_issued": True,
                "voya_booking_reference": "VOYA-2025-00002",
                "external_booking_reference": "FL-LCC-67890",
                "booking_details": {},
            },
            trip_details=trip_details_lcc,
        )

        print(f"[RESULT] Email send result: {result}")
        print("[INFO] Expected: booking_lcc.html PDF should be generated and attached")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Ticket Issued Email (e-ticket PDF)
    print("\n[TEST 3] Ticket Issued Email with PDF")
    print("-" * 70)
    try:
        trip_details_ticket = MockTripDetails(has_tickets=True)

        result = await EmailService.send_email(
            email_type=EmailType.TICKET_ISSUED,
            recipient_email="test@example.com",
            context={
                "user_name": "John",
                "voya_booking_reference": "VOYA-2025-00003",
                "ticket_numbers": ["074-1234567890", "074-0987654321"],
            },
            trip_details=trip_details_ticket,
        )

        print(f"[RESULT] Email send result: {result}")
        print("[INFO] Expected: ticket.html PDF should be generated and attached")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("[COMPLETE] Email Service Tests Complete!")
    print("\n[NEXT STEPS]:")
    print("  1. Check MailHog at http://localhost:8025 for emails")
    print("  2. Verify PDFs are attached to emails")
    print("  3. Download and open PDFs to verify content")
    print("  4. Check logs/pdfs/ directory for generated PDFs")


if __name__ == "__main__":
    asyncio.run(test_email_with_pdf())
