"""Field-level encryption for sensitive passenger PII.

Uses Fernet (symmetric encryption) from cryptography.fernet.
Key should come from PASSENGER_ENCRYPTION_KEY env or AWS Secrets Manager.
"""

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.domains.passenger.schemas import ENCRYPTED_FIELDS

logger = logging.getLogger(__name__)

_cipher: Fernet | None = None


def _reset_cipher() -> None:
    """Reset cached cipher (for testing)."""
    global _cipher
    _cipher = None


def _get_cipher() -> Fernet:
    """Get or create Fernet cipher instance."""
    global _cipher
    if _cipher is not None:
        return _cipher

    key = settings.PASSENGER_ENCRYPTION_KEY
    if key:
        try:
            _cipher = Fernet(key.encode() if isinstance(key, str) else key)
            return _cipher
        except Exception as e:
            logger.error("Invalid PASSENGER_ENCRYPTION_KEY: %s", e)
            raise ValueError("Invalid passenger encryption key configuration") from e

    # Development fallback: derive from SECRET_KEY if in development
    if settings.ENVIRONMENT == "development":
        derived = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"voya-passenger-pii",
            iterations=480000,
        ).derive(settings.SECRET_KEY.encode())
        import base64

        fernet_key = base64.urlsafe_b64encode(derived)
        _cipher = Fernet(fernet_key)
        logger.warning(
            "Using derived key from SECRET_KEY for passenger encryption (dev only)"
        )
        return _cipher

    raise ValueError(
        "PASSENGER_ENCRYPTION_KEY must be set for passenger storage. "
        'Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )


def encrypt_field(value: str) -> str:
    """Encrypt a single string value. Public API for field-level encryption."""
    cipher = _get_cipher()
    return cipher.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """Decrypt a single string value. Public API for field-level decryption."""
    cipher = _get_cipher()
    return cipher.decrypt(value.encode()).decode()


def encrypt_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields before writing to MongoDB."""
    out = dict(doc)
    cipher = _get_cipher()
    for field in ENCRYPTED_FIELDS:
        if field in out and out[field] and isinstance(out[field], str):
            try:
                encrypted = cipher.encrypt(out[field].encode())
                out[field] = encrypted.decode()
            except Exception as e:
                logger.error("Encryption failed for field %s: %s", field, e)
                raise
    return out


def decrypt_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Decrypt sensitive fields after reading from MongoDB."""
    out = dict(doc)
    cipher = _get_cipher()
    for field in ENCRYPTED_FIELDS:
        if field in out and out[field] and isinstance(out[field], str):
            try:
                decrypted = cipher.decrypt(out[field].encode())
                out[field] = decrypted.decode()
            except InvalidToken:
                logger.warning(
                    "Could not decrypt field %s (possibly plaintext from before encryption)",
                    field,
                )
                out[field] = None
            except Exception as e:
                logger.error("Decryption failed for field %s: %s", field, e)
                raise
    return out
