/**
 * Static mock hotel data for Storybook stories — hotel detail, preferences, and supporting UI.
 *
 * Shape-matched to the live backend contracts so stories render like production.
 * Import types from @/types — never redefine shapes inline.
 *
 * Sibling fixture for the search/results track: mockHotelData.ts (if created).
 */

import type { CancellationPolicy, HotelItinerary, RoomOccupancy } from '@/types/hotels';
import type { ExtractedHotelSearchData } from '@/types/api.helpers';

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

export const CHECKIN_DATE = '2026-07-14';
export const CHECKOUT_DATE = '2026-07-21';
export const STAY_NIGHTS = 7;

// ---------------------------------------------------------------------------
// Mock hotel objects (shape-matched to Hotel / HotelItinerary)
// ---------------------------------------------------------------------------

export const mockHotelItinerary: HotelItinerary = {
  id: 'hotel-bcn-001',
  tokenId: 'tok-bcn-001',
  name: 'Gran Hotel Barcelona',
  address: 'Carrer de Provença 185',
  city: 'Barcelona',
  country: 'Spain',
  starRating: 4,
  latitude: 41.3917,
  longitude: 2.165,
  imageUrl: 'https://picsum.photos/seed/hotel-bcn/800/600',
  images: [
    'https://picsum.photos/seed/hotel-bcn-1/800/600',
    'https://picsum.photos/seed/hotel-bcn-2/800/600',
    'https://picsum.photos/seed/hotel-bcn-3/800/600',
  ],
  amenities: ['WiFi', 'Pool', 'Spa', 'Gym', 'Restaurant', 'Bar'],
  description: 'A beautiful 4-star hotel in the heart of Barcelona near Passeig de Gràcia.',
  startingPrice: { currency: 'EUR', amount: 980, perNight: 140 },
  thumbnailUrl: 'https://picsum.photos/seed/hotel-bcn/400/300',
  propertyType: 'Hotel',
  total: 1078,
  originalTotal: 1000,
  platformFeePercentage: 7.8,
};

/** Minimal hotel with no image (triggers fallback rendering). */
export const mockHotelItineraryNoImage: HotelItinerary = {
  id: 'hotel-ams-002',
  tokenId: 'tok-ams-002',
  name: 'Amsterdam Canal View',
  address: 'Keizersgracht 220',
  city: 'Amsterdam',
  country: 'Netherlands',
  starRating: 3,
  latitude: 52.373,
  longitude: 4.892,
  startingPrice: { currency: 'EUR', amount: 490, perNight: 70 },
  propertyType: 'Boutique Hotel',
};

// ---------------------------------------------------------------------------
// Cancellation policies
// ---------------------------------------------------------------------------

/** Free cancellation — refundable with deadline. */
export const mockFreeCancellationPolicy: CancellationPolicy = {
  refundable: true,
  deadline: '2026-07-10T23:59:00',
  description: 'Free cancellation until 23:59 on 10 Jul 2026. After that date a penalty applies.',
};

/** Non-refundable rate. */
export const mockNonRefundablePolicy: CancellationPolicy = {
  refundable: false,
  penaltyAmount: 140,
  penaltyCurrency: 'EUR',
  description: 'This rate is non-refundable. Cancellation will incur a 100% penalty.',
};

/** String-form policy (from rate-rules API). */
export const mockStringCancellationPolicy =
  'Non-refundable. Full payment is charged at time of booking. ' +
  'Cancellation after booking forfeits the full amount.';

// ---------------------------------------------------------------------------
// Price breakdown inputs
// ---------------------------------------------------------------------------

export const mockPriceBreakdown = {
  hotelAmount: 1000,
  platformFeePercentage: 7.8,
  totalAmount: 1078,
  currency: 'EUR',
};

export const mockPriceBreakdownWithVoucher = {
  ...mockPriceBreakdown,
  voucherDiscountCents: 5000, // $50 discount
  voucherCode: 'VOYA-DEMO-1234',
};

export const mockPriceBreakdownLongStay = {
  hotelAmount: 4200,
  platformFeePercentage: 7.8,
  totalAmount: 4527.6,
  currency: 'USD',
};

// ---------------------------------------------------------------------------
// Room configurations (RoomOccupancy)
// ---------------------------------------------------------------------------

export const singleRoom: RoomOccupancy[] = [
  { roomNo: 1, adult: 2, child: 0, childAge: [0] },
];

