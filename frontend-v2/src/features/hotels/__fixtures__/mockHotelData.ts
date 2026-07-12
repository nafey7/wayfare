/**
 * Static mock hotel data for Storybook stories.
 *
 * Shaped to match the live backend contracts so stories render the same as
 * production. No API calls, no randomness. Import types from @/types — never
 * redefine shapes inline.
 *
 * Two shapes are exported:
 *   1. HotelItinerary — for components that take Hotel / HotelItinerary directly
 *      (HotelCard, HotelResults, HotelMapView, HotelMapMarker)
 *   2. Record<string, unknown> / ExtractedHotelSearchData — for components that
 *      consume the raw chat payload (HotelSearchResultsPanel)
 *      These go through hotelMapper(), so they use snake_case field names.
 *
 * Pre-flight: fields in these fixtures were cross-checked against every render util
 * that reads them (hotelMapper, getHotelTotal, getHotelCurrency)
 * so all cards render real data — no N/A placeholders.
 */

import type { ExtractedHotelSearchData } from '@/types/api.helpers';
import type { HotelItinerary, RoomOccupancy } from '@/types/hotels';
import type { FilterableHotel, HotelFilterState } from '@/features/hotels/utils/hotelFilters';
import { defaultHotelFilterState } from '@/features/hotels/utils/hotelFilters';
import type { HotelSortOption } from '@/features/hotels/utils/hotelSort';

export { defaultHotelFilterState };
export type { HotelFilterState, HotelSortOption };

// ---------------------------------------------------------------------------
// Shared constants
// ---------------------------------------------------------------------------

export const MOCK_CHECKIN = '2026-07-10';
export const MOCK_CHECKOUT = '2026-07-17';
export const MOCK_NIGHTS = 7;

// ---------------------------------------------------------------------------
// HotelItinerary fixtures — used directly as props (HotelCard, HotelResults, map)
// ---------------------------------------------------------------------------

export const mockHotelBestValue: HotelItinerary = {
  id: 'hotel-bcn-001',
  tokenId: 'tok-bcn-001',
  productId: 'prod-bcn-001',
  name: 'Hotel Arts Barcelona',
  address: 'Carrer de la Marina, 19-21',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 5,
  latitude: 41.3851,
  longitude: 2.1734,
  description: 'Luxurious beachfront hotel in Barcelona with stunning Mediterranean views.',
  startingPrice: { currency: 'EUR', amount: 1540.0, perNight: 220.0 },
  total: 1540.0,
  fareType: 'Room Only',
  propertyType: 'Hotel',
  facilities: ['WiFi', 'Pool', 'Spa', 'Gym', 'Restaurant'],
};

export const mockHotelCheapest: HotelItinerary = {
  id: 'hotel-bcn-002',
  tokenId: 'tok-bcn-002',
  productId: 'prod-bcn-002',
  name: 'Barceló Raval',
  address: 'Rambla del Raval, 17-21',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 4,
  latitude: 41.3784,
  longitude: 2.1685,
  description: 'Modern 4-star hotel in the vibrant Raval neighbourhood.',
  startingPrice: { currency: 'EUR', amount: 595.0, perNight: 85.0 },
  total: 595.0,
  fareType: 'Room Only',
  propertyType: 'Hotel',
  facilities: ['WiFi', 'Gym', 'Restaurant'],
};

export const mockHotelHighestRated: HotelItinerary = {
  id: 'hotel-bcn-003',
  tokenId: 'tok-bcn-003',
  productId: 'prod-bcn-003',
  name: 'Mandarin Oriental Barcelona',
  address: 'Passeig de Gràcia, 38-40',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 5,
  latitude: 41.3916,
  longitude: 2.1649,
  description: 'Iconic 5-star hotel on the famous Passeig de Gràcia boulevard.',
  startingPrice: { currency: 'EUR', amount: 2100.0, perNight: 300.0 },
  total: 2100.0,
  fareType: 'Breakfast included',
  propertyType: 'Hotel',
  facilities: ['WiFi', 'Pool', 'Spa', 'Gym', 'Restaurant', 'Bar'],
};

const mockHotelExtra1: HotelItinerary = {
  id: 'hotel-bcn-004',
  tokenId: 'tok-bcn-004',
  productId: 'prod-bcn-004',
  name: 'NH Collection Barcelona Gran Hotel Calderón',
  address: 'Rambla de Catalunya, 26',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 4,
  latitude: 41.3905,
  longitude: 2.1647,
  startingPrice: { currency: 'EUR', amount: 826.0, perNight: 118.0 },
  total: 826.0,
  fareType: 'Room Only',
  propertyType: 'Hotel',
  facilities: ['WiFi', 'Pool', 'Gym'],
};

const mockHotelExtra2: HotelItinerary = {
  id: 'hotel-bcn-005',
  tokenId: 'tok-bcn-005',
  productId: 'prod-bcn-005',
  name: 'Ibis Barcelona Passeig De Gracia',
  address: 'Passeig de Gràcia, 46',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 3,
  latitude: 41.3931,
  longitude: 2.165,
  startingPrice: { currency: 'EUR', amount: 350.0, perNight: 50.0 },
  total: 350.0,
  fareType: 'Room Only',
  propertyType: 'Hotel',
  facilities: ['WiFi'],
};

/** Ordered list of all fixture hotels: bestValue, cheapest, highestRated, extras. */
export const mockHotelList: HotelItinerary[] = [
  mockHotelBestValue,
  mockHotelCheapest,
  mockHotelHighestRated,
  mockHotelExtra1,
  mockHotelExtra2,
];

// ---------------------------------------------------------------------------
// FilterableHotel fixtures — for HotelResults / HotelFiltersPanel
// ---------------------------------------------------------------------------

