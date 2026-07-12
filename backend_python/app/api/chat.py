"""Minimal chat API for AI-powered flight booking"""

import logging
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.chat_sse import SSE_HEADERS, SSEEventType, format_sse_event
from app.core.config import settings
from app.core.public_guest_session_header import parse_guest_session_id_header
from app.database.connection import get_connection
from app.domains.auth.dependencies import require_authenticated
from app.domains.chat import chat_service
from app.domains.chat.repository import (
    create_conversation as create_conv_repo,
)
from app.domains.chat.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ClaimChatRequest,
    ClaimChatResponse,
    ClaimOutcomeStatus,
    ConversationListResponse,
    ConversationMeta,
    CreateConversationRequest,
    RenameConversationRequest,
)
from app.domains.user.schemas import UserPublic
from app.shared.chat_lock import ChatLockError, get_chat_lock

# Rich message types that carry extra_data in history responses.
_RICH_MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        "flight_search_results",
        "multicity_flight_search_results",
        "flight_date_range_results",
        "hotel_search_results",
        "itinerary_results",
    }
)

# Keys kept from itinerary action_data (strip large arrays like structured_itinerary, flights, hotels).
_ITINERARY_HISTORY_KEYS: frozenset[str] = frozenset(
    {
        "saved_itinerary_id",
        "origin",
        "destination",
        "user_destination",
        "departure_date",
        "return_date",
        "adults",
        "children",
        "infants",
        "trip_type",
        "origin_location",
        "destination_location",
    }
)


def _infer_message_type(action_data: Any) -> str | None:
    """Infer message type from action_data for legacy messages where action field is None.

    Order matters: check flight/hotel signals before itinerary, because chain
    auto-save (see chat service) can leak ``saved_itinerary_id`` into the
    ``action_data`` of a chained flight/hotel result. ``structured_itinerary``
    is the only key reliably unique to itinerary results.
    """
    if not isinstance(action_data, dict):
        return None
    if "multicity_legs" in action_data:
        return "multicity_flight_search_results"
    if "dates" in action_data and "searched_from" in action_data:
        return "flight_date_range_results"
    sp = action_data.get("search_params", {})
    if isinstance(sp, dict):
        if "check_in_date" in sp or "checkout" in sp:
            return "hotel_search_results"
        if "origin" in sp or "departure_date" in sp:
            return "flight_search_results"
    if "structured_itinerary" in action_data:
        return "itinerary_results"
    return None


def _strip_flights_from_items(items: Any) -> list[dict[str, Any]] | None:
    """Drop the ``flights`` field from each item in a list of dicts.

    Used to slim multicity-leg and date-range payloads for history responses:
    legacy persisted ``action_data`` still embeds per-leg / per-date flight
    arrays (each ~50-150 items) which we never re-render from history.
    Returns ``None`` if ``items`` is not a list.
    """
    if not isinstance(items, list):
        return None
    trimmed: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            trimmed.append({k: v for k, v in item.items() if k != "flights"})
        else:
            # Preserve non-dict entries verbatim (shouldn't happen, but be safe).
            trimmed.append(item)
    return trimmed


