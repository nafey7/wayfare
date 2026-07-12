import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import flightBookingReducer, { type FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import { defaultFlightFilterState } from '@/features/flights/utils/flightFilters';
import type { FlightBookingState } from '@/store/slices/flightBookingSlice';

vi.mock('@mantine/dates', () => ({
  DatePickerInput: () => null,
}));

vi.mock('lucide-react', () => {
  const Stub = () => null;
  return {
    ArrowLeftRight: Stub,
    Calendar: Stub,
    PlaneLanding: Stub,
    PlaneTakeoff: Stub,
    Plus: Stub,
    Trash2: Stub,
  };
});

vi.mock('@/api/flightsApi', () => ({
  useSearchAirportsQuery: () => ({ data: [], isFetching: false }),
}));

import { FlightSearchBarV2 } from './FlightSearchBarV2';

function makeBookingState(overrides: Partial<FlightBookingState>): FlightBookingState {
  return {
    currentStep: 'search',
    searchParams: null,
    searchFormParams: {
      tripType: 'one-way',
      from: '',
      to: '',
      date: '2026-06-01T00:00:00.000Z',
      returnDate: null,
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    },
    selectedFlight: null,
    sessionId: null,
    fareSourceCode: null,
    fareRules: null,
    passengers: [],
    contact: { email: '', country_code: '', phone: '' },
    postalCode: null,
    loading: false,
    error: null,
    bookingReference: null,
    bookingResult: null,
    paymentIntentId: null,
    isLCC: false,
    revalidationResponse: null,
    selectedFlightData: null,
    flightFilters: defaultFlightFilterState,
    savedPassengerIds: {},
    searchTriggerFromChips: 0,
    multicitySelectedLegs: {},
    multicityGroupReference: null,
    multicityLegBookingResults: null,
    flightRouteModalOpen: false,
    voucherRedemptionId: null,
    voucherDiscountCents: null,
    voucherCheckoutVoyaReference: null,
    voucherAppliedCode: null,
    voucherReservationExpiresAt: null,
    cachedFlightResults: null,
    cachedFlightResultsTrusted: false,
    flightResultsCacheTimestamp: null,
    flightResultsCachedParams: null,
    ...overrides,
  };
}

function renderWithStore(ui: ReactElement, state: { flightBooking: FlightBookingState }) {
  const store = configureStore({
    reducer: { flightBooking: flightBookingReducer },
    preloadedState: state,
  });
  return render(
    <Provider store={store}>
      <MantineProvider>{ui}</MantineProvider>
    </Provider>
  );
}

// FlightSearchBarV2 is a headless modal provider — tests cover its modal visibility behaviour.
describe('FlightSearchBarV2', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it('renders nothing visible when route modal is closed', () => {
    const searchFormParams: FlightSearchFormParams = {
      tripType: 'one-way',
      from: 'Paris',
      to: 'Madrid',
      date: '2026-06-01T00:00:00.000Z',
      returnDate: null,
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    };
    renderWithStore(<FlightSearchBarV2 />, {
      flightBooking: makeBookingState({ searchFormParams, flightRouteModalOpen: false }),
    });
    expect(screen.queryByText('From')).not.toBeInTheDocument();
    expect(screen.queryByText('To')).not.toBeInTheDocument();
  });

  it('renders the single-leg route form when modal is open', () => {
    const searchFormParams: FlightSearchFormParams = {
      tripType: 'one-way',
      from: 'Paris',
      to: 'Madrid',
      date: '2026-06-01T00:00:00.000Z',
      returnDate: null,
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    };
    renderWithStore(<FlightSearchBarV2 />, {
      flightBooking: makeBookingState({ searchFormParams, flightRouteModalOpen: true }),
    });
    expect(screen.getByText('From')).toBeInTheDocument();
    expect(screen.getByText('To')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('renders the multi-city form when modal is open', () => {
    const searchFormParams: FlightSearchFormParams = {
      tripType: 'multi-city',
      from: '',
      to: '',
      date: null,
      returnDate: null,
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
      segments: [
        { from: 'Paris', to: 'Madrid', date: '2026-06-01T00:00:00.000Z' },
        { from: 'Madrid', to: 'Barcelona', date: '2026-06-08T00:00:00.000Z' },
      ],
    };
    renderWithStore(<FlightSearchBarV2 />, {
      flightBooking: makeBookingState({ searchFormParams, flightRouteModalOpen: true }),
    });
    expect(screen.getAllByText('From').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Add another leg')).toBeInTheDocument();
  });
});
