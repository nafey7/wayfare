/**
 * Unit tests for flightUtils (flights feature).
 * Covers flightCardToMappedFlight and buildLayoversFromFlightSegments behavior.
 */

import { describe, it, expect } from 'vitest';
import {
  buildProcessedLegsForSearchItinerary,
  findRoundTripSegmentSplitIndex,
  flightCardToMappedFlight,
  getAirlineLogoUrl,
  isRoundTripSearchMissingReturnDate,
  roundTripBoundLabelPerVendorLeg,
  tripDetailsSegmentOutboundReturnLabels,
  type FlightCardFlightInput,
} from './flightUtils';
import type { FlightSearchParamsUI } from '@/types/flights';
import type { FlightLegCamel, FlightSegmentCamel } from '@/types/flightBackend';

/** Minimal leg shape for FlightCardFlightInput */
function makeLeg(overrides: Partial<FlightCardFlightInput['legs'][number]> = {}) {
  return {
    departure: { city: 'London', airport: 'LHR', date: '2026-03-15', time: '10:00' },
    arrival: { city: 'New York', airport: 'JFK', date: '2026-03-15', time: '18:00' },
    duration: '8h 0m',
    stops: 0,
    stopsText: 'Non-stop',
    ...overrides,
  };
}

/** Minimal FlightSegmentCamel for layover tests */
function makeSegment(overrides: Partial<FlightSegmentCamel> = {}): FlightSegmentCamel {
  return {
    departureDatetime: '2026-03-15T10:00:00',
    arrivalDatetime: '2026-03-15T14:00:00',
    departureAirport: { iataCode: 'LHR', cityName: 'London' },
    arrivalAirport: { iataCode: 'CDG', cityName: 'Paris' },
    marketingAirline: { iataCode: 'BA', airlineName: 'British Airways' },
    marketingFlightNumber: { formattedNumber: 'BA301' },
    ...overrides,
  };
}

