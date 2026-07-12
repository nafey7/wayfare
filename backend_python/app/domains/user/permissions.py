"""User permissions and authorization logic.

Handles all authorization checks for user operations.
"""

from .enums import UserRole, UserStatus
from .schemas import UserPublic

# Fields that cannot be updated directly by users
PROTECTED_FIELDS = frozenset(
    [
        "id",
        "_id",
        "email",
        "email_verified",
        "email_verified_at",
        "created_at",
        "updated_at",
        "deleted_at",
        "auth_provider",
        "role",
        "status",
        "failed_login_attempts",
        "last_failed_login",
    ]
)

# Fields that only admins can update
ADMIN_ONLY_FIELDS = frozenset(
    ["subscription_tier", "credits", "limits", "plan_id", "subscription_id", "quota"]
)

# Fields visible to other users (public profile)
PUBLIC_FIELDS = frozenset(["id", "first_name", "profile_image"])

# Fields visible to admins
ADMIN_VISIBLE_FIELDS = frozenset(
    [
        "id",
        "email",
        "first_name",
        "last_name",
        "status",
        "role",
        "created_at",
        "last_login",
        "email_verified",
        "subscription_tier",
        "plan_id",
    ]
)


class UserPermissions:
    """Centralized permission checks for user operations."""

    def __init__(self, user: UserPublic) -> None:
        """Initialize with the user to check permissions for."""
        self.user = user
        self.is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        self.is_super_admin = user.role == UserRole.SUPER_ADMIN
        self.is_active = user.status == UserStatus.ACTIVE

    # ========== BASIC ACCESS PERMISSIONS ==========

    def can_access_api(self) -> bool:
        """Check if user can access API endpoints."""
        return self.is_active

    def can_make_bookings(self) -> bool:
        """Check if user can make travel bookings."""
        return self.is_active and self.user.email_verified

    # ========== OWN PROFILE PERMISSIONS ==========

    def can_update_profile(self) -> bool:
        """Check if user can update their profile."""
        return self.user.status in [UserStatus.ACTIVE, UserStatus.SUSPENDED]

    def can_delete_account(self) -> bool:
        """Check if user can delete their account."""
        return self.user.status != UserStatus.DELETED

    def can_update_field(self, field_name: str) -> bool:
        """Check if user can update a specific field."""
        if field_name in PROTECTED_FIELDS:
            return False

        if field_name in ADMIN_ONLY_FIELDS:
            return self.is_admin

        return True

    # ========== VIEWING OTHER USERS PERMISSIONS ==========

    def can_view_user(self, target_user_id: str) -> bool:
        """Check if user can view another user's details."""
        # Users can view their own details
        if self.user.id == target_user_id:
            return True

        # Admins can view all users
        return self.is_admin

    def can_view_field(self, field_name: str, target_user_id: str) -> bool:
        """Check if user can view a specific field of another user."""
        # Own profile - can see everything
        if self.user.id == target_user_id:
            return True

        # Admin - can see admin fields
        if self.is_admin:
            return field_name in ADMIN_VISIBLE_FIELDS or field_name == "*"

        # Other users - only public fields
        return field_name in PUBLIC_FIELDS

    # ========== ADMIN OPERATIONS ==========

    def can_access_admin_panel(self) -> bool:
        """Check if user can access admin panel."""
        return self.is_admin

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.is_admin

    def can_view_analytics(self) -> bool:
        """Check if user can view system analytics."""
        return self.is_admin

    def can_manage_system_settings(self) -> bool:
        """Check if user can manage system settings."""
        return self.is_super_admin

    def can_change_user_status(
        self, target_user_id: str, new_status: UserStatus
    ) -> bool:
        """Check if user can change another user's status."""
        # Only admins can change status
        if not self.is_admin:
            return False

        # Cannot change own status to deleted/banned
        return not (
            self.user.id == target_user_id
            and new_status in [UserStatus.DELETED, UserStatus.BANNED]
        )