export const multiRoom: RoomOccupancy[] = [
  { roomNo: 1, adult: 2, child: 1, childAge: [7] },
  { roomNo: 2, adult: 1, child: 0, childAge: [0] },
];

export const maxGuestsRoom: RoomOccupancy[] = [
  { roomNo: 1, adult: 4, child: 3, childAge: [5, 8, 12] },
  { roomNo: 2, adult: 3, child: 2, childAge: [6, 10] },
];

// ---------------------------------------------------------------------------
// Image arrays for lightbox
// ---------------------------------------------------------------------------

export const mockImageUrls = [
  'https://picsum.photos/seed/hotel-room-1/1200/800',
  'https://picsum.photos/seed/hotel-room-2/1200/800',
  'https://picsum.photos/seed/hotel-room-3/1200/800',
  'https://picsum.photos/seed/hotel-room-4/1200/800',
  'https://picsum.photos/seed/hotel-room-5/1200/800',
];

export const singleImageUrl = ['https://picsum.photos/seed/hotel-single/1200/800'];

// ---------------------------------------------------------------------------
// ExtractedHotelSearchData — for HotelSearchResultsPanel
//
// Hotels in categories use snake_case keys (hotelMapper reads these).
// ---------------------------------------------------------------------------

const mockRawHotel = (overrides: Record<string, unknown> = {}): Record<string, unknown> => ({
  hotel_id: 'hotel-bcn-001',
  token_id: 'tok-bcn-001',
  hotel_name: 'Gran Hotel Barcelona',
  city: 'Barcelona',
  country: 'Spain',
  hotel_rating: 4,
  total_price: 1078,
  per_night_price: 154,
  currency: 'EUR',
  thumbnail_url: 'https://picsum.photos/seed/hotel-bcn/400/300',
  property_type: 'Hotel',
  fare_type: 'PublicRate',
  facilities: ['WiFi', 'Pool', 'Spa'],
  ...overrides,
});

const mockRawHotelCheap = (overrides: Record<string, unknown> = {}): Record<string, unknown> => ({
  hotel_id: 'hotel-ams-002',
  token_id: 'tok-ams-002',
  hotel_name: 'Amsterdam Budget Inn',
  city: 'Amsterdam',
  country: 'Netherlands',
  hotel_rating: 3,
  total_price: 490,
  per_night_price: 70,
  currency: 'EUR',
  thumbnail_url: 'https://picsum.photos/seed/hotel-ams/400/300',
  property_type: 'Hostel',
  fare_type: 'PublicRate',
  facilities: ['WiFi', 'Breakfast'],
  ...overrides,
});

const mockRawHotelHighRated = (overrides: Record<string, unknown> = {}): Record<string, unknown> => ({
  hotel_id: 'hotel-bcn-003',
  token_id: 'tok-bcn-003',
  hotel_name: 'W Barcelona',
  city: 'Barcelona',
  country: 'Spain',
  hotel_rating: 5,
  total_price: 2100,
  per_night_price: 300,
  currency: 'EUR',
  thumbnail_url: 'https://picsum.photos/seed/hotel-w/400/300',
  property_type: 'Resort',
  fare_type: 'PublicRate',
  facilities: ['WiFi', 'Pool', 'Spa', 'Beachfront'],
  trip_advisor_rating: 4.8,
  ...overrides,
});

export const mockExtractedHotelSearchData: ExtractedHotelSearchData = {
  session_id: 'sess-bcn-story-001',
  data: {
    search_params: {
      destination_city: 'Barcelona',
      country: 'Spain',
      check_in_date: CHECKIN_DATE,
      check_out_date: CHECKOUT_DATE,
      rooms: 1,
      adults: 2,
      children: 0,
    },
    summary: {
      total_hotels: 24,
      nights: STAY_NIGHTS,
      price_range: {
        min: 490,
        max: 2100,
        currency: 'EUR',
      },
    },
    categories: {
      best_value: {
        label: 'Best Value',
        hotels: [mockRawHotel()],
      },
      cheapest: {
        label: 'Cheapest',
        hotels: [mockRawHotelCheap()],
      },
      highest_rated: {
        label: 'Highest Rated',
        hotels: [mockRawHotelHighRated()],
      },
    },
  },
  hotels: [mockRawHotel(), mockRawHotelCheap(), mockRawHotelHighRated()],
};