describe('flightCardToMappedFlight', () => {
  it('maps one-way flight (single leg)', () => {
    const flight: FlightCardFlightInput = {
      id: 'f1',
      aircraftName: 'British Airways',
      tags: ['cheapest'],
      passengers: 2,
      legs: [makeLeg()],
      price: 450,
    };

    const result = flightCardToMappedFlight(flight);

    expect(result.id).toBe('f1');
    expect(result.price).toBe(450);
    expect(result.currency).toBe('USD');
    expect(result.is_round_trip).toBe(false);
    expect(result.outbound).toBeDefined();
    expect(result.outbound.origin_code).toBe('LHR');
    expect(result.outbound.destination_code).toBe('JFK');
    expect(result.outbound.duration).toBe('8h 0m');
    expect(result.outbound.stops).toBe(0);
    expect(result.outbound.layovers).toEqual([]);
    expect(result.return).toBeUndefined();
  });

  it('maps round-trip flight (two legs)', () => {
    const outbound = makeLeg({
      departure: { city: 'London', airport: 'LHR', date: '2026-03-15', time: '10:00' },
      arrival: { city: 'New York', airport: 'JFK', date: '2026-03-15', time: '18:00' },
      duration: '8h 0m',
    });
    const returnLeg = makeLeg({
      departure: { city: 'New York', airport: 'JFK', date: '2026-03-22', time: '20:00' },
      arrival: { city: 'London', airport: 'LHR', date: '2026-03-23', time: '08:00' },
      duration: '7h 0m',
      stops: 0,
    });

    const flight: FlightCardFlightInput = {
      id: 'f2',
      aircraftName: 'British Airways',
      tags: ['round-trip'],
      passengers: 2,
      legs: [outbound, returnLeg],
      price: 850,
    };

    const result = flightCardToMappedFlight(flight);

    expect(result.is_round_trip).toBe(true);
    expect(result.outbound).toBeDefined();
    expect(result.return).toBeDefined();
    expect(result.outbound?.origin_code).toBe('LHR');
    expect(result.outbound?.destination_code).toBe('JFK');
    expect(result.return?.origin_code).toBe('JFK');
    expect(result.return?.destination_code).toBe('LHR');
    expect(result.price).toBe(850);
  });

  it('passes through original_total_fare and platform_fee_percentage', () => {
    const flight: FlightCardFlightInput = {
      id: 'f3',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [makeLeg()],
      price: 462,
      original_total_fare: 420,
      platform_fee_percentage: 10,
    };

    const result = flightCardToMappedFlight(flight);

    expect(result.original_total_fare).toBe(420);
    expect(result.platform_fee_percentage).toBe(10);
  });

  it('builds layovers when leg.stops > 0 and segments.length > 1', () => {
    const seg1 = makeSegment({
      departureDatetime: '2026-03-15T10:00:00',
      arrivalDatetime: '2026-03-15T14:00:00',
      departureAirport: { iataCode: 'LHR', cityName: 'London' },
      arrivalAirport: { iataCode: 'CDG', cityName: 'Paris' },
    });
    const seg2 = makeSegment({
      departureDatetime: '2026-03-15T16:00:00',
      arrivalDatetime: '2026-03-15T20:00:00',
      departureAirport: { iataCode: 'CDG', cityName: 'Paris' },
      arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
    });

    const legWithLayover = makeLeg({
      stops: 1,
      stopsText: '1 stop',
      duration: '6h 0m',
      totalTimeDisplay: '10h 0m',
      segments: [seg1, seg2],
    });

    const flight: FlightCardFlightInput = {
      id: 'f4',
      aircraftName: 'Multi-segment',
      tags: [],
      passengers: 1,
      legs: [legWithLayover],
      price: 350,
    };

    const result = flightCardToMappedFlight(flight);

    expect(result.outbound?.layovers).toHaveLength(1);
    expect(result.outbound?.layovers?.[0]?.destination_code).toBe('CDG');
    expect(result.outbound?.layovers?.[0]?.layover_duration).toBe('2h 0m');
    expect(result.outbound?.flight_duration).toBe('6h 0m');
    expect(result.outbound?.duration).toBe('10h 0m');
  });

  it('uses duration as total when layovers present and totalTimeDisplay set', () => {
    const seg1 = makeSegment({
      departureDatetime: '2026-03-15T08:00:00',
      arrivalDatetime: '2026-03-15T10:00:00',
      departureAirport: { iataCode: 'LHR', cityName: 'London' },
      arrivalAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
    });
    const seg2 = makeSegment({
      departureDatetime: '2026-03-15T12:00:00',
      arrivalDatetime: '2026-03-15T17:00:00',
      departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
      arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
    });

    const leg = makeLeg({
      stops: 1,
      duration: '7h 0m',
      totalTimeDisplay: '9h 0m',
      segments: [seg1, seg2],
    });

    const result = flightCardToMappedFlight({
      id: 'f5',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 400,
    });

    expect(result.outbound?.flight_duration).toBe('7h 0m');
    expect(result.outbound?.duration).toBe('9h 0m');
  });

  it('passes logo_url when firstAirline has logoUrl', () => {
    const leg = makeLeg({
      airlinesInfo: [
        {
          name: 'British Airways',
          code: 'BA',
          flights: ['BA123'],
          logoUrl: 'https://example.com/ba.gif',
        },
      ],
    });

    const result = flightCardToMappedFlight({
      id: 'f6',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 300,
    });

    expect(result.logo_url).toBe('https://example.com/ba.gif');
  });

  it('single-segment leg produces empty layovers', () => {
    const seg = makeSegment();
    const leg = makeLeg({
      stops: 0,
      segments: [seg],
    });

    const result = flightCardToMappedFlight({
      id: 'f7',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 200,
    });

    expect(result.outbound?.layovers).toEqual([]);
  });

  it('handles leg with stops but single segment (no layovers built)', () => {
    const leg = makeLeg({
      stops: 1,
      segments: [makeSegment()],
    });

    const result = flightCardToMappedFlight({
      id: 'f8',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 250,
    });

    expect(result.outbound?.layovers).toEqual([]);
  });

  it('skips invalid or missing datetimes in segments', () => {
    const seg1 = makeSegment({
      departureDatetime: '2026-03-15T10:00:00',
      arrivalDatetime: 'invalid-datetime',
      departureAirport: { iataCode: 'LHR', cityName: 'London' },
      arrivalAirport: { iataCode: 'CDG', cityName: 'Paris' },
    });
    const seg2 = makeSegment({
      departureDatetime: '2026-03-15T16:00:00',
      arrivalDatetime: '2026-03-15T20:00:00',
      departureAirport: { iataCode: 'CDG', cityName: 'Paris' },
      arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
    });

    const leg = makeLeg({
      stops: 1,
      duration: '6h 0m',
      totalTimeDisplay: '10h 0m',
      segments: [seg1, seg2],
    });

    const result = flightCardToMappedFlight({
      id: 'f9',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 350,
    });

    expect(result.outbound?.layovers).toHaveLength(0);
  });

  it('calculates layover duration correctly when crossing midnight', () => {
    const seg1 = makeSegment({
      departureDatetime: '2026-03-15T22:00:00',
      arrivalDatetime: '2026-03-15T23:00:00',
      departureAirport: { iataCode: 'LHR', cityName: 'London' },
      arrivalAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
    });
    const seg2 = makeSegment({
      departureDatetime: '2026-03-16T02:00:00',
      arrivalDatetime: '2026-03-16T08:00:00',
      departureAirport: { iataCode: 'AMS', cityName: 'Amsterdam' },
      arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
    });

    const leg = makeLeg({
      stops: 1,
      duration: '9h 0m',
      totalTimeDisplay: '12h 0m',
      segments: [seg1, seg2],
    });

    const result = flightCardToMappedFlight({
      id: 'f10',
      aircraftName: 'BA',
      tags: [],
      passengers: 1,
      legs: [leg],
      price: 400,
    });

    expect(result.outbound?.layovers).toHaveLength(1);
    expect(result.outbound?.layovers?.[0]?.layover_duration).toBe('3h 0m');
  });

  it('Circle + journeyType merges all segment rows for modal (single itinerary)', () => {
    const seg1 = makeSegment({
      departureAirport: { iataCode: 'DEL', cityName: 'Delhi' },
      arrivalAirport: { iataCode: 'BOM', cityName: 'Mumbai' },
      departureDatetime: '2026-03-15T08:00:00',
      arrivalDatetime: '2026-03-15T10:00:00',
      flightDuration: { totalMinutes: 120 },
    });
    const seg2 = makeSegment({
      departureAirport: { iataCode: 'BOM', cityName: 'Mumbai' },
      arrivalAirport: { iataCode: 'DXB', cityName: 'Dubai' },
      departureDatetime: '2026-03-15T12:00:00',
      arrivalDatetime: '2026-03-15T14:00:00',
      flightDuration: { totalMinutes: 120 },
    });

    const cardLegs: FlightCardFlightInput['legs'] = [
      {
        departure: { city: 'Delhi', airport: 'DEL', date: '3/15/2026', time: '08:00' },
        arrival: { city: 'Mumbai', airport: 'BOM', date: '3/15/2026', time: '10:00' },
        duration: '2h 0m',
        stops: 0,
        stopsText: 'Non-stop',
        segments: [seg1],
        airlinesInfo: [{ name: 'AI', code: 'AI', flights: ['101'] }],
      },
      {
        departure: { city: 'Mumbai', airport: 'BOM', date: '3/15/2026', time: '12:00' },
        arrival: { city: 'Dubai', airport: 'DXB', date: '3/15/2026', time: '14:00' },
        duration: '2h 0m',
        stops: 0,
        stopsText: 'Non-stop',
        segments: [seg2],
        airlinesInfo: [{ name: 'AI', code: 'AI', flights: ['202'] }],
      },
    ];

    const mapped = flightCardToMappedFlight({
      id: 'mc1',
      aircraftName: 'Air India',
      journeyType: 'Circle',
      tags: [],
      passengers: 1,
      legs: cardLegs,
      price: 900,
    });

    expect(mapped.is_round_trip).toBe(false);
    expect(mapped.return).toBeUndefined();
    expect(mapped.outbound?.origin_code).toBe('DEL');
    expect(mapped.outbound?.destination_code).toBe('DXB');
    expect(mapped.outbound?.layovers?.length).toBeGreaterThanOrEqual(1);
  });
});

