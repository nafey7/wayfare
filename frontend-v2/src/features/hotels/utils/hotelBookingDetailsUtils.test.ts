import { describe, it, expect } from 'vitest';
import {
  formatStayDateLine,
  collectHotelImages,
  buildMapsHref,
  mapGuests,
  deriveShowPaymentApprovedChip,
  pickStr,
} from './hotelBookingDetailsUtils';
import type { HotelTripDetailsResponse } from '@/types/hotels';

describe('hotelBookingDetailsUtils', () => {
  describe('formatStayDateLine', () => {
    it('uses numeric daysStr for night label when it is digits only', () => {
      expect(formatStayDateLine('2025-06-01', '2025-06-05', '4')).toContain('4 nights');
    });

    it('does not treat non-numeric daysStr as a night count', () => {
      const line = formatStayDateLine('2025-06-01', '2025-06-05', 'Jun 1–5');
      expect(line).not.toContain('Jun 1–5 nights');
      expect(line).toContain('4 nights');
    });
  });

  describe('collectHotelImages', () => {
    it('collects imageUrl and de-duplicates', () => {
      expect(
        collectHotelImages({
          imageUrl: 'https://a.com/1.jpg',
          images: ['https://a.com/1.jpg', { url: 'https://a.com/2.jpg' }],
        }),
      ).toEqual(['https://a.com/1.jpg', 'https://a.com/2.jpg']);
    });

    it('collects hotelImageUrl from trip-details (booking snapshot)', () => {
      expect(
        collectHotelImages({
          hotelImageUrl: 'https://cdn.example/snap.jpg',
        }),
      ).toEqual(['https://cdn.example/snap.jpg']);
    });
  });

  describe('buildMapsHref', () => {
    it('builds coords URL when lat/lng present', () => {
      expect(buildMapsHref({ latitude: 41.38, longitude: 2.17 })).toContain('41.38,2.17');
    });

    it('falls back to address query', () => {
      const href = buildMapsHref({ address: 'Carrer 1', city: 'Barcelona' });
      expect(href).toContain('query=');
      expect(href).toContain(encodeURIComponent('Carrer 1, Barcelona'));
    });
  });

  describe('mapGuests', () => {
    it('returns placeholder when no guests', () => {
      expect(mapGuests({})).toEqual([{ roleLabel: 'Guest 1', fullName: '—' }]);
    });

    it('maps camelCase guest fields', () => {
      const rows = mapGuests({
        guests: [
          {
            title: 'Mr',
            firstName: 'A',
            lastName: 'B',
            email: 'a@b.com',
          },
        ],
      });
      expect(rows[0]?.fullName).toBe('Mr A B');
      expect(rows[0]?.roleLabel).toBe('Adult 1');
      expect(rows[0]?.contactLines).toEqual(['a@b.com']);
    });

    it('labels children separately from adults', () => {
      const rows = mapGuests({
        guests: [
          { title: 'Mr', firstName: 'A', lastName: 'Senior', isChild: false },
          { title: 'Master', firstName: 'B', lastName: 'Junior', isChild: true },
          { title: 'Mrs', firstName: 'C', lastName: 'Senior', is_child: false },
        ],
      });
      expect(rows.map((r) => r.roleLabel)).toEqual(['Adult 1', 'Child 1', 'Adult 2']);
    });
  });

  describe('deriveShowPaymentApprovedChip', () => {
    it('is true for BOOKED status', () => {
      const detail = { success: true, bookingStatus: 'BOOKED' } as HotelTripDetailsResponse;
      expect(deriveShowPaymentApprovedChip(detail, {})).toBe(true);
    });

    it('is false for CANCELLED', () => {
      const detail = { success: true, bookingStatus: 'CANCELLED' } as HotelTripDetailsResponse;
      expect(deriveShowPaymentApprovedChip(detail, {})).toBe(false);
    });

    it('is false for PENDING', () => {
      const detail = { success: true, bookingStatus: 'PENDING' } as HotelTripDetailsResponse;
      expect(deriveShowPaymentApprovedChip(detail, {})).toBe(false);
    });

    it('respects paymentStatus in booking details', () => {
      expect(
        deriveShowPaymentApprovedChip({ success: true, bookingStatus: null } as HotelTripDetailsResponse, {
          paymentStatus: 'failed',
        }),
      ).toBe(false);
      expect(
        deriveShowPaymentApprovedChip({ success: true, bookingStatus: null } as HotelTripDetailsResponse, {
          paymentStatus: 'captured',
        }),
      ).toBe(true);
    });

    it('is true when paidAt is set without negative payment status', () => {
      expect(
        deriveShowPaymentApprovedChip({ success: true } as HotelTripDetailsResponse, {
          paidAt: '2025-01-01',
        }),
      ).toBe(true);
    });
  });

  describe('pickStr', () => {
    it('returns first non-empty in key order', () => {
      expect(pickStr({ a: '', b: 'x' }, 'a', 'b')).toBe('x');
    });
  });
});
