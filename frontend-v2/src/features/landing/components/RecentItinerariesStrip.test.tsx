import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Hoist mocks so they're defined before module imports
const mockNavigate = vi.hoisted(() => vi.fn());
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockGetItineraries = vi.hoisted(() => vi.fn(() => ({ data: undefined as any })));
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockGetGuestItineraries = vi.hoisted(() => vi.fn(() => [] as any));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/api/itinerariesApi', () => ({
  itinerariesApi: {},
  useGetItinerariesQuery: mockGetItineraries,
}));

vi.mock('@/features/chat/utils/guestItineraries', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/chat/utils/guestItineraries')>();
  return { ...actual, getGuestItineraries: mockGetGuestItineraries };
});

vi.mock('@/features/itinerary/components/AuthenticatedImage', () => ({
  AuthenticatedImage: ({ alt }: { alt: string }) => <img alt={alt} />,
}));

vi.mock('@mantine/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mantine/hooks')>();
  return { ...actual, useMediaQuery: () => true };
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import authReducer from '@/store/slices/authSlice';
import uiReducer from '@/store/slices/uiSlice';
import chatReducer from '@/store/slices/chatSlice';
import { baseApi } from '@/api/baseApi';
import { strapiApi } from '@/api/strapiApi';
import { RecentItinerariesStrip } from './RecentItinerariesStrip';
import { ROUTES } from '@/features/routing/constants';
import { itineraryView } from '@/features/routing';
import type { User } from '@/types/auth';
import type { SavedItinerary } from '@/types/itineraries';
import type { GuestItineraryEntry } from '@/features/chat/utils/guestItineraries';

const mockAuthUser: User = {
  id: '1',
  email: 'a@b.com',
  firstName: 'A',
  lastName: null,
  emailVerified: true,
  createdAt: '2024-01-01',
  updatedAt: '2024-01-01',
};

function makeStore(authenticated: boolean) {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      [strapiApi.reducerPath]: strapiApi.reducer,
      auth: authReducer,
      ui: uiReducer,
      chat: chatReducer,
    },
    preloadedState: {
      auth: {
        user: authenticated ? mockAuthUser : null,
        token: authenticated ? 'tok' : null,
        refreshToken: authenticated ? 'ref' : null,
        isAuthenticated: authenticated,
        loading: false,
        error: null,
      },
    },
    middleware: (gDM) => gDM().concat(baseApi.middleware, strapiApi.middleware),
  });
}

function renderStrip(authenticated: boolean, ui: ReactElement = <RecentItinerariesStrip />) {
  const store = makeStore(authenticated);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MantineProvider theme={mantineTheme}>
          <MemoryRouter>{ui}</MemoryRouter>
        </MantineProvider>
      </Provider>,
    ),
  };
}

const makeSavedItinerary = (overrides: Partial<SavedItinerary> = {}): SavedItinerary => ({
  id: 'it-1',
  structuredItinerary: { itineraryItems: [] },
  tripMeta: {
    destination: 'Barcelona',
    departureDate: '2025-07-01',
    returnDate: '2025-07-08',
    adults: 2,
  },
  createdAt: '2025-06-01T10:00:00Z',
  updatedAt: '2025-06-01T10:00:00Z',
  ...overrides,
});

