"""Test script to reproduce trip-details 422 error."""
# ruff: noqa

import asyncio
import json
import sys

import httpx

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"


async def test_trip_details():
    """Test trip-details endpoint with VOYA reference."""

    # First, login to get a valid token
    login_data = {"email": "flightbooker@example.com", "password": "Flight123!"}

    async with httpx.AsyncClient() as client:
        # Login
        print("Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/api/auth/login", json=login_data
        )

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            return

        login_result = login_response.json()
        access_token = login_result.get("access_token")
        print(f"✅ Login successful, token: {access_token[:20]}...")

        # Test trip-details with a VOYA reference
        voya_ref = "VOYA-4AQYGXHJY8"  # Latest booking from logs

        request_body = {"voya_booking_reference": voya_ref}

        print("\n📤 Testing trip-details with request:")
        print(json.dumps(request_body, indent=2))

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        trip_response = await client.post(
            f"{BASE_URL}/api/flights/trip-details", json=request_body, headers=headers
        )

        print(f"\n📥 Response status: {trip_response.status_code}")

        if trip_response.status_code == 422:
            print("❌ 422 Validation Error!")
            print("\n🔍 Detailed error:")
            try:
                error_detail = trip_response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(trip_response.text)
        elif trip_response.status_code == 200:
            print("✅ Success!")
            result = trip_response.json()
            print("\n📋 Trip details:")
            print(f"  - External ref: {result.get('external_booking_reference')}")
            print(f"  - Booking status: {result.get('booking_status')}")
            print(f"  - Ticket status: {result.get('ticket_status')}")

            # Check airline and date information in segments
            segments = result.get("segments", [])
            if segments:
                print(f"\n✈️ Flight Segments ({len(segments)} segments):")
                for i, seg in enumerate(segments):
                    airline = seg.get("marketing_airline", {})
                    airline_name = airline.get("airline_name", "Unknown")
                    airline_code = airline.get("iata_code", "??")
                    dep_dt = seg.get("departure_datetime", {})
                    dep_time = (
                        dep_dt.get("value") if isinstance(dep_dt, dict) else dep_dt
                    )
                    arr_dt = seg.get("arrival_datetime", {})
                    arr_time = (
                        arr_dt.get("value") if isinstance(arr_dt, dict) else arr_dt
                    )

                    print(f"  [{i + 1}] {airline_name} ({airline_code})")
                    print(f"      Departure: {dep_time}")
                    print(f"      Arrival: {arr_time}")
            else:
                print("\n⚠️ No segments found in response")
        else:
            print(f"❌ Unexpected status: {trip_response.status_code}")
            print(trip_response.text)


if __name__ == "__main__":
    asyncio.run(test_trip_details())
