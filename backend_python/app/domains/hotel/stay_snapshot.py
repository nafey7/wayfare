"""Normalize hotel stay dates from FlightLogic booking_details for booking_events snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def normalize_hotel_stay_date_str(value: object) -> str | None:
    """Return YYYY-MM-DD or None (property-local calendar date; no UTC shifting for date-only)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        candidate = s[:10]
        try:
            datetime.strptime(candidate, "%Y-%m-%d")  # noqa: DTZ007
            return candidate
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.date().isoformat()


def hotel_stay_from_booking_details(
    details: dict[str, Any] | None,
) -> tuple[str | None, str | None, int | None]:
    """Extract check-in, check-out, and nights from supplier or adapter-shaped dict."""
    if not details:
        return (None, None, None)
    check_in = (
        normalize_hotel_stay_date_str(details.get("check_in"))
        or normalize_hotel_stay_date_str(details.get("check_in_date"))
        or normalize_hotel_stay_date_str(details.get("checkIn"))
    )
    check_out = (
        normalize_hotel_stay_date_str(details.get("check_out"))
        or normalize_hotel_stay_date_str(details.get("check_out_date"))
        or normalize_hotel_stay_date_str(details.get("checkOut"))
    )
    nights: int | None = None
    raw_days = details.get("days")
    if raw_days is not None:
        try:
            nights = int(raw_days)
        except (TypeError, ValueError):
            nights = None
    if nights is None and check_in and check_out:
        try:
            d0 = datetime.strptime(check_in, "%Y-%m-%d").date()  # noqa: DTZ007
            d1 = datetime.strptime(check_out, "%Y-%m-%d").date()  # noqa: DTZ007
            delta = (d1 - d0).days
            if delta > 0:
                nights = delta
        except ValueError:
            pass
    return (check_in, check_out, nights)
