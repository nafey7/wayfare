import type { HotelSearchFormParams, RoomOccupancy } from '@/types/hotels';
import type { HotelFilterState } from '../utils/hotelFilters';
import { defaultHotelFilterState } from '../utils/hotelFilters';
import { normalizeHotelSearchFormParams } from './normalizeHotelSearchFormParams';

/**
 * Chat hotel search params (from extraData.data.search_params).
 */
export interface ChatHotelSearchParams {
  destination?: string;
  destination_city?: string;
  city_name?: string;
  country?: string;
  country_name?: string;
  check_in_date?: string;
  check_out_date?: string;
  checkin?: string;
  checkout?: string;
  rooms?: number;
  adults?: number;
  children?: number;
  // Filter fields from backend
  price_min?: number | null;
  price_max?: number | null;
  min_rating?: number | null;
  property_types?: string[] | null;
  refundable_only?: boolean | null;
  required_facilities?: string[] | null;
  max_distance_km?: number | null;
  locality?: string | null;
}

/**
 * Chat hotel filters extracted from backend search_params.
 * These are post-search filters applied client-side on the booker page.
 */
export interface ChatHotelFilters {
  priceMin: number | null;
  priceMax: number | null;
  starRatings: number[];
  propertyTypes: string[];
  refundableOnly: boolean;
  facilities: string[];
  distanceMax: number | null;
  localities: string[];
}

/**
 * Map chat hotel search params to HotelSearchFormParams for URL serialization.
 * Mirrors chatSearchParamsToUI for flights.
 */
export function chatHotelSearchParamsToUI(
  params: ChatHotelSearchParams | Record<string, unknown>
): HotelSearchFormParams {
  // Use only city name for destination (no country). Mirrors dev_ui hotel-booker:
  // destination_city in URL/form is just the city (e.g. "London"); geocoding
  // resolves country at search time via resolveCity().
  const dest =
    params.destination_city ?? params.city_name ?? params.destination ?? '';
  const destination =
    typeof dest === 'string' && dest.trim() ? dest.trim() : '';

  const checkin =
    (params.check_in_date ?? params.checkin ?? null) as string | null;
  const checkout =
    (params.check_out_date ?? params.checkout ?? null) as string | null;

  const roomsCount = Math.min(5, Math.max(1, Number(params.rooms) || 1));
  const adults = Math.min(8, Math.max(1, Number(params.adults) || 2));
  const children = Math.min(4, Math.max(0, Number(params.children) || 0));
  const childAges = children > 0 ? Array.from({ length: children }, () => 5) : [0];

  const rooms: RoomOccupancy[] = Array.from({ length: roomsCount }, (_, i) => ({
    roomNo: i + 1,
    adult: i === 0 ? adults : 1,
    child: i === 0 ? children : 0,
    childAge: i === 0 ? childAges : [0],
  }));

  return {
    destination,
    checkin: checkin && String(checkin).trim() ? checkin : null,
    checkout: checkout && String(checkout).trim() ? checkout : null,
    rooms,
    nationality: 'US',
  };
}

/**
 * Serialize hotel search form params to base64-encoded JSON for URL (?q=).
 */
export function serializeHotelSearchParamsToUrl(
  params: HotelSearchFormParams
): string {
  try {
    const json = JSON.stringify(params);
    return btoa(json);
  } catch (error) {
    console.error('Error serializing hotel search params:', error);
    return '';
  }
}

/**
 * Deserialize hotel search params from base64-encoded JSON in URL.
 */
