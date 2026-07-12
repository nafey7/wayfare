"""Tests for VOYA reference generator."""

import pytest

from app.domains.bookings.reference_generator import VoyaReferenceGenerator


class TestVoyaReferenceGenerator:
    """Test suite for VoyaReferenceGenerator."""

    def test_format_has_correct_prefix(self):
        """Test that generated reference has VOYA prefix."""
        # We can't test async generation without database, so test the format
        assert VoyaReferenceGenerator.PREFIX == "VOYA"

    def test_alphabet_contains_expected_characters(self):
        """Test that alphabet contains expected safe characters."""
        alphabet = VoyaReferenceGenerator.ALPHABET

        # Should contain these safe characters
        assert "A" in alphabet
        assert "Z" in alphabet
        assert "2" in alphabet
        assert "9" in alphabet

    def test_validate_format_invalid_prefix(self):
        """Test validation rejects invalid prefix."""
        invalid_ref = "INVALID-ABC123XYZ9"
        assert VoyaReferenceGenerator.validate_format(invalid_ref) is False

    def test_validate_format_missing_dash(self):
        """Test validation rejects reference without dash."""
        invalid_ref = "VOYAABC123XYZ9"
        assert VoyaReferenceGenerator.validate_format(invalid_ref) is False

    def test_validate_format_wrong_length(self):
        """Test validation rejects wrong length."""
        # Too short
        assert VoyaReferenceGenerator.validate_format("VOYA-ABC123") is False

        # Too long
        assert VoyaReferenceGenerator.validate_format("VOYA-ABC123XYZ9EXTRA") is False

    def test_validate_format_invalid_characters(self):
        """Test validation rejects invalid characters in suffix."""
        # Contains excluded character 'O'
        invalid_ref = "VOYA-ABC123XYZO"
        assert VoyaReferenceGenerator.validate_format(invalid_ref) is False

        # Contains excluded character '0'
        invalid_ref = "VOYA-ABC123XYZ0"
        assert VoyaReferenceGenerator.validate_format(invalid_ref) is False

    def test_validate_format_empty_string(self):
        """Test validation rejects empty string."""
        assert VoyaReferenceGenerator.validate_format("") is False

    def test_validate_format_none(self):
        """Test validation rejects None."""
        assert VoyaReferenceGenerator.validate_format(None) is False

    def test_constants_consistency(self):
        """Test that constants are consistent."""
        # Total length should be: PREFIX + "-" + ID_LENGTH
        expected_length = (
            len(VoyaReferenceGenerator.PREFIX) + 1 + VoyaReferenceGenerator.ID_LENGTH
        )
        assert expected_length == 15  # VOYA-XXXXXXXXXX

    @pytest.mark.asyncio
    async def test_generate_unique_success(self):
        """Test successful generation with mock database."""

        # Mock collection that always returns None (no collision)
        class MockCollection:
            async def find_one(self, query):
                return None  # No existing reference found

        mock_collection = MockCollection()

        # Generate reference
        reference = await VoyaReferenceGenerator.generate_unique(mock_collection)

        # Verify format
        assert reference.startswith("VOYA-")
        assert len(reference) == 15
        assert VoyaReferenceGenerator.validate_format(reference)

    @pytest.mark.asyncio
    async def test_generate_unique_retry_on_collision(self):
        """Test that generator retries on collision."""
        collision_count = 0

        # Mock collection that returns collision on first call, then success
        class MockCollection:
            async def find_one(self, query):
                nonlocal collision_count
                collision_count += 1
                if collision_count == 1:
                    return {
                        "voya_booking_reference": "VOYA-COLLISION1"
                    }  # First call: collision
                return None  # Second call: success

        mock_collection = MockCollection()

        # Generate reference (should succeed on second attempt)
        reference = await VoyaReferenceGenerator.generate_unique(mock_collection)

        # Verify it tried twice
        assert collision_count == 2
        assert VoyaReferenceGenerator.validate_format(reference)

    @pytest.mark.asyncio
    async def test_generate_unique_fails_after_max_retries(self):
        """Test that generator raises error after max retries."""

        # Mock collection that always returns collision
        class MockCollection:
            async def find_one(self, query):
                return {"voya_booking_reference": "VOYA-ALWAYSCOLLISION"}

        mock_collection = MockCollection()

        # Should raise RuntimeError after MAX_RETRIES
        with pytest.raises(
            RuntimeError, match="Failed to generate unique VOYA reference"
        ):
            await VoyaReferenceGenerator.generate_unique(mock_collection)

    @pytest.mark.asyncio
    async def test_generate_unique_creates_different_ids(self):
        """Test that multiple generations create different IDs."""

        class MockCollection:
            async def find_one(self, query):
                return None

        mock_collection = MockCollection()

        # Generate multiple references
        ref1 = await VoyaReferenceGenerator.generate_unique(mock_collection)
        ref2 = await VoyaReferenceGenerator.generate_unique(mock_collection)
        ref3 = await VoyaReferenceGenerator.generate_unique(mock_collection)

        # All should be different (statistically certain with 32^10 combinations)
        assert ref1 != ref2
        assert ref2 != ref3
        assert ref1 != ref3
