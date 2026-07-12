import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { FlightInfo } from '@/types/api.helpers';
import type { ChatMessage } from '@/types/chat';
import { store } from '@/store';
import { clearAuth, setCredentials } from '@/store/slices/authSlice';
import { closeAuthModal } from '@/store/slices/uiSlice';
import type { AuthCredentials } from '@/types/auth';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/test/stubChatContextValue';
import { setCachedFlightResults, clearCachedFlightResults } from '@/store/slices/flightBookingSlice';
import { trackEvent } from '@/utils/gtm';
import { FlightResultMessage } from './FlightResultMessage';

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Avoid `importOriginal` for @mui/icons-material — spreading the real package opens thousands
// of ESM files and can hit EMFILE. Stub only the barrel imports used by this render tree.
vi.mock('@mui/icons-material', () => ({
  __esModule: true,
  Flight: () => null,
  Savings: () => null,
  ThumbUp: () => null,
  Bolt: () => null,
}));

const mediaQueryState = vi.hoisted(() => ({ isMdUp: true }));
vi.mock('@/hooks/useIsMdUp', () => ({
  useIsMdUp: () => mediaQueryState.isMdUp,
}));

const minimalFlight = (id: string): FlightInfo =>
  ({
    id,
    departure_time: '10:00',
    departure_date: '2026-04-01',
    arrival_time: '12:00',
    arrival_date: '2026-04-01',
    origin_code: 'LHR',
    destination_code: 'JFK',
    duration: '2h',
    duration_minutes: 120,
    stops: 0,
    price: 100,
    currency: 'USD',
    airline: 'BA',
    airline_code: 'BA',
  }) as FlightInfo;

const categoriesWithOneEach = {
  cheapest: { label: 'Cheapest', flights: [minimalFlight('c')] },
  fastest: { label: 'Fastest', flights: [minimalFlight('f')] },
  best_value: { label: 'Best Value', flights: [minimalFlight('b')] },
};

const tripSearchParams = {
  origin: 'LHR',
  destination: 'BCN',
  departure_date: '2026-04-01',
  return_date: null as string | null,
  journey_type: 'Circle' as const,
  passengers: { adults: 1, children: 0, infants: 0 },
};

function makeMulticityFlightMessage(): ChatMessage {
  return {
    _id: 'fm-mc',
    from: 'bot',
    type: 'multicity_flight_search_results',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    content: { messages: [{ text: 'Multi-city options LHR–BCN–LHR.' }] },
    extraData: {
      data: {
        search_params: tripSearchParams,
        multicity_parallel: true,
        multicity_legs: [
          {
            leg_index: 0,
            origin: 'LHR',
            destination: 'BCN',
            departure_date: '2026-04-01',
            session_id: 'sess-a',
            summary: { total_flights: 3, direct_count: 1, price_range: { min: 50, max: 200, currency: 'USD' } },
            categories: categoriesWithOneEach,
          },
          {
            leg_index: 1,
            origin: 'BCN',
            destination: 'LHR',
            departure_date: '2026-04-10',
            session_id: 'sess-b',
            summary: { total_flights: 2, direct_count: 0, price_range: { min: 60, max: 180, currency: 'USD' } },
            categories: categoriesWithOneEach,
          },
        ],
      },
    },
  };
}

function makeDateRangeFlightMessage(): ChatMessage {
  return {
    _id: 'fm-dr',
    from: 'bot',
    type: 'flight_date_range_results',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    content: { messages: [{ text: 'Flexible dates for LHR–JFK.' }] },
    extraData: {
      data: {
        dates: [
          {
            date: '2026-06-01',
            available: true,
            session_id: 'dr-sess-1',
            summary: {
              total_flights: 3,
              direct_count: 1,
              price_range: { min: 100, max: 500, currency: 'USD' },
            },
            categories: categoriesWithOneEach,
          },
        ],
        overall: { cheapest: null, fastest: null, best_value: null },
        searched_from: '2026-06-01',
        searched_to: '2026-06-07',
        has_more: false,
      },
    },
  };
}

function makeFlightMessage(): ChatMessage {
  return {
    _id: 'fm-1',
    from: 'bot',
    type: 'flight_search_results',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    content: {
      messages: [
        {
          text: 'I found flights LHR–JFK.\n\n### Best Value\n…',
        },
      ],
    },
    extraData: {
      data: {
        search_params: {
          origin: 'LHR',
          destination: 'JFK',
          departure_date: '2026-06-01',
          return_date: null,
          journey_type: 'OneWay',
          passengers: { adults: 1, children: 0, infants: 0 },
        },
        summary: {
          total_flights: 3,
          direct_count: 1,
          price_range: { min: 100, max: 500, currency: 'USD' },
        },
        categories: categoriesWithOneEach,
      },
      session_id: 'sess-1',
    },
  };
}

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

