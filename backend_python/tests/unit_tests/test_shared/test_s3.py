"""Tests for the thin S3 wrapper (endpoint override + path-style addressing)."""

from unittest.mock import MagicMock, patch

import pytest

import app.shared.s3 as s3_module


@pytest.fixture(autouse=True)
def _clear_cache():
    s3_module.get_s3_client.cache_clear()
    yield
    s3_module.get_s3_client.cache_clear()


def test_get_s3_client_uses_endpoint_override_when_set() -> None:
    fake_settings = MagicMock()
    fake_settings.S3_PHOTOS_REGION = "us-east-1"
    fake_settings.S3_ENDPOINT_URL = "http://minio:9000"
    fake_settings.S3_FORCE_PATH_STYLE = True

    with (
        patch.object(s3_module, "settings", fake_settings),
        patch.object(s3_module, "boto3") as mock_boto,
    ):
        s3_module.get_s3_client()
        kwargs = mock_boto.client.call_args.kwargs
        assert kwargs["region_name"] == "us-east-1"
        assert kwargs["endpoint_url"] == "http://minio:9000"
        assert "config" in kwargs


def test_get_s3_client_omits_endpoint_in_cloud() -> None:
    fake_settings = MagicMock()
    fake_settings.S3_PHOTOS_REGION = "us-east-1"
    fake_settings.S3_ENDPOINT_URL = None
    fake_settings.S3_FORCE_PATH_STYLE = False

    with (
        patch.object(s3_module, "settings", fake_settings),
        patch.object(s3_module, "boto3") as mock_boto,
    ):
        s3_module.get_s3_client()
        kwargs = mock_boto.client.call_args.kwargs
        assert "endpoint_url" not in kwargs
        assert "config" not in kwargs


def test_put_object_requires_bucket() -> None:
    fake_settings = MagicMock()
    fake_settings.S3_PHOTOS_BUCKET = None
    with (
        patch.object(s3_module, "settings", fake_settings),
        pytest.raises(RuntimeError, match="S3_PHOTOS_BUCKET"),
    ):
        s3_module.put_object("k", b"x", content_type="image/jpeg")


def test_put_object_forwards_args() -> None:
    fake_settings = MagicMock()
    fake_settings.S3_PHOTOS_BUCKET = "b"
    client = MagicMock()
    with patch.object(s3_module, "settings", fake_settings):
        s3_module.put_object("k", b"x", content_type="image/jpeg", client=client)
    client.put_object.assert_called_once()
    kwargs = client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "b"
    assert kwargs["Key"] == "k"
    assert kwargs["ContentType"] == "image/jpeg"
    assert "immutable" in kwargs["CacheControl"]
