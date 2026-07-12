import { describe, it, expect } from 'vitest';
import { normalizeHotelSearchFormParams } from './normalizeHotelSearchFormParams';
import type { HotelSearchFormParams } from '@/types/hotels';

const minimal: HotelSearchFormParams = {
  destination: 'Paris',
  checkin: '2026-06-10',
  checkout: '2026-06-14',
  rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
  nationality: 'US',
};

describe('normalizeHotelSearchFormParams', () => {
  it('with fillCheckout false requires both dates', () => {
    expect(
      normalizeHotelSearchFormParams({ ...minimal, checkout: null }, { fillCheckout: false })
    ).toBeNull();
  });

  it('with fillCheckout true fills checkout as night after check-in', () => {
    const n = normalizeHotelSearchFormParams(
      { ...minimal, checkout: null },
      { fillCheckout: true }
    );
    expect(n).not.toBeNull();
    expect(n!.checkout).toBe('2026-06-11');
  });

  it('returns the same core fields for strict and URL modes when checkout is set', () => {
    const strict = normalizeHotelSearchFormParams(minimal, { fillCheckout: false });
    const url = normalizeHotelSearchFormParams(minimal, { fillCheckout: true });
    expect(strict).toEqual(url);
  });

  it('returns null when checkout is on or before check-in', () => {
    expect(
      normalizeHotelSearchFormParams(
        { ...minimal, checkin: '2026-06-10', checkout: '2026-06-10' },
        { fillCheckout: false }
      )
    ).toBeNull();
    expect(
      normalizeHotelSearchFormParams(
        { ...minimal, checkin: '2026-06-14', checkout: '2026-06-10' },
        { fillCheckout: false }
      )
    ).toBeNull();
  });

  it('returns null for invalid ISO date strings', () => {
    expect(
      normalizeHotelSearchFormParams(
        { ...minimal, checkin: 'not-a-date', checkout: '2026-06-14' },
        { fillCheckout: false }
      )
    ).toBeNull();
    expect(
      normalizeHotelSearchFormParams(
        { ...minimal, checkin: '2026-06-10', checkout: 'invalid' },
        { fillCheckout: false }
      )
    ).toBeNull();
  });

  it('returns null when destination is whitespace-only', () => {
    expect(
      normalizeHotelSearchFormParams(
        { ...minimal, destination: '   \t' },
        { fillCheckout: false }
      )
    ).toBeNull();
  });
});
