"""UTC normalization for datetimes from MongoDB (often naive) vs app `datetime.now(UTC)` (aware)."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """Mongo/BSON may yield naive datetimes; treat naive as UTC and compare safely with aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