describe('buildProcessedLegsForSearchItinerary', () => {
  it('expands Circle single API leg with multiple segments into one row per segment', () => {
    const seg1 = makeSegment({
      departureAirport: { iataCode: 'DEL', cityName: 'Delhi' },
      arrivalAirport: { iataCode: 'BOM', cityName: 'Mumbai' },
      departureDatetime: '2026-03-15T08:00:00',
      arrivalDatetime: '2026-03-15T10:00:00',
      flightDuration: { totalMinutes: 120 },
    });
    const seg2 = makeSegment({
      departureAirport: { iataCode: 'BOM', cityName: 'Mumbai' },
      arrivalAirport: { iataCode: 'DXB', cityName: 'Dubai' },
      departureDatetime: '2026-03-15T12:00:00',
      arrivalDatetime: '2026-03-15T14:00:00',
      flightDuration: { totalMinutes: 120 },
    });
    const seg3 = makeSegment({
      departureAirport: { iataCode: 'DXB', cityName: 'Dubai' },
      arrivalAirport: { iataCode: 'BOM', cityName: 'Mumbai' },
      departureDatetime: '2026-03-16T09:00:00',
      arrivalDatetime: '2026-03-16T14:00:00',
      flightDuration: { totalMinutes: 300 },
    });

    const apiLeg: FlightLegCamel = { flightSegments: [seg1, seg2, seg3] };
    const processed = buildProcessedLegsForSearchItinerary('Circle', [apiLeg]);

    expect(processed).toHaveLength(3);
    expect(processed.every((p) => p.legLabel === '')).toBe(true);
    expect(processed[0]!.departure.airport).toBe('DEL');
    expect(processed[0]!.arrival.airport).toBe('BOM');
    expect(processed[2]!.arrival.airport).toBe('BOM');
  });

  it('does not expand Circle when only one segment in the single leg', () => {
    const seg = makeSegment({
      flightDuration: { totalMinutes: 120 },
    });
    const processed = buildProcessedLegsForSearchItinerary('Circle', [
      { flightSegments: [seg] },
    ]);
    expect(processed).toHaveLength(1);
    expect(processed[0]!.stops).toBe(0);
  });

  it('strips per-leg text labels for Return (search cards do not show OUTBOUND/RETURN)', () => {
    const outbound = makeSegment({
      departureAirport: { iataCode: 'LHR', cityName: 'London' },
      arrivalAirport: { iataCode: 'JFK', cityName: 'New York' },
      flightDuration: { totalMinutes: 480 },
    });
    const inbound = makeSegment({
      departureAirport: { iataCode: 'JFK', cityName: 'New York' },
      arrivalAirport: { iataCode: 'LHR', cityName: 'London' },
      flightDuration: { totalMinutes: 420 },
    });
    const processed = buildProcessedLegsForSearchItinerary('Return', [
      { flightSegments: [outbound] },
      { flightSegments: [inbound] },
    ]);
    expect(processed).toHaveLength(2);
    expect(processed.every((p) => p.legLabel === '')).toBe(true);
  });

  it('does not surface OUTBOUND/RETURN-style labels on Circle with two API legs', () => {
    const a = makeSegment({
      departureAirport: { iataCode: 'A', cityName: 'A' },
      arrivalAirport: { iataCode: 'B', cityName: 'B' },
      flightDuration: { totalMinutes: 60 },
    });
    const b = makeSegment({
      departureAirport: { iataCode: 'B', cityName: 'B' },
      arrivalAirport: { iataCode: 'C', cityName: 'C' },
      flightDuration: { totalMinutes: 60 },
    });
    const processed = buildProcessedLegsForSearchItinerary('Circle', [
      { flightSegments: [a] },
      { flightSegments: [b] },
    ]);
    expect(processed).toHaveLength(2);
    expect(processed.every((p) => p.legLabel === '')).toBe(true);
  });
});