const makeGuestEntry = (overrides: Partial<GuestItineraryEntry> = {}): GuestItineraryEntry => ({
  structuredItinerary: { itineraryItems: [] },
  tripMeta: {
    destination: 'Paris',
    departure_date: '2025-08-01',
    return_date: '2025-08-10',
    adults: 1,
  },
  createdAt: Date.now(),
  ...overrides,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
  vi.stubGlobal('sessionStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

// ─── Auth strip ──────────────────────────────────────────────────────────────

describe('AuthItinerariesStrip', () => {
  it('renders nothing when there are no itineraries', () => {
    mockGetItineraries.mockReturnValue({ data: [] });
    renderStrip(true);
    expect(screen.queryByText('Recent trips')).not.toBeInTheDocument();
  });

  it('renders nothing when query data is undefined', () => {
    mockGetItineraries.mockReturnValue({ data: undefined });
    renderStrip(true);
    expect(screen.queryByText('Recent trips')).not.toBeInTheDocument();
  });

  it('renders up to MAX_SHOWN (2) itineraries', () => {
    mockGetItineraries.mockReturnValue({
      data: [
        makeSavedItinerary({ id: 'it-1', tripMeta: { destination: 'Barcelona' }, createdAt: '2025-06-01T10:00:00Z' }),
        makeSavedItinerary({ id: 'it-2', tripMeta: { destination: 'Tokyo' }, createdAt: '2025-05-01T10:00:00Z' }),
        makeSavedItinerary({ id: 'it-3', tripMeta: { destination: 'NewYork' }, createdAt: '2025-04-01T10:00:00Z' }),
      ],
    });
    renderStrip(true);
    expect(screen.getByText('Barcelona')).toBeInTheDocument();
    expect(screen.getByText('Tokyo')).toBeInTheDocument();
    expect(screen.queryByText('NewYork')).not.toBeInTheDocument();
  });

  it('sorts by createdAt desc (newest first)', () => {
    mockGetItineraries.mockReturnValue({
      data: [
        makeSavedItinerary({ id: 'older', tripMeta: { destination: 'OlderCity' }, createdAt: '2025-01-01T00:00:00Z' }),
        makeSavedItinerary({ id: 'newer', tripMeta: { destination: 'NewerCity' }, createdAt: '2025-12-01T00:00:00Z' }),
      ],
    });
    renderStrip(true);
    // First card should be the heading "Recent trips" button, then card buttons
    const destinations = screen.getAllByText(/City/i).map((el) => el.textContent);
    expect(destinations[0]).toBe('NewerCity');
    expect(destinations[1]).toBe('OlderCity');
  });

  it('navigates to itineraryView(id) on card click', async () => {
    const user = userEvent.setup();
    mockGetItineraries.mockReturnValue({
      data: [makeSavedItinerary({ id: 'it-1', tripMeta: { destination: 'Barcelona' } })],
    });
    renderStrip(true);
    await user.click(screen.getByText('Barcelona'));
    expect(mockNavigate).toHaveBeenCalledWith(itineraryView('it-1'));
  });

  it('heading click navigates to ROUTES.ITINERARIES', async () => {
    const user = userEvent.setup();
    mockGetItineraries.mockReturnValue({
      data: [makeSavedItinerary({ id: 'it-1', tripMeta: { destination: 'Barcelona' } })],
    });
    renderStrip(true);
    await user.click(screen.getByText('Recent trips'));
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.ITINERARIES);
  });
});

// ─── Guest strip ──────────────────────────────────────────────────────────────

describe('GuestItinerariesStrip', () => {
  it('renders nothing when there are no guest itineraries', () => {
    mockGetGuestItineraries.mockReturnValue([]);
    renderStrip(false);
    expect(screen.queryByText('Recent trips')).not.toBeInTheDocument();
  });

  it('renders destination from tripMeta', () => {
    mockGetGuestItineraries.mockReturnValue([makeGuestEntry()]);
    renderStrip(false);
    expect(screen.getByText('Paris')).toBeInTheDocument();
  });

  it('renders gracefully when tripMeta is absent', () => {
    mockGetGuestItineraries.mockReturnValue([
      makeGuestEntry({ tripMeta: undefined }),
    ]);
    renderStrip(false);
    // Should still render "Recent trips" heading without crashing
    expect(screen.getByText('Recent trips')).toBeInTheDocument();
  });

  it('caps at MAX_SHOWN (2) entries', () => {
    mockGetGuestItineraries.mockReturnValue([
      makeGuestEntry({ tripMeta: { destination: 'City1' } }),
      makeGuestEntry({ tripMeta: { destination: 'City2' } }),
      makeGuestEntry({ tripMeta: { destination: 'City3' } }),
    ]);
    renderStrip(false);
    expect(screen.getByText('City1')).toBeInTheDocument();
    expect(screen.getByText('City2')).toBeInTheDocument();
    expect(screen.queryByText('City3')).not.toBeInTheDocument();
  });

  it('on card click navigates to ROUTES.PUBLIC_CHAT_ITINERARY', async () => {
    const user = userEvent.setup();
    mockGetGuestItineraries.mockReturnValue([makeGuestEntry()]);
    renderStrip(false);
    await user.click(screen.getByText('Paris'));
    expect(mockNavigate).toHaveBeenCalledWith(
      ROUTES.PUBLIC_CHAT_ITINERARY,
      expect.objectContaining({ state: expect.any(Object) }),
    );
  });

  it('heading click dispatches openAuthModal', async () => {
    const user = userEvent.setup();
    mockGetGuestItineraries.mockReturnValue([makeGuestEntry()]);
    const { store } = renderStrip(false);
    expect(store.getState().ui.authModalOpen).toBe(false);
    await user.click(screen.getByText('Recent trips'));
    expect(store.getState().ui.authModalOpen).toBe(true);
  });
});
