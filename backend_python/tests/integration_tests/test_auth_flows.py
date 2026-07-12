"""Integration tests for authentication API endpoints.

These tests verify the complete authentication flows including:
- Registration flow
- Login flow
- Password reset flow
- Session management
"""

import httpx

from tests.integration_tests.conftest import APITestHelper


class TestRegistrationFlow:
    """Test user registration flow."""

    async def test_check_email_new_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test email check for new user."""
        response = await http_client.post(
            "/api/auth/check-email", json={"email": "api-test@example.com"}
        )

        data = api_helper.assert_success_response(response)
        assert data["exists"] is False
        assert data["verified"] is None
        assert "new user" in data["message"].lower()

    async def test_register_new_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test registering a new user."""
        response = await http_client.post(
            "/api/auth/register",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test",
            },
        )

        data = api_helper.assert_success_response(response)
        assert "registration initiated" in data["message"].lower()

    async def test_check_email_unverified_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test email check for unverified user."""
        # First register user
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test",
            },
        )

        # Then check email status
        response = await http_client.post(
            "/api/auth/check-email", json={"email": "api-test@example.com"}
        )

        data = api_helper.assert_success_response(response)
        assert data["exists"] is True
        assert data["verified"] is False
        assert "complete your registration" in data["message"].lower()

    async def test_register_existing_user_error(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test registering an existing user returns appropriate error."""
        # Register user first
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test",
            },
        )

        # Try to register again
        response = await http_client.post(
            "/api/auth/register",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test",
            },
        )

        # Should still succeed (idempotent) but return same message
        data = api_helper.assert_success_response(response)
        assert "registration initiated" in data["message"].lower()


class TestPasswordResetFlow:
    """Test password reset flow."""

    async def test_forgot_password_existing_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test forgot password for existing user."""
        # First register a user
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "reset-test@example.com",
                "first_name": "Reset",
                "last_name": "Test",
            },
        )

        # Request password reset
        response = await http_client.post(
            "/api/auth/forgot-password", json={"email": "reset-test@example.com"}
        )

        data = api_helper.assert_success_response(response)
        assert "password reset link has been sent" in data["message"].lower()

    async def test_forgot_password_nonexistent_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test forgot password for non-existent user (should not reveal user existence)."""
        response = await http_client.post(
            "/api/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )

        data = api_helper.assert_success_response(response)
        # Should return same message to avoid email enumeration
        assert "password reset link has been sent" in data["message"].lower()

    async def test_validate_registration_token_valid(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test validating a valid registration token (from registration email).

        Registration tokens are stored in password_reset_token. This test uses
        the registration flow (which sends email with token) - the token is stored
        before the email is sent. We use forgot-password to ensure we have a
        token to validate (both flows use the same storage).
        """
        # Register user then request password reset - both store token in same field
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "reg-token-test@example.com",
                "first_name": "Reg",
                "last_name": "Test",
            },
        )
        await http_client.post(
            "/api/auth/forgot-password",
            json={"email": "reg-token-test@example.com"},
        )

        # Get token from database (stored by forgot-password; registration uses same field)
        reg_token = await api_helper.get_user_reset_token("reg-token-test@example.com")
        assert reg_token is not None

        # Validate registration token
        response = await http_client.post(
            "/api/auth/validate-registration-token", json={"token": reg_token}
        )

        data = api_helper.assert_success_response(response)
        assert "token is valid" in data["message"].lower()

    async def test_validate_registration_token_invalid(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
    ):
        """Test validating an invalid registration token."""
        response = await http_client.post(
            "/api/auth/validate-registration-token",
            json={"token": "invalid-reg-token-12345"},
        )

        api_helper.assert_error_response(response, 400, "invalid or expired")

    async def test_validate_reset_token_valid(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test validating a valid reset token."""
        # First register user and request reset
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "reset-test@example.com",
                "first_name": "Reset",
                "last_name": "Test",
            },
        )

        await http_client.post(
            "/api/auth/forgot-password", json={"email": "reset-test@example.com"}
        )

        # Get reset token from database
        reset_token = await api_helper.get_user_reset_token("reset-test@example.com")
        assert reset_token is not None

        # Validate token
        response = await http_client.post(
            "/api/auth/validate-reset-token", json={"token": reset_token}
        )

        data = api_helper.assert_success_response(response)
        assert "token is valid" in data["message"].lower()

    async def test_validate_reset_token_invalid(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test validating an invalid reset token."""
        response = await http_client.post(
            "/api/auth/validate-reset-token", json={"token": "invalid-token-12345"}
        )

        api_helper.assert_error_response(response, 400, "invalid or expired")

    async def test_reset_password_success(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test successful password reset."""
        # Setup: register user and request reset
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "reset-test@example.com",
                "first_name": "Reset",
                "last_name": "Test",
            },
        )

        await http_client.post(
            "/api/auth/forgot-password", json={"email": "reset-test@example.com"}
        )

        # Get reset token
        reset_token = await api_helper.get_user_reset_token("reset-test@example.com")
        assert reset_token is not None

        # Reset password
        response = await http_client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )

        data = api_helper.assert_success_response(response)
        assert "password reset successfully" in data["message"].lower()
        assert "user" in data
        assert data["user"]["email"] == "reset-test@example.com"

    async def test_reset_password_mismatched_passwords(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test password reset with mismatched passwords."""
        # Setup: register user and request reset
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "reset-test@example.com",
                "first_name": "Reset",
                "last_name": "Test",
            },
        )

        await http_client.post(
            "/api/auth/forgot-password", json={"email": "reset-test@example.com"}
        )

        reset_token = await api_helper.get_user_reset_token("reset-test@example.com")

        # Try to reset with mismatched passwords
        response = await http_client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newpassword123",
                "confirm_password": "differentpassword123",
            },
        )

        api_helper.assert_error_response(response, 422, "passwords do not match")

    async def test_reset_password_invalid_token(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test password reset with invalid token."""
        response = await http_client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )

        api_helper.assert_error_response(response, 400, "invalid")


