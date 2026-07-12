import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { makeTestStore } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { setConversations } from '@/store/slices/chatSlice';
import type { AuthCredentials } from '@/types/auth';
import type { ConversationMeta } from '@/types/chat';
import { NEW_CHAT_PENDING_KEY } from './useStartNewChat';
import { useConversations } from './useConversations';

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('@/api', () => ({
  useListConversationsQuery: () => ({ data: undefined }),
  useRenameConversationMutation: () => [vi.fn()],
  useDeleteConversationMutation: () => [vi.fn()],
}));

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

const CONVERSATIONS: ConversationMeta[] = [
  {
    chat_id: 'conv-1',
    name: 'First conversation',
    message_count: 2,
    last_message_at: '2026-05-01T10:00:00Z',
    last_message_preview: 'Hello',
    created_at: '2026-05-01T09:00:00Z',
  },
];

describe('useConversations', () => {
  let testStore: ReturnType<typeof makeTestStore>;

  function makeWrapper(initialPath = '/chat') {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <Provider store={testStore}>
          <MemoryRouter initialEntries={[initialPath]}>{children}</MemoryRouter>
        </Provider>
      );
    };
  }

  beforeEach(() => {
    testStore = makeTestStore();
    sessionStorage.removeItem(NEW_CHAT_PENDING_KEY);
    navigateMock.mockReset();
  });

  it('skips auto-select and clears the flag when NEW_CHAT_PENDING_KEY is set', () => {
    testStore.dispatch(setCredentials(makeCredentials()));
    testStore.dispatch(setConversations(CONVERSATIONS));
    sessionStorage.setItem(NEW_CHAT_PENDING_KEY, '1');

    renderHook(() => useConversations(), { wrapper: makeWrapper() });

    expect(sessionStorage.getItem(NEW_CHAT_PENDING_KEY)).toBeNull();
    expect(testStore.getState().chat.chatId).toBeNull();
  });

  it('auto-selects the most recent conversation when no pending flag is set', () => {
    testStore.dispatch(setCredentials(makeCredentials()));
    testStore.dispatch(setConversations(CONVERSATIONS));

    renderHook(() => useConversations(), { wrapper: makeWrapper() });

    expect(testStore.getState().chat.chatId).toBe('conv-1');
  });

  it('createNewConversation navigates to /chat when invoked from a content route', () => {
    testStore.dispatch(setCredentials(makeCredentials()));
    testStore.dispatch(setConversations(CONVERSATIONS));

    const { result } = renderHook(() => useConversations(), {
      wrapper: makeWrapper('/itinerary/6a144417738a337a8b44130f'),
    });

    act(() => {
      result.current.createNewConversation();
    });

    expect(navigateMock).toHaveBeenCalledWith('/chat');
  });

  it('createNewConversation does not navigate when already on a chat route', () => {
    testStore.dispatch(setCredentials(makeCredentials()));
    testStore.dispatch(setConversations(CONVERSATIONS));

    const { result } = renderHook(() => useConversations(), {
      wrapper: makeWrapper('/chat'),
    });

    act(() => {
      result.current.createNewConversation();
    });

    expect(navigateMock).not.toHaveBeenCalled();
  });
});
