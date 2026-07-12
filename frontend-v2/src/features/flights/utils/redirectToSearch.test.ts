import { describe, it, expect, vi } from 'vitest';
import * as urlParams from './urlParams';
import { buildFlightSearchRedirectTarget } from './redirectToSearch';
import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';

const validParams: FlightSearchFormParams = {
  tripType: 'round-trip',
  from: 'LHR',
  to: 'JFK',
  date: '2026-03-15',
  returnDate: '2026-03-22',
  travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
};

describe('buildFlightSearchRedirectTarget', () => {
  it('returns /flights/search?q=... when params are valid', () => {
    const result = buildFlightSearchRedirectTarget(validParams);
    expect(result).toMatch(/^\/flights\/search\?q=/);
    const q = result.split('?q=')[1] as string;
    expect(q).toBeTruthy();
    expect(() => decodeURIComponent(q)).not.toThrow();
    expect(() => atob(decodeURIComponent(q))).not.toThrow();
  });

  it('returns /flights/search when from is empty', () => {
    const result = buildFlightSearchRedirectTarget({ ...validParams, from: '' });
    expect(result).toBe('/flights/search');
  });

  it('returns /flights/search when to is empty', () => {
    const result = buildFlightSearchRedirectTarget({ ...validParams, to: '' });
    expect(result).toBe('/flights/search');
  });

  it('returns /flights/search when from is whitespace only', () => {
    const result = buildFlightSearchRedirectTarget({ ...validParams, from: '   ' });
    expect(result).toBe('/flights/search');
  });

  it('returns /flights/search when to is whitespace only', () => {
    const result = buildFlightSearchRedirectTarget({ ...validParams, to: '   ' });
    expect(result).toBe('/flights/search');
  });

  it('returns /flights/search when serializeSearchParamsToUrl returns empty string', () => {
    const spy = vi.spyOn(urlParams, 'serializeSearchParamsToUrl').mockReturnValue('');
    const result = buildFlightSearchRedirectTarget(validParams);
    expect(result).toBe('/flights/search');
    spy.mockRestore();
  });

  it('prepends optional prefix for public chat routes', () => {
    const prefix = '/public/chat';
    expect(buildFlightSearchRedirectTarget({ ...validParams, from: '' }, prefix)).toBe(
      `${prefix}/flights/search`
    );
    const withQ = buildFlightSearchRedirectTarget(validParams, prefix);
    // `/` has no special meaning in RegExp; building from a literal prefix is enough.
    expect(withQ).toMatch(new RegExp(`^${prefix}/flights/search\\?q=`));
  });
});
