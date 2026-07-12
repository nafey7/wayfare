"""Server-Sent Events encoding helpers for POST /chat/message/stream.

Implements piece 1 of issue #1117 (the SSE transport layer for the
itinerary skeleton-streaming work deferred out of PR #1116). Subsequent
pieces wire the real graph events:

- Piece 2: ChatService.process_message_streaming() emits the same event
  types from supervisor graph state transitions.
- Piece 3: generate_itinerary tool emits ``itinerary_partial`` as the
  structured-output LLM streams day plans one piece at a time.
- Piece 4: frontend EventSource subscriber consumes them.

SSE wire format (per WHATWG HTML living standard, EventSource section):

    id: <event_id>
    event: <type>
    data: <json>
    <blank line>

The ``id:`` field lets the client reconnect with ``Last-Event-ID`` so the
server can replay missed events. The blank line is the event terminator.
``\\n\\n`` works on every browser; the spec also allows ``\\r\\n\\r\\n``.

Why these specific HTTP headers
-------------------------------
* ``Cache-Control: no-cache, no-transform`` — proxies and the browser's
  HTTP cache must not buffer the response. ``no-transform`` blocks gzip
  middleware that would otherwise wait for a full chunk before flushing.
* ``Connection: keep-alive`` — the response is a long-lived stream; the
  client and intermediaries should not tear the connection down between
  events.
* ``X-Accel-Buffering: no`` — Nginx-specific opt-out from response
  buffering. Without it, Nginx buffers the entire response before
  forwarding, which defeats the point of streaming.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any


class SSEEventType(StrEnum):
    """Discrete moments in a chat turn that SSE clients subscribe to.

    Only the events the backend actually emits today are listed. When
    new event kinds are introduced (token streaming, side-search status
    rails, etc.) add the corresponding members alongside the producer
    code rather than declaring them speculatively.
    """

    START = "start"
    PROGRESS = "progress"
    ITINERARY_PARTIAL = "itinerary_partial"
    COMPLETE = "complete"
    ERROR = "error"


SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
    # AWS Application Load Balancer gzips ``text/event-stream`` by
    # default, which buffers the entire response and defeats streaming.
    # ``Content-Encoding: identity`` tells ALB to leave the body alone.
    # Harmless on dev / non-ALB deploys.
    "Content-Encoding": "identity",
}


def format_sse_event(
    event_id: str,
    event_type: SSEEventType | str,
    data: dict[str, Any],
) -> str:
    """Encode one SSE event as the on-the-wire string the client expects.

    ``data`` is JSON-serialized with compact separators (no whitespace) so
    proxies that line-buffer don't split an event across flushes.
    ``event_type`` accepts either the typed enum (for events the API
    layer raises itself) or a plain string (for tool-emitted custom
    events whose name only exists in domain code).

    Returns a string ending with the blank-line terminator. Raises
    ``TypeError`` if ``data`` contains a non-JSON-encodable value — the
    caller must serialize Pydantic / datetime values before passing in.
    """
    type_value = (
        event_type.value if isinstance(event_type, SSEEventType) else event_type
    )
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event_id}\nevent: {type_value}\ndata: {payload}\n\n"


__all__ = ["SSE_HEADERS", "SSEEventType", "format_sse_event"]
