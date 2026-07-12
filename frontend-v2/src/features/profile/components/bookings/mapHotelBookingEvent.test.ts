import { describe, expect, it } from 'vitest';
import type { HotelMyBookingListItem } from '@/types/hotels';
import { mapHotelMyBookingToRow } from './mapHotelBookingEvent';

describe('mapHotelMyBookingToRow', () => {
  it('maps name, city, image URL, and reference for navigation', () => {
    const item: HotelMyBookingListItem = {
      voyaBookingReference: 'VOYA-XYZ',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: 120,
      hotelImageUrl: 'https://example.com/thumb.jpg',
      hotelName: 'Grand Plaza',
      hotelCity: 'Paris',
    };
    const row = mapHotelMyBookingToRow(item);
    expect(row.summaryLine).toBe('Grand Plaza');
    expect(row.locationLine).toBe('Paris');
    expect(row.hotelImageUrl).toBe('https://example.com/thumb.jpg');
    expect(row.hotelNameRaw).toBe('Grand Plaza');
    expect(row.hotelCityRaw).toBe('Paris');
    expect(row.canNavigate).toBe(true);
    expect(row.reference).toBe('VOYA-XYZ');
  });

  it('disables navigation without reference and falls back title', () => {
    const item: HotelMyBookingListItem = {
      voyaBookingReference: null,
      action: 'PENDING',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      hotelImageUrl: null,
      hotelName: null,
      hotelCity: null,
    };
    const row = mapHotelMyBookingToRow(item);
    expect(row.canNavigate).toBe(false);
    expect(row.summaryLine).toBe('Hotel booking');
    expect(row.locationLine).toBeNull();
    expect(row.hotelImageUrl).toBeNull();
    expect(row.hotelNameRaw).toBeNull();
    expect(row.hotelCityRaw).toBeNull();
  });

  it('trims empty image URL to null', () => {
    const item: HotelMyBookingListItem = {
      voyaBookingReference: 'VOYA-1',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      hotelImageUrl: '   ',
      hotelName: 'A',
      hotelCity: null,
    };
    const row = mapHotelMyBookingToRow(item);
    expect(row.hotelImageUrl).toBeNull();
    expect(row.hotelNameRaw).toBe('A');
    expect(row.hotelCityRaw).toBeNull();
  });

  it('uses stay line only (no booked-on suffix) when check-in/out exist', () => {
    const item: HotelMyBookingListItem = {
      voyaBookingReference: 'VOYA-STAY',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: '2026-03-15T10:00:00.000Z',
      amount: null,
      hotelImageUrl: null,
      hotelName: 'Sea View',
      hotelCity: 'Lisbon',
      hotelCheckInDate: '2026-06-10',
      hotelCheckOutDate: '2026-06-12',
      hotelNights: 2,
    };
    const row = mapHotelMyBookingToRow(item);
    expect(row.dateLabel).toBe('10 Jun 2026 – 12 Jun 2026 (2 nights)');
    expect(row.dateLabel).not.toMatch(/booked/i);
  });
});
