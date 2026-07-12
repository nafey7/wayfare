import { describe, it, expect, beforeEach, vi } from 'vitest';
import flightBookingReducer, {
  setStep,
  setSearchFormParams,
  setTripType,
  setFrom,
  setTo,
  setDate,
  setReturnDate,
  setTravellers,
  selectFlight,
  setFareRules,
  setPassengers,
  setContact,
  setPostalCode,
  updatePassenger,
  setBookingResult,
  setPaymentIntentId,
  setIsLCC,
  setRevalidationResponse,
  setSelectedFlightData,
  setFlightFilters,
  resetFlightFilters,
  resetBooking,
  clearSelection,
  triggerSearchFromChips,
  resetSearchTriggerFromChips,
  setMulticityLegSelection,
  clearMulticityLegSelection,
  clearMulticityLegSelections,
  setMulticityLegBookingResults,
  selectCurrentStep,
  selectSessionId,
  selectPassengers,
  selectContact,
  selectBookingResult,
  selectIsLCC,
  selectRevalidationResponse,
  selectSelectedFlightData,
  selectFlightFilters,
  setCachedFlightResults,
  clearCachedFlightResults,
  selectCachedFlightResults,
  selectFlightResultsCacheTimestamp,
  selectFlightResultsCachedParams,
} from './flightBookingSlice';
import type { FlightBookingState } from './flightBookingSlice';
import { defaultFlightFilterState } from '@/features/flights/utils/flightFilters';
import type { MappedFlight } from '@/types/flight';

// Minimal shape for selectFlight payload (MappedFlight-compatible)
const mockFlight: MappedFlight = {
  is_round_trip: false,
  outbound: {
    duration: '2h',
    stops: 0,
    layovers: [],
  },
  id: 'f1',
  price: 100,
};

