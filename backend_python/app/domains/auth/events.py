"""Authentication event handlers - simple and clean."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from app.domains.common import EmailStr
from app.domains.email import EmailService, EmailType

logger = logging.getLogger(__name__)


# Module-level reference set for detached background tasks. asyncio.create_task
# does not hold a strong reference to the task, so without this the task can
# be garbage-collected mid-flight. Tasks remove themselves on completion.
_background_tasks: set[asyncio.Task[None]] = set()


def _log_background_task_exception(task: asyncio.Task[None]) -> None:
    """Surface exceptions from detached tasks through our logger instead of
    Python's default 'Task exception was never retrieved' warning."""
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc is not None:
        logger.error(
            f"[BackgroundTask] {task.get_name()} raised: {exc}",
            exc_info=(type(exc), exc, exc.__traceback__),
        )


def _spawn_background(coro: Coroutine[Any, Any, None], *, name: str) -> None:
    """Schedule a coroutine as a detached background task.

    Used to genuinely decouple side-effects (like CRM sync) from the HTTP
    request path, so a slow or hanging integration cannot add latency to
    the user-facing response.
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    task.add_done_callback(_log_background_task_exception)


async def _sync_to_activecampaign(user_id: str) -> None:
    """Sync a newly registered user to ActiveCampaign.

    Scheduled via `_spawn_background` from the event handlers so the HTTP
    response is not blocked on AC's network round-trip. Failures are logged
    and swallowed; when no API credentials are configured the call is a
    no-op.
    """
    # Local imports keep module load lightweight and avoid pulling httpx /
    # UserService into module-import time when the integration is unused.
    from app.domains.user import UserNotFoundError, UserService
    from integrations.activecampaign import get_activecampaign_client

    try:
        client = get_activecampaign_client()
        if client is None:
            return

        try:
            user = await UserService.get_user_public(user_id)
        except UserNotFoundError:
            # User was deleted between signup and sync — unusual but not an
            # error for this integration. Logged as info to keep signal:noise
            # high on the actual AC-down error log.
            logger.info(
                f"[ActiveCampaign] Skipping sync — user {user_id} no longer exists"
            )
            return

        if not user.email:
            logger.warning(
                f"[ActiveCampaign] Skipping sync — user {user_id} has no email"
            )
            return

        await client.create_contact(
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
        )
    except Exception as e:
        logger.error(
            f"[ActiveCampaign] Failed to sync contact for user {user_id}: {e}",
            exc_info=True,
        )


class AuthEventHandler:
    """Handle authentication events with direct method calls."""

    # ==============================================================
    # REGISTRATION EVENTS
    # ==============================================================

    @staticmethod
    async def handle_registration_started(user_id: str, email: EmailStr) -> None:
        """Handle registration initiation."""
        logger.info(f"Registration started: user={user_id}, email={email}")
        # Detach AC sync from the request path so a slow or hanging
        # ActiveCampaign cannot delay the signup HTTP response.
        _spawn_background(
            _sync_to_activecampaign(user_id),
            name=f"ac-sync-started-{user_id}",
        )

    @staticmethod
    async def handle_registration_completed(
        user_id: str, provider: str = "local"
    ) -> None:
        """Handle registration completion - send welcome email."""
        logger.info(f"Registration completed: user={user_id}, provider={provider}")

        # Detached AC sync. Google OAuth signups never emit
        # handle_registration_started, so this is the only hook that catches
        # them. Duplicates on the email/password path (where started already
        # fired) are treated as success by the client (HTTP 422 ⇒ ok).
        _spawn_background(
            _sync_to_activecampaign(user_id),
            name=f"ac-sync-completed-{user_id}",
        )

        # Get user details for the email
        from app.domains.user import UserService

        user = await UserService.get_user_public(user_id)

        if user:
            # Send welcome email
            await EmailService.send_email(
                email_type=EmailType.WELCOME,
                recipient_email=user.email,
                context={"user_name": user.first_name or "there"},
            )
            logger.info(f"Welcome email sent to {user.email}")

    # ==============================================================
    # LOGIN/LOGOUT EVENTS
    # ==============================================================

    @staticmethod
    async def handle_login_success(
        user_id: str,
        email: EmailStr,
        ip_address: str | None = None,
        provider: str = "local",
        is_new: bool = False,
    ) -> None:
        """Handle successful login."""
        logger.info(
            f"Login success: user={user_id}, email={email}, ip={ip_address}, provider={provider}"
        )

        if is_new:
            logger.info(f"New user registered via {provider}: {email}")

    @staticmethod
    async def handle_login_failed(
        email: EmailStr,
        reason: str,
        ip_address: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Handle failed login attempt."""
        if user_id:
            # Known user - could track failed attempts for account locking
            logger.warning(
                f"Login failed: user={user_id}, email={email}, reason={reason}, ip={ip_address}"
            )
        else:
            # Unknown user - potential probe attempt
            logger.warning(
                f"Login failed: email={email}, reason={reason}, ip={ip_address}"
            )

        # Could implement rate limiting or account locking here
        # For now, just log the attempt

    @staticmethod
    async def handle_logout(user_id: str, session_id: str) -> None:
        """Handle user logout."""
        logger.info(f"User logout: user={user_id}, session={session_id}")

    # ==============================================================
    # TOKEN MANAGEMENT EVENTS
    # ==============================================================

    @staticmethod
    async def handle_token_refreshed(user_id: str, session_id: str) -> None:
        """Handle token refresh."""
        logger.debug(f"Token refreshed: user={user_id}, session={session_id}")

    # ==============================================================
    # PASSWORD EVENTS
    # ==============================================================

    @staticmethod
    async def handle_password_reset_requested(
        user_id: str, email: EmailStr, reset_token: str, user_name: str | None = None
    ) -> None:
        """Handle password reset request with email sending."""
        logger.info(f"Password reset requested: user={user_id}, email={email}")

        try:
            await EmailService.send_email(
                EmailType.PASSWORD_RESET,
                email,
                {"reset_token": reset_token, "user_name": user_name or "User"},
            )
        except Exception as e:
            logger.warning(f"Failed to send password reset email to {email}: {e}")

    @staticmethod
    async def handle_password_reset_completed(user_id: str, email: EmailStr) -> None:
        """Handle password reset completion."""
        logger.info(f"Password reset completed: user={user_id}")

        try:
            await EmailService.send_email(
                EmailType.PASSWORD_CHANGED, email, {"first_name": "User"}
            )
        except Exception as e:
            logger.warning(
                f"Failed to send password reset confirmation to {email}: {e}"
            )

    @staticmethod
    async def handle_registration_setup_requested(
        user_id: str, email: EmailStr, setup_token: str, user_name: str | None = None
    ) -> None:
        """Handle registration setup request with email sending."""
        logger.info(
            f"🎬 [Event] Registration setup requested: user={user_id}, email={email}"
        )
        logger.info(
            f"🎬 [Event] Setup token: {setup_token[:8]}..., user_name: {user_name}"
        )

        try:
            logger.info(
                f"🎬 [Event] Calling EmailService.send_email for REGISTRATION_SETUP to: {email}"
            )
            email_result = await EmailService.send_email(
                EmailType.REGISTRATION_SETUP,
                email,
                {"setup_token": setup_token, "user_name": user_name or "User"},
            )
            logger.info(
                f"🎬 [Event] EmailService.send_email result: {email_result} for {email}"
            )
            if email_result:
                logger.info(
                    f"🎬 [Event] ✅ Registration setup email sent successfully to: {email}"
                )
            else:
                logger.error(
                    f"🎬 [Event] ❌ Registration setup email failed to send to: {email}"
                )
        except Exception as e:
            logger.error(
                f"🎬 [Event] ❌ Exception sending registration setup email to {email}: {e}",
                exc_info=True,
            )

    # ==============================================================
    # SECURITY EVENTS
    # ==============================================================

    @staticmethod
    async def handle_suspicious_activity(details: dict[str, Any]) -> None:
        """Handle suspicious activity detection."""
        logger.warning(f"Suspicious activity detected: {details}")
        # Could trigger security alerts, temporary locks, etc.

    @staticmethod
    async def handle_account_locked(
        user_id: str, reason: str, locked_until: str | None = None
    ) -> None:
        """Handle account locking."""
        logger.warning(
            f"Account locked: user={user_id}, reason={reason}, until={locked_until}"
        )
        # Could send notification email to user
