"""Unit tests for passenger schemas and masking."""

import pytest

from app.domains.passenger.schemas import (
    ENCRYPTED_FIELDS,
    PassengerCreate,
    mask_date,
    mask_sensitive,
)


class TestMasking:
    """Tests for sensitive field masking."""

    def test_mask_sensitive_long_value(self):
        """Mask shows last 4 chars."""
        assert mask_sensitive("AB1234567") == "****4567"  # pragma: allowlist secret

    def test_mask_sensitive_short_value(self):
        """Short value returns ****."""
        assert mask_sensitive("123") == "****"

    def test_mask_sensitive_none(self):
        """None returns ****."""
        assert mask_sensitive(None) == "****"

    def test_mask_sensitive_empty(self):
        """Empty returns ****."""
        assert mask_sensitive("") == "****"

    def test_mask_date_valid(self):
        """Date masking preserves year."""
        assert mask_date("2028-05-15") == "2028-**-**"

    def test_mask_date_none(self):
        """None date returns placeholder."""
        assert mask_date(None) == "****-**-**"


class TestEncryptedFields:
    """Verify encrypted fields constant."""

    def test_sensitive_fields_defined(self):
        """Sensitive PII fields per GDPR."""
        assert "passport_number" in ENCRYPTED_FIELDS
        assert "passport_expiry" in ENCRYPTED_FIELDS
        assert "frequent_flyer_number" in ENCRYPTED_FIELDS


class TestPassengerCreate:
    """Tests for PassengerCreate schema validation."""

    def test_valid_create(self):
        """Valid passenger passes validation."""
        p = PassengerCreate(
            title="Mr",
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            nationality="US",
        )
        assert p.first_name == "John"
        assert p.nationality == "US"

    def test_nationality_uppercase(self):
        """Nationality normalized to uppercase."""
        p = PassengerCreate(
            title="Mr",
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            nationality="us",
        )
        assert p.nationality == "US"

    def test_invalid_date_format(self):
        """Invalid date format raises."""
        with pytest.raises(ValueError):
            PassengerCreate(
                title="Mr",
                first_name="John",
                last_name="Doe",
                date_of_birth="01-15-1990",
                nationality="US",
            )

    def test_invalid_nationality_length(self):
        """Nationality must be 2 chars."""
        with pytest.raises(ValueError):
            PassengerCreate(
                title="Mr",
                first_name="John",
                last_name="Doe",
                date_of_birth="1990-01-15",
                nationality="USA",
            )

    def test_with_sensitive_fields(self):
        """Can include passport and FF number."""
        p = PassengerCreate(
            title="Mr",
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            nationality="US",
            passport_number="AB1234567",  # pragma: allowlist secret
            passport_expiry="2028-05-15",
            frequent_flyer_number="FF123456",
        )
        assert p.passport_number == "AB1234567"  # pragma: allowlist secret
        assert p.frequent_flyer_number == "FF123456"

    def test_title_validation_adult_mr(self):
        """Adult with Mr passes."""
        p = PassengerCreate(
            title="Mr",
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            nationality="US",
            type="adult",
        )
        assert p.title == "Mr"

    def test_title_validation_adult_rejects_master(self):
        """Adult with Master raises."""
        with pytest.raises(
            ValueError, match="Adult must have title Mr, Mrs, Miss, or Ms"
        ):
            PassengerCreate(
                title="Master",
                first_name="John",
                last_name="Doe",
                date_of_birth="1990-01-15",
                nationality="US",
                type="adult",
            )

    def test_title_validation_child_master(self):
        """Child with Master passes."""
        p = PassengerCreate(
            title="Master",
            first_name="John",
            last_name="Doe",
            date_of_birth="2015-01-15",
            nationality="US",
            type="child",
        )
        assert p.title == "Master"

    def test_title_validation_child_rejects_mr(self):
        """Child with Mr raises."""
        with pytest.raises(
            ValueError, match="Child/infant must have title Master or Miss"
        ):
            PassengerCreate(
                title="Mr",
                first_name="John",
                last_name="Doe",
                date_of_birth="2015-01-15",
                nationality="US",
                type="child",
            )

    def test_title_validation_no_type_skips(self):
        """When type is not provided, title validation is skipped."""
        p = PassengerCreate(
            title="Mr",
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            nationality="US",
        )
        assert p.title == "Mr"
