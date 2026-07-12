import { describe, it, expect, beforeEach, vi } from 'vitest';
import hotelBookingReducer, {
  triggerSearchFromChips,
  resetSearchTriggerFromChips,
  setTripType,
  setMultistaySegments,
  updateMultistaySegment,
  setMultistayLegSearchResults,
  setMultistayLegSelection,
  clearAllMultistayLegSelections,
  setMultistayLegBookingResults,
  setMultistayActiveLegTab,
  setCachedHotelResults,
  clearCachedHotelResults,
  selectCachedHotelResults,
  selectHotelResultsCacheTimestamp,
  selectHotelResultsCachedParams,
} from './hotelBookingSlice';
import type { HotelBookingState } from './hotelBookingSlice';
import type { HotelItinerary, RoomRate, RateRulesResponse } from '@/types/hotels';
import { defaultHotelFilterState } from '@/features/hotels/utils/hotelFilters';

function getInitialState(overrides?: Partial<HotelBookingState>): {
  hotelBooking: HotelBookingState;
} {
  return {
    hotelBooking: {
      currentStep: 'search',
      searchFormParams: {
        destination: '',
        checkin: '2026-01-01',
        checkout: '2026-01-02',
        rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
        nationality: 'US',
      },
      searchParams: null,
      sessionId: null,
      internalSessionId: null,
      selectedHotel: null,
      tokenId: null,
      productId: null,
      hotelId: null,
      selectedRoom: null,
      rateBasisId: null,
      rateRulesResponse: null,
      roomRatesResponse: null,
      guests: [],
      contactEmail: '',
      contactPhone: '',
      specialRequests: '',
      bookingResult: null,
      paymentIntentId: null,
      bookingReference: null,
      loading: false,
      error: null,
      hotelFilters: defaultHotelFilterState,
      searchTriggerFromChips: 0,
      voucherRedemptionId: null,
      voucherDiscountCents: null,
      voucherCheckoutVoyaReference: null,
      voucherAppliedCode: null,
      voucherReservationExpiresAt: null,
      cachedHotelResults: null,
      cachedHotelResultsTrusted: false,
      hotelResultsCacheTimestamp: null,
      hotelResultsCachedParams: null,
      tripType: 'single',
      multistaySegments: [],
      multistayLegs: [],
      multistayGroupReference: null,
      multistayLegBookingResults: [],
      multistayActiveLegTab: 0,
      ...overrides,
    },
  };
}

describe('hotelBookingSlice', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  it('increments on triggerSearchFromChips', () => {
    let state = hotelBookingReducer(undefined, { type: '@@INIT' });
    expect(state.searchTriggerFromChips).toBe(0);
    state = hotelBookingReducer(state, triggerSearchFromChips());
    expect(state.searchTriggerFromChips).toBe(1);
    state = hotelBookingReducer(state, triggerSearchFromChips());
    expect(state.searchTriggerFromChips).toBe(2);
  });

  it('resets to zero on resetSearchTriggerFromChips', () => {
    let state = hotelBookingReducer(undefined, { type: '@@INIT' });
    state = hotelBookingReducer(state, triggerSearchFromChips());
    state = hotelBookingReducer(state, triggerSearchFromChips());
    expect(state.searchTriggerFromChips).toBe(2);
    state = hotelBookingReducer(state, resetSearchTriggerFromChips());
    expect(state.searchTriggerFromChips).toBe(0);
  });

});

