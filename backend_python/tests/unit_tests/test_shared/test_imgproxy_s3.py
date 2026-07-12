"""Tests for the s3:// imgproxy helpers used by user profile photos."""

from unittest.mock import MagicMock, patch

import pytest

from app.shared.imgproxy import (
    AVATAR_SIZES,
    build_avatar_urls,
    get_imgproxy_url_for_s3,
)


@pytest.fixture
def mock_settings_enabled() -> MagicMock:
    s = MagicMock()
    s.IMGPROXY_ENABLED = True
    s.IMGPROXY_URL = "/imgproxy"
    s.IMGPROXY_KEY = "0" * 64
    s.IMGPROXY_SALT = "1" * 64
    s.S3_PHOTOS_BUCKET = "myvoya-test-photos"
    return s


def test_get_imgproxy_url_for_s3_signs_path(mock_settings_enabled: MagicMock) -> None:
    with patch("app.shared.imgproxy.settings", mock_settings_enabled):
        url = get_imgproxy_url_for_s3("users/abc/avatar/u.jpg", width=128, height=128)
    assert url.startswith("/imgproxy/")
    assert "rs:fill:128:128" in url


def test_build_avatar_urls_returns_three_sizes(
    mock_settings_enabled: MagicMock,
) -> None:
    with patch("app.shared.imgproxy.settings", mock_settings_enabled):
        urls = build_avatar_urls("users/abc/avatar/u.jpg")
    assert urls is not None
    assert set(urls.keys()) == {"sm", "md", "lg"}
    for preset, (w, h) in AVATAR_SIZES.items():
        assert f"rs:fill:{w}:{h}" in urls[preset]


def test_build_avatar_urls_none_when_no_key(
    mock_settings_enabled: MagicMock,
) -> None:
    with patch("app.shared.imgproxy.settings", mock_settings_enabled):
        assert build_avatar_urls(None) is None
        assert build_avatar_urls("") is None


def test_get_imgproxy_url_for_s3_empty_without_bucket() -> None:
    s = MagicMock()
    s.IMGPROXY_ENABLED = True
    s.IMGPROXY_URL = "/imgproxy"
    s.IMGPROXY_KEY = "0" * 64
    s.IMGPROXY_SALT = "1" * 64
    s.S3_PHOTOS_BUCKET = None
    with patch("app.shared.imgproxy.settings", s):
        assert get_imgproxy_url_for_s3("u.jpg", width=64, height=64) == ""
