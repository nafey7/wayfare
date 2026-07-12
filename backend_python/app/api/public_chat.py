"""Public (guest) chat API — no JWT; IP rate limits and guest session header."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.feature_flags import public_chat_enabled
from app.core.privacy_logging import log_bucket
from app.core.public_chat_rate_limit import (
    check_public_chat_rate_limit,
    check_public_chat_session_message_limit,
)
from app.core.public_guest_session_header import parse_guest_session_id_header
from app.core.public_places_rate_limit import get_trusted_request_client_ip
from app.domains.chat.repository import guest_session_may_use_chat_id
from app.domains.chat.schemas import ChatRequest, ChatResponse, PublicChatErrorBody
from app.shared.chat_lock import ChatLockError, get_chat_lock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/chat", tags=["public-chat"])


async def _dispatch_public_message(
    message: str,
    guest_session_id: str,
    chat_id: str,
    client_ip: str,
) -> ChatResponse:
    """Delegate to ChatService; separated for unit tests (patch without importing service graph)."""
    from app.domains.chat.service import chat_service

    return await chat_service.process_public_message(
        message=message,
        guest_session_id=guest_session_id,
        chat_id=chat_id,
        client_ip=client_ip,
    )


@router.post(
    "/message",
    response_model=ChatResponse,
    responses={
        403: {
            "description": "Public chat disabled via feature flag.",
            "model": PublicChatErrorBody,
        },
        429: {
            "description": (
                "Too many requests: IP rate limit, per-session message cap, or another message "
                "is in flight for this chat. See `code` (public_rate_limit, public_session_limit, "
                "vs chat_request_in_progress)."
            ),
            "model": PublicChatErrorBody,
        },
        500: {
            "description": "Unexpected server error while processing the message.",
            "model": PublicChatErrorBody,
        },
    },
    summary="Send a guest chat message",
    description="Unauthenticated chat for the public landing page. Requires X-Public-Chat-Session (UUID).",
)
async def public_chat_message(
    request: Request,
    body: ChatRequest,
    x_public_chat_session: Annotated[
        str | None, Header(alias="X-Public-Chat-Session")
    ] = None,
) -> ChatResponse | JSONResponse:
    """Process a guest message when the public-chat feature flag is enabled."""
    if not public_chat_enabled():
        logger.debug("public_chat.request_rejected feature_disabled")
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Public chat is disabled.",
                "code": "public_chat_disabled",
            },
        )

    # Validate session before counting toward IP rate limit
    session_id = parse_guest_session_id_header(x_public_chat_session)

    if not check_public_chat_rate_limit(request):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Guest chat rate limit exceeded. Sign up to continue chatting.",
                "code": "public_rate_limit",
            },
        )

    if not check_public_chat_session_message_limit(session_id):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Guest chat message limit for this session reached. Sign up to continue chatting.",
                "code": "public_session_limit",
            },
        )

    if body.chat_id is None:
        chat_id = str(uuid.uuid4())
    else:
        chat_id = str(body.chat_id)
        if not await guest_session_may_use_chat_id(chat_id, session_id):
            raise HTTPException(
                status_code=403,
                detail="This conversation does not belong to your guest session.",
            )
    client_ip = get_trusted_request_client_ip(request)
    chat_lock = get_chat_lock()
    try:
        async with chat_lock.acquire(chat_id):
            response = await _dispatch_public_message(
                message=body.message,
                guest_session_id=session_id,
                chat_id=chat_id,
                client_ip=client_ip,
            )
            logger.info(
                "public_chat.message_completed session_bucket=%s chat_bucket=%s",
                log_bucket(session_id),
                log_bucket(chat_id),
            )
            return response
    except ChatLockError:
        logger.warning(
            "public_chat.request_rejected chat_lock_held chat_bucket=%s",
            log_bucket(chat_id),
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Another request is already processing for this conversation. "
                "Please wait for the previous request to complete.",
                "code": "chat_request_in_progress",
            },
        )
    except Exception:
        logger.exception("public_chat.unhandled_error")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected error occurred while processing your message.",
                "code": "public_chat_error",
            },
        )
