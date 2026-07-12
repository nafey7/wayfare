import type { NavigateFunction } from 'react-router-dom';

import type { AppDispatch } from '@/store';
import {
  setTripMeta,
  setLastItineraryPath,
  setLastItineraryState,
} from '@/store/slices/uiSlice';
import { clearCachedFlightResults } from '@/store/slices/flightBookingSlice';
import { clearCachedHotelResults } from '@/store/slices/hotelBookingSlice';
import {
  hydrateFlightSideSearchFromItinerary,
  hydrateHotelSideSearchFromItinerary,
} from '@/features/chat/utils/hydrateItinerarySideSearches';
import { itineraryView } from '@/features/routing';
import type { ItineraryNavigationState } from '@/features/itinerary/types';
import { parseDestinationLocation } from '@/features/itinerary/utils/destinationLocation';
import { itinerariesApi } from '@/api/itinerariesApi';
import { getStructuredItinerary } from '@/features/itinerary/utils/structuredItinerary';

function buildTripMeta(extraData: Record<string, unknown>) {
  const destination_location = parseDestinationLocation(
    extraData.destination_location as { latitude?: unknown; longitude?: unknown } | undefined
  );
  const origin_location = parseDestinationLocation(
    extraData.origin_location as { latitude?: unknown; longitude?: unknown } | undefined
  );
  // Prefer user_destination (e.g. "Walt Disney World") for display title,
  // fall back to destination (resolved city e.g. "Orlando").
  const displayDestination =
    (extraData.user_destination as string | undefined) ??
    (extraData.destination as string | undefined);
  return {
    origin: extraData.origin as string | undefined,
    destination: displayDestination,
    departure_date: extraData.departure_date as string | undefined,
    return_date: extraData.return_date as string | undefined,
    adults: extraData.adults as number | undefined,
    children: extraData.children as number | undefined,
    infants: extraData.infants as number | undefined,
    trip_type: extraData.trip_type as string | undefined,
    destination_location,
    origin_location,
  };
}

export interface CommitItineraryResult {
  targetPath: string;
  /** Present when navigating to unsaved itinerary — pass to `navigate(..., { state })`. */
  locationState?: ItineraryNavigationState;
}

/**
 * Writes itinerary rich-result data to Redux (path, trip meta, structured itinerary) without
 * navigating — mirrors "View itinerary" so Tab B / post-registration routes can render content
 * without `location.state`. Also used by `applySuccessfulChatResponse` (same as flights/hotels).
 *
 * @param routePrefix  `''` for authenticated routes, `'/public/chat'` for public chat routes.
 * @param chatId       Active chatId to key the per-chat itinerary state (null → '__anon__').
 */
export function commitItineraryRichResultToUiState(
  dispatch: AppDispatch,
  extraData: Record<string, unknown> | undefined,
  routePrefix = '',
  chatId: string | null = null,
  options: { skipFlightHydration?: boolean; skipHotelHydration?: boolean } = {}
): CommitItineraryResult | undefined {
  if (!extraData) return undefined;
  const resolvedChatId = chatId ?? '__anon__';
  const savedItineraryId = extraData.saved_itinerary_id as string | undefined;
  const destination = (extraData.destination as string | undefined) ?? undefined;
  const structuredItinerary = getStructuredItinerary(extraData);
  const tripMeta = buildTripMeta(extraData);

  // Re-hydrate the flight/hotel caches from THIS itinerary's payload so that
  // clicking View Itinerary on an older chat message doesn't leave stale
  // results from the most recent live chat in Redux. If the payload carries
  // `flights` / `hotels`, the side-search hydrator stores them with
  // `trusted: true`. If not, we clear the cache so the destination page
  // refetches when the user opens Flights/Hotels. See docs/CHAT_NAV_BAR_SYNC.md.
  const hasFlights =
    Array.isArray(extraData.flights) && (extraData.flights as unknown[]).length > 0;
  const hasHotels =
    Array.isArray(extraData.hotels) && (extraData.hotels as unknown[]).length > 0;

  if (options.skipFlightHydration) {
    // Multi-city chain response already hydrated flight results — don't overwrite with flat list.
  } else if (hasFlights) {
    hydrateFlightSideSearchFromItinerary(dispatch, extraData);
  } else {
    dispatch(clearCachedFlightResults());
  }

  if (options.skipHotelHydration) {
    // Multi-stay chain response already hydrated hotel results — don't overwrite with flat list.
  } else if (hasHotels) {
    hydrateHotelSideSearchFromItinerary(dispatch, extraData);
  } else {
    dispatch(clearCachedHotelResults());
  }

  if (import.meta.env.DEV) {
    console.log('[ChatNavSync] commitItineraryRichResultToUiState', {
      hasFlights,
      hasHotels,
      savedItineraryId,
      destination,
    });
  }

  dispatch(setTripMeta({ chatId: resolvedChatId, meta: tripMeta }));
  if (savedItineraryId) {
    // Invalidate RTK Query cache so the itinerary page refetches the updated
    // document (e.g. after a modification regenerates the itinerary in-place).
    dispatch(
      itinerariesApi.util.invalidateTags([
        { type: 'SavedItineraries', id: savedItineraryId },
      ])
    );
    const targetPath = `${routePrefix}${itineraryView(savedItineraryId)}`;
    dispatch(setLastItineraryPath({ chatId: resolvedChatId, path: targetPath }));
    // Always pass the structured itinerary from the response so the page can
    // show the latest version immediately — even when the user is already on
    // the same /itinerary/:id URL (e.g. after a modification regeneration).
    // Without this, RTK Query may serve stale cached data for the same ID.
    const locationState: ItineraryNavigationState = {
      structuredItinerary: structuredItinerary ?? {},
      tripMeta,
      savedItineraryId,
    };
    dispatch(setLastItineraryState({ chatId: resolvedChatId, state: locationState }));
    return { targetPath, locationState };
  }
  const searchParams = new URLSearchParams();
  if (destination) searchParams.set('destination', destination);
  const query = searchParams.toString();
  const basePath = `${routePrefix}/itinerary`;
  const targetPath = query ? `${basePath}?${query}` : basePath;
  dispatch(setLastItineraryPath({ chatId: resolvedChatId, path: targetPath }));
  const locationState: ItineraryNavigationState = {
    structuredItinerary: structuredItinerary ?? {},
    tripMeta,
  };
  dispatch(setLastItineraryState({ chatId: resolvedChatId, state: locationState }));
  return { targetPath, locationState };
}

/**
 * Same navigation as "View itinerary" in chat — used by the button and `/chat` auto-redirect.
 * @param routePrefix  `''` for authenticated routes, `'/public/chat'` for public chat routes.
 * @param chatId       Active chatId to key the per-chat itinerary state (null → '__anon__').
 */
export function navigateItineraryFromChatExtraData(
  dispatch: AppDispatch,
  navigate: NavigateFunction,
  extraData: Record<string, unknown> | undefined,
  routePrefix = '',
  chatId: string | null = null,
  options: { skipFlightHydration?: boolean; skipHotelHydration?: boolean } = {}
): void {
  const committed = commitItineraryRichResultToUiState(dispatch, extraData, routePrefix, chatId, options);
  if (!committed) return;
  if (committed.locationState) {
    navigate(committed.targetPath, { state: committed.locationState });
  } else {
    navigate(committed.targetPath);
  }
}
