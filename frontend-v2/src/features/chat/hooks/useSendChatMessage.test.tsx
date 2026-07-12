/**
 * Tests for ``useSendChatMessage`` — issue #1117 piece 4b.
 *
 * Covers the streaming chat hook's three jobs: drive the SSE endpoint,
 * dispatch ``itinerary_partial`` payloads to Redux, and fall back to
 * the non-streaming POST /chat/message when SSE is unavailable. The SSE
 * transport itself is exercised by ``sseChat.test.ts``; here we focus
 * on hook-level behavior and fallback semantics.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { chatApi } from '@/api/chatApi';
import { makeTestStore } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import {
  selectStreamingItinerary,
  clearStreamingItinerary,
} from '@/store/slices/chatSlice';
import type { AuthCredentials } from '@/types/auth';
import type { ChatResponse } from '@/types/chat';

import { useSendChatMessage } from './useSendChatMessage';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeCredentials(): AuthCredentials {
  return {
    accessToken: 'test-token',
    refreshToken: 'test-refresh',
    tokenType: 'bearer',
    expiresIn: 3600,
    sessionId: 'sess-1',
    isNew: false,
    user: {
      id: 'u1',
      email: 't@test.com',
      firstName: 'Test',
      lastName: 'User',
      emailVerified: true,
      createdAt: '',
      updatedAt: '',
    },
  };
}

/** Build a fake fetch impl whose response body streams the given SSE blocks. */
function streamingFetch(blocks: string[], status = 200): typeof fetch {
  const encoder = new TextEncoder();
  return vi.fn(async () => {
    const stream = new ReadableStream({
      start(controller) {
        for (const b of blocks) controller.enqueue(encoder.encode(b));
        controller.close();
      },
    });
    return new Response(stream, {
      status,
      headers: { 'Content-Type': 'text/event-stream' },
    });
  }) as unknown as typeof fetch;
}

