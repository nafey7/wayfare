import { describe, expect, it } from 'vitest';

import type { Hotel, HotelItinerary } from '@/types/hotels';

import { getHotelKey, getPosition, hasValidCoords } from './hotelMapCoords';

/** Minimal fixture; utilities accept API-shaped `unknown` fields at runtime. */
function hotelFixture(obj: Record<string, unknown>): Hotel | HotelItinerary {
  return obj as unknown as Hotel | HotelItinerary;
}

describe('hasValidCoords', () => {
  it('returns true for valid latitude/longitude', () => {
    expect(hasValidCoords(hotelFixture({ latitude: 51.5074, longitude: -0.1278 }))).toBe(true);
  });

  it('accepts lat/lng aliases', () => {
    expect(hasValidCoords(hotelFixture({ lat: 40.7128, lng: -74.006 }))).toBe(true);
  });

  it('accepts lon alias for longitude', () => {
    expect(hasValidCoords(hotelFixture({ latitude: 1, lon: 2 }))).toBe(true);
  });

  it('returns false when latitude or longitude parses to NaN', () => {
    expect(hasValidCoords(hotelFixture({ latitude: 'not-a-number', longitude: 0 }))).toBe(false);
    expect(hasValidCoords(hotelFixture({ latitude: 0, longitude: Number.NaN }))).toBe(false);
  });

  it('treats (0, 0) as sentinel and returns false', () => {
    expect(hasValidCoords(hotelFixture({ latitude: 0, longitude: 0 }))).toBe(false);
    expect(hasValidCoords(hotelFixture({ latitude: '0', longitude: '0' }))).toBe(false);
  });

  it('treats (-1, -1) as sentinel and returns false', () => {
    expect(hasValidCoords(hotelFixture({ latitude: -1, longitude: -1 }))).toBe(false);
    expect(hasValidCoords(hotelFixture({ latitude: '-1', longitude: '-1' }))).toBe(false);
  });

  it('treats one-axis zero as valid (only (0,0) is the sentinel)', () => {
    expect(hasValidCoords(hotelFixture({ latitude: 0, longitude: -0.12 }))).toBe(true);
    expect(hasValidCoords(hotelFixture({ latitude: 51.5, longitude: 0 }))).toBe(true);
  });

  it('returns false when coordinate fields are missing', () => {
    expect(hasValidCoords(hotelFixture({ name: 'X' }))).toBe(false);
  });
});

describe('getPosition', () => {
  it('returns parsed coordinates when valid', () => {
    expect(getPosition(hotelFixture({ latitude: '51.5', longitude: -0.12 }))).toEqual({
      lat: 51.5,
      lng: -0.12,
    });
  });

  it('returns { lat: 0, lng: 0 } for NaN latitude or longitude', () => {
    expect(getPosition(hotelFixture({ latitude: Number.NaN, longitude: 1 }))).toEqual({
      lat: 0,
      lng: 1,
    });
    expect(getPosition(hotelFixture({ latitude: 1, longitude: Number.NaN }))).toEqual({
      lat: 1,
      lng: 0,
    });
    expect(getPosition(hotelFixture({ latitude: 'x', longitude: 'y' }))).toEqual({
      lat: 0,
      lng: 0,
    });
  });
});

describe('getHotelKey', () => {
  it('prefers tokenId over id', () => {
    expect(getHotelKey(hotelFixture({ tokenId: 'tok-1', id: 'id-1' }))).toBe('tok-1');
  });

  it('falls back to id when tokenId is missing', () => {
    expect(getHotelKey({ id: 'id-only' } as unknown as Hotel)).toBe('id-only');
  });

  it('returns empty string when neither tokenId nor id is set', () => {
    expect(getHotelKey(hotelFixture({ name: 'Orphan' }))).toBe('');
  });
});
