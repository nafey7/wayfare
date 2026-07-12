import { describe, it, expect } from 'vitest';
import { chatSearchParamsToUI, extractChatFilters, chatFiltersToFilterState } from './chatSearchParamsToUI';
import { serializeSearchParamsToUrl, deserializeSearchParamsFromUrl } from '@/features/flights/utils/urlParams';
import { defaultFlightFilterState } from '@/features/flights/utils/flightFilters';
import type { FlightSearchParams } from '@/types/api.helpers';

describe('chatSearchParamsToUI', () => {
  const baseParams: FlightSearchParams = {
    origin: 'LHR',
    destination: 'JFK',
    departure_date: '2026-03-15',
    return_date: '2026-03-22',
    journey_type: 'Return',
    passengers: { adults: 2, children: 1, infants: 0 },
  };

  it('maps origin/destination to from/to', () => {
    const result = chatSearchParamsToUI(baseParams);
    expect(result.from).toBe('LHR');
    expect(result.to).toBe('JFK');
  });

  it('prefers origin_city/destination_city over IATA codes', () => {
    const result = chatSearchParamsToUI({
      ...baseParams,
      origin_city: 'London',
      destination_city: 'New York',
    });
    expect(result.from).toBe('London');
    expect(result.to).toBe('New York');
  });

  it('falls back to IATA codes when city names are null', () => {
    const result = chatSearchParamsToUI({
      ...baseParams,
      origin_city: null,
      destination_city: null,
    });
    expect(result.from).toBe('LHR');
    expect(result.to).toBe('JFK');
  });

  it('maps OneWay to one-way tripType', () => {
    const result = chatSearchParamsToUI({ ...baseParams, journey_type: 'OneWay' });
    expect(result.tripType).toBe('one-way');
  });

  it('maps Return to round-trip tripType', () => {
    const result = chatSearchParamsToUI({ ...baseParams, journey_type: 'Return' });
    expect(result.tripType).toBe('round-trip');
  });

  it('maps RoundTrip to round-trip tripType', () => {
    const result = chatSearchParamsToUI({ ...baseParams, journey_type: 'RoundTrip' });
    expect(result.tripType).toBe('round-trip');
  });

  it('maps Circle to round-trip tripType', () => {
    const result = chatSearchParamsToUI({ ...baseParams, journey_type: 'Circle' });
    expect(result.tripType).toBe('round-trip');
  });

  it('converts departure_date and return_date to Date objects', () => {
    const result = chatSearchParamsToUI(baseParams);
    expect(result.date).toBeInstanceOf(Date);
    expect(result.date!.toISOString()).toMatch(/2026-03-15/);
    expect(result.returnDate).toBeInstanceOf(Date);
    expect(result.returnDate!.toISOString()).toMatch(/2026-03-22/);
  });

  it('maps passengers to travellers with cabinClass default', () => {
    const result = chatSearchParamsToUI(baseParams);
    expect(result.travellers.adults).toBe(2);
    expect(result.travellers.children).toBe(1);
    expect(result.travellers.infants).toBe(0);
    expect(result.travellers.cabinClass).toBe('Economy');
  });

  it('defaults passengers when missing', () => {
    const params = {
      ...baseParams,
      passengers: undefined as unknown as FlightSearchParams['passengers'],
    };
    const result = chatSearchParamsToUI(params as FlightSearchParams);
    expect(result.travellers.adults).toBe(1);
    expect(result.travellers.children).toBe(0);
    expect(result.travellers.infants).toBe(0);
  });

  it('handles null return_date', () => {
    const result = chatSearchParamsToUI({ ...baseParams, return_date: null });
    expect(result.returnDate).toBeUndefined();
  });

  it('produces UI params that round-trip through URL (see full results flow)', () => {
    const uiParams = chatSearchParamsToUI(baseParams);
    const encoded = serializeSearchParamsToUrl(uiParams);
    expect(encoded).toBeTruthy();
    const decoded = deserializeSearchParamsFromUrl(encoded);
    expect(decoded).not.toBeNull();
    expect(decoded!.from).toBe(baseParams.origin);
    expect(decoded!.to).toBe(baseParams.destination);
    expect(decoded!.tripType).toBe('round-trip');
    expect(decoded!.travellers.adults).toBe(baseParams.passengers.adults);
  });

  it('passes through originIsCity and destinationIsCity', () => {
    const result = chatSearchParamsToUI({
      ...baseParams,
      origin_is_city: true,
      destination_is_city: false,
    });
    expect(result.originIsCity).toBe(true);
    expect(result.destinationIsCity).toBe(false);
  });

  describe('cabin_class mapping', () => {
    it('maps "Business" cabin_class to Business', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'Business' });
      expect(result.travellers.cabinClass).toBe('Business');
    });

    it('maps "First" cabin_class to First', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'First' });
      expect(result.travellers.cabinClass).toBe('First');
    });

    it('maps "Premium Economy" cabin_class to Premium Economy', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'Premium Economy' });
      expect(result.travellers.cabinClass).toBe('Premium Economy');
    });

    it('maps "economy" (lowercase) to Economy', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'economy' });
      expect(result.travellers.cabinClass).toBe('Economy');
    });

    it('maps "business" (lowercase) to Business', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'business' });
      expect(result.travellers.cabinClass).toBe('Business');
    });

    it('defaults to Economy when cabin_class is undefined', () => {
      const result = chatSearchParamsToUI(baseParams);
      expect(result.travellers.cabinClass).toBe('Economy');
    });

    it('defaults to Economy for unknown cabin_class', () => {
      const result = chatSearchParamsToUI({ ...baseParams, cabin_class: 'SuperLuxury' });
      expect(result.travellers.cabinClass).toBe('Economy');
    });
  });
});

