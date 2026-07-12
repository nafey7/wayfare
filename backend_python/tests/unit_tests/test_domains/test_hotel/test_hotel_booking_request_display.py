"""Hotel book request accepts optional display fields for booking_events."""

from app.domains.hotel.schemas import GuestInfo, HotelBookingRequest


def test_hotel_booking_request_optional_display_fields() -> None:
    guest = GuestInfo(
        title="Mr",
        first_name="A",
        last_name="B",
        room_number=1,
        is_child=False,
    )
    req = HotelBookingRequest(
        session_id="fl-sess",
        product_id="prod",
        token_id="tok",
        rate_basis_id="rate",
        client_ref="VOYA-TEST",
        customer_email="a@b.com",
        customer_phone="+15550001111",
        booking_note="",
        guests=[guest],
        room_count=1,
        hotel_image_url="https://img.example/x.jpg",
        hotel_name="Grand",
        hotel_city="Lisbon",
        hotel_address="Rua das Flores 1",
    )
    assert req.hotel_image_url == "https://img.example/x.jpg"
    assert req.hotel_name == "Grand"
    assert req.hotel_city == "Lisbon"
    assert req.hotel_address == "Rua das Flores 1"
