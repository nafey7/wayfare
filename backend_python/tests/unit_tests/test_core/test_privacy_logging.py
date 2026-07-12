"""Tests for privacy_logging helpers."""

from app.core.privacy_logging import log_bucket


def test_log_bucket_stable_for_same_input() -> None:
    a = log_bucket("192.168.1.1")
    b = log_bucket("192.168.1.1")
    assert a == b
    assert len(a) == 16


def test_log_bucket_differs_for_different_inputs() -> None:
    assert log_bucket("a") != log_bucket("b")
