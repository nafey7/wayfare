"""Base schema classes for Pydantic models across the application."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Base model with strict validation - no extra fields allowed.

    This should be the default for all API request/response models
    to catch typos and ensure API contract compliance.
    """

    model_config = ConfigDict(
        extra="forbid",  # No extra fields allowed
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        validate_assignment=True,  # Validate on field assignment
        use_enum_values=True,  # Use enum values in serialization
        populate_by_name=True,  # Accept both field name and alias
    )


class FlexibleModel(BaseModel):
    """Base model that allows extra fields.

    Use this for:
    - External webhook payloads
    - Third-party API responses
    - Backwards compatibility scenarios
    """

    model_config = ConfigDict(
        extra="allow",  # Accept extra fields
        populate_by_name=True,  # Accept both field name and alias
    )


class IgnoreExtraModel(BaseModel):
    """Base model that silently ignores extra fields.

    Use this for:
    - Database models where schema might have extra columns
    - Legacy integrations
    """

    model_config = ConfigDict(extra="ignore")  # Silently ignore extra fields
