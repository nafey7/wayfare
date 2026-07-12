"""Simple chat service with AI integration for flight bookings"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .schemas import ClaimChatResponse

from app.core.logging import get_backend_logger
from app.domains.saved_itinerary import (
    SavedItineraryCreate,
    upsert_saved_itinerary_for_chat,
)
from app.domains.user.schemas import UserPublic

from . import repository
from .enums import MessageSender
from .schemas import ChatResponse


@dataclass(frozen=True)
class _SupervisorTurnContext:
    """Per-turn identifiers + handles for the supervisor pipeline.

    Bundles auth-resolved values that the pre-stream + post-stream phases
    both need so each takes a single context argument instead of
    re-deriving them. Created via
    :meth:`ChatService._resolve_supervisor_context` after the user-vs-guest
    XOR check.

    ``invoke_user_id`` is the LangGraph/Langfuse identifier (Mongo id for
    auth, ``guest:<uuid>`` opaque string for public chat). ``persist_uid``
    is the Mongo user id for repo writes — ``None`` for guest, so guest
    bot messages are stored with ``guest_fingerprint`` instead.
    """

    message: str
    chat_id: str
    invoke_user_id: str
    user_email: str | None
    user: UserPublic | None
    persist_uid: str | None
    guest_session_id: str | None
    guest_fp: str | None
    client_ip: str | None


@dataclass(frozen=True)
class ChatStreamEvent:
    """Domain-level streaming event yielded during a chat turn.

    The API layer (``app/api/chat.py``) wraps each in the SSE wire format
    (``id:`` + ``event:`` + ``data:``). ``event`` names mirror
    :class:`app.api.chat_sse.SSEEventType` values, so the same set of
    strings flows from domain code through the wire to the FE's typed
    event handler — but ``service.py`` doesn't import the API layer to
    avoid the layering reversal.
    """

    event: str
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Conversation auto-naming prompt
# ---------------------------------------------------------------------------
_CONVERSATION_NAME_PROMPT = (
    "Generate a short, descriptive title (2-5 words) for a travel chat "
    "conversation that starts with this user message.\n\n"
    "Rules:\n"
    "- Focus on the travel topic: destination, activity, or intent.\n"
    "- Use Title Case (e.g. 'Flights to Paris').\n"
    "- NEVER use generic titles like 'New Conversation', 'Chat', 'Greeting', "
    "'Hello', 'Hi', or 'Conversation'.\n"
    "- For trivial greetings ('hi', 'hello', 'thanks'), return 'Travel Assistant'.\n"
    "- Do NOT add quotes, punctuation, or any extra text.\n\n"
    "Examples:\n"
    "- 'Find flights to Paris' → Flights to Paris\n"
    "- 'Plan a trip to Tokyo' → Tokyo Trip Planning\n"
    "- 'Book a hotel in Bali' → Bali Hotel Booking\n"
    "- 'hi' → Travel Assistant\n"
    "- 'hello there' → Travel Assistant\n"
    "- 'cheapest flight from London to NYC' → London to NYC Flights\n\n"
    "User message: {message}\n\n"
    "Title:"
)

# Titles the LLM sometimes returns that are too generic — reject and retry/fallback.
# When a returned title falls in this set we use the SHALLOW_PLACEHOLDER instead and
# allow the namer to re-run on the next message (see ``_should_run_auto_name``). The
# chip-command entries (search flights / find hotels / plan a trip) catch the case
# where the user clicked a suggestion chip first and the LLM returned the chip text
# verbatim — without re-naming, every chip-started conversation would get the same
# title. Keep entries lowercase; the comparison is case-insensitive.
_SHALLOW_PLACEHOLDER = "Travel Assistant"
_GENERIC_TITLE_BLOCKLIST: frozenset[str] = frozenset(
    {
        "new conversation",
        "chat",
        "conversation",
        "greeting",
        "hello",
        "hi",
        "untitled",
        # Chip-command titles — generated when the user clicked a suggestion
        # before typing anything specific. Re-naming on the next message
        # produces a meaningful trip-specific title.
        "search flights",
        "find hotels",
        "plan a trip",
        "travel assistant",
    }
)

# ---------------------------------------------------------------------------
# Anti-spam dedup cache
# ---------------------------------------------------------------------------
# chat_id -> (last_message, timestamp). Short TTL window drops identical
# resends while the previous request is still in flight. Per-process;
# acceptable for current single-replica deploy. Wrapped in an asyncio.Lock so
# the read/write/cleanup sequence is atomic under concurrent dispatch —
# without it, the cleanup loop could race with concurrent inserts.
_DEDUPE_WINDOW_SECONDS = 5.0
_DEDUPE_CLEANUP_THRESHOLD = 1000
_DEDUPE_CLEANUP_TTL_SECONDS = 60.0
_recent_messages: dict[str, tuple[str, float]] = {}
_recent_messages_lock = asyncio.Lock()


async def _is_duplicate_resend(chat_id: str, message: str) -> bool:
    """Return True if the same message was sent for this chat within the dedupe window."""
    async with _recent_messages_lock:
        now = time.monotonic()
        last = _recent_messages.get(chat_id)
        if last is not None:
            last_msg, last_ts = last
            if last_msg == message and (now - last_ts) < _DEDUPE_WINDOW_SECONDS:
                return True
        _recent_messages[chat_id] = (message, now)
        # Opportunistic cleanup: drop entries older than the cleanup TTL to
        # bound memory.  Inside the lock, so the snapshot+delete is atomic.
        if len(_recent_messages) > _DEDUPE_CLEANUP_THRESHOLD:
            cutoff = now - _DEDUPE_CLEANUP_TTL_SECONDS
            for cid in list(_recent_messages):
                if _recent_messages[cid][1] < cutoff:
                    del _recent_messages[cid]
        return False


def _payload_contains_backend_places_photo_url(obj: Any) -> bool:
    """True if nested payload includes a backend Places photo proxy URL."""
    marker = "/api/places/photos/"

    def walk(x: Any) -> bool:
        if isinstance(x, str):
            return marker in x
        if isinstance(x, dict):
            return any(walk(v) for v in x.values())
        if isinstance(x, list):
            return any(walk(i) for i in x)
        return False

    return walk(obj)


def _last_itinerary_results_in_chain(
    chain_responses: list[Any],
) -> dict[str, Any] | None:
    """Last ``itinerary_results`` in top-level chain index order.

    Only the top-level ``chain_responses`` array is considered (same order as
    ``sanitized_chain`` for the client). When multiple ``itinerary_results`` nodes
    exist, the one with the greatest index wins.
    """
    last: dict[str, Any] | None = None
    for cr in chain_responses:
        if isinstance(cr, dict) and cr.get("type") == "itinerary_results":
            last = cr
    return last


# Keys stripped from supervisor ``result`` when building ``ChatResponse.data`` (non-itinerary).
_CHAT_EXTRA_DATA_EXCLUDED_KEYS: frozenset[str] = frozenset(
    {
        "message",
        "chat_id",
        "type",
        "intent",
        "agent",
        "confidence",
        "message_id",
        "response_time",
        "signal",
        "done_reason",
        "agent_status",
        "failed_reason",
        "collected_params",
        "cross_agent_data",
        "shared_context",
        "classification_confidence",
        "booking_plan",
        "auto_chain",
        "task_queue",
        "detour_return",
        "previous_agent",
        "remaining_steps",
        "chain_responses",
    }
)

# Same as above plus chain-only metadata keys not sent to the client.
_CHAT_CHAIN_SANITIZE_EXCLUDED_KEYS: frozenset[str] = _CHAT_EXTRA_DATA_EXCLUDED_KEYS | {
    "is_detour",
    "reason",
}

# Keys stripped when persisting intermediate chain responses as ``action_data`` (subset of
# ``_CHAT_EXTRA_DATA_EXCLUDED_KEYS`` — more fields kept for DB context than for wire).
_CHAIN_MSG_ACTION_DATA_EXCLUDED_KEYS: frozenset[str] = frozenset(
    {
        "message",
        "type",
        "message_id",
        "signal",
        "done_reason",
        "agent_status",
        "collected_params",
        "cross_agent_data",
    }
)


class ChatService:
    """Simple chat service focused on AI-powered flight bookings"""

    def __init__(self) -> None:
        """Initialize with AI components"""
        self.logger = get_backend_logger()  # This goes to /ecs/voya-backend

    @staticmethod
    async def _get_conversation_doc(chat_id: str) -> dict[str, Any] | None:
        """Fetch a conversation document by chat_id."""
        from app.database.dependencies import get_database

        db = await get_database()
        return cast(
            "dict[str, Any] | None",
            await db[repository.CONVERSATIONS_COLLECTION].find_one(
                {"chat_id": chat_id}
            ),
        )

    async def _auto_name_conversation(
        self, chat_id: str, user_id: str, first_message: str
    ) -> str | None:
        """Generate a short conversation title from the first user message.

        Uses a cheap/fast LLM (gpt-5.4-nano) to avoid latency.
        Rejects generic titles like 'New Conversation' and falls back to
        'Travel Assistant' so the sidebar never shows the placeholder default.
        Returns the final name, or None on failure.
        """
        from app.ai.graph.llm_factory import create_llm
        from app.ai.graph.supervisor_v2 import _normalize_llm_content

        try:
            llm = create_llm("conversation_namer", temperature=0.3)
            prompt = _CONVERSATION_NAME_PROMPT.format(message=first_message[:200])
            response = await llm.ainvoke(prompt)
            # `response.content` may be a plain string (Chat Completions /
            # Gemini) or a list of content-blocks (OpenAI Responses API on
            # gpt-5.4-nano). Normalize both into one string before cleaning —
            # without this the literal "[{'type':'text','text':'...'}]" ends
            # up as the conversation name.
            raw_text = _normalize_llm_content(response.content)
            # Clean: strip quotes, punctuation, trailing colons/periods, whitespace
            name = raw_text.strip().strip("\"'`").strip(".:-").strip()[:50]
            # Reject generic / chip-command titles — fall back to the shallow
            # placeholder so the namer is allowed to re-run on the next
            # message (see ``_should_run_auto_name``).
            if not name or name.lower() in _GENERIC_TITLE_BLOCKLIST:
                name = _SHALLOW_PLACEHOLDER
            await repository.rename_conversation(chat_id, user_id, name)
            return name
        except Exception as e:
            self.logger.warning(
                "Auto-name conversation failed (chat_id=%s): %s", chat_id, e
            )
        return None

    async def _try_auto_save_itinerary_and_enrich(
        self,
        user_id: str,
        response: dict[str, Any],
        data: dict[str, Any],
        chat_id: str,
    ) -> dict[str, Any]:
        """When response is itinerary_results with structured_itinerary, save and add saved_itinerary_id to data."""
        if response.get("type") != "itinerary_results":
            return data
        metadata = response.get("metadata") or {}
        structured_itinerary = (
            metadata.get("structured_itinerary")
            or response.get("structured_itinerary")
            or {}
        )
        if not isinstance(structured_itinerary, dict):
            self.logger.warning(
                "structured_itinerary in metadata is not a dict (type=%s, chat_id=%s)",
                type(structured_itinerary).__name__,
                chat_id,
            )
            return data
        trip_meta_raw: dict[str, Any] = {}
        for key in repository.ITINERARY_TRIP_META_KEYS:
            val = response.get(key)
            if val is not None:
                trip_meta_raw[key] = val
        trip_meta = trip_meta_raw if trip_meta_raw else None
        try:
            saved = await upsert_saved_itinerary_for_chat(
                user_id,
                chat_id,
                SavedItineraryCreate(
                    structured_itinerary=structured_itinerary,
                    trip_meta=trip_meta,
                ),
            )
            data["saved_itinerary_id"] = saved.id
        except Exception as e:
            self.logger.exception(
                "Auto-save itinerary failed (chat_id=%s): %s",
                chat_id,
                e,
            )
        return data

    def _log_outgoing_payload(
        self,
        *,
        chat_id: str,
        response_type: str,
        bot_response: str,
        extra_data: dict[str, Any] | None,
    ) -> None:
        """Issue #1034 debug log: what does the frontend actually receive?

        Tracks the post-#1034 invariants:
          - ``categories`` should be absent from ``data.data``
          - flat ``flights[]`` / ``hotels[]`` should be at the envelope top level
          - bot message should be a compact summary (LLM never saw the heavy
            payload thanks to the ``content_and_artifact`` split)

        Output is intentionally a single structured line per chat response so
        it's easy to grep in production.
        """
        try:
            data = extra_data or {}
            inner = data.get("data") if isinstance(data, dict) else None

            flights = data.get("flights") if isinstance(data, dict) else None
            hotels = data.get("hotels") if isinstance(data, dict) else None
            multicity_legs = (
                (inner or {}).get("multicity_legs") if isinstance(inner, dict) else None
            )
            dates = (inner or {}).get("dates") if isinstance(inner, dict) else None

            has_inner_categories = bool(
                isinstance(inner, dict) and inner.get("categories")
            )

            payload_size = len(json.dumps(data)) if data else 0
            self.logger.info(
                "chat_service.outgoing_payload chat_id=%s type=%s "
                "msg_len=%d data_bytes=%d "
                "flights=%s hotels=%s multicity_legs=%s date_range_dates=%s "
                "inner_has_categories=%s",
                chat_id,
                response_type,
                len(bot_response or ""),
                payload_size,
                len(flights) if isinstance(flights, list) else None,
                len(hotels) if isinstance(hotels, list) else None,
                len(multicity_legs) if isinstance(multicity_legs, list) else None,
                len(dates) if isinstance(dates, list) else None,
                has_inner_categories,
            )
        except Exception as e:
            # Logging must never break the response — log a one-liner and move on.
            self.logger.warning(
                "chat_service.outgoing_payload_log_failed chat_id=%s err=%s",
                chat_id,
                e,
            )

    @staticmethod
    def _resolve_supervisor_context(
        *,
        message: str,
        chat_id: str,
        user: UserPublic | None,
        guest_session_id: str | None,
        client_ip: str | None,
    ) -> _SupervisorTurnContext:
        """Validate user-XOR-guest and resolve per-turn identifiers.

        Splits the input into the values different layers actually consume:
        ``invoke_user_id`` (LangGraph/Langfuse identifier — opaque string in
        both cases), ``persist_uid`` (Mongo user id, ``None`` for guest), and
        ``guest_fp`` (repo "fingerprint" alias, ``None`` for authenticated).
        """
        if (user is None) == (guest_session_id is None):
            raise ValueError("Exactly one of user or guest_session_id is required")

        if user is not None:
            return _SupervisorTurnContext(
                message=message,
                chat_id=chat_id,
                invoke_user_id=user.id,
                user_email=user.email,
                user=user,
                persist_uid=user.id,
                guest_session_id=None,
                guest_fp=None,
                client_ip=None,
            )

        # Guest chat — guest_session_id is non-None by the XOR check above.
        # ``invoke_user_id`` is the opaque ``guest:<uuid>`` string we feed to
        # LangGraph/Langfuse; it's not a Mongo id, so ``persist_uid`` stays None
        # and the repo writes use ``guest_fingerprint`` instead.
        assert guest_session_id is not None  # noqa: S101  # nosec B101 — invariant from XOR check
        return _SupervisorTurnContext(
            message=message,
            chat_id=chat_id,
            invoke_user_id=f"guest:{guest_session_id}",
            user_email=None,
            user=None,
            persist_uid=None,
            guest_session_id=guest_session_id,
            guest_fp=guest_session_id,
            client_ip=client_ip,
        )

    @staticmethod
    def _build_duplicate_resend_response(chat_id: str) -> ChatResponse:
        """Short-circuit response when the same message arrives twice in the dedupe window."""
        return ChatResponse(
            message=(
                "Got your message — still working on the previous one. Hang tight!"
            ),
            message_id=None,
            chat_id=chat_id,
            intent_name="duplicate_resend",
            confidence=1.0,
            type="message",
            data=None,
            places_session_token=None,
        )

    async def _assemble_response_from_supervisor_result(
        self,
        result: dict[str, Any],
        ctx: _SupervisorTurnContext,
    ) -> ChatResponse:
        """Turn the supervisor's shaped result + turn context into a ChatResponse.

        Side effects (in order):

        - Records AI-CHAT-010 consecutive-error telemetry (Slack alert when
          the count crosses ``CONSECUTIVE_ERROR_ALERT_THRESHOLD``).
        - Persists the user message.
        - Auto-names the conversation on the first real message or while
          the title is still the shallow placeholder (authenticated only).
        - Persists each intermediate auto-chain bot message and then the
          primary bot message.
        - Auto-saves itinerary on ``itinerary_results`` and on chain
          itineraries (authenticated only).
        - Mints a Places session token for guest users when the payload
          embeds backend Places photo URLs.
        - Logs the outgoing payload (issue #1034 debug).

        Used by both ``_handle_via_supervisor_v2`` (non-streaming) and the
        streaming pipeline added in piece 2c of issue #1117. Pure function
        of (result, ctx) + module-level repository / logger.
        """
        chat_id = ctx.chat_id
        message = ctx.message
        persist_uid = ctx.persist_uid
        guest_fp = ctx.guest_fp
        user = ctx.user
        guest_session_id = ctx.guest_session_id
        client_ip = ctx.client_ip

        # ----- AI-CHAT-010: consecutive-error tracking + Slack alert -----
        # Increment on error responses; reset on any successful response.
        # On reaching CONSECUTIVE_ERROR_ALERT_THRESHOLD, post a Slack alert
        # (no-op without SLACK_WEBHOOK_URL set) and append a soft-reset
        # offer to the user message so they aren't stuck guessing.
        from app.ai.errors import (
            CONSECUTIVE_ERROR_ALERT_THRESHOLD,
            ErrorClass,
            post_consecutive_error_alert,
            record_error_for_session,
            reset_error_count_for_session,
        )

        is_error_response = result.get("type") == "error"
        if is_error_response:
            count, recent_classes = record_error_for_session(
                chat_id, result.get("error_class") or ErrorClass.UNKNOWN.value
            )
            self.logger.warning(
                "chat_service.error_response chat_id=%s class=%s count=%d",
                chat_id,
                result.get("error_class") or "unknown",
                count,
            )
            # Fire the Slack alert + soft-reset offer ONLY on the
            # boundary-crossing turn. Subsequent failures keep the
            # counter incrementing (so we still log them) but don't
            # re-alert and don't keep stacking the reset offer onto
            # every reply.
            if count == CONSECUTIVE_ERROR_ALERT_THRESHOLD:
                # Fire Slack alert (best-effort, never blocks the response).
                await post_consecutive_error_alert(
                    chat_id=chat_id,
                    user_id=persist_uid,
                    consecutive_count=count,
                    recent_error_classes=recent_classes,
                    latest_user_message=message,
                )
                base_msg = result.get("message") or ""
                if "reset" not in base_msg.lower():
                    result["message"] = (
                        f"{base_msg}\n\nIt looks like we keep hitting a "
                        f"snag here. Want me to reset our conversation and "
                        f"try a fresh start?"
                    )
        else:
            reset_error_count_for_session(chat_id)
        # ----- end AI-CHAT-010 -----

        # Store user message
        await repository.create_message(
            content={"text": message},
            user_id=persist_uid,
            chat_id=chat_id,
            sender=MessageSender.USER,
            guest_fingerprint=guest_fp,
            intent_name=result.get("intent", "supervisor_v2"),
            action_data={
                "confidence": result.get("confidence", 1.0),
                "source": "supervisor_v2",
            },
        )

        # Update conversation metadata (authenticated users only)
        conversation_name: str | None = None
        if persist_uid is not None:
            await repository.update_conversation_on_message(chat_id, message)
            # Auto-name on the first real message AND on any subsequent
            # message while the current title is still the shallow
            # placeholder. This handles the "user clicked a suggestion
            # chip first → namer produced 'Search Flights' / 'Find
            # Hotels' verbatim" case: those titles are now blocklisted
            # to the placeholder, and the next message (which usually
            # contains the actual destination/dates) gets a chance to
            # produce a specific title like "Amsterdam to London Flights".
            conv_doc = await self._get_conversation_doc(chat_id)
            if conv_doc and (
                conv_doc.get("message_count", 0) <= 1
                or conv_doc.get("name") == _SHALLOW_PLACEHOLDER
            ):
                conversation_name = await self._auto_name_conversation(
                    chat_id, persist_uid, message
                )

        # Determine response type based on agent
        active_agent = result.get("agent", "general")
        response_type = result.get("type", "message")

        # Map agent to intent name for analytics.
        # "itinerary" maps to "create_itinerary" to match V1 format
        # (frontend and analytics rely on this value).
        agent_intent_map = {
            "flight": "flight_conversation",
            "hotel": "hotel_conversation",
            "itinerary": "create_itinerary",
            "general": "general_query",
        }
        intent_name = agent_intent_map.get(active_agent, "general_query")

        # Store bot response(s).
        # When auto-chain ran (e.g. "book everything" → flight + hotel),
        # chain_responses has all intermediate results. Store each as a
        # separate bot message so chat history shows both search results.
        chain_responses = result.get("chain_responses", [])
        if len(chain_responses) > 1:
            # Store intermediate responses (all except the last, which is
            # also in agent_response and stored below as the primary).
            for i, chain_resp in enumerate(chain_responses[:-1]):
                chain_type = chain_resp.get("type", "message")
                chain_msg = chain_resp.get("message", "")
                chain_data = {
                    k: v
                    for k, v in chain_resp.items()
                    if k not in _CHAIN_MSG_ACTION_DATA_EXCLUDED_KEYS
                }
                self.logger.info(
                    "Storing chain response %d/%d: type=%s",
                    i + 1,
                    len(chain_responses) - 1,
                    chain_type,
                )
                await repository.create_message(
                    content={"text": chain_msg},
                    user_id=persist_uid,
                    chat_id=chat_id,
                    sender=MessageSender.BOT,
                    guest_fingerprint=guest_fp,
                    intent_name=chain_type,
                    action_data=chain_data or None,
                )

        bot_response = result.get("message", "")

        # Build response data matching V1 shape.
        # For itinerary_results, V1 uses data=metadata (with
        # structured_itinerary inside) plus travel fields at top level.
        # For other types, pack all extra fields into data.
        if response_type == "itinerary_results":
            metadata = result.get("metadata") or {}
            extra_data = {
                **metadata,
                "origin": result.get("origin"),
                "destination": result.get("destination"),
                "origin_iata": result.get("origin_iata"),
                "destination_iata": result.get("destination_iata"),
                "origin_name": result.get("origin_name"),
                "destination_name": result.get("destination_name"),
                "departure_date": result.get("departure_date"),
                "return_date": result.get("return_date"),
                "adults": result.get("adults"),
                "children": result.get("children"),
                "infants": result.get("infants"),
                "trip_type": result.get("trip_type"),
                # Multi-hub country destinations: expose hub list so the
                # frontend can derive multi-city trip type reliably.
                "destination_hub_list": result.get("destination_hub_list"),
                "origin_location": result.get("origin_location"),
                "destination_location": result.get("destination_location"),
                "suggestions": result.get("suggestions"),
                # Personalized itinerary (#1038): full best-value-sorted
                # flight + hotel lists. The LLM never saw these — they
                # ride on the response side-channel for the FE rails and
                # the stitched Day 1 / Day N cards.
                "flights": result.get("flights"),
                "hotels": result.get("hotels"),
                # Session IDs + search params for hydrating the FE
                # recommendations slice — so clicking the Flights / Stays
                # tabs from the itinerary skips the duplicate FlightLogic
                # call and the booking flow has the session it needs.
                "flight_session_id": result.get("flight_session_id"),
                "hotel_session_id": result.get("hotel_session_id"),
                "flight_search_params": result.get("flight_search_params"),
                "hotel_search_params": result.get("hotel_search_params"),
                # Multi-hub country side-searches (#1152): merge multicity
                # chain_results into any existing chain_responses so neither
                # overwrites the other (itinerary supervisor doesn't chain today,
                # but guard against future changes).
                "chain_responses": (
                    list(metadata.get("chain_responses") or [])
                    + list(result.get("chain_results") or [])
                )
                or None,
            }
            if user is not None:
                extra_data = await self._try_auto_save_itinerary_and_enrich(
                    user.id, dict(result), extra_data, chat_id
                )
        else:
            extra_data = {
                k: v
                for k, v in result.items()
                if k not in _CHAT_EXTRA_DATA_EXCLUDED_KEYS
            }

        if response_type != "itinerary_results":
            chain_itin = _last_itinerary_results_in_chain(chain_responses)
            if chain_itin is not None and user is not None:
                base = extra_data if isinstance(extra_data, dict) else {}
                extra_data = await self._try_auto_save_itinerary_and_enrich(
                    user.id, chain_itin, base, chat_id
                )

        # When auto-chain produced multiple results (e.g. "book everything"
        # → flight + hotel), include all chain responses so the frontend
        # can render each result as a separate UI component.
        # Each chain response is sanitized to match the same shape as a
        # normal ChatResponse.data (strip internal keys, keep search data).
        if len(chain_responses) > 1:
            sanitized_chain = []
            for cr in chain_responses:
                sanitized = {
                    k: v
                    for k, v in cr.items()
                    if k not in _CHAT_CHAIN_SANITIZE_EXCLUDED_KEYS
                }
                # Preserve type and message for frontend routing
                sanitized["type"] = cr.get("type", "message")
                sanitized["message"] = cr.get("message", "")
                sanitized_chain.append(sanitized)
            if extra_data is None:
                extra_data = {}
            extra_data["chain_responses"] = sanitized_chain

        primary_action_data = (
            extra_data if response_type == "itinerary_results" else result.get("data")
        )
        # Chain-only itinerary auto-save adds saved_itinerary_id to extra_data (wire
        # response). Persist the same id on action_data so reload matches live response.
        if response_type != "itinerary_results" and isinstance(extra_data, dict):
            chain_sid = extra_data.get("saved_itinerary_id")
            if chain_sid is not None:
                if isinstance(primary_action_data, dict):
                    primary_action_data = {
                        **primary_action_data,
                        "saved_itinerary_id": chain_sid,
                    }
                elif primary_action_data is None:
                    primary_action_data = {"saved_itinerary_id": chain_sid}
        await repository.create_message(
            content={"text": bot_response},
            user_id=persist_uid,
            chat_id=chat_id,
            sender=MessageSender.BOT,
            guest_fingerprint=guest_fp,
            intent_name=intent_name,
            action=response_type,
            action_data=primary_action_data,
        )

        # Attach conversation_name so frontend can update sidebar
        if conversation_name and isinstance(extra_data, dict):
            extra_data["conversation_name"] = conversation_name
        elif conversation_name:
            extra_data = {"conversation_name": conversation_name}

        places_session_token: str | None = None
        if (
            guest_session_id is not None
            and client_ip is not None
            and isinstance(extra_data, dict)
            and _payload_contains_backend_places_photo_url(extra_data)
        ):
            from app.core.places_session import mint_places_session_token

            places_session_token = mint_places_session_token(
                guest_session_id, client_ip
            )
            self.logger.info(
                "places_session_token_mint | session_prefix=%s",
                guest_session_id[:8],
            )

        # Issue #1034 debug: log what we send to the frontend so we can
        # verify (a) categories are gone, (b) the flat flights/hotels array
        # is present + size, (c) message size to confirm the artifact
        # split kept the LLM-visible content compact.
        self._log_outgoing_payload(
            chat_id=chat_id,
            response_type=response_type,
            bot_response=bot_response,
            extra_data=extra_data,
        )

        return ChatResponse(
            message=bot_response,
            chat_id=chat_id,
            type=response_type,
            intent_name=intent_name,
            confidence=result.get("confidence", 1.0),
            message_id=result.get("message_id"),
            data=extra_data or None,
            places_session_token=places_session_token,
        )

    async def _build_supervisor_error_response(
        self,
        exc: Exception,
        ctx: _SupervisorTurnContext,
    ) -> ChatResponse:
        """Build the ``type=error`` ChatResponse for an uncaught supervisor exception.

        AI-CHAT-010: anything that escapes ``invoke_supervisor_v2``
        (checkpointer failure, surprise infra bug, etc.) must still go
        through the same telemetry path as supervisor-level errors:
        classify -> bump counter -> Slack alert at threshold -> user
        sees a class-specific message, not the pre-AI-CHAT-010 copy.

        Used by both the non-streaming path (returns directly) and the
        streaming path (wraps the response in an ``error`` SSE event).
        """
        from app.ai.errors import (
            CONSECUTIVE_ERROR_ALERT_THRESHOLD,
            classify_exception,
            post_consecutive_error_alert,
            record_error_for_session,
        )

        classified = classify_exception(exc)
        self.logger.exception(
            "V2 Supervisor unhandled exception chat_id=%s class=%s detail=%s",
            ctx.chat_id,
            classified.cls.value,
            classified.log_detail,
        )

        count, recent_classes = record_error_for_session(
            ctx.chat_id, classified.cls.value
        )
        # Fire Slack alert + soft-reset offer only on the boundary-
        # crossing turn (count == threshold) so we don't spam Slack or
        # repeat the offer on every subsequent failure.
        user_message = classified.user_message
        if count == CONSECUTIVE_ERROR_ALERT_THRESHOLD:
            await post_consecutive_error_alert(
                chat_id=ctx.chat_id,
                user_id=ctx.persist_uid,
                consecutive_count=count,
                recent_error_classes=recent_classes,
                latest_user_message=ctx.message,
            )
            user_message = (
                f"{user_message}\n\nIt looks like we keep hitting a "
                f"snag here. Want me to reset our conversation and "
                f"try a fresh start?"
            )

        # Never expose raw exception strings to clients on public/guest
        # chat (HTTP 200 path); auth users get debug context.
        if ctx.guest_session_id is not None:
            error_data: dict[str, str] | None = {
                "code": "processing_failed",
                "error_class": classified.cls.value,
            }
        else:
            error_data = {
                "error": str(exc),
                "error_class": classified.cls.value,
            }
        return ChatResponse(
            message=user_message,
            message_id=None,
            chat_id=ctx.chat_id,
            type="error",
            intent_name="error",
            confidence=0.0,
            data=error_data,
            places_session_token=None,
        )

    async def _handle_via_supervisor_v2(
        self,
        message: str,
        chat_id: str,
        *,
        user: UserPublic | None = None,
        guest_session_id: str | None = None,
        client_ip: str | None = None,
    ) -> ChatResponse:
        """Route message through V2 Supervisor.

        The V2 Supervisor classifies intent and dispatches to the appropriate
        sub-agent (flight, hotel, itinerary, general). It handles hand-back
        signals and re-routing automatically.

        Pass ``user`` for authenticated chat, or ``guest_session_id`` for public guest chat.
        """
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        # Anti-spam: short-circuit identical resends within the dedupe window.
        # The previous request is likely still being processed by the supervisor.
        if await _is_duplicate_resend(chat_id, message):
            self.logger.info(
                "chat_service.duplicate_resend_dropped chat_id=%s msg_len=%d",
                chat_id,
                len(message),
            )
            return self._build_duplicate_resend_response(chat_id)

        ctx = self._resolve_supervisor_context(
            message=message,
            chat_id=chat_id,
            user=user,
            guest_session_id=guest_session_id,
            client_ip=client_ip,
        )

        try:
            self.logger.info(
                "chat_service.supervisor_v2_invoke chat_id=%s",
                chat_id,
            )
            result = await invoke_supervisor_v2(
                message=message,
                user_id=ctx.invoke_user_id,
                chat_id=chat_id,
                user_email=ctx.user_email,
            )
            self.logger.info(
                "chat_service.supervisor_v2_done chat_id=%s agent=%s type=%s message_len=%d",
                chat_id,
                result.get("agent", "?"),
                result.get("type", "?"),
                len(result.get("message", "")),
            )
            return await self._assemble_response_from_supervisor_result(result, ctx)
        except Exception as e:
            return await self._build_supervisor_error_response(e, ctx)

    async def process_message(
        self, message: str, user: UserPublic, chat_id: str | None = None
    ) -> ChatResponse:
        """Process incoming chat message with AI.

        Args:
            message: User's message text
            user: Authenticated user (required)
            chat_id: Optional existing chat ID

        Returns:
            Response with AI-generated content and metadata
        """
        self.logger.info(
            "Processing message (len=%d, chat_id=%s)",
            len(message),
            chat_id or "new",
        )

        # Get or create chat conversation
        if not chat_id:
            chat_id = await repository.get_or_create_chat_conversation(user.id)

        return await self._handle_via_supervisor_v2(
            message,
            chat_id,
            user=user,
        )

    async def process_message_streaming(
        self,
        message: str,
        user: UserPublic,
        chat_id: str | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """SSE-streaming counterpart of :meth:`process_message`.

        Yields domain ``ChatStreamEvent`` objects as the supervisor graph
        runs. The API layer (``POST /chat/message/stream``) wraps each in
        the SSE wire format and writes to ``text/event-stream``. Used by
        the streaming chat endpoint added in #1117 to surface progress to
        the user during the ~30 s cold-turn budget instead of a frozen
        "thinking" indicator.

        Event order on a healthy turn:

        1. ``start`` — chat_id (sent immediately so the FE can clear its
           own "thinking" placeholder).
        2. ``progress`` — one per supervisor node finish
           (``route_or_classify``, ``pre_resolve_trip``,
           ``dispatch_itinerary``, …). FE renders as a stepper or activity
           log.
        3. zero-or-more custom events — tool-emitted payloads pass through
           verbatim. Piece 3 of #1117 will route ``itinerary_partial``
           chunks here as ``generate_itinerary`` streams its structured
           output.
        4. ``complete`` — final ChatResponse JSON (same shape as POST
           /chat/message returns). All persistence side-effects (user
           message, bot message(s), auto-name, auto-save, AI-CHAT-010
           telemetry) fire BEFORE this event, inside
           :meth:`_assemble_response_from_supervisor_result`.

        Edge cases:

        - Duplicate resend within the 5 s dedupe window: ``start`` +
          ``complete`` only, carrying the "still working on the previous
          one" body. No persistence.
        - Supervisor classified the turn as ``type=error`` (transient
          recovery, content-policy, etc.): the supervisor's streaming
          wrapper still emits a terminal ``final`` (or ``error`` kind)
          event with the shaped error envelope; we run it through the
          same assembly so AI-CHAT-010 telemetry fires and the error bot
          message is persisted, then emit ``complete``.
        - Unhandled exception escapes the supervisor stream or the
          assembly: ``error`` SSE event with the classified user-facing
          message. AI-CHAT-010 telemetry fires via
          :meth:`_build_supervisor_error_response`.

        Authenticated chat only — guest streaming is a future piece.

        Token deltas (``stream_mode="messages"``) are intentionally NOT
        relayed in piece 2c. Emitting every LLM token from the supervisor
        classify + agent ReAct loop + nested tool calls would flood the
        stream with non-final text. Adding a "final agent message only"
        filter is its own piece.
        """
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        self.logger.info(
            "Processing streaming message (len=%d, chat_id=%s)",
            len(message),
            chat_id or "new",
        )

        if not chat_id:
            chat_id = await repository.get_or_create_chat_conversation(user.id)

        # Dedupe short-circuit. Mirrors _handle_via_supervisor_v2: when the
        # same message arrives twice within the dedupe window the previous
        # request is likely still being processed; replying with a soft
        # "hang tight" beats persisting a duplicate.
        if await _is_duplicate_resend(chat_id, message):
            self.logger.info(
                "chat_service.duplicate_resend_dropped (streaming) chat_id=%s msg_len=%d",
                chat_id,
                len(message),
            )
            dedupe = self._build_duplicate_resend_response(chat_id)
            yield ChatStreamEvent(event="start", data={"chat_id": chat_id})
            yield ChatStreamEvent(event="complete", data=dedupe.model_dump(mode="json"))
            return

        ctx = self._resolve_supervisor_context(
            message=message,
            chat_id=chat_id,
            user=user,
            guest_session_id=None,
            client_ip=None,
        )

        yield ChatStreamEvent(event="start", data={"chat_id": chat_id})

        supervisor_result: dict[str, Any] | None = None

        try:
            async for graph_event in invoke_supervisor_v2_streaming(
                message=message,
                user_id=ctx.invoke_user_id,
                chat_id=chat_id,
                user_email=ctx.user_email,
            ):
                kind = graph_event.get("kind")
                if kind in ("final", "error"):
                    # Both terminals carry a shaped supervisor result —
                    # classified errors flow through the same post-stream
                    # assembly as successes so AI-CHAT-010 telemetry +
                    # persistence run consistently.
                    supervisor_result = graph_event.get("result") or {}
                    break
                if kind == "node_update":
                    yield ChatStreamEvent(
                        event="progress",
                        data={"node": graph_event.get("node", "")},
                    )
                    continue
                if kind == "custom":
                    # Tool-emitted payloads — piece 3 will route
                    # itinerary_partial chunks through this channel. Tool
                    # payloads name themselves via a ``type`` field; fall
                    # back to "custom" if absent so unknown tools don't
                    # break the wire format.
                    data = graph_event.get("data")
                    if isinstance(data, dict):
                        yield ChatStreamEvent(
                            event=str(data.get("type") or "custom"),
                            data=data,
                        )
                    continue
                # ``token`` events are deliberately dropped — see the
                # method docstring for why.

            if supervisor_result is None:
                raise RuntimeError(
                    "invoke_supervisor_v2_streaming finished without terminal event"
                )

            response = await self._assemble_response_from_supervisor_result(
                supervisor_result, ctx
            )
            yield ChatStreamEvent(
                event="complete", data=response.model_dump(mode="json")
            )
        except Exception as e:
            self.logger.exception(
                "process_message_streaming: unhandled error chat_id=%s",
                chat_id,
            )
            error_response = await self._build_supervisor_error_response(e, ctx)
            yield ChatStreamEvent(
                event="error",
                data=error_response.model_dump(mode="json"),
            )

    async def process_public_message(
        self,
        message: str,
        *,
        guest_session_id: str,
        chat_id: str,
        client_ip: str,
    ) -> ChatResponse:
        """Process a guest message for the public landing chat (no JWT)."""
        self.logger.info("Processing public (guest) chat message")
        return await self._handle_via_supervisor_v2(
            message,
            chat_id,
            guest_session_id=guest_session_id,
            client_ip=client_ip,
        )

    async def claim_guest_thread(
        self,
        *,
        user_id: str,
        fingerprint: str,
        chat_id: str,
        max_age_minutes: int,
    ) -> "ClaimChatResponse":
        """Re-own a guest chat thread for the authenticated user.

        Idempotent; safe to call twice. Saved-itinerary docs pointing at the
        same ``chat_id`` are defensively relinked to the user.
        """
        from .repository import claim_messages_for_user
        from .schemas import (
            CLAIM_MESSAGE_CAP,
            ClaimChatResponse,
            ClaimOutcomeStatus,
        )

        outcome = await claim_messages_for_user(
            chat_id=chat_id,
            fingerprint=fingerprint,
            user_id=user_id,
            max_age_minutes=max_age_minutes,
            message_cap=CLAIM_MESSAGE_CAP,
        )

        if outcome.status in (
            ClaimOutcomeStatus.CLAIMED,
            ClaimOutcomeStatus.ALREADY_CLAIMED,
        ):
            try:
                from app.domains.saved_itinerary.repository import (
                    relink_saved_itineraries_to_user,
                )

                # Defensive: re-own any saved_itineraries doc that landed without
                # a user_id (legacy / partial-write paths). With the backfill
                # below, this stays correct even if both paths produced a doc.
                relinked = await relink_saved_itineraries_to_user(
                    chat_id=chat_id, user_id=user_id
                )
                if relinked:
                    self.logger.info(
                        "chat_claim.itinerary_relinked count=%s chat_id=%s",
                        relinked,
                        chat_id,
                    )
            except Exception as exc:
                self.logger.warning(
                    "chat_claim.itinerary_relink_failed chat_id=%s err=%s",
                    chat_id,
                    exc,
                )

            try:
                from .repository import backfill_guest_itinerary_for_chat

                # Guest auto-save is gated on authentication, so itinerary
                # messages generated pre-claim have ``structured_itinerary`` in
                # ``action_data`` but no ``saved_itinerary_id``. Create the
                # saved_itineraries row now and stamp the id back so reload
                # routes to ``/itinerary/:id`` instead of the empty
                # ``/itinerary?destination=...`` fallback.
                stamped = await backfill_guest_itinerary_for_chat(
                    chat_id=chat_id, user_id=user_id
                )
                if stamped:
                    self.logger.info(
                        "chat_claim.itinerary_backfilled count=%s chat_id=%s",
                        stamped,
                        chat_id,
                    )
            except Exception as exc:
                self.logger.warning(
                    "chat_claim.itinerary_backfill_failed chat_id=%s err=%s",
                    chat_id,
                    exc,
                )

        if outcome.status in (
            ClaimOutcomeStatus.CLAIMED,
            ClaimOutcomeStatus.ALREADY_CLAIMED,
            ClaimOutcomeStatus.NOTHING_TO_CLAIM,
        ):
            self.logger.info(
                "chat_claim.completed status=%s chat_id=%s user_id=%s count=%s",
                outcome.status.value,
                chat_id,
                user_id,
                outcome.message_count,
            )
        else:
            self.logger.warning(
                "chat_claim.rejected status=%s chat_id=%s user_id=%s",
                outcome.status.value,
                chat_id,
                user_id,
            )

        return ClaimChatResponse(
            status=outcome.status,
            chat_id=outcome.chat_id,
            message_count=outcome.message_count,
        )


# Singleton instance for dependency injection
chat_service = ChatService()