describe('round-trip segment labels (trip details)', () => {
  const seg = (dep: string, arr: string) => ({
    departureAirport: { iataCode: dep },
    arrivalAirport: { iataCode: arr },
  });

  it('findRoundTripSegmentSplitIndex finds split for LHR–LIS–JFK / JFK–LIS–LHR', () => {
    const segments = [
      seg('LHR', 'LIS'),
      seg('LIS', 'JFK'),
      seg('JFK', 'LIS'),
      seg('LIS', 'LHR'),
    ];
    expect(findRoundTripSegmentSplitIndex(segments)).toBe(2);
    expect(tripDetailsSegmentOutboundReturnLabels(segments)).toEqual([
      'OUTBOUND',
      'OUTBOUND',
      'RETURN',
      'RETURN',
    ]);
  });

  it('returns null for one-way with connection (does not return to origin)', () => {
    const segments = [seg('LHR', 'LIS'), seg('LIS', 'JFK')];
    expect(findRoundTripSegmentSplitIndex(segments)).toBeNull();
  });

  it('roundTripBoundLabelPerVendorLeg is null when a vendor leg straddles the outbound/return split', () => {
    const segments = [
      seg('LHR', 'LIS'),
      seg('LIS', 'JFK'),
      seg('JFK', 'LIS'),
      seg('LIS', 'LHR'),
    ];
    const flightLegs = [
      { flightSegments: [segments[0]!] },
      { flightSegments: segments.slice(1) },
    ];
    expect(roundTripBoundLabelPerVendorLeg(flightLegs)).toEqual(['OUTBOUND', null]);
  });
});

