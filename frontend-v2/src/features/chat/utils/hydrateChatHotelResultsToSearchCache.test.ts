import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type {
  ChatHotelInfo,
  ExtractedHotelSearchData,
  HotelSearchParams,
} from '@/types/api.helpers';
import {
  chatHotelToHotelItinerary,
  chatSearchParamsToFormParams,
  chatExtractedToHotelSearchResponse,
} from './hydrateChatHotelResultsToSearchCache';

function makeHotel(overrides: Partial<ChatHotelInfo> = {}): ChatHotelInfo {
  return {
    hotel_id: 'hotel-1',
    token_id: 'token-1',
    product_id: 'product-1',
    hotel_name: 'Hotel Atlantis',
    city: 'Barcelona',
    country: 'Spain',
    address: '1 Carrer de la Marina',
    hotel_rating: 4,
    total_price: 250.5,
    per_night_price: 125.25,
    currency: 'EUR',
    facilities: ['Wifi', 'Pool'],
    latitude: 41.3851,
    longitude: 2.1734,
    thumbnail_url: 'https://cdn.example.com/img.jpg',
    ...overrides,
  };
}

function makeSearchParams(overrides: Partial<HotelSearchParams> = {}): HotelSearchParams {
  return {
    destination_city: 'Barcelona',
    country: 'Spain',
    check_in_date: '2026-06-10',
    check_out_date: '2026-06-12',
    rooms: 1,
    adults: 2,
    children: 0,
    ...overrides,
  };
}

describe('chatHotelToHotelItinerary', () => {
  it('maps required IDs to camelCase', () => {
    const h = chatHotelToHotelItinerary(makeHotel());
    expect(h.id).toBe('hotel-1');
    expect(h.tokenId).toBe('token-1');
    expect(h.productId).toBe('product-1');
  });

  it('maps name with fallback chain (hotel_name → name → "Unknown Hotel")', () => {
    expect(chatHotelToHotelItinerary(makeHotel({ hotel_name: 'X' })).name).toBe('X');
    expect(
      chatHotelToHotelItinerary(
        makeHotel({ hotel_name: undefined, name: 'Fallback' })
      ).name
    ).toBe('Fallback');
    expect(
      chatHotelToHotelItinerary(
        makeHotel({ hotel_name: undefined, name: undefined })
      ).name
    ).toBe('Unknown Hotel');
  });

  it('maps starRating from hotel_rating, coercing string to number', () => {
    expect(chatHotelToHotelItinerary(makeHotel({ hotel_rating: 5 })).starRating).toBe(5);
    expect(chatHotelToHotelItinerary(makeHotel({ hotel_rating: '4' })).starRating).toBe(4);
    expect(chatHotelToHotelItinerary(makeHotel({ hotel_rating: undefined })).starRating).toBe(0);
  });

  it('coerces lat/lng strings to numbers via Number()', () => {
    const h = chatHotelToHotelItinerary(
      makeHotel({ latitude: '41.3851', longitude: '2.1734' })
    );
    expect(h.latitude).toBeCloseTo(41.3851);
    expect(h.longitude).toBeCloseTo(2.1734);
  });

  it('defaults invalid lat/lng to 0 (map filter will exclude these)', () => {
    const h = chatHotelToHotelItinerary(
      makeHotel({ latitude: 'not-a-number', longitude: undefined })
    );
    expect(h.latitude).toBe(0);
    expect(h.longitude).toBe(0);
  });

  it('builds startingPrice from total_price + per_night_price + currency', () => {
    const h = chatHotelToHotelItinerary(makeHotel());
    expect(h.startingPrice.amount).toBe(250.5);
    expect(h.startingPrice.perNight).toBe(125.25);
    expect(h.startingPrice.currency).toBe('EUR');
    expect(h.total).toBe(250.5);
  });

  it('defaults currency to GBP when missing', () => {
    const h = chatHotelToHotelItinerary(makeHotel({ currency: undefined }));
    expect(h.startingPrice.currency).toBe('GBP');
  });

  it('passes through facilities array', () => {
    const h = chatHotelToHotelItinerary(makeHotel({ facilities: ['Spa', 'Bar'] }));
    expect(h.facilities).toEqual(['Spa', 'Bar']);
  });

  it('leaves facilities undefined when absent', () => {
    const h = chatHotelToHotelItinerary(makeHotel({ facilities: undefined }));
    expect(h.facilities).toBeUndefined();
  });

  it('maps thumbnail_url to imageUrl and thumbnailUrl (absolute URL passes through)', () => {
    const h = chatHotelToHotelItinerary(
      makeHotel({ thumbnail_url: 'https://cdn.example.com/img.jpg' })
    );
    expect(h.imageUrl).toBe('https://cdn.example.com/img.jpg');
    expect(h.thumbnailUrl).toBe('https://cdn.example.com/img.jpg');
  });

  it('maps optional fields when present', () => {
    const h = chatHotelToHotelItinerary(
      makeHotel({
        original_total_fare: 280,
        platform_fee_percentage: 10.5,
        fare_type: 'Refundable',
        property_type: 'Hotel',
        nearby_distance_km: 1.5,
      })
    );
    expect(h.originalTotal).toBe(280);
    expect(h.platformFeePercentage).toBe(10.5);
    expect(h.fareType).toBe('Refundable');
    expect(h.propertyType).toBe('Hotel');
    expect(h.nearbyDistanceKm).toBe(1.5);
  });

});

