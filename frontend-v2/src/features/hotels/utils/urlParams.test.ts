import { describe, it, expect, vi } from 'vitest';
import {
  chatHotelSearchParamsToUI,
  serializeHotelSearchParamsToUrl,
  deserializeHotelSearchParamsFromUrl,
  extractChatHotelFilters,
  chatHotelFiltersToFilterState,
  serializeChatHotelFiltersToUrl,
  deserializeChatHotelFiltersFromUrl,
  buildHotelSearchUrlPath,
} from './urlParams';
import type { HotelSearchFormParams } from '@/types/hotels';
import type { ChatHotelFilters } from './urlParams';
import { defaultHotelFilterState } from './hotelFilters';

describe('chatHotelSearchParamsToUI', () => {
  it('maps destination_city to destination (city only, no country)', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Paris',
      country: 'France',
      check_in_date: '2026-03-15',
      check_out_date: '2026-03-18',
    });
    expect(result.destination).toBe('Paris');
  });

  it('uses city_name when destination_city is missing', () => {
    const result = chatHotelSearchParamsToUI({
      city_name: 'London',
      country: 'UK',
      check_in_date: '2026-04-01',
      check_out_date: '2026-04-03',
    });
    expect(result.destination).toBe('London');
  });

  it('uses destination when provided', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Barcelona',
      check_in_date: '2026-05-10',
      check_out_date: '2026-05-12',
    });
    expect(result.destination).toBe('Barcelona');
  });

  it('maps check_in_date and check_out_date to checkin/checkout', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Rome',
      check_in_date: '2026-03-20',
      check_out_date: '2026-03-23',
    });
    expect(result.checkin).toBe('2026-03-20');
    expect(result.checkout).toBe('2026-03-23');
  });

  it('accepts checkin/checkout as alternates', () => {
    const result = chatHotelSearchParamsToUI({
      city_name: 'Berlin',
      checkin: '2026-06-01',
      checkout: '2026-06-05',
    });
    expect(result.checkin).toBe('2026-06-01');
    expect(result.checkout).toBe('2026-06-05');
  });

  it('maps rooms, adults, children to RoomOccupancy array', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Madrid',
      check_in_date: '2026-04-01',
      check_out_date: '2026-04-03',
      rooms: 1,
      adults: 3,
      children: 1,
    });
    expect(result.rooms).toHaveLength(1);
    const room = result.rooms![0]!;
    expect(room.adult).toBe(3);
    expect(room.child).toBe(1);
    expect(room.childAge).toEqual([5]);
  });

  it('defaults to 1 room, 2 adults, 0 children when missing', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Vienna',
      check_in_date: '2026-05-01',
      check_out_date: '2026-05-03',
    });
    expect(result.rooms).toHaveLength(1);
    const room0 = result.rooms![0]!;
    expect(room0.adult).toBe(2);
    expect(room0.child).toBe(0);
  });

  it('returns nationality US', () => {
    const result = chatHotelSearchParamsToUI({
      destination_city: 'Amsterdam',
      check_in_date: '2026-06-01',
      check_out_date: '2026-06-04',
    });
    expect(result.nationality).toBe('US');
  });

  it('produces UI params that round-trip through URL (see full results flow)', () => {
    const chatParams = {
      destination_city: 'Paris',
      country: 'France',
      check_in_date: '2026-03-15',
      check_out_date: '2026-03-18',
      rooms: 2,
      adults: 4,
      children: 1,
    };
    const uiParams = chatHotelSearchParamsToUI(chatParams);
    const encoded = serializeHotelSearchParamsToUrl(uiParams);
    expect(encoded).toBeTruthy();
    const decoded = deserializeHotelSearchParamsFromUrl(encoded);
    expect(decoded).not.toBeNull();
    expect(decoded!.destination).toBe('Paris');
    expect(decoded!.checkin).toBe(chatParams.check_in_date);
    expect(decoded!.checkout).toBe(chatParams.check_out_date);
    expect(decoded!.rooms).toHaveLength(2);
    const firstRoom = decoded!.rooms![0]!;
    expect(firstRoom.adult).toBe(4);
    expect(firstRoom.child).toBe(1);
  });

  it('handles Record<string, unknown> from chat extraData', () => {
    const raw = {
      destination_city: 'Tokyo',
      country_name: 'Japan',
      check_in_date: '2026-07-01',
      check_out_date: '2026-07-05',
    } as Record<string, unknown>;
    const result = chatHotelSearchParamsToUI(raw);
    expect(result.destination).toBe('Tokyo');
    expect(result.checkin).toBe('2026-07-01');
    expect(result.checkout).toBe('2026-07-05');
  });
});

