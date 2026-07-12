import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';

import { makeTestStore } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { selectAuthModalOpen } from '@/store/slices/uiSlice';
import { useGuestNewConversationGuard } from './useGuestNewConversationGuard';

const getPublicChatId = vi.fn<() => string | null>();
const clearGuestItineraries = vi.fn();

vi.mock('@/features/chat/utils/publicChatSession', () => ({
  getPublicChatId: () => getPublicChatId(),
}));

vi.mock('@/features/chat/utils/guestItineraries', () => ({
  clearGuestItineraries: () => clearGuestItineraries(),
}));

describe('useGuestNewConversationGuard', () => {
  let testStore: ReturnType<typeof makeTestStore>;

  function wrapper({ children }: { children: ReactNode }) {
    return <Provider store={testStore}>{children}</Provider>;
  }

  function authenticate() {
    testStore.dispatch(
      setCredentials({
        accessToken: 'tok',
        refreshToken: 'rtok',
        tokenType: 'bearer',
        expiresIn: 3600,
        sessionId: 's1',
        isNew: false,
        user: {
          id: 'u1',
          email: 'a@b.com',
          firstName: 'A',
          lastName: 'B',
          emailVerified: true,
          createdAt: '',
          updatedAt: '',
        },
      }),
    );
  }

  beforeEach(() => {
    testStore = makeTestStore();
    getPublicChatId.mockReset();
    clearGuestItineraries.mockReset();
  });

  it('runs the action immediately when user is authenticated', () => {
    authenticate();
    getPublicChatId.mockReturnValue('chat-1');

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });
    const action = vi.fn();

    act(() => {
      result.current.requestNewConversation(action);
    });

    expect(action).toHaveBeenCalledTimes(1);
    expect(result.current.dialogProps.open).toBe(false);
  });

  it('runs the action immediately when guest has no active chat', () => {
    getPublicChatId.mockReturnValue(null);

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });
    const action = vi.fn();

    act(() => {
      result.current.requestNewConversation(action);
    });

    expect(action).toHaveBeenCalledTimes(1);
    expect(result.current.dialogProps.open).toBe(false);
  });

  it('opens the dialog and defers the action when guest has an active chat', () => {
    getPublicChatId.mockReturnValue('chat-1');

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });
    const action = vi.fn();

    act(() => {
      result.current.requestNewConversation(action);
    });

    expect(action).not.toHaveBeenCalled();
    expect(result.current.dialogProps.open).toBe(true);
  });

  it('Save chat dispatches openAuthModal, drops pending action and closes the dialog', () => {
    getPublicChatId.mockReturnValue('chat-1');

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });
    const action = vi.fn();

    act(() => {
      result.current.requestNewConversation(action);
    });
    act(() => {
      result.current.dialogProps.onSaveChat();
    });

    expect(action).not.toHaveBeenCalled();
    expect(clearGuestItineraries).not.toHaveBeenCalled();
    expect(result.current.dialogProps.open).toBe(false);
    expect(selectAuthModalOpen(testStore.getState())).toBe(true);
  });

  it('Proceed anyway clears guest itineraries then runs the pending action', () => {
    getPublicChatId.mockReturnValue('chat-1');
    const calls: string[] = [];
    clearGuestItineraries.mockImplementation(() => calls.push('clear'));
    const action = vi.fn(() => calls.push('action'));

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });

    act(() => {
      result.current.requestNewConversation(action);
    });
    act(() => {
      result.current.dialogProps.onProceed();
    });

    expect(clearGuestItineraries).toHaveBeenCalledTimes(1);
    expect(action).toHaveBeenCalledTimes(1);
    expect(calls).toEqual(['clear', 'action']);
    expect(result.current.dialogProps.open).toBe(false);
  });

  it('Cancel/close drops the pending action without dispatching anything', () => {
    getPublicChatId.mockReturnValue('chat-1');

    const { result } = renderHook(() => useGuestNewConversationGuard(), { wrapper });
    const action = vi.fn();

    act(() => {
      result.current.requestNewConversation(action);
    });
    act(() => {
      result.current.dialogProps.onClose();
    });

    expect(action).not.toHaveBeenCalled();
    expect(clearGuestItineraries).not.toHaveBeenCalled();
    expect(selectAuthModalOpen(testStore.getState())).toBe(false);
    expect(result.current.dialogProps.open).toBe(false);
  });
});
