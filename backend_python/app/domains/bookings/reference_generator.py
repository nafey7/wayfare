"""VOYA booking reference generator.

Generates unique, cryptographically random booking references with VOYA prefix.
Format: VOYA-XXXXXXXXXX (15 characters total)
"""

import logging
from typing import Any

from nanoid import generate

logger = logging.getLogger(__name__)


class VoyaReferenceGenerator:
    """Generate unique VOYA booking references.

    Properties:
    - Format: VOYA-XXXXXXXXXX
    - Cryptographically random (no enumeration possible)
    - Collision-resistant (~1 quadrillion combinations)
    - Database validation before return
    """

    PREFIX = "VOYA"
    # Exclude ambiguous characters: 0/O, 1/I/L for better readability
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    ID_LENGTH = 10
    MAX_RETRIES = 3

    @staticmethod
    async def generate_unique(booking_collection: Any) -> str:
        """Generate unique VOYA reference with database validation.

        Args:
            booking_collection: MongoDB collection to check uniqueness

        Returns:
            Unique VOYA reference (format: VOYA-XXXXXXXXXX)

        Raises:
            RuntimeError: If unable to generate unique reference after max retries
        """
        for attempt in range(1, VoyaReferenceGenerator.MAX_RETRIES + 1):
            # Generate candidate reference
            unique_id = generate(
                VoyaReferenceGenerator.ALPHABET, VoyaReferenceGenerator.ID_LENGTH
            )
            voya_booking_reference = f"{VoyaReferenceGenerator.PREFIX}-{unique_id}"

            # Validate uniqueness in database
            existing = await booking_collection.find_one(
                {"voya_booking_reference": voya_booking_reference}
            )

            if not existing:
                logger.info(
                    f"Generated unique VOYA reference: {voya_booking_reference}"
                )
                return voya_booking_reference

            # Collision detected (extremely rare - should almost never happen)
            logger.warning(
                f"VOYA reference collision detected: {voya_booking_reference} "
                f"(attempt {attempt}/{VoyaReferenceGenerator.MAX_RETRIES})"
            )

        # This should statistically never happen with proper alphabet size
        error_msg = (
            f"Failed to generate unique VOYA reference after "
            f"{VoyaReferenceGenerator.MAX_RETRIES} attempts"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    @staticmethod
    def validate_format(reference: str) -> bool:
        """Validate VOYA reference format.

        Args:
            reference: Reference to validate

        Returns:
            True if valid format, False otherwise
        """
        if not reference:
            return False

        # Check prefix
        if not reference.startswith(f"{VoyaReferenceGenerator.PREFIX}-"):
            return False

        # Check total length (VOYA- + 10 chars = 15)
        if (
            len(reference)
            != len(VoyaReferenceGenerator.PREFIX) + 1 + VoyaReferenceGenerator.ID_LENGTH
        ):
            return False

        # Check suffix contains only allowed characters
        suffix = reference[len(VoyaReferenceGenerator.PREFIX) + 1 :]
        return all(c in VoyaReferenceGenerator.ALPHABET for c in suffix)
