"""Chat model for MongoDB 'chats_python' collection."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.database.types import PyObjectId


class ChatsPythonModel(BaseModel):
    """Chat model for MongoDB 'chats_python' collection."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # MongoDB _id field
    id: PyObjectId | None = Field(default=None, alias="_id")

    # Chat fields
    user_id: PyObjectId | None = None
    session_id: PyObjectId | None = None
    chat_id: str | None = None
    fingerprint: str | None = None

    # Content fields
    content: dict[str, Any] | None = None
    action: str | None = None
    action_data: dict[str, Any] | None = None

    # Message metadata
    from_: str | None = Field(
        default=None, alias="from"
    )  # AI / USER / SYSTEM - keep alias for reserved word
    intent_name: str | None = None  # welcome / plan_a_trip / fast_finds

    # Status
    status: int = 10  # 10=active, 0=deleted

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
