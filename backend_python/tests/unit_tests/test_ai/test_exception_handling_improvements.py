"""
Unit tests for exception handling improvements.

Tests the enhanced exception handling added throughout the system including:
- InvalidTokenError handling in auth endpoints
- Global exception handlers
- UnboundLocalError fixes in flight handlers
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.auth import (
    complete_registration,
    reset_password,
    validate_registration_token,
    validate_reset_token,
)
from app.domains.auth.exceptions import InvalidTokenError
from app.domains.auth.schemas import (
    CompleteRegistrationRequest,
    ResetPasswordRequest,
    ValidateRegistrationTokenRequest,
    ValidateResetTokenRequest,
)


class TestExceptionHandlingImprovements:
    """Test exception handling improvements"""

    def test_complete_registration_invalid_token_error(self):
        """Test that complete_registration handles InvalidTokenError properly"""

        request_data = CompleteRegistrationRequest(
            token="invalid_token",  # noqa: S106 - Test token, not real password
            password="newpassword123",  # noqa: S106 - Test password, not hardcoded secret
            confirm_password="newpassword123",  # noqa: S106 - Required field
        )

        mock_request = Mock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        with patch("app.api.auth.AuthService") as mock_auth_service:
            mock_auth_instance = Mock()
            mock_auth_service.return_value = mock_auth_instance

            # Simulate InvalidTokenError being raised
            mock_auth_instance.complete_registration.side_effect = InvalidTokenError(
                "Invalid verification token: Token is invalid or expired"
            )

            # Should handle InvalidTokenError and convert to HTTPException
            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(complete_registration(request_data, mock_request))

            assert exc_info.value.status_code == 400
            assert "Invalid or expired registration token" in exc_info.value.detail

    def test_validate_reset_token_invalid_token_error(self):
        """Test that validate_reset_token handles InvalidTokenError properly"""

        request_data = ValidateResetTokenRequest(token="invalid_token")  # noqa: S106 - Test token, not hardcoded secret

        with patch("app.api.auth.AuthService") as mock_auth_service:
            mock_auth_instance = Mock()
            mock_auth_service.return_value = mock_auth_instance

            # Simulate InvalidTokenError being raised
            mock_auth_instance.validate_reset_token.side_effect = InvalidTokenError(
                "Invalid reset token"
            )

            # Should handle InvalidTokenError and convert to HTTPException
            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(validate_reset_token(request_data))

            assert exc_info.value.status_code == 400
            assert "Invalid or expired reset token" in exc_info.value.detail

    def test_validate_registration_token_invalid_token_error(self):
        """Test that validate_registration_token handles InvalidTokenError properly"""

        request_data = ValidateRegistrationTokenRequest(token="invalid_token")  # noqa: S106 - Test token

        with patch("app.api.auth.AuthService") as mock_auth_service:
            mock_auth_instance = Mock()
            mock_auth_service.return_value = mock_auth_instance

            mock_auth_instance.validate_registration_token.side_effect = (
                InvalidTokenError("verification", "Token is invalid or expired")
            )

            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(validate_registration_token(request_data))

            assert exc_info.value.status_code == 400
            assert "Invalid or expired registration token" in exc_info.value.detail

    def test_reset_password_invalid_token_error(self):
        """Test that reset_password handles InvalidTokenError properly"""

        request_data = ResetPasswordRequest(
            token="invalid_token",  # noqa: S106 - Test token, not hardcoded secret
            new_password="newpassword123",  # noqa: S106 - Test password, not hardcoded secret
            confirm_password="newpassword123",  # noqa: S106 - Required field
        )

        with patch("app.api.auth.AuthService") as mock_auth_service:
            mock_auth_instance = Mock()
            mock_auth_service.return_value = mock_auth_instance

            # Simulate InvalidTokenError being raised
            mock_auth_instance.reset_password.side_effect = InvalidTokenError(
                token_type="reset", reason="token is invalid or expired"
            )

            # Should handle InvalidTokenError and convert to HTTPException
            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(reset_password(request_data))

            assert exc_info.value.status_code == 400
            assert "Invalid reset token" in str(exc_info.value.detail)

    async def test_global_invalid_token_exception_handler(self):
        """Test the global InvalidTokenError exception handler"""

        from app.main import invalid_token_exception_handler

        # Create mock request and exception
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/auth/complete-registration"

        mock_exception = InvalidTokenError("Token expired")

        # Call the global exception handler
        response = await invalid_token_exception_handler(mock_request, mock_exception)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        assert response.body == b'{"detail":"Invalid or expired token"}'
