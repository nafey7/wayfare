"""Unit tests for passenger PII encryption."""

from unittest.mock import patch

import pytest

from app.domains.passenger.encryption import decrypt_document, encrypt_document


@pytest.fixture
def sample_doc():
    """Sample document with sensitive fields."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "passport_number": "AB1234567",  # pragma: allowlist secret
        "passport_expiry": "2028-05-15",
        "frequent_flyer_number": "FF789012",
    }


@pytest.fixture
def mock_cipher():
    """Use development key derivation for tests."""
    from app.domains.passenger.encryption import _reset_cipher

    _reset_cipher()
    with patch("app.domains.passenger.encryption.settings") as mock_settings:
        mock_settings.PASSENGER_ENCRYPTION_KEY = None
        mock_settings.ENVIRONMENT = "development"
        mock_settings.SECRET_KEY = (
            "test-secret-key-32-chars-long!!!"  # pragma: allowlist secret
        )
        yield mock_settings


class TestEncryption:
    """Tests for encrypt/decrypt roundtrip."""

    def test_encrypt_decrypt_roundtrip(self, sample_doc, mock_cipher):
        """Encrypted document decrypts back to original."""
        encrypted = encrypt_document(sample_doc)
        assert encrypted["passport_number"] != sample_doc["passport_number"]
        assert encrypted["passport_number"].startswith("gAAAAA")  # Fernet prefix

        decrypted = decrypt_document(encrypted)
        assert decrypted["passport_number"] == sample_doc["passport_number"]
        assert decrypted["passport_expiry"] == sample_doc["passport_expiry"]
        assert decrypted["frequent_flyer_number"] == sample_doc["frequent_flyer_number"]

    def test_non_sensitive_unchanged(self, sample_doc, mock_cipher):
        """Non-sensitive fields are not encrypted."""
        encrypted = encrypt_document(sample_doc)
        assert encrypted["first_name"] == "John"
        assert encrypted["last_name"] == "Doe"

    def test_none_sensitive_skipped(self, mock_cipher):
        """None/empty sensitive fields are skipped."""
        doc = {"first_name": "Jane", "passport_number": None, "passport_expiry": ""}
        encrypted = encrypt_document(doc)
        assert (
            "passport_number" not in encrypted or encrypted["passport_number"] is None
        )
        decrypted = decrypt_document(encrypted)
        assert decrypted["first_name"] == "Jane"

    def test_invalid_token_sets_field_to_none(self, mock_cipher):
        """When decryption fails (InvalidToken), field is set to None gracefully."""
        # Document with invalid/corrupt ciphertext for one encrypted field
        doc = {
            "first_name": "John",
            "last_name": "Doe",
            "passport_number": "invalid-not-fernet-ciphertext",
            "passport_expiry": "2028-05-15",
            "frequent_flyer_number": "FF789012",
        }
        # First encrypt a valid doc to get valid ciphertext for passport_expiry and FF
        valid_encrypted = encrypt_document(
            {
                "passport_number": "X",  # will be overwritten
                "passport_expiry": "2028-05-15",
                "frequent_flyer_number": "FF789012",
            }
        )
        doc["passport_expiry"] = valid_encrypted["passport_expiry"]
        doc["frequent_flyer_number"] = valid_encrypted["frequent_flyer_number"]
        # Keep passport_number as invalid to trigger InvalidToken
        result = decrypt_document(doc)
        assert result["passport_number"] is None
        assert result["passport_expiry"] == "2028-05-15"
        assert result["frequent_flyer_number"] == "FF789012"