class TestLoginFlow:
    """Test login flows."""

    async def test_login_unverified_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test login attempt with unverified user."""
        # Register user (but don't complete registration)
        await http_client.post(
            "/api/auth/register",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test",
            },
        )

        # Try to login
        response = await http_client.post(
            "/api/auth/login",
            json={"email": "api-test@example.com", "password": "anypassword"},
        )

        api_helper.assert_error_response(
            response, 401, "complete your registration first"
        )

    async def test_login_nonexistent_user(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test login with non-existent user."""
        response = await http_client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "anypassword"},
        )

        api_helper.assert_error_response(response, 401, "invalid email or password")


class TestSessionManagement:
    """Test session management endpoints."""

    async def test_logout_without_token(
        self, http_client: httpx.AsyncClient, api_helper: APITestHelper
    ):
        """Test logout without authentication token."""
        response = await http_client.post("/api/auth/logout")

        # Should require authentication
        api_helper.assert_error_response(response, 403, "not authenticated")

    async def test_refresh_token_invalid(
        self, http_client: httpx.AsyncClient, api_helper: APITestHelper
    ):
        """Test refresh token with invalid token."""
        response = await http_client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid-refresh-token"}
        )

        api_helper.assert_error_response(response, 401, "invalid or expired")


class TestRegistrationCompletionFlow:
    """Test registration link → validate → complete registration flow."""

    async def test_complete_registration_flow(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test complete registration flow: register → validate token → set password.

        Uses forgot-password to obtain a token (same storage as registration email).
        Simulates user clicking link and completing registration.
        """
        email = "complete-reg-flow@example.com"

        # Step 1: Register user (sends registration email)
        response = await http_client.post(
            "/api/auth/register",
            json={"email": email, "first_name": "Complete", "last_name": "Flow"},
        )
        api_helper.assert_success_response(response)

        # Step 2: Request password reset to get token (registration uses same field;
        # in real flow user gets token from registration email)
        await http_client.post("/api/auth/forgot-password", json={"email": email})
        reg_token = await api_helper.get_user_reset_token(email)
        assert reg_token is not None

        # Step 3: Validate registration token (CompleteRegistrationPage does this on mount)
        response = await http_client.post(
            "/api/auth/validate-registration-token", json={"token": reg_token}
        )
        api_helper.assert_success_response(response)

        # Step 4: Complete registration with password
        response = await http_client.post(
            "/api/auth/complete-registration",
            json={
                "token": reg_token,
                "password": "SecurePass123",  # pragma: allowlist secret
                "confirm_password": "SecurePass123",  # pragma: allowlist secret
            },
        )
        data = api_helper.assert_success_response(response)
        assert "access_token" in data
        assert data.get("user", {}).get("email") == email

        # Step 5: Verify can login with new password
        response = await http_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePass123",  # pragma: allowlist secret
            },
        )
        api_helper.assert_success_response(response)


class TestEndToEndAuthFlow:
    """Test complete end-to-end authentication scenarios."""

    async def test_complete_password_reset_flow(
        self,
        http_client: httpx.AsyncClient,
        api_helper: APITestHelper,
        clean_test_users,
    ):
        """Test the complete password reset flow from start to finish."""
        email = "e2e-test@example.com"

        # Step 1: Register user
        response = await http_client.post(
            "/api/auth/register",
            json={"email": email, "first_name": "E2E", "last_name": "Test"},
        )
        api_helper.assert_success_response(response)

        # Step 2: Request password reset
        response = await http_client.post(
            "/api/auth/forgot-password", json={"email": email}
        )
        api_helper.assert_success_response(response)

        # Step 3: Get reset token (simulating email click)
        reset_token = await api_helper.get_user_reset_token(email)
        assert reset_token is not None

        # Step 4: Validate reset token
        response = await http_client.post(
            "/api/auth/validate-reset-token", json={"token": reset_token}
        )
        api_helper.assert_success_response(response)

        # Step 5: Reset password
        response = await http_client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "securepassword123",
                "confirm_password": "securepassword123",
            },
        )
        data = api_helper.assert_success_response(response)
        assert data["user"]["email"] == email

        # Step 6: Verify token is no longer valid
        response = await http_client.post(
            "/api/auth/validate-reset-token", json={"token": reset_token}
        )
        api_helper.assert_error_response(response, 400, "invalid or expired")


class TestConfigEndpoints:
    """Test configuration endpoints."""

    async def test_google_oauth_config(
        self, http_client: httpx.AsyncClient, api_helper: APITestHelper
    ):
        """Test Google OAuth configuration endpoint."""
        response = await http_client.get("/api/auth/config/google")

        data = api_helper.assert_success_response(response)
        assert "client_id" in data
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)
