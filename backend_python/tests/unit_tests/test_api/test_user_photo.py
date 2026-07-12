"""Unit tests for the profile photo API endpoints.

Covers the exception → HTTP status mapping in ``app/api/user.py`` for both
``PUT /api/user/me/photo`` and ``DELETE /api/user/me/photo``. The service
layer is mocked — these tests only assert the HTTP/handler wiring.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile, status

from app.api.user import delete_my_photo, upload_my_photo
from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.exceptions import (
    InvalidPhotoError,
    PhotoTooLargeError,
    UnsupportedPhotoTypeError,
)
from app.domains.user.schemas import PhotoUrlsResponse, UserPhotoResponse, UserPublic


@pytest.fixture
def current_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="Photo",
        last_name="Tester",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        discount_eligible=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_upload_file(
    data: bytes = b"\xff\xd8\xff\xe0jpeg-bytes",
    *,
    filename: str = "avatar.jpg",
    content_type: str = "image/jpeg",
    size: int | None = None,
) -> UploadFile:
    """Build a Starlette ``UploadFile`` with the given bytes/MIME/size."""
    file = UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        size=size if size is not None else len(data),
        headers=None,  # type: ignore[arg-type]
    )
    # Starlette resolves content_type lazily from headers; set it directly for tests.
    file.headers = {"content-type": content_type}  # type: ignore[assignment]
    return file


@pytest.mark.asyncio
async def test_upload_photo_success_returns_200_body(current_user: UserPublic) -> None:
    expected = UserPhotoResponse(
        photo_key="users/u/avatar/abc.jpg",
        photo_urls=PhotoUrlsResponse(sm="/sm", md="/md", lg="/lg"),
    )
    with patch(
        "app.domains.user.photo_service.upload_profile_photo",
        new=AsyncMock(return_value=expected),
    ) as mock_upload:
        result = await upload_my_photo(
            file=_make_upload_file(), current_user=current_user
        )

    assert result == expected
    mock_upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_photo_short_circuits_oversize_via_file_size(
    current_user: UserPublic,
) -> None:
    """Files whose Content-Length exceeds the limit must 413 without buffering."""
    big = _make_upload_file(size=99 * 1024 * 1024)

    with (
        patch(
            "app.domains.user.photo_service.upload_profile_photo",
            new=AsyncMock(),
        ) as mock_upload,
        pytest.raises(HTTPException) as exc,
    ):
        await upload_my_photo(file=big, current_user=current_user)

    assert exc.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    mock_upload.assert_not_called()


@pytest.mark.asyncio
async def test_upload_photo_too_large_from_service_returns_413(
    current_user: UserPublic,
) -> None:
    with (
        patch(
            "app.domains.user.photo_service.upload_profile_photo",
            new=AsyncMock(side_effect=PhotoTooLargeError(max_bytes=5 * 1024 * 1024)),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await upload_my_photo(file=_make_upload_file(), current_user=current_user)

    assert exc.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_upload_photo_unsupported_type_returns_415(
    current_user: UserPublic,
) -> None:
    with (
        patch(
            "app.domains.user.photo_service.upload_profile_photo",
            new=AsyncMock(side_effect=UnsupportedPhotoTypeError("image/gif")),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await upload_my_photo(
            file=_make_upload_file(content_type="image/gif"),
            current_user=current_user,
        )

    assert exc.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


@pytest.mark.asyncio
async def test_upload_photo_invalid_returns_400(current_user: UserPublic) -> None:
    with (
        patch(
            "app.domains.user.photo_service.upload_profile_photo",
            new=AsyncMock(side_effect=InvalidPhotoError("corrupt bytes")),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await upload_my_photo(file=_make_upload_file(), current_user=current_user)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_photo_with_existing_returns_204(current_user: UserPublic) -> None:
    with patch(
        "app.domains.user.photo_service.delete_profile_photo",
        new=AsyncMock(return_value=None),
    ) as mock_delete:
        response = await delete_my_photo(current_user=current_user)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_delete.assert_awaited_once_with(current_user.id)


@pytest.mark.asyncio
async def test_delete_photo_when_none_set_is_idempotent_204(
    current_user: UserPublic,
) -> None:
    """Service returns None when there's nothing to delete; handler still 204s."""
    with patch(
        "app.domains.user.photo_service.delete_profile_photo",
        new=AsyncMock(return_value=None),
    ):
        response = await delete_my_photo(current_user=current_user)

    assert response.status_code == status.HTTP_204_NO_CONTENT
