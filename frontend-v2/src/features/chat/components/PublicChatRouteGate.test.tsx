import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';

import chatReducer, { type ChatState } from '@/store/slices/chatSlice';
import { PublicChatRouteGate } from './PublicChatRouteGate';

const defaultConfig: ChatState['config'] = {
  chatFeedbackEnabled: false,
  publicChatEnabled: false,
  langgraphFlightsEnabled: false,
  langgraphHotelsEnabled: false,
  environment: 'development',
};

function makeStore(chat: Partial<ChatState>) {
  const { config: cfgOverride, ...rest } = chat;
  const initial: ChatState = {
    messages: [],
    chatId: null,
    loading: false,
    config: { ...defaultConfig, ...cfgOverride },
    configLoaded: false,
    feedbackSubmitted: {},
    conversations: [],
    conversationsLoaded: false,
    conversationSidebarOpen: true,
    streamingItinerary: { partial: null, active: false },
    ...rest,
  };
  return configureStore({
    reducer: { chat: chatReducer },
    preloadedState: { chat: initial },
  });
}

function renderGate(configLoaded: boolean, publicChatEnabled: boolean) {
  const store = makeStore({
    configLoaded,
    config: { ...defaultConfig, publicChatEnabled },
  });
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/public/chat']}>
        <MantineProvider theme={mantineTheme}>
          <Routes>
            <Route
              path="/public/chat"
              element={
                <PublicChatRouteGate>
                  <div data-testid="chat-child">Chat content</div>
                </PublicChatRouteGate>
              }
            />
            <Route path="/" element={<div data-testid="home">Home</div>} />
          </Routes>
        </MantineProvider>
      </MemoryRouter>
    </Provider>
  );
}

describe('PublicChatRouteGate', () => {
  it('shows loading when config is not loaded', () => {
    renderGate(false, true);
    expect(screen.getByLabelText('Loading chat')).toBeInTheDocument();
  });

  it('redirects to home when public chat is disabled', async () => {
    renderGate(true, false);
    expect(await screen.findByTestId('home')).toBeInTheDocument();
  });

  it('renders children when public chat is enabled', () => {
    renderGate(true, true);
    expect(screen.getByTestId('chat-child')).toBeInTheDocument();
  });
});