function frame(event: string, data: unknown, id = 'evt-1'): string {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function ok(chatId = 'c-1'): ChatResponse {
  return {
    message: 'Done',
    message_id: 'm-1',
    chat_id: chatId,
    intent_name: 'general_query',
    confidence: 1,
    type: 'message',
    data: undefined,
    places_session_token: null,
  };
}

// ---------------------------------------------------------------------------
// Streaming happy path
// ---------------------------------------------------------------------------


describe('useSendChatMessage — streaming path', () => {
  let store: ReturnType<typeof makeTestStore>;

  function wrap({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }

  beforeEach(() => {
    store = makeTestStore();
    store.dispatch(setCredentials(makeCredentials()));
  });

  it('streams itinerary_partial events into Redux then returns the complete response', async () => {
    const fetchImpl = streamingFetch([
      frame('start', { chat_id: 'c-1' }, 'e1'),
      frame(
        'itinerary_partial',
        { itineraryItems: [{ day: 1, title: 'Arrival' }] },
        'e2',
      ),
      frame(
        'itinerary_partial',
        {
          itineraryItems: [
            { day: 1, title: 'Arrival', activities: [{ location: 'Hotel' }] },
          ],
        },
        'e3',
      ),
      frame('complete', ok('c-1'), 'e4'),
    ]);

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });

    // While iterating the stream, partials should land in Redux.
    // We sample state once `sendMessage` resolves; the streaming hook
    // clears the slot in its `finally`, so we observe the FINAL
    // partial here only if we hook the dispatch. Simpler: assert the
    // hook returned the final response, and that `clearStreamingItinerary`
    // ran (slot reset to {partial: null, active: false}).
    let response: ChatResponse | null = null;
    await act(async () => {
      response = await result.current.sendMessage(
        { message: 'plan a trip' },
        { fetchImpl },
      );
    });

    expect(response).toEqual(ok('c-1'));
    const slot = selectStreamingItinerary(store.getState());
    expect(slot).toEqual({ partial: null, active: false });
  });

  it('dispatches setStreamingItinerary on each itinerary_partial frame', async () => {
    const fetchImpl = streamingFetch([
      frame('start', { chat_id: 'c-1' }, 'e1'),
      frame(
        'itinerary_partial',
        { itineraryItems: [{ day: 1, title: 'Day One' }] },
        'e2',
      ),
      frame('complete', ok('c-1'), 'e3'),
    ]);

    // Spy on dispatch by watching the store directly. We block the
    // clear from running by stubbing the hook's finally — instead,
    // record dispatched actions as they happen.
    const dispatched: string[] = [];
    const origDispatch = store.dispatch;
    // @ts-expect-error — overriding for test instrumentation.
    store.dispatch = (action: unknown) => {
      if (typeof action === 'object' && action && 'type' in action) {
        dispatched.push((action as { type: string }).type);
      }
      return origDispatch(action as Parameters<typeof origDispatch>[0]);
    };

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });
    await act(async () => {
      await result.current.sendMessage({ message: 'hi' }, { fetchImpl });
    });

    expect(dispatched).toContain('chat/setStreamingItinerary');
    // clear fires in finally — partial always gets cleared.
    expect(dispatched).toContain('chat/clearStreamingItinerary');
  });

  it('throws an Error when the stream emits a terminal error event', async () => {
    const fetchImpl = streamingFetch([
      frame('start', { chat_id: 'c-1' }, 'e1'),
      frame(
        'error',
        { message: 'AI ran into a snag', error_class: 'transient_llm' },
        'e2',
      ),
    ]);

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });
    await act(async () => {
      await expect(
        result.current.sendMessage({ message: 'hi' }, { fetchImpl }),
      ).rejects.toThrow(/AI ran into a snag/);
    });
  });

  it('does NOT fall back to non-streaming when stream fails after partial frames arrived', async () => {
    // Review concern (#1126): the fallback used to fire on any
    // post-frame failure, but by that point the backend may have
    // already persisted the user message (and possibly bot messages),
    // so a fresh POST /chat/message would duplicate them — and the 5 s
    // dedupe window won't catch it for itinerary turns that take
    // 25-70 s. Gate fallback on ``framesReceived === 0``.
    //
    // Simulate: server emits two frames then the underlying stream
    // closes without a terminal event (e.g. server crashes, network
    // hard-fails). The hook should throw, NOT silently retry via the
    // non-streaming endpoint.
    const sseFetch = streamingFetch([
      frame('start', { chat_id: 'c-1' }, 'e1'),
      frame('progress', { node: 'dispatch_itinerary' }, 'e2'),
      // Stream closes here — no complete, no error event. Hook will
      // throw "SSE stream ended without complete or error event".
    ]);
    const fallbackSpy = vi
      .spyOn(chatApi.endpoints.sendMessage, 'initiate')
      .mockImplementation(((() => {
        throw new Error(
          'fallback must NOT be called when frames already arrived',
        );
      }) as unknown) as typeof chatApi.endpoints.sendMessage.initiate);

    try {
      const { result } = renderHook(() => useSendChatMessage(), {
        wrapper: wrap,
      });
      await act(async () => {
        await expect(
          result.current.sendMessage({ message: 'hi' }, { fetchImpl: sseFetch }),
        ).rejects.toThrow(/SSE stream ended without complete or error event/);
      });
      // Fallback was NOT called — verified by the spy never being
      // invoked (would have thrown the "must NOT be called" error).
      expect(fallbackSpy).not.toHaveBeenCalled();
    } finally {
      fallbackSpy.mockRestore();
    }
  });
});

// ---------------------------------------------------------------------------
// Fallback to non-streaming on 404 / 405
// ---------------------------------------------------------------------------


