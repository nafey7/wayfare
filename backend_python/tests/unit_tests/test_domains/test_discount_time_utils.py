"""Tests for discount UTC datetime normalization."""

from datetime import UTC, datetime

from app.domains.discount.time_utils import ensure_utc_aware


def test_ensure_utc_aware_naive_assumes_utc() -> None:
    naive = datetime(2026, 6, 1, 12, 0, 0)
    out = ensure_utc_aware(naive)
    assert out is not None
    assert out.tzinfo == UTC
    assert out.hour == 12


def test_ensure_utc_aware_z_offset() -> None:
    aware = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert ensure_utc_aware(aware) == aware


def test_ensure_utc_aware_none() -> None:
    assert ensure_utc_aware(None) is None
