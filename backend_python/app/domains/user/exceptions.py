"""User domain exceptions.

All custom exceptions for user operations with proper error handling.
"""

from typing import Any


class UserDomainError(Exception):
    """Base exception for all user domain errors."""

    def __init__(
        self, message: str = "User domain error occurred", code: str | None = None
    ) -> None:
        self.message = message
        self.code = code or "USER_ERROR"
        super().__init__(self.message)


# ==============================================================================
# LOOKUP EXCEPTIONS
# ==============================================================================


class UserNotFoundError(UserDomainError):
    """Raised when user is not found."""

    def __init__(self, user_id: str | None = None) -> None:
        message = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(message, "USER_NOT_FOUND")
        self.user_id = user_id


class EmailAlreadyExistsError(UserDomainError):
    """Raised when trying to create user with existing email."""

    def __init__(self, email: str | None = None) -> None:
        message = (
            f"Email {email} is already registered" if email else "Email already exists"
        )
        super().__init__(message, "EMAIL_EXISTS")
        self.email = email


# ==============================================================================
# VALIDATION EXCEPTIONS
# ==============================================================================


class ValidationError(UserDomainError):
    """Raised when validation fails."""

    def __init__(
        self, field: str | None = None, value: Any = None, reason: str | None = None
    ) -> None:
        if field and reason:
            message = f"Validation failed for {field}: {reason}"
        elif field:
            message = f"Invalid value for field: {field}"
        elif reason:
            message = f"Validation error: {reason}"
        else:
            message = "Validation failed"
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value
        self.reason = reason


class InvalidPhoneNumberError(ValidationError):
    """Raised when phone number format is invalid."""

    def __init__(self, phone: str | None = None, reason: str | None = None) -> None:
        super().__init__(
            field="phone", value=phone, reason=reason or "Invalid phone number format"
        )
        self.code = "INVALID_PHONE"


class InvalidAddressError(ValidationError):
    """Raised when address data is invalid."""

    def __init__(self, field: str | None = None, reason: str | None = None) -> None:
        super().__init__(
            field=f"address.{field}" if field else "address",
            reason=reason or "Invalid address data",
        )
        self.code = "INVALID_ADDRESS"


class InvalidPhotoError(ValidationError):
    """Raised when a profile photo upload fails validation (corrupt, dimensions, etc.)."""

    def __init__(self, reason: str | None = None) -> None:
        super().__init__(field="photo", reason=reason or "Invalid profile photo")
        self.code = "INVALID_PHOTO"


class UnsupportedPhotoTypeError(InvalidPhotoError):
    """Raised when the upload MIME type is not in the allowlist."""

    def __init__(self, content_type: str | None = None) -> None:
        super().__init__(
            reason=(
                f"Unsupported photo type: {content_type}"
                if content_type
                else "Unsupported photo type"
            )
        )
        self.code = "UNSUPPORTED_PHOTO_TYPE"
        self.content_type = content_type


class PhotoTooLargeError(InvalidPhotoError):
    """Raised when the upload exceeds ``AVATAR_MAX_BYTES``."""

    def __init__(self, max_bytes: int | None = None) -> None:
        super().__init__(
            reason=(
                f"Photo exceeds maximum allowed size of {max_bytes} bytes"
                if max_bytes
                else "Photo exceeds maximum allowed size"
            )
        )
        self.code = "PHOTO_TOO_LARGE"
        self.max_bytes = max_bytes


class InvalidTimezoneError(ValidationError):
    """Raised when timezone format is invalid."""

    def __init__(self, timezone: str | None = None) -> None:
        super().__init__(
            field="timezone",
            value=timezone,
            reason=(
                f"'{timezone}' is not a valid timezone"
                if timezone
                else "Invalid timezone format"
            ),
        )
        self.code = "INVALID_TIMEZONE"


# ==============================================================================
# PERMISSION EXCEPTIONS
# ==============================================================================


class InsufficientPermissionsError(UserDomainError):
    """Raised when user doesn't have required permissions."""

    def __init__(
        self, action: str | None = None, required_role: str | None = None
    ) -> None:
        if action:
            message = f"Insufficient permissions for action: {action}"
        elif required_role:
            message = f"This action requires role: {required_role}"
        else:
            message = "Insufficient permissions to perform this action"
        super().__init__(message, "INSUFFICIENT_PERMISSIONS")
        self.action = action
        self.required_role = required_role


# ==============================================================================
# STATUS EXCEPTIONS
# ==============================================================================


class InvalidUserStatusError(UserDomainError):
    """Raised when user status prevents the requested operation."""

    def __init__(
        self, current_status: str | None = None, required_status: str | None = None
    ) -> None:
        if current_status and required_status:
            message = f"Operation requires status {required_status}, but user has status {current_status}"
        elif current_status:
            message = f"Operation not allowed for users with status: {current_status}"
        else:
            message = "User status prevents this operation"
        super().__init__(message, "INVALID_STATUS")
        self.current_status = current_status
        self.required_status = required_status