describe('buildHotelSearchUrlPath', () => {
  const minimal: HotelSearchFormParams = {
    destination: 'Lyon',
    checkin: '2026-08-01',
    checkout: '2026-08-05',
    rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
    nationality: 'US',
  };

  it('returns null without destination', () => {
    expect(buildHotelSearchUrlPath({ ...minimal, destination: '' })).toBeNull();
  });

  it('returns null without check-in', () => {
    expect(buildHotelSearchUrlPath({ ...minimal, checkin: null })).toBeNull();
    expect(buildHotelSearchUrlPath({ ...minimal, checkin: '' })).toBeNull();
  });

  it('fills missing checkout as the day after check-in', () => {
    const path = buildHotelSearchUrlPath({
      ...minimal,
      checkout: null,
    });
    expect(path).not.toBeNull();
    expect(path).toMatch(/^\/hotels\/search\?q=/);
    const q = path!.split('?q=')[1] as string;
    const json = JSON.parse(atob(decodeURIComponent(q))) as HotelSearchFormParams;
    expect(json.checkout).toBe('2026-08-02');
    expect(json.checkin).toBe('2026-08-01');
    expect(json.destination).toBe('Lyon');
  });

  it('uses explicit checkout when present', () => {
    const path = buildHotelSearchUrlPath(minimal);
    expect(path).not.toBeNull();
    const q = path!.split('?q=')[1] as string;
    const json = JSON.parse(atob(decodeURIComponent(q))) as HotelSearchFormParams;
    expect(json.checkout).toBe('2026-08-05');
  });
});

describe('extractChatHotelFilters', () => {
  it('returns null when no filters are set', () => {
    expect(extractChatHotelFilters({
      destination_city: 'Paris',
      check_in_date: '2026-03-15',
      check_out_date: '2026-03-18',
    })).toBeNull();
  });

  it('extracts price_min and price_max', () => {
    const filters = extractChatHotelFilters({ price_min: 50, price_max: 300 });
    expect(filters).not.toBeNull();
    expect(filters!.priceMin).toBe(50);
    expect(filters!.priceMax).toBe(300);
  });

  it('extracts min_rating as starRatings array', () => {
    const filters = extractChatHotelFilters({ min_rating: 4 });
    expect(filters).not.toBeNull();
    expect(filters!.starRatings).toEqual([4, 5]);
  });

  it('extracts min_rating 3 as [3, 4, 5]', () => {
    const filters = extractChatHotelFilters({ min_rating: 3 });
    expect(filters!.starRatings).toEqual([3, 4, 5]);
  });

  it('extracts property_types', () => {
    const filters = extractChatHotelFilters({ property_types: ['Hotel', 'Resort'] });
    expect(filters).not.toBeNull();
    expect(filters!.propertyTypes).toEqual(['Hotel', 'Resort']);
  });

  it('extracts refundable_only', () => {
    const filters = extractChatHotelFilters({ refundable_only: true });
    expect(filters).not.toBeNull();
    expect(filters!.refundableOnly).toBe(true);
  });

  it('extracts required_facilities', () => {
    const filters = extractChatHotelFilters({ required_facilities: ['WiFi', 'Pool'] });
    expect(filters).not.toBeNull();
    expect(filters!.facilities).toEqual(['WiFi', 'Pool']);
  });

  it('extracts max_distance_km', () => {
    const filters = extractChatHotelFilters({ max_distance_km: 5 });
    expect(filters).not.toBeNull();
    expect(filters!.distanceMax).toBe(5);
  });

  it('extracts locality as single-element localities array', () => {
    const filters = extractChatHotelFilters({ locality: 'Marais' });
    expect(filters).not.toBeNull();
    expect(filters!.localities).toEqual(['Marais']);
  });

  it('extracts combined filters', () => {
    const filters = extractChatHotelFilters({
      price_max: 200,
      min_rating: 4,
      refundable_only: true,
      required_facilities: ['WiFi'],
    });
    expect(filters).not.toBeNull();
    expect(filters!.priceMax).toBe(200);
    expect(filters!.starRatings).toEqual([4, 5]);
    expect(filters!.refundableOnly).toBe(true);
    expect(filters!.facilities).toEqual(['WiFi']);
  });
});

