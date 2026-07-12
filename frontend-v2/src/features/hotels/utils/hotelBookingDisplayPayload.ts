import type { HotelItinerary } from '@/types/hotels';

/** Optional fields POST /hotels/book accepts for booking_events (profile list). */
export interface HotelBookingDisplayPayload {
  hotelImageUrl?: string;
  hotelName?: string;
  hotelCity?: string;
  /** Street/property address; persisted on booking_events for confirmation UI. */
  hotelAddress?: string;
  /** WGS84; persisted for trip-details / confirmation “show on map”. */
  hotelLatitude?: number;
  hotelLongitude?: number;
}

/**
 * Build payload from the in-memory selected hotel (Redux / session restore).
 * Sent on book so Mongo booking_events get hotel_name, hotel_city, hotel_address, hotel_image_url,
 * and coordinates when the internal session has no selected_hotel blob (common SPA path).
 */
export function buildHotelBookingDisplayPayload(
  hotel: HotelItinerary | null
): HotelBookingDisplayPayload | undefined {
  if (!hotel) return undefined;

  const rawName =
    hotel.name?.trim() ||
    (hotel as { hotelName?: string }).hotelName?.trim() ||
    '';
  const rawCity = hotel.city?.trim() || '';
  const rawAddress = hotel.address?.trim() || '';
  const firstImage = hotel.images?.map((u) => u?.trim()).find(Boolean);
  const rawUrl =
    hotel.thumbnailUrl?.trim() ||
    hotel.imageUrl?.trim() ||
    firstImage ||
    '';
  const lat =
    typeof hotel.latitude === 'number' && Number.isFinite(hotel.latitude)
      ? hotel.latitude
      : undefined;
  const lng =
    typeof hotel.longitude === 'number' && Number.isFinite(hotel.longitude)
      ? hotel.longitude
      : undefined;

  const out: HotelBookingDisplayPayload = {};
  if (rawUrl) out.hotelImageUrl = rawUrl;
  if (rawName) out.hotelName = rawName;
  if (rawCity) out.hotelCity = rawCity;
  if (rawAddress) out.hotelAddress = rawAddress;
  if (lat !== undefined) out.hotelLatitude = lat;
  if (lng !== undefined) out.hotelLongitude = lng;

  return Object.keys(out).length > 0 ? out : undefined;
}
