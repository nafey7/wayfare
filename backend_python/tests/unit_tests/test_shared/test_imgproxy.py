"""Unit tests for the imgproxy URL signing utility.

Tests cover:
- Base64 URL encoding
- HMAC-SHA256 signing
- URL generation with various options
- Batch URL transformation
- Configuration handling (enabled/disabled, missing keys)
"""

import base64
import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

from app.shared.imgproxy import (
    _encode_url,
    _get_signing_keys,
    _sign_path,
    get_imgproxy_url,
    transform_image_urls,
    transform_thumbnail_url,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_settings_enabled() -> MagicMock:
    """Mock settings with imgproxy enabled and valid keys."""
    settings = MagicMock()
    settings.IMGPROXY_ENABLED = True
    settings.IMGPROXY_URL = "/imgproxy"  # Default relative path
    # Valid hex-encoded keys (32 bytes each)
    settings.IMGPROXY_KEY = "0" * 64  # 32 bytes as hex
    settings.IMGPROXY_SALT = "1" * 64  # 32 bytes as hex
    return settings


@pytest.fixture
def mock_settings_disabled() -> MagicMock:
    """Mock settings with imgproxy disabled."""
    settings = MagicMock()
    settings.IMGPROXY_ENABLED = False
    settings.IMGPROXY_KEY = "0" * 64
    settings.IMGPROXY_SALT = "1" * 64
    return settings


@pytest.fixture
def mock_settings_no_keys() -> MagicMock:
    """Mock settings with imgproxy enabled but no keys."""
    settings = MagicMock()
    settings.IMGPROXY_ENABLED = True
    settings.IMGPROXY_URL = "/imgproxy"  # Default relative path
    settings.IMGPROXY_KEY = None
    settings.IMGPROXY_SALT = None
    return settings


@pytest.fixture(autouse=True)
def clear_signing_keys_cache() -> None:
    """Clear the LRU cache before each test."""
    _get_signing_keys.cache_clear()


# ==============================================================================
# TESTS - URL Encoding
# ==============================================================================


class TestEncodeUrl:
    """Tests for base64 URL encoding."""

    def test_encode_simple_url(self) -> None:
        """Test encoding a simple URL."""
        url = "https://example.com/image.jpg"
        encoded = _encode_url(url)

        # Verify it's valid base64url (no padding)
        assert "=" not in encoded
        assert "+" not in encoded
        assert "/" not in encoded

        # Verify decoding works
        # Add padding back for decoding
        padded = encoded + "=" * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        assert decoded == url

    def test_encode_url_with_special_chars(self) -> None:
        """Test encoding URL with special characters."""
        url = "https://example.com/path?foo=bar&baz=qux#anchor"
        encoded = _encode_url(url)

        # Should be valid base64url
        assert "=" not in encoded
        padded = encoded + "=" * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        assert decoded == url

    def test_encode_url_with_unicode(self) -> None:
        """Test encoding URL with unicode characters."""
        url = "https://example.com/café/日本語.jpg"
        encoded = _encode_url(url)

        padded = encoded + "=" * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        assert decoded == url


# ==============================================================================
# TESTS - Signing Keys
# ==============================================================================


class TestGetSigningKeys:
    """Tests for signing key retrieval."""

    def test_returns_keys_when_configured(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test returns decoded keys when properly configured."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            keys = _get_signing_keys()

            assert keys is not None
            key, salt = keys
            assert isinstance(key, bytes)
            assert isinstance(salt, bytes)
            assert len(key) == 32  # 64 hex chars = 32 bytes
            assert len(salt) == 32

    def test_returns_none_when_key_missing(self) -> None:
        """Test returns None when key is missing."""
        settings = MagicMock()
        settings.IMGPROXY_KEY = None
        settings.IMGPROXY_SALT = "1" * 64

        with patch("app.shared.imgproxy.settings", settings):
            _get_signing_keys.cache_clear()
            keys = _get_signing_keys()
            assert keys is None

    def test_returns_none_when_salt_missing(self) -> None:
        """Test returns None when salt is missing."""
        settings = MagicMock()
        settings.IMGPROXY_KEY = "0" * 64
        settings.IMGPROXY_SALT = None

        with patch("app.shared.imgproxy.settings", settings):
            _get_signing_keys.cache_clear()
            keys = _get_signing_keys()
            assert keys is None

    def test_returns_none_when_invalid_hex(self) -> None:
        """Test returns None when keys are not valid hex."""
        settings = MagicMock()
        settings.IMGPROXY_KEY = "not-valid-hex"
        settings.IMGPROXY_SALT = "also-not-hex"

        with patch("app.shared.imgproxy.settings", settings):
            _get_signing_keys.cache_clear()
            keys = _get_signing_keys()
            assert keys is None

    def test_caches_result(self, mock_settings_enabled: MagicMock) -> None:
        """Test that result is cached."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            keys1 = _get_signing_keys()
            keys2 = _get_signing_keys()

            assert keys1 is keys2  # Same object (cached)


# ==============================================================================
# TESTS - Path Signing
# ==============================================================================


class TestSignPath:
    """Tests for HMAC path signing."""

    def test_sign_path_with_keys(self, mock_settings_enabled: MagicMock) -> None:
        """Test signing a path produces valid signature."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            signature = _sign_path("/rs:fit:200:150/encoded_url")

            # Should be base64url without padding
            assert "=" not in signature
            assert "+" not in signature
            assert "/" not in signature
            assert len(signature) > 0

    def test_sign_path_returns_insecure_without_keys(
        self, mock_settings_no_keys: MagicMock
    ) -> None:
        """Test returns 'insecure' when keys not configured."""
        with patch("app.shared.imgproxy.settings", mock_settings_no_keys):
            signature = _sign_path("/rs:fit:200:150/encoded_url")
            assert signature == "insecure"

    def test_sign_path_is_deterministic(self, mock_settings_enabled: MagicMock) -> None:
        """Test same path produces same signature."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            path = "/rs:fit:200:150/encoded_url"
            sig1 = _sign_path(path)
            sig2 = _sign_path(path)
            assert sig1 == sig2

    def test_different_paths_produce_different_signatures(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test different paths produce different signatures."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            sig1 = _sign_path("/rs:fit:200:150/url1")
            sig2 = _sign_path("/rs:fit:200:150/url2")
            assert sig1 != sig2

    def test_signature_matches_manual_calculation(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test signature matches manually calculated HMAC."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            path = "/rs:fit:200:150/test"
            signature = _sign_path(path)

            # Manual calculation
            key = bytes.fromhex("0" * 64)
            salt = bytes.fromhex("1" * 64)
            msg = salt + path.encode("utf-8")
            expected = hmac.new(key, msg, hashlib.sha256).digest()
            expected_b64 = (
                base64.urlsafe_b64encode(expected).rstrip(b"=").decode("ascii")
            )

            assert signature == expected_b64


# ==============================================================================
# TESTS - URL Generation
# ==============================================================================


class TestGetImgproxyUrl:
    """Tests for imgproxy URL generation."""

    def test_returns_original_when_disabled(
        self, mock_settings_disabled: MagicMock
    ) -> None:
        """Test returns original URL when imgproxy disabled."""
        with patch("app.shared.imgproxy.settings", mock_settings_disabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url)
            assert result == url

    def test_returns_original_when_empty(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test returns original URL when empty."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            assert get_imgproxy_url("") == ""
            assert get_imgproxy_url(None) is None  # type: ignore[arg-type]

    def test_generates_signed_url(self, mock_settings_enabled: MagicMock) -> None:
        """Test generates properly formatted signed URL."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url)

            assert result.startswith("/imgproxy/")
            # Should have signature followed by base64 encoded URL
            parts = result.split("/")
            assert len(parts) >= 3
            assert parts[1] == "imgproxy"
            # parts[2] is signature, parts[3] is encoded URL

    def test_includes_resize_options(self, mock_settings_enabled: MagicMock) -> None:
        """Test includes resize options when specified."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url, width=200, height=150)

            assert "rs:fit:200:150" in result

    def test_custom_resize_type(self, mock_settings_enabled: MagicMock) -> None:
        """Test custom resize type."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url, width=200, height=150, resize_type="fill")

            assert "rs:fill:200:150" in result

    def test_includes_format_option(self, mock_settings_enabled: MagicMock) -> None:
        """Test includes format option when specified."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url, format="webp")

            assert "f:webp" in result

    def test_width_only(self, mock_settings_enabled: MagicMock) -> None:
        """Test with width only (height=0)."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url, width=200)

            assert "rs:fit:200:0" in result

    def test_height_only(self, mock_settings_enabled: MagicMock) -> None:
        """Test with height only (width=0)."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url, height=150)

            assert "rs:fit:0:150" in result

    def test_no_resize_options(self, mock_settings_enabled: MagicMock) -> None:
        """Test without resize options."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url)

            # Should not have resize options
            assert "rs:" not in result

    def test_insecure_url_without_keys(self, mock_settings_no_keys: MagicMock) -> None:
        """Test generates insecure URL when keys not configured."""
        with patch("app.shared.imgproxy.settings", mock_settings_no_keys):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url)

            assert result.startswith("/imgproxy/insecure/")

    def test_uses_cdn_url_when_configured(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test uses absolute CDN URL when IMGPROXY_URL is set to CDN subdomain."""
        mock_settings_enabled.IMGPROXY_URL = "https://cdn.myvoya.ai/imgproxy"
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/image.jpg"
            result = get_imgproxy_url(url)

            assert result.startswith("https://cdn.myvoya.ai/imgproxy/")
            # Should still have signature and encoded URL
            assert "/imgproxy/" in result


# ==============================================================================
# TESTS - Batch Transformation
# ==============================================================================


class TestTransformImageUrls:
    """Tests for batch URL transformation."""

    def test_transforms_list_of_urls(self, mock_settings_enabled: MagicMock) -> None:
        """Test transforms a list of URLs."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            urls = [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg",
                "https://example.com/image3.jpg",
            ]
            results = transform_image_urls(urls)

            assert len(results) == 3
            for result in results:
                assert result.startswith("/imgproxy/")

    def test_returns_empty_list_for_none(self) -> None:
        """Test returns empty list for None input."""
        result = transform_image_urls(None)
        assert result == []

    def test_returns_empty_list_for_empty(self) -> None:
        """Test returns empty list for empty input."""
        result = transform_image_urls([])
        assert result == []

    def test_passes_dimensions(self, mock_settings_enabled: MagicMock) -> None:
        """Test passes width/height to all URLs."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            urls = ["https://example.com/image.jpg"]
            results = transform_image_urls(urls, width=300, height=200)

            assert len(results) == 1
            assert "rs:fit:300:200" in results[0]


# ==============================================================================
# TESTS - Thumbnail Transformation
# ==============================================================================


class TestTransformThumbnailUrl:
    """Tests for thumbnail URL transformation."""

    def test_transforms_thumbnail_with_defaults(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test transforms thumbnail with default dimensions (400x300)."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/thumb.jpg"
            result = transform_thumbnail_url(url)

            assert result.startswith("/imgproxy/")
            assert "rs:fit:400:300" in result

    def test_transforms_thumbnail_with_custom_dimensions(
        self, mock_settings_enabled: MagicMock
    ) -> None:
        """Test transforms thumbnail with custom dimensions."""
        with patch("app.shared.imgproxy.settings", mock_settings_enabled):
            url = "https://example.com/thumb.jpg"
            result = transform_thumbnail_url(url, width=200, height=150)

            assert "rs:fit:200:150" in result

    def test_returns_empty_string_for_none(self) -> None:
        """Test returns empty string for None input."""
        result = transform_thumbnail_url(None)
        assert result == ""

    def test_returns_empty_string_for_empty(self) -> None:
        """Test returns empty string for empty input."""
        result = transform_thumbnail_url("")
        assert result == ""
