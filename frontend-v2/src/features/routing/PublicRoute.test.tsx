import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render as rtlRender, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';

function render(ui: React.ReactElement) {
  return rtlRender(<MantineProvider env="test">{ui}</MantineProvider>);
}

import authReducer from '@/store/slices/authSlice';
import type { AuthState } from '@/store/slices/authSlice';
import chatReducer from '@/store/slices/chatSlice';
import type { FrontendConfig } from '@/types/chat';
import { stashPublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';

import { PublicRoute } from './PublicRoute';
import { ROUTES } from './constants';

vi.mock('@/utils/devLog', () => ({
  devLog: vi.fn(),
}));

const PENDING_REGISTRATION_KEY = 'voya_public_chat_pending_complete_registration_v1';
const PUBLIC_CHAT_ROUTE_MESSAGED_KEY = 'voya_public_chat_route_user_messaged_v1';

const defaultChatConfig: FrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: false,
  langgraphFlightsEnabled: false,
  langgraphHotelsEnabled: false,
  environment: 'development',
};

function createStore(
  authenticated: boolean,
  options?: { publicChatEnabled?: boolean; configLoaded?: boolean }
) {
  const auth: AuthState = {
    user: null,
    token: authenticated ? 'test-token' : null,
    refreshToken: authenticated ? 'rt' : null,
    isAuthenticated: authenticated,
    loading: false,
    error: null,
  };
  const publicChatEnabled = options?.publicChatEnabled ?? false;
  const configLoaded = options?.configLoaded ?? false;
  return configureStore({
    reducer: { auth: authReducer, chat: chatReducer },
    preloadedState: {
      auth,
      chat: {
        messages: [],
        chatId: null,
        loading: false,
        config: { ...defaultChatConfig, publicChatEnabled },
        configLoaded,
        feedbackSubmitted: {},
        conversations: [],
        conversationsLoaded: false,
        conversationSidebarOpen: true,
        streamingItinerary: { partial: null, active: false },
      },
    },
  });
}

function ChatLocationProbe() {
  const { pathname, search } = useLocation();
  return (
    <span data-testid="chat-location">
      {pathname}
      {search}
    </span>
  );
}

