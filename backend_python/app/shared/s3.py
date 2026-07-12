"""Thin S3 client wrapper.

Uses the boto3 default credential chain (ECS task role in cloud, MinIO root
creds via env vars locally). When ``S3_ENDPOINT_URL`` is set we override the
endpoint and switch to path-style addressing (required by MinIO).

Designed so tests can monkey-patch ``get_s3_client`` or pass a stub client
into ``put_object`` / ``delete_object``.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_s3_client() -> Any:
    """Return a cached boto3 S3 client honoring local endpoint overrides."""
    kwargs: dict[str, Any] = {"region_name": settings.S3_PHOTOS_REGION}

    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

    if settings.S3_FORCE_PATH_STYLE:
        kwargs["config"] = Config(s3={"addressing_style": "path"})

    return boto3.client("s3", **kwargs)


def put_object(
    key: str,
    body: bytes,
    *,
    content_type: str,
    cache_control: str = "public, max-age=31536000, immutable",
    client: Any | None = None,
) -> None:
    """Upload ``body`` to the configured photos bucket under ``key``."""
    bucket = settings.S3_PHOTOS_BUCKET
    if not bucket:
        raise RuntimeError("S3_PHOTOS_BUCKET is not configured")

    (client or get_s3_client()).put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        CacheControl=cache_control,
    )


def delete_object(key: str, *, client: Any | None = None) -> None:
    """Delete ``key`` from the photos bucket. Idempotent — S3 200s on miss."""
    bucket = settings.S3_PHOTOS_BUCKET
    if not bucket:
        raise RuntimeError("S3_PHOTOS_BUCKET is not configured")

    (client or get_s3_client()).delete_object(Bucket=bucket, Key=key)
