"""Authentication service - simplified and clean."""

import logging
import secrets
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domains.user.schemas import UserPrivate, UserPublic
    from app.domains.user.service import UserService

import bcrypt
import jwt
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.domains.common import AuthProvider, EmailStr, now_utc, timedelta

from . import repository as auth_repo
from .events import AuthEventHandler
from .exceptions import (
    GoogleAuthError,
    InvalidTokenError,
    RegistrationError,
)
from .schemas import SessionResponse

logger = logging.getLogger(__name__)


def _get_user_service() -> "UserService":
    """Lazy import UserService to avoid circular imports."""
    from app.domains.user import UserService

    return UserService


class AuthService:
    """Clean, simple authentication service - pure static utility class."""

    # ============================================================
    # 1. REGISTRATION & ONBOARDING
    # ============================================================

    @staticmethod
    async def register_user_passwordless(
        email: EmailStr, first_name: str, last_name: str
    ) -> "UserPrivate":
        """Register user without password - sends setup email."""
        logger.info(
            f"🔐 [Registration] Starting passwordless registration for: {email}"
        )
        # Check if user exists
        existing = await _get_user_service().get_user_private_by_email(email)
        if existing and existing.email_verified:
            logger.warning(f"🔐 [Registration] Email already verified: {email}")
            raise RegistrationError("Email already registered and verified")

        if existing and not existing.email_verified:
            # Resend registration email for unverified user
            logger.info(
                f"🔐 [Registration] Resending registration email for existing unverified user: {email}"
            )
            email_sent = await AuthService.send_registration_email(str(existing.id))
            logger.info(
                f"🔐 [Registration] Resend email result: {email_sent} for user: {email}"
            )
            return existing

        # Create new user without password
        logger.info(f"🔐 [Registration] Creating new user: {email}")
        user_dict = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        user = await _get_user_service().create_user(
            user_data=user_dict,
            auth_provider=AuthProvider.LOCAL,
            skip_email_verification=False,
            return_private=True,
            trigger_events=False,  # Don't trigger events for passwordless registration
        )

        logger.info(
            f"🔐 [Registration] User created successfully, ID: {user.id}, email: {email}"
        )

        # Send registration email
        logger.info(f"🔐 [Registration] Sending registration email to: {email}")
        email_sent = await AuthService.send_registration_email(str(user.id))
        logger.info(
            f"🔐 [Registration] Registration email sent result: {email_sent} for user: {email}"
        )

        # Handle registration started event
        await AuthEventHandler.handle_registration_started(
            user_id=str(user.id), email=email
        )

        logger.info(f"🔐 [Registration] Registration process completed for: {email}")
        return user

    @staticmethod
    async def send_registration_email(user_id: str) -> bool:
        """Send registration completion email."""
        logger.info(f"📧 [Email] Preparing registration email for user_id: {user_id}")

        user = await _get_user_service().get_user_private(user_id)
        if not user:
            logger.error(f"📧 [Email] User not found for ID: {user_id}")
            return False

        logger.info(f"📧 [Email] User found: {user.email}, generating setup token")

        # Generate token
        token = secrets.token_urlsafe(32)
        expiry = now_utc() + timedelta(hours=72)
        logger.info(f"📧 [Email] Setup token generated, expires: {expiry}")

        # Store token
        await auth_repo.set_password_reset_token(
            user_id=str(user.id), token=token, expiry=expiry
        )
        logger.info(f"📧 [Email] Setup token stored in database for user: {user.email}")

        # Send email via event
        logger.info(f"📧 [Email] Triggering registration setup email for: {user.email}")
        await AuthEventHandler.handle_registration_setup_requested(
            user_id=str(user.id),
            email=user.email,
            setup_token=token,
            user_name=user.first_name,
        )

        logger.info(
            f"📧 [Email] Registration email process completed for: {user.email}"
        )
        return True

    @staticmethod
    async def complete_registration(token: str, password: str) -> "UserPrivate":
        """Complete registration by setting password."""
        # Find user by token
        user_data = await auth_repo.get_user_by_reset_token(token)
        if not user_data:
            raise InvalidTokenError("verification", "Token is invalid or expired")

        # Set password and verify email
        password_hash = AuthService.hash_password(password)
        await auth_repo.complete_user_registration(
            user_id=str(user_data["_id"]), password_hash=password_hash
        )

        # Handle registration completed event
        await AuthEventHandler.handle_registration_completed(
            user_id=str(user_data["_id"]), provider=AuthProvider.LOCAL
        )

        # Return updated user
        return await _get_user_service().get_user_private(str(user_data["_id"]))

    # ============================================================
    # 2. LOGIN & AUTHENTICATION
    # ============================================================

    @staticmethod
    async def authenticate_user(
        email: EmailStr, password: str, ip_address: str | None = None
    ) -> "UserPrivate | None":
        """Authenticate user with email and password."""
        user = await _get_user_service().get_user_private_by_email(email)
        if not user:
            # Handle failed login event
            await AuthEventHandler.handle_login_failed(
                email=email, reason="user_not_found", ip_address=ip_address
            )
            return None

        # Check password
        if not user.password_hash:
            logger.warning(f"User {email} has no password hash")
            await AuthEventHandler.handle_login_failed(
                email=email,
                reason="no_password",
                ip_address=ip_address,
                user_id=str(user.id),
            )
            return None

        if not AuthService.verify_password(password, user.password_hash):
            # Handle failed login event
            await AuthEventHandler.handle_login_failed(
                email=email,
                reason="invalid_password",
                ip_address=ip_address,
                user_id=str(user.id),
            )
            return None

        # Check if email is verified
        if not user.email_verified:
            # Handle failed login event
            await AuthEventHandler.handle_login_failed(
                email=email,
                reason="email_not_verified",
                ip_address=ip_address,
                user_id=str(user.id),
            )
            return None

        # Update last login
        await auth_repo.update_user_last_login(str(user.id))

        # Handle success event
        await AuthEventHandler.handle_login_success(
            user_id=str(user.id), email=email, ip_address=ip_address
        )

        return user

    @staticmethod
    async def authenticate_google_user(id_token_str: str) -> "tuple[UserPrivate, bool]":
        """Authenticate or create user from Google ID token."""
        try:
            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            email = idinfo["email"]
            google_id = idinfo.get("sub")  # Google's unique user ID
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            profile_image = idinfo.get("picture")

            # Check if user exists
            user = await _get_user_service().get_user_private_by_email(email)
            is_new = False

            if not user:
                # Create new user with Google as provider
                user_dict = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "profile_image": profile_image,
                    "google_id": google_id,  # Store Google's unique ID
                }
                created_user = await _get_user_service().create_user(
                    user_data=user_dict,
                    auth_provider=AuthProvider.GOOGLE,
                    skip_email_verification=True,  # Google emails are pre-verified
                    return_private=True,
                    trigger_events=True,  # Trigger events for Google registration
                )
                # Since return_private=True, this will be UserPrivate
                from app.domains.user.schemas import UserPrivate

                user = created_user if isinstance(created_user, UserPrivate) else None
                if not user:
                    raise GoogleAuthError("Failed to create user account")
                is_new = True

                # Handle registration completed event for new Google users
                await AuthEventHandler.handle_registration_completed(
                    user_id=str(user.id), provider=AuthProvider.GOOGLE
                )
            else:
                # User exists - update Google info and handle mixed auth
                update_fields = {}

                # Store Google ID if not already stored
                if not user.google_id:
                    update_fields["google_id"] = google_id
                    logger.info(f"Linking Google account to existing user: {email}")

                # Update auth provider to support both if currently local-only
                if user.auth_provider == AuthProvider.LOCAL:
                    update_fields["auth_provider"] = "both"  # Now supports both methods
                    logger.info(
                        f"User {email} can now login with both email/password and Google"
                    )
                elif user.auth_provider == AuthProvider.GOOGLE and not user.google_id:
                    # Old Google user without stored ID
                    update_fields["google_id"] = google_id

                # Update profile image if newer
                if profile_image and profile_image != user.profile_image:
                    update_fields["profile_image"] = profile_image

                # Apply updates if any
                if update_fields:
                    await auth_repo.link_google_account(
                        user_id=str(user.id),
                        google_id=google_id,
                        update_fields=update_fields,
                    )

                # Verify it's the same Google account if google_id was already stored
                if user.google_id and user.google_id != google_id:
                    logger.warning(
                        f"Different Google account attempted for email: {email}"
                    )
                    raise GoogleAuthError(
                        "This email is already linked to a different Google account. "
                        "Please use the original Google account or login with email/password."
                    )

            # Update last login
            await auth_repo.update_user_last_login(str(user.id))

            # Handle login success event
            await AuthEventHandler.handle_login_success(
                user_id=str(user.id),
                email=email,
                provider=AuthProvider.GOOGLE,
                is_new=is_new,
            )

            return user, is_new

        except ValueError as e:
            logger.error(f"Google auth failed: {e}")
            raise GoogleAuthError("Invalid Google ID token") from e
        except GoogleAuthError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Log unexpected errors but don't expose details
            logger.error(f"Unexpected error in Google auth: {e}")
            raise GoogleAuthError("Authentication failed. Please try again.") from e

    # ============================================================
    # 3. SESSION & TOKEN MANAGEMENT
    # ============================================================

    @staticmethod
    async def create_session(
        user_id: str,
        fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[SessionResponse, str, str]:
        """Create new user session."""
        # Generate refresh token
        refresh_token = AuthService.create_refresh_token()

        # Prepare session data
        session_data = {
            "user_id": user_id,
            "fingerprint": fingerprint,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "refresh_token": refresh_token,
            "expires_at": now_utc() + timedelta(days=30),
        }

        # Create session in database
        session_model = await auth_repo.create_session(session_data)

        # Convert to response schema
        session = SessionResponse.from_model(session_model)

        # Create access token
        access_token = AuthService.create_access_token(user_id, str(session.id))

        return session, access_token, refresh_token

    @staticmethod
    async def refresh_access_token(refresh_token: str) -> tuple[str, str] | None:
        """Refresh access token using refresh token."""
        # Find session by refresh token
        session = await auth_repo.get_session_by_refresh_token(refresh_token)
        if not session:
            return None

        # Update session activity
        await auth_repo.update_session_activity(str(session.id))

        # Generate new tokens (ensure IDs are strings)
        user_id = str(session.user_id) if session.user_id else None
        session_id = str(session.id) if session.id else None

        if not user_id or not session_id:
            return None

        new_access = AuthService.create_access_token(user_id, session_id)
        new_refresh = AuthService.create_refresh_token()

        # Update refresh token in database
        update_success = await auth_repo.update_refresh_token(session_id, new_refresh)
        if not update_success:
            logger.error(
                f"Failed to update refresh token in database for session {session_id}"
            )
            # Return None to indicate failure - tokens not persisted
            return None

        # Handle token refreshed event
        await AuthEventHandler.handle_token_refreshed(
            user_id=user_id, session_id=session_id
        )

        return new_access, new_refresh

    @staticmethod
    async def get_user_sessions(user_id: str) -> list[SessionResponse]:
        """Get all active sessions for a user."""
        session_models = await auth_repo.get_user_sessions(
            user_id, include_expired=False
        )
        return [SessionResponse.from_model(model) for model in session_models]

    @staticmethod
    async def revoke_user_session(session_id: str, user_id: str) -> bool:
        """Revoke a specific session for a user (security check included)."""
        return await auth_repo.delete_user_session(session_id, user_id)

    # ============================================================
    # 4. LOGOUT
    # ============================================================

    @staticmethod
    async def logout_user_session(token: str) -> bool:
        """Logout user by invalidating session."""
        payload = AuthService.decode_access_token(token)
        if not payload:
            return False

        session_id = payload.get("session_id")
        user_id = payload.get("user_id")
        if not session_id:
            return False

        # Delete session
        success = await auth_repo.delete_session(session_id)

        if success:
            # Handle logout event
            await AuthEventHandler.handle_logout(user_id=user_id, session_id=session_id)
            return True

        return False

    @staticmethod
    async def logout_all_sessions(user_id: str) -> bool:
        """Logout user from all devices by invalidating all sessions."""
        count = await auth_repo.delete_all_user_sessions(user_id)

        if count > 0:
            logger.info(f"Logged out user {user_id} from {count} sessions")
            return True

        return False

    # ============================================================
    # 5. PASSWORD RESET & CHANGE
    # ============================================================

    @staticmethod
    async def send_password_reset_email(email: EmailStr) -> bool:
        """Send password reset email."""
        user = await _get_user_service().get_user_private_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True

        # Generate token
        token = secrets.token_urlsafe(32)
        expiry = now_utc() + timedelta(hours=24)

        # Store token
        await auth_repo.set_password_reset_token(
            user_id=str(user.id), token=token, expiry=expiry
        )

        # Send email via event
        await AuthEventHandler.handle_password_reset_requested(
            user_id=str(user.id),
            email=user.email,
            reset_token=token,
            user_name=user.first_name,
        )

        return True

    @staticmethod
    async def validate_reset_token(token: str) -> bool:
        """Validate password reset token."""
        # Find user by token - this will raise InvalidTokenError if token is invalid/expired
        user_data = await auth_repo.get_user_by_reset_token(token)
        if not user_data:
            raise InvalidTokenError("password reset", "Token is invalid or expired")
        return True

    @staticmethod
    async def validate_registration_token(token: str) -> bool:
        """Validate registration token (from email verification link).

        Registration tokens are stored in password_reset_token (shared with password reset
        flow). This method validates tokens for the complete-registration flow.
        """
        user_data = await auth_repo.get_user_by_reset_token(token)
        if not user_data:
            raise InvalidTokenError("verification", "Token is invalid or expired")
        return True

    @staticmethod
    async def reset_password(token: str, new_password: str) -> "UserPrivate":
        """Reset password using token."""
        # Find user by token
        user_data = await auth_repo.get_user_by_reset_token(token)
        if not user_data:
            raise InvalidTokenError("password reset", "Token is invalid or expired")

        # Update password and clear token
        password_hash = AuthService.hash_password(new_password)
        await auth_repo.update_user_password(str(user_data["_id"]), password_hash)
        await auth_repo.clear_password_reset_token(str(user_data["_id"]))

        # Handle password reset completed event
        await AuthEventHandler.handle_password_reset_completed(
            user_id=str(user_data["_id"]), email=user_data["email"]
        )

        # Return updated user
        return await _get_user_service().get_user_private(str(user_data["_id"]))

    @staticmethod
    async def change_user_password(user_id: str, new_password: str) -> bool:
        """Change password for a user (after verification)."""
        password_hash = AuthService.hash_password(new_password)

        result = await auth_repo.update_user_password(user_id, password_hash)

        if result:
            logger.info(f"Password changed for user {user_id}")
            # Get user email for event handler
            user = await _get_user_service().get_user_private(user_id)
            if user and user.email:
                await AuthEventHandler.handle_password_reset_completed(
                    user_id=user_id, email=user.email
                )
            return True

        return False

    # ============================================================
    # 6. TOKEN UTILITIES (Low-level)
    # ============================================================

    @staticmethod
    def create_access_token(user_id: str, session_id: str) -> str:
        """Create JWT access token."""
        # Ensure IDs are strings (not ObjectId)
        payload = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "exp": now_utc() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": now_utc(),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def create_refresh_token() -> str:
        """Create secure refresh token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def decode_access_token(token: str) -> dict[str, Any] | None:
        """Decode and validate access token."""
        token_preview = token[:20] + "..." if len(token) > 20 else token
        logger.debug(f"🔓 [JWT Decode] Attempting to decode token: {token_preview}")

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            logger.debug(
                f"🔓 [JWT Decode] Successfully decoded token, payload: {payload}"
            )
            return payload
        except jwt.ExpiredSignatureError:
            token_preview = token[:20] + "..." if len(token) > 20 else token
            logger.warning(f"🔓 Token expired: {token_preview}")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(
                f"🔓 [JWT Decode] Invalid token: {e} for token: {token_preview}"
            )
            return None

    @staticmethod
    async def verify_access_token(token: str) -> "UserPublic | None":
        """Verify token and return user."""
        payload = AuthService.decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        user = await _get_user_service().get_user_public(user_id)
        return user if user else None

    @staticmethod
    async def verify_token_with_details(
        token: str,
    ) -> "tuple[UserPublic | None, str | None]":
        """Verify token and return user with error details.

        Returns:
            Tuple of (user, error_message)
            - (user, None) if token is valid
            - (None, error_message) if token is invalid
        """
        token_preview = token[:20] + "..." if len(token) > 20 else token
        logger.info(f"🔍 [Token Verify] Verifying token: {token_preview}")

        payload = AuthService.decode_access_token(token)
        if not payload:
            logger.warning(
                f"🔍 [Token Verify] Token decode failed for: {token_preview}"
            )
            return None, "Invalid or expired token"

        logger.info(
            f"🔍 [Token Verify] Token decoded successfully, payload keys: {list(payload.keys())}"
        )

        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("🔍 No user_id in token payload")
            return None, "Invalid token format"

        logger.info(f"🔍 [Token Verify] Looking up user by ID: {user_id}")

        user = await _get_user_service().get_user_public(user_id)
        if not user:
            logger.warning(f"🔍 User not found: {user_id}")
            return None, "User not found"

        logger.info(
            f"🔍 [Token Verify] Successfully verified token for user: {user.email} (role: {user.role})"
        )
        return user, None

    @staticmethod
    async def get_session_id_from_token(token: str) -> str | None:
        """Extract session ID from access token."""
        payload = AuthService.decode_access_token(token)
        return payload.get("session_id") if payload else None

    # ============================================================
    # 7. PASSWORD UTILITIES (Low-level)
    # ============================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            # Ensure password is string and encode it
            if isinstance(password, bytes):
                password_bytes = password
            else:
                password_bytes = password.encode("utf-8")

            # Ensure hashed is bytes
            if isinstance(hashed, bytes):
                hashed_bytes = hashed
            else:
                hashed_bytes = hashed.encode("utf-8")

            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except (ValueError, AttributeError):
            # Invalid salt or encoding error means password doesn't match
            return False

    # ============================================================
    # 8. API RESPONSE BUILDERS
    # ============================================================

    @staticmethod
    def format_user_for_api(user: "UserPrivate | UserPublic") -> dict[str, Any]:
        """Format user object for API responses with consistent structure."""
        from app.shared.imgproxy import build_avatar_urls

        # Handle role - convert enum to string if needed
        role = "user"  # default
        if hasattr(user, "role"):
            role = user.role.value if hasattr(user.role, "value") else str(user.role)

        # Profile photo: signed imgproxy URLs for each preset so the frontend
        # header avatar populates on login/register/OAuth without an extra
        # /api/user/me/profile round-trip.
        photo_key = getattr(user, "photo_key", None)
        photo_urls = build_avatar_urls(photo_key)

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_image": user.profile_image,
            "email_verified": user.email_verified,
            "role": role,
            "photo_key": photo_key,
            "photo_urls": photo_urls,
        }

    @staticmethod
    async def create_auth_response(
        user_id: str,
        fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Create complete authentication response with session and tokens.

        Used by login, register, and OAuth endpoints to reduce duplication.
        """
        # Get full user data
        user = await _get_user_service().get_user_private(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Create session with tokens
        session, access_token, refresh_token = await AuthService.create_session(
            user_id,
            fingerprint=fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "user": AuthService.format_user_for_api(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": str(session.id) if session.id else None,
        }

    @staticmethod
    async def create_google_auth_response(
        user: "UserPrivate",
        is_new: bool,
        fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Create response for Google authentication endpoints."""
        # Create session with tokens
        session, access_token, refresh_token = await AuthService.create_session(
            str(user.id),
            fingerprint=fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": AuthService.format_user_for_api(user),
            "is_new_user": is_new,
            "session_id": str(session.id) if session.id else None,
        }