export function deserializeHotelSearchParamsFromUrl(
  encoded: string
): HotelSearchFormParams | null {
  try {
    const json = atob(encoded);
    const parsed = JSON.parse(json) as HotelSearchFormParams;
    // Normalize rooms: ensure childAge array length matches child
    const rooms: RoomOccupancy[] = (parsed.rooms ?? []).map((r, i) => {
      const child = Math.min(4, Math.max(0, r.child ?? 0));
      const childAge = r.childAge ?? [];
      const ages =
        child === 0
          ? [0]
          : Array.from({ length: child }, (_, j) =>
              typeof childAge[j] === 'number' && childAge[j] >= 0 && childAge[j] <= 17
                ? childAge[j]
                : 5
            );
      return {
        roomNo: i + 1,
        adult: Math.min(8, Math.max(1, r.adult ?? 1)),
        child,
        childAge: ages,
      };
    });
    return {
      destination: parsed.destination ?? '',
      checkin: parsed.checkin ?? null,
      checkout: parsed.checkout ?? null,
      rooms: rooms.length > 0 ? rooms : [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
      nationality: parsed.nationality ?? 'US',
    };
  } catch (error) {
    console.error('Error deserializing hotel search params:', error);
    return null;
  }
}

/**
 * Extract post-search filters from backend hotel search_params.
 * Returns null if no filters are present (all default values).
 */
export function extractChatHotelFilters(
  params: ChatHotelSearchParams | Record<string, unknown>,
): ChatHotelFilters | null {
  const priceMin = (params.price_min as number | null | undefined) ?? null;
  const priceMax = (params.price_max as number | null | undefined) ?? null;
  const minRating = (params.min_rating as number | null | undefined) ?? null;
  const starRatings =
    minRating != null ? Array.from({ length: 5 - minRating + 1 }, (_, i) => minRating + i) : [];
  const propertyTypes = Array.isArray(params.property_types) ? params.property_types : [];
  const refundableOnly = params.refundable_only === true;
  const facilities = Array.isArray(params.required_facilities) ? params.required_facilities : [];
  const distanceMax = (params.max_distance_km as number | null | undefined) ?? null;
  const locality = (params.locality as string | null | undefined) ?? null;
  const localities = locality ? [locality] : [];

  // Return null if no filters are set
  if (
    priceMin === null &&
    priceMax === null &&
    starRatings.length === 0 &&
    propertyTypes.length === 0 &&
    !refundableOnly &&
    facilities.length === 0 &&
    distanceMax === null &&
    localities.length === 0
  ) {
    return null;
  }

  return { priceMin, priceMax, starRatings, propertyTypes, refundableOnly, facilities, distanceMax, localities };
}

/**
 * Convert ChatHotelFilters to HotelFilterState by spreading over defaults.
 */
export function chatHotelFiltersToFilterState(filters: ChatHotelFilters): HotelFilterState {
  return {
    ...defaultHotelFilterState,
    priceMin: filters.priceMin,
    priceMax: filters.priceMax,
    starRatings: filters.starRatings,
    propertyTypes: filters.propertyTypes,
    refundableOnly: filters.refundableOnly,
    facilities: filters.facilities,
    distanceMax: filters.distanceMax,
    localities: filters.localities,
  };
}

/**
 * Serialize ChatHotelFilters to base64-encoded JSON for the ?f= URL param.
 */
export function serializeChatHotelFiltersToUrl(filters: ChatHotelFilters): string {
  try {
    return btoa(JSON.stringify(filters));
  } catch (error) {
    console.error('Error serializing hotel chat filters:', error);
    return '';
  }
}

/**
 * Deserialize ChatHotelFilters from base64-encoded JSON in the ?f= URL param.
 */
export function deserializeChatHotelFiltersFromUrl(encoded: string): ChatHotelFilters | null {
  try {
    const json = atob(encoded);
    const parsed = JSON.parse(json);
    return {
      priceMin: parsed.priceMin ?? null,
      priceMax: parsed.priceMax ?? null,
      starRatings: Array.isArray(parsed.starRatings) ? parsed.starRatings : [],
      propertyTypes: Array.isArray(parsed.propertyTypes) ? parsed.propertyTypes : [],
      refundableOnly: parsed.refundableOnly ?? false,
      facilities: Array.isArray(parsed.facilities) ? parsed.facilities : [],
      distanceMax: parsed.distanceMax ?? null,
      localities: Array.isArray(parsed.localities) ? parsed.localities : [],
    };
  } catch (error) {
    console.error('Error deserializing hotel chat filters:', error);
    return null;
  }
}

/**
 * Full `/hotels/search?q=…` path for deep-linking and tab chip resume.
 * Fills missing checkout with the night after check-in when only one trip date exists.
 */
export function buildHotelSearchUrlPath(params: HotelSearchFormParams): string | null {
  const dates = normalizeHotelSearchFormParams(params, { fillCheckout: true });
  if (!dates) return null;

  const merged: HotelSearchFormParams = {
    ...params,
    destination: dates.destination,
    checkin: dates.checkin,
    checkout: dates.checkout,
  };
  const encoded = serializeHotelSearchParamsToUrl(merged);
  if (!encoded) return null;
  return `/hotels/search?q=${encodeURIComponent(encoded)}`;
}
