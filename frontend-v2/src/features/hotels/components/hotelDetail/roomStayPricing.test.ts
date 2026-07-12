import { describe, expect, it } from 'vitest';

import type { RoomRate } from '@/types/hotels';

import { resolveRoomStayPricing } from './roomStayPricing';

function room(partial: Partial<RoomRate> & Pick<RoomRate, 'rateBasisId'>): RoomRate {
  const { rateBasisId, ...rest } = partial;
  return {
    rateBasisId,
    ...rest,
  };
}

describe('resolveRoomStayPricing', () => {
  it('single night: total and per night match', () => {
    const r = room({ rateBasisId: '1', totalPrice: 199, pricePerNight: 199, currency: 'USD' });
    const p = resolveRoomStayPricing(r, 1);
    expect(p.total).toBe(199);
    expect(p.perNight).toBe(199);
    expect(p.nights).toBe(1);
  });

  it('multi-night: backend duplicate total in both fields → derive per night', () => {
    const r = room({ rateBasisId: '1', totalPrice: 300, pricePerNight: 300, currency: 'USD' });
    const p = resolveRoomStayPricing(r, 3);
    expect(p.total).toBe(300);
    expect(p.perNight).toBe(100);
    expect(p.nights).toBe(3);
  });

  it('multi-night: consistent per-night and total', () => {
    const r = room({ rateBasisId: '1', totalPrice: 300, pricePerNight: 100, currency: 'USD' });
    const p = resolveRoomStayPricing(r, 3);
    expect(p.total).toBe(300);
    expect(p.perNight).toBe(100);
  });

  it('multi-night: only total → spread across nights', () => {
    const r = room({ rateBasisId: '1', totalPrice: 400, currency: 'EUR' });
    const p = resolveRoomStayPricing(r, 4);
    expect(p.total).toBe(400);
    expect(p.perNight).toBe(100);
  });

  it('multi-night: only per night → multiply to total', () => {
    const r = room({ rateBasisId: '1', pricePerNight: 80, currency: 'GBP' });
    const p = resolveRoomStayPricing(r, 5);
    expect(p.perNight).toBe(80);
    expect(p.total).toBe(400);
  });

  it('multi-night: inconsistent pair → trust total, derive per night', () => {
    const r = room({ rateBasisId: '1', totalPrice: 290, pricePerNight: 99, currency: 'USD' });
    const p = resolveRoomStayPricing(r, 3);
    expect(p.total).toBe(290);
    expect(p.perNight).toBeCloseTo(290 / 3, 5);
  });

  it('parses string amounts (API may serialize decimals as JSON strings)', () => {
    const r = {
      rateBasisId: '1',
      totalPrice: '476.11',
      currency: 'USD',
    } as unknown as RoomRate;
    const p = resolveRoomStayPricing(r, 1);
    expect(p.total).toBe(476.11);
    expect(p.perNight).toBe(476.11);
  });

  it('parses string amounts via nested price object', () => {
    const r = {
      rateBasisId: '1',
      currency: 'USD',
      price: { currency: 'USD', amount: '476.11', perNight: '476.11' },
    } as unknown as RoomRate;
    const p = resolveRoomStayPricing(r, 2);
    expect(p.total).toBeCloseTo(476.11, 2);
    expect(p.perNight).toBeCloseTo(238.055, 3);
  });
});
