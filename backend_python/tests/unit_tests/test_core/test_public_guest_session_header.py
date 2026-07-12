"""Tests for X-Public-Chat-Session header parsing."""

import uuid

import pytest
from fastapi import HTTPException

from app.core.public_guest_session_header import parse_guest_session_id_header


def test_parse_accepts_valid_uuid_string() -> None:
    u = uuid.uuid4()
    assert parse_guest_session_id_header(str(u)) == str(u)


def test_parse_normalizes_whitespace() -> None:
    u = uuid.uuid4()
    assert parse_guest_session_id_header(f"  {u}  ") == str(u)


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_rejects_missing(raw: str | None) -> None:
    with pytest.raises(HTTPException) as exc:
        parse_guest_session_id_header(raw)
    assert exc.value.status_code == 400
    assert "Missing or empty" in (exc.value.detail or "")


def test_parse_rejects_non_uuid() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_guest_session_id_header("not-a-uuid")
    assert exc.value.status_code == 400
    assert "UUID" in (exc.value.detail or "")
