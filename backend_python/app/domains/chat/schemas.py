"""Minimal chat schemas"""

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.security_constants import MAX_CHAT_MESSAGE_LENGTH


class ChatRequest(BaseModel):
    """Simple chat request - requires authentication"""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description=(
            f"User's message (1-{MAX_CHAT_MESSAGE_LENGTH} characters after trim)"
        ),
    )
    chat_id: UUID | None = Field(
        None,
        description="Optional existing chat ID (UUID string)",
    )


class PublicChatErrorBody(BaseModel):
    """JSON body for ``POST /public/chat/message`` when HTTP status is not 200."""

    detail: str = Field(..., description="Human-readable error message")
    code: str = Field(
        ...,
        description=(
            "Stable machine code: public_chat_disabled, public_rate_limit, "
            "public_session_limit, chat_request_in_progress, public_chat_error"
        ),
    )


class ChatResponse(BaseModel):
    """AI chat response - flexible structure"""

    message: str = Field(..., description="AI response text")
    message_id: str | None = Field(
        None, description="Message ID for feedback correlation"
    )
    chat_id: str = Field(..., description="Chat conversation ID")
    intent_name: str = Field(..., description="Detected intent name")
    confidence: float = Field(..., description="Intent confidence")
    type: str = Field(..., description="Response type")
    data: dict[str, Any] | None = Field(
        None, description="Additional data based on type"
    )
    places_session_token: str | None = Field(
        None,
        description="Short-lived JWT for guest Places images (public chat itinerary only)",
    )


class ChatMessage(BaseModel):
    """Single message in chat history"""

    sender: str = Field(..., description="Who sent it (USER/BOT/SYSTEM)")
    message: str = Field(..., description="Message text")
    timestamp: str | None = Field(None, description="ISO timestamp")
    intent_name: str | None = Field(None, description="Detected intent name")
    type: str | None = Field(None, description="Message type")
    extra_data: dict[str, Any] | None = Field(
        None, description="Rich payload for flight/hotel/itinerary messages"
    )


class ChatHistoryResponse(BaseModel):
    """Chat history response"""

    chat_id: str = Field(..., description="Chat conversation ID")
    messages: list[ChatMessage] = Field(..., description="List of messages")
    count: int = Field(..., description="Number of messages")


# --- Multi-conversation schemas ---


class ConversationMeta(BaseModel):
    """Metadata for a single conversation (sidebar display)."""

    chat_id: str = Field(..., description="Conversation UUID")
    name: str = Field(..., description="Conversation display name")
    message_count: int = Field(0, description="Number of messages")
    last_message_at: str | None = Field(
        None, description="ISO timestamp of last message"
    )
    last_message_preview: str = Field("", description="First 100 chars of last message")
    created_at: str | None = Field(None, description="ISO timestamp of creation")


class ConversationListResponse(BaseModel):
    """Response for GET /conversations."""

    conversations: list[ConversationMeta]
    total: int = Field(..., description="Total conversation count")
    has_more: bool = Field(False, description="Whether more pages exist")


class CreateConversationRequest(BaseModel):
    """Request for POST /conversations."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        None,
        max_length=50,
        description="Optional conversation name (auto-named on first message if omitted)",
    )


# --- Guest-chat claim schemas ---


class ClaimOutcomeStatus(StrEnum):
    """Result status for ``POST /api/chat/claim``."""

    CLAIMED = "claimed"
    ALREADY_CLAIMED = "already_claimed"
    NOTHING_TO_CLAIM = "nothing_to_claim"
    REJECTED_FINGERPRINT_MISMATCH = "rejected_fingerprint_mismatch"
    REJECTED_TOO_OLD = "rejected_too_old"
    REJECTED_TOO_LARGE = "rejected_too_large"
    REJECTED_OWNED_BY_OTHER_USER = "rejected_owned_by_other_user"


# Server-side hard cap (clamped from request).
CLAIM_MAX_AGE_MINUTES_HARD_CAP = 7 * 24 * 60  # 7 days
CLAIM_DEFAULT_MAX_AGE_MINUTES = 24 * 60  # 24 hours
CLAIM_MESSAGE_CAP = 200


class ClaimChatRequest(BaseModel):
    """Body for ``POST /api/chat/claim``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    chat_id: UUID | None = Field(
        None,
        description="Guest chat thread id (from voya_public_chat_id in localStorage).",
    )
    max_age_minutes: int = Field(
        CLAIM_DEFAULT_MAX_AGE_MINUTES,
        ge=1,
        le=CLAIM_MAX_AGE_MINUTES_HARD_CAP,
        description=(
            "Only claim threads whose newest message is within this window. "
            f"Server-clamped to <= {CLAIM_MAX_AGE_MINUTES_HARD_CAP} minutes."
        ),
    )


class ClaimChatResponse(BaseModel):
    """Response for ``POST /api/chat/claim``."""

    status: ClaimOutcomeStatus = Field(..., description="Claim outcome status")
    chat_id: str | None = Field(None, description="Claimed chat id, when applicable")
    message_count: int = Field(0, description="Number of messages now owned by user")


class RenameConversationRequest(BaseModel):
    """Request for PUT /conversations/{chat_id}."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="New conversation name",
    )
