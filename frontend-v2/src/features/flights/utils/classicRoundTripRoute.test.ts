import { describe, expect, it } from 'vitest';
import { tryClassicRoundTripLine } from './classicRoundTripRoute';

describe('tryClassicRoundTripLine', () => {
  it('returns A ⇆ B when return is inverse of outbound and trip is round_trip', () => {
    expect(
      tryClassicRoundTripLine('LHR', 'JFK', 'JFK', 'LHR', 'round_trip'),
    ).toBe('LHR ⇆ JFK');
  });

  it('is case-insensitive on IATA codes', () => {
    expect(
      tryClassicRoundTripLine('lhr', 'jfk', 'JFK', 'lhr', 'round_trip'),
    ).toBe('LHR ⇆ JFK');
  });

  it('returns null for open-jaw style round trip (airports do not match)', () => {
    expect(
      tryClassicRoundTripLine('JFK', 'LHR', 'LHR', 'CDG', 'round_trip'),
    ).toBeNull();
  });

  it('returns null unless flightTripType is round_trip', () => {
    expect(
      tryClassicRoundTripLine('JFK', 'LHR', 'LHR', 'JFK', 'one_way'),
    ).toBeNull();
    expect(tryClassicRoundTripLine('JFK', 'LHR', 'LHR', 'JFK', null)).toBeNull();
  });
});
