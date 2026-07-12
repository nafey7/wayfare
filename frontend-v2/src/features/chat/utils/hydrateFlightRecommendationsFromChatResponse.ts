import type { AppDispatch } from '@/store';
import { setLastFlightPath, setTripMeta } from '@/store/slices/uiSlice';
import {
  setCachedFlightResults,
  clearCachedFlightResults,
  setSearchFormParams,
  setDate as setFlightDate,
  setReturnDate as setFlightReturnDate,
  setTripType as setFlightTripType,
} from '@/store/slices/flightBookingSlice';
import {
  extractFlightSearchResults,
  extractFlightDateRangeResults,
  dateRangeToFlightSearchData,
  type ExtractedDateRangeFlightData,
  type ExtractedFlightSearchData,
  type FlightSearchParams,
} from '@/types/api.helpers';
import { extractMulticityFlightSearchResults } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import type { MulticityChatPayloadNormalized } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import { mapCabinClass } from '@/features/chat/utils/chatSearchParamsToUI';
import {
  extractedToSearchResponse,
  multicityToSearchResponse,
  searchParamsToFormParams,
} from '@/features/chat/utils/hydrateChatFlightResultsToSearchCache';
import {
  crossPopulateHotelFromFlightParams,
  crossPopulateHotelFromTripBounds,
} from '@/features/chat/utils/crossPopulateNavBarParams';
import { ROUTES } from '@/features/routing';

function dispatchSingleFlightFormAndChips(
  dispatch: AppDispatch,
  params: FlightSearchParams
) {
  dispatch(setSearchFormParams(searchParamsToFormParams(params)));
}

function persistMulticitySessionId(normalized: MulticityChatPayloadNormalized) {
  const sid =
    normalized.legs.find((l) => l.sessionId?.trim())?.sessionId ??
    normalized.legs[0]?.sessionId;
  if (sid) {
    try {
      localStorage.setItem('sessionId', sid);
    } catch {
      // Ignore storage errors
    }
  }
}

function dispatchMulticityTripFormAndChips(
  dispatch: AppDispatch,
  normalized: MulticityChatPayloadNormalized,
  chatId: string | null = null
) {
  const legs = normalized.legs;
  const trip = normalized.searchParams;
  const passengers = trip.passengers ?? { adults: 1, children: 0, infants: 0 };
  dispatch(
    setSearchFormParams({
      tripType: 'multi-city',
      from: legs[0]!.origin,
      to: legs[0]!.destination,
      date: legs[0]!.departureDate,
      returnDate: null,
      travellers: {
        adults: passengers.adults,
        children: passengers.children,
        infants: passengers.infants,
        cabinClass: mapCabinClass(trip.cabin_class),
      },
      segments: legs.map((l) => ({
        from: l.origin,
        to: l.destination,
        date: l.departureDate,
      })),
    })
  );
  dispatch(
    setTripMeta({
      chatId: chatId ?? '__anon__',
      meta: {
        origin: legs[0]!.origin,
        destination: legs[legs.length - 1]!.destination,
        departure_date: legs[0]!.departureDate,
        return_date: undefined,
        adults: passengers.adults,
        children: passengers.children,
        infants: passengers.infants,
        trip_type: 'multi_city',
      },
    })
  );
}

/** Persist session, Redux search cache, and last path — no navigation. */
export function hydrateFlightSearchResultsFromPayload(
  dispatch: AppDispatch,
  rawData: unknown
): ExtractedFlightSearchData | null {
  const extracted = extractFlightSearchResults(rawData);
  if (!extracted) return null;
  const sessionId =
    extracted.session_id ?? (rawData as { sessionId?: string })?.sessionId;
  if (sessionId) {
    try {
      localStorage.setItem('sessionId', sessionId);
    } catch {
      // Ignore storage errors
    }
  }
  const { data, params } = extractedToSearchResponse(extracted);
  dispatch(setCachedFlightResults({ data, params, trusted: true }));
  dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
  dispatchSingleFlightFormAndChips(dispatch, extracted.data.search_params);
  dispatch(crossPopulateHotelFromFlightParams(extracted.data.search_params));
  // DEV-only rollout telemetry for the chat→FlightSearchPage cache-hit handoff.
  // TODO(#1060): remove these `[FlightChat] N/3` logs (1/3 here, 2/3 in FlightResultMessage,
  // 3/3 in FlightSearchPage) once cache-hit behavior has stabilised in staging/production.
  if (import.meta.env.DEV) {
    console.groupCollapsed('[FlightChat] 1/3 Redux hydrated from chat response');
    console.log('flights stored:', data.fareItineraries?.length ?? 0);
    console.log('cached params (date format):', params.date);
    console.log('form params (date format):', extracted.data.search_params.departure_date);
    console.log('sessionId:', sessionId);
    console.groupEnd();
  }
  return extracted;
}

