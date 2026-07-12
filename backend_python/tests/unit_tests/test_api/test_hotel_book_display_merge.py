"""booking_events hotel display merge: session first, client fills gaps only."""

import pytest

from app.domains.hotel.booking_event_display import (
    merge_session_and_client_hotel_display,
)
from app.domains.hotel.schemas import GuestInfo, HotelBookingRequest


def _minimal_request(**kwargs: object) -> HotelBookingRequest:
    guest = GuestInfo(
        title="Mr",
        first_name="A",
        last_name="B",
        room_number=1,
        is_child=False,
    )
    base: dict[str, object] = {
        "session_id": "fl-sess",
        "product_id": "prod",
        "token_id": "tok",
        "rate_basis_id": "rate",
        "client_ref": "VOYA-TEST",
        "customer_email": "a@b.com",
        "customer_phone": "+15550001111",
        "booking_note": "",
        "guests": [guest],
        "room_count": 1,
    }
    base.update(kwargs)
    return HotelBookingRequest(**base)


def test_client_fills_when_session_empty() -> None:
    req = _minimal_request(
        hotel_name="Client Hotel",
        hotel_city="Lisbon",
        hotel_address="Rua 1",
        hotel_image_url="https://img.example/x.jpg",
        hotel_latitude=38.72,
        hotel_longitude=-9.14,
    )
    img, name, city, addr, lat, lng = merge_session_and_client_hotel_display({}, req)
    assert name == "Client Hotel"
    assert city == "Lisbon"
    assert addr == "Rua 1"
    assert img == "https://img.example/x.jpg"
    assert lat == pytest.approx(38.72)
    assert lng == pytest.approx(-9.14)


def test_session_preserves_zero_latitude_and_longitude() -> None:
    """0.0 is valid WGS84; must not fall through to alternate keys."""
    session = {
        "latitude": 0.0,
        "longitude": 0.0,
    }
    req = _minimal_request(hotel_latitude=10.0, hotel_longitude=20.0)
    _, _, _, _, lat, lng = merge_session_and_client_hotel_display(session, req)
    assert lat == pytest.approx(0.0)
    assert lng == pytest.approx(0.0)


def test_session_wins_over_client() -> None:
    session = {
        "hotel_name": "Session Inn",
        "city": "Porto",
        "address": "Av. Boavista",
        "thumbnail_url": "https://session/img.jpg",
        "latitude": 41.15,
        "longitude": -8.61,
    }
    req = _minimal_request(
        hotel_name="Malicious Override",
        hotel_city="Elsewhere",
        hotel_address="Fake",
        hotel_image_url="https://evil.example/x.jpg",
        hotel_latitude=0.0,
        hotel_longitude=0.0,
    )
    img, name, city, addr, lat, lng = merge_session_and_client_hotel_display(
        session, req
    )
    assert name == "Session Inn"
    assert city == "Porto"
    assert addr == "Av. Boavista"
    assert img == "https://session/img.jpg"
    assert lat == pytest.approx(41.15)
    assert lng == pytest.approx(-8.61)


def test_client_fills_only_missing_lat_when_session_has_lng() -> None:
    session = {"longitude": -9.14}
    req = _minimal_request(hotel_latitude=38.72)
    _, _, _, _, lat, lng = merge_session_and_client_hotel_display(session, req)
    assert lat == pytest.approx(38.72)
    assert lng == pytest.approx(-9.14)


def test_invalid_client_latitude_rejected() -> None:
    req = _minimal_request(hotel_latitude=95.0, hotel_longitude=10.0)
    _, _, _, _, lat, lng = merge_session_and_client_hotel_display({}, req)
    assert lat is None
    assert lng == pytest.approx(10.0)


def test_invalid_client_longitude_rejected() -> None:
    req = _minimal_request(hotel_latitude=10.0, hotel_longitude=200.0)
    _, _, _, _, lat, lng = merge_session_and_client_hotel_display({}, req)
    assert lat == pytest.approx(10.0)
    assert lng is None


def test_long_client_name_truncated() -> None:
    long_name = "H" * 250
    req = _minimal_request(hotel_name=long_name)
    _, name, _, _, _, _ = merge_session_and_client_hotel_display({}, req)
    assert name is not None
    assert len(name) == 200
    assert name == "H" * 200
