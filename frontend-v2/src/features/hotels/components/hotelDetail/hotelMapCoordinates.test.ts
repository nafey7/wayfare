import { describe, expect, it } from 'vitest';

import { isValidHotelMapCoordinates } from './hotelMapCoordinates';

describe('isValidHotelMapCoordinates', () => {
  it('accepts typical hotel coordinates', () => {
    expect(isValidHotelMapCoordinates(51.5074, -0.1278)).toBe(true);
  });

  it('accepts equator with non-zero longitude', () => {
    expect(isValidHotelMapCoordinates(0, -79.5)).toBe(true);
  });

  it('rejects non-finite values', () => {
    expect(isValidHotelMapCoordinates(Number.NaN, 0)).toBe(false);
    expect(isValidHotelMapCoordinates(1, Number.POSITIVE_INFINITY)).toBe(false);
  });

  it('rejects (0,0) sentinel', () => {
    expect(isValidHotelMapCoordinates(0, 0)).toBe(false);
  });

  it('rejects out-of-range latitude or longitude', () => {
    expect(isValidHotelMapCoordinates(91, 0)).toBe(false);
    expect(isValidHotelMapCoordinates(0, 181)).toBe(false);
  });

  it('rejects undefined', () => {
    expect(isValidHotelMapCoordinates(undefined, -0.12)).toBe(false);
  });
});
