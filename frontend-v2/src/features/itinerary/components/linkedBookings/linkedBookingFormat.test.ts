import { describe, it, expect } from 'vitest';
import { formatAirportPairLine } from './linkedBookingFormat';

describe('formatAirportPairLine', () => {
  it('joins departure and arrival with arrow', () => {
    expect(formatAirportPairLine('JFK', 'LHR')).toBe('JFK → LHR');
  });

  it('returns a single code when only departure is set', () => {
    expect(formatAirportPairLine('JFK', null)).toBe('JFK');
  });

  it('returns null when both are empty', () => {
    expect(formatAirportPairLine(undefined, '')).toBeNull();
  });
});
