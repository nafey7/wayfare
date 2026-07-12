"""User service for orchestrating user operations.

Service class that provides clear separation between public and authenticated operations.
"""

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.domains.common import AuthProvider, EmailStr

from . import repository, validators
from .constants import (
    DEFAULT_USER_SEARCH_LIMIT,
    MAX_USER_SEARCH_LIMIT,
    is_myvoya_team_admin_email,
)
from .enums import UserRole, UserStatus
from .events import UserEventHandler
from .exceptions import (
    InsufficientPermissionsError,
    InvalidUserStatusError,
    UserNotFoundError,
)
from .permissions import UserPermissions
from .schemas import (
    ProfileAggregateResponse,
    ProfileUserResponse,
    UserCreateRequest,
    UserPrivate,
    UserPublic,
    UserResponse,
    UserStatistics,
    UserUpdateRequest,
)

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations with clear auth separation."""

    def __init__(self, current_user: UserPublic | None = None) -> None:
        """Initialize service with optional current user for authenticated operations."""
        self.current_user = current_user
        self.permissions = UserPermissions(current_user) if current_user else None

    # ============================================================
    # PUBLIC OPERATIONS (No authentication required)
    # ============================================================

    @staticmethod
    async def create_user(
        user_data: UserCreateRequest | dict[str, Any],
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        skip_email_verification: bool = False,
        return_private: bool = False,
        trigger_events: bool = True,
    ) -> UserPublic | UserPrivate:
        """Create new user - flexible for all registration types.

        Args:
            user_data: User data as UserCreateRequest or dict
            auth_provider: Authentication provider (LOCAL, GOOGLE, etc.)
            skip_email_verification: Whether to skip email verification
            return_private: Return UserPrivate instead of UserPublic
            trigger_events: Whether to trigger user creation events
        """
        # Convert to dict if needed
        if isinstance(user_data, UserCreateRequest):
            email = str(user_data.email)
            user_dict = user_data.model_dump(exclude_unset=True)
        else:
            email = user_data.get("email", "")
            user_dict = user_data

        logger.info(f"Creating new user: {email} via {auth_provider}")

        # Business validation (requires database check)
        await validators.validate_email_uniqueness(email)

        # Set auth provider and email verification
        user_dict["auth_provider"] = auth_provider

        # Handle email verification based on provider
        if auth_provider == AuthProvider.GOOGLE:
            user_dict["email_verified"] = True  # Google emails are pre-verified
        elif skip_email_verification:
            user_dict["email_verified"] = True
        else:
            user_dict["email_verified"] = user_dict.get("email_verified", False)

        # Set is_tester based on environment if not explicitly provided
        if "is_tester" not in user_dict:
            user_dict["is_tester"] = settings.ENVIRONMENT != "production"

        # Set discount_eligible to True for new users (promotional $50 discount)
        # Existing users in DB default to False (field doesn't exist)
        if "discount_eligible" not in user_dict:
            user_dict["discount_eligible"] = True

        # Grant admin role to @myvoya.ai team members unless caller already set a role.
        # For LOCAL signups, role is stored before email_verified=True; access still
        # requires a verified email at login (see auth service email_verified check).
        if "role" not in user_dict and is_myvoya_team_admin_email(email):
            user_dict["role"] = UserRole.ADMIN
            logger.info("Assigned admin role to @myvoya.ai user: %s", email)

        # Create user
        user_model = await repository.create_user(user_dict)

        # Convert to appropriate schema
        if return_private:
            user = UserPrivate.from_model(user_model)
        else:
            user = UserPublic.from_model(user_model)

        # Handle post-creation events if requested
        if trigger_events:
            await UserEventHandler.handle_user_created(
                UserPublic.from_model(user_model),
                skip_email_verification or auth_provider == AuthProvider.GOOGLE,
            )

        return user

    @staticmethod
    async def get_user_public(user_id: str) -> UserPublic:
        """Get user by ID - returns UserPublic schema."""
        user_model = await repository.get_user_by_id(user_id)
        if not user_model:
            raise UserNotFoundError(f"User {user_id} not found")

        return UserPublic.from_model(user_model)

    @staticmethod
    async def get_user_private(user_id: str) -> UserPrivate:
        """Get user with all fields including sensitive data - internal use only."""
        user_model = await repository.get_user_by_id(user_id)
        if not user_model:
            raise UserNotFoundError(f"User {user_id} not found")

        return UserPrivate.from_model(user_model)

    @staticmethod
    async def get_user_public_by_email(email: str | EmailStr) -> UserPublic | None:
        """Get user by email - returns UserPublic schema."""
        user_model = await repository.get_user_by_email(str(email))
        return UserPublic.from_model(user_model) if user_model else None

    @staticmethod
    async def get_user_private_by_email(email: str | EmailStr) -> UserPrivate | None:
        """Get full user by email with sensitive fields - internal use only."""
        user_model = await repository.get_user_by_email(str(email))
        return UserPrivate.from_model(user_model) if user_model else None

    @staticmethod
    async def verify_email(user_id: str) -> bool:
        """Mark user email as verified - token-based."""
        logger.info(f"Verifying email for user {user_id}")

        success = await repository.verify_email(user_id)

        if success:
            user = await UserService.get_user_public(user_id)
            await UserEventHandler.handle_email_verified(user)

        return success

    # ============================================================
    # AUTHENTICATED OPERATIONS (Require current_user)
    # ============================================================

    async def get_profile(self, user_id: str) -> ProfileAggregateResponse:
        """Get full profile aggregate: user + preferences + passengers (primary first).

        Single call for entire profile page. Uses parallel fetches.
        """
        from app.domains.passenger.repository import get_passengers_for_user
        from app.domains.user_preferences.repository import get_preferences

        user_model, preferences, passengers = await asyncio.gather(
            repository.get_user_by_id(user_id),
            get_preferences(user_id),
            get_passengers_for_user(user_id),
        )
        if not user_model:
            raise UserNotFoundError(f"User {user_id} not found")

        user_public = UserPublic.from_model(user_model)
        return ProfileAggregateResponse(
            user=ProfileUserResponse.from_user_public(user_public),
            preferences=preferences,
            passengers=passengers,
        )

    async def get_user_profile(self, user_id: str) -> UserResponse:
        """Get user profile with appropriate visibility."""
        logger.info(f"Getting profile for user {user_id}")

        # Get user model
        user_model = await repository.get_user_by_id(user_id)
        if not user_model:
            raise UserNotFoundError(f"User {user_id} not found")

        # Convert to UserPublic
        user = UserPublic.from_model(user_model)

        # Add extra fields for response
        extra_fields = {}
        if hasattr(user_model, "plan_id"):
            extra_fields["plan_id"] = (
                str(user_model.plan_id) if user_model.plan_id else None
            )
        if hasattr(user_model, "subscription_id"):
            extra_fields["subscription_id"] = (
                str(user_model.subscription_id) if user_model.subscription_id else None
            )

        # Check if statistics should be included
        if self.current_user.id == user_id or self.permissions.can_view_analytics():
            stats_data = await repository.get_user_statistics(user_id)
            if stats_data:
                extra_fields["statistics"] = UserStatistics(**stats_data)

        return UserResponse.from_user(user, **extra_fields)

    async def get_user_statistics(self, user_id: str) -> UserStatistics:
        """Get detailed user statistics - self or admin only."""
        logger.info(f"Getting statistics for user {user_id}")

        # Check permissions
        if (
            self.current_user.id != user_id
            and not self.permissions.can_view_analytics()
        ):
            raise InsufficientPermissionsError("Not authorized to view statistics")

        stats_data = await repository.get_user_statistics(user_id)
        return UserStatistics(**stats_data) if stats_data else UserStatistics()

    async def update_user(
        self, user_id: str, update_data: UserUpdateRequest
    ) -> UserPublic:
        """Update user with validation and authorization."""
        logger.info(f"Updating user {user_id}")

        # Check if current user can update this profile (self or admin)
        is_self = self.current_user.id == user_id
        if not (is_self or self.permissions.can_manage_users()):
            raise InsufficientPermissionsError("Not authorized to update this user")

        # Get existing user
        existing_user = await self.get_user_public(user_id)

        # Check if user can update their profile
        existing_perms = UserPermissions(existing_user)
        if not existing_perms.can_update_profile():
            raise InvalidUserStatusError(
                "User account status does not allow profile updates"
            )

        # Pydantic has already validated structure and format
        # Get update data
        update_dict = update_data.model_dump(exclude_unset=True)

        # Additional business logic validation using validators
        if "email" in update_dict and update_dict["email"] != existing_user.email:
            await validators.validate_email_uniqueness(update_dict["email"])

        if update_dict.get("mobile"):
            validators.validate_phone_number(update_dict["mobile"])

        if update_dict.get("profile_image"):
            validators.validate_profile_image_url(update_dict["profile_image"])

        # Check field-level permissions
        for field_name in update_dict:
            if not self.permissions.can_update_field(field_name):
                raise InsufficientPermissionsError(
                    f"Not authorized to update field: {field_name}"
                )

        # Update user
        updated_model = await repository.update_user(user_id, update_dict)
        if not updated_model:
            raise UserNotFoundError(f"Failed to update user {user_id}")

        updated_user = UserPublic.from_model(updated_model)

        # Handle post-update events
        await UserEventHandler.handle_user_updated(updated_user, update_dict)

        return updated_user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user with authorization check."""
        logger.info(f"Deleting user {user_id}")

        # Check permissions
        is_self_delete = self.current_user.id == user_id

        if not (is_self_delete or self.permissions.can_manage_users()):
            raise InsufficientPermissionsError("Not authorized to delete this user")

        # Get user and check if deletable
        user = await self.get_user_public(user_id)
        user_perms = UserPermissions(user)

        if not user_perms.can_delete_account():
            raise InvalidUserStatusError(
                "User account cannot be deleted in current state"
            )

        # Delete user
        success = await repository.delete_user(user_id)

        if success:
            await UserEventHandler.handle_user_deleted(
                user, deleted_by_self=is_self_delete
            )

        return success

    # ============================================================
    # ADMIN OPERATIONS (Require admin role)
    # ============================================================

    async def search_users(
        self,
        search_term: str | None = None,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = DEFAULT_USER_SEARCH_LIMIT,
    ) -> list[UserPublic]:
        """Search users - admin only."""

        if not self.permissions.can_manage_users():
            raise InsufficientPermissionsError("Not authorized to search users")

        logger.info("Searching users with filters")

        # Validate pagination
        skip = max(0, skip)
        limit = min(max(1, limit), MAX_USER_SEARCH_LIMIT)

        # Extract filters
        status = None
        role = None
        verified_only = False

        if filters:
            status = filters.get("status")
            role = filters.get("role")
            verified_only = bool(filters.get("verified"))

        # Execute search
        user_models = await repository.search_users(
            search_term=search_term,
            status=status,
            role=role,
            verified_only=verified_only,
            skip=skip,
            limit=limit,
        )

        return [UserPublic.from_model(model) for model in user_models]

    async def count_users(self, filters: dict[str, Any] | None = None) -> int:
        """Count users - admin only."""

        if not self.permissions.can_manage_users():
            raise InsufficientPermissionsError("Not authorized to count users")

        status = None
        role = None
        verified_only = False

        if filters:
            status = filters.get("status")
            role = filters.get("role")
            verified_only = bool(filters.get("verified"))

        return await repository.count_users(
            status=status, role=role, verified_only=verified_only
        )

    async def update_user_status(self, user_id: str, new_status: UserStatus) -> bool:
        """Update user status - admin only."""
        logger.info(f"Updating user {user_id} status to {new_status}")

        # Check permissions
        if not self.permissions.can_change_user_status(user_id, new_status):
            raise InsufficientPermissionsError("Not authorized to change user status")

        # Get current user for old status
        user = await self.get_user_public(user_id)
        old_status = user.status

        # Update status
        updated_model = await repository.update_user(user_id, {"status": new_status})
        success = updated_model is not None

        if success:
            # Refresh user and send notification
            updated_user = await self.get_user_public(user_id)
            await UserEventHandler.handle_status_changed(
                updated_user, old_status, new_status
            )

        return success