export function hydrateMulticityFlightSearchResultsFromPayload(
  dispatch: AppDispatch,
  rawData: unknown,
  chatId: string | null = null
): MulticityChatPayloadNormalized | null {
  const normalized = extractMulticityFlightSearchResults(rawData);
  if (!normalized) return null;
  persistMulticitySessionId(normalized);
  const { data, params } = multicityToSearchResponse(normalized);
  dispatch(setCachedFlightResults({ data, params, trusted: true }));
  dispatchMulticityTripFormAndChips(dispatch, normalized, chatId);
  dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
  // Multicity: use first leg origin date as check-in and the final destination
  // (last leg) for the hotel chip. Checkout is left to nextDayIso fallback.
  const firstLeg = normalized.legs[0];
  const lastLeg = normalized.legs[normalized.legs.length - 1];
  if (firstLeg && lastLeg) {
    const passengers = normalized.searchParams.passengers ?? { adults: 1, children: 0, infants: 0 };
    dispatch(crossPopulateHotelFromTripBounds({
      destination: lastLeg.destination,
      checkin: firstLeg.departureDate,
      checkout: null,
      adults: passengers.adults,
      children: passengers.children,
    }));
  }
  return normalized;
}

/**
 * Syncs date-range chips for any valid payload; hydrates recommendations Redux when a curated slice exists.
 */
export function hydrateFlightDateRangeFromPayload(
  dispatch: AppDispatch,
  rawData: unknown
): {
  extracted: ExtractedFlightSearchData | null;
  dateRange: ExtractedDateRangeFlightData;
} | null {
  const dateRange = extractFlightDateRangeResults(rawData);
  if (!dateRange) return null;

  dispatch(setFlightDate(dateRange.searched_from || null));
  dispatch(setFlightReturnDate(dateRange.searched_to || null));
  dispatch(setFlightTripType('one-way'));

  const extracted = dateRangeToFlightSearchData(dateRange);
  if (extracted) {
    if (extracted.session_id) {
      try {
        localStorage.setItem('sessionId', extracted.session_id);
      } catch {
        // Ignore storage errors
      }
    }
    const { data, params } = extractedToSearchResponse(extracted);
    dispatch(setCachedFlightResults({ data, params, trusted: true }));
    dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
    dispatch(crossPopulateHotelFromFlightParams(extracted.data.search_params));
  }
  return { extracted, dateRange };
}

/**
 * For history messages: pre-fill the search form and clear stale cached results
 * so FlightSearchPage triggers a fresh API call instead of rendering old data.
 * Does NOT store cached results (unlike hydrateFlightSearchResultsFromPayload).
 */
export function hydrateFlightSearchParamsForFreshSearch(
  dispatch: AppDispatch,
  rawData: unknown
): boolean {
  const extracted = extractFlightSearchResults(rawData);
  if (!extracted) return false;
  dispatch(clearCachedFlightResults());
  dispatchSingleFlightFormAndChips(dispatch, extracted.data.search_params);
  dispatch(crossPopulateHotelFromFlightParams(extracted.data.search_params));
  dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
  return true;
}

/**
 * For history multicity messages: pre-fill the search form and clear stale cache.
 */
export function hydrateMulticityFlightSearchParamsForFreshSearch(
  dispatch: AppDispatch,
  rawData: unknown
): boolean {
  const normalized = extractMulticityFlightSearchResults(rawData);
  if (!normalized) return false;
  dispatch(clearCachedFlightResults());
  dispatchMulticityTripFormAndChips(dispatch, normalized);
  const firstLeg = normalized.legs[0];
  const lastLeg = normalized.legs[normalized.legs.length - 1];
  if (firstLeg && lastLeg) {
    const passengers = normalized.searchParams.passengers ?? { adults: 1, children: 0, infants: 0 };
    dispatch(crossPopulateHotelFromTripBounds({
      destination: lastLeg.destination,
      checkin: firstLeg.departureDate,
      checkout: null,
      adults: passengers.adults,
      children: passengers.children,
    }));
  }
  dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
  return true;
}
