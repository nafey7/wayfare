/**
 * Hotel result utilities for chat: image resolution, mapping backend data to display shape.
 * Hotel result display utilities (migrated from legacy CRA frontend)
 */

/** Round to 2 decimal places for currency (matches flight search and hotel-booker). */
function round2(value: number | null | undefined): number | null | undefined {
  if (value == null || Number.isNaN(Number(value))) return value;
  return Math.round(Number(value) * 100) / 100;
}

/**
 * Backend origin for resolving relative image URLs (e.g. /imgproxy/...).
 * Chat runs on frontend origin; imgproxy is served by the backend.
 */
function getBackendOrigin(): string {
  const apiUrl = import.meta.env.VITE_API_URL;
  if (!apiUrl || apiUrl === 'undefined' || String(apiUrl).trim() === '') {
    return import.meta.env.MODE === 'production' ? '' : 'http://localhost:8000';
  }
  const trimmed = String(apiUrl).trim();
  if (trimmed.startsWith('/')) return '';
  try {
    return new URL(trimmed).origin;
  } catch {
    return import.meta.env.MODE === 'production' ? '' : 'http://localhost:8000';
  }
}

/**
 * Resolves hotel image URL for use in <img src>. Backend returns relative paths
 * (e.g. "/imgproxy/insecure/rs:fit:400:300/..."); these must be loaded from the backend origin.
 */
export function resolveHotelImageUrl(url: string | null | undefined): string | null {
  if (url == null || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('/')) {
    const origin = getBackendOrigin();
    return origin ? `${origin}${trimmed}` : trimmed;
  }
  return trimmed;
}

/**
 * Normalized hotel shape for display in chat cards and modal.
 * Price fields rounded to 2 decimals (same as flight results).
 */
export interface MappedHotel {
  hotel_id: string;
  token_id: string;
  product_id: string;
  hotel_name: string;
  city: string;
  country: string;
  address: string;
  locality: string;
  hotel_rating: number;
  trip_advisor_rating: number | null;
  trip_advisor_reviews: number | string | null;
  total_price: number;
  per_night_price: number;
  currency: string;
  fare_type: string;
  original_total_fare: number | null;
  platform_fee_percentage: number | null;
  facilities: string[];
  property_type: string;
  thumbnail_url: string | null;
  distance_value: number | string | null;
  distance_unit: string | null;
}

type RawHotel = Record<string, unknown>;

/**
 * Maps raw hotel data from backend to normalized format for display.
 * Handles different field naming conventions (snake_case, camelCase).
 */
export function hotelMapper(hotel: RawHotel | null | undefined): MappedHotel | null {
  if (!hotel || typeof hotel !== 'object') return null;

  const getStr = (...keys: string[]) => {
    for (const k of keys) {
      const v = hotel[k];
      if (v != null && String(v).trim() !== '') return String(v).trim();
    }
    return '';
  };
  const getNum = (val: unknown, def: number): number => {
    if (val == null) return def;
    const n = Number(val);
    return Number.isNaN(n) ? def : n;
  };

  return {
    hotel_id: getStr('hotel_id', 'hotelId') || '',
    token_id: getStr('token_id', 'tokenId') || '',
    product_id: getStr('product_id', 'productId') || '',

    hotel_name:
      getStr('hotel_name', 'hotelName', 'name') || 'Unknown Hotel',
    city: getStr('city'),
    country: getStr('country'),
    address: getStr('address'),
    locality: getStr('locality'),

    hotel_rating: getNum(hotel.hotel_rating ?? hotel.hotelRating ?? hotel.star_rating, 0),
    trip_advisor_rating:
      (hotel.trip_advisor_rating ?? hotel.tripAdvisorRating) != null
        ? Number(hotel.trip_advisor_rating ?? hotel.tripAdvisorRating)
        : null,
    trip_advisor_reviews: (() => {
      const v = hotel.trip_advisor_reviews ?? hotel.tripAdvisorReviews;
      if (v == null) return null;
      if (typeof v === 'number' || typeof v === 'string') return v;
      return null;
    })(),

    total_price: round2(getNum(hotel.total_price ?? hotel.totalPrice ?? hotel.total, 0)) ?? 0,
    per_night_price: round2(getNum(hotel.per_night_price ?? hotel.perNightPrice, 0)) ?? 0,
    currency: getStr('currency') || 'GBP',
    fare_type: getStr('fare_type', 'fareType'),
    original_total_fare:
      hotel.original_total_fare != null
        ? (round2(Number(hotel.original_total_fare)) ?? null)
        : null,
    platform_fee_percentage:
      hotel.platform_fee_percentage != null
        ? Number(hotel.platform_fee_percentage)
        : null,

    facilities: Array.isArray(hotel.facilities)
      ? (hotel.facilities as unknown[]).map((f) => String(f))
      : [],
    property_type: getStr('property_type', 'propertyType'),

    thumbnail_url:
      getStr(
        'thumbnail_url',
        'thumbnailUrl',
        'thumbNailUrl',
        'image_url',
        'imageUrl'
      ) || null,

    distance_value: (() => {
      const v = hotel.distance_value ?? hotel.distanceValue;
      if (v == null) return null;
      if (typeof v === 'number' || typeof v === 'string') return v;
      return null;
    })(),
    distance_unit: (() => {
      const v = hotel.distance_unit ?? hotel.distanceUnit;
      if (v == null || typeof v !== 'string') return null;
      return v;
    })(),
  };
}
