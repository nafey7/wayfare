"""Tests for voucher / promo redaction helpers used in logs and Sentry."""

from app.core.logging import scrub_sensitive_structured_data, scrub_sentry_event


def test_scrub_masks_voucher_code_key_when_value_looks_like_voucher() -> None:
    payload: dict = {"code": "VOYA-ABCD-1234", "detail": "ok"}
    scrub_sensitive_structured_data(payload)
    assert payload["code"] == "VOYA…34"
    assert payload["detail"] == "ok"


def test_scrub_leaves_api_error_code_strings() -> None:
    payload: dict = {"code": "public_chat_disabled"}
    scrub_sensitive_structured_data(payload)
    assert payload["code"] == "public_chat_disabled"


def test_scrub_always_masks_voucher_code_field() -> None:
    payload: dict = {"voucher_code": "VOYA-ZZZZ-9999"}
    scrub_sensitive_structured_data(payload)
    assert payload["voucher_code"] == "VOYA…99"


def test_scrub_sentry_event_walks_nested() -> None:
    event: dict = {
        "extra": {"body": {"code": "VOYA-XXXX-YYYY"}},
        "tags": {"route": "apply"},
    }
    scrub_sentry_event(event)
    assert event["extra"]["body"]["code"] == "VOYA…YY"
    assert event["tags"]["route"] == "apply"
