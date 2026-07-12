"""Tests for the profile photo service (validation, S3 ops, replace flow)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.domains.user import photo_service
from app.domains.user.exceptions import (
    InvalidPhotoError,
    PhotoTooLargeError,
    UnsupportedPhotoTypeError,
)


def _make_jpeg_bytes(size: tuple[int, int] = (200, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def fake_settings() -> MagicMock:
    s = MagicMock()
    s.S3_PHOTOS_BUCKET = "test-bucket"
    s.AVATAR_MAX_BYTES = 5 * 1024 * 1024
    s.AVATAR_ALLOWED_MIME = "image/jpeg,image/png,image/webp"
    s.AVATAR_MAX_DIMENSION = 4096
    return s


@pytest.fixture(autouse=True)
def _patch_settings(fake_settings: MagicMock):
    with (
        patch.object(photo_service, "settings", fake_settings),
        patch("app.shared.s3.settings", fake_settings),
    ):
        yield


@pytest.mark.asyncio
async def test_upload_happy_path() -> None:
    s3_client = MagicMock()
    with (
        patch.object(
            photo_service.repository, "get_photo_key", AsyncMock(return_value=None)
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=True)
        ),
    ):
        result = await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )
    assert result.photo_key.startswith("users/u1/avatar/")
    assert result.photo_key.endswith(".jpg")
    s3_client.put_object.assert_called_once()
    assert s3_client.put_object.call_args.kwargs["ContentType"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_replace_deletes_previous() -> None:
    s3_client = MagicMock()
    with (
        patch.object(
            photo_service.repository,
            "get_photo_key",
            AsyncMock(return_value="users/u1/avatar/old.jpg"),
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=True)
        ),
    ):
        await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )
    delete_keys = [c.kwargs["Key"] for c in s3_client.delete_object.call_args_list]
    assert "users/u1/avatar/old.jpg" in delete_keys


@pytest.mark.asyncio
async def test_upload_old_delete_failure_does_not_fail_request() -> None:
    s3_client = MagicMock()
    s3_client.delete_object.side_effect = RuntimeError("boom")
    with (
        patch.object(
            photo_service.repository,
            "get_photo_key",
            AsyncMock(return_value="users/u1/avatar/old.jpg"),
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=True)
        ),
    ):
        result = await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )
    assert result.photo_key.startswith("users/u1/avatar/")


@pytest.mark.asyncio
async def test_db_write_failure_compensates_s3() -> None:
    s3_client = MagicMock()
    with (
        patch.object(
            photo_service.repository, "get_photo_key", AsyncMock(return_value=None)
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=False)
        ),
        pytest.raises(RuntimeError),
    ):
        await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )
    # New object must be cleaned up.
    s3_client.delete_object.assert_called_once()


@pytest.mark.asyncio
async def test_reject_oversize(fake_settings: MagicMock) -> None:
    fake_settings.AVATAR_MAX_BYTES = 100
    s3_client = MagicMock()
    with pytest.raises(PhotoTooLargeError):
        await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )


@pytest.mark.asyncio
async def test_reject_bad_declared_mime() -> None:
    s3_client = MagicMock()
    with pytest.raises(UnsupportedPhotoTypeError):
        await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(),
            declared_mime="image/gif",
            s3_client=s3_client,
        )


@pytest.mark.asyncio
async def test_reject_unidentifiable_bytes() -> None:
    s3_client = MagicMock()
    with pytest.raises(InvalidPhotoError):
        await photo_service.upload_profile_photo(
            "u1",
            b"not-an-image" * 100,
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )


@pytest.mark.asyncio
async def test_reject_oversize_dimensions(fake_settings: MagicMock) -> None:
    fake_settings.AVATAR_MAX_DIMENSION = 100
    s3_client = MagicMock()
    with pytest.raises(InvalidPhotoError):
        await photo_service.upload_profile_photo(
            "u1",
            _make_jpeg_bytes(size=(500, 500)),
            declared_mime="image/jpeg",
            s3_client=s3_client,
        )


@pytest.mark.asyncio
async def test_delete_when_present() -> None:
    s3_client = MagicMock()
    with (
        patch.object(
            photo_service.repository,
            "get_photo_key",
            AsyncMock(return_value="users/u1/avatar/cur.jpg"),
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=True)
        ),
    ):
        await photo_service.delete_profile_photo("u1", s3_client=s3_client)
    s3_client.delete_object.assert_called_once()


@pytest.mark.asyncio
async def test_delete_when_absent_is_idempotent() -> None:
    s3_client = MagicMock()
    with patch.object(
        photo_service.repository, "get_photo_key", AsyncMock(return_value=None)
    ):
        await photo_service.delete_profile_photo("u1", s3_client=s3_client)
    s3_client.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_upload_accepts_png() -> None:
    s3_client = MagicMock()
    with (
        patch.object(
            photo_service.repository, "get_photo_key", AsyncMock(return_value=None)
        ),
        patch.object(
            photo_service.repository, "set_photo_key", AsyncMock(return_value=True)
        ),
    ):
        result = await photo_service.upload_profile_photo(
            "u1",
            _make_png_bytes(),
            declared_mime="image/png",
            s3_client=s3_client,
        )
    assert result.photo_key.endswith(".png")
