import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { makeTestStore } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { setChatId, clearMessages } from '@/store/slices/chatSlice';
import { chatApi } from '@/api/chatApi';
import type { AuthCredentials } from '@/types/auth';

import { useChatHistoryLoader } from './useChatHistoryLoader';

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

describe('useChatHistoryLoader', () => {
  let testStore: ReturnType<typeof makeTestStore>;
  let initiateSpy: ReturnType<typeof vi.spyOn>;

  function makeWrapper() {
    return function Wrapper({ children }: { children: ReactNode }) {
      return <Provider store={testStore}>{children}</Provider>;
    };
  }

  beforeEach(() => {
    testStore = makeTestStore();
    // Stub the RTK Query thunk so we don't hit the network. Returns a
    // thenable matching the .unwrap() chain used by the hook.
    initiateSpy = vi.spyOn(chatApi.endpoints.getChatHistory, 'initiate');
    initiateSpy.mockImplementation((() => {
      // Redux thunk middleware invokes the action with (dispatch, getState)
      // and returns its result. We return an object with `.unwrap` so the
      // hook's `dispatch(initiate(...)).unwrap()` chain resolves.
      const thunkAction = () => ({
        unwrap: () => Promise.resolve({ messages: [] }),
      });
      return thunkAction;
    }) as unknown as typeof chatApi.endpoints.getChatHistory.initiate);
  });

  afterEach(() => {
    initiateSpy.mockRestore();
  });

  it('refetches history when the user goes chat A → New Chat → chat A again', async () => {
    testStore.dispatch(setCredentials(makeCredentials()));

    const { rerender } = renderHook(
      ({ chatId }: { chatId: string | null }) =>
        useChatHistoryLoader({ isAuthenticated: true, chatId }),
      {
        wrapper: makeWrapper(),
        initialProps: { chatId: 'conv-A' as string | null },
      }
    );

    // Initial open of conv-A: history fetched once.
    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).toHaveBeenCalledTimes(1);
    expect(initiateSpy).toHaveBeenLastCalledWith({ chatId: 'conv-A', limit: 50 });

    // User hits "New Chat" → chatId clears. No fetch should happen.
    act(() => {
      testStore.dispatch(setChatId(null));
    });
    rerender({ chatId: null });
    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).toHaveBeenCalledTimes(1);

    // User clicks the original conversation again. The sidebar handler
    // dispatches clearMessages() before setting chatId, so Redux messages
    // are empty here. History must refetch — without the null-tracking fix
    // this stayed at 1 and the chat panel rendered blank.
    act(() => {
      testStore.dispatch(clearMessages());
      testStore.dispatch(setChatId('conv-A'));
    });
    rerender({ chatId: 'conv-A' });
    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).toHaveBeenCalledTimes(2);
    expect(initiateSpy).toHaveBeenLastCalledWith({ chatId: 'conv-A', limit: 50 });
  });

  it('does not refetch when chatId stays the same across renders', async () => {
    testStore.dispatch(setCredentials(makeCredentials()));

    const { rerender } = renderHook(
      ({ chatId }: { chatId: string | null }) =>
        useChatHistoryLoader({ isAuthenticated: true, chatId }),
      {
        wrapper: makeWrapper(),
        initialProps: { chatId: 'conv-A' as string | null },
      }
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).toHaveBeenCalledTimes(1);

    rerender({ chatId: 'conv-A' });
    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).toHaveBeenCalledTimes(1);
  });

  it('skips fetch when Redux already has live messages for the chat', async () => {
    testStore.dispatch(setCredentials(makeCredentials()));
    // Simulate the just-sent-first-message state: messages already populated.
    testStore.dispatch({
      type: 'chat/setMessages',
      payload: [
        {
          id: 'm1',
          text: 'hi',
          sender: 'user',
          timestamp: new Date().toISOString(),
          type: 'message',
        },
      ],
    });

    renderHook(
      () => useChatHistoryLoader({ isAuthenticated: true, chatId: 'conv-A' }),
      { wrapper: makeWrapper() }
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(initiateSpy).not.toHaveBeenCalled();
  });
});
