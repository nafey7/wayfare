"""Merge session selected_hotel + client book payload fields for booking_events display."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from app.domains.hotel.schemas import HotelBookingRequest

from app.domains.hotel.json_float import (
    finite_float_from_hotel_json,
    first_dict_coord_value,
)

logger = logging.getLogger(__name__)


def _nonempty_trimmed(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _session_display_str(raw: object | None) -> str | None:
    if raw is None:
        return None
    return _nonempty_trimmed(str(raw))


def _optional_hotel_wgs84_latitude(value: object) -> float | None:
    x = finite_float_from_hotel_json(value)
    if x is None:
        return None
    if -90.0 <= x <= 90.0:
        return x
    logger.info(
        "hotel_book_display_invalid_geo_rejected",
        extra={"field": "hotel_latitude", "raw": value},
    )
    return None


def _optional_hotel_wgs84_longitude(value: object) -> float | None:
    x = finite_float_from_hotel_json(value)
    if x is None:
        return None
    if -180.0 <= x <= 180.0:
        return x
    logger.info(
        "hotel_book_display_invalid_geo_rejected",
        extra={"field": "hotel_longitude", "raw": value},
    )
    return None


_HOTEL_DISPLAY_NAME_MAX = 200
_HOTEL_DISPLAY_CITY_MAX = 120
_HOTEL_DISPLAY_ADDRESS_MAX = 500
_HOTEL_DISPLAY_IMAGE_URL_MAX = 2048


def _blank_hotel_display_str(value: str | None) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _cap_trimmed_display_str(
    value: str | None, max_len: int, field_name: str
) -> str | None:
    trimmed = _nonempty_trimmed(value)
    if trimmed is None:
        return None
    if len(trimmed) <= max_len:
        return trimmed
    logger.info(
        "hotel_book_display_field_truncated",
        extra={"field": field_name, "original_len": len(trimmed), "max_len": max_len},
    )
    return trimmed[:max_len]


class MergedHotelBookingDisplay(NamedTuple):
    """Session-first hotel marketing + geo fields merged with the client book request."""

    hotel_image_url: str | None
    hotel_name: str | None
    hotel_city: str | None
    hotel_address: str | None
    hotel_latitude: float | None
    hotel_longitude: float | None


def merge_session_and_client_hotel_display(
    selected_hotel: object,
    modified_request: HotelBookingRequest,
) -> MergedHotelBookingDisplay:
    """Session first; client request fills missing display/geo only.

    Mirrors trip-details overlay semantics (_overlay_booking_event_display_on_details):
    do not replace non-empty session values with client marketing/geo fields.
    """
    hotel_image_url: str | None = None
    hotel_name: str | None = None
    hotel_city: str | None = None
    hotel_address: str | None = None
    hotel_latitude: float | None = None
    hotel_longitude: float | None = None

    sh = selected_hotel if isinstance(selected_hotel, dict) else None
    if sh:
        hotel_image_url = _session_display_str(
            sh.get("thumbnail_url") or sh.get("thumbnailUrl")
        )
        hotel_name = _session_display_str(sh.get("hotel_name") or sh.get("hotelName"))
        hotel_city = _session_display_str(sh.get("city"))
        hotel_address = _session_display_str(sh.get("address"))
        hotel_latitude = _optional_hotel_wgs84_latitude(
            first_dict_coord_value(sh, "latitude", "lat")
        )
        hotel_longitude = _optional_hotel_wgs84_longitude(
            first_dict_coord_value(sh, "longitude", "lng", "lon")
        )

    c_img = _cap_trimmed_display_str(
        modified_request.hotel_image_url,
        _HOTEL_DISPLAY_IMAGE_URL_MAX,
        "hotel_image_url",
    )
    if _blank_hotel_display_str(hotel_image_url) and c_img is not None:
        hotel_image_url = c_img
    elif c_img is not None and not _blank_hotel_display_str(hotel_image_url):
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_image_url", "reason": "session_has_value"},
        )

    c_name = _cap_trimmed_display_str(
        modified_request.hotel_name, _HOTEL_DISPLAY_NAME_MAX, "hotel_name"
    )
    if _blank_hotel_display_str(hotel_name) and c_name is not None:
        hotel_name = c_name
    elif c_name is not None and not _blank_hotel_display_str(hotel_name):
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_name", "reason": "session_has_value"},
        )

    c_city = _cap_trimmed_display_str(
        modified_request.hotel_city, _HOTEL_DISPLAY_CITY_MAX, "hotel_city"
    )
    if _blank_hotel_display_str(hotel_city) and c_city is not None:
        hotel_city = c_city
    elif c_city is not None and not _blank_hotel_display_str(hotel_city):
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_city", "reason": "session_has_value"},
        )

    c_addr = _cap_trimmed_display_str(
        modified_request.hotel_address,
        _HOTEL_DISPLAY_ADDRESS_MAX,
        "hotel_address",
    )
    if _blank_hotel_display_str(hotel_address) and c_addr is not None:
        hotel_address = c_addr
    elif c_addr is not None and not _blank_hotel_display_str(hotel_address):
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_address", "reason": "session_has_value"},
        )

    if hotel_latitude is None and modified_request.hotel_latitude is not None:
        parsed = _optional_hotel_wgs84_latitude(modified_request.hotel_latitude)
        if parsed is not None:
            hotel_latitude = parsed
    elif hotel_latitude is not None and modified_request.hotel_latitude is not None:
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_latitude", "reason": "session_has_value"},
        )

    if hotel_longitude is None and modified_request.hotel_longitude is not None:
        parsed = _optional_hotel_wgs84_longitude(modified_request.hotel_longitude)
        if parsed is not None:
            hotel_longitude = parsed
    elif hotel_longitude is not None and modified_request.hotel_longitude is not None:
        logger.info(
            "hotel_book_display_override_ignored",
            extra={"field": "hotel_longitude", "reason": "session_has_value"},
        )

    return MergedHotelBookingDisplay(
        hotel_image_url,
        hotel_name,
        hotel_city,
        hotel_address,
        hotel_latitude,
        hotel_longitude,
    )
