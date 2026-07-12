"""Stable anonymized buckets for operational logs (not reversible identifiers)."""

import hashlib


def log_bucket(value: str, *, digest_size: int = 8) -> str:
    """Return a short hex digest for correlating logs without logging raw PII."""
    return hashlib.blake2b(value.encode("utf-8"), digest_size=digest_size).hexdigest()
