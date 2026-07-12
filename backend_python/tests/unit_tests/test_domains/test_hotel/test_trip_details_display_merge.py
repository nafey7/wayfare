"""Merge booking_events display snapshots into hotel trip-details booking_details."""

from types import SimpleNamespace

from app.domains.hotel.service import _overlay_booking_event_display_on_details


def test_overlay_fills_blank_supplier_fields() -> None:
    event = SimpleNamespace(
        hotel_name="Grand Lisbon",
        hotel_city="Lisbon",
        hotel_address="Rua Example 1",
        hotel_image_url="https://img.example/property.jpg",
        hotel_latitude=None,
        hotel_longitude=None,
    )
    merged = _overlay_booking_event_display_on_details({}, event)
    assert merged["hotel_name"] == "Grand Lisbon"
    assert merged["city"] == "Lisbon"
    assert merged["address"] == "Rua Example 1"
    assert merged["image"] == "https://img.example/property.jpg"


def test_overlay_preserves_supplier_when_present() -> None:
    event = SimpleNamespace(
        hotel_name="Grand Lisbon",
        hotel_city="Lisbon",
        hotel_address="Rua Example 1",
        hotel_image_url="https://img.example/property.jpg",
        hotel_latitude=None,
        hotel_longitude=None,
    )
    merged = _overlay_booking_event_display_on_details(
        {
            "hotel_name": "API Hotel",
            "city": "Porto",
            "address": "Supplier St 2",
            "image": "https://api.example/x.jpg",
        },
        event,
    )
    assert merged["hotel_name"] == "API Hotel"
    assert merged["city"] == "Porto"
    assert merged["address"] == "Supplier St 2"
    assert merged["image"] == "https://api.example/x.jpg"


def test_overlay_skips_image_when_images_array_present() -> None:
    event = SimpleNamespace(
        hotel_name="Grand Lisbon",
        hotel_city="Lisbon",
        hotel_address=None,
        hotel_image_url="https://img.example/property.jpg",
        hotel_latitude=None,
        hotel_longitude=None,
    )
    merged = _overlay_booking_event_display_on_details(
        {"images": ["https://a.com/1.jpg"]},
        event,
    )
    assert merged.get("image") is None
    assert merged["images"] == ["https://a.com/1.jpg"]


def test_overlay_fills_geo_from_event_when_supplier_omits() -> None:
    event = SimpleNamespace(
        hotel_name="H",
        hotel_city="Lisbon",
        hotel_address=None,
        hotel_image_url=None,
        hotel_latitude=38.7223,
        hotel_longitude=-9.1393,
    )
    merged = _overlay_booking_event_display_on_details({}, event)
    assert merged["latitude"] == 38.7223
    assert merged["longitude"] == -9.1393


def test_overlay_preserves_supplier_geo_when_present() -> None:
    event = SimpleNamespace(
        hotel_name="H",
        hotel_city="Lisbon",
        hotel_address=None,
        hotel_image_url=None,
        hotel_latitude=1.0,
        hotel_longitude=2.0,
    )
    merged = _overlay_booking_event_display_on_details(
        {"latitude": 40.0, "longitude": -3.0},
        event,
    )
    assert merged["latitude"] == 40.0
    assert merged["longitude"] == -3.0


def test_overlay_fills_address_when_supplier_blank_or_whitespace() -> None:
    """Supplier payload may omit street; booking_events snapshot should backfill."""
    event = SimpleNamespace(
        hotel_name="API Hotel",
        hotel_city="Lisbon",
        hotel_address="Rua do Comércio 10",
        hotel_image_url=None,
        hotel_latitude=None,
        hotel_longitude=None,
    )
    merged_empty = _overlay_booking_event_display_on_details(
        {
            "hotel_name": "API Hotel",
            "city": "Lisbon",
            "address": "",
        },
        event,
    )
    assert merged_empty["address"] == "Rua do Comércio 10"

    merged_ws = _overlay_booking_event_display_on_details({"address": "  \t"}, event)
    assert merged_ws["address"] == "Rua do Comércio 10"
