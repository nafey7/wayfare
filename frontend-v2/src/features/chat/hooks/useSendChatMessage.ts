/**
 * Streaming chat hook — drives POST /chat/message/stream with a
 * transparent fallback to the existing POST /chat/message mutation.
 *
 * Issue #1117 piece 4b. The caller (``ChatContext.sendMessage``) gets
 * the same ``ChatResponse`` it always got — the hook hides which
 * transport actually delivered it. SSE-supported turns surface
 * ``itinerary_partial`` events into Redux so
 * ``ItineraryDetailsComponent`` can render skeleton days within seconds
 * instead of after the full ~30 s blocking call.
 *
 * Fallback to the non-streaming endpoint fires when:
 * - The streaming endpoint returns 404 (backend
 *   ``CHAT_STREAMING_ENABLED=false`` per environment).
 * - The browser doesn't support fetch streaming (older Safari, some
 *   proxies). Same observable: ``postChatStream`` rejects before the
 *   first event.
 * - Any unexpected fetch / parse failure mid-stream BEFORE the server
 *   has emitted the ``complete`` event.
 *
 * Lock-busy 429 propagates as-is (matches the non-streaming endpoint's
 * detail body so the caller's existing handler works on either path).
 */

import { useCallback, useState } from 'react';

import { chatApi } from '@/api/chatApi';
import { selectAuthToken } from '@/store/slices/authSlice';
import {
  clearStreamingItinerary,
  setStreamingItinerary,
} from '@/store/slices/chatSlice';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import type { ChatMessageRequest, ChatResponse } from '@/types/chat';
import {
  SSEHttpError,
  decodeSSEFrame,
  postChatStream,
} from '@/utils/sseChat';

/**
 * Thrown when the SSE stream itself succeeded but the server emitted a
 * terminal ``error`` event (e.g. classifier ran into a non-retryable
 * failure). This is distinct from ``SSEHttpError`` (transport-level
 * failure — fallback-eligible) so ``shouldFallBackToNonStreaming`` can
 * propagate stream errors instead of silently retrying via the
 * non-streaming endpoint (same backend, same failure mode).
 */
export class ChatStreamError extends Error {
  constructor(
    message: string,
    public readonly errorClass?: string,
  ) {
    super(message);
    this.name = 'ChatStreamError';
  }
}

const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) || '/api';

/**
 * SSE event shape on the wire from POST /chat/message/stream.
 *
 * Mirrors ``app.api.chat_sse.SSEEventType`` on the backend. The
 * ``complete`` event carries the same ``ChatResponse`` shape the
 * non-streaming endpoint returns directly.
 */
type StreamEventType =
  | 'start'
  | 'progress'
  | 'itinerary_partial'
  | 'complete'
  | 'error';

interface SendChatOptions {
  /** AbortSignal — fires when the chat panel unmounts mid-stream. */
  signal?: AbortSignal;
  /** Override fetch for tests (forwarded to ``postChatStream``). */
  fetchImpl?: typeof fetch;
}

interface UseSendChatMessageResult {
  /** Send a chat turn and resolve with the final ChatResponse. */
  sendMessage: (
    request: ChatMessageRequest,
    options?: SendChatOptions,
  ) => Promise<ChatResponse>;
  /** True between the start of an SSE turn and its terminal event. */
  isStreaming: boolean;
}

export function useSendChatMessage(): UseSendChatMessageResult {
  const dispatch = useAppDispatch();
  const token = useAppSelector(selectAuthToken);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(
    async (
      request: ChatMessageRequest,
      options: SendChatOptions = {},
    ): Promise<ChatResponse> => {
      setIsStreaming(true);
      // Tracks how many SSE frames the streaming turn actually received.
      // Read on the error path to gate the non-streaming fallback — once
      // any frame has landed the backend has started persisting messages
      // for this turn, and a fresh POST /chat/message would create
      // duplicates that the 5 s dedupe window may not catch (cold-turn
      // itineraries run 25-70 s).
      const progress = { framesReceived: 0 };

      try {
        const response = await runStreamingTurn({
          request,
          token,
          fetchImpl: options.fetchImpl,
          signal: options.signal,
          onPartialItinerary: (payload) => {
            dispatch(setStreamingItinerary(payload));
          },
          progress,
        });
        return response;
      } catch (err) {
        // Fall back to the non-streaming endpoint only when:
        // (a) the SSE attempt failed BEFORE any frame arrived
        //     (transport rejection — same observable as the route not
        //     existing), AND
        // (b) the error class itself is fallback-eligible (404, network
        //     blip; not 429 lock-busy, not a stream-emitted error).
        // Anything else propagates so the caller's existing error
        // handler runs and the user sees the right message.
        if (
          progress.framesReceived === 0 &&
          shouldFallBackToNonStreaming(err)
        ) {
          return await sendNonStreaming(dispatch, request);
        }
        throw err;
      } finally {
        dispatch(clearStreamingItinerary());
        setIsStreaming(false);
      }
    },
    [dispatch, token],
  );

  return { sendMessage, isStreaming };
}

/**
 * Drive the SSE endpoint to completion and return the final ChatResponse.
 *
 * Iterates the event stream, ignoring events that piece 4 doesn't render
 * (``progress``, ``agent_text_delta``, ``side_search_*``) and dispatching
 * ``itinerary_partial`` payloads to Redux via ``onPartialItinerary``.
 * The terminal ``complete`` event delivers the final response; a
 * terminal ``error`` event is converted to a thrown Error so the
 * caller's catch block handles it the same way mutation failures are
 * handled today.
 */