describe('getAirlineLogoUrl', () => {
  it('returns logoUrl when present', () => {
    expect(getAirlineLogoUrl({ logoUrl: 'https://x.com/logo.gif' })).toBe(
      'https://x.com/logo.gif'
    );
  });

  it('returns logo_url when present (snake_case)', () => {
    expect(getAirlineLogoUrl({ logo_url: 'https://x.com/snake.gif' })).toBe(
      'https://x.com/snake.gif'
    );
  });

  it('prefers logoUrl over logo_url', () => {
    expect(
      getAirlineLogoUrl({
        logoUrl: 'https://camel.gif',
        logo_url: 'https://snake.gif',
      })
    ).toBe('https://camel.gif');
  });

  it('returns undefined for null or undefined', () => {
    expect(getAirlineLogoUrl(null)).toBeUndefined();
    expect(getAirlineLogoUrl(undefined)).toBeUndefined();
  });

  it('returns undefined when neither logoUrl nor logo_url present', () => {
    expect(getAirlineLogoUrl({ iata_code: 'BA' })).toBeUndefined();
  });
});

const baseUiParams = (): Omit<FlightSearchParamsUI, 'tripType' | 'returnDate'> => ({
  from: 'LHR',
  to: 'CDG',
  date: new Date('2026-06-01'),
  travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
});

describe('isRoundTripSearchMissingReturnDate', () => {
  it('is true for round-trip without returnDate (invalid API restore)', () => {
    expect(
      isRoundTripSearchMissingReturnDate({
        ...baseUiParams(),
        tripType: 'round-trip',
        returnDate: null,
      }),
    ).toBe(true);
    expect(
      isRoundTripSearchMissingReturnDate({
        ...baseUiParams(),
        tripType: 'round-trip',
      }),
    ).toBe(true);
  });

  it('is false when round-trip has returnDate', () => {
    expect(
      isRoundTripSearchMissingReturnDate({
        ...baseUiParams(),
        tripType: 'round-trip',
        returnDate: new Date('2026-06-15'),
      }),
    ).toBe(false);
  });

  it('is false for one-way and multi-city', () => {
    expect(
      isRoundTripSearchMissingReturnDate({
        ...baseUiParams(),
        tripType: 'one-way',
      }),
    ).toBe(false);
    expect(
      isRoundTripSearchMissingReturnDate({
        ...baseUiParams(),
        tripType: 'multi-city',
        segments: [
          { from: 'LHR', to: 'CDG', date: new Date('2026-06-01') },
          { from: 'CDG', to: 'BCN', date: new Date('2026-06-10') },
        ],
      }),
    ).toBe(false);
  });

  it('is false for null or undefined', () => {
    expect(isRoundTripSearchMissingReturnDate(null)).toBe(false);
    expect(isRoundTripSearchMissingReturnDate(undefined)).toBe(false);
  });
});
