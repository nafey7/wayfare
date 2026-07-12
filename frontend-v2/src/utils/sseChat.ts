/**
 * SSE client for POST `/chat/message/stream` (issue #1117 piece 4).
 *
 * The native `EventSource` API only supports GET requests and can't send
 * custom headers — neither works for our auth-gated POST endpoint. So we
 * use `fetch` with a streamed response body and parse the
 * `text/event-stream` wire format ourselves.
 *
 * Wire format (per WHATWG HTML living standard, EventSource section):
 *
 *     id: <event_id>
 *     event: <type>
 *     data: <json>
 *     <blank line>
 *
 * Multi-line `data:` is allowed by the spec but the backend never emits
 * it (compact JSON encoding) so the parser keeps a single `data` buffer
 * per event and joins multi-line with `\n` per spec for completeness.
 */

/** Parsed SSE event in the on-the-wire shape — string `data` (JSON-encoded). */
export interface SSEFrame {
  id: string;
  event: string;
  data: string;
}

/** A frame with `data` decoded from JSON, when callers want it typed. */
export interface SSEEvent<T = unknown> {
  id: string;
  event: string;
  data: T;
}

export interface PostChatStreamOptions {
  /** Absolute or `/api/...`-relative URL of the streaming endpoint. */
  url: string;
  /** JSON-serializable request body. */
  body: unknown;
  /** Optional Bearer token; omit for guest streams. */
  token?: string | null;
  /** Extra headers (e.g. `X-Public-Chat-Session` if guest streaming ships). */
  headers?: Record<string, string>;
  /**
   * Optional `Last-Event-ID` to send on reconnect so the server can
   * replay missed events. The backend doesn't implement replay in
   * Piece 1, but the field is part of the wire contract.
   */
  lastEventId?: string;
  /** AbortSignal for cancellation (e.g. component unmounts mid-stream). */
  signal?: AbortSignal;
  /** Custom `fetch` impl — used by tests to inject a controlled stream. */
  fetchImpl?: typeof fetch;
}

/** Thrown when the response is not a 2xx + `text/event-stream`. */
export class SSEHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly responseBody: string,
    message?: string,
  ) {
    super(message ?? `SSE request failed with HTTP ${status}`);
    this.name = 'SSEHttpError';
  }
}

/**
 * Async-iterate the SSE event stream from the chat streaming endpoint.
 *
 * The caller is responsible for inspecting each `event` field (one of
 * `start`, `progress`, `agent_text_delta`, `itinerary_partial`,
 * `side_search_flight`, `side_search_hotel`, `complete`, `error`) and
 * `JSON.parse(frame.data)` when ready.
 *
 * The async iterator finishes when the server closes the stream OR when
 * the AbortSignal fires. A non-2xx HTTP status raises `SSEHttpError`
 * before any frame is yielded so callers can fall back to the
 * non-streaming endpoint synchronously.
 */
export async function* postChatStream({
  url,
  body,
  token,
  headers,
  lastEventId,
  signal,
  fetchImpl,
}: PostChatStreamOptions): AsyncGenerator<SSEFrame, void, void> {
  const fetcher = fetchImpl ?? fetch;
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    ...headers,
  };
  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }
  if (lastEventId) {
    requestHeaders['Last-Event-ID'] = lastEventId;
  }

  const response = await fetcher(url, {
    method: 'POST',
    headers: requestHeaders,
    body: JSON.stringify(body),
    signal,
    // Some browsers require this to avoid the response being buffered
    // by HTTP/2 push handling. Harmless when unsupported.
    cache: 'no-store',
  });

  if (!response.ok) {
    // Slurp body text for the error envelope so callers can branch on
    // e.g. lock-busy 429 details — same shape as the non-streaming
    // endpoint returns.
    const text = await response.text().catch(() => '');
    throw new SSEHttpError(response.status, text);
  }

  const contentType = response.headers.get('Content-Type') ?? '';
  if (!contentType.toLowerCase().startsWith('text/event-stream')) {
    const text = await response.text().catch(() => '');
    throw new SSEHttpError(
      response.status,
      text,
      `Expected text/event-stream, got ${contentType || 'no Content-Type'}`,
    );
  }

  if (!response.body) {
    // No streamable body (older Safari, mocks). Treat as an empty stream
    // — the caller's fallback path takes over.
    return;
  }

  const decoder = new TextDecoder('utf-8');
  const reader = response.body.getReader();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Events are separated by a blank line. Per spec both `\n\n` and
      // `\r\n\r\n` are valid; normalize CRLF first.
      const normalized = buffer.replace(/\r\n/g, '\n');
      const blocks = normalized.split('\n\n');

      // The last segment may be a partial event still being received;
      // write it back to ``buffer`` BEFORE yielding any completed
      // frames so that if ``parseSSEBlock`` ever throws (e.g. a future
      // change adds JSON validation in the parser) we don't lose the
      // pending tail that was queued for the next iteration.
      buffer = blocks[blocks.length - 1] ?? '';
      for (let i = 0; i < blocks.length - 1; i++) {
        const block = blocks[i] ?? '';
        const frame = parseSSEBlock(block);
        if (frame) yield frame;
      }
    }

    // Flush any trailing partial event the server emitted right before
    // closing the stream (rare but legal — no trailing blank line).
    if (buffer.trim().length > 0) {
      const frame = parseSSEBlock(buffer);
      if (frame) yield frame;
    }
  } finally {
    // Always release the reader so the connection can be reused / closed.
    reader.releaseLock();
  }
}

/**
 * Parse a single SSE event block (lines separated by `\n`) into a frame.
 *
 * Returns `null` when the block contains no `data:` field — comment
 * lines (`: keep-alive`) and orphan `event:` headers are dropped per
 * spec. Multi-line `data:` values are joined with `\n` (also per spec).
 */
export function parseSSEBlock(block: string): SSEFrame | null {
  let id = '';
  let event = 'message';
  const dataLines: string[] = [];

  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue; // comment line
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;
    const field = line.slice(0, colonIdx);
    // Spec: one leading space after the colon is stripped if present.
    let value = line.slice(colonIdx + 1);
    if (value.startsWith(' ')) value = value.slice(1);

    if (field === 'id') id = value;
    else if (field === 'event') event = value || 'message';
    else if (field === 'data') dataLines.push(value);
  }

  if (dataLines.length === 0) return null;
  return { id, event, data: dataLines.join('\n') };
}

/**
 * Parse a frame's `data` field with JSON.parse, surfacing the typed
 * payload alongside the wire metadata. Callers that don't care about
 * typing can just `JSON.parse(frame.data)` themselves.
 */
export function decodeSSEFrame<T = unknown>(frame: SSEFrame): SSEEvent<T> {
  return {
    id: frame.id,
    event: frame.event,
    data: JSON.parse(frame.data) as T,
  };
}
