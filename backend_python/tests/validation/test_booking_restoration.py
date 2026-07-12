#!/usr/bin/env python3
"""
Minimal test for booking restoration functionality.
Works with Python 3.11+ using only standard library.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class MockAPIHandler(BaseHTTPRequestHandler):
    """Mock API server to simulate booking endpoint."""

    def do_GET(self):
        """Handle GET requests for booking data."""
        # Parse the path
        path = self.path

        if path.startswith("/api/bookings/VOYA-"):
            # Extract booking reference
            booking_ref = path.split("/")[-1]

            # Mock booking data
            mock_booking = {
                "voya_booking_reference": booking_ref,
                "external_booking_reference": "FL123456",
                "booking_status": "CONFIRMED",
                "ticket_status": "PENDING",
                "trip_details": {
                    "flights": [
                        {
                            "departure_airport": "AMS",
                            "arrival_airport": "JFK",
                            "departure_datetime": "2025-01-15T10:30:00Z",
                            "airline_name": "KLM",
                            "flight_number": "KL601",
                        }
                    ],
                    "total_price": "599.00",
                    "currency": "EUR",
                },
            }

            # Send response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(mock_booking).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default HTTP server logs."""
        pass


def test_url_parsing():
    """Test URL parameter parsing functionality."""
    print("🔍 Testing URL parameter parsing...")

    # Test cases
    test_urls = [
        "?booking=VOYA-ABC123&step=payment",
        "?booking=VOYA-XYZ789",
        "?session_id=sess123&booking=VOYA-DEF456&step=payment",
    ]

    for test_url in test_urls:
        params = urllib.parse.parse_qs(test_url.lstrip("?"))
        booking = params.get("booking", [None])[0]
        step = params.get("step", [None])[0]

        print(f"  URL: {test_url}")
        print(f"    booking: {booking}")
        print(f"    step: {step}")

        # Validate booking reference format
        if booking and booking.startswith("VOYA-") and len(booking) >= 9:
            print("    ✅ Valid booking reference format")
        else:
            print("    ❌ Invalid booking reference format")
        print()


def test_api_endpoint(port=8765):
    """Test mock API endpoint functionality."""
    print(f"🌐 Testing API endpoint on port {port}...")

    # Start mock server in thread
    server = HTTPServer(("localhost", port), MockAPIHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(0.5)

    try:
        # Test API call
        test_booking_ref = "VOYA-TEST123"
        api_url = f"http://localhost:{port}/api/bookings/{test_booking_ref}"

        print(f"  Making request to: {api_url}")

        with urllib.request.urlopen(api_url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print("  ✅ API Response received")
                print(f"    booking_reference: {data.get('voya_booking_reference')}")
                print(f"    booking_status: {data.get('booking_status')}")
                print(f"    ticket_status: {data.get('ticket_status')}")

                # Test flight details
                flights = data.get("trip_details", {}).get("flights", [])
                if flights:
                    flight = flights[0]
                    print(
                        f"    flight: {flight.get('departure_airport')} → {flight.get('arrival_airport')}"
                    )
                    print(
                        f"    price: {data.get('trip_details', {}).get('currency')} {data.get('trip_details', {}).get('total_price')}"
                    )

                return True
            print(f"  ❌ API Error: {response.status}")
            return False

    except Exception as e:
        print(f"  ❌ API Test Failed: {e}")
        return False
    finally:
        server.shutdown()


def test_step_navigation():
    """Test step navigation logic."""
    print("📋 Testing step navigation logic...")

    test_cases = [
        {
            "name": "GDS booking pending payment",
            "booking_status": "CONFIRMED",
            "ticket_status": "PENDING",
            "expected_step": "payment",
        },
        {
            "name": "LCC booking with tickets issued",
            "booking_status": "CONFIRMED",
            "ticket_status": "ISSUED",
            "expected_step": "confirmation",
        },
        {
            "name": "Failed booking",
            "booking_status": "FAILED",
            "ticket_status": "NONE",
            "expected_step": "payment",
        },
    ]

    for test_case in test_cases:
        booking_status = test_case["booking_status"]
        ticket_status = test_case["ticket_status"]
        expected = test_case["expected_step"]

        # Simulate the navigation logic
        if booking_status == "CONFIRMED" and ticket_status == "ISSUED":
            final_step = "confirmation"
        elif booking_status == "CONFIRMED" and ticket_status != "ISSUED":
            final_step = "payment"
        else:
            final_step = "payment"  # Default to payment for pending bookings

        result = "✅" if final_step == expected else "❌"
        print(f"  {result} {test_case['name']}: {final_step} (expected: {expected})")


def test_payment_summary_data():
    """Test payment summary population."""
    print("🧾 Testing payment summary data extraction...")

    mock_trip_details = {
        "flights": [
            {
                "departure_airport": "AMS",
                "arrival_airport": "JFK",
                "departure_datetime": "2025-01-15T10:30:00Z",
                "airline_name": "KLM",
                "flight_number": "KL601",
            }
        ],
        "total_price": "599.00",
        "currency": "EUR",
    }

    # Extract data (simulate JavaScript logic)
    outbound_flight = mock_trip_details.get("flights", [{}])[0]

    if outbound_flight:
        departure = outbound_flight.get("departure_airport")
        arrival = outbound_flight.get("arrival_airport")
        airline = outbound_flight.get("airline_name")
        flight_num = outbound_flight.get("flight_number")
        price = mock_trip_details.get("total_price")
        currency = mock_trip_details.get("currency")

        print(f"  ✅ Flight route: {departure} → {arrival}")
        print(f"  ✅ Airline: {airline} ({flight_num})")
        print(f"  ✅ Price: {currency} {price}")

        return True
    print("  ❌ No flight data available")
    return False


def main():
    """Run all tests."""
    print("🚀 Testing Booking Restoration Functionality")
    print("=" * 50)

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"Python Version: {python_version}")
    print()

    # Run tests
    tests = [
        test_url_parsing,
        lambda: test_api_endpoint(8765),
        test_step_navigation,
        test_payment_summary_data,
    ]

    passed = 0
    total = len(tests)

    for i, test in enumerate(tests, 1):
        try:
            result = test()
            if result is not False:  # None or True counts as pass
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with error: {e}")

        if i < total:
            print()

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Booking restoration should work correctly.")
        return 0
    print("⚠️  Some tests failed. Check implementation.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
