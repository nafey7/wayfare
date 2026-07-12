"""Profile photo upload/delete orchestration.

Responsibilities:
- Validate the upload (size, MIME, dimensions, decompression-bomb guard).
- Re-encode through Pillow to strip EXIF (incl. GPS) and normalize orientation.
- PutObject to the photos bucket.
- Persist ``photo_key`` on the user document.
- Replace flow: best-effort delete of the previous object.
- Compensate on DB failure by deleting the just-uploaded object.

Designed to be readable and dependency-light. Tests inject a stub S3 client
into the module-level functions via the ``s3_client`` kwarg.
"""

from __future__ import annotations

import asyncio
import io
import logging
import uuid
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.shared import s3 as s3_module
from app.shared.imgproxy import build_avatar_urls

from . import repository
from .exceptions import (
    InvalidPhotoError,
    PhotoTooLargeError,
    UnsupportedPhotoTypeError,
)
from .schemas import PhotoUrlsResponse, UserPhotoResponse

logger = logging.getLogger(__name__)

# Pillow decompression-bomb guard. Set once at import (module-global; mutating
# this per-request from async handlers races between coroutines).
Image.MAX_IMAGE_PIXELS = settings.AVATAR_MAX_DIMENSION**2 * 4

# Pillow → output format / extension / content-type mapping.
_FORMAT_TO_EXT: dict[str, str] = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_MIME_TO_FORMAT: dict[str, str] = {v: k for k, v in _FORMAT_TO_MIME.items()}


def _allowed_mimes() -> set[str]:
    raw = settings.AVATAR_ALLOWED_MIME or ""
    return {m.strip() for m in raw.split(",") if m.strip()}


def _validate_and_reencode(raw: bytes, declared_mime: str | None) -> tuple[bytes, str]:
    """Validate raw bytes and return ``(stripped_bytes, output_mime)``.

    Raises domain-specific exceptions on rejection.
    """
    max_bytes = settings.AVATAR_MAX_BYTES
    if len(raw) > max_bytes:
        raise PhotoTooLargeError(max_bytes=max_bytes)
    if not raw:
        raise InvalidPhotoError("Empty upload")

    allowed = _allowed_mimes()
    if declared_mime and declared_mime not in allowed:
        raise UnsupportedPhotoTypeError(declared_mime)

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError) as e:
        raise InvalidPhotoError(f"Image could not be decoded: {e}") from e

    fmt = (img.format or "").upper()
    if fmt not in _FORMAT_TO_MIME:
        raise UnsupportedPhotoTypeError(fmt or "unknown")

    sniffed_mime = _FORMAT_TO_MIME[fmt]
    if sniffed_mime not in allowed:
        raise UnsupportedPhotoTypeError(sniffed_mime)

    w, h = img.size
    if w > settings.AVATAR_MAX_DIMENSION or h > settings.AVATAR_MAX_DIMENSION:
        raise InvalidPhotoError(
            f"Image dimensions {w}x{h} exceed max of {settings.AVATAR_MAX_DIMENSION}px"
        )

    # Re-encode in a fresh image to drop EXIF (incl. GPS). For JPEG/WEBP also
    # apply orientation normalization based on EXIF tag before stripping.
    from PIL import ImageOps

    img = ImageOps.exif_transpose(img)

    out = io.BytesIO()
    if fmt == "JPEG":
        rgb = img.convert("RGB")
        rgb.save(out, format="JPEG", quality=95, optimize=True)
    elif fmt == "PNG":
        img.save(out, format="PNG", optimize=True)
    else:  # WEBP
        img.save(out, format="WEBP", quality=95, method=6)

    return out.getvalue(), sniffed_mime


def _build_key(user_id: str, mime: str) -> str:
    ext = _FORMAT_TO_EXT[_MIME_TO_FORMAT[mime]]
    return f"users/{user_id}/avatar/{uuid.uuid4().hex}.{ext}"


async def upload_profile_photo(
    user_id: str,
    raw_bytes: bytes,
    *,
    declared_mime: str | None,
    s3_client: Any | None = None,
) -> UserPhotoResponse:
    """Validate, strip EXIF, upload to S3, persist photo_key, replace previous."""
    if not settings.S3_PHOTOS_BUCKET:
        raise RuntimeError("S3_PHOTOS_BUCKET is not configured")

    stripped, mime = await asyncio.to_thread(
        _validate_and_reencode, raw_bytes, declared_mime
    )
    new_key = _build_key(user_id, mime)

    previous_key = await repository.get_photo_key(user_id)

    await asyncio.to_thread(
        lambda: s3_module.put_object(
            new_key, stripped, content_type=mime, client=s3_client
        )
    )

    persisted = await repository.set_photo_key(user_id, new_key)
    if not persisted:
        # Compensate: don't leave an orphan in S3 when the DB write didn't happen.
        try:
            await asyncio.to_thread(
                lambda: s3_module.delete_object(new_key, client=s3_client)
            )
        except Exception:
            logger.exception(
                "avatar.compensating_delete_failed key=%s user_id=%s",
                new_key,
                user_id,
            )
        raise RuntimeError("Failed to persist photo_key for user")

    if previous_key and previous_key != new_key:
        try:
            await asyncio.to_thread(
                lambda: s3_module.delete_object(previous_key, client=s3_client)
            )
        except Exception:
            logger.warning(
                "avatar.old_object.delete_failed old_key=%s new_key=%s user_id=%s",
                previous_key,
                new_key,
                user_id,
                exc_info=True,
            )

    photo_urls_dict = build_avatar_urls(new_key) or {}
    logger.info(
        "avatar.upload.success user_id=%s key=%s mime=%s bytes=%s",
        user_id,
        new_key,
        mime,
        len(stripped),
    )
    return UserPhotoResponse(
        photo_key=new_key,
        photo_urls=PhotoUrlsResponse(**photo_urls_dict),
    )


async def delete_profile_photo(
    user_id: str,
    *,
    s3_client: Any | None = None,
) -> None:
    """Delete the user's current photo (if any). Idempotent."""
    current = await repository.get_photo_key(user_id)
    if not current:
        return

    await repository.set_photo_key(user_id, None)

    try:
        await asyncio.to_thread(
            lambda: s3_module.delete_object(current, client=s3_client)
        )
    except Exception:
        logger.warning(
            "avatar.delete.s3_failed key=%s user_id=%s",
            current,
            user_id,
            exc_info=True,
        )

    logger.info("avatar.delete.success user_id=%s key=%s", user_id, current)
