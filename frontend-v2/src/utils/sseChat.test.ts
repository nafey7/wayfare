/**
 * Tests for the SSE client utility (#1117 piece 4a).
 *
 * Covers the wire-format parser, frame decoding, fetch integration, and
 * error envelopes. Mocks `fetch` with `ReadableStream` so we drive the
 * exact chunk timing the production code will see — including events
 * split across multiple reads (a common reality with chunked transfer).
 */

import { describe, expect, it, vi } from 'vitest';
import {
  SSEHttpError,
  decodeSSEFrame,
  parseSSEBlock,
  postChatStream,
} from './sseChat';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function streamingResponse(
  chunks: string[],
  init: ResponseInit = {},
): Response {
  // Build a ReadableStream that emits each chunk as a separate read so
  // tests can simulate events arriving in pieces.
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
    ...init,
  });
}

function frame(event: string, data: unknown, id = 'evt-1'): string {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

async function collect<T>(it: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const v of it) out.push(v);
  return out;
}

// ---------------------------------------------------------------------------
// parseSSEBlock
// ---------------------------------------------------------------------------

describe('parseSSEBlock', () => {
  it('parses id, event, and data fields', () => {
    const result = parseSSEBlock('id: abc\nevent: start\ndata: {"chat_id":"c1"}');
    expect(result).toEqual({
      id: 'abc',
      event: 'start',
      data: '{"chat_id":"c1"}',
    });
  });

  it('defaults event to "message" when omitted', () => {
    const result = parseSSEBlock('id: x\ndata: hello');
    expect(result?.event).toBe('message');
  });

  it('strips exactly one leading space after the colon (SSE spec)', () => {
    // "data:hello" and "data: hello" must both yield "hello"; "data:  hello"
    // yields " hello" (only ONE space stripped).
    expect(parseSSEBlock('data:hello')?.data).toBe('hello');
    expect(parseSSEBlock('data: hello')?.data).toBe('hello');
    expect(parseSSEBlock('data:  hello')?.data).toBe(' hello');
  });

  it('joins multi-line data fields with newlines', () => {
    const result = parseSSEBlock('event: bigdata\ndata: line1\ndata: line2');
    expect(result?.data).toBe('line1\nline2');
  });

  it('drops comment lines (those starting with ":")', () => {
    const result = parseSSEBlock(': keep-alive\nevent: ping\ndata: ok');
    expect(result?.event).toBe('ping');
    expect(result?.data).toBe('ok');
  });

  it('returns null when no data field is present', () => {
    expect(parseSSEBlock(': only comment')).toBeNull();
    expect(parseSSEBlock('event: orphan')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// decodeSSEFrame
// ---------------------------------------------------------------------------

describe('decodeSSEFrame', () => {
  it('JSON-parses the data field and preserves id + event', () => {
    const decoded = decodeSSEFrame<{ chat_id: string }>({
      id: 'evt-7',
      event: 'start',
      data: '{"chat_id":"c-99"}',
    });
    expect(decoded).toEqual({
      id: 'evt-7',
      event: 'start',
      data: { chat_id: 'c-99' },
    });
  });

  it('throws SyntaxError on malformed JSON', () => {
    expect(() =>
      decodeSSEFrame({ id: 'x', event: 'start', data: '{broken' }),
    ).toThrow(SyntaxError);
  });
});

// ---------------------------------------------------------------------------
// postChatStream — happy path
// ---------------------------------------------------------------------------

describe('postChatStream', () => {
  it('yields each event in order when the body arrives in one chunk', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(
        streamingResponse([
          frame('start', { chat_id: 'c1' }, 'e1') +
            frame('progress', { node: 'route_or_classify' }, 'e2') +
            frame('complete', { message: 'done' }, 'e3'),
        ]),
      );

    const events = await collect(
      postChatStream({
        url: '/api/chat/message/stream',
        body: { message: 'hi' },
        token: 'jwt-token',
        fetchImpl,
      }),
    );

    expect(events.map((e) => e.event)).toEqual(['start', 'progress', 'complete']);
    expect(events.map((e) => e.id)).toEqual(['e1', 'e2', 'e3']);
    expect(JSON.parse(events[0]!.data)).toEqual({ chat_id: 'c1' });

    // Auth + content-type headers wired correctly.
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [, init] = fetchImpl.mock.calls[0]!;
    const sentHeaders = init?.headers as Record<string, string>;
    expect(sentHeaders.Authorization).toBe('Bearer jwt-token');
    expect(sentHeaders.Accept).toBe('text/event-stream');
    expect(init?.method).toBe('POST');
  });

  it('handles events split across multiple chunks at arbitrary byte boundaries', async () => {
    // Simulate a real chunked transfer where the second event arrives
    // half in one chunk and half in the next — the parser must buffer
    // across reads to recover both events.
    const fetchImpl = vi.fn().mockResolvedValue(
      streamingResponse([
        // Chunk 1: complete first event + start of second
        `id: e1\nevent: start\ndata: {"chat_id":"c1"}\n\nid: e2\nevent`,
        // Chunk 2: rest of second event + start of third
        `: progress\ndata: {"node":"route"}\n\nid: e3\n`,
        // Chunk 3: tail of third event (no trailing blank line — server closed)
        `event: complete\ndata: {"message":"done"}\n\n`,
      ]),
    );

    const events = await collect(
      postChatStream({
        url: '/api/chat/message/stream',
        body: { message: 'hi' },
        fetchImpl,
      }),
    );
    expect(events.map((e) => e.event)).toEqual(['start', 'progress', 'complete']);
  });

  it('flushes a trailing partial event when the server closes without a blank line', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      streamingResponse([
        // Note: no trailing \n\n on the last event — the spec allows
        // this, and the parser must still emit it on stream-close.
        `id: e1\nevent: complete\ndata: {"message":"done"}`,
      ]),
    );
    const events = await collect(
      postChatStream({
        url: '/api/chat/message/stream',
        body: { message: 'hi' },
        fetchImpl,
      }),
    );
    expect(events).toHaveLength(1);
    expect(events[0]!.event).toBe('complete');
  });

  it('omits Authorization when no token is given (guest streaming)', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(streamingResponse([frame('start', { chat_id: 'c1' })]));
    await collect(
      postChatStream({
        url: '/api/chat/message/stream',
        body: { message: 'hi' },
        fetchImpl,
      }),
    );
    const headers = fetchImpl.mock.calls[0]![1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('forwards Last-Event-ID for reconnect-with-replay', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(streamingResponse([frame('start', { chat_id: 'c1' })]));
    await collect(
      postChatStream({
        url: '/api/chat/message/stream',
        body: { message: 'hi' },
        lastEventId: 'evt-42',
        fetchImpl,
      }),
    );
    const headers = fetchImpl.mock.calls[0]![1]?.headers as Record<string, string>;
    expect(headers['Last-Event-ID']).toBe('evt-42');
  });
});

// ---------------------------------------------------------------------------
// postChatStream — error envelopes
// ---------------------------------------------------------------------------

describe('postChatStream error handling', () => {
  it('raises SSEHttpError when the response is non-2xx', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response('Not Found', { status: 404 }),
    );
    await expect(
      collect(
        postChatStream({
          url: '/api/chat/message/stream',
          body: { message: 'hi' },
          fetchImpl,
        }),
      ),
    ).rejects.toMatchObject({
      name: 'SSEHttpError',
      status: 404,
    });
  });

  it('preserves the 429 detail body so callers can surface the right message', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: 'Another request is already processing for this conversation. Please wait for the previous request to complete.',
        }),
        {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    try {
      await collect(
        postChatStream({
          url: '/api/chat/message/stream',
          body: { message: 'hi' },
          fetchImpl,
        }),
      );
      throw new Error('expected SSEHttpError');
    } catch (e) {
      const err = e as SSEHttpError;
      expect(err.status).toBe(429);
      expect(JSON.parse(err.responseBody).detail).toMatch(
        /Another request is already processing/,
      );
    }
  });

  it('raises SSEHttpError when Content-Type is not text/event-stream', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response('{"hello":"world"}', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(
      collect(
        postChatStream({
          url: '/api/chat/message/stream',
          body: { message: 'hi' },
          fetchImpl,
        }),
      ),
    ).rejects.toMatchObject({
      name: 'SSEHttpError',
      status: 200,
    });
  });
});
