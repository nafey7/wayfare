"""Tests for hotel JSON float parsing helpers."""

from app.domains.hotel.json_float import (
    finite_float_from_hotel_json,
    first_dict_coord_value,
)


def test_finite_float_preserves_zero() -> None:
    assert finite_float_from_hotel_json(0.0) == 0.0
    assert finite_float_from_hotel_json(0) == 0.0


def test_first_dict_coord_value_prefers_first_non_none() -> None:
    d = {"latitude": 0.0, "lat": 99.0}
    assert first_dict_coord_value(d, "latitude", "lat") == 0.0


def test_first_dict_coord_value_skips_none() -> None:
    d = {"latitude": None, "lat": 1.5}
    assert first_dict_coord_value(d, "latitude", "lat") == 1.5
