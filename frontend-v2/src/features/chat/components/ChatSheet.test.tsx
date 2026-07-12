import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import uiReducer from '@/store/slices/uiSlice';
import type { ChatStateValue } from '@/store/slices/uiSlice';
import chatReducer from '@/store/slices/chatSlice';

// Must be hoisted so vi.mock() picks them up at module resolution time.
const mockIsMobile = vi.hoisted(() => vi.fn(() => true));
const mockScrollHidden = vi.hoisted(() => vi.fn(() => false));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return {
    ...actual,
    useMediaQuery: mockIsMobile,
  };
});

vi.mock('@/hooks', () => ({
  useScrollDirectionHidden: mockScrollHidden,
}));

// Stub heavy ChatPanel — we only care about the ChatSheet shell.
vi.mock('./ChatPanel', () => ({ ChatPanel: () => <div data-testid="chat-panel" /> }));

// Stub useBottomSheet so tests aren't coupled to DOM geometry.
vi.mock('@/components/sheet/useBottomSheet', () => ({
  useBottomSheet: () => ({
    sheetRef: { current: null },
    sheetStyle: { position: 'absolute', bottom: 0, height: 44 },
    handleRef: { current: null },
    handleProps: {
      onClick: vi.fn(),
      onTouchStart: vi.fn(),
      onTouchEnd: vi.fn(),
      style: {},
    },
    listRef: { current: null },
  }),
}));

import { ChatSheet } from './ChatSheet';

function makeStore(chatState: ChatStateValue = 'resting') {
  const initial = uiReducer(undefined, { type: 'init' });
  const initialChat = chatReducer(undefined, { type: 'init' });
  return configureStore({
    reducer: { ui: uiReducer, chat: chatReducer },
    preloadedState: {
      ui: { ...initial, chatState },
      chat: initialChat,
    },
  });
}

interface RenderSheetOptions {
  isAuthenticated?: boolean;
  onOpenSidebar?: () => void;
  onNewChat?: () => void;
}

function renderSheet(chatState: ChatStateValue = 'resting', options: RenderSheetOptions = {}) {
  const store = makeStore(chatState);

  return render(
    <Provider store={store}>
      <MantineProvider theme={mantineTheme}>
        <ChatSheet {...options} />
      </MantineProvider>
    </Provider>
  );
}

describe('ChatSheet', () => {
  beforeEach(() => {
    mockIsMobile.mockReturnValue(true);
    mockScrollHidden.mockReturnValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns null on desktop (no pill, no panel rendered)', () => {
    mockIsMobile.mockReturnValue(false);
    renderSheet('resting');
    expect(screen.queryByText('Ask Voya…')).toBeNull();
    expect(screen.queryByTestId('chat-panel')).toBeNull();
    expect(screen.queryByRole('button', { name: /minimise/i })).toBeNull();
  });

  describe('resting state', () => {
    it('renders "Ask Voya…" pill', () => {
      renderSheet('resting');
      expect(screen.getByText('Ask Voya…')).toBeDefined();
    });

    it('does not render the drag handle header', () => {
      renderSheet('resting');
      expect(screen.queryByRole('button', { name: /minimise/i })).toBeNull();
    });

    it('does not render ChatPanel', () => {
      renderSheet('resting');
      expect(screen.queryByTestId('chat-panel')).toBeNull();
    });
  });

  describe('expanded (full) state', () => {
    it('renders the minimise button', () => {
      renderSheet('full');
      expect(screen.getByRole('button', { name: /minimise chat/i })).toBeDefined();
    });

    it('renders ChatPanel', () => {
      renderSheet('full');
      expect(screen.getByTestId('chat-panel')).toBeDefined();
    });

    it('does not render "Ask Voya…" pill', () => {
      renderSheet('full');
      expect(screen.queryByText('Ask Voya…')).toBeNull();
    });
  });

  describe('auth-gated header buttons (expanded sheet)', () => {
    it('renders hamburger and new-chat buttons when authenticated and callbacks supplied', () => {
      renderSheet('full', { isAuthenticated: true, onOpenSidebar: vi.fn(), onNewChat: vi.fn() });

      expect(screen.getByRole('button', { name: /open conversations/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /new chat/i })).toBeDefined();
    });

    it('fires onOpenSidebar when hamburger is clicked', async () => {
      const user = userEvent.setup();
      const onOpenSidebar = vi.fn();
      renderSheet('full', { isAuthenticated: true, onOpenSidebar, onNewChat: vi.fn() });

      await user.click(screen.getByRole('button', { name: /open conversations/i }));
      expect(onOpenSidebar).toHaveBeenCalledOnce();
    });

    it('fires onNewChat when new-chat button is clicked', async () => {
      const user = userEvent.setup();
      const onNewChat = vi.fn();
      renderSheet('full', { isAuthenticated: true, onOpenSidebar: vi.fn(), onNewChat });

      await user.click(screen.getByRole('button', { name: /new chat/i }));
      expect(onNewChat).toHaveBeenCalledOnce();
    });

    it('does not render header buttons when not authenticated', () => {
      renderSheet('full', { isAuthenticated: false, onOpenSidebar: vi.fn(), onNewChat: vi.fn() });

      expect(screen.queryByRole('button', { name: /open conversations/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /new chat/i })).toBeNull();
    });

    it('does not render header buttons when authenticated but callbacks are not supplied', () => {
      renderSheet('full', { isAuthenticated: true });

      expect(screen.queryByRole('button', { name: /open conversations/i })).toBeNull();
      expect(screen.queryByRole('button', { name: /new chat/i })).toBeNull();
    });
  });
});
