#!/usr/bin/env python3
"""Quick test of MongoDB serialization fix for Decimal objects"""

import os

# Add current directory to path
import sys
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.domains.booking_sessions.service import BookingSessionService


# Test data with problematic types
class TestEnum(Enum):
    ECONOMY = "economy"
    BUSINESS = "business"


test_data = {
    "simple_string": "test",
    "simple_number": 123,
    "decimal_price": Decimal("50.62"),
    "nested_decimal": {
        "price": Decimal("100.25"),
        "tax": Decimal("15.50"),
        "items": [{"cost": Decimal("25.00")}, {"cost": Decimal("75.25")}],
    },
    "enum_value": TestEnum.ECONOMY,
    "date_value": date(2025, 1, 1),
    "datetime_value": datetime.now(),
    "complex_nested": {
        "flight_data": {
            "price": Decimal("500.00"),
            "class": TestEnum.BUSINESS,
            "date": date(2025, 3, 15),
        }
    },
}


def test_serialization():
    """Test that serialization handles all problematic types"""
    print("Testing MongoDB serialization fix...")

    try:
        serialized = BookingSessionService._serialize_for_mongo(test_data)

        print("✅ Serialization successful!")
        print("Original data types:")
        print(f"  decimal_price: {type(test_data['decimal_price'])}")
        print(f"  enum_value: {type(test_data['enum_value'])}")
        print(f"  nested decimal: {type(test_data['nested_decimal']['price'])}")

        print("\nSerialized data types:")
        print(
            f"  decimal_price: {type(serialized['decimal_price'])} = {serialized['decimal_price']}"
        )
        print(
            f"  enum_value: {type(serialized['enum_value'])} = {serialized['enum_value']}"
        )
        print(
            f"  nested decimal: {type(serialized['nested_decimal']['price'])} = {serialized['nested_decimal']['price']}"
        )

        # Verify all Decimal objects are converted
        def check_no_decimals(obj, path=""):
            if isinstance(obj, Decimal):
                raise ValueError(f"Found unconverted Decimal at {path}: {obj}")
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_no_decimals(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    check_no_decimals(value, f"{path}[{i}]" if path else f"[{i}]")

        check_no_decimals(serialized)
        print("✅ No unconverted Decimal objects found!")

        return True

    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_serialization()
    if success:
        print("\n🎉 Serialization fix is working correctly!")
        print("Ready for deployment and end-to-end testing.")
    else:
        print("\n💥 Serialization fix needs more work.")
        sys.exit(1)
