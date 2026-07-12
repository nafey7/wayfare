import { describe, expect, it } from 'vitest';
import { getFlightRouteLabel } from './flightRouteLabel';
import type { LinkedBookingEventSummary } from '@/types/itineraries';

const leg = (dep: string, arr: string, idx = 0) => ({
  legIndex: idx,
  departureIata: dep,
  arrivalIata: arr,
  segmentCount: 0,
  segments: [],
});

const makeEvent = (overrides: Partial<LinkedBookingEventSummary> = {}): LinkedBookingEventSummary => ({
  voyaBookingReference: 'VOYA-0001',
  eventType: 'FLIGHT',
  timestamp: '',
  ...overrides,
});

describe('getFlightRouteLabel', () => {
  it('returns "Flight" for null input', () => {
    expect(getFlightRouteLabel(null)).toBe('Flight');
  });

  it('returns "Flight" for undefined input', () => {
    expect(getFlightRouteLabel(undefined)).toBe('Flight');
  });

  it('returns "Flight" when no route data is present', () => {
    expect(getFlightRouteLabel(makeEvent())).toBe('Flight');
  });

  it('returns "DEP → ARR" for a one-way flight using routeLegs', () => {
    expect(getFlightRouteLabel(makeEvent({ flightTripType: 'one_way', routeLegs: [leg('JFK', 'LHR')] }))).toBe('JFK → LHR');
  });

  it('returns "DEP ↔ ARR" for a round-trip flight where second leg returns to origin', () => {
    expect(
      getFlightRouteLabel(makeEvent({ flightTripType: 'round_trip', routeLegs: [leg('JFK', 'LHR'), leg('LHR', 'JFK')] })),
    ).toBe('JFK ↔ LHR');
  });

  it('returns "DEP → ARR" for multi_city even when it looks like a round-trip', () => {
    expect(
      getFlightRouteLabel(makeEvent({ flightTripType: 'multi_city', routeLegs: [leg('JFK', 'LHR'), leg('LHR', 'JFK')] })),
    ).toBe('JFK → LHR');
  });

  it('returns "DEP → ARR" for round_trip with only one leg (missing return)', () => {
    expect(getFlightRouteLabel(makeEvent({ flightTripType: 'round_trip', routeLegs: [leg('AMS', 'BCN')] }))).toBe('AMS → BCN');
  });

  it('falls back to legacy departureAirportIata/arrivalAirportIata when no routeLegs', () => {
    expect(getFlightRouteLabel(makeEvent({ departureAirportIata: 'SYD', arrivalAirportIata: 'MEL' }))).toBe('SYD → MEL');
  });

  it('returns departure code alone when only departureAirportIata is set', () => {
    expect(getFlightRouteLabel(makeEvent({ departureAirportIata: 'CDG' }))).toBe('CDG');
  });

  it('trims whitespace from IATA codes', () => {
    expect(getFlightRouteLabel(makeEvent({ routeLegs: [leg(' JFK ', ' LHR ')] }))).toBe('JFK → LHR');
  });
});