describe('chatHotelFiltersToFilterState', () => {
  it('spreads chat filters over default filter state', () => {
    const state = chatHotelFiltersToFilterState({
      priceMin: null,
      priceMax: 200,
      starRatings: [4, 5],
      propertyTypes: ['Hotel'],
      refundableOnly: true,
      facilities: ['WiFi'],
      distanceMax: null,
      localities: [],
    });
    expect(state.priceMax).toBe(200);
    expect(state.starRatings).toEqual([4, 5]);
    expect(state.propertyTypes).toEqual(['Hotel']);
    expect(state.refundableOnly).toBe(true);
    expect(state.facilities).toEqual(['WiFi']);
    expect(state.nameQuery).toBe(defaultHotelFilterState.nameQuery);
    expect(state.nonRefundableOnly).toBe(defaultHotelFilterState.nonRefundableOnly);
  });

  it('preserves all default fields not in ChatHotelFilters', () => {
    const state = chatHotelFiltersToFilterState({
      priceMin: null,
      priceMax: null,
      starRatings: [],
      propertyTypes: [],
      refundableOnly: false,
      facilities: [],
      distanceMax: null,
      localities: [],
    });
    expect(state).toEqual(defaultHotelFilterState);
  });
});

describe('serializeChatHotelFiltersToUrl / deserializeChatHotelFiltersFromUrl', () => {
  const sampleFilters: ChatHotelFilters = {
    priceMin: 50,
    priceMax: 300,
    starRatings: [4, 5],
    propertyTypes: ['Hotel'],
    refundableOnly: true,
    facilities: ['WiFi', 'Pool'],
    distanceMax: 5,
    localities: ['Marais'],
  };

  it('round-trips chat hotel filters through serialize/deserialize', () => {
    const encoded = serializeChatHotelFiltersToUrl(sampleFilters);
    expect(encoded).toBeTruthy();
    const decoded = deserializeChatHotelFiltersFromUrl(encoded);
    expect(decoded).not.toBeNull();
    expect(decoded!.priceMin).toBe(50);
    expect(decoded!.priceMax).toBe(300);
    expect(decoded!.starRatings).toEqual([4, 5]);
    expect(decoded!.propertyTypes).toEqual(['Hotel']);
    expect(decoded!.refundableOnly).toBe(true);
    expect(decoded!.facilities).toEqual(['WiFi', 'Pool']);
    expect(decoded!.distanceMax).toBe(5);
    expect(decoded!.localities).toEqual(['Marais']);
  });

  it('handles empty/null filter values', () => {
    const emptyFilters: ChatHotelFilters = {
      priceMin: null,
      priceMax: null,
      starRatings: [],
      propertyTypes: [],
      refundableOnly: false,
      facilities: [],
      distanceMax: null,
      localities: [],
    };
    const encoded = serializeChatHotelFiltersToUrl(emptyFilters);
    const decoded = deserializeChatHotelFiltersFromUrl(encoded);
    expect(decoded).not.toBeNull();
    expect(decoded!.priceMin).toBeNull();
    expect(decoded!.starRatings).toEqual([]);
    expect(decoded!.refundableOnly).toBe(false);
  });

  it('returns null for invalid base64', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(deserializeChatHotelFiltersFromUrl('not-valid!!!')).toBeNull();
    consoleSpy.mockRestore();
  });

  it('returns null for invalid JSON inside base64', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(deserializeChatHotelFiltersFromUrl(btoa('{ invalid json'))).toBeNull();
    consoleSpy.mockRestore();
  });

  it('defaults missing fields in deserialized filters', () => {
    const partial = btoa(JSON.stringify({ priceMax: 200 }));
    const decoded = deserializeChatHotelFiltersFromUrl(partial);
    expect(decoded).not.toBeNull();
    expect(decoded!.priceMax).toBe(200);
    expect(decoded!.priceMin).toBeNull();
    expect(decoded!.starRatings).toEqual([]);
    expect(decoded!.propertyTypes).toEqual([]);
    expect(decoded!.refundableOnly).toBe(false);
    expect(decoded!.facilities).toEqual([]);
    expect(decoded!.distanceMax).toBeNull();
    expect(decoded!.localities).toEqual([]);
  });
});
