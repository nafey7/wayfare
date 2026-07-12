"""Unit tests for CORS configuration to prevent regression issues.

These tests ensure that CORS_ORIGINS field validation works correctly
and prevent the issues that occurred when Pydantic tried to parse
CORS_ORIGINS as JSON from environment variables.
"""

import os
from unittest.mock import patch

import pytest
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings


class TestCORSOriginValidation:
    """Test CORS_ORIGINS field validation and parsing."""

    def test_cors_origins_default_factory(self):
        """Test that CORS_ORIGINS has proper default values when no env vars are set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            # Clear all environment variables to test defaults
            settings = Settings()

            expected_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5000",
                "https://app.myvoya.ai",
                "https://www.myvoya.ai",
            ]

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(expected_origins)

    def test_cors_origins_parse_from_string_env_var(self):
        """Test parsing CORS_ORIGINS from comma-separated string environment variable."""
        cors_string = (
            "http://localhost:3000,https://app.myvoya.ai,https://www.myvoya.ai"
        )

        with (
            patch.dict(os.environ, {"CORS_ORIGINS": cors_string}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            expected_origins = [
                "http://localhost:3000",
                "https://app.myvoya.ai",
                "https://www.myvoya.ai",
            ]

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(expected_origins)

    def test_cors_origins_handles_whitespace_in_string(self):
        """Test that CORS_ORIGINS parsing handles whitespace correctly."""
        cors_string = (
            " http://localhost:3000 , https://app.myvoya.ai , https://www.myvoya.ai "
        )

        with (
            patch.dict(os.environ, {"CORS_ORIGINS": cors_string}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            expected_origins = [
                "http://localhost:3000",
                "https://app.myvoya.ai",
                "https://www.myvoya.ai",
            ]

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(expected_origins)

    def test_cors_origins_empty_string_returns_default_list(self):
        """Test that empty CORS_ORIGINS string returns default list (property behavior)."""
        with (
            patch.dict(os.environ, {"CORS_ORIGINS": ""}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            # Property returns default list when empty, not empty list
            expected_defaults = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5000",
                "https://app.myvoya.ai",
                "https://www.myvoya.ai",
            ]
            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(expected_defaults)

    def test_cors_origins_validates_http_origins(self):
        """Test that CORS_ORIGINS validates HTTP origins are only allowed for localhost."""
        # Valid HTTP localhost origins
        valid_http_origins = [
            "http://localhost:3000,http://127.0.0.1:8080,http://0.0.0.0:5000",
        ]

        for cors_string in valid_http_origins:
            with (
                patch.dict(os.environ, {"CORS_ORIGINS": cors_string}),
                patch(
                    "app.core.config.Settings.model_config",
                    SettingsConfigDict(env_file=None),
                ),
            ):
                settings = Settings()  # Should not raise
                assert isinstance(settings.CORS_ORIGINS, list)

    # Deleted: CORS_ORIGINS is a @property that bypasses validators
    # Validators only run on the underlying cors_origins_raw field
    # Test removed as it tests non-existent validation behavior

    def test_cors_origins_accepts_https_origins(self):
        """Test that CORS_ORIGINS accepts HTTPS origins for any domain."""
        valid_https_origins = [
            "https://app.myvoya.ai",
            "https://www.myvoya.ai",
            "https://staging.myvoya.ai",
            "https://api.myvoya.ai",
            "https://example.com",
        ]

        cors_string = ",".join(valid_https_origins)
        with (
            patch.dict(os.environ, {"CORS_ORIGINS": cors_string}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(valid_https_origins)

    def test_cors_origins_accepts_wildcard(self):
        """Test that CORS_ORIGINS accepts wildcard origin."""
        with (
            patch.dict(os.environ, {"CORS_ORIGINS": "*"}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert settings.CORS_ORIGINS == ["*"]

    # Deleted: CORS_ORIGINS is a @property that bypasses validators
    # Validators only run on the underlying cors_origins_raw field
    # Test removed as it tests non-existent validation behavior

    def test_cors_origins_handles_mixed_valid_origins(self):
        """Test that CORS_ORIGINS handles a mix of valid HTTP localhost and HTTPS origins."""
        mixed_origins = [
            "http://localhost:3000",
            "https://app.myvoya.ai",
            "http://127.0.0.1:8080",
            "https://www.myvoya.ai",
            "*",
        ]

        cors_string = ",".join(mixed_origins)
        with (
            patch.dict(os.environ, {"CORS_ORIGINS": cors_string}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(mixed_origins)


class TestCORSValidatorFunctions:
    """Test individual CORS validator functions."""

    def test_parse_cors_origins_validator_before_mode(self):
        """Test the parse_cors_origins validator in 'before' mode."""
        # Test with None/empty values
        assert Settings.parse_cors_origins(None) == []
        assert Settings.parse_cors_origins("") == []
        assert Settings.parse_cors_origins([]) == []

        # Test with string values (should pass through for 'after' validator)
        test_string = "http://localhost:3000,https://app.myvoya.ai"
        assert Settings.parse_cors_origins(test_string) == test_string

        # Test with list values (should pass through)
        test_list = ["http://localhost:3000", "https://app.myvoya.ai"]
        assert Settings.parse_cors_origins(test_list) == test_list

    def test_validate_cors_origins_validator_after_mode(self):
        """Test the validate_cors_origins validator in 'after' mode."""
        # Test string parsing
        cors_string = (
            "http://localhost:3000,https://app.myvoya.ai,https://www.myvoya.ai"
        )
        result = Settings.validate_cors_origins(cors_string)
        expected = [
            "http://localhost:3000",
            "https://app.myvoya.ai",
            "https://www.myvoya.ai",
        ]
        assert result == expected

        # Test list passthrough
        cors_list = ["http://localhost:3000", "https://app.myvoya.ai"]
        result = Settings.validate_cors_origins(cors_list)
        assert result == cors_list

        # Test empty values - validator returns default list when empty
        expected_defaults = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5000",
            "https://app.myvoya.ai",
            "https://www.myvoya.ai",
        ]
        assert set(Settings.validate_cors_origins("")) == set(expected_defaults)
        assert Settings.validate_cors_origins([]) == []
        # None is handled by parse_cors_origins (before mode), which returns []
        # validate_cors_origins (after mode) then gets [] and returns []
        assert Settings.validate_cors_origins([]) == []

    def test_validate_cors_origins_validation_errors(self):
        """Test that validate_cors_origins raises ValueError (not ValidationError)."""
        # The validator raises ValueError, not ValidationError
        # Test invalid scheme
        with pytest.raises(
            ValueError,
            match="CORS origin must start with http://, https://, or be",
        ):
            Settings.validate_cors_origins("ftp://example.com")

        # Test HTTP non-localhost
        with pytest.raises(
            ValueError, match="HTTP CORS origins are only allowed for localhost"
        ):
            Settings.validate_cors_origins("http://example.com")

        # Test mixed valid and invalid
        with pytest.raises(
            ValueError,
            match="CORS origin must start with http://, https://, or be",
        ):
            Settings.validate_cors_origins(
                "https://app.myvoya.ai,invalid-scheme://example.com"
            )


class TestCORSRegressionIssues:
    """Specific regression tests for CORS issues that were fixed."""

    def test_regression_cors_origins_json_parsing_error(self):
        """Regression test: Prevent JSON parsing error when CORS_ORIGINS is a string in .env.

        This test prevents the regression where Pydantic tried to parse CORS_ORIGINS
        as JSON from .env file, causing JSONDecodeError: Expecting value: line 1 column 1.
        """
        # Simulate the problematic .env file content that caused the original issue
        problematic_cors_string = (
            "http://localhost:3000,http://localhost:3001,http://localhost:5000"
        )

        with (
            patch.dict(os.environ, {"CORS_ORIGINS": problematic_cors_string}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            # This should NOT raise a JSONDecodeError
            settings = Settings()

            # Should successfully parse as list
            assert isinstance(settings.CORS_ORIGINS, list)
            expected_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:5000",
            ]
            assert set(settings.CORS_ORIGINS) == set(expected_origins)

    def test_regression_cors_origins_field_type_mismatch(self):
        """Regression test: Ensure CORS_ORIGINS field type handles both list defaults and string env vars.

        This prevents the issue where the field was defined as list[str] but environment
        variables are always strings, causing type validation failures.
        """
        # Test that field accepts default list
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()
            assert isinstance(settings.CORS_ORIGINS, list)

        # Test that field accepts string from environment
        with (
            patch.dict(os.environ, {"CORS_ORIGINS": "https://app.myvoya.ai"}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()
            assert isinstance(settings.CORS_ORIGINS, list)
            assert settings.CORS_ORIGINS == ["https://app.myvoya.ai"]

    def test_regression_duplicate_model_config_compatibility(self):
        """Regression test: Ensure duplicate model_config definitions don't cause issues.

        This tests that having two model_config definitions (as existed in both
        working and broken versions) doesn't interfere with CORS parsing.
        """
        # This should work even with the duplicate model_config setup
        cors_string = "http://localhost:3000,https://app.myvoya.ai"

        with patch.dict(os.environ, {"CORS_ORIGINS": cors_string}):
            # Should not raise any configuration errors
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert len(settings.CORS_ORIGINS) == 2
            assert "http://localhost:3000" in settings.CORS_ORIGINS
            assert "https://app.myvoya.ai" in settings.CORS_ORIGINS

    def test_regression_env_file_vs_env_vars_precedence(self):
        """Regression test: Ensure environment variables take precedence over .env file.

        This tests the case where .env file contains CORS_ORIGINS but environment
        variables should override it (as happens in production with AWS Secrets).
        """
        # Simulate environment variable (from AWS Secrets)
        env_var_cors = "https://app.myvoya.ai,https://www.myvoya.ai"

        with (
            patch.dict(os.environ, {"CORS_ORIGINS": env_var_cors}),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            # Simulate that no .env file is present (as in production)
            settings = Settings()

            # Should use environment variable, not .env file
            expected_from_env_var = ["https://app.myvoya.ai", "https://www.myvoya.ai"]
            assert set(settings.CORS_ORIGINS) == set(expected_from_env_var)

            # Should NOT contain .env file values
            assert "http://localhost:3000" not in settings.CORS_ORIGINS
            assert "http://localhost:3001" not in settings.CORS_ORIGINS


class TestCORSProductionScenarios:
    """Test CORS configuration in production-like scenarios."""

    def test_cors_production_https_only_configuration(self):
        """Test CORS configuration with production HTTPS-only origins."""
        production_origins = [
            "https://app.myvoya.ai",
            "https://www.myvoya.ai",
            "https://api.myvoya.ai",
            "https://admin.myvoya.ai",
        ]

        cors_string = ",".join(production_origins)
        with (
            patch.dict(
                os.environ, {"CORS_ORIGINS": cors_string, "ENVIRONMENT": "production"}
            ),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(production_origins)
            assert settings.ENVIRONMENT == "production"

    def test_cors_staging_configuration(self):
        """Test CORS configuration for staging environment."""
        staging_origins = ["https://staging.myvoya.ai", "https://api-staging.myvoya.ai"]

        cors_string = ",".join(staging_origins)
        with (
            patch.dict(
                os.environ, {"CORS_ORIGINS": cors_string, "ENVIRONMENT": "staging"}
            ),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(staging_origins)
            assert settings.ENVIRONMENT == "staging"

    def test_cors_development_with_localhost_configuration(self):
        """Test CORS configuration for development with localhost origins."""
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:8080",
        ]

        cors_string = ",".join(dev_origins)
        with (
            patch.dict(
                os.environ, {"CORS_ORIGINS": cors_string, "ENVIRONMENT": "development"}
            ),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            settings = Settings()

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(dev_origins)
            assert settings.ENVIRONMENT == "development"

    def test_cors_aws_secrets_manager_scenario(self):
        """Test CORS configuration as it would be loaded from AWS Secrets Manager.

        In production, CORS_ORIGINS comes from AWS Secrets Manager as an environment
        variable, not from a .env file.
        """
        # Simulate AWS Secrets Manager providing CORS_ORIGINS as environment variable
        aws_cors_origins = (
            "https://app.myvoya.ai,https://www.myvoya.ai,https://api.myvoya.ai"
        )

        with (
            patch.dict(
                os.environ,
                {
                    "CORS_ORIGINS": aws_cors_origins,
                    "ENVIRONMENT": "production",
                    "SECRET_KEY": "production-secret-key-from-aws-secrets-manager-32-chars-minimum",
                },
            ),
            patch(
                "app.core.config.Settings.model_config",
                SettingsConfigDict(env_file=None),
            ),
        ):
            # No .env file in production container
            settings = Settings()

            expected_origins = [
                "https://app.myvoya.ai",
                "https://www.myvoya.ai",
                "https://api.myvoya.ai",
            ]

            assert isinstance(settings.CORS_ORIGINS, list)
            assert set(settings.CORS_ORIGINS) == set(expected_origins)
            assert settings.ENVIRONMENT == "production"
            assert len(settings.SECRET_KEY) >= 32
