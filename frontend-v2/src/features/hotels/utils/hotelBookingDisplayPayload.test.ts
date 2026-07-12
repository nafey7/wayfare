import { describe, expect, it } from 'vitest';
import { buildHotelBookingDisplayPayload } from './hotelBookingDisplayPayload';
import type { HotelItinerary } from '@/types/hotels';

const baseHotel: HotelItinerary = {
  id: 'hid',
  tokenId: 'tok',
  name: 'Grand Hotel',
  address: '1 Main St',
  city: 'Barcelona',
  country: 'ES',
  starRating: 4,
  latitude: 41.3874,
  longitude: 2.1686,
  startingPrice: { currency: 'EUR', amount: 100, perNight: 50 },
  thumbnailUrl: 'https://cdn.example/thumb.jpg',
};

describe('buildHotelBookingDisplayPayload', () => {
  it('returns undefined for null', () => {
    expect(buildHotelBookingDisplayPayload(null)).toBeUndefined();
  });

  it('maps name, city, address, thumbnailUrl, coordinates', () => {
    expect(buildHotelBookingDisplayPayload(baseHotel)).toEqual({
      hotelImageUrl: 'https://cdn.example/thumb.jpg',
      hotelName: 'Grand Hotel',
      hotelCity: 'Barcelona',
      hotelAddress: '1 Main St',
      hotelLatitude: 41.3874,
      hotelLongitude: 2.1686,
    });
  });

  it('prefers thumbnailUrl over imageUrl and images', () => {
    const h: HotelItinerary = {
      ...baseHotel,
      thumbnailUrl: 'https://a/thumb',
      imageUrl: 'https://b/img',
      images: ['https://c/first'],
    };
    expect(buildHotelBookingDisplayPayload(h)?.hotelImageUrl).toBe('https://a/thumb');
  });

  it('falls back to imageUrl then images', () => {
    const noThumb: HotelItinerary = {
      ...baseHotel,
      thumbnailUrl: undefined,
      imageUrl: 'https://fallback.jpg',
    };
    expect(buildHotelBookingDisplayPayload(noThumb)?.hotelImageUrl).toBe(
      'https://fallback.jpg'
    );
  });
});