describe('hotelBookingSlice — multi-stay reducers', () => {
  function base(overrides?: Partial<HotelBookingState>): HotelBookingState {
    return getInitialState(overrides).hotelBooking;
  }

  it('setTripType switches to multi-stay and seeds two default segments', () => {
    const next = hotelBookingReducer(base(), setTripType('multi-stay'));
    expect(next.tripType).toBe('multi-stay');
    expect(next.multistaySegments).toHaveLength(2);
    expect(next.multistayLegs).toHaveLength(0);
  });

  it('setTripType back to single does not alter segments', () => {
    const withMulti = hotelBookingReducer(base(), setTripType('multi-stay'));
    const backToSingle = hotelBookingReducer(withMulti, setTripType('single'));
    expect(backToSingle.tripType).toBe('single');
    expect(backToSingle.multistaySegments).toHaveLength(2);
  });

  it('setMultistaySegments resizes the legs array to match', () => {
    const segments = [
      { destination: 'Paris', checkin: '2026-06-01', checkout: '2026-06-05', rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }] },
      { destination: 'Rome', checkin: '2026-06-05', checkout: '2026-06-09', rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }] },
      { destination: 'Madrid', checkin: '2026-06-09', checkout: '2026-06-12', rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }] },
    ];
    const next = hotelBookingReducer(base(), setMultistaySegments(segments));
    expect(next.multistaySegments).toHaveLength(3);
    expect(next.multistayLegs).toHaveLength(3);

    // Shrink back to 2 — legs array trims
    const shrunk = hotelBookingReducer(next, setMultistaySegments(segments.slice(0, 2)));
    expect(shrunk.multistaySegments).toHaveLength(2);
    expect(shrunk.multistayLegs).toHaveLength(2);
  });

  it('updateMultistaySegment patches a single segment field', () => {
    const s = hotelBookingReducer(base(), setTripType('multi-stay'));
    const updated = hotelBookingReducer(s, updateMultistaySegment({ index: 0, segment: { destination: 'Tokyo' } }));
    expect(updated.multistaySegments[0]?.destination).toBe('Tokyo');
    expect(updated.multistaySegments[1]?.destination).toBe('');
  });

  it('setMultistayLegSearchResults populates hotels and clears prior selection', () => {
    const withMulti = hotelBookingReducer(base(), setTripType('multi-stay'));
    const grown = hotelBookingReducer(withMulti, setMultistaySegments([
      { destination: 'A', checkin: '2026-06-01', checkout: '2026-06-03', rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }] },
      { destination: 'B', checkin: '2026-06-03', checkout: '2026-06-06', rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }] },
    ]));
    const fakeHotel = { id: 'h1', name: 'Hotel A' } as unknown as HotelItinerary;
    const next = hotelBookingReducer(grown, setMultistayLegSearchResults({ legIndex: 0, sessionId: 'sess1', hotels: [fakeHotel] }));
    expect(next.multistayLegs[0]?.sessionId).toBe('sess1');
    expect(next.multistayLegs[0]?.hotels).toHaveLength(1);
    expect(next.multistayLegs[0]?.selectedHotel).toBeNull();
  });

  it('setMultistayLegSelection stores selection on the correct leg', () => {
    const withLegs = hotelBookingReducer(base(), setMultistaySegments([
      { destination: 'A', checkin: '2026-06-01', checkout: '2026-06-03', rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }] },
      { destination: 'B', checkin: '2026-06-03', checkout: '2026-06-06', rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }] },
    ]));
    const fakeHotel = { id: 'h1', name: 'Hotel A' } as unknown as HotelItinerary;
    const fakeRoom = { rateBasisId: 'rb1' } as unknown as RoomRate;
    const fakeRateRules = {} as RateRulesResponse;
    const next = hotelBookingReducer(withLegs, setMultistayLegSelection({
      legIndex: 1,
      hotel: fakeHotel,
      tokenId: 'tok1',
      productId: 'prod1',
      hotelId: 'hid1',
      room: fakeRoom,
      rateRules: fakeRateRules,
      internalSessionId: 'isess1',
      roomRatesResponse: null,
      currency: 'USD',
    }));
    expect(next.multistayLegs[1]?.selectedHotel).toEqual(fakeHotel);
    expect(next.multistayLegs[1]?.rateBasisId).toBe('rb1');
    expect(next.multistayLegs[0]?.selectedHotel).toBeNull();
  });

  it('clearAllMultistayLegSelections resets selections but keeps search results', () => {
    const withLegs = hotelBookingReducer(base(), setMultistaySegments([
      { destination: 'A', checkin: '2026-06-01', checkout: '2026-06-03', rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }] },
    ]));
    const fakeHotel = { id: 'h1' } as unknown as HotelItinerary;
    const withResults = hotelBookingReducer(withLegs, setMultistayLegSearchResults({ legIndex: 0, sessionId: 'sess1', hotels: [fakeHotel] }));
    const fakeRoom = { rateBasisId: 'rb1' } as unknown as RoomRate;
    const withSelection = hotelBookingReducer(withResults, setMultistayLegSelection({
      legIndex: 0, hotel: fakeHotel, tokenId: 't', productId: 'p', hotelId: 'h',
      room: fakeRoom, rateRules: {} as RateRulesResponse, internalSessionId: 'i', roomRatesResponse: null, currency: 'USD',
    }));
    expect(withSelection.multistayLegs[0]?.selectedHotel).not.toBeNull();

    const cleared = hotelBookingReducer(withSelection, clearAllMultistayLegSelections());
    expect(cleared.multistayLegs[0]?.selectedHotel).toBeNull();
    expect(cleared.multistayLegs[0]?.hotels).toHaveLength(1);
    expect(cleared.multistayLegBookingResults).toHaveLength(0);
    expect(cleared.multistayGroupReference).toBeNull();
  });

  it('setMultistayLegBookingResults stores results', () => {
    const next = hotelBookingReducer(base(), setMultistayLegBookingResults([
      { legIndex: 0, voyaBookingReference: 'VOYA-001', externalBookingReference: 'EXT-1', hotelName: 'Hotel A', hotelCity: 'Paris' },
      { legIndex: 1, voyaBookingReference: 'VOYA-002', externalBookingReference: null, hotelName: null, hotelCity: null },
    ]));
    expect(next.multistayLegBookingResults).toHaveLength(2);
    expect(next.multistayLegBookingResults[0]?.voyaBookingReference).toBe('VOYA-001');
  });

  it('setMultistayActiveLegTab updates the active tab index', () => {
    const next = hotelBookingReducer(base(), setMultistayActiveLegTab(2));
    expect(next.multistayActiveLegTab).toBe(2);
  });

  describe('setCachedHotelResults', () => {
    const params = {
      destination: 'Paris',
      checkin: '2026-08-01',
      checkout: '2026-08-05',
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: 'US',
    };

    const mockData = { sessionId: 's1', hotels: [] } as unknown as import('./hotelBookingSlice').HotelBookingState['cachedHotelResults'];

    it('stores data, timestamp ≈ now, and params', () => {
      const before = Date.now();
      let s = base();
      s = hotelBookingReducer(s, setCachedHotelResults({ data: mockData!, params }));
      const after = Date.now();
      expect(s.cachedHotelResults).toBe(mockData);
      expect(s.hotelResultsCachedParams).toEqual(params);
      expect(s.hotelResultsCacheTimestamp).toBeGreaterThanOrEqual(before);
      expect(s.hotelResultsCacheTimestamp).toBeLessThanOrEqual(after);
    });

    it('clearCachedHotelResults resets all three fields to null', () => {
      let s = base();
      s = hotelBookingReducer(s, setCachedHotelResults({ data: mockData!, params }));
      s = hotelBookingReducer(s, clearCachedHotelResults());
      expect(s.cachedHotelResults).toBeNull();
      expect(s.hotelResultsCacheTimestamp).toBeNull();
      expect(s.hotelResultsCachedParams).toBeNull();
    });

    it('selectors return cache fields from state', () => {
      let s = base();
      s = hotelBookingReducer(s, setCachedHotelResults({ data: mockData!, params }));
      const wrapped = { hotelBooking: s };
      expect(selectCachedHotelResults(wrapped)).toBe(mockData);
      expect(selectHotelResultsCachedParams(wrapped)).toEqual(params);
      expect(selectHotelResultsCacheTimestamp(wrapped)).toBeGreaterThan(0);
    });
  });
});