function getInitialState(overrides?: Partial<FlightBookingState>): { flightBooking: FlightBookingState } {
  return {
    flightBooking: {
      currentStep: 'search',
      searchParams: null,
      searchFormParams: {
        tripType: 'one-way',
        from: '',
        to: '',
        date: new Date().toISOString(),
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
    },
  };
}

describe('flightBookingSlice', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  describe('setStep', () => {
    it('sets currentStep', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setStep('results'));
      expect(next.currentStep).toBe('results');
    });
  });

  describe('setSearchFormParams', () => {
    it('updates searchFormParams', () => {
      const state = getInitialState();
      const params = {
        tripType: 'round-trip' as const,
        from: 'LHR',
        to: 'JFK',
        date: '2026-03-15',
        returnDate: '2026-03-22',
        travellers: { adults: 2, children: 0, infants: 0, cabinClass: 'Economy' as const },
      };
      const next = flightBookingReducer(state.flightBooking, setSearchFormParams(params));
      expect(next.searchFormParams.from).toBe('LHR');
      expect(next.searchFormParams.returnDate).toBe('2026-03-22');
    });
  });

  describe('setTripType', () => {
    it('clears returnDate when switching to one-way', () => {
      const state = getInitialState({
        searchFormParams: {
          tripType: 'round-trip',
          from: 'LHR',
          to: 'JFK',
          date: '2026-03-15',
          returnDate: '2026-03-22',
          travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
        },
      });
      const next = flightBookingReducer(state.flightBooking, setTripType('one-way'));
      expect(next.searchFormParams.tripType).toBe('one-way');
      expect(next.searchFormParams.returnDate).toBeNull();
    });
  });

  describe('setFrom / setTo', () => {
    it('updates from airport', () => {
      const state = getInitialState();
      const next = flightBookingReducer(
        state.flightBooking,
        setFrom({ value: 'LHR', airport: { iata: 'LHR', name: 'Heathrow', city: 'London', country: 'UK' } })
      );
      expect(next.searchFormParams.from).toBe('LHR');
      expect(next.searchFormParams.fromAirport?.iata).toBe('LHR');
    });
    it('updates to airport', () => {
      const state = getInitialState();
      const next = flightBookingReducer(
        state.flightBooking,
        setTo({ value: 'JFK', airport: { iata: 'JFK', name: 'JFK', city: 'New York', country: 'US' } })
      );
      expect(next.searchFormParams.to).toBe('JFK');
    });
  });

  describe('setDate / setReturnDate / setTravellers', () => {
    it('updates date and returnDate', () => {
      const state = getInitialState();
      let next = flightBookingReducer(state.flightBooking, setDate('2026-04-01'));
      expect(next.searchFormParams.date).toBe('2026-04-01');
      next = flightBookingReducer(next, setReturnDate('2026-04-10'));
      expect(next.searchFormParams.returnDate).toBe('2026-04-10');
    });
    it('updates travellers', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setTravellers({ adults: 3, children: 1, infants: 0, cabinClass: 'Business' }));
      expect(next.searchFormParams.travellers.adults).toBe(3);
      expect(next.searchFormParams.travellers.cabinClass).toBe('Business');
    });
  });

  describe('selectFlight', () => {
    it('sets selectedFlight, sessionId, fareSourceCode', () => {
      const state = getInitialState();
      const next = flightBookingReducer(
        state.flightBooking,
        selectFlight({ flight: mockFlight, sessionId: 'sess-1', fareSourceCode: 'FSC-1' })
      );
      expect(next.selectedFlight).toEqual(mockFlight);
      expect(next.sessionId).toBe('sess-1');
      expect(next.fareSourceCode).toBe('FSC-1');
    });
  });

  describe('setFareRules / setPassengers / setContact / setPostalCode', () => {
    it('updates fare rules', () => {
      const state = getInitialState();
      const rules = {
        sessionId: 's1',
        fareSourceCode: 'f1',
        fareRules: [{ ruleDescription: 'Test' }],
      };
      const next = flightBookingReducer(state.flightBooking, setFareRules(rules));
      expect(next.fareRules?.fareRules).toHaveLength(1);
    });
    it('sets passengers array', () => {
      const state = getInitialState();
      const passengers = [
        {
          type: 'adult' as const,
          title: 'Mr',
          firstName: 'John',
          lastName: 'Doe',
          dateOfBirth: '1990-01-15',
          nationality: 'US',
        },
      ];
      const next = flightBookingReducer(state.flightBooking, setPassengers(passengers));
      expect(next.passengers).toHaveLength(1);
      expect(next.passengers[0]!.firstName).toBe('John');
    });
    it('updates contact', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setContact({ email: 'a@b.com', country_code: '1', phone: '555' }));
      expect(next.contact.email).toBe('a@b.com');
      expect(next.contact.phone).toBe('555');
    });
    it('sets postal code', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setPostalCode('1234AB'));
      expect(next.postalCode).toBe('1234AB');
    });
  });

  describe('updatePassenger', () => {
    it('updates existing passenger by index', () => {
      const state = getInitialState({
        passengers: [
          {
            type: 'adult',
            title: 'Mr',
            firstName: 'John',
            lastName: 'Doe',
            dateOfBirth: '1990-01-15',
            nationality: 'US',
          },
        ],
      });
      const next = flightBookingReducer(
        state.flightBooking,
        updatePassenger({ index: 0, details: { firstName: 'Jane' } })
      );
      expect(next.passengers[0]!.firstName).toBe('Jane');
      expect(next.passengers[0]!.lastName).toBe('Doe');
    });
    it('creates passenger at index if missing', () => {
      const state = getInitialState();
      const next = flightBookingReducer(
        state.flightBooking,
        updatePassenger({
          index: 0,
          details: {
            type: 'adult',
            title: 'Mr',
            firstName: 'New',
            lastName: 'User',
            dateOfBirth: '1985-05-05',
            nationality: 'GB',
          },
        })
      );
      expect(next.passengers[0]!.firstName).toBe('New');
    });
  });

  describe('setBookingResult / setPaymentIntentId / setIsLCC', () => {
    it('sets booking result and reference', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setBookingResult({
        voyaBookingReference: 'VYA-123',
        status: 'confirmed',
        totalAmount: 19900,
        currency: 'USD',
      }));
      expect(next.bookingResult?.voyaBookingReference).toBe('VYA-123');
      expect(next.bookingReference).toBe('VYA-123');
    });
    it('sets payment intent id (Revolut order_id) and isLCC', () => {
      const state = getInitialState();
      const revolutOrderId = '550e8400-e29b-41d4-a716-446655440000';
      let next = flightBookingReducer(state.flightBooking, setPaymentIntentId(revolutOrderId));
      expect(next.paymentIntentId).toBe(revolutOrderId);
      next = flightBookingReducer(next, setIsLCC(true));
      expect(next.isLCC).toBe(true);
    });
  });

  describe('setSelectedFlightData', () => {
    it('sets selected flight data from search', () => {
      const state = getInitialState();
      const flightData = {
        id: 'f1',
        aircraftName: 'Boeing 737',
        flightNumber: 'BA123',
        tags: [],
        passengers: 1,
        passengerCounts: { adults: 1, children: 0, infants: 0 },
        legs: [],
        price: 100,
      };
      const next = flightBookingReducer(state.flightBooking, setSelectedFlightData(flightData));
      expect(next.selectedFlightData?.id).toBe('f1');
      expect(next.selectedFlightData?.flightNumber).toBe('BA123');
    });
    it('clears when passed null', () => {
      const state = getInitialState({
        selectedFlightData: {
          id: 'f1',
          aircraftName: 'Boeing 737',
          flightNumber: 'BA123',
          tags: [],
          passengers: 1,
          passengerCounts: { adults: 1, children: 0, infants: 0 },
          legs: [],
          price: 100,
        },
      });
      const next = flightBookingReducer(state.flightBooking, setSelectedFlightData(null));
      expect(next.selectedFlightData).toBeNull();
    });
  });

  describe('setRevalidationResponse', () => {
    it('sets revalidation and derives isLCC from fareType WebFare', () => {
      const state = getInitialState();
      const next = flightBookingReducer(state.flightBooking, setRevalidationResponse({
        sessionId: 's',
        fareSourceCode: 'f',
        isFareAvailable: true,
        validatedFareItineraries: [
          { flightLegs: [], updatedPricing: { fareType: 'WebFare' }, pricing: {} },
        ],
      }));
      expect(next.revalidationResponse?.sessionId).toBe('s');
      expect(next.isLCC).toBe(true);
    });
  });

  describe('setFlightFilters / resetFlightFilters', () => {
    it('updates and resets flight filters', () => {
      const state = getInitialState();
      const withPrice = { ...defaultFlightFilterState, priceMin: 50 };
      let next = flightBookingReducer(state.flightBooking, setFlightFilters(withPrice));
      expect(next.flightFilters.priceMin).toBe(50);
      next = flightBookingReducer(next, resetFlightFilters());
      expect(next.flightFilters.priceMin).toBeNull();
    });
  });

  describe('resetBooking', () => {
    it('resets to initial state with default form params', () => {
      const state = getInitialState({
        currentStep: 'payment',
        sessionId: 'sess',
        passengers: [{ type: 'adult', title: 'Mr', firstName: 'J', lastName: 'D', dateOfBirth: '1990-01-01', nationality: 'US' }],
      });
      const next = flightBookingReducer(state.flightBooking, resetBooking());
      expect(next.currentStep).toBe('search');
      expect(next.sessionId).toBeNull();
      expect(next.passengers).toHaveLength(0);
    });
  });

  describe('multicity leg selection', () => {
    it('setMulticityLegSelection stores per leg and clearMulticityLegSelection removes one', () => {
      const state = getInitialState();
      const rev = {
        sessionId: 's1',
        fareSourceCode: 'f1',
        isFareAvailable: true,
        validatedFareItineraries: [],
      };
      let next = flightBookingReducer(
        state.flightBooking,
        setMulticityLegSelection({
          legIndex: 0,
          sessionId: 's1',
          fareSourceCode: 'f1',
          selectedFlightData: {
            id: '0::f1',
            aircraftName: 'A',
            flightNumber: '1',
            tags: [],
            passengers: 1,
            passengerCounts: { adults: 1, children: 0, infants: 0 },
            legs: [],
            price: 10,
          },
          revalidateResponse: rev,
        })
      );
      expect(next.multicitySelectedLegs[0]?.fareSourceCode).toBe('f1');
      next = flightBookingReducer(next, clearMulticityLegSelection(0));
      expect(next.multicitySelectedLegs[0]).toBeUndefined();
    });

    it('clearMulticityLegSelections clears all', () => {
      const state = getInitialState({
        multicitySelectedLegs: {
          0: {
            legIndex: 0,
            sessionId: 's',
            fareSourceCode: 'f',
            selectedFlightData: {
              id: 'x',
              aircraftName: 'A',
              flightNumber: '1',
              tags: [],
              passengers: 1,
              passengerCounts: { adults: 1, children: 0, infants: 0 },
              legs: [],
              price: 1,
            },
            revalidateResponse: {
              sessionId: 's',
              fareSourceCode: 'f',
              isFareAvailable: true,
              validatedFareItineraries: [],
            },
          },
        },
      });
      const next = flightBookingReducer(state.flightBooking, clearMulticityLegSelections());
      expect(Object.keys(next.multicitySelectedLegs)).toHaveLength(0);
    });
  });

  describe('clearSelection', () => {
    it('clears selected flight, session, fare code, fare rules, revalidation and selectedFlightData', () => {
      const state = getInitialState({
        currentStep: 'rules',
        selectedFlight: mockFlight,
        sessionId: 's',
        fareSourceCode: 'f',
        fareRules: { sessionId: 's', fareSourceCode: 'f', fareRules: [] },
        revalidationResponse: { sessionId: 's', fareSourceCode: 'f', isFareAvailable: true, validatedFareItineraries: [] },
        selectedFlightData: {
          id: 'f1',
          aircraftName: 'Boeing 737',
          flightNumber: 'BA123',
          tags: [],
          passengers: 1,
          passengerCounts: { adults: 1, children: 0, infants: 0 },
          legs: [],
          price: 100,
        },
      });
      const next = flightBookingReducer(state.flightBooking, clearSelection());
      expect(next.selectedFlight).toBeNull();
      expect(next.sessionId).toBeNull();
      expect(next.fareSourceCode).toBeNull();
      expect(next.fareRules).toBeNull();
      expect(next.revalidationResponse).toBeNull();
      expect(next.selectedFlightData).toBeNull();
      expect(next.currentStep).toBe('results');
    });

    it('clears multicity leg selections', () => {
      const state = getInitialState({
        multicitySelectedLegs: {
          0: {
            legIndex: 0,
            sessionId: 's',
            fareSourceCode: 'f',
            selectedFlightData: {
              id: '0::f',
              aircraftName: 'A',
              flightNumber: '1',
              tags: [],
              passengers: 1,
              passengerCounts: { adults: 1, children: 0, infants: 0 },
              legs: [],
              price: 1,
            },
            revalidateResponse: {
              sessionId: 's',
              fareSourceCode: 'f',
              isFareAvailable: true,
              validatedFareItineraries: [],
            },
          },
        },
      });
      const next = flightBookingReducer(state.flightBooking, clearSelection());
      expect(Object.keys(next.multicitySelectedLegs)).toHaveLength(0);
      expect(next.multicityLegBookingResults).toBeNull();
    });

    it('setMulticityLegBookingResults stores per-leg refs', () => {
      const state = getInitialState();
      const next = flightBookingReducer(
        state.flightBooking,
        setMulticityLegBookingResults([
          { legIndex: 0, voyaBookingReference: 'VOYA-A' },
          { legIndex: 1, voyaBookingReference: 'VOYA-B' },
        ])
      );
      expect(next.multicityLegBookingResults).toHaveLength(2);
      expect(next.multicityLegBookingResults?.[1]?.voyaBookingReference).toBe('VOYA-B');
    });
  });

  describe('selectors', () => {
    it('selectCurrentStep, selectSessionId, selectPassengers, selectContact return state', () => {
      const state = getInitialState({
        currentStep: 'passengers',
        sessionId: 'sess-1',
        passengers: [],
        contact: { email: 'x@y.com', country_code: '44', phone: '7' },
      });
      expect(selectCurrentStep(state)).toBe('passengers');
      expect(selectSessionId(state)).toBe('sess-1');
      expect(selectPassengers(state)).toEqual([]);
      expect(selectContact(state).email).toBe('x@y.com');
    });
    it('selectBookingResult, selectIsLCC, selectRevalidationResponse, selectSelectedFlightData, selectFlightFilters', () => {
      const flightData = {
        id: 'f1',
        aircraftName: 'Boeing 737',
        flightNumber: 'BA123',
        tags: [],
        passengers: 1,
        passengerCounts: { adults: 1, children: 0, infants: 0 },
        legs: [],
        price: 100,
      };
      const state = getInitialState({
        bookingResult: { voyaBookingReference: 'VYA-1', status: 'confirmed', totalAmount: 100, currency: 'USD' },
        isLCC: true,
        revalidationResponse: { sessionId: 's', fareSourceCode: 'f', isFareAvailable: true, validatedFareItineraries: [] },
        selectedFlightData: flightData,
        flightFilters: { ...defaultFlightFilterState, directOnly: true },
      });
      expect(selectBookingResult(state)?.voyaBookingReference).toBe('VYA-1');
      expect(selectIsLCC(state)).toBe(true);
      expect(selectRevalidationResponse(state)?.sessionId).toBe('s');
      expect(selectSelectedFlightData(state)?.id).toBe('f1');
      expect(selectFlightFilters(state).directOnly).toBe(true);
    });
  });

  describe('searchTriggerFromChips', () => {
    it('increments on triggerSearchFromChips and resets on resetSearchTriggerFromChips', () => {
      let s = getInitialState().flightBooking;
      s = flightBookingReducer(s, triggerSearchFromChips());
      expect(s.searchTriggerFromChips).toBe(1);
      s = flightBookingReducer(s, triggerSearchFromChips());
      expect(s.searchTriggerFromChips).toBe(2);
      s = flightBookingReducer(s, resetSearchTriggerFromChips());
      expect(s.searchTriggerFromChips).toBe(0);
    });
  });

  describe('setCachedFlightResults', () => {
    const params = {
      tripType: 'one-way' as const,
      from: 'LHR',
      to: 'JFK',
      date: '2026-08-01',
      returnDate: null,
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' as const },
    };

    const mockData = { sessionId: 's1', fareItineraries: [] } as unknown as import('./flightBookingSlice').FlightBookingState['cachedFlightResults'];

    it('stores data, timestamp ≈ now, and params', () => {
      const before = Date.now();
      let s = getInitialState().flightBooking;
      s = flightBookingReducer(s, setCachedFlightResults({ data: mockData!, params }));
      const after = Date.now();
      expect(s.cachedFlightResults).toBe(mockData);
      expect(s.flightResultsCachedParams).toEqual(params);
      expect(s.flightResultsCacheTimestamp).toBeGreaterThanOrEqual(before);
      expect(s.flightResultsCacheTimestamp).toBeLessThanOrEqual(after);
    });

    it('clearCachedFlightResults resets all three fields to null', () => {
      let s = getInitialState().flightBooking;
      s = flightBookingReducer(s, setCachedFlightResults({ data: mockData!, params }));
      s = flightBookingReducer(s, clearCachedFlightResults());
      expect(s.cachedFlightResults).toBeNull();
      expect(s.flightResultsCacheTimestamp).toBeNull();
      expect(s.flightResultsCachedParams).toBeNull();
    });

    it('selectors return cache fields from state', () => {
      let s = getInitialState().flightBooking;
      s = flightBookingReducer(s, setCachedFlightResults({ data: mockData!, params }));
      const wrapped = { flightBooking: s };
      expect(selectCachedFlightResults(wrapped)).toBe(mockData);
      expect(selectFlightResultsCachedParams(wrapped)).toEqual(params);
      expect(selectFlightResultsCacheTimestamp(wrapped)).toBeGreaterThan(0);
    });
  });
});
