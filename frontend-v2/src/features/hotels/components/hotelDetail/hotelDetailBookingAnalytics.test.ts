import { describe, expect, it } from 'vitest';

import type { RoomRate } from '@/types/hotels';

import { buildHotelRoomSelectedEventPayload } from './hotelDetailBookingAnalytics';
import { resolveRoomStayPricing } from './roomStayPricing';

function room(partial: Partial<RoomRate> & Pick<RoomRate, 'rateBasisId'>): RoomRate {
  return { ...partial } as RoomRate;
}

describe('buildHotelRoomSelectedEventPayload', () => {
  it('sets total_price and currency from resolveRoomStayPricing (single source of truth)', () => {
    const r = room({
      rateBasisId: '1',
      roomType: 'Deluxe',
      totalPrice: 300,
      pricePerNight: 300,
      currency: 'USD',
    });
    const nights = 3;
    const payload = buildHotelRoomSelectedEventPayload(r, nights);
    const pricing = resolveRoomStayPricing(r, nights);
    expect(payload.total_price).toBe(pricing.total);
    expect(payload.currency).toBe(pricing.currency);
    expect(payload.nights).toBe(nights);
    expect(payload.room_name).toBe('Deluxe');
  });

  it('uses roomName when roomType is absent', () => {
    const r = room({
      rateBasisId: '1',
      roomName: 'Standard King',
      totalPrice: 199,
      currency: 'EUR',
    });
    expect(buildHotelRoomSelectedEventPayload(r, 1).room_name).toBe('Standard King');
  });

  it('uses empty room_name when neither roomType nor roomName is set', () => {
    const r = room({ rateBasisId: '1', totalPrice: 100, currency: 'USD' });
    expect(buildHotelRoomSelectedEventPayload(r, 1).room_name).toBe('');
  });

  it('matches multi-night duplicate-total derivation (regression: GTM total vs display)', () => {
    const r = room({
      rateBasisId: '1',
      totalPrice: 300,
      pricePerNight: 300,
      currency: 'GBP',
    });
    const nights = 3;
    const payload = buildHotelRoomSelectedEventPayload(r, nights);
    expect(payload.total_price).toBe(300);
    expect(resolveRoomStayPricing(r, nights).total).toBe(300);
  });

  it('exposes non-finite totals consistently with resolveRoomStayPricing when data is empty', () => {
    const r = room({ rateBasisId: '1', currency: 'USD' });
    const payload = buildHotelRoomSelectedEventPayload(r, 2);
    const pricing = resolveRoomStayPricing(r, 2);
    expect(payload.total_price).toBe(pricing.total);
    expect(payload.currency).toBe(pricing.currency);
  });
});
