import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { makeTestStore } from '@/store';
import { selectChatId } from '@/store/slices/chatSlice';
import { useGuestChatClaim } from './useGuestChatClaim';

const claimMutation = vi.fn();

vi.mock('@/api', () => ({
  useClaimGuestChatMutation: () => [claimMutation, { isLoading: false }],
}));

const getSessionId = vi.fn();
const getChatId = vi.fn();
const clearSession = vi.fn();

vi.mock('@/features/chat/utils/publicChatSession', () => ({
  getPublicChatSessionId: () => getSessionId(),
  getPublicChatId: () => getChatId(),
  clearPublicChatSession: () => clearSession(),
}));

vi.mock('@/features/chat/utils/publicChatGuestTranscript', () => ({
  clearGuestChatTranscript: vi.fn(),
}));

describe('useGuestChatClaim', () => {
  let testStore: ReturnType<typeof makeTestStore>;

  function wrapper({ children }: { children: ReactNode }) {
    return <Provider store={testStore}>{children}</Provider>;
  }

  beforeEach(() => {
    testStore = makeTestStore();
    claimMutation.mockReset();
    getSessionId.mockReset();
    getChatId.mockReset();
    clearSession.mockReset();
  });

  function renderTheHook(args: {
    isAuthenticated: boolean;
    publicChatEnabled: boolean;
    configLoaded: boolean;
  }) {
    return renderHook(
      () =>
        useGuestChatClaim({
          dispatch: testStore.dispatch,
          isAuthenticated: args.isAuthenticated,
          publicChatEnabled: args.publicChatEnabled,
          configLoaded: args.configLoaded,
        }),
      { wrapper },
    );
  }

  it('does nothing when not authenticated', () => {
    getSessionId.mockReturnValue('sid');
    getChatId.mockReturnValue('cid');
    renderTheHook({ isAuthenticated: false, publicChatEnabled: true, configLoaded: true });
    expect(claimMutation).not.toHaveBeenCalled();
  });

  it('does nothing when there is no guest chat id', () => {
    getSessionId.mockReturnValue('sid');
    getChatId.mockReturnValue(null);
    renderTheHook({ isAuthenticated: true, publicChatEnabled: true, configLoaded: true });
    expect(claimMutation).not.toHaveBeenCalled();
  });

  it('fires claim mutation once on first authed render with guest keys', async () => {
    getSessionId.mockReturnValue('session-uuid');
    getChatId.mockReturnValue('guest-chat-id');
    claimMutation.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          status: 'claimed',
          chat_id: 'guest-chat-id',
          message_count: 2,
        }),
    });

    const { rerender } = renderTheHook({
      isAuthenticated: true,
      publicChatEnabled: true,
      configLoaded: true,
    });

    expect(claimMutation).toHaveBeenCalledTimes(1);
    expect(claimMutation).toHaveBeenCalledWith({
      body: { chat_id: 'guest-chat-id' },
      sessionId: 'session-uuid',
    });

    await waitFor(() => {
      expect(selectChatId(testStore.getState())).toBe('guest-chat-id');
    });
    expect(clearSession).toHaveBeenCalled();

    // Second render: ref-guard prevents a re-fire.
    rerender();
    expect(claimMutation).toHaveBeenCalledTimes(1);
  });

  it('on nothing_to_claim drops the stale chat id and clears guest keys', async () => {
    getSessionId.mockReturnValue('session-uuid');
    getChatId.mockReturnValue('orphan-chat-id');
    claimMutation.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          status: 'nothing_to_claim',
          chat_id: 'orphan-chat-id',
          message_count: 0,
        }),
    });

    renderTheHook({ isAuthenticated: true, publicChatEnabled: true, configLoaded: true });

    await waitFor(() => {
      expect(clearSession).toHaveBeenCalled();
    });
    expect(selectChatId(testStore.getState())).toBeNull();
  });

  it('on 4xx rejection nulls chat id and clears guest keys', async () => {
    getSessionId.mockReturnValue('session-uuid');
    getChatId.mockReturnValue('guest-chat-id');
    claimMutation.mockReturnValue({
      unwrap: () => Promise.reject({ status: 403, data: { detail: 'mismatch' } }),
    });

    renderTheHook({ isAuthenticated: true, publicChatEnabled: true, configLoaded: true });

    await waitFor(() => {
      expect(clearSession).toHaveBeenCalled();
    });
    expect(selectChatId(testStore.getState())).toBeNull();
  });

  it('on 5xx leaves guest keys in place', async () => {
    getSessionId.mockReturnValue('session-uuid');
    getChatId.mockReturnValue('guest-chat-id');
    claimMutation.mockReturnValue({
      unwrap: () => Promise.reject({ status: 500 }),
    });

    renderTheHook({ isAuthenticated: true, publicChatEnabled: true, configLoaded: true });

    await waitFor(() => {
      expect(claimMutation).toHaveBeenCalledTimes(1);
    });
    expect(clearSession).not.toHaveBeenCalled();
    expect(selectChatId(testStore.getState())).toBeNull();
  });
});
