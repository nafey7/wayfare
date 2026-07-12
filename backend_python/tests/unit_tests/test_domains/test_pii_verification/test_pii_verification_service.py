"""Unit tests for PII verification service - token creation and verification."""

import pytest

from app.domains.pii_verification.service import (
    create_pii_view_token,
    verify_pii_view_token,
)


@pytest.mark.unit
class TestPiiViewToken:
    """Test PII view token create and verify."""

    def test_create_and_verify_token(self) -> None:
        user_id = "507f1f77bcf86cd799439011"
        token = create_pii_view_token(user_id)
        assert token
        assert isinstance(token, str)
        decoded = verify_pii_view_token(token)
        assert decoded == user_id

    def test_verify_expired_token_returns_none(self) -> None:
        import jwt

        from app.core.config import settings

        payload = {
            "user_id": "507f1f77bcf86cd799439011",
            "aud": "pii-view",
            "exp": 0,
            "iat": 0,
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        result = verify_pii_view_token(expired_token)
        assert result is None

    def test_verify_invalid_token_returns_none(self) -> None:
        assert verify_pii_view_token("invalid") is None
