import { describe, it, expect } from 'vitest';
import {
  defaultHotelFilterState,
  filterHotels,
  toFilterableHotel,
  getHotelTotal,
  getHotelCurrency,
  isDefaultHotelFilterState,
  extractPropertyTypesFromHotels,
  getDistanceBounds,
  extractFacilitiesFromHotels,
  extractLocalitiesFromHotels,
  countActiveHotelFilters,
  type HotelFilterState,
  type FilterableHotel,
} from './hotelFilters';
import type { Hotel, HotelItinerary } from '@/types/hotels';

function makeHotel(overrides: Partial<FilterableHotel>): FilterableHotel {
  return {
    id: 'h1',
    tokenId: 't1',
    name: 'Test Hotel',
    starRating: 4,
    total: 200,
    currency: 'USD',
    facilities: [],
    ...overrides,
  };
}

function makeHotelType(overrides: Partial<Hotel>): Hotel {
  return {
    id: 'h1',
    tokenId: 't1',
    name: 'Test Hotel',
    address: '123 Main St',
    city: 'Paris',
    country: 'FR',
    starRating: 4,
    latitude: 0,
    longitude: 0,
    startingPrice: { currency: 'USD', amount: 200, perNight: 100 },
    ...overrides,
  };
}

describe('hotelFilters', () => {
  describe('defaultHotelFilterState', () => {
    it('has empty nameQuery and null price bounds', () => {
      expect(defaultHotelFilterState.nameQuery).toBe('');
      expect(defaultHotelFilterState.priceMin).toBeNull();
      expect(defaultHotelFilterState.priceMax).toBeNull();
    });
    it('has empty starRatings, propertyTypes, facilities, localities and fare type flags false', () => {
      expect(defaultHotelFilterState.starRatings).toEqual([]);
      expect(defaultHotelFilterState.propertyTypes).toEqual([]);
      expect(defaultHotelFilterState.refundableOnly).toBe(false);
      expect(defaultHotelFilterState.nonRefundableOnly).toBe(false);
      expect(defaultHotelFilterState.distanceMin).toBeNull();
      expect(defaultHotelFilterState.distanceMax).toBeNull();
      expect(defaultHotelFilterState.facilities).toEqual([]);
      expect(defaultHotelFilterState.localities).toEqual([]);
    });
  });

  describe('getHotelTotal and getHotelCurrency', () => {
    it('uses startingPrice.amount when no total/originalTotal', () => {
      const h = makeHotelType({ startingPrice: { currency: 'EUR', amount: 150, perNight: 75 } });
      expect(getHotelTotal(h)).toBe(150);
      expect(getHotelCurrency(h)).toBe('EUR');
    });
    it('uses originalTotal when present on itinerary (no total)', () => {
      const h = makeHotelType({}) as HotelItinerary;
      (h as HotelItinerary).originalTotal = 300;
      expect(getHotelTotal(h)).toBe(300);
    });
    it('prefers total (with platform fee) over originalTotal when both present', () => {
      const h = makeHotelType({}) as HotelItinerary & { total?: number };
      (h as HotelItinerary).originalTotal = 200;
      h.total = 223.46; // price with 10.5% platform fee
      expect(getHotelTotal(h)).toBe(223.46);
    });
  });

  describe('toFilterableHotel', () => {
    it('maps Hotel to FilterableHotel', () => {
      const h = makeHotelType({ name: 'Grand Hotel', starRating: 5 });
      const f = toFilterableHotel(h);
      expect(f.name).toBe('Grand Hotel');
      expect(f.starRating).toBe(5);
      expect(f.total).toBe(200);
      expect(f.currency).toBe('USD');
    });
  });

  describe('isDefaultHotelFilterState', () => {
    it('returns true for default state', () => {
      expect(isDefaultHotelFilterState(defaultHotelFilterState)).toBe(true);
    });
    it('returns false when nameQuery is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, nameQuery: 'spa' })).toBe(false);
    });
    it('returns false when priceMin is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, priceMin: 50 })).toBe(false);
    });
    it('returns false when propertyTypes is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, propertyTypes: ['Hotel'] })).toBe(false);
    });
    it('returns false when distanceMin is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, distanceMin: 1 })).toBe(false);
    });
    it('returns false when facilities is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, facilities: ['WiFi'] })).toBe(false);
    });
    it('returns false when localities is set', () => {
      expect(isDefaultHotelFilterState({ ...defaultHotelFilterState, localities: ['Downtown'] })).toBe(false);
    });
  });

  describe('filterHotels', () => {
    it('returns all hotels when state is default', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', total: 100 }),
        makeHotel({ id: '2', total: 200 }),
      ];
      const result = filterHotels(hotels, defaultHotelFilterState);
      expect(result).toHaveLength(2);
    });

    it('filters by nameQuery', () => {
      const state: HotelFilterState = { ...defaultHotelFilterState, nameQuery: 'Grand' };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', name: 'Grand Plaza' }),
        makeHotel({ id: '2', name: 'Small Inn' }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.name).toBe('Grand Plaza');
    });

    it('filters by priceMin and priceMax', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        priceMin: 150,
        priceMax: 250,
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', total: 100 }),
        makeHotel({ id: '2', total: 200 }),
        makeHotel({ id: '3', total: 300 }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.total).toBe(200);
    });

    it('filters by starRatings', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        starRatings: [4, 5],
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', starRating: 3 }),
        makeHotel({ id: '2', starRating: 4 }),
        makeHotel({ id: '3', starRating: 5 }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(2);
      expect(result.map((h) => h.starRating).sort()).toEqual([4, 5]);
    });

    it('filters by refundableOnly', () => {
      const state: HotelFilterState = { ...defaultHotelFilterState, refundableOnly: true };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', fareType: 'Refundable' }),
        makeHotel({ id: '2', fareType: 'Non-Refundable' }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.fareType).toBe('Refundable');
    });

    it('filters by nonRefundableOnly', () => {
      const state: HotelFilterState = { ...defaultHotelFilterState, nonRefundableOnly: true };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', fareType: 'Refundable' }),
        makeHotel({ id: '2', fareType: 'Non-Refundable' }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.fareType).toBe('Non-Refundable');
    });

    it('filters by propertyTypes', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        propertyTypes: ['Hotel', 'Apartment'],
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', propertyType: 'Hotel' }),
        makeHotel({ id: '2', propertyType: 'Apartment' }),
        makeHotel({ id: '3', propertyType: 'Hostel' }),
        makeHotel({ id: '4' }), // no propertyType → Others
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(2);
      expect(result.map((h) => h.propertyType).sort()).toEqual(['Apartment', 'Hotel']);
    });

    it('filters by distanceMin and distanceMax', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        distanceMin: 1,
        distanceMax: 3,
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', distanceFromCenter: 0.5 }),
        makeHotel({ id: '2', distanceFromCenter: 2 }),
        makeHotel({ id: '3', distanceFromCenter: 4 }),
        makeHotel({ id: '4' }), // no distance → included (no filter applied)
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(2); // id 2 (in range) and id 4 (no distance = pass)
      expect(result.map((h) => h.id).sort()).toEqual(['2', '4']);
    });

    it('filters by facilities (hotel must have all selected - AND)', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        facilities: ['Pool', 'Spa'],
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', facilities: ['WiFi', 'Pool', 'Spa'] }),
        makeHotel({ id: '2', facilities: ['Spa'] }),
        makeHotel({ id: '3', facilities: ['Bar'] }),
        makeHotel({ id: '4', facilities: ['Pool'] }),
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(1);
      expect(result[0]!.id).toBe('1');
    });

    it('filters by localities', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        localities: ['8th Arrondissement', 'Montmartre'],
      };
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', locality: '8th Arrondissement' }),
        makeHotel({ id: '2', locality: 'Montmartre' }),
        makeHotel({ id: '3', locality: 'Le Marais' }),
        makeHotel({ id: '4' }), // no locality
      ];
      const result = filterHotels(hotels, state);
      expect(result).toHaveLength(2);
      expect(result.map((h) => h.id).sort()).toEqual(['1', '2']);
    });
  });

  describe('extractPropertyTypesFromHotels', () => {
    it('returns unique types with Others last', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', propertyType: 'Hotel' }),
        makeHotel({ id: '2', propertyType: 'Apartment' }),
        makeHotel({ id: '3' }), // no type → Others
        makeHotel({ id: '4', propertyType: 'Hotel' }),
      ];
      const types = extractPropertyTypesFromHotels(hotels);
      expect(types).toContain('Hotel');
      expect(types).toContain('Apartment');
      expect(types).toContain('Others');
      expect(types.indexOf('Others')).toBe(types.length - 1);
    });
  });

  describe('getDistanceBounds', () => {
    it('returns hasDistance false when no hotels have distance', () => {
      const hotels: FilterableHotel[] = [makeHotel({ id: '1' }), makeHotel({ id: '2' })];
      const bounds = getDistanceBounds(hotels);
      expect(bounds.hasDistance).toBe(false);
    });
    it('returns min/max when hotels have distanceFromCenter', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', distanceFromCenter: 2.3 }),
        makeHotel({ id: '2', distanceFromCenter: 5.7 }),
      ];
      const bounds = getDistanceBounds(hotels);
      expect(bounds.hasDistance).toBe(true);
      expect(bounds.distanceMin).toBe(2.3);
      expect(bounds.distanceMax).toBe(5.7);
    });
  });

  describe('extractFacilitiesFromHotels', () => {
    it('returns unique sorted facilities', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', facilities: ['Pool', 'WiFi'] }),
        makeHotel({ id: '2', facilities: ['WiFi', 'Bar'] }),
      ];
      const list = extractFacilitiesFromHotels(hotels);
      expect(list).toEqual(['Bar', 'Pool', 'WiFi']);
    });
  });

  describe('extractLocalitiesFromHotels', () => {
    it('returns unique sorted localities', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', locality: 'Montmartre' }),
        makeHotel({ id: '2', locality: '8th Arrondissement' }),
        makeHotel({ id: '3', locality: 'Montmartre' }),
      ];
      const list = extractLocalitiesFromHotels(hotels);
      expect(list).toEqual(['8th Arrondissement', 'Montmartre']);
    });
  });

  describe('countActiveHotelFilters', () => {
    it('returns 0 for default state', () => {
      expect(countActiveHotelFilters(defaultHotelFilterState)).toBe(0);
    });

    it('counts nameQuery', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, nameQuery: 'Paris' })).toBe(1);
    });

    it('counts priceMin', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, priceMin: 50 })).toBe(1);
    });

    it('counts priceMax', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, priceMax: 500 })).toBe(1);
    });

    it('counts priceMin and priceMax as one category', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, priceMin: 50, priceMax: 500 })).toBe(1);
    });

    it('counts starRatings', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, starRatings: [4, 5] })).toBe(1);
    });

    it('counts propertyTypes', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, propertyTypes: ['Hotel'] })).toBe(1);
    });

    it('counts facilities', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, facilities: ['WiFi'] })).toBe(1);
    });

    it('counts localities', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, localities: ['Montmartre'] })).toBe(1);
    });

    it('counts refundableOnly', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, refundableOnly: true })).toBe(1);
    });

    it('counts nonRefundableOnly', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, nonRefundableOnly: true })).toBe(1);
    });

    it('counts refundableOnly and nonRefundableOnly as one category', () => {
      expect(
        countActiveHotelFilters({ ...defaultHotelFilterState, refundableOnly: true, nonRefundableOnly: true })
      ).toBe(1);
    });

    it('counts distanceMin or distanceMax', () => {
      expect(countActiveHotelFilters({ ...defaultHotelFilterState, distanceMin: 0, distanceMax: 5 })).toBe(1);
    });

    it('sums multiple active filter categories', () => {
      const state: HotelFilterState = {
        ...defaultHotelFilterState,
        nameQuery: 'Hilton',
        starRatings: [4, 5],
        facilities: ['Pool'],
        priceMax: 300,
      };
      expect(countActiveHotelFilters(state)).toBe(4);
    });
  });
});
