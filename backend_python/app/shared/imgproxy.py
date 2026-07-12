"""imgproxy URL signing utility.

Generates signed URLs for imgproxy to prevent abuse and unauthorized access.
Uses base64 encoding to obfuscate source URLs.
See: https://docs.imgproxy.net/usage/signing_url

Usage:
    from app.shared.imgproxy import get_imgproxy_url, transform_image_urls

    # Single URL
    signed_url = get_imgproxy_url("https://example.com/image.jpg")

    # With resize options
    signed_url = get_imgproxy_url("https://example.com/image.jpg", width=300, height=200)

    # Transform list of URLs
    signed_urls = transform_image_urls(["https://example.com/a.jpg", "https://example.com/b.jpg"])
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


def _encode_url(url: str) -> str:
    """Encode a URL using URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(url.encode("utf-8")).rstrip(b"=").decode("ascii")


@lru_cache(maxsize=1)
def _get_signing_keys() -> tuple[bytes, bytes] | None:
    """Get imgproxy signing key and salt as bytes.

    Returns None if signing is not configured.
    Cached to avoid repeated hex decoding.
    """
    key = getattr(settings, "IMGPROXY_KEY", None)
    salt = getattr(settings, "IMGPROXY_SALT", None)

    if not key or not salt:
        return None

    try:
        return bytes.fromhex(key), bytes.fromhex(salt)
    except ValueError as e:
        logger.warning("Invalid imgproxy key/salt format (must be hex): %s", e)
        return None


def _sign_path(path: str) -> str:
    """Sign an imgproxy path using HMAC-SHA256.

    Args:
        path: The imgproxy path to sign (e.g., "/rs:fit:300:200/{base64_url}")

    Returns:
        Base64url-encoded signature (without padding)
    """
    keys = _get_signing_keys()
    if keys is None:
        # No signing configured, use "insecure" prefix
        return "insecure"

    key, salt = keys

    # imgproxy expects: HMAC-SHA256(key, salt + path)
    msg = salt + path.encode("utf-8")
    signature = hmac.new(key, msg, hashlib.sha256).digest()

    # Base64url encode without padding
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def get_imgproxy_url(
    source_url: str,
    *,
    width: int = 0,
    height: int = 0,
    resize_type: str = "fit",
    format: str | None = None,
) -> str:
    """Generate a signed imgproxy URL for an image.

    Args:
        source_url: Original image URL to proxy
        width: Target width (0 = auto)
        height: Target height (0 = auto)
        resize_type: Resize mode - "fit", "fill", "auto" (default: "fit")
        format: Output format - "webp", "avif", "jpeg", "png" (default: auto-detect)

    Returns:
        Signed imgproxy URL path (e.g., "/imgproxy/{signature}/rs:fit:300:200/{base64}")
        Returns original URL if imgproxy is disabled or URL is empty.
    """
    # Check if imgproxy is enabled
    if not getattr(settings, "IMGPROXY_ENABLED", False):
        return source_url

    if not source_url:
        return source_url

    # Build processing options
    options_parts: list[str] = []

    if width or height:
        options_parts.append(f"rs:{resize_type}:{width}:{height}")

    if format:
        options_parts.append(f"f:{format}")

    options_path = "/".join(options_parts)
    if options_path:
        options_path = "/" + options_path

    # Encode source URL as base64 (obfuscates the original URL)
    encoded_url = _encode_url(source_url)
    path = f"{options_path}/{encoded_url}"

    # Sign the path
    signature = _sign_path(path)

    # Use IMGPROXY_URL from settings (supports CDN subdomains)
    base_url = getattr(settings, "IMGPROXY_URL", "/imgproxy").rstrip("/")
    return f"{base_url}/{signature}{path}"


def transform_image_urls(
    urls: list[str] | None,
    *,
    width: int = 0,
    height: int = 0,
) -> list[str]:
    """Transform a list of image URLs to imgproxy URLs.

    Args:
        urls: List of image URLs to transform
        width: Target width for all images (0 = auto)
        height: Target height for all images (0 = auto)

    Returns:
        List of transformed URLs (or original URLs if imgproxy disabled)
    """
    if not urls:
        return []

    return [get_imgproxy_url(url, width=width, height=height) for url in urls]


def get_imgproxy_url_for_s3(
    key: str,
    *,
    width: int,
    height: int,
    resize_type: str = "fill",
    bucket: str | None = None,
) -> str:
    """Sign an imgproxy URL whose source is ``s3://<bucket>/<key>``.

    Used for private user profile photos: imgproxy fetches via IAM (``IMGPROXY_USE_S3``)
    and we never expose the bucket directly. Bucket defaults to ``settings.S3_PHOTOS_BUCKET``.
    """
    target_bucket = bucket or getattr(settings, "S3_PHOTOS_BUCKET", None)
    if not target_bucket:
        return ""

    source_url = f"s3://{target_bucket}/{key}"
    return get_imgproxy_url(
        source_url, width=width, height=height, resize_type=resize_type
    )


# Avatar size presets — single source of truth, baked into API responses.
AVATAR_SIZES: dict[str, tuple[int, int]] = {
    "sm": (64, 64),
    "md": (128, 128),
    "lg": (256, 256),
}


def build_avatar_urls(key: str | None) -> dict[str, str] | None:
    """Return signed imgproxy URLs for the three avatar size presets.

    Returns ``None`` when the user has no photo (``key`` is falsy) so callers can
    serialize ``photo_urls: None`` to the frontend.
    """
    if not key:
        return None

    return {
        preset: get_imgproxy_url_for_s3(key, width=w, height=h, resize_type="fill")
        for preset, (w, h) in AVATAR_SIZES.items()
    }


def transform_thumbnail_url(
    url: str | None,
    *,
    width: int = 400,
    height: int = 300,
) -> str:
    """Transform a thumbnail URL with default thumbnail dimensions.

    Args:
        url: Thumbnail URL to transform
        width: Thumbnail width (default: 400)
        height: Thumbnail height (default: 300)

    Returns:
        Transformed URL or empty string if None
    """
    if not url:
        return ""

    return get_imgproxy_url(url, width=width, height=height)
