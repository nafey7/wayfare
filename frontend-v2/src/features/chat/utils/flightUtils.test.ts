import { describe, it, expect } from 'vitest';
import {
  addDurations,
  getTotalJourneyDuration,
  getStopsLabel,
  getSegmentFlightNumber,
} from './flightUtils';
import type { MappedFlight, FlightSegment } from '@/types/flight';

describe('addDurations', () => {
  it('adds two durations in Xh Ym format', () => {
    expect(addDurations('2h 30m', '1h 15m')).toBe('3h 45m');
  });

  it('handles hours only', () => {
    expect(addDurations('2h', '3h')).toBe('5h 0m');
  });

  it('handles zero minutes in output when exact hours', () => {
    expect(addDurations('1h 0m', '2h 0m')).toBe('3h 0m');
  });
});

describe('getTotalJourneyDuration', () => {
  it('returns outbound duration for one-way', () => {
    const flight: MappedFlight = {
      outbound: { duration: '5h 30m', stops: 0, layovers: [] },
      is_round_trip: false,
    } as MappedFlight;
    expect(getTotalJourneyDuration(flight)).toBe('5h 30m');
  });

  it('returns outbound + return for round-trip', () => {
    const flight: MappedFlight = {
      outbound: { duration: '5h 30m', stops: 0, layovers: [] },
      return: { duration: '6h 15m', stops: 0, layovers: [] },
      is_round_trip: true,
    } as MappedFlight;
    expect(getTotalJourneyDuration(flight)).toBe('11h 45m');
  });

  it('returns outbound only when is_round_trip but no return duration', () => {
    const flight: MappedFlight = {
      outbound: { duration: '5h 30m', stops: 0, layovers: [] },
      is_round_trip: true,
      return: undefined,
    } as MappedFlight;
    expect(getTotalJourneyDuration(flight)).toBe('5h 30m');
  });

  it('returns 0h 0m when outbound missing', () => {
    const flight = { is_round_trip: false } as MappedFlight;
    expect(getTotalJourneyDuration(flight)).toBe('0h 0m');
  });
});

describe('getStopsLabel', () => {
  it('returns Direct for 0 stops', () => {
    expect(getStopsLabel(0)).toBe('Direct');
  });

  it('returns 1 Stop for 1 stop', () => {
    expect(getStopsLabel(1)).toBe('1 Stop');
  });

  it('returns N Stops for multiple', () => {
    expect(getStopsLabel(2)).toBe('2 Stops');
  });
});

describe('getSegmentFlightNumber', () => {
  it('prefers flight_number_info.formatted_number', () => {
    const seg: FlightSegment = {
      flight_number_info: { formatted_number: 'BA 123' },
      flight_number: 'BA123',
    };
    expect(getSegmentFlightNumber(seg)).toBe('BA 123');
  });

  it('falls back to flight_number when no flight_number_info', () => {
    const seg: FlightSegment = { flight_number: 'AA456' };
    expect(getSegmentFlightNumber(seg)).toBe('AA456');
  });

  it('builds from flight_number_info.number and airline_prefix', () => {
    const seg: FlightSegment = {
      flight_number_info: { number: '789', airline_prefix: 'UA ' },
    };
    expect(getSegmentFlightNumber(seg)).toBe('UA 789');
  });

  it('returns empty string when no flight number data', () => {
    expect(getSegmentFlightNumber({})).toBe('');
  });
});
