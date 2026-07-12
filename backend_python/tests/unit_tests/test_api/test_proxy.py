"""Unit tests for image proxy API endpoint."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.proxy import router

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create test client for proxy API testing."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_httpx_get():
    """Mock httpx.AsyncClient.get for testing image fetching."""
    with patch("app.api.proxy.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.content = b"fake_image_data"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_async_client
        yield mock_async_client


# ==============================================================================
# DNS RESOLUTION TESTS (Non-blocking behavior)
# ==============================================================================


@pytest.mark.asyncio
async def test_dns_resolution_is_non_blocking():
    """Test that DNS resolution uses executor and doesn't block event loop."""
    from app.api.proxy import proxy_image

    # Mock the executor to verify it's called
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]  # example.com IP
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        # Mock other parts to avoid actual network calls
        with (
            patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
            patch("app.api.proxy.httpx.AsyncClient") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = b"fake_image"
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_response.raise_for_status = MagicMock()

            mock_async_client = AsyncMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            # This should not block
            url = "https://example.com/image.jpg"
            result = await proxy_image(url=url)

            # Verify executor was called
            mock_executor.assert_called_once()
            assert result is not None


# ==============================================================================
# SSRF PROTECTION TESTS (Internal IP Blocking)
# ==============================================================================


@pytest.mark.asyncio
async def test_blocks_localhost():
    """Test that localhost URLs are blocked."""
    from app.api.proxy import proxy_image

    test_cases = [
        ("http://localhost/image.jpg", 403),
        ("http://127.0.0.1/image.jpg", 403),
        (
            "http://::1/image.jpg",
            400,
        ),  # IPv6 localhost may be rejected as invalid URL format
        ("http://0.0.0.0/image.jpg", 403),
    ]

    for url, expected_status in test_cases:
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == expected_status
        if expected_status == 403:
            assert (
                "Internal IPs" in exc_info.value.detail
                or "localhost" in exc_info.value.detail
            )


@pytest.mark.asyncio
async def test_blocks_aws_metadata_service():
    """Test that AWS metadata service IP is blocked."""
    from app.api.proxy import proxy_image

    url = "http://169.254.169.254/latest/meta-data/"
    with pytest.raises(HTTPException) as exc_info:
        await proxy_image(url=url)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_blocks_private_ip_addresses():
    """Test that private IP addresses are blocked."""
    from app.api.proxy import proxy_image

    private_ips = [
        "192.168.1.1",  # Private
        "10.0.0.1",  # Private
        "172.16.0.1",  # Private
    ]

    for ip in private_ips:
        url = f"http://{ip}/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_blocks_loopback_addresses():
    """Test that loopback addresses are blocked."""
    from app.api.proxy import proxy_image

    loopback_ips = ["127.0.0.1", "127.1.1.1"]

    for ip in loopback_ips:
        url = f"http://{ip}/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_blocks_link_local_addresses():
    """Test that link-local addresses are blocked."""
    from app.api.proxy import proxy_image

    # Link-local addresses (169.254.0.0/16)
    link_local_ip = "169.254.1.1"
    url = f"http://{link_local_ip}/image.jpg"
    with pytest.raises(HTTPException) as exc_info:
        await proxy_image(url=url)
    assert exc_info.value.status_code == 403


# ==============================================================================
# DNS REBINDING PROTECTION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_blocks_dns_rebinding_to_private_ip():
    """Test that hostnames resolving to private IPs are blocked (DNS rebinding protection)."""
    from app.api.proxy import proxy_image

    # Mock DNS resolution to return private IP
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        # Return private IP address
        mock_executor.return_value = ["192.168.1.100"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://malicious.example.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403
        assert "internal" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_blocks_dns_rebinding_to_loopback():
    """Test that hostnames resolving to loopback IPs are blocked."""
    from app.api.proxy import proxy_image

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["127.0.0.1"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://evil.example.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_blocks_dns_rebinding_to_link_local():
    """Test that hostnames resolving to link-local IPs are blocked."""
    from app.api.proxy import proxy_image

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["169.254.1.1"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://rebind.example.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_allows_public_ip_resolution():
    """Test that hostnames resolving to public IPs are allowed."""
    from app.api.proxy import proxy_image

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        # Return public IP address
        mock_executor.return_value = ["93.184.216.34"]  # example.com
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        with (
            patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
            patch("app.api.proxy.httpx.AsyncClient") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = b"fake_image"
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_response.raise_for_status = MagicMock()

            mock_async_client = AsyncMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            url = "http://example.com/image.jpg"
            result = await proxy_image(url=url)
            assert result is not None


@pytest.mark.asyncio
async def test_blocks_on_dns_resolution_failure():
    """Test that DNS resolution failures result in blocking (fail-safe)."""
    from app.api.proxy import proxy_image

    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        # Simulate DNS resolution failure
        mock_executor.side_effect = socket.gaierror("Name or service not known")
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://nonexistent-domain-12345.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_handles_multiple_resolved_ips():
    """Test that all resolved IPs are checked (some may be private, some public)."""
    from app.api.proxy import proxy_image

    # Mock DNS to return multiple IPs, one private
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        # Return mix of public and private IPs
        mock_executor.return_value = ["93.184.216.34", "192.168.1.1", "8.8.8.8"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://mixed.example.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        # Should block because one IP is private
        assert exc_info.value.status_code == 403


# ==============================================================================
# DOMAIN WHITELIST TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_allows_whitelisted_domains():
    """Test that whitelisted domains are allowed when allow_all is False."""
    from app.api.proxy import proxy_image

    whitelisted_domains = [
        "dynamic-media-cdn.tripadvisor.com",
        "media-cdn.tripadvisor.com",
        "cf.bstatic.com",
        "photos.hotelbeds.com",
    ]

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", False),
        patch("asyncio.get_event_loop") as mock_loop,
        patch("app.api.proxy.httpx.AsyncClient") as mock_client,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        mock_response = MagicMock()
        mock_response.content = b"fake_image"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client

        for domain in whitelisted_domains:
            url = f"https://{domain}/image.jpg"
            result = await proxy_image(url=url)
            assert result is not None


@pytest.mark.asyncio
async def test_allows_whitelisted_subdomains():
    """Test that subdomains of whitelisted domains are allowed."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", False),
        patch("asyncio.get_event_loop") as mock_loop,
        patch("app.api.proxy.httpx.AsyncClient") as mock_client,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        mock_response = MagicMock()
        mock_response.content = b"fake_image"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client

        # Test subdomain of travelapi.com
        url = "https://api.travelapi.com/image.jpg"
        result = await proxy_image(url=url)
        assert result is not None


@pytest.mark.asyncio
async def test_blocks_non_whitelisted_domains_when_allow_all_false():
    """Test that non-whitelisted domains are blocked when allow_all is False."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", False),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]  # Public IP
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "http://unauthorized-domain.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 403
        assert "not allowed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_allows_all_domains_when_allow_all_true():
    """Test that all domains are allowed when allow_all is True."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
        patch("asyncio.get_event_loop") as mock_loop,
        patch("app.api.proxy.httpx.AsyncClient") as mock_client,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        mock_response = MagicMock()
        mock_response.content = b"fake_image"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client

        url = "http://any-external-domain.com/image.jpg"
        result = await proxy_image(url=url)
        assert result is not None


# ==============================================================================
# URL VALIDATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_rejects_url_without_hostname():
    """Test that URLs without hostname are rejected."""
    from app.api.proxy import proxy_image

    invalid_urls = [
        "not-a-url",
        "http://",
        "https://",
        "://example.com",
    ]

    for url in invalid_urls:
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 400
        assert (
            "hostname" in exc_info.value.detail.lower()
            or "format" in exc_info.value.detail.lower()
        )


@pytest.mark.asyncio
async def test_rejects_invalid_url_format():
    """Test that invalid URL formats are rejected."""
    from app.api.proxy import proxy_image

    with pytest.raises(HTTPException) as exc_info:
        await proxy_image(url="http://[invalid")
    assert exc_info.value.status_code == 400


# ==============================================================================
# IMAGE FETCHING TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_successfully_proxies_valid_image(mock_httpx_get):
    """Test successful image proxying."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
        patch("asyncio.get_event_loop") as mock_loop,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        url = "https://example.com/image.jpg"
        result = await proxy_image(url=url)

        assert result is not None
        assert result.body == b"fake_image_data"
        assert result.media_type == "image/jpeg"
        # timeout is passed to AsyncClient constructor, not to get() method
        mock_httpx_get.get.assert_called_once_with(url)


@pytest.mark.asyncio
async def test_handles_http_error():
    """Test handling of HTTP errors during image fetch."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
        patch("asyncio.get_event_loop") as mock_loop,
        patch("app.api.proxy.httpx.AsyncClient") as mock_client,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(
            side_effect=httpx.HTTPError("Connection error")
        )
        mock_client.return_value = mock_async_client

        url = "https://example.com/image.jpg"
        with pytest.raises(HTTPException) as exc_info:
            await proxy_image(url=url)
        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_sets_cache_headers():
    """Test that cache headers are set correctly."""
    from app.api.proxy import proxy_image

    with (
        patch("app.api.proxy.settings.IMAGE_PROXY_ALLOW_ALL_DOMAINS", True),
        patch("asyncio.get_event_loop") as mock_loop,
        patch("app.api.proxy.httpx.AsyncClient") as mock_client,
    ):
        mock_event_loop = MagicMock()
        mock_executor = AsyncMock()
        mock_executor.return_value = ["93.184.216.34"]
        mock_event_loop.run_in_executor = mock_executor
        mock_loop.return_value = mock_event_loop

        mock_response = MagicMock()
        mock_response.content = b"fake_image"
        mock_response.headers = {"content-type": "image/png"}
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client

        url = "https://example.com/image.png"
        result = await proxy_image(url=url)

        assert "Cache-Control" in result.headers
        assert result.headers["Cache-Control"] == "public, max-age=3600"
        assert "Access-Control-Allow-Origin" in result.headers
        assert result.headers["Access-Control-Allow-Origin"] == "*"