describe('FlightResultMessage', () => {
  beforeEach(() => {
    mediaQueryState.isMdUp = true;
    mockNavigate.mockClear();
    store.dispatch(clearAuth());
    store.dispatch(closeAuthModal());
  });

  it('navigates to public flight search when guest clicks View flights', async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <FlightResultMessage message={makeFlightMessage()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button', { name: /view flights/i }));
    expect(store.getState().ui.authModalOpen).toBe(false);
    expect(mockNavigate).toHaveBeenCalled();
    const [path] = mockNavigate.mock.calls[0]!;
    expect(path).toBe('/public/chat/flights/search');
  });

  it('navigates to flight search when authenticated user clicks View flights', async () => {
    store.dispatch(setCredentials(makeTestCredentials()));
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <FlightResultMessage message={makeFlightMessage()} />
      </TestWrapper>
    );
    await user.click(screen.getByRole('button', { name: /view flights/i }));
    expect(store.getState().ui.authModalOpen).toBe(false);
    expect(mockNavigate).toHaveBeenCalled();
    const [path, opts] = mockNavigate.mock.calls[0]!;
    expect(path).toBe('/flights/search');
    expect(opts).toMatchObject({
      state: expect.objectContaining({ fromChat: true }),
    });
  });

  describe('mobile viewport (below md)', () => {
    beforeEach(() => {
      mediaQueryState.isMdUp = false;
    });

    it('renders View flights CTA without inline panel for single-city results', () => {
      render(
        <TestWrapper>
          <FlightResultMessage message={makeFlightMessage()} />
        </TestWrapper>
      );
      expect(screen.getByRole('button', { name: /view flights/i })).toBeInTheDocument();
      expect(
        screen.queryByRole('tablist', { name: /flight options/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('tablist', { name: /multi-city legs/i })
      ).not.toBeInTheDocument();
    });

    it('renders View flights CTA without inline panel for multi-city results', () => {
      render(
        <TestWrapper>
          <FlightResultMessage message={makeMulticityFlightMessage()} />
        </TestWrapper>
      );
      expect(screen.getByRole('button', { name: /view flights/i })).toBeInTheDocument();
      expect(
        screen.queryByRole('tablist', { name: /multi-city legs/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('tablist', { name: /flight options/i })
      ).not.toBeInTheDocument();
    });

    it('renders View flights CTA without inline panel for date-range results', () => {
      render(
        <TestWrapper>
          <FlightResultMessage message={makeDateRangeFlightMessage()} />
        </TestWrapper>
      );
      expect(screen.getByRole('button', { name: /view flights/i })).toBeInTheDocument();
      expect(
        screen.queryByRole('tablist', { name: /flight options/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('history messages (_isFromHistory: true)', () => {
    function makeHistoryFlightMessage(): ChatMessage {
      const base = makeFlightMessage();
      return {
        ...base,
        extraData: { ...(base.extraData as object), _isFromHistory: true },
      };
    }

    function makeHistoryMulticityFlightMessage(): ChatMessage {
      const base = makeMulticityFlightMessage();
      return {
        ...base,
        extraData: { ...(base.extraData as object), _isFromHistory: true },
      };
    }

    it('clears stale cached results before navigating (does NOT hydrate cache)', async () => {
      store.dispatch(setCredentials(makeTestCredentials()));
      // Seed a stale cache so we can assert it gets cleared (history → fresh-search path)
      store.dispatch(
        setCachedFlightResults({
          data: { fareItineraries: [{ id: 'stale' }] } as never,
          params: { from: 'STALE', to: 'STALE', date: null } as never,
        })
      );
      expect(store.getState().flightBooking.cachedFlightResults).not.toBeNull();

      const user = userEvent.setup();
      render(
        <TestWrapper>
          <FlightResultMessage message={makeHistoryFlightMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view flights/i }));

      // History branch calls clearCachedFlightResults — cache must be empty
      expect(store.getState().flightBooking.cachedFlightResults).toBeNull();
      // But search-form params are still hydrated from the history payload
      expect(store.getState().flightBooking.searchFormParams.from).toBe('LHR');
      expect(store.getState().flightBooking.searchFormParams.to).toBe('JFK');
      expect(mockNavigate).toHaveBeenCalledWith(
        '/flights/search',
        expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
      );
    });

    it('tags the chat_view_flights_clicked GTM event with is_history: true', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <FlightResultMessage message={makeHistoryFlightMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view flights/i }));
      expect(trackEvent).toHaveBeenCalledWith(
        'chat_view_flights_clicked',
        expect.objectContaining({ is_history: true, result_type: 'flight_search_results' })
      );
    });

    it('non-history (live) clicks tag the GTM event with is_history: false', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <FlightResultMessage message={makeFlightMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view flights/i }));
      expect(trackEvent).toHaveBeenCalledWith(
        'chat_view_flights_clicked',
        expect.objectContaining({ is_history: false })
      );
    });

    it('multi-city history click clears stale cache and navigates with multi-city tripType', async () => {
      store.dispatch(setCredentials(makeTestCredentials()));
      store.dispatch(
        setCachedFlightResults({
          data: { fareItineraries: [{ id: 'stale' }] } as never,
          params: { from: 'STALE' } as never,
        })
      );
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <FlightResultMessage message={makeHistoryMulticityFlightMessage()} />
        </TestWrapper>
      );
      await user.click(screen.getByRole('button', { name: /view flights/i }));
      expect(store.getState().flightBooking.cachedFlightResults).toBeNull();
      expect(store.getState().flightBooking.searchFormParams.tripType).toBe('multi-city');
      expect(mockNavigate).toHaveBeenCalledWith(
        '/flights/search',
        expect.objectContaining({ state: expect.objectContaining({ fromChat: true }) })
      );
    });

    describe('mobile viewport (below md) with history message', () => {
      beforeEach(() => {
        mediaQueryState.isMdUp = false;
        store.dispatch(clearCachedFlightResults());
      });

      it('falls through to button-only view (no inline panel) for history messages', () => {
        render(
          <TestWrapper>
            <FlightResultMessage message={makeHistoryFlightMessage()} />
          </TestWrapper>
        );
        // History messages skip the mobile inline-panel branch — the CTA must
        // remain present so the user can re-run the search.
        expect(screen.getByRole('button', { name: /view flights/i })).toBeInTheDocument();
      });
    });
  });
});
