import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { store } from '@/store';
import { syncItineraryToSearchParams } from '@/store/thunks/syncItineraryToSearchParams';
import type { ItineraryNavigationState } from '../types';
import { ItineraryPage } from './ItineraryPage';

// The unified test for the restore-from-history flow is: when an itinerary is
// viewed and tripMeta is present, the page must hydrate the flight + hotel
// search forms via `syncItineraryToSearchParams`. We spy on the thunk creator
// and assert the args; the thunk itself has its own unit tests.
vi.mock('@/store/thunks/syncItineraryToSearchParams', async () => {
  const actual = await vi.importActual<
    typeof import('@/store/thunks/syncItineraryToSearchParams')
  >('@/store/thunks/syncItineraryToSearchParams');
  return {
    ...actual,
    syncItineraryToSearchParams: vi.fn(actual.syncItineraryToSearchParams),
  };
});

// Heavy children are not under test here — they bring in Google Maps,
// framer-motion drag state, etc. Stub them out.
vi.mock('../components', async () => {
  const actual = await vi.importActual<typeof import('../components')>('../components');
  return {
    ...actual,
    MultiDayRouteMap: () => null,
    ItineraryDetailsComponent: () => null,
    ItineraryDayCard: () => null,
    ItineraryStopDetail: () => null,
    LinkedBookingChips: () => null,
  };
});

vi.mock('@/api/itinerariesApi', () => ({
  useGetItineraryQuery: () => ({ data: undefined, isLoading: false, error: undefined }),
}));

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

function TestWrapper({
  children,
  navState,
}: {
  children: ReactNode;
  navState?: ItineraryNavigationState;
}) {
  return (
    <Provider store={store}>
      <MantineProvider theme={mantineTheme} env="test">
        <MemoryRouter initialEntries={[{ pathname: '/itinerary', state: navState }]}>
          <Routes>
            <Route path="/itinerary" element={children} />
          </Routes>
        </MemoryRouter>
      </MantineProvider>
    </Provider>
  );
}

const validItinerary: ItineraryNavigationState['structuredItinerary'] = {
  itineraryItems: [
    { day: 1, title: 'Day 1', description: 'Arrive', imageUrl: '' },
  ],
};

describe('ItineraryPage history restoration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dispatches syncItineraryToSearchParams with tripMeta when viewing an itinerary', () => {
    const navState: ItineraryNavigationState = {
      structuredItinerary: validItinerary,
      tripMeta: {
        origin: 'LHR',
        destination: 'BCN',
        departure_date: '2026-06-01',
        return_date: '2026-06-08',
        adults: 2,
        children: 1,
        infants: 0,
        trip_type: 'round_trip',
      },
    };

    render(
      <TestWrapper navState={navState}>
        <ItineraryPage />
      </TestWrapper>
    );

    expect(syncItineraryToSearchParams).toHaveBeenCalledWith(
      expect.objectContaining({
        origin: 'LHR',
        destination: 'BCN',
        departure_date: '2026-06-01',
        return_date: '2026-06-08',
        adults: 2,
        children: 1,
        infants: 0,
        trip_type: 'round_trip',
      })
    );

    // End-to-end: thunk fires through and populates both search-form slices.
    const flight = store.getState().flightBooking.searchFormParams;
    expect(flight.from).toBe('LHR');
    expect(flight.to).toBe('BCN');
    expect(flight.date).toBe('2026-06-01');
    expect(flight.returnDate).toBe('2026-06-08');
    expect(flight.tripType).toBe('round-trip');
    expect(flight.travellers.adults).toBe(2);

    const hotel = store.getState().hotelBooking.searchFormParams;
    expect(hotel.destination).toBe('BCN');
    expect(hotel.checkin).toBe('2026-06-01');
    expect(hotel.checkout).toBe('2026-06-08');
  });

  it('infers one-way trip type when tripMeta has no return_date', () => {
    const navState: ItineraryNavigationState = {
      structuredItinerary: validItinerary,
      tripMeta: { origin: 'LHR', destination: 'BCN', departure_date: '2026-06-01' },
    };

    render(
      <TestWrapper navState={navState}>
        <ItineraryPage />
      </TestWrapper>
    );

    expect(syncItineraryToSearchParams).toHaveBeenCalledWith(
      expect.objectContaining({ trip_type: 'one_way' })
    );
  });

  it('passes trip_type multi_city for multi-city itineraries', () => {
    const navState: ItineraryNavigationState = {
      structuredItinerary: validItinerary,
      tripMeta: {
        origin: 'LHR',
        destination: 'BCN',
        departure_date: '2026-06-01',
        return_date: '2026-06-08',
        trip_type: 'multi_city',
      },
    };

    render(
      <TestWrapper navState={navState}>
        <ItineraryPage />
      </TestWrapper>
    );

    // ItineraryPage forwards 'multi_city' so the flight form shows multi-city mode.
    expect(syncItineraryToSearchParams).toHaveBeenCalledWith(
      expect.objectContaining({ trip_type: 'multi_city' })
    );
  });

  it('does not dispatch the sync thunk when tripMeta is absent', () => {
    const navState: ItineraryNavigationState = {
      structuredItinerary: validItinerary,
      // no tripMeta
    };

    render(
      <TestWrapper navState={navState}>
        <ItineraryPage />
      </TestWrapper>
    );

    expect(syncItineraryToSearchParams).not.toHaveBeenCalled();
  });

  it('does not dispatch the sync thunk when tripMeta has neither origin nor destination', () => {
    const navState: ItineraryNavigationState = {
      structuredItinerary: validItinerary,
      tripMeta: { adults: 1 },
    };

    render(
      <TestWrapper navState={navState}>
        <ItineraryPage />
      </TestWrapper>
    );

    expect(syncItineraryToSearchParams).not.toHaveBeenCalled();
  });
});
