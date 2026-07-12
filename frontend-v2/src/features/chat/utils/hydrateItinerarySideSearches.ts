/**
 * Pre-populate flight + hotel results from an itinerary response (#1038).
 *
 * The personalised-itinerary backend runs flight + hotel searches in parallel
 * with ``generate_itinerary`` and ships the full results alongside session IDs
 * and search params. This module dispatches the same Redux actions that the
 * chat hydrators dispatch — so when the user clicks the Flights / Stays tabs
 * from the itinerary page, the cached results render instantly without a
 * duplicate FlightLogic call.
 *
 * Graceful no-op when ``data.flights`` / ``data.hotels`` are empty.
 */
import type { AppDispatch } from '@/store';
import { setLastFlightPath, setLastHotelPath } from '@/store/slices/uiSlice';
import { setCachedFlightResults, setSearchFormParams as setFlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import {
  setCachedHotelResults,
  setSearchFormParams as setHotelSearchFormParams,
  setTripType as setHotelTripType,
} from '@/store/slices/hotelBookingSlice';
import { ROUTES } from '@/features/routing';
import { extractedToSearchResponse } from '@/features/chat/utils/hydrateChatFlightResultsToSearchCache';
import { chatExtractedToHotelSearchResponse } from '@/features/chat/utils/hydrateChatHotelResultsToSearchCache';
import type {
  ExtractedFlightSearchData,
  ExtractedHotelSearchData,
  FlightInfo,
  FlightSearchParams,
  HotelSearchParams,
} from '@/types/api.helpers';

function isNonEmptyArray<T>(v: unknown): v is T[] {
  return Array.isArray(v) && v.length > 0;
}

function buildFlightSummary(flights: FlightInfo[]): {
  total_flights: number;
  direct_count: number;
  price_range: { min: number; max: number; currency: string };
} {
  const prices = flights
    .map((f) => Number(f.price))
    .filter((n) => Number.isFinite(n) && n > 0);
  const directCount = flights.filter((f) => f.stops === 0).length;
  const currency =
    flights.find((f) => typeof f.currency === 'string')?.currency ?? 'USD';
  return {
    total_flights: flights.length,
    direct_count: directCount,
    price_range: {
      min: prices.length ? Math.min(...prices) : 0,
      max: prices.length ? Math.max(...prices) : 0,
      currency,
    },
  };
}

function buildHotelSummary(
  hotels: Record<string, unknown>[],
  searchParams: HotelSearchParams | undefined
): {
  total_found: number;
  nights: number;
  price_range: { min: number; max: number; currency: string };
} {
  const perNight = hotels
    .map((h) => Number(h.per_night_price ?? h.total_price))
    .filter((n) => Number.isFinite(n) && n > 0);
  // Walk the whole list looking for a currency string — `hotels[0].currency`
  // alone would silently drop the field for the whole summary if a partial
  // payload omits it on just the first record (matches the resilience of the
  // price extraction above).
  const currency =
    hotels
      .map((h) => h.currency)
      .find((c): c is string => typeof c === 'string' && c.length > 0) ?? 'USD';

  // Compute nights from checkin/checkout when present so the FE renders
  // "N nights" correctly. Falls back to 1.
  let nights = 1;
  const checkin = searchParams?.check_in_date ?? searchParams?.checkin;
  const checkout = searchParams?.check_out_date ?? searchParams?.checkout;
  if (checkin && checkout) {
    const start = new Date(checkin).getTime();
    const end = new Date(checkout).getTime();
    if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
      nights = Math.max(1, Math.round((end - start) / (24 * 60 * 60 * 1000)));
    }
  }

  return {
    total_found: hotels.length,
    nights,
    price_range: {
      min: perNight.length ? Math.min(...perNight) : 0,
      max: perNight.length ? Math.max(...perNight) : 0,
      currency,
    },
  };
}

/**
 * If ``data.flights`` is non-empty, hydrate the flight recommendations slice
 * so navigating to /flights/recommendations renders instantly with no
 * FlightLogic call.
 */
export function hydrateFlightSideSearchFromItinerary(
  dispatch: AppDispatch,
  data: Record<string, unknown>
): void {
  const flights = data.flights;
  if (!isNonEmptyArray<FlightInfo>(flights)) return;

  const sessionId = (data.flight_session_id as string | null | undefined) ?? '';
  const searchParams = (data.flight_search_params as FlightSearchParams | null | undefined) ??
    (data.search_params as FlightSearchParams | undefined) ??
    ({} as FlightSearchParams);

  const extracted: ExtractedFlightSearchData = {
    data: {
      search_params: searchParams,
      summary: buildFlightSummary(flights),
    },
    flights,
    session_id: sessionId,
  };

  if (sessionId) {
    try {
      localStorage.setItem('sessionId', sessionId);
    } catch {
      // Ignore storage errors
    }
  }
  const { data: searchResponseData, params } = extractedToSearchResponse(extracted);
  dispatch(setCachedFlightResults({ data: searchResponseData, params, trusted: true }));
  // Mirror flight_search_results strategy: set searchFormParams to the same params
  // used for cachedFlightResultsParams so areFlightParamsEqual passes on FlightSearchPage mount.
  dispatch(setFlightSearchFormParams(params));
  dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
}

/**
 * Mirror for hotels — hydrate the in-memory hotel results cache so the Stays
 * tab on the itinerary page renders instantly with no FlightLogic call.
 */
export function hydrateHotelSideSearchFromItinerary(
  dispatch: AppDispatch,
  data: Record<string, unknown>
): void {
  const hotels = data.hotels;
  if (!isNonEmptyArray<Record<string, unknown>>(hotels)) return;

  const sessionId = (data.hotel_session_id as string | null | undefined) ?? '';
  const searchParams = (data.hotel_search_params as HotelSearchParams | null | undefined) ??
    ({} as HotelSearchParams);

  const extracted: ExtractedHotelSearchData = {
    data: {
      search_params: searchParams,
      summary: buildHotelSummary(hotels, searchParams),
    },
    hotels,
    session_id: sessionId,
  };

  if (sessionId) {
    try {
      localStorage.setItem('hotelSessionId', sessionId);
    } catch {
      // Ignore storage errors
    }
  }
  const { data: searchResponseData, params } = chatExtractedToHotelSearchResponse(extracted);
  dispatch(setCachedHotelResults({ data: searchResponseData, params, trusted: true }));
  // Mirror flight side: set searchFormParams to the same params used for
  // cachedHotelResultsParams so areHotelParamsEqual passes on HotelSearchPage mount.
  dispatch(setHotelSearchFormParams(params));
  // Itinerary side-searches are always single-stay; promote tripType so the
  // nav-bar "Stay type" chip shows "Single stay" instead of the placeholder.
  dispatch(setHotelTripType('single'));
  dispatch(setLastHotelPath(ROUTES.HOTELS_SEARCH));
}
