"""Unit tests for Places API rate limiting."""

from unittest.mock import MagicMock, patch

import app.core.places_rate_limit as plr
from app.core.places_rate_limit import (
    check_places_photo_rate_limit,
    check_places_search_rate_limit,
)

# Use small limits for fast tests; validates boundary logic (LIMIT allowed, LIMIT+1 rejected)
_SEARCH_LIMIT = 3
_PHOTO_LIMIT = 5


def _make_request(ip: str = "192.168.1.1") -> MagicMock:
    """Build a mock Request with X-Forwarded-For."""
    req = MagicMock()
    req.headers = {"X-Forwarded-For": ip}
    req.client = None
    return req


@patch("app.core.places_rate_limit.PLACES_SEARCH_RATE_LIMIT_PER_MINUTE", _SEARCH_LIMIT)
@patch("app.core.places_rate_limit.PLACES_PHOTO_RATE_LIMIT_PER_MINUTE", _PHOTO_LIMIT)
@patch("app.core.places_rate_limit.settings")
class TestPlacesSearchRateLimit:
    """Tests for check_places_search_rate_limit."""

    def test_allows_exactly_limit_requests(self, mock_settings: MagicMock) -> None:
        """Exactly LIMIT requests are allowed; (LIMIT+1)th is rejected."""
        mock_settings.RATE_LIMIT_ENABLED = True
        req = _make_request(ip="rate-test-search")

        for _ in range(_SEARCH_LIMIT):
            assert check_places_search_rate_limit(req) is True

        assert check_places_search_rate_limit(req) is False

    def test_rejects_when_disabled(self, mock_settings: MagicMock) -> None:
        """When RATE_LIMIT_ENABLED is False, all requests pass."""
        mock_settings.RATE_LIMIT_ENABLED = False
        req = _make_request(ip="rate-test-disabled")

        for _ in range(_SEARCH_LIMIT + 5):
            assert check_places_search_rate_limit(req) is True

    def test_per_ip_isolation(self, mock_settings: MagicMock) -> None:
        """Each IP has its own limit."""
        mock_settings.RATE_LIMIT_ENABLED = True
        req_a = _make_request(ip="ip-a")
        req_b = _make_request(ip="ip-b")

        for _ in range(_SEARCH_LIMIT):
            assert check_places_search_rate_limit(req_a) is True
        assert check_places_search_rate_limit(req_a) is False

        for _ in range(_SEARCH_LIMIT):
            assert check_places_search_rate_limit(req_b) is True
        assert check_places_search_rate_limit(req_b) is False


@patch("app.core.places_rate_limit.PLACES_SEARCH_RATE_LIMIT_PER_MINUTE", _SEARCH_LIMIT)
@patch("app.core.places_rate_limit.PLACES_PHOTO_RATE_LIMIT_PER_MINUTE", _PHOTO_LIMIT)
@patch("app.core.places_rate_limit.settings")
class TestPlacesPhotoRateLimit:
    """Tests for check_places_photo_rate_limit."""

    def test_allows_exactly_limit_requests(self, mock_settings: MagicMock) -> None:
        """Exactly LIMIT requests are allowed; (LIMIT+1)th is rejected."""
        mock_settings.RATE_LIMIT_ENABLED = True
        req = _make_request(ip="rate-test-photo")

        for _ in range(_PHOTO_LIMIT):
            assert check_places_photo_rate_limit(req) is True

        assert check_places_photo_rate_limit(req) is False

    def test_rejects_when_disabled(self, mock_settings: MagicMock) -> None:
        """When RATE_LIMIT_ENABLED is False, all requests pass."""
        mock_settings.RATE_LIMIT_ENABLED = False
        req = _make_request(ip="rate-test-photo-disabled")

        for _ in range(_PHOTO_LIMIT + 5):
            assert check_places_photo_rate_limit(req) is True


@patch("app.core.places_rate_limit.PLACES_SEARCH_RATE_LIMIT_PER_MINUTE", _SEARCH_LIMIT)
@patch("app.core.places_rate_limit.PLACES_PHOTO_RATE_LIMIT_PER_MINUTE", _PHOTO_LIMIT)
@patch("app.core.places_rate_limit._SWEEP_EVERY", 10)
@patch("app.core.places_rate_limit.settings")
class TestStaleIPSweep:
    """Tests for periodic stale IP eviction."""

    def test_evicts_stale_ips(self, mock_settings: MagicMock) -> None:
        """Stale IP entries (inactive 60+ s) are evicted when sweep runs."""
        mock_settings.RATE_LIMIT_ENABLED = True
        plr._search_timestamps.clear()
        plr._sweep_counter = 0

        with patch("app.core.places_rate_limit.time.monotonic") as mock_monotonic:
            # t=0: 5 IPs make 1 request each
            mock_monotonic.return_value = 0
            for i in range(5):
                req = _make_request(ip=f"stale-ip-{i}")
                assert check_places_search_rate_limit(req) is True
            assert len(plr._search_timestamps) == 5

            # t=70: 10 fresh IPs make requests; 10th call triggers sweep
            mock_monotonic.return_value = 70
            for i in range(10):
                req = _make_request(ip=f"fresh-ip-{i}")
                assert check_places_search_rate_limit(req) is True

        # Only the 10 fresh IPs remain; 5 stale were evicted
        assert len(plr._search_timestamps) == 10
        for i in range(10):
            assert f"fresh-ip-{i}" in plr._search_timestamps
        for i in range(5):
            assert f"stale-ip-{i}" not in plr._search_timestamps

    def test_sweep_does_not_remove_active_ips(self, mock_settings: MagicMock) -> None:
        """Active IPs (recent requests) are not evicted by sweep."""
        mock_settings.RATE_LIMIT_ENABLED = True
        plr._search_timestamps.clear()
        plr._sweep_counter = 0

        with patch("app.core.places_rate_limit.time.monotonic") as mock_monotonic:
            # t=0: 5 IPs make requests; sweep runs on each (SWEEP_EVERY=10, so after 10)
            mock_monotonic.return_value = 0
            for i in range(5):
                req = _make_request(ip=f"active-ip-{i}")
                assert check_places_search_rate_limit(req) is True
            # 5 more requests to trigger sweep on 10th call
            for i in range(5):
                req = _make_request(ip=f"active-ip-{i}")
                assert check_places_search_rate_limit(req) is True

        # All 5 active IPs remain (ts[-1]=0, cutoff=-60, so 0 >= -60)
        assert len(plr._search_timestamps) == 5