async function runStreamingTurn({
  request,
  token,
  fetchImpl,
  signal,
  onPartialItinerary,
  progress,
}: {
  request: ChatMessageRequest;
  token: string | null;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
  onPartialItinerary: (payload: Record<string, unknown>) => void;
  /**
   * Mutable counter that ticks once per SSE frame received from the wire.
   * The caller reads it after a thrown error to decide whether the
   * non-streaming endpoint is safe to retry against — if any frames
   * landed, the backend has likely already persisted the user message
   * (and possibly bot messages) and a fresh POST would create duplicates.
   */
  progress: { framesReceived: number };
}): Promise<ChatResponse> {
  interface ErrorPayload {
    message?: string;
    error_class?: string;
  }

  let completeResponse: ChatResponse | null = null;
  let errorPayload: ErrorPayload | null = null;

  for await (const frame of postChatStream({
    url: `${API_BASE_URL}/chat/message/stream`,
    body: request,
    token,
    signal,
    fetchImpl,
  })) {
    progress.framesReceived++;
    const eventType = frame.event as StreamEventType;
    switch (eventType) {
      case 'itinerary_partial': {
        const payload = decodeSSEFrame<Record<string, unknown>>(frame).data;
        onPartialItinerary(payload);
        break;
      }
      case 'complete': {
        completeResponse = decodeSSEFrame<ChatResponse>(frame).data;
        break;
      }
      case 'error': {
        errorPayload = decodeSSEFrame<ErrorPayload>(frame).data;
        break;
      }
      // start / progress — accepted but not consumed by the FE today
      // (no progress stepper rendered). Any unknown event type from
      // a future backend version also lands here and is dropped
      // silently — we never throw on unrecognized events because the
      // wire contract is forward-compatible by design.
      default:
        break;
    }
  }

  if (errorPayload) {
    const message =
      errorPayload.message ?? 'An error occurred while processing your message.';
    throw new ChatStreamError(message, errorPayload.error_class);
  }

  if (!completeResponse) {
    // Server closed the stream without a terminal event. Shouldn't
    // happen — backend always emits ``complete`` or ``error``. The
    // fallback path below will check ``progress.framesReceived`` to
    // avoid double-sending if any non-terminal frames already arrived.
    throw new SSEHttpError(
      0,
      '',
      'SSE stream ended without complete or error event',
    );
  }

  return completeResponse;
}

/**
 * Decide whether an SSE failure should silently fall back to the
 * non-streaming endpoint, or propagate to the caller.
 *
 * Fall back on:
 * - 404 (feature flag off in this environment).
 * - Network / fetch errors BEFORE the stream's content-type check (e.g.
 *   the browser doesn't support streamed bodies — same observable as
 *   the SSE endpoint not existing).
 *
 * Propagate on:
 * - 429 (lock contention — the same error the non-streaming endpoint
 *   raises; the FE's existing handler shows the "wait" message).
 * - Stream-emitted ``error`` events (server classified the failure and
 *   wants the FE to surface it).
 * - 5xx from the stream endpoint (real server problem — falling back
 *   to the same backend wouldn't help and would mask the issue).
 */
function shouldFallBackToNonStreaming(err: unknown): boolean {
  // Stream-emitted error events — server classified the failure and
  // wants the FE to surface it. Retrying via the non-streaming endpoint
  // would hit the same backend and produce the same result, so propagate.
  if (err instanceof ChatStreamError) {
    return false;
  }
  if (err instanceof SSEHttpError) {
    // 404 / 405 → endpoint doesn't exist. Anything else is a real
    // failure the caller should see.
    return err.status === 404 || err.status === 405;
  }
  // User-initiated cancellation — propagate so the caller knows the
  // turn was cancelled, don't paper over with the non-streaming endpoint.
  // NOTE: the AbortSignal passed into ``sendMessage`` only plumbs through
  // to ``postChatStream`` (SSE attempt). The non-streaming fallback in
  // ``sendNonStreaming`` doesn't honour the signal — by design, because
  // returning ``false`` here ensures we don't reach the fallback when
  // the caller explicitly aborted. Anyone changing the abort behaviour
  // must keep that guarantee.
  if (err instanceof DOMException && err.name === 'AbortError') {
    return false;
  }
  // Anything else (TypeError from fetch on unsupported browser,
  // network blip before the first frame) — fall through to the
  // non-streaming endpoint.
  return true;
}

/**
 * Non-streaming POST /chat/message via the existing RTK Query mutation.
 *
 * Pulled into a helper so the streaming path and the fallback path
 * share exactly one source of truth for the mutation's error surface.
 * Dispatched directly (rather than via the React hook) because this
 * function runs inside an async callback that's not a hook itself —
 * RTK Query's ``initiate`` exposes the same mutation programmatically.
 */
async function sendNonStreaming(
  dispatch: ReturnType<typeof useAppDispatch>,
  request: ChatMessageRequest,
): Promise<ChatResponse> {
  const result = await dispatch(
    chatApi.endpoints.sendMessage.initiate(request),
  ).unwrap();
  return result;
}
