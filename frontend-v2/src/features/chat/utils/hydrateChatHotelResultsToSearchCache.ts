/**
 * Converts chat-pipeline hotel data shapes into the HotelSearchResponse + HotelSearchFormParams
 * shape consumed by HotelSearchPage / setCachedHotelResults.
 *
 * Chat produces ChatHotelInfo[] (snake_case, flat). HotelSearchPage reads HotelItinerary[]
 * (camelCase, structured). This module is the boundary adapter — mirror of
 * hydrateChatFlightResultsToSearchCache.ts for the flight pipeline.
 *
 * Verified against the live `hotel_search_results` payload produced by
 * `_build_hotel_response`: `hotel_id`, `token_id`, `product_id` are non-empty
 * FlightLogic IDs identical to those returned from /api/hotels/search and
 * accepted by /api/hotels/room-rates. `thumbnail_url` is a relative
 * `/imgproxy/...` path served by the backend; `resolveHotelImageUrl` rewrites
 * it to absolute when VITE_API_URL points to a different origin.
 */
import type {
  ChatHotelInfo,
  ExtractedHotelSearchData,
  HotelSearchParams,
} from '@/types/api.helpers';
import type {
  Hotel,
  HotelItinerary,
  HotelSearchFormParams,
  HotelSearchRequest,
  HotelSearchResponse,
  RoomOccupancy,
} from '@/types/hotels';
import { resolveHotelImageUrl } from '@/features/chat/utils/hotelUtils';

