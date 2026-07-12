"""Admin domain package.

This package contains all admin-related business logic, models, and services.
"""

from .service import AdminService, get_admin_service

__all__ = [
    "AdminService",
    "get_admin_service",
]
