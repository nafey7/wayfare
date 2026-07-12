"""User domain package.

Clean domain-driven design for user management.
"""

# Schemas (Data Models)
# Exceptions
from .exceptions import (
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    InvalidUserStatusError,
    UserDomainError,
    UserNotFoundError,
    ValidationError,
)

# Permissions
from .permissions import UserPermissions
from .schemas import (
    Address,
    UserBase,
    UserCreateRequest,
    UserPreferencesUpdateRequest,
    UserPrivate,
    UserPublic,
    UserResponse,
    UserStatistics,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)

# Service Class (Main API)
from .service import UserService

__all__ = [
    # Schemas
    "Address",
    # Exceptions
    "EmailAlreadyExistsError",
    "InsufficientPermissionsError",
    "InvalidUserStatusError",
    "UserBase",
    "UserCreateRequest",
    "UserDomainError",
    "UserNotFoundError",
    # Permissions
    "UserPermissions",
    "UserPreferencesUpdateRequest",
    "UserPrivate",
    "UserPublic",
    "UserResponse",
    # Service
    "UserService",
    "UserStatistics",
    "UserStatusUpdateRequest",
    "UserUpdateRequest",
    "ValidationError",
]
