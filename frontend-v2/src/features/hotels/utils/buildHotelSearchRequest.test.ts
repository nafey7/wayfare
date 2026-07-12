import { describe, it, expect } from 'vitest';
import { buildHotelSearchRequestFromFormParams } from './buildHotelSearchRequest';
import type { HotelSearchFormParams } from '@/types/hotels';

const base: HotelSearchFormParams = {
  destination: 'Paris',
  checkin: '2026-06-10',
  checkout: '2026-06-14',
  rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
  nationality: 'US',
};

describe('buildHotelSearchRequestFromFormParams', () => {
  it('returns a request when destination, check-in, and check-out are valid', () => {
    const r = buildHotelSearchRequestFromFormParams(base);
    expect(r).not.toBeNull();
    expect(r!.cityName).toBe('Paris');
    expect(r!.checkin).toBe('2026-06-10');
    expect(r!.checkout).toBe('2026-06-14');
    expect(r!.nationality).toBe('US');
    expect(r!.occupancy).toHaveLength(1);
    expect(r!.occupancy[0]!.adult).toBe(2);
  });

  it('returns null when destination is missing or blank', () => {
    expect(buildHotelSearchRequestFromFormParams({ ...base, destination: '' })).toBeNull();
    expect(buildHotelSearchRequestFromFormParams({ ...base, destination: '   ' })).toBeNull();
  });

  it('returns null when check-in or check-out is missing (strict; URL helper may fill checkout)', () => {
    expect(buildHotelSearchRequestFromFormParams({ ...base, checkin: '' })).toBeNull();
    expect(buildHotelSearchRequestFromFormParams({ ...base, checkin: null })).toBeNull();
    expect(buildHotelSearchRequestFromFormParams({ ...base, checkout: '' })).toBeNull();
  });

  it('returns null when checkout is on or before check-in', () => {
    expect(
      buildHotelSearchRequestFromFormParams({
        ...base,
        checkin: '2026-06-10',
        checkout: '2026-06-10',
      })
    ).toBeNull();
    expect(
      buildHotelSearchRequestFromFormParams({
        ...base,
        checkin: '2026-06-10',
        checkout: '2026-06-09',
      })
    ).toBeNull();
  });

  it('maps multiple rooms to occupancy', () => {
    const r = buildHotelSearchRequestFromFormParams({
      ...base,
      rooms: [
        { roomNo: 1, adult: 2, child: 1, childAge: [5] },
        { roomNo: 2, adult: 1, child: 0, childAge: [0] },
      ],
    });
    expect(r!.occupancy).toHaveLength(2);
    expect(r!.occupancy[0]!.child).toBe(1);
    expect(r!.occupancy[1]!.child).toBe(0);
  });
});
