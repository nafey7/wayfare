import type { AppDispatch } from '@/store';
import { setLastHotelPath } from '@/store/slices/uiSlice';
import {
  setCachedHotelResults,
  clearCachedHotelResults,
  setSearchFormParams,
  setTripType,
  setMultistaySegments,
  setMultistayLegSearchResults,
} from '@/store/slices/hotelBookingSlice';
import {
  extractHotelSearchResults,
  type ExtractedHotelSearchData,
} from '@/types/api.helpers';
import {
  chatExtractedToHotelSearchResponse,
  chatSearchParamsToFormParams,
  chatHotelToHotelItinerary,
} from '@/features/chat/utils/hydrateChatHotelResultsToSearchCache';
import { crossPopulateFlightFromHotelParams } from '@/features/chat/utils/crossPopulateNavBarParams';
import { ROUTES } from '@/features/routing';

/** Persist session, hydrate the hotel search cache, set last path — no navigation. */
export function hydrateHotelSearchResultsFromPayload(
  dispatch: AppDispatch,
  rawData: unknown
): ExtractedHotelSearchData | null {
  const extracted = extractHotelSearchResults(rawData);
  if (!extracted) return null;

  const sid = extracted.session_id?.trim();
  if (sid) {
    try {
      localStorage.setItem('hotelSessionId', sid);
    } catch {
      // Ignore storage errors
    }
  }

  const { data, params } = chatExtractedToHotelSearchResponse(extracted);
  dispatch(setCachedHotelResults({ data, params, trusted: true }));
  dispatch(setSearchFormParams(chatSearchParamsToFormParams(extracted.data.search_params)));
  // Chat hotel results are always single-stay; promote tripType from null so the
  // nav-bar "Stay type" chip shows "Single stay" instead of the placeholder.
  dispatch(setTripType('single'));
  dispatch(setLastHotelPath(ROUTES.HOTELS_SEARCH));
  dispatch(crossPopulateFlightFromHotelParams(extracted.data.search_params));
  return extracted;
}

/**
 * For history messages: pre-fill the hotel search form and clear stale cached results
 * so HotelSearchPage triggers a fresh API call instead of rendering old data.
 * Does NOT store cached results (unlike hydrateHotelSearchResultsFromPayload).
 */
export function hydrateHotelSearchParamsForFreshSearch(
  dispatch: AppDispatch,
  rawData: unknown
): boolean {
  const extracted = extractHotelSearchResults(rawData);
  if (!extracted) return false;
  dispatch(clearCachedHotelResults());
  dispatch(setSearchFormParams(chatSearchParamsToFormParams(extracted.data.search_params)));
  dispatch(setTripType('single'));
  dispatch(setLastHotelPath(ROUTES.HOTELS_SEARCH));
  dispatch(crossPopulateFlightFromHotelParams(extracted.data.search_params));
  return true;
}

/**
 * Hydrate multi-stay hotel results from a ``multistay_hotel_search_results`` chain payload.
 * Sets trip type to 'multi-stay', populates segments and per-leg results in Redux.
 */
export function hydrateMultistayHotelSearchResultsFromPayload(
  dispatch: AppDispatch,
  rawData: unknown
): boolean {
  if (!rawData || typeof rawData !== 'object') return false;
  const root = rawData as Record<string, unknown>;
  const inner = (root.data ?? root) as Record<string, unknown>;
  const legsRaw = inner.multistay_legs as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(legsRaw) || legsRaw.length < 1) return false;

  dispatch(setTripType('multi-stay'));

  const sp = (inner.search_params ?? {}) as Record<string, unknown>;
  const adults = (sp.adults as number | undefined) ?? 1;
  const children = (sp.children as number | undefined) ?? 0;
  const rooms = (sp.rooms as number | undefined) ?? 1;
  const childAge = children > 0 ? Array.from({ length: children }, () => 5) : [0];
  const roomOccupancies = Array.from({ length: rooms }, (_, i) => ({
    roomNo: i + 1,
    adult: adults,
    child: children,
    childAge,
  }));

  const segments = legsRaw.map((leg) => ({
    destination: String(leg.destination ?? ''),
    checkin: (leg.check_in_date as string | null | undefined) ?? null,
    checkout: (leg.check_out_date as string | null | undefined) ?? null,
    rooms: roomOccupancies,
  }));
  dispatch(setMultistaySegments(segments));

  for (let i = 0; i < legsRaw.length; i++) {
    const leg = legsRaw[i]!;
    const sessionId = String(leg.session_id ?? '');
    const rawHotels = Array.isArray(leg.hotels) ? (leg.hotels as unknown[]) : [];
    // Map raw snake_case backend objects → camelCase HotelItinerary (resolves thumbnailUrl etc.)
    const hotels = rawHotels.map((h) => chatHotelToHotelItinerary(h as Record<string, unknown>)).filter(Boolean);
    dispatch(setMultistayLegSearchResults({ legIndex: i, sessionId, hotels }));
  }

  dispatch(setLastHotelPath(ROUTES.HOTELS_SEARCH));
  return true;
}
