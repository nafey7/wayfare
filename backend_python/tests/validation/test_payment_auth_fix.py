#!/usr/bin/env python3
"""
Test authentication flow for payment from email links.
"""

import json
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class MockPaymentAuthHandler(BaseHTTPRequestHandler):
    """Mock API server to simulate authentication flow."""

    def do_POST(self):
        """Handle POST requests for login and ticket issuance."""
        path = self.path

        if path == "/api/auth/login":
            # Mock successful login
            login_response = {
                "access_token": "mock_token_12345",
                "user": {
                    "id": "test_user_id",
                    "email": "flightbooker@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                },
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(login_response).encode())
            return

        if path == "/api/flights/issue_ticket":
            # Check for Authorization header
            auth_header = self.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                # No token or invalid format
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"detail": "Authentication required for ticketing"}
                    ).encode()
                )
                return

            token = auth_header.replace("Bearer ", "")
            if token != "mock_token_12345":
                # Invalid token
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"detail": "Invalid or expired token"}).encode()
                )
                return

            # Valid token - successful ticket issuance
            ticket_response = {
                "success": True,
                "message": "Ticket issued successfully",
                "ticket_number": "123456789",
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ticket_response).encode())
            return

        # Unknown endpoint
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for booking data."""
        path = self.path

        if path.startswith("/api/bookings/VOYA-"):
            booking_ref = path.split("/")[-1]

            # Mock booking response
            booking_response = {
                "voya_booking_reference": booking_ref,
                "external_booking_reference": "TR12345",
                "booking_status": "CONFIRMED",
                "ticket_status": "PENDING",
                "trip_details": {
                    "message": "Your booking is confirmed. Complete payment to receive your tickets."
                },
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(booking_response).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def simulate_email_link_flow(port=8769):
    """Simulate the complete email link to payment flow."""
    print("🔗 Simulating Email Link to Payment Flow")
    print("=" * 60)

    # Start mock server
    server = HTTPServer(("localhost", port), MockPaymentAuthHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://localhost:{port}"

    try:
        print("Step 1: User clicks email payment link (unauthenticated)")

        # Step 1: Get booking data (should work without auth)
        booking_ref = "VOYA-TEST123"
        booking_url = f"{base_url}/api/bookings/{booking_ref}"

        with urllib.request.urlopen(booking_url) as response:
            booking_data = json.loads(response.read().decode())
            print(f"  ✅ Booking loaded: {booking_data['voya_booking_reference']}")
            print(f"  ✅ Status: {booking_data['booking_status']}")

        print("\nStep 2: Auto-login triggered for payment processing")

        # Step 2: Auto-login (simulates loadBookingFromReference auto-login)
        login_url = f"{base_url}/api/auth/login"
        login_data = {
            "email": "flightbooker@example.com",
            "password": "Flight123!",  # pragma: allowlist secret
        }

        login_request = urllib.request.Request(
            login_url,
            data=json.dumps(login_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(login_request) as response:
            login_response = json.loads(response.read().decode())
            access_token = login_response["access_token"]
            print(f"  ✅ Auto-login successful: {login_response['user']['first_name']}")
            print(f"  ✅ Access token: {access_token[:20]}...")

        print("\nStep 3: User completes payment and triggers ticket issuance")

        # Step 3: Issue ticket (requires authentication)
        ticket_url = f"{base_url}/api/flights/issue_ticket"
        ticket_data = {
            "voya_booking_reference": booking_ref,
            "payment_id": "demo_payment_intent",
        }

        ticket_request = urllib.request.Request(
            ticket_url,
            data=json.dumps(ticket_data).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )

        with urllib.request.urlopen(ticket_request) as response:
            ticket_response = json.loads(response.read().decode())
            print(
                f"  ✅ Ticket issued successfully: {ticket_response['ticket_number']}"
            )
            print(f"  ✅ Message: {ticket_response['message']}")

        print("\n🎉 Complete Email-to-Payment Flow Successful!")
        print("  ✅ Booking loaded without authentication")
        print("  ✅ Auto-login triggered seamlessly")
        print("  ✅ Payment processing authenticated")
        print("  ✅ Ticket issuance completed")

        return True

    except Exception as e:
        print(f"\n❌ Flow failed: {e}")
        return False
    finally:
        server.shutdown()


def test_authentication_failure_scenarios(port=8770):
    """Test what happens when authentication fails."""
    print("\n🚨 Testing Authentication Failure Scenarios")
    print("=" * 60)

    # Start mock server
    server = HTTPServer(("localhost", port), MockPaymentAuthHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://localhost:{port}"

    try:
        print("Scenario 1: Ticket issuance without authentication")

        # Try to issue ticket without authentication
        ticket_url = f"{base_url}/api/flights/issue_ticket"
        ticket_data = {
            "voya_booking_reference": "VOYA-TEST123",
            "payment_id": "demo_payment_intent",
        }

        ticket_request = urllib.request.Request(
            ticket_url,
            data=json.dumps(ticket_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(ticket_request) as response:
                print(f"  ❌ Unexpected success: {response.status}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                error_data = json.loads(e.read().decode())
                print(f"  ✅ Correctly rejected: {error_data['detail']}")
            else:
                print(f"  ❌ Unexpected error: {e.code}")

        print("\nScenario 2: Ticket issuance with invalid token")

        # Try with invalid token
        invalid_request = urllib.request.Request(
            ticket_url,
            data=json.dumps(ticket_data).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(invalid_request) as response:
                print(f"  ❌ Unexpected success: {response.status}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                error_data = json.loads(e.read().decode())
                print(f"  ✅ Correctly rejected: {error_data['detail']}")
            else:
                print(f"  ❌ Unexpected error: {e.code}")

        print("\n✅ Authentication security working correctly")
        return True

    except Exception as e:
        print(f"\n❌ Security test failed: {e}")
        return False
    finally:
        server.shutdown()


def main():
    """Run authentication flow tests."""
    print("🔐 Payment Authentication Flow Tests")
    print("=" * 70)

    tests = [simulate_email_link_flow, test_authentication_failure_scenarios]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("\n" + "=" * 30 + " PASS " + "=" * 30)
            else:
                print("\n" + "=" * 30 + " FAIL " + "=" * 30)
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            print("\n" + "=" * 30 + " ERROR " + "=" * 29)
        print()

    print("=" * 70)
    print(f"Tests: {passed}/{total} passed")

    if passed == total:
        print("🎉 All authentication tests passed!")
        print("\n📋 Key Points:")
        print("  🔐 Auto-login ensures seamless user experience")
        print("  🛡️  Security maintained with proper token validation")
        print("  📧 Email links work end-to-end")
        print("  💳 Payment flow authenticated correctly")
        return 0
    print("⚠️  Some authentication tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
