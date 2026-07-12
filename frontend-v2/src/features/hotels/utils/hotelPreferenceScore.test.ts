import { describe, it, expect } from 'vitest';
import {
  computeHotelPreferenceScore,
  sortHotelsByPreference,
} from './hotelPreferenceScore';
import type { FilterableHotel } from './hotelFilters';
import type { HotelsPreferences, TravelStylePreferences } from '@/types/profile';

function makeHotel(overrides: Partial<FilterableHotel>): FilterableHotel {
  return {
    id: 'h1',
    tokenId: 't1',
    name: 'Test Hotel',
    starRating: 3,
    total: 100,
    currency: 'USD',
    facilities: [],
    ...overrides,
  };
}

function makePrefs(overrides: Partial<HotelsPreferences>): HotelsPreferences {
  return {
    bedType: null,
    roomType: null,
    amenities: [],
    hotelStyle: [],
    locationPreference: [],
    cancellation: [],
    ...overrides,
  };
}

function makeTravelStyle(overrides: Partial<TravelStylePreferences>): TravelStylePreferences {
  return {
    travelPace: null,
    budgetMindset: null,
    accommodation: null,
    activityDensity: null,
    primaryGoals: [],
    gettingAround: [],
    ...overrides,
  };
}

describe('computeHotelPreferenceScore', () => {
  // 1. All three attributes match → score 3
  it('scores 3 when all attributes match', () => {
    const hotel = makeHotel({
      fareType: 'Refundable',
      facilities: ['Swimming Pool', 'Gym'],
      propertyType: 'Hotel',
    });
    const prefs = makePrefs({
      cancellation: ['refundable'],
      amenities: ['pool'],
      roomType: 'hotel',
    });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(3);
  });

  // 2. Zero attributes match → score 0
  it('scores 0 when no attributes match', () => {
    const hotel = makeHotel({
      fareType: 'Non-Refundable',
      facilities: ['WiFi'],
      propertyType: 'Apartment',
    });
    const prefs = makePrefs({
      cancellation: ['refundable'],
      amenities: ['spa'],
      roomType: 'hotel',
    });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 3. Cancellation only: preference "refundable", fareType "Refundable" → score 1
  it('scores 1 for cancellation match: refundable', () => {
    const hotel = makeHotel({ fareType: 'Refundable' });
    const prefs = makePrefs({ cancellation: ['refundable'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 4. Cancellation mismatch: preference "refundable", fareType "Non-Refundable" → score 0
  it('scores 0 for cancellation mismatch: refundable vs Non-Refundable', () => {
    const hotel = makeHotel({ fareType: 'Non-Refundable' });
    const prefs = makePrefs({ cancellation: ['refundable'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 5. nonrefundable: preference "nonrefundable", fareType "Non-Refundable" → score 1
  it('scores 1 for cancellation match: nonrefundable vs Non-Refundable', () => {
    const hotel = makeHotel({ fareType: 'Non-Refundable' });
    const prefs = makePrefs({ cancellation: ['nonrefundable'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 6. nonrefundable mismatch: preference "nonrefundable", fareType "Refundable" → score 0
  it('scores 0 for cancellation mismatch: nonrefundable vs Refundable', () => {
    const hotel = makeHotel({ fareType: 'Refundable' });
    const prefs = makePrefs({ cancellation: ['nonrefundable'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 7. No cancellation preference ([]) → score 0
  it('scores 0 when cancellation preference is empty', () => {
    const hotel = makeHotel({ fareType: 'Refundable' });
    const prefs = makePrefs({ cancellation: [] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 8. Amenities match: user ["pool"], facilities ["Swimming Pool"] → score 1
  it('scores 1 when amenity matches via keyword (pool → Swimming Pool)', () => {
    const hotel = makeHotel({ facilities: ['Swimming Pool'] });
    const prefs = makePrefs({ amenities: ['pool'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 9. Amenities no match: user ["spa"], facilities ["Gym", "Pool"] → score 0
  it('scores 0 when no amenity keyword matches', () => {
    const hotel = makeHotel({ facilities: ['Gym', 'Pool'] });
    const prefs = makePrefs({ amenities: ['spa'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 10. Amenities empty ([]) → score 0
  it('scores 0 when amenities preference is empty', () => {
    const hotel = makeHotel({ facilities: ['Spa', 'Pool'] });
    const prefs = makePrefs({ amenities: [] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 11. Amenities partial: only one of multiple preferred matches → still score 1
  it('scores 1 when at least one of multiple preferred amenities matches', () => {
    const hotel = makeHotel({ facilities: ['Swimming Pool'] });
    const prefs = makePrefs({ amenities: ['spa', 'pool', 'gym'] });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 12. roomType match: preference "hotel", propertyType "Hotel" → score 1
  it('scores 1 for roomType match: hotel vs Hotel', () => {
    const hotel = makeHotel({ propertyType: 'Hotel' });
    const prefs = makePrefs({ roomType: 'hotel' });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 13. roomType match: preference "apartment", propertyType "Serviced Apartment" → score 1
  it('scores 1 for roomType substring match: apartment vs Serviced Apartment', () => {
    const hotel = makeHotel({ propertyType: 'Serviced Apartment' });
    const prefs = makePrefs({ roomType: 'apartment' });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(1);
  });

  // 14. roomType mismatch: preference "hotel", propertyType "Apartment" → score 0
  it('scores 0 for roomType mismatch: hotel vs Apartment', () => {
    const hotel = makeHotel({ propertyType: 'Apartment' });
    const prefs = makePrefs({ roomType: 'hotel' });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 15. roomType null → score 0
  it('scores 0 when roomType preference is null', () => {
    const hotel = makeHotel({ propertyType: 'Hotel' });
    const prefs = makePrefs({ roomType: null });
    expect(computeHotelPreferenceScore(hotel, prefs)).toBe(0);
  });

  // 16. prefs = null → score 0 for all
  it('scores 0 when prefs is null', () => {
    const hotel = makeHotel({
      fareType: 'Refundable',
      facilities: ['Pool'],
      propertyType: 'Hotel',
    });
    expect(computeHotelPreferenceScore(hotel, null)).toBe(0);
  });

  // Star rating via travelStyle.accommodation
  it('scores 1 when accommodation is "4" and hotel is 4-star', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 4 }), null, makeTravelStyle({ accommodation: '4' }))).toBe(1);
  });

  it('scores 1 when accommodation is "4" and hotel is 5-star', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 5 }), null, makeTravelStyle({ accommodation: '4' }))).toBe(1);
  });

  it('scores 0 when accommodation is "4" and hotel is 3-star', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 3 }), null, makeTravelStyle({ accommodation: '4' }))).toBe(0);
  });

  it('scores 1 when accommodation is "5" and hotel is 5-star', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 5 }), null, makeTravelStyle({ accommodation: '5' }))).toBe(1);
  });

  it('scores 0 when accommodation is "5" and hotel is 4-star', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 4 }), null, makeTravelStyle({ accommodation: '5' }))).toBe(0);
  });

  it('scores 0 when accommodation is "noPref"', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 5 }), null, makeTravelStyle({ accommodation: 'noPref' }))).toBe(0);
  });

  it('scores 0 when prefs is null and travelStyle is null/undefined', () => {
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 5 }), null)).toBe(0);
    expect(computeHotelPreferenceScore(makeHotel({ starRating: 5 }), null, null)).toBe(0);
  });

  it('scores 4 when all hotel prefs and accommodation match', () => {
    const hotel = makeHotel({
      fareType: 'Refundable',
      facilities: ['Swimming Pool'],
      propertyType: 'Hotel',
      starRating: 5,
    });
    const prefs = makePrefs({ cancellation: ['refundable'], amenities: ['pool'], roomType: 'hotel' });
    const ts = makeTravelStyle({ accommodation: '5' });
    expect(computeHotelPreferenceScore(hotel, prefs, ts)).toBe(4);
  });
});

describe('sortHotelsByPreference', () => {
  // 17. Correct descending-score order with price tiebreaker
  it('sorts hotels descending by score with price tiebreaker', () => {
    const prefs = makePrefs({
      cancellation: ['refundable'],
      amenities: ['pool'],
      roomType: 'hotel',
    });
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'a', fareType: 'Non-Refundable', facilities: [], propertyType: 'Apartment', total: 100 }),
      makeHotel({ id: 'b', fareType: 'Refundable', facilities: ['Swimming Pool'], propertyType: 'Hotel', total: 200 }),
      makeHotel({ id: 'c', fareType: 'Refundable', facilities: [], propertyType: 'Apartment', total: 150 }),
    ];
    const result = sortHotelsByPreference(hotels, prefs);
    expect(result.map((h) => h.id)).toEqual(['b', 'c', 'a']);
  });

  // 17b. Price tiebreaker: two hotels with the same score are sorted by ascending price
  it('applies ascending price tiebreaker when scores are equal', () => {
    const prefs = makePrefs({ cancellation: ['refundable'] });
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'x', fareType: 'Refundable', total: 300 }),
      makeHotel({ id: 'y', fareType: 'Refundable', total: 150 }),
    ];
    const result = sortHotelsByPreference(hotels, prefs);
    expect(result.map((h) => h.id)).toEqual(['y', 'x']);
  });

  // 18. prefs = null → returns price-ascending order
  it('falls back to price-ascending when prefs is null', () => {
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'a', total: 300 }),
      makeHotel({ id: 'b', total: 100 }),
      makeHotel({ id: 'c', total: 200 }),
    ];
    const result = sortHotelsByPreference(hotels, null);
    expect(result.map((h) => h.total)).toEqual([100, 200, 300]);
  });

  // 19. Does not mutate input array
  it('does not mutate the input array', () => {
    const prefs = makePrefs({ cancellation: ['refundable'] });
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'a', total: 300 }),
      makeHotel({ id: 'b', total: 100 }),
    ];
    const original = [...hotels];
    sortHotelsByPreference(hotels, prefs);
    expect(hotels).toEqual(original);
  });

  it('sorts by accommodation star rating from travelStyle when prefs is null', () => {
    const ts = makeTravelStyle({ accommodation: '5' });
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'a', starRating: 3, total: 100 }),
      makeHotel({ id: 'b', starRating: 5, total: 300 }),
      makeHotel({ id: 'c', starRating: 4, total: 200 }),
    ];
    const result = sortHotelsByPreference(hotels, null, ts);
    expect(result[0]!.id).toBe('b'); // only 5-star scores 1
  });

  it('sorts 4-star preference: 4-star before 5-star (price tiebreaker), then 3-star last', () => {
    const ts = makeTravelStyle({ accommodation: '4' });
    const hotels: FilterableHotel[] = [
      makeHotel({ id: 'a', starRating: 3, total: 100 }),
      makeHotel({ id: 'b', starRating: 5, total: 300 }),
      makeHotel({ id: 'c', starRating: 4, total: 200 }),
    ];
    const result = sortHotelsByPreference(hotels, null, ts);
    expect(result.map((h) => h.id)).toEqual(['c', 'b', 'a']);
  });
});