describe('PublicRoute', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'localStorage',
      (() => {
        const m: Record<string, string> = {};
        return {
          getItem: (k: string) => m[k] ?? null,
          setItem: (k: string, v: string) => {
            m[k] = v;
          },
          removeItem: (k: string) => {
            delete m[k];
          },
          clear: () => {
            Object.keys(m).forEach((k) => delete m[k]);
          },
          length: 0,
          key: () => null,
        };
      })()
    );
  });

  it('renders children when not authenticated', () => {
    const store = createStore(false);
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat']}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicRoute>
                  <div>guest-chat</div>
                </PublicRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.getByText('guest-chat')).toBeInTheDocument();
  });

  it('redirects authenticated user from /public/chat to /chat when guest messaged there (localStorage flag)', () => {
    localStorage.setItem(PUBLIC_CHAT_ROUTE_MESSAGED_KEY, '1');
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat']}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicRoute>
                  <div>guest-chat</div>
                </PublicRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('guest-chat')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-shell')).toHaveTextContent('chat');
  });

  it('redirects authenticated user from /public/chat to home when guest did not message there', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat']}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicRoute>
                  <div>guest-chat</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
            <Route path="/chat" element={<div data-testid="chat-shell">chat</div>} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('guest-chat')).not.toBeInTheDocument();
    expect(screen.getByTestId('home')).toHaveTextContent('home');
  });

  it('redirects authenticated user with ?prompt= to /chat?prompt=', () => {
    const store = createStore(true);
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat?prompt=hello%20world']}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicRoute>
                  <div>guest-chat</div>
                </PublicRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.getByTestId('chat-location')).toHaveTextContent(
      '/chat?prompt=hello%20world'
    );
  });

  it('redirects authenticated user from /public/chat?prompt= to /chat without query when public chat is enabled', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat?prompt=hello']}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicRoute>
                  <div>guest-chat</div>
                </PublicRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.getByTestId('chat-location')).toHaveTextContent('/chat');
  });

  it('redirects authenticated user on / to home when public chat is off or config not loaded', () => {
    const store = createStore(true);
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route
              path="/"
              element={
                <PublicRoute>
                  <div>landing</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('landing')).not.toBeInTheDocument();
    expect(screen.getByTestId('home')).toHaveTextContent('home');
  });

  it('redirects authenticated user on / to home when public chat is enabled but guest did not message on /public/chat', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route
              path="/"
              element={
                <PublicRoute>
                  <div>landing</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('landing')).not.toBeInTheDocument();
    expect(screen.getByTestId('home')).toHaveTextContent('home');
  });

  it('redirects authenticated user on / to /chat when public chat is enabled and /public/chat message flag is set', () => {
    localStorage.setItem(PUBLIC_CHAT_ROUTE_MESSAGED_KEY, '1');
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route
              path="/"
              element={
                <PublicRoute>
                  <div>landing</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('landing')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent('/chat');
  });

  it('redirects authenticated user from /complete-registration to stashed return-to without intent flag', () => {
    stashPublicChatReturnTo('/flights/recommendations');
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[ROUTES.COMPLETE_REGISTRATION]}>
          <Routes>
            <Route
              path={ROUTES.COMPLETE_REGISTRATION}
              element={
                <PublicRoute>
                  <div>complete-registration</div>
                </PublicRoute>
              }
            />
            <Route
              path="/flights/recommendations"
              element={
                <div data-testid="flight-recs">
                  <ChatLocationProbe />
                  flights
                </div>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('complete-registration')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent('/flights/recommendations');
    expect(localStorage.getItem('voya_public_chat_return_to')).toBeNull();
  });

  it('redirects authenticated user from /complete-registration to stashed return-to when public chat is on and intent flag is set', () => {
    localStorage.setItem(PENDING_REGISTRATION_KEY, '1');
    stashPublicChatReturnTo('/flights/recommendations');
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[ROUTES.COMPLETE_REGISTRATION]}>
          <Routes>
            <Route
              path={ROUTES.COMPLETE_REGISTRATION}
              element={
                <PublicRoute>
                  <div>complete-registration</div>
                </PublicRoute>
              }
            />
            <Route
              path="/flights/recommendations"
              element={
                <div data-testid="flight-recs">
                  <ChatLocationProbe />
                  flights
                </div>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('complete-registration')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent(
      '/flights/recommendations'
    );
  });

  it('keeps /complete-registration children when handoff is set but no stashed path (no /chat Navigate — page navigates imperatively)', () => {
    localStorage.setItem(PENDING_REGISTRATION_KEY, '1');
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[ROUTES.COMPLETE_REGISTRATION]}>
          <Routes>
            <Route
              path={ROUTES.COMPLETE_REGISTRATION}
              element={
                <PublicRoute>
                  <div>complete-registration</div>
                </PublicRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <div data-testid="chat-shell">
                  <ChatLocationProbe />
                  chat
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.getByText('complete-registration')).toBeInTheDocument();
  });

  it('shows loading on /complete-registration when authenticated until config is loaded (avoids premature redirect)', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: false });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[ROUTES.COMPLETE_REGISTRATION]}>
          <Routes>
            <Route
              path={ROUTES.COMPLETE_REGISTRATION}
              element={
                <PublicRoute>
                  <div>complete-registration</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    expect(screen.queryByText('complete-registration')).not.toBeInTheDocument();
    expect(screen.queryByTestId('home')).not.toBeInTheDocument();
  });

  it('redirects authenticated user from /complete-registration to home when no funnel signals', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[ROUTES.COMPLETE_REGISTRATION]}>
          <Routes>
            <Route
              path={ROUTES.COMPLETE_REGISTRATION}
              element={
                <PublicRoute>
                  <div>complete-registration</div>
                </PublicRoute>
              }
            />
            <Route path={ROUTES.HOME} element={<div data-testid="home">home</div>} />
            <Route path="/chat" element={<div data-testid="chat-shell">chat</div>} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('complete-registration')).not.toBeInTheDocument();
    expect(screen.getByTestId('home')).toHaveTextContent('home');
  });

  it('redirects authenticated user from /public/chat/flights/recommendations to /flights/recommendations', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat/flights/recommendations']}>
          <Routes>
            <Route
              path="/public/chat/*"
              element={
                <PublicRoute>
                  <div>public-content</div>
                </PublicRoute>
              }
            />
            <Route
              path="/flights/recommendations"
              element={
                <div data-testid="flight-recs">
                  <ChatLocationProbe />
                  flights
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('public-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent(
      '/flights/recommendations'
    );
  });

  it('redirects authenticated user from /public/chat/hotels/search?q=abc to /hotels/search?q=abc', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat/hotels/search?q=abc']}>
          <Routes>
            <Route
              path="/public/chat/*"
              element={
                <PublicRoute>
                  <div>public-content</div>
                </PublicRoute>
              }
            />
            <Route
              path="/hotels/search"
              element={
                <div data-testid="hotel-search">
                  <ChatLocationProbe />
                  hotels
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('public-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent(
      '/hotels/search?q=abc'
    );
  });

  it('redirects authenticated user from /public/chat/itinerary to /itinerary', () => {
    const store = createStore(true, { publicChatEnabled: true, configLoaded: true });
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={['/public/chat/itinerary']}>
          <Routes>
            <Route
              path="/public/chat/*"
              element={
                <PublicRoute>
                  <div>public-content</div>
                </PublicRoute>
              }
            />
            <Route
              path="/itinerary"
              element={
                <div data-testid="itinerary">
                  <ChatLocationProbe />
                  itinerary
                </div>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
    expect(screen.queryByText('public-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-location')).toHaveTextContent('/itinerary');
  });
});
