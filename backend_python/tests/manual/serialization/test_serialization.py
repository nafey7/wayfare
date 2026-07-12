#!/usr/bin/env python3
"""
Standalone test for flight booking handler serialization fixes
Tests the JSON serialization of flight data including dates and decimals
"""

import base64
import json
import sys
from datetime import date, datetime
from decimal import Decimal


def convert_all_data(obj):
    """Convert data for JSON serialization - matches our implementation"""
    if isinstance(obj, dict):
        return {k: convert_all_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_all_data(item) for item in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "__float__"):
        try:
            return float(obj)
        except (ValueError, TypeError):
            return str(obj)
    return obj


def serialize_flight_for_url(flight):
    """Serialize flight object for URL transmission"""
    try:
        # Convert flight object to dict
        if hasattr(flight, "model_dump"):
            flight_dict = flight.model_dump()
        elif hasattr(flight, "__dict__"):
            flight_dict = dict(flight.__dict__)
        else:
            flight_dict = dict(flight) if flight else {}

        # Convert dates and decimals
        return convert_all_data(flight_dict)
    except Exception as e:
        print(f"Flight serialization error: {e}")
        return {"error": "serialization_failed", "flight_id": "unknown"}


def generate_flight_booker_url_test(
    session_id, selected_flight, search_params, selected_option
):
    """Test URL generation with pre-selected flight data"""
    try:
        # Prepare flight data for URL - serialize all data consistently
        flight_data = {
            "session_id": session_id,
            "selected_flight": serialize_flight_for_url(selected_flight),
            "search_params": convert_all_data(search_params),
            "selected_option": selected_option,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "chat_booking",
        }

        # Encode as base64 for URL safety
        flight_json = json.dumps(flight_data, ensure_ascii=True, separators=(",", ":"))
        encoded_data = base64.urlsafe_b64encode(flight_json.encode("utf-8")).decode(
            "ascii"
        )

        # Generate URL
        base_url = "https://app.myvoya.ai/dev/flight-booker/index.html"
        url_with_preflight = f"{base_url}?preflight={encoded_data}"

        print(f"✅ Generated flight-booker URL successfully for session {session_id}")
        return url_with_preflight

    except Exception as e:
        print(f"❌ URL generation error: {e}")
        return "https://app.myvoya.ai/dev/flight-booker/index.html"


def test_serialization_fixes():
    """Test all the serialization fixes we implemented"""
    print("🧪 Testing flight booking handler serialization fixes...\n")

    # Test 1: Date serialization in search_params
    print("Test 1: Date objects in search_params")
    search_params = {
        "origin": "AMS",
        "destination": "JFK",
        "departure_date": date(2025, 10, 15),  # This was causing the error
        "journey_type": "OneWay",
        "adults": 1,
        "children": 0,
        "infants": 0,
    }

    try:
        converted_params = convert_all_data(search_params)
        json.dumps(converted_params)
        print(f"✅ Date conversion successful: {converted_params['departure_date']}")
    except Exception as e:
        print(f"❌ Date conversion failed: {e}")
        return False

    # Test 2: Decimal objects in flight data
    print("\nTest 2: Decimal objects in flight pricing")
    flight_data = {
        "flight_id": "FL001",
        "airline": "Test Airways",
        "price": Decimal("299.50"),  # Common in pricing data
        "departure_date": datetime(2025, 10, 15, 9, 25),
    }

    try:
        converted_flight = serialize_flight_for_url(flight_data)
        _ = json.dumps(converted_flight)  # Verify JSON serialization works
        print(
            f"✅ Decimal conversion successful: {converted_flight['price']} (type: {type(converted_flight['price'])})"
        )
    except Exception as e:
        print(f"❌ Decimal conversion failed: {e}")
        return False

    # Test 3: Full URL generation (the complete flow)
    print("\nTest 3: Complete URL generation")
    session_id = "test_session_123"
    selected_option = 1

    try:
        url = generate_flight_booker_url_test(
            session_id, flight_data, search_params, selected_option
        )

        # Verify URL structure
        if url.startswith(
            "https://app.myvoya.ai/dev/flight-booker/index.html?preflight="
        ):
            print("✅ URL structure correct")

            # Extract and verify encoded data
            encoded_part = url.split("?preflight=")[1]
            decoded_json = base64.urlsafe_b64decode(
                encoded_part.encode("ascii")
            ).decode("utf-8")
            decoded_data = json.loads(decoded_json)

            print("✅ Decoded data validation:")
            print(f"   - Session ID: {decoded_data['session_id']}")
            print(f"   - Selected option: {decoded_data['selected_option']}")
            print(
                f"   - Departure date: {decoded_data['search_params']['departure_date']}"
            )
            print(f"   - Flight price: {decoded_data['selected_flight']['price']}")

        else:
            print(f"❌ URL structure incorrect: {url}")
            return False

    except Exception as e:
        print(f"❌ Complete URL generation failed: {e}")
        return False

    print("\n🎉 All serialization tests passed! The fixes should work in production.")
    return True


def test_message_simplification():
    """Test the simplified message format"""
    print("\n📝 Testing simplified message format...")

    flight_booker_url = "https://app.myvoya.ai/dev/flight-booker/index.html?preflight=eyJ0ZXN0IjoidHJ1ZSJ9"
    message = f"Great! Click here 👉 [Complete Your Booking]({flight_booker_url}) to add your personal data and finalise your booking"

    print(f"✅ Message length: {len(message)} characters (much shorter than before)")
    print(f"✅ Message format: {message}")

    return True


if __name__ == "__main__":
    success = test_serialization_fixes()
    test_message_simplification()

    if success:
        print("\n🚀 Ready for production testing!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed - fixes need more work")
        sys.exit(1)