def _build_extra_data_for_history(
    msg_type: str | None, action_data: Any
) -> dict[str, Any] | None:
    """Return a trimmed extra_data dict for history responses.

    - Flight/hotel single-search: action_data is already ``result["data"]``
      (search_params + summary) — return as-is.
    - Multicity: legacy persisted payload includes ``multicity_legs`` with
      per-leg ``flights`` arrays. Strip the flights to keep history payloads
      bounded; the frontend re-runs the search to populate results.
    - Date-range: same treatment for the ``dates`` array.
    - Itinerary: keep only the minimal trip-meta fields needed for navigation.
    - Other types: return None.
    """
    if not isinstance(action_data, dict) or not msg_type:
        return None
    if msg_type not in _RICH_MESSAGE_TYPES:
        return None
    if msg_type == "itinerary_results":
        return {k: v for k, v in action_data.items() if k in _ITINERARY_HISTORY_KEYS}

    trimmed = dict(action_data)
    if msg_type == "multicity_flight_search_results":
        legs = _strip_flights_from_items(trimmed.get("multicity_legs"))
        if legs is not None:
            trimmed["multicity_legs"] = legs
    elif msg_type == "flight_date_range_results":
        dates = _strip_flights_from_items(trimmed.get("dates"))
        if dates is not None:
            trimmed["dates"] = dates
    return trimmed


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Feedback models
class FeedbackType(StrEnum):
    """Type of feedback."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class ChatFeedbackRequest(BaseModel):
    """Request to submit chat feedback."""

    message_id: str = Field(..., description="Message ID from chat response")
    chat_id: str | None = Field(None, description="Chat conversation ID (fallback)")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    comment: str | None = Field(None, description="Optional user comment")


class ChatFeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    success: bool
    message: str


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest, user: UserPublic = Depends(require_authenticated)
) -> ChatResponse:
    """Send message to AI chat - handles all intents"""
    logger.info(f"💬 [Chat] POST /chat/message called by user: {user.email}")
    logger.info(f"💬 [Chat] Message: {request.message}")
    logger.info(f"💬 [Chat] Chat ID: {request.chat_id}")

    # Get chat_id for locking. ChatGPT-style UX: when the client omits chat_id,
    # always create a *new* conversation. The frontend sends chat_id when the
    # user is continuing an existing conversation, and sends null when they've
    # clicked "New chat" (or it's their first-ever message).
    if request.chat_id is not None:
        chat_id = str(request.chat_id)
    else:
        new_conv = await create_conv_repo(user.id)
        chat_id = new_conv["chat_id"]

    # Acquire lock for this chat_id to prevent race conditions
    chat_lock = get_chat_lock()

    try:
        async with chat_lock.acquire(chat_id):
            response = await chat_service.process_message(
                message=request.message, user=user, chat_id=chat_id
            )
            logger.info(
                f"💬 [Chat] Response generated successfully for user: {user.email}"
            )
            return response
    except ChatLockError as e:
        logger.warning(
            f"💬 [Chat] Request rejected - another request in progress for chat_id={chat_id}: {e}"
        )
        raise HTTPException(
            status_code=429,
            detail="Another request is already processing for this conversation. Please wait for the previous request to complete.",
        ) from e
    except Exception as e:
        logger.error(
            f"💬 [Chat] Error processing message for user {user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Claim guest chat thread
# ---------------------------------------------------------------------------

_CLAIM_STATUS_HTTP: dict[ClaimOutcomeStatus, int] = {
    ClaimOutcomeStatus.CLAIMED: 200,
    ClaimOutcomeStatus.ALREADY_CLAIMED: 200,
    ClaimOutcomeStatus.NOTHING_TO_CLAIM: 200,
    ClaimOutcomeStatus.REJECTED_FINGERPRINT_MISMATCH: 403,
    ClaimOutcomeStatus.REJECTED_OWNED_BY_OTHER_USER: 403,
    ClaimOutcomeStatus.REJECTED_TOO_OLD: 409,
    ClaimOutcomeStatus.REJECTED_TOO_LARGE: 409,
}

# Fail loudly at import time if a new ClaimOutcomeStatus is added without an
# HTTP mapping, rather than silently defaulting to 200 at request time.
_missing_claim_status = set(ClaimOutcomeStatus) - _CLAIM_STATUS_HTTP.keys()
if _missing_claim_status:
    raise RuntimeError(
        f"_CLAIM_STATUS_HTTP missing entries for: {sorted(s.value for s in _missing_claim_status)}"
    )


@router.post("/claim", response_model=ClaimChatResponse)
async def claim_guest_chat(
    body: ClaimChatRequest,
    x_public_chat_session: Annotated[
        str | None, Header(alias="X-Public-Chat-Session")
    ] = None,
    user: UserPublic = Depends(require_authenticated),
) -> ClaimChatResponse:
    """Re-own a guest chat thread for the authenticated user.

    Requires the same ``X-Public-Chat-Session`` UUID the guest used when
    posting messages. Idempotent; safe to call twice.
    """
    fingerprint = parse_guest_session_id_header(x_public_chat_session)
    if body.chat_id is None:
        # v1: claim by chat_id only; no fingerprint-only path.
        return ClaimChatResponse(
            status=ClaimOutcomeStatus.NOTHING_TO_CLAIM,
            chat_id=None,
            message_count=0,
        )

    response = await chat_service.claim_guest_thread(
        user_id=user.id,
        fingerprint=fingerprint,
        chat_id=str(body.chat_id),
        max_age_minutes=body.max_age_minutes,
    )
    http_status = _CLAIM_STATUS_HTTP[response.status]
    if http_status >= 400:
        raise HTTPException(status_code=http_status, detail=response.status.value)
    return response


# Mirrors /chat/message's 429 detail verbatim so the FE's fallback logic
# can branch on the same string regardless of which endpoint it hit.
_LOCK_BUSY_DETAIL = (
    "Another request is already processing for this conversation. "
    "Please wait for the previous request to complete."
)


@router.post("/message/stream")
async def chat_message_stream(
    request: ChatRequest,
    user: UserPublic = Depends(require_authenticated),
) -> StreamingResponse:
    """SSE sibling of POST /chat/message — issue #1117.

    Establishes the streaming transport (SSE framing, proxy-safe headers,
    per-chat lock semantics shared with POST /chat/message) and relays
    typed ``ChatStreamEvent`` objects from
    :meth:`ChatService.process_message_streaming` onto the wire. The
    streaming method drives ``graph.astream(...)`` under the hood so
    progress events fire as the supervisor graph runs instead of after a
    single ~30 s blocking call.

    Gated by ``settings.CHAT_STREAMING_ENABLED``. With the flag off the
    route returns 404 so the frontend's EventSource error handler trips
    its fallback to POST /chat/message.
    """
    if not settings.CHAT_STREAMING_ENABLED:
        # Mimic FastAPI's default "not found" so the FE EventSource error
        # handler triggers the fallback to non-streaming POST /chat/message.
        raise HTTPException(status_code=404, detail="Not Found")

    logger.info(
        f"💬 [Chat/Stream] POST /chat/message/stream called by user: {user.email}"
    )

    # Resolve chat_id with the same "null means new conversation" semantics
    # as the non-streaming endpoint, so a fresh thread doesn't need a prior
    # POST /chat/conversations round-trip.
    if request.chat_id is not None:
        chat_id = str(request.chat_id)
    else:
        new_conv = await create_conv_repo(user.id)
        chat_id = new_conv["chat_id"]

    chat_lock = get_chat_lock()

    # Acquire the lock BEFORE returning the StreamingResponse so a 429
    # surfaces as a real HTTP status to the client (not as an error event
    # on a 200 stream). ``AsyncExitStack.pop_all()`` then transfers
    # ownership of the entered context manager to the generator below,
    # which releases it when the stream finishes or errors. Without
    # ``pop_all``, the ``async with`` here would release the lock as soon
    # as we return the response — defeating the point.
    #
    # Trade-offs documented for the next reader:
    # 1. **Orphan-conversation on 429**: when ``chat_id`` was None we
    #    already called ``create_conv_repo`` above. If lock acquisition
    #    then raises 429, the new conversation is empty / orphaned. In
    #    practice this is *essentially impossible* because the lock key
    #    is the freshly-minted UUID we just created — nothing else has
    #    held that key, and the per-chat lock has a 5-min TTL that
    #    expires anything stale. The 429 surface only triggers in the
    #    ``chat_id`` is provided branch above (existing conversation
    #    with a parallel request), where no new conversation has been
    #    created. Matches POST /chat/message's behavior intentionally.
    # 2. **Lock leak if StreamingResponse never iterated**: Starlette's
    #    contract guarantees the response body generator IS iterated
    #    (even on client disconnect, it consumes the body to closure),
    #    so the ``async with lock_stack`` finally block in
    #    ``event_generator`` always runs. The lock's 5-min TTL is the
    #    absolute backstop if the runtime crashes between
    #    ``pop_all()`` and the generator's first iteration.
    async with AsyncExitStack() as stack:
        try:
            await stack.enter_async_context(chat_lock.acquire(chat_id))
        except ChatLockError as e:
            logger.warning(
                f"💬 [Chat/Stream] Request rejected - lock busy for chat_id={chat_id}: {e}"
            )
            raise HTTPException(status_code=429, detail=_LOCK_BUSY_DETAIL) from e
        # Lock now held; donate the stack to the generator. The outer
        # ``async with`` becomes a no-op exit.
        lock_stack = stack.pop_all()

    async def event_generator() -> Any:
        # The generator owns the lock from this point on. ChatService
        # catches all internal failures and yields its own ``error``
        # event; the outer try/except below is a safety net for the
        # unlikely case where something escapes the streaming method
        # anyway (e.g. import failure on the supervisor module).
        async with lock_stack:
            try:
                async for stream_event in chat_service.process_message_streaming(
                    message=request.message,
                    user=user,
                    chat_id=chat_id,
                ):
                    yield format_sse_event(
                        event_id=str(uuid4()),
                        event_type=stream_event.event,
                        data=stream_event.data,
                    )
            except Exception as exc:  # noqa: BLE001 — must catch everything for SSE error envelope
                logger.error(
                    f"💬 [Chat/Stream] Error processing message for user {user.email}: {exc}",
                    exc_info=True,
                )
                # Don't leak the raw exception message — match the
                # non-streaming endpoint's generic 500 detail surface.
                yield format_sse_event(
                    event_id=str(uuid4()),
                    event_type=SSEEventType.ERROR,
                    data={
                        "message": "An error occurred while processing your message.",
                        "error_class": type(exc).__name__,
                    },
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def _models_to_chat_messages(messages_models: list[Any]) -> list[Any]:
    from app.domains.chat.schemas import ChatMessage

    chat_messages = []
    for msg in messages_models:
        message_text = ""
        if isinstance(msg.content, dict):
            message_text = msg.content.get("text", "")
        elif msg.content:
            message_text = str(msg.content)
        msg_type = msg.action or _infer_message_type(msg.action_data)
        extra_data = _build_extra_data_for_history(msg_type, msg.action_data)
        chat_messages.append(
            ChatMessage(
                sender=msg.from_ or "UNKNOWN",
                message=message_text,
                timestamp=msg.created_at.isoformat() if msg.created_at else None,
                intent_name=msg.intent_name,
                type=msg_type,
                extra_data=extra_data,
            )
        )
    return chat_messages


@router.get("/latest", response_model=ChatHistoryResponse)
async def get_latest_chat_messages(
    limit: int = Query(50, ge=1, le=100),
    user: UserPublic = Depends(require_authenticated),
) -> ChatHistoryResponse:
    """Get messages from user's latest conversation"""
    try:
        from app.domains.chat.repository import (
            get_chat_messages,
            get_or_create_chat_conversation,
        )

        conversation_id = await get_or_create_chat_conversation(user.id)
        messages_models = await get_chat_messages(conversation_id, limit)
        chat_messages = _models_to_chat_messages(messages_models)
        return ChatHistoryResponse(
            chat_id=conversation_id, messages=chat_messages, count=len(chat_messages)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/latest")
async def clear_latest_chat_messages(
    user: UserPublic = Depends(require_authenticated),
) -> dict[str, Any]:
    """Clear messages from user's latest conversation"""
    try:
        from app.domains.chat.repository import clear_chat_messages as clear_messages
        from app.domains.chat.repository import get_or_create_chat_conversation

        conversation_id = await get_or_create_chat_conversation(user.id)

        deleted_count = await clear_messages(conversation_id)

        return {
            "message": f"Latest chat messages cleared successfully ({deleted_count} messages)",
            "chat_id": conversation_id,
            "deleted_count": deleted_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Conversation routes (must be registered BEFORE `/{chat_id}` so they aren't
# captured by the parametric route).
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: UserPublic = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ConversationListResponse:
    """List user's conversations for the sidebar."""
    from app.domains.chat.repository import list_user_conversations

    conversations_raw, total = await list_user_conversations(
        user.id, limit=limit, offset=offset
    )
    items = [
        ConversationMeta(
            chat_id=c["chat_id"],
            name=c.get("name", "New conversation"),
            message_count=c.get("message_count", 0),
            last_message_at=(
                c["last_message_at"].isoformat() if c.get("last_message_at") else None
            ),
            last_message_preview=c.get("last_message_preview", ""),
            created_at=(c["created_at"].isoformat() if c.get("created_at") else None),
        )
        for c in conversations_raw
    ]
    return ConversationListResponse(
        conversations=items,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/conversations", response_model=ConversationMeta, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    user: UserPublic = Depends(require_authenticated),
) -> ConversationMeta:
    """Create a new conversation."""
    from app.domains.chat.repository import create_conversation as create_conv

    name = request.name or "New conversation"
    doc = await create_conv(user.id, name=name)
    return ConversationMeta(
        chat_id=doc["chat_id"],
        name=doc["name"],
        message_count=0,
        last_message_at=(
            doc["last_message_at"].isoformat() if doc.get("last_message_at") else None
        ),
        last_message_preview="",
        created_at=(doc["created_at"].isoformat() if doc.get("created_at") else None),
    )


@router.put("/conversations/{chat_id}")
async def rename_conversation(
    chat_id: str,
    request: RenameConversationRequest,
    user: UserPublic = Depends(require_authenticated),
) -> dict[str, str]:
    """Rename a conversation."""
    from app.domains.chat.repository import rename_conversation as rename_conv

    updated = await rename_conv(chat_id, user.id, request.name)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"chat_id": chat_id, "name": request.name}


@router.delete("/conversations/{chat_id}")
async def delete_conversation(
    chat_id: str,
    user: UserPublic = Depends(require_authenticated),
) -> dict[str, str]:
    """Soft-delete a conversation."""
    from app.domains.chat.repository import soft_delete_conversation

    deleted = await soft_delete_conversation(chat_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"chat_id": chat_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# Parametric `/{chat_id}` routes — MUST come after `/conversations*` above to
# avoid shadowing them.
# ---------------------------------------------------------------------------


@router.get("/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_messages_by_id(
    chat_id: str,
    limit: int = Query(50, ge=1, le=100),
    user: UserPublic = Depends(require_authenticated),
) -> ChatHistoryResponse:
    """Get messages from a specific conversation (owner only)."""
    try:
        from app.domains.chat.repository import (
            get_chat_messages,
            user_owns_conversation,
        )

        if not await user_owns_conversation(chat_id, user.id):
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages_models = await get_chat_messages(chat_id, limit)
        chat_messages = _models_to_chat_messages(messages_models)
        return ChatHistoryResponse(
            chat_id=chat_id, messages=chat_messages, count=len(chat_messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{chat_id}")
async def clear_chat_messages_by_id(
    chat_id: str, user: UserPublic = Depends(require_authenticated)
) -> dict[str, Any]:
    """Clear chat messages for a specific conversation ID (owner only)."""
    try:
        from app.domains.chat.repository import clear_chat_messages as clear_messages
        from app.domains.chat.repository import user_owns_conversation

        if not await user_owns_conversation(chat_id, user.id):
            raise HTTPException(status_code=404, detail="Conversation not found")

        deleted_count = await clear_messages(chat_id)

        return {
            "message": f"Chat messages cleared successfully ({deleted_count} messages)",
            "chat_id": chat_id,
            "deleted_count": deleted_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def submit_chat_feedback(
    feedback: ChatFeedbackRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> ChatFeedbackResponse:
    """Submit thumbs up/down feedback for an AI response.

    Feedback is stored in MongoDB and sent to Langfuse for analysis.
    """
    if not settings.VOYA_FEATURE_FLAG_CHAT_FEEDBACK:
        raise HTTPException(
            status_code=403,
            detail="Chat feedback feature is not enabled",
        )

    try:
        db = get_connection().get_database()
        collection = db.chat_feedback

        # Store feedback in MongoDB
        feedback_doc = {
            "user_id": str(current_user.id),
            "message_id": feedback.message_id,
            "chat_id": feedback.chat_id,
            "feedback_type": feedback.feedback_type.value,
            "comment": feedback.comment,
            "created_at": datetime.now(UTC),
        }

        await collection.insert_one(feedback_doc)

        logger.info(
            f"Chat feedback received: {feedback.feedback_type.value} "
            f"for message {feedback.message_id}"
        )

        # Submit to Langfuse for LLM observability
        from app.ai.graph.tracing import submit_feedback_to_langfuse

        langfuse_submitted = submit_feedback_to_langfuse(
            message_id=feedback.message_id,
            session_id=feedback.chat_id,
            feedback_type=feedback.feedback_type.value,
            comment=feedback.comment,
        )

        if langfuse_submitted:
            logger.debug(
                f"Feedback submitted to Langfuse for message {feedback.message_id}"
            )

        return ChatFeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
        )

    except Exception as e:
        logger.error(f"Failed to store chat feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback",
        ) from e
