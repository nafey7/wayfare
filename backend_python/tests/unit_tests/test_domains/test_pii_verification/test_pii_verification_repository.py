"""Unit tests for PII verification repository - HMAC, verification logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.domains.pii_verification.repository import (
    PII_REQUEST_RATE_LIMIT_COUNT,
    PII_REQUEST_RATE_LIMIT_MINUTES,
    _generate_otp,
    check_pii_request_rate_limit,
    mask_email,
    record_pii_request,
    verify_otp,
)


@pytest.mark.unit
class TestGenerateOtp:
    """Test _generate_otp produces unique 6-digit codes (regression: OTP stuck in Docker)."""

    def test_otp_format(self) -> None:
        otp = _generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_otp_uniqueness_rapid_calls(self) -> None:
        """Consecutive calls typically yield different OTPs (CSPRNG)."""
        otps = [_generate_otp() for _ in range(20)]
        assert len(set(otps)) == 20, f"Expected 20 unique OTPs, got duplicates: {otps}"


@pytest.mark.unit
class TestMaskEmail:
    """Test mask_email utility."""

    def test_mask_email_normal(self) -> None:
        assert mask_email("john@gmail.com") == "j***@gmail.com"

    def test_mask_email_single_char_local(self) -> None:
        assert mask_email("a@b.com") == "a***@b.com"

    def test_mask_email_empty_local(self) -> None:
        assert mask_email("@domain.com") == "***@domain.com"

    def test_mask_email_empty(self) -> None:
        assert mask_email("") == "***@***"

    def test_mask_email_no_at(self) -> None:
        assert mask_email("invalid") == "***@***"


@pytest.mark.unit
@pytest.mark.asyncio
class TestVerifyOtp:
    """Test verify_otp - HMAC comparison, attempts, expiry."""

    @patch("app.domains.pii_verification.repository.get_database")
    async def test_verify_otp_not_found(self, mock_get_db: MagicMock) -> None:
        mock_coll = AsyncMock()
        mock_coll.find_one.return_value = None
        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_coll
        mock_get_db.return_value = mock_db

        success, msg = await verify_otp("challenge123", "user1", "123456")
        assert success is False
        assert "Invalid or expired" in (msg or "")

    @patch("app.domains.pii_verification.repository.get_database")
    async def test_verify_otp_expired(self, mock_get_db: MagicMock) -> None:
        """Expired challenge: find_one returns None (no doc with expires_at > now)."""
        uid = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_coll = AsyncMock()
        mock_coll.find_one.return_value = None  # No doc found (expired or invalid)
        mock_db = AsyncMock()
        mock_db.__getitem__.return_value = mock_coll
        mock_get_db.return_value = mock_db

        success, msg = await verify_otp("ch1", uid, "123456")
        assert success is False
        assert "Invalid or expired" in (msg or "")


@pytest.mark.unit
@pytest.mark.asyncio
class TestPiiRequestRateLimit:
    """Test check_pii_request_rate_limit and record_pii_request."""

    @patch("app.domains.pii_verification.repository.get_database")
    async def test_rate_limit_allows_when_under_limit(
        self, mock_get_db: MagicMock
    ) -> None:
        uid = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_coll = AsyncMock()
        mock_coll.count_documents.return_value = 1
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_coll
        mock_get_db.return_value = mock_db

        allowed, msg = await check_pii_request_rate_limit(uid)
        assert allowed is True
        assert msg is None

    @patch("app.domains.pii_verification.repository.get_database")
    async def test_rate_limit_blocks_when_at_limit(
        self, mock_get_db: MagicMock
    ) -> None:
        uid = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_coll = AsyncMock()
        mock_coll.count_documents.return_value = PII_REQUEST_RATE_LIMIT_COUNT
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_coll
        mock_get_db.return_value = mock_db

        allowed, msg = await check_pii_request_rate_limit(uid)
        assert allowed is False
        assert "Too many" in (msg or "")
        assert str(PII_REQUEST_RATE_LIMIT_MINUTES) in (msg or "")

    @patch("app.domains.pii_verification.repository.get_database")
    async def test_record_pii_request_inserts(self, mock_get_db: MagicMock) -> None:
        uid = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_coll = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_coll
        mock_get_db.return_value = mock_db

        await record_pii_request(uid)
        mock_coll.insert_one.assert_called_once()
        doc = mock_coll.insert_one.call_args[0][0]
        assert doc["user_id"] == ObjectId(uid)
        assert "requested_at" in doc