describe('chatSearchParamsToFormParams', () => {
  it('maps destination_city first', () => {
    expect(chatSearchParamsToFormParams(makeSearchParams()).destination).toBe('Barcelona');
  });

  it('falls back to city_name', () => {
    expect(
      chatSearchParamsToFormParams(
        makeSearchParams({ destination_city: undefined, city_name: 'Lyon' })
      ).destination
    ).toBe('Lyon');
  });

  it('falls back to destination', () => {
    expect(
      chatSearchParamsToFormParams(
        makeSearchParams({
          destination_city: undefined,
          city_name: undefined,
          destination: 'Madrid',
        })
      ).destination
    ).toBe('Madrid');
  });

  it('maps check_in_date / check_out_date to checkin/checkout', () => {
    const f = chatSearchParamsToFormParams(makeSearchParams());
    expect(f.checkin).toBe('2026-06-10');
    expect(f.checkout).toBe('2026-06-12');
  });

  it('falls back to checkin/checkout when check_in_date is absent', () => {
    const f = chatSearchParamsToFormParams(
      makeSearchParams({
        check_in_date: undefined,
        check_out_date: undefined,
        checkin: '2026-08-01',
        checkout: '2026-08-05',
      })
    );
    expect(f.checkin).toBe('2026-08-01');
    expect(f.checkout).toBe('2026-08-05');
  });

  it('distributes adults evenly across rooms', () => {
    const f = chatSearchParamsToFormParams(
      makeSearchParams({ rooms: 3, adults: 6 })
    );
    expect(f.rooms).toHaveLength(3);
    expect(f.rooms!.every((r) => r.adult === 2)).toBe(true);
  });

  it('puts the remainder in the first room', () => {
    const f = chatSearchParamsToFormParams(
      makeSearchParams({ rooms: 3, adults: 5 })
    );
    expect(f.rooms![0]!.adult).toBeGreaterThan(f.rooms![1]!.adult);
    expect(f.rooms!.reduce((s, r) => s + r.adult, 0)).toBe(5);
  });

  it('defaults nationality to US', () => {
    expect(chatSearchParamsToFormParams(makeSearchParams()).nationality).toBe('US');
  });
});

describe('chatExtractedToHotelSearchResponse', () => {
  function makeExtracted(
    overrides: Partial<ExtractedHotelSearchData> = {}
  ): ExtractedHotelSearchData {
    return {
      session_id: 'sid-42',
      hotels: [
        makeHotel() as unknown as Record<string, unknown>,
        makeHotel({ hotel_id: 'hotel-2', token_id: 'token-2', product_id: 'product-2' }) as unknown as Record<string, unknown>,
      ],
      data: {
        search_params: makeSearchParams(),
        summary: { total_hotels: 2, nights: 2 },
      },
      ...overrides,
    };
  }

  it('produces a HotelSearchResponse envelope with the right shape', () => {
    const { data, params } = chatExtractedToHotelSearchResponse(makeExtracted());
    expect(data.sessionId).toBe('sid-42');
    expect(data.hotels).toHaveLength(2);
    expect(data.totalResults).toBe(2);
    expect(data.nextToken).toBeUndefined();
    expect(data.curatedHotels).toBeUndefined();
    expect(params.destination).toBe('Barcelona');
  });

  it('passes hotels through chatHotelToHotelItinerary', () => {
    const { data } = chatExtractedToHotelSearchResponse(makeExtracted());
    expect((data.hotels[0] as { tokenId?: string }).tokenId).toBe('token-1');
    expect((data.hotels[1] as { tokenId?: string }).tokenId).toBe('token-2');
  });

  it('produces a searchParams envelope from form params', () => {
    const { data } = chatExtractedToHotelSearchResponse(makeExtracted());
    expect(data.searchParams.cityName).toBe('Barcelona');
    expect(data.searchParams.countryName).toBe('Spain');
    expect(data.searchParams.checkin).toBe('2026-06-10');
    expect(data.searchParams.checkout).toBe('2026-06-12');
  });

  it('handles empty hotels array', () => {
    const { data } = chatExtractedToHotelSearchResponse(
      makeExtracted({ hotels: [] })
    );
    expect(data.hotels).toEqual([]);
    expect(data.totalResults).toBe(0);
  });

  it('defaults sessionId to empty string when missing', () => {
    const { data } = chatExtractedToHotelSearchResponse(
      makeExtracted({ session_id: '' })
    );
    expect(data.sessionId).toBe('');
  });

  describe('runtime guards (batched)', () => {
    let warn: ReturnType<typeof vi.spyOn>;
    beforeEach(() => {
      warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });
    afterEach(() => {
      warn.mockRestore();
    });

    it('emits one warn for a response containing hotels with missing IDs', () => {
      chatExtractedToHotelSearchResponse(
        makeExtracted({
          hotels: [
            makeHotel({ hotel_id: undefined }) as unknown as Record<string, unknown>,
            makeHotel({ token_id: undefined }) as unknown as Record<string, unknown>,
            makeHotel() as unknown as Record<string, unknown>,
          ],
        })
      );
      expect(warn).toHaveBeenCalledOnce();
      expect(warn.mock.calls[0][0]).toMatch(/2 hotel\(s\)/);
    });

    it('does not warn when all hotels have valid IDs', () => {
      chatExtractedToHotelSearchResponse(makeExtracted());
      expect(warn).not.toHaveBeenCalled();
    });
  });
});
