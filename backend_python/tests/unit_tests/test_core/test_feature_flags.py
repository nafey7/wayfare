"""Tests for app.core.feature_flags — SSM-backed feature flag loader."""

import importlib
from unittest.mock import MagicMock, patch

import pytest

import app.core.feature_flags as ff_module


def _reset_module() -> None:
    """Reset module-level globals between tests."""
    ff_module._flags.clear()
    ff_module._loaded = False
    ff_module._FLAG_PREFIX = None


@pytest.fixture(autouse=True)
def reset_flags() -> None:
    """Ensure each test starts with a clean flag state."""
    _reset_module()
    yield
    _reset_module()


def _make_ssm_client(parameters: list[dict]) -> MagicMock:
    """Return a mock boto3 SSM client whose paginator yields *parameters*."""
    page = {"Parameters": parameters}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    return client


# ---------------------------------------------------------------------------
# SSM load success
# ---------------------------------------------------------------------------


def test_load_flags_true_values() -> None:
    """All truthy SSM string representations should map to True."""
    parameters = [
        {"Name": "/voya/test/feature-flags/public-chat", "Value": "true"},
        {"Name": "/voya/test/feature-flags/other-flag", "Value": "1"},
        {"Name": "/voya/test/feature-flags/third-flag", "Value": "yes"},
    ]
    ssm_client = _make_ssm_client(parameters)

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module._load_flags()

    assert ff_module._flags["public-chat"] is True
    assert ff_module._flags["other-flag"] is True
    assert ff_module._flags["third-flag"] is True


def test_load_flags_false_values() -> None:
    """Non-truthy SSM values should map to False."""
    parameters = [
        {"Name": "/voya/test/feature-flags/public-chat", "Value": "false"},
        {"Name": "/voya/test/feature-flags/other-flag", "Value": "0"},
        {"Name": "/voya/test/feature-flags/third-flag", "Value": "no"},
    ]
    ssm_client = _make_ssm_client(parameters)

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module._load_flags()

    assert ff_module._flags["public-chat"] is False
    assert ff_module._flags["other-flag"] is False
    assert ff_module._flags["third-flag"] is False


def test_load_flags_case_insensitive() -> None:
    """SSM values should be compared case-insensitively."""
    parameters = [
        {"Name": "/voya/test/feature-flags/flag-a", "Value": "True"},
        {"Name": "/voya/test/feature-flags/flag-b", "Value": "YES"},
        {"Name": "/voya/test/feature-flags/flag-c", "Value": "False"},
    ]
    ssm_client = _make_ssm_client(parameters)

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module._load_flags()

    assert ff_module._flags["flag-a"] is True
    assert ff_module._flags["flag-b"] is True
    assert ff_module._flags["flag-c"] is False


# ---------------------------------------------------------------------------
# SSM unavailable — fallback to settings
# ---------------------------------------------------------------------------


def test_load_flags_ssm_unavailable_does_not_raise() -> None:
    """When boto3 raises, _load_flags() should not propagate the exception."""
    with patch("boto3.client", side_effect=Exception("no credentials")):
        ff_module._load_flags()  # Must not raise

    assert ff_module._flags == {}  # No flags loaded


def test_get_flag_falls_back_to_default_when_ssm_unavailable() -> None:
    """When SSM is unavailable, get_flag() returns the caller-supplied default."""
    with patch("boto3.client", side_effect=Exception("no credentials")):
        result = ff_module.get_flag("public-chat", default=True)

    assert result is True


def test_public_chat_enabled_falls_back_to_settings() -> None:
    """public_chat_enabled() falls back to settings when SSM has no entry."""
    with (
        patch("boto3.client", side_effect=Exception("no credentials")),
        patch(
            "app.core.feature_flags.get_flag",
            wraps=lambda name, default=False: default,
        ),
        patch("app.core.config.settings") as mock_settings,
    ):
        mock_settings.VOYA_FEATURE_FLAG_PUBLIC_CHAT = True
        # Re-import to pick up the mock
        importlib.reload(ff_module)
        _reset_module()

        result = ff_module.public_chat_enabled()

    assert result is True


# ---------------------------------------------------------------------------
# Idempotency — _load_flags() only runs once
# ---------------------------------------------------------------------------


def test_load_flags_only_called_once() -> None:
    """_load_flags() should be idempotent: SSM is only queried once."""
    ssm_client = _make_ssm_client(
        [{"Name": "/voya/test/feature-flags/public-chat", "Value": "true"}]
    )

    with (
        patch("boto3.client", return_value=ssm_client) as mock_boto,
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module._load_flags()
        ff_module._load_flags()  # Second call should be a no-op

    # boto3.client() should only have been called once
    assert mock_boto.call_count == 1


def test_get_flag_triggers_load_once() -> None:
    """get_flag() triggers _load_flags() on first call only."""
    ssm_client = _make_ssm_client(
        [{"Name": "/voya/test/feature-flags/public-chat", "Value": "false"}]
    )

    with (
        patch("boto3.client", return_value=ssm_client) as mock_boto,
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module.get_flag("public-chat", default=True)
        ff_module.get_flag("public-chat", default=True)

    assert mock_boto.call_count == 1


# ---------------------------------------------------------------------------
# get_flag() default handling
# ---------------------------------------------------------------------------


def test_get_flag_returns_ssm_value_when_present() -> None:
    """get_flag() returns the SSM value when the flag is loaded."""
    ssm_client = _make_ssm_client(
        [{"Name": "/voya/test/feature-flags/my-flag", "Value": "true"}]
    )

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        result = ff_module.get_flag("my-flag", default=False)

    assert result is True


def test_get_flag_returns_default_for_unknown_flag() -> None:
    """get_flag() returns the default when the flag name is not in SSM."""
    ssm_client = _make_ssm_client([])  # No parameters returned

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        result = ff_module.get_flag("nonexistent-flag", default=True)

    assert result is True


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_load_flags_handles_multiple_pages() -> None:
    """_load_flags() should load flags from all paginator pages."""
    page1 = {
        "Parameters": [{"Name": "/voya/test/feature-flags/flag-a", "Value": "true"}]
    }
    page2 = {
        "Parameters": [{"Name": "/voya/test/feature-flags/flag-b", "Value": "false"}]
    }

    paginator = MagicMock()
    paginator.paginate.return_value = [page1, page2]
    ssm_client = MagicMock()
    ssm_client.get_paginator.return_value = paginator

    with (
        patch("boto3.client", return_value=ssm_client),
        patch.object(ff_module, "_ssm_prefix", return_value="/voya/test/feature-flags"),
    ):
        ff_module._load_flags()

    assert ff_module._flags["flag-a"] is True
    assert ff_module._flags["flag-b"] is False
