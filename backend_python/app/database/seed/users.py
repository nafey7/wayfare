"""Test user data definitions."""

from app.domains.user.enums import UserRole, UserStatus

TEST_USERS = [
    {
        "email": "testuser@example.com",
        "password": "Test123!",  # pragma: allowlist secret
        "first_name": "Test",
        "last_name": "User",
        "role": UserRole.USER.value,
        "status": UserStatus.ACTIVE.value,
    },
    {
        "email": "testadmin@example.com",
        "password": "Admin123!",  # pragma: allowlist secret
        "first_name": "Test",
        "last_name": "Admin",
        "role": UserRole.ADMIN.value,
        "status": UserStatus.ACTIVE.value,
    },
    {
        "email": "flightbooker@example.com",
        "password": "Flight123!",  # pragma: allowlist secret
        "first_name": "Flight",
        "last_name": "Booker",
        "role": UserRole.USER.value,
        "status": UserStatus.ACTIVE.value,
    },
    {
        "email": "hotelbooker@example.com",
        "password": "Hotel123!",  # pragma: allowlist secret
        "first_name": "Hotel",
        "last_name": "Booker",
        "role": UserRole.USER.value,
        "status": UserStatus.ACTIVE.value,
    },
]
