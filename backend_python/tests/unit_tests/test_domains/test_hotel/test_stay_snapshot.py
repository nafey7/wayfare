"""Tests for hotel stay date normalization from booking_details."""

from datetime import date, datetime

import pytest

from app.domains.hotel.stay_snapshot import (
    hotel_stay_from_booking_details,
    normalize_hotel_stay_date_str,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("2026-04-06", "2026-04-06"),
        ("2026-04-06T14:00:00Z", "2026-04-06"),
        ("2026-04-06T14:00:00+00:00", "2026-04-06"),
        (datetime(2026, 4, 6, 14, 0, 0), "2026-04-06"),
        (date(2026, 4, 6), "2026-04-06"),
    ],
)
def test_normalize_hotel_stay_date_str(raw: object, expected: str | None) -> None:
    assert normalize_hotel_stay_date_str(raw) == expected


def test_hotel_stay_from_booking_details_snake_and_camel() -> None:
    ci, co, n = hotel_stay_from_booking_details(
        {"check_in": "2026-04-06", "check_out": "2026-04-12", "days": 6}
    )
    assert ci == "2026-04-06"
    assert co == "2026-04-12"
    assert n == 6

    ci2, co2, n2 = hotel_stay_from_booking_details(
        {"checkIn": "2026-05-01", "checkOut": "2026-05-03"}
    )
    assert ci2 == "2026-05-01"
    assert co2 == "2026-05-03"
    assert n2 == 2
