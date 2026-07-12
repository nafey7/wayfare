import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { store } from '@/store';
import { clearAuth, setCredentials } from '@/store/slices/authSlice';
import { closeAuthModal } from '@/store/slices/uiSlice';
import type { AuthCredentials } from '@/types/auth';
import type { ChatMessage } from '@/types/chat';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { ROUTES } from '@/features/routing';
import { getStubChatContextValue } from '@/test/stubChatContextValue';
import { setCachedHotelResults, clearCachedHotelResults } from '@/store/slices/hotelBookingSlice';
import { trackEvent } from '@/utils/gtm';
import { HotelResultMessage } from './HotelResultMessage';

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Match HotelSearchResultsPanel's barrel icon imports (avoid loading the full icons package).
vi.mock('@mui/icons-material', () => ({
  __esModule: true,
  Savings: () => null,
  ThumbUp: () => null,
  Star: () => null,
  LocationOn: () => null,
}));

const mediaQueryState = vi.hoisted(() => ({ isMdUp: true }));
vi.mock('@/hooks/useIsMdUp', () => ({
  useIsMdUp: () => mediaQueryState.isMdUp,
}));

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

function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <Provider store={store}>
      <MemoryRouter>
        <MantineProvider theme={mantineTheme}>
          <ChatContext.Provider value={getStubChatContextValue()}>{children}</ChatContext.Provider>
        </MantineProvider>
      </MemoryRouter>
    </Provider>
  );
}

function makeHotelMessage(): ChatMessage {
  return {
    _id: 'hm-1',
    from: 'bot',
    type: 'hotel_search_results',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    content: { messages: [{ text: 'Hotel results' }] },
    extraData: {
      session_id: 'hotel-sess-1',
      data: {
        summary: { total_found: 3, nights: 2, price_range: { min: 100, currency: 'GBP' } },
        categories: {
          best_value: { hotels: [] },
          // At least one non-empty list so HotelSearchResultsPanel tabKeys is non-empty (panel returns null if all empty)
          cheapest: {
            hotels: [
              {
                hotel_id: 'h-test-1',
                token_id: 'tok-1',
                product_id: 'p-1',
                hotel_name: 'Stub Hotel',
                total_price: 100,
                currency: 'GBP',
              },
            ],
          },
          highest_rated: { hotels: [] },
        },
        search_params: {
          destination_city: 'Paris',
          check_in_date: '2026-06-01',
          check_out_date: '2026-06-03',
          adults: 2,
        },
      },
    },
  };
}

describe('HotelResultMessage conversion gate', () => {
  beforeEach(() => {
    mediaQueryState.isMdUp = true;
    mockNavigate.mockClear();
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
  });

  it('navigates to public hotel search when guest clicks View hotels', async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <HotelResultMessage message={makeHotelMessage()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button', { name: /view hotels/i }));
    expect(store.getState().ui.authModalOpen).toBe(false);
    expect(mockNavigate).toHaveBeenCalled();
    const [path] = mockNavigate.mock.calls[0]!;
    expect(path).toBe(ROUTES.PUBLIC_CHAT_HOTELS_SEARCH);
  });

  it('navigates to hotel search when authenticated user clicks View hotels', async () => {
    store.dispatch(setCredentials(makeTestCredentials()));
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <HotelResultMessage message={makeHotelMessage()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button', { name: /view hotels/i }));
    expect(store.getState().ui.authModalOpen).toBe(false);
    expect(store.getState().hotelBooking.cachedHotelResults).not.toBeNull();
    expect(store.getState().ui.lastHotelPath).toBe(ROUTES.HOTELS_SEARCH);
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.HOTELS_SEARCH, {
      state: expect.objectContaining({ fromChat: true }),
    });
  });

  it('shows summary text from structured extraData', () => {
    render(
      <TestWrapper>
        <HotelResultMessage message={makeHotelMessage()} />
      </TestWrapper>
    );
    expect(screen.getByText(/We found 3 hotels in Paris/)).toBeInTheDocument();
  });

  describe('mobile viewport (below md)', () => {
    beforeEach(() => {
      mediaQueryState.isMdUp = false;
    });

    it('renders View hotels CTA without inline hotel list', () => {
      render(
        <TestWrapper>
          <HotelResultMessage message={makeHotelMessage()} />
        </TestWrapper>
      );
      // Mobile now mirrors desktop: summary + CTA, no inline HotelSearchResultsPanel.
      expect(screen.getByRole('button', { name: /view hotels/i })).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /show all hotels/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('history messages (_isFromHistory: true)', () => {
    function makeHistoryHotelMessage(): ChatMessage {
      const base = makeHotelMessage();
      return {
        ...base,
        extraData: { ...(base.extraData as object), _isFromHistory: true },
      };
    }

    it('clears stale cached hotel results before navigating (does NOT hydrate cache)', async () => {
      store.dispatch(setCredentials(makeTestCredentials()));
      store.dispatch(
        setCachedHotelResults({
          data: { hotels: [{ id: 'stale' }] } as never,
          params: { destination: 'Stale City' } as never,
        })
      );
      expect(store.getState().hotelBooking.cachedHotelResults).not.toBeNull();

      const user = userEvent.setup();
      render(
        <TestWrapper>
          <HotelResultMessage message={makeHistoryHotelMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view hotels/i }));

      // History branch must clear the cache so HotelSearchPage triggers a fresh fetch.
      expect(store.getState().hotelBooking.cachedHotelResults).toBeNull();
      // Search-form params still hydrated from the history payload.
      expect(store.getState().hotelBooking.searchFormParams.destination).toBe('Paris');
      expect(mockNavigate).toHaveBeenCalledWith(
        ROUTES.HOTELS_SEARCH,
        expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
      );
    });

    it('tags chat_view_hotels_clicked GTM event with is_history: true for history messages', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <HotelResultMessage message={makeHistoryHotelMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view hotels/i }));
      expect(trackEvent).toHaveBeenCalledWith(
        'chat_view_hotels_clicked',
        expect.objectContaining({ is_history: true, result_type: 'hotel_search_results' })
      );
    });

    it('non-history (live) clicks tag GTM event with is_history: false', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <HotelResultMessage message={makeHotelMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view hotels/i }));
      expect(trackEvent).toHaveBeenCalledWith(
        'chat_view_hotels_clicked',
        expect.objectContaining({ is_history: false })
      );
    });

    describe('mobile viewport (below md) with history message', () => {
      beforeEach(() => {
        mediaQueryState.isMdUp = false;
        store.dispatch(clearCachedHotelResults());
      });

      it('falls through to button-only view (no inline panel) for history messages', () => {
        render(
          <TestWrapper>
            <HotelResultMessage message={makeHistoryHotelMessage()} />
          </TestWrapper>
        );
        // History messages skip the mobile inline-panel branch — the CTA must
        // remain present so the user can re-run the search.
        expect(screen.getByRole('button', { name: /view hotels/i })).toBeInTheDocument();
      });
    });
  });
});
