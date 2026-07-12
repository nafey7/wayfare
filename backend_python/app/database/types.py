"""MongoDB type definitions and validators for Pydantic models."""

from typing import Annotated, Any, Optional

from bson import ObjectId
from pydantic import BeforeValidator, PlainSerializer


def validate_object_id(v: Any) -> ObjectId:
    """Validate and convert to ObjectId."""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError(f"Invalid ObjectId: {v}")


# PyObjectId type for Pydantic v2
PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(str, return_type=str),
]

# Type aliases for common patterns to help IDEs
PyObjectIdList = list[PyObjectId]
OptionalPyObjectIdList = Optional[list[PyObjectId]]