describe('useSendChatMessage — fallback path', () => {
  let store: ReturnType<typeof makeTestStore>;
  let initiateSpy: ReturnType<typeof vi.spyOn> | null = null;

  function wrap({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }

  beforeEach(() => {
    store = makeTestStore();
    store.dispatch(setCredentials(makeCredentials()));
  });

  afterEach(() => {
    initiateSpy?.mockRestore();
    initiateSpy = null;
  });

  /**
   * Spy on ``chatApi.endpoints.sendMessage.initiate`` so the fallback
   * path doesn't actually exercise RTK Query's ``fetchBaseQuery`` —
   * which calls ``new Request('/api/...')`` and fails in the test env
   * (undici's Request constructor requires absolute URLs even when
   * jsdom provides ``window.location``). In a real browser the same
   * relative URL works fine; the test-env limitation isn't something
   * we need to model here. We assert the call shape + return value
   * instead, which exercises the part of the hook we actually want
   * to verify.
   */
  function stubSendMessageMutation(response: ChatResponse): void {
    initiateSpy = vi
      .spyOn(chatApi.endpoints.sendMessage, 'initiate')
      .mockImplementation((() => {
        const thunk = (() => {
          const promise = Promise.resolve({
            data: response,
            requestId: 'r',
            isError: false,
          }) as Promise<unknown> & {
            unwrap: () => Promise<ChatResponse>;
            requestId: string;
            arg: unknown;
            abort: () => void;
            unsubscribe: () => void;
            reset: () => void;
          };
          promise.unwrap = () => Promise.resolve(response);
          promise.requestId = 'r';
          promise.arg = response;
          promise.abort = () => undefined;
          promise.unsubscribe = () => undefined;
          promise.reset = () => undefined;
          return promise;
        }) as unknown as ReturnType<
          typeof chatApi.endpoints.sendMessage.initiate
        >;
        return thunk;
      }) as unknown as typeof chatApi.endpoints.sendMessage.initiate);
  }

  it('falls back to POST /chat/message when stream returns 404', async () => {
    const realResponse = ok('c-fallback');
    stubSendMessageMutation(realResponse);

    const sseFetch = vi.fn(async () =>
      new Response('Not Found', { status: 404 }),
    ) as unknown as typeof fetch;

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });
    let response: ChatResponse | null = null;
    await act(async () => {
      response = await result.current.sendMessage(
        { message: 'plan a trip' },
        { fetchImpl: sseFetch },
      );
    });

    expect(response).toEqual(realResponse);
    // SSE attempt fired once; fallback mutation was invoked once.
    expect((sseFetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
    expect(initiateSpy).toHaveBeenCalledOnce();
    expect(initiateSpy).toHaveBeenCalledWith({ message: 'plan a trip' });
  });

  it('propagates 429 instead of falling back (lock-busy is a real failure)', async () => {
    const sseFetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          detail:
            'Another request is already processing for this conversation. ' +
            'Please wait for the previous request to complete.',
        }),
        {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    ) as unknown as typeof fetch;
    // Pre-stub the mutation; if the hook calls it we'll know via the spy.
    stubSendMessageMutation(ok('should-not-be-used'));

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });
    await act(async () => {
      await expect(
        result.current.sendMessage(
          { message: 'plan a trip' },
          { fetchImpl: sseFetch },
        ),
      ).rejects.toMatchObject({ status: 429 });
    });
    // Fallback was NOT invoked.
    expect(initiateSpy).not.toHaveBeenCalled();
  });

  it('clears streamingItinerary even when the SSE attempt errored before any event', async () => {
    // Pre-populate the slot so we can assert it gets cleared on failure.
    store.dispatch({
      type: 'chat/setStreamingItinerary',
      payload: { itineraryItems: [{ day: 1 }] },
    });

    const sseFetch = vi.fn(async () =>
      new Response('Not Found', { status: 404 }),
    ) as unknown as typeof fetch;
    stubSendMessageMutation(ok('c-1'));

    const { result } = renderHook(() => useSendChatMessage(), { wrapper: wrap });
    await act(async () => {
      await result.current.sendMessage(
        { message: 'plan a trip' },
        { fetchImpl: sseFetch },
      );
    });

    const slot = selectStreamingItinerary(store.getState());
    expect(slot).toEqual({ partial: null, active: false });
    // Explicit cleanup to avoid leaking state into other tests.
    store.dispatch(clearStreamingItinerary());
  });
});
