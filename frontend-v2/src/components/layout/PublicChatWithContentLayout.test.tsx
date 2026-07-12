import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import uiReducer from '@/store/slices/uiSlice';

// Stub heavy layout components so the layout shell is isolatable.
vi.mock('./MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));
vi.mock('./ContentPanel', () => ({
  ContentPanel: () => <div data-testid="content-panel" />,
}));
// Spread `importActual` so any other barrel export (ChatProvider, useChatContext, etc.)
// remains functional if a future dependency pulls it in transitively.
vi.mock('@/features/chat', async (importActual) => {
  const actual = await importActual<typeof import('@/features/chat')>();
  return {
    ...actual,
    ChatPanel: () => <div data-testid="chat-panel" />,
    ChatSheet: () => <div data-testid="chat-sheet" />,
  };
});
vi.mock('@/features/auth/components/AuthModal', () => ({
  AuthModal: () => null,
}));
vi.mock('@/features/chat/context/useChatContext', () => ({
  useChatContext: () => ({ openChat: vi.fn() }),
}));

import { PublicChatWithContentLayout } from './PublicChatWithContentLayout';

function makeStore() {
  return configureStore({ reducer: { ui: uiReducer } });
}

function renderLayout(pathname: string) {
  // Tests assert DOM presence, not visual visibility. The ChatSheet stub always
  // renders a <div>; the real ChatSheet's own useMediaQuery gate is bypassed by
  // the mock above. The MantineProvider viewport here verifies layout wiring,
  // not whether ChatSheet is visible at a given breakpoint.
  return render(
    <Provider store={makeStore()}>
      <MantineProvider theme={mantineTheme}>
        <MemoryRouter initialEntries={[pathname]}>
          <PublicChatWithContentLayout />
        </MemoryRouter>
      </MantineProvider>
    </Provider>
  );
}

describe('PublicChatWithContentLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('standalone /public/chat (index)', () => {
    it('renders ChatPanel', () => {
      renderLayout('/public/chat');
      expect(screen.getByTestId('chat-panel')).toBeDefined();
    });

    it('does NOT render ContentPanel', () => {
      renderLayout('/public/chat');
      expect(screen.queryByTestId('content-panel')).toBeNull();
    });

    it('does NOT render ChatSheet (chat is already full-width)', () => {
      renderLayout('/public/chat');
      expect(screen.queryByTestId('chat-sheet')).toBeNull();
    });
  });

  describe('content routes (flights, hotels, itinerary)', () => {
    const contentRoutes = [
      '/public/chat/flights/search',
      '/public/chat/hotels/search',
      '/public/chat/itinerary',
    ];

    contentRoutes.forEach((route) => {
      it(`renders ChatSheet on ${route}`, () => {
        renderLayout(route);
        expect(screen.getByTestId('chat-sheet')).toBeDefined();
      });

      it(`renders ContentPanel on ${route}`, () => {
        renderLayout(route);
        expect(screen.getByTestId('content-panel')).toBeDefined();
      });

      it(`renders ChatPanel on ${route}`, () => {
        renderLayout(route);
        expect(screen.getByTestId('chat-panel')).toBeDefined();
      });
    });
  });
});
