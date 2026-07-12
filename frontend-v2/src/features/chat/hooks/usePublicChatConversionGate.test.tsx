import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { store } from '@/store';
import { clearAuth, setCredentials } from '@/store/slices/authSlice';
import { closeAuthModal } from '@/store/slices/uiSlice';
import type { AuthCredentials } from '@/types/auth';
import { usePublicChatConversionGate } from './usePublicChatConversionGate';
import { PUBLIC_CHAT_CONVERSION_INTENT_KEY } from '@/features/chat/utils/publicChatSession';
import { ROUTES } from '@/features/routing';

const RETURN_TO_KEY = 'voya_public_chat_return_to';

function makeTestCredentials(): AuthCredentials {
  return {
    accessToken: 'test-access-token',
    refreshToken: 'test-refresh-token',
    tokenType: 'bearer',
    expiresIn: 3600,
    sessionId: 'sess-1',
    isNew: false,
    user: {
      id: 'u1',
      email: 't@example.com',
      firstName: 'T',
      lastName: 'User',
      emailVerified: true,
      createdAt: '',
      updatedAt: '',
    },
  };
}

function createWrapper(initialPath = '/') {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialPath]}>
        <Provider store={store}>{children}</Provider>
      </MemoryRouter>
    );
  };
}

describe('usePublicChatConversionGate', () => {
  beforeEach(() => {
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
    localStorage.removeItem(RETURN_TO_KEY);
    localStorage.removeItem(PUBLIC_CHAT_CONVERSION_INTENT_KEY);
  });

  it('returns true and does not open auth when authenticated', () => {
    store.dispatch(setCredentials(makeTestCredentials()));
    const { result } = renderHook(() => usePublicChatConversionGate(), {
      wrapper: createWrapper(),
    });
    let ok = false;
    act(() => {
      ok = result.current.ensureAuthenticated('itinerary_view');
    });
    expect(ok).toBe(true);
    expect(store.getState().ui.authModalOpen).toBe(false);
  });

  it('returns false, opens auth modal, and stores intent when guest', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const { result } = renderHook(() => usePublicChatConversionGate(), {
      wrapper: createWrapper(),
    });
    let ok = true;
    act(() => {
      ok = result.current.ensureAuthenticated('flight_book_now');
    });
    expect(ok).toBe(false);
    expect(store.getState().ui.authModalOpen).toBe(true);
    expect(setItem).toHaveBeenCalledWith(
      PUBLIC_CHAT_CONVERSION_INTENT_KEY,
      'flight_book_now'
    );
    setItem.mockRestore();
  });

  it('stores conversion intent and return-to when guest is on a public chat content route', () => {
    const { result } = renderHook(() => usePublicChatConversionGate(), {
      wrapper: createWrapper(ROUTES.PUBLIC_CHAT_FLIGHTS_SEARCH),
    });
    act(() => {
      result.current.ensureAuthenticated('flight_book_now');
    });
    expect(localStorage.getItem(PUBLIC_CHAT_CONVERSION_INTENT_KEY)).toBe('flight_book_now');
    const raw = localStorage.getItem(RETURN_TO_KEY);
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!)).toMatchObject({
      path: ROUTES.FLIGHTS_SEARCH,
    });
  });
});
