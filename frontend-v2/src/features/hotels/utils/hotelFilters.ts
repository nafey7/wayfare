/**
 * Hotel filter state and application logic.
 * Mirrors flight filter pattern: name search, price range, star rating, fare type.
 */

import type { Hotel, HotelItinerary } from '@/types/hotels';

export interface HotelFilterState {
  nameQuery: string;
  priceMin: number | null;
  priceMax: number | null;
  starRatings: number[]; // e.g. [3, 4, 5] = show 3, 4, 5 star
  propertyTypes: string[]; // e.g. ["Hotel", "Apartment"]
  refundableOnly: boolean;
  nonRefundableOnly: boolean;
  distanceMin: number | null;
  distanceMax: number | null;
  facilities: string[]; // e.g. ["WiFi", "Pool"] – hotel must have all selected (AND)
  localities: string[]; // e.g. ["8th Arrondissement"] – neighbourhood/locality
}

export const defaultHotelFilterState: HotelFilterState = {
  nameQuery: '',
  priceMin: null,
  priceMax: null,
  starRatings: [],
  propertyTypes: [],
  refundableOnly: false,
  nonRefundableOnly: false,
  distanceMin: null,
  distanceMax: null,
  facilities: [],
  localities: [],
};

/** Hotel shape used for filtering (id, price, name, rating, fareType, propertyType, distance, facilities, locality). */
export interface FilterableHotel {
  id: string;
  tokenId: string;
  name: string;
  productId?: string;
  hotelId?: string;
  starRating: number;
  fareType?: string;
  total: number;
  currency: string;
  propertyType?: string;
  /** Distance from search center in km (when provided by API). */
  distanceFromCenter?: number | null;
  /** Haversine distance in km from the requested nearby_location (set by backend). */
  nearbyDistanceKm?: number;
  /** Facility/amenity names (from API facilities or amenities). */
  facilities: string[];
  /** Neighbourhood/locality (when provided by API). */
  locality?: string;
  address?: string;
  city?: string;
  thumbnailUrl?: string;
  imageUrl?: string;
}

/** Parse numeric value; API may return string (e.g. Decimal). */
function toNumber(v: unknown): number {
  if (v == null) return NaN;
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isNaN(n) ? NaN : n;
}

/**
 * Extract total price for filtering and display (supports Hotel and HotelItinerary).
 * Prefers total (price with platform fee) to match hotel-booker reference and backend contract.
 * originalTotal is used only when total is unavailable (for breakdown, use originalTotal explicitly).
 */
export function getHotelTotal(h: Hotel | HotelItinerary): number {
  const it = h as HotelItinerary & { total?: unknown; total_price?: unknown };
  const raw =
    it.total != null
      ? it.total
      : it.total_price != null
        ? it.total_price
        : it.originalTotal != null
          ? it.originalTotal
          : h.startingPrice?.amount ?? 0;
  const n = toNumber(raw);
  return Number.isNaN(n) ? 0 : n;
}

/** Extract currency from hotel. */
export function getHotelCurrency(h: Hotel | HotelItinerary): string {
  const raw = h as { currency?: string };
  return h.startingPrice?.currency ?? raw.currency ?? 'USD';
}

/** Convert ISO currency code to its display symbol (e.g. "USD" → "$", "EUR" → "€"). */
export function hotelCurrencySymbol(code: string): string {
  try {
    // Use en-US locale so USD renders as "$" not "US $" regardless of browser locale.
    const parts = Intl.NumberFormat('en-US', { style: 'currency', currency: code }).formatToParts(0);
    return parts.find((p) => p.type === 'currency')?.value ?? code;
  } catch {
    return code;
  }
}

/** Normalize hotel to FilterableHotel for filter/sort. */
export function toFilterableHotel(h: Hotel | HotelItinerary): FilterableHotel {
  const it = h as HotelItinerary;
  const raw = h as unknown as Record<string, unknown>;
  const distance =
    raw.distanceValue != null && typeof raw.distanceValue === 'number'
      ? raw.distanceValue
      : raw.distance_value != null && typeof raw.distance_value === 'number'
        ? raw.distance_value
        : null;
  const facilitiesRaw = raw.facilities ?? h.amenities;
  const facilities: string[] = Array.isArray(facilitiesRaw)
    ? facilitiesRaw.filter((f): f is string => typeof f === 'string' && f.trim() !== '')
    : [];
  const locality =
    typeof raw.locality === 'string' && raw.locality.trim() !== ''
      ? raw.locality.trim()
      : typeof raw.locality_name === 'string' && raw.locality_name.trim() !== ''
        ? raw.locality_name.trim()
        : undefined;
  const nearbyDist = typeof raw.nearbyDistanceKm === 'number' ? raw.nearbyDistanceKm : undefined;
  return {
    id: h.id,
    tokenId: h.tokenId,
    name: h.name ?? (it as { hotelName?: string }).hotelName ?? '',
    productId: it.productId,
    hotelId: h.id,
    starRating: h.starRating ?? 0,
    fareType: it.fareType,
    total: getHotelTotal(h),
    currency: getHotelCurrency(h),
    propertyType: it.propertyType,
    distanceFromCenter: distance ?? undefined,
    nearbyDistanceKm: nearbyDist,
    facilities,
    locality,
    address: h.address,
    city: h.city,
    thumbnailUrl: it.thumbnailUrl ?? h.imageUrl,
    imageUrl: h.imageUrl,
  };
}

function arrayEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((x, i) => sb[i] === x);
}

export function isDefaultHotelFilterState(state: HotelFilterState): boolean {
  const d = defaultHotelFilterState;
  return (
    state.nameQuery === d.nameQuery &&
    state.priceMin === d.priceMin &&
    state.priceMax === d.priceMax &&
    state.starRatings.length === 0 &&
    arrayEqual(state.propertyTypes, d.propertyTypes) &&
    state.refundableOnly === d.refundableOnly &&
    state.nonRefundableOnly === d.nonRefundableOnly &&
    state.distanceMin === d.distanceMin &&
    state.distanceMax === d.distanceMax &&
    arrayEqual(state.facilities, d.facilities) &&
    arrayEqual(state.localities, d.localities)
  );
}

/**
 * Filter hotels by the given filter state.
 */
export function filterHotels<T extends FilterableHotel>(
  hotels: T[],
  state: HotelFilterState
): T[] {
  return hotels.filter((hotel) => {
    if (state.nameQuery.trim()) {
      const q = state.nameQuery.trim().toLowerCase();
      const name = (hotel.name ?? '').toLowerCase();
      if (!name.includes(q)) return false;
    }
    if (state.priceMin !== null && hotel.total < state.priceMin) return false;
    if (state.priceMax !== null && hotel.total > state.priceMax) return false;
    if (state.starRatings.length > 0) {
      if (!state.starRatings.includes(hotel.starRating)) return false;
    }
    if (state.propertyTypes.length > 0) {
      const normalized =
        hotel.propertyType?.trim() ? hotel.propertyType.trim() : 'Others';
      if (!state.propertyTypes.includes(normalized)) return false;
    }
    if (state.refundableOnly) {
      const ft = (hotel.fareType ?? '').toLowerCase();
      const isNonRefund = ft.includes('non-refund') || ft.includes('nonrefund');
      if (!ft.includes('refund') || isNonRefund) return false;
    }
    if (state.nonRefundableOnly) {
      const ft = (hotel.fareType ?? '').toLowerCase();
      if (!ft.includes('non-refund') && !ft.includes('nonrefund')) return false;
    }
    const distance = hotel.distanceFromCenter ?? null;
    if (distance !== null) {
      if (state.distanceMin !== null && distance < state.distanceMin) return false;
      if (state.distanceMax !== null && distance > state.distanceMax) return false;
    }
    if (state.facilities.length > 0) {
      const hotelFacilities = hotel.facilities ?? [];
      const hasAll = state.facilities.every((f) => hotelFacilities.includes(f));
      if (!hasAll) return false;
    }
    if (state.localities.length > 0) {
      const loc = hotel.locality?.trim();
      if (!loc || !state.localities.includes(loc)) return false;
    }
    return true;
  });
}

/** Extract unique property types from hotels for filter options. "Others" for empty/null. */
export function extractPropertyTypesFromHotels(
  hotels: FilterableHotel[]
): string[] {
  const set = new Set<string>();
  for (const h of hotels) {
    const t = h.propertyType?.trim();
    set.add(t ? t : 'Others');
  }
  const arr = Array.from(set);
  const othersIndex = arr.indexOf('Others');
  if (othersIndex > -1) {
    arr.splice(othersIndex, 1);
  }
  arr.sort((a, b) => a.localeCompare(b));
  if (othersIndex > -1) {
    arr.push('Others');
  }
  return arr;
}

/** Extract unique facilities from all hotels (sorted). */
export function extractFacilitiesFromHotels(hotels: FilterableHotel[]): string[] {
  const set = new Set<string>();
  for (const h of hotels) {
    for (const f of h.facilities ?? []) {
      const t = f?.trim();
      if (t) set.add(t);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

/** Extract unique localities from all hotels (sorted). */
export function extractLocalitiesFromHotels(hotels: FilterableHotel[]): string[] {
  const set = new Set<string>();
  for (const h of hotels) {
    const loc = h.locality?.trim();
    if (loc) set.add(loc);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

/** Count how many filter categories are non-default (for "Filters (N)" badge). */
export function countActiveHotelFilters(state: HotelFilterState): number {
  let count = 0;
  if (state.nameQuery.trim()) count++;
  if (state.priceMin !== null || state.priceMax !== null) count++;
  if (state.starRatings.length > 0) count++;
  if (state.propertyTypes.length > 0) count++;
  if (state.facilities.length > 0) count++;
  if (state.localities.length > 0) count++;
  if (state.refundableOnly || state.nonRefundableOnly) count++;
  if (state.distanceMin !== null || state.distanceMax !== null) count++;
  return count;
}

/** Distance bounds from hotels that have distanceFromCenter. */
export function getDistanceBounds(hotels: FilterableHotel[]): {
  distanceMin: number;
  distanceMax: number;
  hasDistance: boolean;
} {
  let min = Infinity;
  let max = -Infinity;
  for (const h of hotels) {
    const d = h.distanceFromCenter;
    if (d != null && typeof d === 'number') {
      if (d < min) min = d;
      if (d > max) max = d;
    }
  }
  const hasDistance = min !== Infinity && max !== -Infinity;
  if (!hasDistance) return { distanceMin: 0, distanceMax: 50, hasDistance: false };
  min = Math.floor(min * 10) / 10;
  max = Math.ceil(max * 10) / 10;
  if (max <= min) max = min + 1;
  return { distanceMin: min, distanceMax: max, hasDistance: true };
}