function toNumberOrZero(value: unknown): number {
  if (value == null) return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toFiniteNumber(value: unknown): number | undefined {
  if (value == null) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function toCoordinate(value: unknown): number {
  const n = toFiniteNumber(value);
  return n ?? 0;
}

function pickString(...values: unknown[]): string {
  for (const v of values) {
    if (typeof v === 'string' && v.trim() !== '') return v;
    if (typeof v === 'number') return String(v);
  }
  return '';
}

/** Convert a single chat hotel record into a HotelItinerary. */
export function chatHotelToHotelItinerary(
  raw: ChatHotelInfo | Record<string, unknown>
): HotelItinerary {
  const r = raw as Record<string, unknown>;

  const id = pickString(r.hotel_id, r.hotelId);
  const tokenId = pickString(r.token_id, r.tokenId);
  const productId = pickString(r.product_id, r.productId);

  // Validation deferred to chatExtractedToHotelSearchResponse for batched reporting

  const thumb = pickString(
    r.thumbnail_url,
    r.thumbnailUrl,
    r.thumbNailUrl,
    r.image_url,
    r.imageUrl
  );
  const resolvedThumb = thumb ? resolveHotelImageUrl(thumb) ?? undefined : undefined;

  const total = toNumberOrZero(r.total_price ?? r.totalPrice ?? r.total);
  const perNight = toNumberOrZero(r.per_night_price ?? r.perNightPrice);
  const currency = pickString(r.currency) || 'GBP';
  const starRating = toNumberOrZero(r.hotel_rating ?? r.hotelRating ?? r.starRating);
  const latitude = toCoordinate(r.latitude);
  const longitude = toCoordinate(r.longitude);

  const facilities = Array.isArray(r.facilities)
    ? (r.facilities as unknown[]).map((f) => String(f))
    : undefined;

  const originalTotal = toFiniteNumber(r.original_total_fare ?? r.originalTotalFare);
  const platformFee = toFiniteNumber(r.platform_fee_percentage ?? r.platformFeePercentage);
  const fareType = pickString(r.fare_type, r.fareType) || undefined;
  const propertyType = pickString(r.property_type, r.propertyType) || undefined;
  const nearbyDistanceKm = toFiniteNumber(r.nearby_distance_km ?? r.nearbyDistanceKm);

  const itinerary: HotelItinerary = {
    id,
    tokenId,
    productId: productId || undefined,
    name: pickString(r.hotel_name, r.hotelName, r.name) || 'Unknown Hotel',
    address: pickString(r.address),
    city: pickString(r.city),
    country: pickString(r.country),
    starRating,
    latitude,
    longitude,
    imageUrl: resolvedThumb,
    thumbnailUrl: resolvedThumb,
    facilities,
    startingPrice: {
      currency,
      amount: total,
      perNight,
    },
    total,
  };

  if (originalTotal != null) itinerary.originalTotal = originalTotal;
  if (platformFee != null) itinerary.platformFeePercentage = platformFee;
  if (fareType) itinerary.fareType = fareType;
  if (propertyType) itinerary.propertyType = propertyType;
  if (nearbyDistanceKm != null) itinerary.nearbyDistanceKm = nearbyDistanceKm;

  return itinerary;
}

function buildRoomsFromHotelParams(
  roomCount: number,
  totalAdults: number,
  totalChildren: number
): RoomOccupancy[] {
  const perRoomAdults = Math.max(1, Math.floor(totalAdults / roomCount));
  const remainder = Math.max(0, totalAdults - perRoomAdults * roomCount);
  const perRoomChildren = Math.floor(totalChildren / roomCount);
  return Array.from({ length: roomCount }, (_, i) => ({
    roomNo: i + 1,
    adult: i === 0 ? perRoomAdults + remainder : perRoomAdults,
    child: perRoomChildren,
    childAge: Array<number>(perRoomChildren).fill(0),
  }));
}

/** Build HotelSearchFormParams (camelCase persisted form) from chat HotelSearchParams. */
export function chatSearchParamsToFormParams(
  params: HotelSearchParams
): HotelSearchFormParams {
  const destination =
    params.destination_city ??
    params.city_name ??
    params.destination ??
    '';
  const checkin = params.check_in_date ?? params.checkin ?? null;
  const checkout = params.check_out_date ?? params.checkout ?? null;
  const roomCount = Math.max(1, params.rooms ?? 1);
  const totalAdults = Math.max(1, params.adults ?? 2);
  const totalChildren = Math.max(0, params.children ?? 0);

  return {
    destination,
    checkin,
    checkout,
    rooms: buildRoomsFromHotelParams(roomCount, totalAdults, totalChildren),
    nationality: 'US',
  };
}

/** Build a HotelSearchRequest (matches the request envelope HotelSearchPage stores). */
function formParamsToSearchRequest(
  params: HotelSearchFormParams,
  countryName?: string
): HotelSearchRequest {
  return {
    checkin: params.checkin ?? '',
    checkout: params.checkout ?? '',
    cityName: params.destination,
    countryName,
    occupancy: (params.rooms ?? []).map((r) => ({
      roomNo: r.roomNo,
      adult: r.adult ?? 1,
      child: r.child ?? 0,
      childAge:
        (r.child ?? 0) > 0
          ? (r.childAge ?? [0]).slice(0, r.child!)
          : [0],
    })),
    nationality: params.nationality || 'US',
  };
}

/**
 * Adapt a chat ExtractedHotelSearchData into the HotelSearchResponse +
 * HotelSearchFormParams pair consumed by setCachedHotelResults.
 *
 * `curatedHotels` is left undefined — HotelSearchPage renders the flat list
 * gracefully when curated buckets are missing.
 */
export function chatExtractedToHotelSearchResponse(
  extracted: ExtractedHotelSearchData
): { data: HotelSearchResponse; params: HotelSearchFormParams } {
  const params = chatSearchParamsToFormParams(extracted.data.search_params);
  const hotels = extracted.hotels.map(chatHotelToHotelItinerary);

  const invalid = hotels.filter((h) => !h.id || !h.tokenId || !h.productId);
  if (invalid.length > 0) {
    console.warn(
      `[hydrateChatHotelResultsToSearchCache] ${invalid.length} hotel(s) missing id/tokenId/productId — booking will fail`,
      invalid.map((h) => ({ id: h.id, tokenId: h.tokenId, productId: h.productId }))
    );
  }

  const country =
    extracted.data.search_params.country ??
    extracted.data.search_params.country_name ??
    undefined;

  const data: HotelSearchResponse = {
    sessionId: extracted.session_id ?? '',
    hotels: hotels as Hotel[],
    nextToken: undefined,
    totalResults: extracted.hotels.length,
    searchParams: formParamsToSearchRequest(params, country ?? undefined),
  };

  return { data, params };
}
