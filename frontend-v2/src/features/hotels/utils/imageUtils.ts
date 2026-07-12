/**
 * Resolves hotel/room image URLs for use in <img src>.
 *
 * Backend returns relative paths (e.g. "/imgproxy/insecure/rs:fit:400:300/...")
 * that are served by the backend (imgproxy). When the app runs on a different
 * origin (e.g. Vite dev server), relative URLs must be resolved to the backend
 * origin so the browser loads images from the correct host.
 *
 * Mirrors the logic in frontend (chat) HotelResultMessage/utils.js resolveHotelImageUrl.
 */

import type { Hotel, HotelItinerary } from '@/types/hotels';
import { getBackendOriginFromApiBase } from '@/utils/apiAssetUrl';

/**
 * Picks the best available thumbnail URL for a hotel, preferring thumbnailUrl
 * over imageUrl over images[0]. Uses || (not ??) so empty strings are skipped.
 */
export function getHotelThumbnailUrl(hotel: Hotel | HotelItinerary): string | undefined {
  const it = hotel as HotelItinerary;
  return it.thumbnailUrl || hotel.imageUrl || hotel.images?.[0];
}

/**
 * Resolves a hotel or room image URL for use in <img src>.
 * Relative paths (e.g. /imgproxy/...) are resolved to the backend origin.
 *
 * @param url - thumbnail_url, imageUrl, or images[0] from the API
 * @returns Full URL for img src, or null if empty
 */
export function resolveHotelImageUrl(url: string | null | undefined): string | null {
  if (url == null || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('/')) {
    const origin = getBackendOriginFromApiBase();
    return origin ? `${origin}${trimmed}` : trimmed;
  }
  return trimmed;
}
