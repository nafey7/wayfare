import { describe, it, expect } from 'vitest';
import {
  sortHotels,
  getHotelPrice,
  getHotelRating,
  getHotelName,
  DEFAULT_HOTEL_SORT,
  HOTEL_SORT_OPTIONS,
  getHotelSortMenuItems,
} from './hotelSort';
import type { FilterableHotel } from './hotelFilters';

function makeHotel(overrides: Partial<FilterableHotel>): FilterableHotel {
  return {
    id: 'h1',
    tokenId: 't1',
    name: 'Hotel A',
    starRating: 4,
    total: 200,
    currency: 'USD',
    facilities: [],
    ...overrides,
  };
}

describe('hotelSort', () => {
  describe('DEFAULT_HOTEL_SORT and HOTEL_SORT_OPTIONS', () => {
    it('default is price-low', () => {
      expect(DEFAULT_HOTEL_SORT).toBe('price-low');
    });
    it('HOTEL_SORT_OPTIONS includes all options', () => {
      expect(HOTEL_SORT_OPTIONS).toContain('preference-match');
      expect(HOTEL_SORT_OPTIONS).toContain('recommended');
      expect(HOTEL_SORT_OPTIONS).toContain('price-low');
      expect(HOTEL_SORT_OPTIONS).toContain('price-high');
      expect(HOTEL_SORT_OPTIONS).toContain('rating-high');
      expect(HOTEL_SORT_OPTIONS).toContain('rating-low');
      expect(HOTEL_SORT_OPTIONS).toContain('name-az');
      expect(HOTEL_SORT_OPTIONS).toHaveLength(7);
    });
  });

  describe('getHotelPrice, getHotelRating, getHotelName', () => {
    it('returns total, starRating, name', () => {
      const h = makeHotel({ total: 199, starRating: 5, name: 'Grand' });
      expect(getHotelPrice(h)).toBe(199);
      expect(getHotelRating(h)).toBe(5);
      expect(getHotelName(h)).toBe('Grand');
    });
  });

  describe('getHotelSortMenuItems', () => {
    it('always prepends preference-match as first item', () => {
      const items = getHotelSortMenuItems(false);
      expect(items[0]).toEqual({ value: 'preference-match', label: 'Your preferences' });
    });

    it('omits recommended when nearby location is unavailable', () => {
      const items = getHotelSortMenuItems(false);
      expect(items.map((item) => item.value)).not.toContain('recommended');
      expect(items).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ value: 'price-low' }),
          expect.objectContaining({ value: 'price-high' }),
        ])
      );
    });

    it('includes both preference-match (first) and recommended when nearby location is available', () => {
      const items = getHotelSortMenuItems(true);
      expect(items[0]).toEqual({ value: 'preference-match', label: 'Your preferences' });
      expect(items[1]).toEqual({ value: 'recommended', label: 'Nearest First' });
    });
  });

  describe('sortHotels', () => {
    it('sorts by price-low', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', total: 300 }),
        makeHotel({ id: '2', total: 100 }),
        makeHotel({ id: '3', total: 200 }),
      ];
      const result = sortHotels(hotels, 'price-low');
      expect(result.map((h) => h.total)).toEqual([100, 200, 300]);
    });

    it('sorts by price-high', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', total: 100 }),
        makeHotel({ id: '2', total: 300 }),
        makeHotel({ id: '3', total: 200 }),
      ];
      const result = sortHotels(hotels, 'price-high');
      expect(result.map((h) => h.total)).toEqual([300, 200, 100]);
    });

    it('sorts by rating-high', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', starRating: 3 }),
        makeHotel({ id: '2', starRating: 5 }),
        makeHotel({ id: '3', starRating: 4 }),
      ];
      const result = sortHotels(hotels, 'rating-high');
      expect(result.map((h) => h.starRating)).toEqual([5, 4, 3]);
    });

    it('sorts by rating-low', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', starRating: 5 }),
        makeHotel({ id: '2', starRating: 3 }),
        makeHotel({ id: '3', starRating: 4 }),
      ];
      const result = sortHotels(hotels, 'rating-low');
      expect(result.map((h) => h.starRating)).toEqual([3, 4, 5]);
    });

    it('sorts by name-az', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', name: 'Zebra Inn' }),
        makeHotel({ id: '2', name: 'Alpha Hotel' }),
        makeHotel({ id: '3', name: 'Mango Resort' }),
      ];
      const result = sortHotels(hotels, 'name-az');
      expect(result.map((h) => h.name)).toEqual(['Alpha Hotel', 'Mango Resort', 'Zebra Inn']);
    });

    it('does not mutate input array', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', total: 200 }),
        makeHotel({ id: '2', total: 100 }),
      ];
      const copy = [...hotels];
      sortHotels(hotels, 'price-low');
      expect(hotels).toEqual(copy);
    });

    it('sorts by recommended (nearbyDistanceKm ascending)', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', nearbyDistanceKm: 5.0 }),
        makeHotel({ id: '2', nearbyDistanceKm: 1.2 }),
        makeHotel({ id: '3', nearbyDistanceKm: 3.4 }),
      ];
      const result = sortHotels(hotels, 'recommended');
      expect(result.map((h) => h.nearbyDistanceKm)).toEqual([1.2, 3.4, 5.0]);
    });

    it('recommended puts undefined nearbyDistanceKm last', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', nearbyDistanceKm: undefined }),
        makeHotel({ id: '2', nearbyDistanceKm: 2.5 }),
        makeHotel({ id: '3', nearbyDistanceKm: undefined }),
      ];
      const result = sortHotels(hotels, 'recommended');
      expect(result[0]!.id).toBe('2');
      expect(result[0]!.nearbyDistanceKm).toBe(2.5);
      expect(result[1]!.nearbyDistanceKm).toBeUndefined();
      expect(result[2]!.nearbyDistanceKm).toBeUndefined();
    });

    it('recommended with all undefined nearbyDistanceKm preserves relative order', () => {
      const hotels: FilterableHotel[] = [
        makeHotel({ id: '1', nearbyDistanceKm: undefined }),
        makeHotel({ id: '2', nearbyDistanceKm: undefined }),
      ];
      const result = sortHotels(hotels, 'recommended');
      expect(result.map((h) => h.id)).toEqual(['1', '2']);
    });

    it('throws when called with preference-match', () => {
      const hotels: FilterableHotel[] = [makeHotel({ id: '1', total: 100 })];
      expect(() => sortHotels(hotels, 'preference-match')).toThrow(
        'preference-match must be sorted via sortHotelsByPreference'
      );
    });
  });
});