describe('extractChatFilters', () => {
  const baseParams: FlightSearchParams = {
    origin: 'LHR',
    destination: 'JFK',
    departure_date: '2026-03-15',
    return_date: null,
    journey_type: 'OneWay',
    passengers: { adults: 1, children: 0, infants: 0 },
  };

  it('returns null when no filters are set', () => {
    expect(extractChatFilters(baseParams)).toBeNull();
  });

  it('returns null when cabin_class is Economy (default)', () => {
    expect(extractChatFilters({ ...baseParams, cabin_class: 'Economy' })).toBeNull();
  });

  it('extracts directOnly from direct_flight=1', () => {
    const filters = extractChatFilters({ ...baseParams, direct_flight: 1 });
    expect(filters).not.toBeNull();
    expect(filters!.directOnly).toBe(true);
  });

  it('extracts directOnly from max_stops=0', () => {
    const filters = extractChatFilters({ ...baseParams, max_stops: 0 });
    expect(filters).not.toBeNull();
    expect(filters!.directOnly).toBe(true);
  });

  it('does not set directOnly when direct_flight=0', () => {
    expect(extractChatFilters({ ...baseParams, direct_flight: 0 })).toBeNull();
  });

  it('extracts price_min and price_max', () => {
    const filters = extractChatFilters({ ...baseParams, price_min: 100, price_max: 500 });
    expect(filters).not.toBeNull();
    expect(filters!.priceMin).toBe(100);
    expect(filters!.priceMax).toBe(500);
  });

  it('extracts preferred_airline as single-element array', () => {
    const filters = extractChatFilters({ ...baseParams, preferred_airline: 'BA' });
    expect(filters).not.toBeNull();
    expect(filters!.airlines).toEqual(['BA']);
  });

  it('does not extract cabin_class as post-filter (handled at API level)', () => {
    expect(extractChatFilters({ ...baseParams, cabin_class: 'Business' })).toBeNull();
  });

  it('extracts duration limits', () => {
    const filters = extractChatFilters({
      ...baseParams,
      max_outbound_duration: 600,
      max_inbound_duration: 480,
    });
    expect(filters).not.toBeNull();
    expect(filters!.outboundDurationMax).toBe(600);
    expect(filters!.inboundDurationMax).toBe(480);
  });

  it('extracts combined filters', () => {
    const filters = extractChatFilters({
      ...baseParams,
      direct_flight: 1,
      price_max: 500,
      preferred_airline: 'BA',
    });
    expect(filters).not.toBeNull();
    expect(filters!.directOnly).toBe(true);
    expect(filters!.priceMax).toBe(500);
    expect(filters!.airlines).toEqual(['BA']);
  });
});

describe('chatFiltersToFilterState', () => {
  it('spreads chat filters over default filter state', () => {
    const state = chatFiltersToFilterState({
      priceMin: null,
      priceMax: 500,
      directOnly: true,
      airlines: ['BA'],
      outboundDurationMax: null,
      inboundDurationMax: null,
    });

    expect(state.priceMax).toBe(500);
    expect(state.directOnly).toBe(true);
    expect(state.airlines).toEqual(['BA']);
    expect(state.priceMin).toBeNull();
    expect(state.stops1).toBe(defaultFlightFilterState.stops1);
  });

  it('preserves all default fields not in ChatFlightFilters', () => {
    const state = chatFiltersToFilterState({
      priceMin: null,
      priceMax: null,
      directOnly: false,
      airlines: [],
      outboundDurationMax: null,
      inboundDurationMax: null,
    });

    expect(state).toEqual(defaultFlightFilterState);
  });
});
