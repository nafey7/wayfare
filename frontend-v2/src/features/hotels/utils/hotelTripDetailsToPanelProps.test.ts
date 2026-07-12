import { describe, it, expect } from 'vitest';
import type { Hotel, HotelBookingResponse, HotelTripDetailsResponse } from '@/types/hotels';
import {
  syntheticTripDetailsFromBookingResult,
  hotelTripDetailsToPanelProps,
} from './hotelTripDetailsToPanelProps';

const startingPrice = { currency: 'USD', amount: 100, perNight: 50 };

function minimalHotel(overrides: Partial<Hotel> = {}): Hotel {
  return {
    id: 'h1',
    tokenId: 't1',
    name: 'Test Hotel',
    address: '1 Main St',
    city: 'NYC',
    country: 'US',
    starRating: 4,
    latitude: 40.7,
    longitude: -74.0,
    startingPrice,
    ...overrides,
  };
}

describe('syntheticTripDetailsFromBookingResult', () => {
  it('maps totalAmount cents to bookingDetails.totalPrice in major units', () => {
    const br: HotelBookingResponse = {
      voyaBookingReference: 'VOYA-1',
      status: 'confirmed',
      totalAmount: 19950,
      currency: 'USD',
      hotel: minimalHotel(),
    };
    const syn = syntheticTripDetailsFromBookingResult(br);
    expect(syn.success).toBe(true);
    expect(syn.bookingDetails?.totalPrice).toBe(199.5);
    expect(syn.bookingDetails?.currency).toBe('USD');
  });

  it('maps guests into bookingDetails for downstream panel mapping', () => {
    const br: HotelBookingResponse = {
      voyaBookingReference: 'VOYA-2',
      status: 'confirmed',
      hotel: minimalHotel(),
      guests: [
        { title: 'Mr', firstName: 'Ada', lastName: 'Lovelace', email: 'ada@example.com' },
      ],
    };
    const syn = syntheticTripDetailsFromBookingResult(br);
    const guests = syn.bookingDetails?.guests as Array<Record<string, unknown>> | undefined;
    expect(guests?.[0]).toMatchObject({
      firstName: 'Ada',
      lastName: 'Lovelace',
      email: 'ada@example.com',
    });
    const panel = hotelTripDetailsToPanelProps(syn, 'VOYA-2');
    expect(panel?.guests[0]?.fullName).toContain('Ada');
    expect(panel?.guests[0]?.contactLines).toContain('ada@example.com');
  });

  it('prefers hotel.images over imageUrl for bookingDetails.images', () => {
    const br: HotelBookingResponse = {
      voyaBookingReference: 'VOYA-3',
      status: 'confirmed',
      hotel: minimalHotel({
        images: ['https://cdn.example/a.jpg', 'https://cdn.example/b.jpg'],
        imageUrl: 'https://cdn.example/fallback.jpg',
      }),
    };
    const syn = syntheticTripDetailsFromBookingResult(br);
    expect(syn.bookingDetails?.images).toEqual([
      'https://cdn.example/a.jpg',
      'https://cdn.example/b.jpg',
    ]);
  });

  it('uses imageUrl as a single-image list when images is empty', () => {
    const br: HotelBookingResponse = {
      voyaBookingReference: 'VOYA-4',
      status: 'confirmed',
      hotel: minimalHotel({
        images: [],
        imageUrl: 'https://cdn.example/only.jpg',
      }),
    };
    const syn = syntheticTripDetailsFromBookingResult(br);
    expect(syn.bookingDetails?.images).toEqual(['https://cdn.example/only.jpg']);
  });
});

describe('hotelTripDetailsToPanelProps', () => {
  it('returns null when success is false', () => {
    const detail = {
      success: false,
      bookingDetails: { hotelName: 'X', city: 'Y', totalPrice: 10, currency: 'USD' },
    } as HotelTripDetailsResponse;
    expect(hotelTripDetailsToPanelProps(detail, 'REF')).toBeNull();
  });

  it('returns null when bookingDetails is empty', () => {
    const detail: HotelTripDetailsResponse = {
      success: true,
      voyaBookingReference: 'REF',
      bookingDetails: {},
      errors: null,
    };
    expect(hotelTripDetailsToPanelProps(detail, 'REF')).toBeNull();
  });

  it('uses hotelCity when city is absent (camelCase trip-details)', () => {
    const detail: HotelTripDetailsResponse = {
      success: true,
      voyaBookingReference: 'voya-ref-88',
      bookingStatus: 'BOOKED',
      bookingDetails: {
        hotelName: 'Grand Plaza',
        hotelCity: 'Madrid',
        address: 'Calle 1',
        checkIn: '2025-06-01',
        checkOut: '2025-06-05',
        currency: 'EUR',
        totalPrice: 450,
        guests: [],
        rooms: [{ name: 'Standard' }],
      },
      errors: null,
    };
    const panel = hotelTripDetailsToPanelProps(detail, 'voya-ref-88');
    expect(panel?.destinationTitle).toBe('Madrid');
    expect(panel?.headlineCity).toBe('Madrid');
    expect(panel?.hotelCity).toBe('Madrid');
  });

  it('maps a representative trip-details shape to panel props', () => {
    const detail: HotelTripDetailsResponse = {
      success: true,
      voyaBookingReference: 'voya-ref-99',
      bookingStatus: 'BOOKED',
      bookingDetails: {
        hotelName: 'Grand Plaza',
        city: 'Barcelona',
        address: 'Carrer 1',
        checkIn: '2025-06-01',
        checkOut: '2025-06-05',
        currency: 'EUR',
        totalPrice: 450,
        guests: [
          {
            title: 'Mr',
            firstName: 'Jo',
            lastName: 'Bloggs',
            email: 'jo@example.com',
          },
        ],
        rooms: [{ name: 'Deluxe', boardType: 'BB' }],
      },
      errors: null,
    };
    const panel = hotelTripDetailsToPanelProps(detail, 'voya-ref-99');
    expect(panel).not.toBeNull();
    expect(panel?.reservationCode).toBe('VOYA-REF-99');
    expect(panel?.paymentAmountFormatted).toContain('450.00');
    expect(panel?.paymentAmountFormatted).toContain('EUR');
    expect(panel?.roomTypeName).toBe('Deluxe');
    expect(panel?.roomAmenityChip).toBe('BB');
    expect(panel?.hotelCity).toBe('Barcelona');
  });

  it('uses singular night for a 1-night stay from check-in/out dates', () => {
    const detail: HotelTripDetailsResponse = {
      success: true,
      voyaBookingReference: 'voya-ref-1n',
      bookingStatus: 'BOOKED',
      bookingDetails: {
        hotelName: 'Grand Plaza',
        city: 'Barcelona',
        checkIn: '2025-06-01',
        checkOut: '2025-06-02',
        currency: 'EUR',
        totalPrice: 100,
        guests: [],
        rooms: [{ name: 'Standard' }],
      },
      errors: null,
    };
    const panel = hotelTripDetailsToPanelProps(detail, 'voya-ref-1n');
    expect(panel?.nightsAdultsLine).toContain('1 night');
    expect(panel?.nightsAdultsLine).not.toContain('1 nights');
  });
});
