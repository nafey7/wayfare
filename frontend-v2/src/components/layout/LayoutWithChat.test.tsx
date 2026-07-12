import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import uiReducer from '@/store/slices/uiSlice';
import chatReducer from '@/store/slices/chatSlice';
import authReducer from '@/store/slices/authSlice';

const mockIsMobile = vi.hoisted(() => vi.fn(() => false));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return { ...actual, useMediaQuery: mockIsMobile };
});

vi.mock('./MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));
vi.mock('./ContentPanel', () => ({
  ContentPanel: () => <div data-testid="content-panel" />,
}));
vi.mock('@/features/chat', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/chat')>();
  return { ...actual, ChatPanel: () => <div data-testid="chat-panel" /> };
});
vi.mock('@/features/chat/components/ChatSheet', () => ({
  ChatSheet: () => <div data-testid="chat-sheet" />,
}));
vi.mock('@/features/chat/components/ConversationSidebar', () => ({
  ConversationSidebar: () => <div data-testid="conversation-sidebar" />,
}));
vi.mock('@/features/chat/hooks/useConversations', () => ({
  useConversations: () => ({
    conversations: [],
    conversationsLoaded: true,
    chatId: null,
    switchConversation: vi.fn(),
    createNewConversation: vi.fn(),
    renameConversation: vi.fn(),
    deleteConversation: vi.fn(),
  }),
}));
vi.mock('@/features/chat/utils/publicChatSignupIntent', () => ({
  clearPublicChatPendingCompleteRegistration: vi.fn(),
}));

import { LayoutWithChat } from './LayoutWithChat';

interface StoreOverrides {
  sidebarOpen?: boolean;
  isAuthenticated?: boolean;
}

function makeStore({ sidebarOpen = false, isAuthenticated = false }: StoreOverrides = {}) {
  const initialUi = uiReducer(undefined, { type: 'init' });
  const initialChat = chatReducer(undefined, { type: 'init' });
  const initialAuth = authReducer(undefined, { type: 'init' });
  return configureStore({
    reducer: { ui: uiReducer, chat: chatReducer, auth: authReducer },
    preloadedState: {
      ui: initialUi,
      chat: { ...initialChat, conversationSidebarOpen: sidebarOpen },
      auth: { ...initialAuth, isAuthenticated },
    },
  });
}

function renderLayout(overrides: StoreOverrides = {}, pathname = '/chat') {
  const store = makeStore(overrides);
  render(
    <Provider store={store}>
      <MantineProvider theme={mantineTheme}>
        <MemoryRouter initialEntries={[pathname]}>
          <LayoutWithChat />
        </MemoryRouter>
      </MantineProvider>
    </Provider>
  );
  return store;
}

describe('LayoutWithChat — ESC key guard', () => {
  beforeEach(() => {
    mockIsMobile.mockReturnValue(false);
    vi.clearAllMocks();
  });

  it('closes the drawer when ESC is pressed', () => {
    const store = renderLayout({ sidebarOpen: true, isAuthenticated: true });
    expect(store.getState().chat.conversationSidebarOpen).toBe(true);

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });

    expect(store.getState().chat.conversationSidebarOpen).toBe(false);
  });

  it('does not close the drawer when ESC is already defaultPrevented', () => {
    // Simulate a nested modal that owns the ESC key by dispatching from a child
    // element whose own keydown listener calls preventDefault() — the event then
    // bubbles up to the document handler in LayoutWithChat with defaultPrevented=true.
    const store = renderLayout({ sidebarOpen: true, isAuthenticated: true });

    const inner = document.createElement('div');
    document.body.appendChild(inner);
    inner.addEventListener('keydown', (e) => e.preventDefault());

    act(() => {
      inner.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
      );
    });

    document.body.removeChild(inner);
    expect(store.getState().chat.conversationSidebarOpen).toBe(true);
  });

  it('restores focus to the hamburger button after ESC dismisses the drawer', () => {
    renderLayout({ sidebarOpen: true, isAuthenticated: true });
    const hamburger = screen.getByRole('button', { name: /open conversations/i });

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });

    expect(document.activeElement).toBe(hamburger);
  });
});