/** Converts a HotelItinerary to a FilterableHotel for filter/sort components. */
function toFilterable(h: HotelItinerary): FilterableHotel {
  return {
    id: h.id,
    tokenId: h.tokenId,
    name: h.name,
    productId: h.productId,
    starRating: h.starRating,
    fareType: h.fareType,
    total: h.total ?? h.startingPrice.amount,
    currency: h.startingPrice.currency,
    propertyType: h.propertyType,
    facilities: h.facilities ?? [],
    address: h.address,
    city: h.city,
  };
}

export const mockFilterableHotels: FilterableHotel[] = mockHotelList.map(toFilterable);

export const mockActiveFilterState: HotelFilterState = {
  ...defaultHotelFilterState,
  starRatings: [4, 5],
  nameQuery: 'Barcelona',
};

// ---------------------------------------------------------------------------
// RoomOccupancy fixtures — for HotelSearchBarV2 stories
// ---------------------------------------------------------------------------

export const mockSingleRoom: RoomOccupancy[] = [
  { roomNo: 1, adult: 2, child: 0, childAge: [] },
];

export const mockMultipleRooms: RoomOccupancy[] = [
  { roomNo: 1, adult: 2, child: 0, childAge: [] },
  { roomNo: 2, adult: 1, child: 1, childAge: [7] },
];

// ---------------------------------------------------------------------------
// Raw chat-format hotel records — for ExtractedHotelSearchData categories.
// These go through hotelMapper() so they use snake_case field names.
// Every field the renderer reads is explicitly set (no N/A risk).
// ---------------------------------------------------------------------------

const chatHotelBestValue: Record<string, unknown> = {
  hotel_id: 'hotel-bcn-001',
  token_id: 'tok-bcn-001',
  product_id: 'prod-bcn-001',
  hotel_name: 'Hotel Arts Barcelona',
  name: 'Hotel Arts Barcelona',
  city: 'Barcelona',
  country: 'Spain',
  address: 'Carrer de la Marina, 19-21',
  locality: 'Poblenou',
  hotel_rating: 5,
  total_price: 1540.0,
  per_night_price: 220.0,
  currency: 'EUR',
  fare_type: 'Room Only',
  property_type: 'Hotel',
  latitude: 41.3851,
  longitude: 2.1734,
  thumbnail_url: null,
  facilities: ['WiFi', 'Pool', 'Spa'],
};

const chatHotelCheapest: Record<string, unknown> = {
  hotel_id: 'hotel-bcn-002',
  token_id: 'tok-bcn-002',
  product_id: 'prod-bcn-002',
  hotel_name: 'Barceló Raval',
  name: 'Barceló Raval',
  city: 'Barcelona',
  country: 'Spain',
  address: 'Rambla del Raval, 17-21',
  locality: 'El Raval',
  hotel_rating: 4,
  total_price: 595.0,
  per_night_price: 85.0,
  currency: 'EUR',
  fare_type: 'Room Only',
  property_type: 'Hotel',
  latitude: 41.3784,
  longitude: 2.1685,
  thumbnail_url: null,
  facilities: ['WiFi', 'Gym'],
};

const chatHotelHighestRated: Record<string, unknown> = {
  hotel_id: 'hotel-bcn-003',
  token_id: 'tok-bcn-003',
  product_id: 'prod-bcn-003',
  hotel_name: 'Mandarin Oriental Barcelona',
  name: 'Mandarin Oriental Barcelona',
  city: 'Barcelona',
  country: 'Spain',
  address: 'Passeig de Gràcia, 38-40',
  locality: 'Eixample',
  hotel_rating: 5,
  total_price: 2100.0,
  per_night_price: 300.0,
  currency: 'EUR',
  fare_type: 'Breakfast included',
  property_type: 'Hotel',
  latitude: 41.3916,
  longitude: 2.1649,
  thumbnail_url: null,
  facilities: ['WiFi', 'Pool', 'Spa'],
};

/**
 * Shape-matched ExtractedHotelSearchData fixture.
 * summary.nights and price_range.currency are set (PR #703 root cause: omitting them
 * produced "1 night. Prices start from £85" instead of "7 nights. Prices start from €595").
 */
export const mockExtractedHotelSearchData: ExtractedHotelSearchData = {
  session_id: 'sess-hotel-bcn-2026',
  hotels: [chatHotelBestValue, chatHotelCheapest, chatHotelHighestRated],
  data: {
    search_params: {
      destination_city: 'Barcelona',
      country: 'Spain',
      check_in_date: MOCK_CHECKIN,
      check_out_date: MOCK_CHECKOUT,
      rooms: 1,
      adults: 2,
      children: 0,
    },
    summary: {
      total_found: 48,
      nights: MOCK_NIGHTS,
      price_range: {
        min: 595,
        max: 2100,
        currency: 'EUR',
      },
    },
    categories: {
      cheapest: {
        label: 'Cheapest',
        hotels: [chatHotelCheapest],
      },
      best_value: {
        label: 'Best Value',
        hotels: [chatHotelBestValue],
      },
      highest_rated: {
        label: 'Highest Rated',
        hotels: [chatHotelHighestRated],
      },
    },
  },
};

/** Sort menu items used in hotel stories. */
export const mockSortMenuItems: { value: HotelSortOption; label: string }[] = [
  { value: 'price-low', label: 'Price: Low to High' },
  { value: 'price-high', label: 'Price: High to Low' },
  { value: 'rating-high', label: 'Rating: High to Low' },
  { value: 'rating-low', label: 'Rating: Low to High' },
  { value: 'name-az', label: 'Name: A to Z' },
];
