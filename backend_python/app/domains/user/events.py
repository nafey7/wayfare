"""User domain event handlers.

Handles side effects like sending emails, notifications, and logging.
"""

import logging
from typing import Any

from app.domains.email import EmailService, EmailType

from .enums import UserStatus
from .schemas import UserPublic

logger = logging.getLogger(__name__)


class UserEventHandler:
    """Handle user domain events."""

    # ==============================================================
    # LIFECYCLE EVENTS
    # ==============================================================

    @staticmethod
    async def handle_user_created(
        user: UserPublic, skip_welcome_email: bool = False
    ) -> None:
        """Handle user creation event."""
        logger.info(f"User created: {user.id}")

        if not skip_welcome_email:
            try:
                await EmailService.send_email(
                    EmailType.WELCOME,
                    user.email,
                    {"first_name": user.first_name or "User"},
                )
            except Exception as e:
                # Don't fail user creation if email fails
                logger.warning(f"Failed to send welcome email to {user.email}: {e}")

    @staticmethod
    async def handle_email_verified(user: UserPublic) -> None:
        """Handle email verification event."""
        logger.info(f"Email verified for user {user.id}")

        try:
            await EmailService.send_email(
                EmailType.EMAIL_VERIFIED,
                user.email,
                {"first_name": user.first_name or "User"},
            )
        except Exception as e:
            logger.warning(f"Failed to send verification email to {user.email}: {e}")

    @staticmethod
    async def handle_user_deleted(
        user: UserPublic, deleted_by_self: bool = False
    ) -> None:
        """Handle user deletion event."""
        logger.info(f"User deleted: {user.id}")

        if deleted_by_self:
            try:
                await EmailService.send_email(
                    EmailType.ACCOUNT_DELETED,
                    user.email,
                    {"first_name": user.first_name or "User"},
                )
            except Exception as e:
                logger.warning(f"Failed to send deletion email to {user.email}: {e}")

    # ==============================================================
    # PROFILE EVENTS
    # ==============================================================

    @staticmethod
    async def handle_user_updated(user: UserPublic, changes: dict[str, Any]) -> None:
        """Handle user update event."""
        logger.info(f"User updated: {user.id}, fields: {list(changes.keys())}")

        # Send email if critical fields were updated
        critical_fields = {"email", "first_name", "last_name", "mobile"}
        if any(field in changes for field in critical_fields):
            try:
                # Profile update notification - not implemented yet
                # Could add EmailType.PROFILE_UPDATED if needed
                logger.info(f"Profile updated for {user.email}: {list(changes.keys())}")
            except Exception as e:
                logger.warning(
                    f"Failed to send profile update email to {user.email}: {e}"
                )

    @staticmethod
    async def handle_preferences_updated(
        user: UserPublic, changes: dict[str, Any]
    ) -> None:
        """Handle preferences update event."""
        logger.info(f"Preferences updated for user {user.id}: {list(changes.keys())}")
        # Could notify about important preference changes

    # ==============================================================
    # STATUS EVENTS
    # ==============================================================

    @staticmethod
    async def handle_status_changed(
        user: UserPublic, old_status: UserStatus, new_status: UserStatus
    ) -> None:
        """Handle user status change event."""
        logger.info(f"User {user.id} status changed from {old_status} to {new_status}")

        # Determine email type based on status change
        email_type = None

        if new_status == UserStatus.SUSPENDED:
            email_type = EmailType.ACCOUNT_SUSPENDED
        elif new_status == UserStatus.BANNED:
            email_type = EmailType.ACCOUNT_BANNED
        elif new_status == UserStatus.ACTIVE and old_status in [
            UserStatus.SUSPENDED,
            UserStatus.BANNED,
        ]:
            email_type = EmailType.ACCOUNT_REACTIVATED

        if email_type:
            try:
                await EmailService.send_email(
                    email_type,
                    user.email,
                    {
                        "first_name": user.first_name or "User",
                        "old_status": old_status,
                        "new_status": new_status,
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send status change email to {user.email}: {e}"
                )

    # ==============================================================
    # ACTIVITY EVENTS
    # ==============================================================

    @staticmethod
    async def handle_login(user: UserPublic) -> None:
        """Handle user login event."""
        logger.info(f"User logged in: {user.id}")
        # Could add login notification, security alerts, etc.
