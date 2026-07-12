import { useState, useMemo, useEffect, useCallback, useRef, type ComponentProps } from 'react';
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Container,
  Group,
  Loader,
  Select,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { MapComponent } from '@/features/itinerary/components';
import { FLIGHTS_CONTENT_SPLIT } from '@/components/layout/layoutConstants';
import {
  getFlightSearchPageMapProps,
  getItineraryMapOverrideFromTripMeta,
  type FlightRecommendationsMapCoordinateOverrides,
} from '../utils/flightMapLocation';
import { selectActiveSavedItineraryIdForBooking } from '@/store/slices/uiSlice';
import { useGetItineraryQuery } from '@/api/itinerariesApi';
import { useMediaQuery } from '@mantine/hooks';
import { Filter, SlidersHorizontal } from 'lucide-react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import {
  FLIGHT_DETAILS_MULTICITY_SEGMENT,
  ROUTES,
  flightDetailsPath,
  isPublicChatRoute,
} from '@/features/routing/constants';
import { getContentRoutePrefix } from '@/features/routing';
import { usePublicChatConversionGate } from '@/features/chat/hooks/usePublicChatConversionGate';
import { showErrorToast, showErrorToastFromError, showSuccessToast } from '@/utils/toast';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { FlightSearchBarV2 } from '../components/FlightSearchBarV2';
import type { FlightSearchParamsUI } from '@/types/flights';
import { FlightResults } from '../components/FlightResults';
import { FlightFiltersDialog } from '../components/FlightFiltersDialog';
import { countActiveFilters } from '../utils/flightFilters';
import { MulticitySelectionBottomBar } from '../components/MulticitySelectionBottomBar';
import { MulticityLegPillTabs } from '../components/MulticityLegPillTabs';
import {
  useLazySearchFlightsQuery,
  useRevalidateFlightMutation,
  useLazyResolveAirportQuery,
} from '@/api/flightsApi';
import { useGetProfileQuery } from '@/api/usersApi';
import { formatDateForAPI, isRoundTripSearchMissingReturnDate } from '../utils/flightUtils';
import type {
  FlightSearchRequestBackend,
  FlightSearchResponseCamel,
  FlightRevalidateResponseCamel,
} from '@/types/flightBackend';
import { mapFareItinerariesToFlightCards } from '../utils/mapFareItinerariesToFlightCards';
import { parseMulticityFlightId } from '../utils/multicityFlightIds';
import {
  setSearchFormParams,
  selectSearchFormParams,
  selectSearchTriggerFromChips,
  resetSearchTriggerFromChips,
  setFlightFilters,
  selectFlightFilters,
  setPassengers,
  clearSavedPassengerIds,
  setMulticityLegSelection,
  clearMulticityLegSelections,
  selectMulticitySelectedLegs,
  setCachedFlightResults,
  clearCachedFlightResults,
  selectCachedFlightResults,
  selectCachedFlightResultsTrusted,
  selectFlightResultsCacheTimestamp,
  selectFlightResultsCachedParams,
} from '@/store/slices/flightBookingSlice';
import { isSearchCacheExpired, areFlightParamsEqual } from '@/utils/searchResultsCache';
import { defaultFlightFilterState } from '../utils/flightFilters';
import {
  serializeSearchParamsToUrl,
  deserializeSearchParamsFromUrl,
  deserializeChatFiltersFromUrl,
  convertUIToFormParams,
  convertFormParamsToUI,
} from '../utils/urlParams';
import { chatFiltersToFilterState } from '@/features/chat/utils/chatSearchParamsToUI';
import { useResolvedSearchParams } from '../hooks/useResolvedSearchParams';
import { filterFlights, type FilterableFlight } from '../utils/flightFilters';
import {
  sortFlights,
  FLIGHT_SORT_MENU_ITEMS,
  type FlightSortOption,
} from '../utils/flightSort';
import { sortFlightsByPreference } from '../utils/flightPreferenceScore';
import { resolveToIata } from '../utils/resolveAirport';
import { MobileSortToolbar } from '@/components/layout/MobileSortToolbar';
import { validateDatesNotInPast } from '@/utils/dateValidation';

/**
 * Flight Search Page
 * Displays search bar initially, then shows results and filters after search
 */
export function FlightSearchPage() {
  const isLgDown = useMediaQuery('(max-width: 1199px)') ?? false;
  const [filtersDialogOpen, setFiltersDialogOpen] = useState(false);
  const [flightSortBy, setFlightSortBy] = useState<FlightSortOption>('preference-match');
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { ensureAuthenticated } = usePublicChatConversionGate();
  const onPublicRoute = isPublicChatRoute(location.pathname);
  const handleChangePreferences = useCallback(() => {
    if (onPublicRoute) {
      navigate(ROUTES.ONBOARDING);
      return;
    }
    navigate('/profile?section=flight');
  }, [navigate, onPublicRoute]);
  const routePrefix = getContentRoutePrefix(location.pathname);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectingFlightId, setSelectingFlightId] = useState<string | null>(null);
  const lastRestoredFilters = useRef<string>('');
  const prevFlightChipTrigger = useRef(0);
  const autoSearchAttemptedRef = useRef(false);
  // Prevents URL-change effect from double-firing when handleSearch already triggered the API call.
  const skipNextUrlEffectRef = useRef(false);
  const [revalidateFlight] = useRevalidateFlightMutation();
  const [triggerSearch, { data: lazyData, isLoading, error }] = useLazySearchFlightsQuery();

  // Redux state
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const searchTriggerFromChips = useAppSelector(selectSearchTriggerFromChips);
  const filterState = useAppSelector(selectFlightFilters);
  const multicitySelectedLegs = useAppSelector(selectMulticitySelectedLegs);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // Redux search results cache
  const cachedFlightResults = useAppSelector(selectCachedFlightResults);
  const cachedFlightResultsTrusted = useAppSelector(selectCachedFlightResultsTrusted);
  const cacheTimestamp = useAppSelector(selectFlightResultsCacheTimestamp);
  const cachedFlightResultsParams = useAppSelector(selectFlightResultsCachedParams);

  // User flight preferences for "Recommended for you" sort
  const { data: profile } = useGetProfileQuery(undefined, { skip: !isAuthenticated });
  const flightsPrefs = profile?.preferences?.flights ?? null;

  const [resolveAirport] = useLazyResolveAirportQuery();
  const [activeLegTab, setActiveLegTab] = useState(0);

  /**
   * Resolve origin/destination to IATA codes (mirrors flight-booker).
   * Ensures search API always receives iata_code even when user entered city name.
   */
  const resolveOriginDestination = useCallback(
    async (
      from: string,
      to: string,
      fromAirport?: { iata?: string; isCityOption?: boolean } | null,
      toAirport?: { iata?: string; isCityOption?: boolean } | null
    ): Promise<{
      originIata: string;
      destIata: string;
      cityWiseOrigin: boolean;
      cityWiseDest: boolean;
      originCoords: { latitude: number | null; longitude: number | null } | null;
      destCoords: { latitude: number | null; longitude: number | null } | null;
    }> => {
      const orig = resolveToIata(from, fromAirport ?? undefined);
      const dest = resolveToIata(to, toAirport ?? undefined);

      let originIata = orig.iata;
      let destIata = dest.iata;
      let cityWiseOrigin = orig.cityWise;
      let cityWiseDest = dest.cityWise;

      const [originRes, destRes] = await Promise.all([
        orig.needsResolve ? resolveAirport(from.trim()).unwrap() : null,
        dest.needsResolve ? resolveAirport(to.trim()).unwrap() : null,
      ]);

      if (originRes) {
        const code = originRes.iataCode?.trim().toUpperCase() ?? '';
        originIata = code.length === 3 ? code : '';
        cityWiseOrigin = true;
      }
      if (destRes) {
        const code = destRes.iataCode?.trim().toUpperCase() ?? '';
        destIata = code.length === 3 ? code : '';
        cityWiseDest = true;
      }

      return {
        originIata,
        destIata,
        cityWiseOrigin,
        cityWiseDest,
        originCoords: originRes
          ? { latitude: originRes.latitude ?? null, longitude: originRes.longitude ?? null }
          : null,
        destCoords: destRes
          ? { latitude: destRes.latitude ?? null, longitude: destRes.longitude ?? null }
          : null,
      };
    },
    [resolveAirport]
  );

  /**
   * Build search request from UI params (shared logic).
   * Uses resolved IATA codes so API always receives iata_code (mirrors flight-booker).
   * When resolved is missing (URL restore), derives from params via resolveToIata.
   */
  const buildSearchRequest = useCallback(
    (
      params: FlightSearchParamsUI,
      resolved?: {
        originIata: string;
        destIata: string;
        cityWiseOrigin: boolean;
        cityWiseDest: boolean;
      },
      multicityResolvedLegs?: Array<{
        originIata: string;
        destIata: string;
        cityWiseOrigin: boolean;
        cityWiseDest: boolean;
      }>
    ): FlightSearchRequestBackend => {
      const cabinClassMap: Record<string, string> = {
        Economy: 'Economy',
        'Premium Economy': 'Premium Economy',
        Business: 'Business',
        First: 'First',
      };
      const cabinClass =
        (params.travellers.cabinClass && cabinClassMap[params.travellers.cabinClass]) || 'Economy';

      const baseReturn = (
        journeyType: 'OneWay' | 'Return' | 'Circle',
        originDestinationInfo: Array<{
          departure_date: string;
          origin_airport: { iata_code: string };
          destination_airport: { iata_code: string };
        }>,
        cityWiseOrigin: boolean,
        cityWiseDest: boolean
      ): FlightSearchRequestBackend => ({
        journey_type: journeyType,
        origin_destination_info: originDestinationInfo,
        adults: params.travellers.adults ?? 1,
        children: params.travellers.children ?? 0,
        infants: params.travellers.infants ?? 0,
        cabin_class: cabinClass,
        direct_flight: 0,
        city_wise_search_origin: cityWiseOrigin,
        city_wise_search_destination: cityWiseDest,
        revalidate_flights_count: 5,
      });

      // Multi-city (Circle): backend expects one origin_destination_info entry per leg with its own departure_date
      if (params.tripType === 'multi-city' && params.segments && params.segments.length >= 2) {
        if (multicityResolvedLegs && multicityResolvedLegs.length === params.segments.length) {
          const originDestinationInfo = params.segments.map((segment, i) => ({
            departure_date: formatDateForAPI(segment.date),
            origin_airport: { iata_code: multicityResolvedLegs[i]!.originIata },
            destination_airport: { iata_code: multicityResolvedLegs[i]!.destIata },
          }));
          return baseReturn(
            'Circle',
            originDestinationInfo,
            multicityResolvedLegs.some((l) => l.cityWiseOrigin),
            multicityResolvedLegs.some((l) => l.cityWiseDest)
          );
        }
        let cityWiseO = false;
        let cityWiseD = false;
        const originDestinationInfo = params.segments.map((segment) => {
          const o = resolveToIata(segment.from, segment.fromAirport ?? undefined);
          const d = resolveToIata(segment.to, segment.toAirport ?? undefined);
          if (o.cityWise) cityWiseO = true;
          if (d.cityWise) cityWiseD = true;
          return {
            departure_date: formatDateForAPI(segment.date),
            origin_airport: { iata_code: o.iata },
            destination_airport: { iata_code: d.iata },
          };
        });
        return baseReturn('Circle', originDestinationInfo, cityWiseO, cityWiseD);
      }

      let originIata: string;
      let destIata: string;
      let cityWiseOrigin: boolean;
      let cityWiseDest: boolean;

      if (resolved) {
        originIata = resolved.originIata;
        destIata = resolved.destIata;
        cityWiseOrigin = resolved.cityWiseOrigin;
        cityWiseDest = resolved.cityWiseDest;
      } else {
        const orig = resolveToIata(params.from, params.fromAirport ?? undefined);
        const dest = resolveToIata(params.to, params.toAirport ?? undefined);
        originIata = orig.iata;
        destIata = dest.iata;
        cityWiseOrigin = orig.cityWise || (params.originIsCity ?? false);
        cityWiseDest = dest.cityWise || (params.destinationIsCity ?? false);
      }

      if (params.tripType === 'round-trip') {
        const originDestinationInfo = [
          {
            departure_date: formatDateForAPI(params.date),
            origin_airport: { iata_code: originIata },
            destination_airport: { iata_code: destIata },
          },
        ];
        if (params.returnDate) {
          originDestinationInfo.push({
            departure_date: formatDateForAPI(params.returnDate),
            origin_airport: { iata_code: destIata },
            destination_airport: { iata_code: originIata },
          });
        }
        return baseReturn('Return', originDestinationInfo, cityWiseOrigin, cityWiseDest);
      }

      return baseReturn(
        'OneWay',
        [
          {
            departure_date: formatDateForAPI(params.date),
            origin_airport: { iata_code: originIata },
            destination_airport: { iata_code: destIata },
          },
        ],
        cityWiseOrigin,
        cityWiseDest
      );
    },
    []
  );

  // Derive search request from URL (?q=) - useQuery runs when this exists; cache used on return from details
  const encodedParams = searchParams.get('q') ?? '';
  const restoredParams = useMemo(
    () => deserializeSearchParamsFromUrl(encodedParams),
    [encodedParams]
  );

  useEffect(() => {
    setFlightSortBy('preference-match');
    if (!encodedParams) {
      setHasSearched(false);
      // Allow auto-search to re-fire when navigating from chat (or anywhere that drops ?q=)
      // while staying on this page — component doesn't unmount, so the ref must be cleared explicitly.
      autoSearchAttemptedRef.current = false;
    }
  }, [encodedParams]);

  // Resolve city names (e.g. "London") to IATA codes for the API.
  // Also syncs Redux form state with original city names for search bar display.
  const resolvedParams = useResolvedSearchParams(restoredParams);

  // When chat filters specify direct-only, pass it at API level too
  // (API returns more direct flights with direct_flight=1 than client-side filtering)
  const encodedFilters = searchParams.get('f') ?? '';
  const searchRequest = useMemo(() => {
    if (!resolvedParams) return null;
    // Avoid 422: Return requires two O&D rows; URL restore can omit returnDate (bad bookmark/handoff).
    if (isRoundTripSearchMissingReturnDate(resolvedParams)) return null;
    const request = buildSearchRequest(resolvedParams);
    if (encodedFilters) {
      const chatFilters = deserializeChatFiltersFromUrl(encodedFilters);
      if (chatFilters?.directOnly) {
        request.direct_flight = 1;
      }
    }
    return request;
  }, [resolvedParams, buildSearchRequest, encodedFilters]);

  // Use the Redux cache as the display source; trigger the lazy query only on cache miss.
  const searchResponse = cachedFlightResults;

  // URL-derived form params used for cache comparison to avoid stale Redux closure in the effect below.
  const urlFormParams = useMemo(
    () => (resolvedParams ? convertUIToFormParams(resolvedParams) : null),
    [resolvedParams]
  );

  // Synchronous cache hit: Redux already has valid results for the current search params.
  // When URL params are present, only compare after IATA resolution settles (urlFormParams != null).
  // Falls back to Redux form params only when there are no URL params (from-chat case where
  // Redux is pre-populated but the URL has no ?q= yet).
  const activeParams = searchParams.get('q') ? urlFormParams : searchFormParams;
  const hasReduxCacheHit = Boolean(
    cachedFlightResults &&
    !isSearchCacheExpired(cacheTimestamp) &&
    activeParams != null &&
    areFlightParamsEqual(activeParams, cachedFlightResultsParams)
  );

  // Store successful lazy query results in Redux cache.
  useEffect(() => {
    if (lazyData && searchFormParams) {
      dispatch(setCachedFlightResults({ data: lazyData, params: searchFormParams }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lazyData]);

  // On URL change / mount: check Redux cache and trigger API only on cache miss.
  // handleSearch sets skipNextUrlEffectRef before navigating so explicit searches don't double-fire.
  // Compares URL-derived urlFormParams (not Redux searchFormParams) to avoid a stale-closure race:
  // when the URL changes, setSearchFormParams may not have propagated yet on the first render,
  // so comparing Redux state would see A===A and incorrectly skip the fetch for URL params B.
  useEffect(() => {
    if (!searchRequest || !resolvedParams) return;
    if (isRoundTripSearchMissingReturnDate(resolvedParams)) return;

    if (skipNextUrlEffectRef.current) {
      skipNextUrlEffectRef.current = false;
      return;
    }

    const paramsMatch = areFlightParamsEqual(urlFormParams, cachedFlightResultsParams);
    const cacheExpired = isSearchCacheExpired(cacheTimestamp);

    if (!paramsMatch || cacheExpired) {
      void triggerSearch(searchRequest);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchRequest]); // intentionally only re-runs when URL-derived request changes

  useEffect(() => {
    if (!encodedParams || !restoredParams) return;
    if (encodedFilters && lastRestoredFilters.current !== encodedFilters) {
      const chatFilters = deserializeChatFiltersFromUrl(encodedFilters);
      if (chatFilters) {
        dispatch(setFlightFilters(chatFiltersToFilterState(chatFilters)));
        lastRestoredFilters.current = encodedFilters;
      }
    }
    if (!resolvedParams) return;
    if (isRoundTripSearchMissingReturnDate(resolvedParams)) {
      setHasSearched(false);
      return;
    }
    setHasSearched(true);
  }, [encodedParams, encodedFilters, restoredParams, resolvedParams, dispatch]);

  // Store search sessionId from search response (camelCase from API transform)
  useEffect(() => {
    const response = searchResponse as FlightSearchResponseCamel | undefined;
    const searchSessionId = response?.sessionId;
    if (searchSessionId) {
      localStorage.setItem('sessionId', searchSessionId);
    }
  }, [searchResponse]);

  const multicityLegs = (searchResponse as FlightSearchResponseCamel | undefined)?.multicityLegs;
  const isMulticitySearchUi =
    searchFormParams.tripType === 'multi-city' &&
    Array.isArray(multicityLegs) &&
    multicityLegs.length >= 2;

  const showMulticityBottomBar = Boolean(
    hasSearched &&
    !isLoading &&
    !isSearching &&
    !error &&
    isMulticitySearchUi &&
    multicityLegs &&
    multicityLegs.length >= 2
  );

  // Transform API response to FlightCard rows (one-way / round-trip use top-level itineraries)
  const flights = useMemo(() => {
    const response = searchResponse as FlightSearchResponseCamel | undefined;
    if (!response) return [];
    if (isMulticitySearchUi) return [];
    return mapFareItinerariesToFlightCards({
      fareItineraries: response.fareItineraries ?? [],
      travellers: searchFormParams.travellers,
    });
  }, [searchResponse, searchFormParams.travellers, isMulticitySearchUi]);

  /** Multicity: leg_index → card rows for that leg */
  const flightsByLeg = useMemo(() => {
    const response = searchResponse as FlightSearchResponseCamel | undefined;
    if (!response || !isMulticitySearchUi || !multicityLegs) return null;
    const out: Record<number, ReturnType<typeof mapFareItinerariesToFlightCards>> = {};
    multicityLegs.forEach((leg, idx) => {
      const key = leg.legIndex ?? idx;
      out[key] = mapFareItinerariesToFlightCards({
        fareItineraries: leg.fareItineraries ?? [],
        travellers: searchFormParams.travellers,
        legIndex: key,
      });
    });
    return out;
  }, [searchResponse, isMulticitySearchUi, multicityLegs, searchFormParams.travellers]);

  useEffect(() => {
    const n = multicityLegs?.length ?? 0;
    if (n > 0 && activeLegTab >= n) setActiveLegTab(Math.max(0, n - 1));
  }, [multicityLegs?.length, activeLegTab]);

  const filteredSortedDisplay = useMemo(() => {
    if (isMulticitySearchUi && flightsByLeg && multicityLegs) {
      const leg = multicityLegs[activeLegTab];
      if (!leg) return [];
      const key = leg.legIndex ?? activeLegTab;
      const filtered = filterFlights(flightsByLeg[key] ?? [], filterState);
      if (flightSortBy === 'preference-match') {
        return sortFlightsByPreference(filtered, flightsPrefs);
      }
      return sortFlights(filtered, flightSortBy);
    }
    const filtered = filterFlights(flights, filterState);
    if (flightSortBy === 'preference-match') {
      return sortFlightsByPreference(filtered, flightsPrefs);
    }
    return sortFlights(filtered, flightSortBy);
  }, [
    isMulticitySearchUi,
    flightsByLeg,
    multicityLegs,
    activeLegTab,
    flights,
    filterState,
    flightSortBy,
    flightsPrefs,
  ]);

  const displayedFlightCount = filteredSortedDisplay.length;
  const flightsFoundLabel = `${displayedFlightCount} ${displayedFlightCount === 1 ? 'flight' : 'flights'} found`;
  const activeFilterCount = useMemo(() => countActiveFilters(filterState), [filterState]);

  const filterPanelFlights = useMemo(() => {
    if (isMulticitySearchUi && flightsByLeg && multicityLegs) {
      const leg = multicityLegs[activeLegTab];
      if (!leg) return [];
      const key = leg.legIndex ?? activeLegTab;
      return flightsByLeg[key] ?? [];
    }
    return flights;
  }, [isMulticitySearchUi, flightsByLeg, multicityLegs, activeLegTab, flights]);

  const isRoundTrip = searchFormParams.tripType === 'round-trip';

  const handleSearch = useCallback(async (
    params: FlightSearchParamsUI,
    options?: { silent?: boolean }
  ) => {
    // `silent` suppresses the network/resolve catch-block toast for searches
    // the user did not explicitly initiate (e.g. auto-search re-fired by a
    // Redux change driven by typing into the origin field — see the
    // `?query=L → 404 Resource not found` repro). Validation toasts (missing
    // date, past date, etc.) stay loud because they're actionable feedback.
    const silent = options?.silent === true;
    // Origin, destination, and dates validation for search
    if (params.tripType !== 'multi-city') {
      if (!params.from?.trim()) {
        showErrorToast('Please enter an origin.');
        return;
      }
      if (!params.to?.trim()) {
        showErrorToast('Please enter a destination.');
        return;
      }
      if (!params.date) {
        showErrorToast('Please select a departure date.');
        return;
      }
      if (params.tripType === 'round-trip' && !params.returnDate) {
        showErrorToast('Please select a return date.');
        return;
      }
      const pastDateError = validateDatesNotInPast([
        { label: 'Departure date', value: params.date },
        { label: 'Return date', value: params.returnDate },
      ]);
      if (pastDateError) {
        showErrorToast(pastDateError);
        return;
      }
    } else if (params.tripType === 'multi-city' && params.segments) {
      const slots = params.segments.map((seg, i) => ({
        label: `Leg ${i + 1}: departure date`,
        value: seg?.date,
      }));
      const pastDateError = validateDatesNotInPast(slots);
      if (pastDateError) {
        showErrorToast(pastDateError);
        return;
      }
    }
    try {
      let resolved:
        | {
            originIata: string;
            destIata: string;
            cityWiseOrigin: boolean;
            cityWiseDest: boolean;
            originCoords: { latitude: number | null; longitude: number | null } | null;
            destCoords: { latitude: number | null; longitude: number | null } | null;
          }
        | undefined;
      let multicityResolvedLegs:
        | Array<{
            originIata: string;
            destIata: string;
            cityWiseOrigin: boolean;
            cityWiseDest: boolean;
          }>
        | undefined;

      if (params.tripType !== 'multi-city') {
        resolved = await resolveOriginDestination(
          params.from,
          params.to,
          params.fromAirport,
          params.toAirport
        );
        if (resolved.originIata.length !== 3 || resolved.destIata.length !== 3) {
          showErrorToast(
            'Could not resolve origin or destination. Please select from the dropdown or enter a valid airport code.'
          );
          return;
        }
      } else if (params.tripType === 'multi-city' && params.segments) {
        if (params.segments.length < 2) {
          showErrorToast('Multi-city search needs at least two legs.');
          return;
        }
        const incomplete = params.segments.findIndex(
          (seg) => !seg.from?.trim() || !seg.to?.trim() || !seg.date
        );
        if (incomplete >= 0) {
          showErrorToast(`Leg ${incomplete + 1}: Enter origin, destination, and departure date.`);
          return;
        }
        multicityResolvedLegs = [];
        for (const seg of params.segments) {
          const legResolved = await resolveOriginDestination(
            seg.from,
            seg.to,
            seg.fromAirport ?? null,
            seg.toAirport ?? null
          );
          if (legResolved.originIata.length !== 3 || legResolved.destIata.length !== 3) {
            showErrorToast(
              'Could not resolve airports for one leg. Pick airports from the list or use 3-letter codes.'
            );
            return;
          }
          multicityResolvedLegs.push(legResolved);
        }
      }

      // Resolve map coordinates via the single resolution path.
      // City-name lookups already fetched coords inside resolveOriginDestination; for
      // IATA-direct entries (user selected from autocomplete) we call resolveAirport once here.
      if (resolved) {
        const needOrigin = !resolved.originCoords && resolved.originIata.length === 3;
        const needDest = !resolved.destCoords && resolved.destIata.length === 3;
        const [oAirport, dAirport] =
          needOrigin || needDest
            ? await Promise.all([
                needOrigin
                  ? resolveAirport(resolved.originIata).unwrap().catch(() => null)
                  : Promise.resolve(null),
                needDest
                  ? resolveAirport(resolved.destIata).unwrap().catch(() => null)
                  : Promise.resolve(null),
              ])
            : [null, null];
        const originCoords =
          resolved.originCoords ??
          (oAirport
            ? { latitude: oAirport.latitude ?? null, longitude: oAirport.longitude ?? null }
            : null);
        const destCoords =
          resolved.destCoords ??
          (dAirport
            ? { latitude: dAirport.latitude ?? null, longitude: dAirport.longitude ?? null }
            : null);
        const next: FlightRecommendationsMapCoordinateOverrides = {};
        if (originCoords?.latitude != null && originCoords.longitude != null) {
          next.origin = { latitude: originCoords.latitude, longitude: originCoords.longitude };
        }
        if (destCoords?.latitude != null && destCoords.longitude != null) {
          next.destination = { latitude: destCoords.latitude, longitude: destCoords.longitude };
        }
        setMapCoordinateOverrides(Object.keys(next).length ? next : null);
      } else {
        setMapCoordinateOverrides(null);
      }

      const searchRequest = buildSearchRequest(params, resolved, multicityResolvedLegs);
      const newFormParams = convertUIToFormParams(params);

      // Redux cache hit: params match and cache is fresh — navigate and show cached results.
      if (
        areFlightParamsEqual(newFormParams, cachedFlightResultsParams) &&
        !isSearchCacheExpired(cacheTimestamp)
      ) {
        const encoded = serializeSearchParamsToUrl(params);
        navigate(`${routePrefix}/flights/search?q=${encodeURIComponent(encoded)}`, {
          replace: true,
        });
        dispatch(setSearchFormParams(newFormParams));
        setHasSearched(true);
        return;
      }

      // Cache miss: clear stale cache, reset state, show loading, navigate, and call API.
      setIsSearching(true);
      dispatch(clearCachedFlightResults());
      dispatch(setFlightFilters(defaultFlightFilterState));
      setFlightSortBy('preference-match');
      dispatch(setPassengers([]));
      dispatch(clearSavedPassengerIds());
      dispatch(clearMulticityLegSelections());
      setActiveLegTab(0);
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('sessionId');
      }

      const encoded = serializeSearchParamsToUrl(params);
      // Signal to URL-change effect that this search is already handled here.
      skipNextUrlEffectRef.current = true;
      navigate(`${routePrefix}/flights/search?q=${encodeURIComponent(encoded)}`, { replace: true });

      dispatch(setSearchFormParams(newFormParams));

      await triggerSearch(searchRequest);

      setHasSearched(true);
    } catch (err) {
      console.error('Flight search failed:', err);
      if (!silent) {
        showErrorToastFromError(
          err,
          'Could not search flights. Please check your origin and destination.'
        );
      }
    } finally {
      setIsSearching(false);
    }
  }, [
    buildSearchRequest,
    cachedFlightResultsParams,
    cacheTimestamp,
    dispatch,
    navigate,
    resolveAirport,
    resolveOriginDestination,
    routePrefix,
    triggerSearch,
  ]);

  // React to chip dialog Apply/radio: trigger search with current form params.
  // `prevFlightChipTrigger` avoids re-firing when only `searchFormParams` / `handleSearch` change;
  // deps include them so the effect reads fresh values when the counter actually increments.
  useEffect(() => {
    if (searchTriggerFromChips === prevFlightChipTrigger.current) return;
    prevFlightChipTrigger.current = searchTriggerFromChips;
    if (searchTriggerFromChips === 0) return;
    dispatch(resetSearchTriggerFromChips());
    const uiParams = convertFormParamsToUI(searchFormParams);
    void handleSearch(uiParams);
  }, [searchTriggerFromChips, searchFormParams, handleSearch, dispatch]);

  // Auto-search when all required params are present in Redux but no ?q= in URL.
  // Covers navigation from chat or other surfaces that pre-fill Redux without encoding URL params.
  // Re-runs when searchFormParams changes so it can retry once async resolution settles
  // (e.g. IATA resolution lands a tick after mount).
  useEffect(() => {
    if (autoSearchAttemptedRef.current || encodedParams || hasSearched) {
      if (import.meta.env.DEV) {
        console.log('[FlightChat] auto-search effect skipped (guard)', {
          autoSearchAttempted: autoSearchAttemptedRef.current,
          encodedParams: Boolean(encodedParams),
          hasSearched,
        });
      }
      return;
    }
    const params = searchFormParams;

    // Cache hit: fresh results for the current params already exist (e.g. arriving from chat).
    // Show them immediately without triggering any API call or resolveOriginDestination roundtrip.
    // NOTE: intentionally does NOT set autoSearchAttemptedRef so React 18 StrictMode's second
    // effect pass can also call setHasSearched(true) — countering the [encodedParams] effect
    // resetting hasSearched(false) between the two passes.
    const paramsMatch = areFlightParamsEqual(params, cachedFlightResultsParams);
    const cacheExpired = isSearchCacheExpired(cacheTimestamp);
    // When the cache was populated by a live-chat hydrator (fresh chat response
    // in the current session), trust it without the strict params check — the
    // chat response is the authoritative source for the trip, even if its own
    // metadata is inconsistent with the prefetched results' search params.
    // See docs/CHAT_NAV_BAR_SYNC.md.
    const cacheHit =
      Boolean(cachedFlightResults) &&
      !cacheExpired &&
      (cachedFlightResultsTrusted || paramsMatch);

    if (cacheHit) {
      // TODO(#1060): remove these `[FlightChat] 3/3` DEV logs once cache-hit behaviour
      // has stabilised in staging/production. See sibling 1/3 + 2/3 logs.
      if (import.meta.env.DEV) {
        console.log('[FlightChat] 3/3 Cache HIT — displaying results from Redux, no API call', {
          flightsInCache: (cachedFlightResults as { fareItineraries?: unknown[] }).fareItineraries?.length ?? 0,
          trusted: cachedFlightResultsTrusted,
          paramsMatch_strict: paramsMatch,
          cacheAgeMs: cacheTimestamp ? Date.now() - cacheTimestamp : 'n/a',
        });
      }
      setHasSearched(true);
      return;
    }
    // TODO(#1060): remove this companion `[FlightChat] 3/3 Cache MISS` log alongside the HIT log above.
    if (import.meta.env.DEV) {
      console.log('[FlightChat] 3/3 Cache MISS — will call search API', {
        hasCachedResults: Boolean(cachedFlightResults),
        cacheExpired,
        trusted: cachedFlightResultsTrusted,
        paramsMatch_strict: paramsMatch,
        reduxParams: params,
        cachedParams: cachedFlightResultsParams,
      });
    }

    let hasRequired: boolean;
    if (params.tripType === 'multi-city') {
      const segs = params.segments ?? [];
      hasRequired = segs.length >= 2 && segs.every((s) => s.from?.trim() && s.to?.trim() && s.date);
    } else {
      hasRequired =
        Boolean(params.from?.trim()) &&
        Boolean(params.to?.trim()) &&
        Boolean(params.date) &&
        (params.tripType !== 'round-trip' || Boolean(params.returnDate));
    }
    if (!hasRequired) {
      if (import.meta.env.DEV) {
        console.log('[FlightChat] auto-search skipped — nav bar params incomplete', {
          tripType: params.tripType,
          from: params.from,
          to: params.to,
          date: params.date,
          returnDate: params.returnDate,
          segments: params.segments,
        });
      }
      return;
    }
    if (import.meta.env.DEV) {
      console.log('[FlightChat] auto-search firing handleSearch with nav-bar params', {
        from: params.from,
        to: params.to,
        date: params.date,
        returnDate: params.returnDate,
        tripType: params.tripType,
      });
    }
    autoSearchAttemptedRef.current = true;
    // Auto-search runs in response to Redux state — including keystroke-driven
    // setFrom/setTo updates — so any failure here is not a direct response to
    // the user clicking "Search". Suppress error toasts; the user can still
    // see what's wrong via the empty results state and the Search button.
    void handleSearch(convertFormParamsToUI(params), { silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handleSearch is stable; rerun on form-params changes only
  }, [searchFormParams, encodedParams, hasSearched, cachedFlightResults, cacheTimestamp, cachedFlightResultsParams, cachedFlightResultsTrusted]);

  const handleFlightSelect = async (flightId: string) => {
    if (onPublicRoute && !ensureAuthenticated('flight_show_all_book')) return;

    if (selectingFlightId) {
      return;
    }

    try {
      setSelectingFlightId(flightId);

      const response = searchResponse as FlightSearchResponseCamel | undefined;
      const mcLegs = response?.multicityLegs;
      const isMcUi =
        searchFormParams.tripType === 'multi-city' && Array.isArray(mcLegs) && mcLegs.length >= 2;

      // Multicity: per-leg session + fare; stay on results and store in Redux (details in Phase 5)
      if (isMcUi && mcLegs) {
        const parsed = parseMulticityFlightId(flightId);
        if (!parsed) {
          showErrorToast('Invalid flight selection.');
          return;
        }
        const legMeta =
          mcLegs.find((l) => (l.legIndex ?? -1) === parsed.legIndex) ?? mcLegs[parsed.legIndex];
        if (!legMeta?.sessionId) {
          showErrorToast('This leg has no active search session. Try searching again.');
          return;
        }
        const legKey = legMeta.legIndex ?? parsed.legIndex;
        const rows = flightsByLeg?.[legKey] ?? [];
        const selectedRow = rows.find((f) => f.id === flightId);
        if (!selectedRow) {
          console.error('Selected flight not found for multicity leg');
          return;
        }

        const adults = searchFormParams.travellers.adults ?? 1;
        const children = searchFormParams.travellers.children ?? 0;
        const infants = searchFormParams.travellers.infants ?? 0;

        const revalidateResponse = await revalidateFlight({
          sessionId: legMeta.sessionId,
          fareSourceCode: parsed.fareSourceCode,
          adults,
          children,
          infants,
        }).unwrap();

        if (revalidateResponse.isFareAvailable === false) {
          showErrorToast(
            '⚠️ This flight is no longer available or the price has changed. Please pick another option.'
          );
          return;
        }

        dispatch(
          setMulticityLegSelection({
            legIndex: parsed.legIndex,
            sessionId: legMeta.sessionId,
            fareSourceCode: parsed.fareSourceCode,
            selectedFlightData: {
              id: selectedRow.id,
              aircraftName: selectedRow.aircraftName,
              flightNumber: selectedRow.flightNumber,
              tags: selectedRow.tags,
              passengers: selectedRow.passengers,
              passengerCounts: selectedRow.passengerCounts,
              legs: selectedRow.legs,
              price: selectedRow.price,
              _originalItinerary: selectedRow._originalItinerary,
            },
            revalidateResponse: revalidateResponse as FlightRevalidateResponseCamel,
          })
        );
        const pickedIndices = new Set(Object.keys(multicitySelectedLegs).map((k) => Number(k)));
        pickedIndices.add(parsed.legIndex);
        const pickedCount = pickedIndices.size;
        const totalLegs = mcLegs.length;
        if (pickedCount >= totalLegs) {
          showSuccessToast('All legs selected. Continue to passenger details and payment.');
        } else {
          showSuccessToast(`Leg ${parsed.legIndex + 1} selected (${pickedCount}/${totalLegs}).`);
        }
        return;
      }

      // One-way / round-trip: find flight and navigate to details after revalidate
      type FlightItem = {
        id: string;
        aircraftName: string;
        tags: string[];
        passengers: number;
        legs: unknown[];
        price: number;
        discount?: number;
      };
      const selectedFlightData = flights.find((f: FlightItem) => f.id === flightId);
      if (!selectedFlightData) {
        console.error('Selected flight not found');
        return;
      }

      const searchSessionId = response?.sessionId ?? localStorage.getItem('sessionId') ?? '';

      if (!searchSessionId) {
        console.error('No session ID available for flight selection');
        return;
      }

      const adults = searchFormParams.travellers.adults ?? 1;
      const children = searchFormParams.travellers.children ?? 0;
      const infants = searchFormParams.travellers.infants ?? 0;

      const revalidateResponse = await revalidateFlight({
        sessionId: searchSessionId,
        fareSourceCode: flightId,
        adults,
        children,
        infants,
      }).unwrap();

      if (revalidateResponse.isFareAvailable === false) {
        showErrorToast(
          '⚠️ This flight is no longer available or the price has changed. Please search again.'
        );
        return;
      }

      const encodedFareSourceCode = encodeURIComponent(flightId);
      navigate(`/flights/details/${encodedFareSourceCode}`, {
        state: {
          revalidateResponse,
          selectedFlightData,
          searchSessionId,
        },
      });
    } catch (err) {
      console.error('Error selecting flight:', err);
      showErrorToast('The flight is no longer available');
    } finally {
      setSelectingFlightId(null);
    }
  };

  const [mapCoordinateOverrides, setMapCoordinateOverrides] =
    useState<FlightRecommendationsMapCoordinateOverrides | null>(null);

  // Seed map overrides from the active saved itinerary's tripMeta (city-center
  // lat/lng) when the user arrives via Itinerary → View flights. handleSearch
  // overrides win as soon as the user runs a search. Stale-itinerary guard:
  // override only applies when the tripMeta city matches the nav-bar string
  // case-insensitively — see getItineraryMapOverrideFromTripMeta.
  const activeSavedItineraryId = useAppSelector(selectActiveSavedItineraryIdForBooking);
  const { data: activeItinerary } = useGetItineraryQuery(activeSavedItineraryId ?? '', {
    skip: !activeSavedItineraryId,
  });
  const itineraryMapOverride = useMemo(
    () =>
      getItineraryMapOverrideFromTripMeta(activeItinerary?.tripMeta ?? null, {
        from: searchFormParams.from,
        to: searchFormParams.to,
        fromIata: searchFormParams.fromAirport?.iata,
        toIata: searchFormParams.toAirport?.iata,
      }),
    [
      activeItinerary?.tripMeta,
      searchFormParams.from,
      searchFormParams.to,
      searchFormParams.fromAirport?.iata,
      searchFormParams.toAirport?.iata,
    ]
  );
  const effectiveMapOverrides = mapCoordinateOverrides ?? itineraryMapOverride;

  const mapProps = useMemo(
    () =>
      getFlightSearchPageMapProps(
        {
          from: searchFormParams.from,
          to: searchFormParams.to,
          fromIata: searchFormParams.fromAirport?.iata,
          toIata: searchFormParams.toAirport?.iata,
        },
        effectiveMapOverrides
      ),
    [
      searchFormParams.from,
      searchFormParams.to,
      searchFormParams.fromAirport?.iata,
      searchFormParams.toAirport?.iata,
      effectiveMapOverrides,
    ]
  );

  return (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      {/* Search bar + alerts: fixed at top, never scrolls */}
      <Box style={{ flex: '0 0 auto' }}>
        <Container size="xl" px={0} pt={0}>
          <FlightSearchBarV2 />

          {/* Malformed round-trip URL (?q=) — missing return date would 422 the search API */}
          {encodedParams && resolvedParams && isRoundTripSearchMissingReturnDate(resolvedParams) && (
            <Alert color="yellow" mb="md">
              This round-trip link is missing a return date. Choose a return date above and search
              again.
            </Alert>
          )}

          {/* Initial state - show "search flights" text only when no URL params and no cached results */}
          {!hasSearched && !hasReduxCacheHit && !encodedParams && (
            <Box ta="center" py={64}>
              <Title order={5} c="dimmed" fw={500}>
                Search flights
              </Title>
              <Text c="dimmed" mt="md">
                Enter your travel details above and click "Search flights" to find available options
              </Text>
            </Box>
          )}

          {/* Loading state — suppressed when Redux already has valid cached results */}
          {(isLoading ||
            isSearching ||
            (!!encodedParams &&
              !hasSearched &&
              !hasReduxCacheHit &&
              !error &&
              !!restoredParams &&
              !isRoundTripSearchMissingReturnDate(resolvedParams))) && (
            <Group justify="center" align="center" py={64}>
              <Loader />
              <Text c="dimmed">Searching for flights…</Text>
            </Group>
          )}

          {/* Error state */}
          {error && (
            <Box mb="xl">
              <Alert color="red">
                {'data' in error &&
                typeof error.data === 'object' &&
                error.data &&
                'detail' in error.data
                  ? String(error.data.detail)
                  : 'Failed to search flights. Please try again.'}
              </Alert>
            </Box>
          )}
        </Container>
      </Box>

      {/* Two-column results layout: left = scrollable flight list, right = map */}
      {(hasSearched || hasReduxCacheHit) && !isLoading && !isSearching && (
        <Group
          gap="md"
          align="stretch"
          wrap="nowrap"
          style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}
        >
          {/* Left column: label + multicity tabs + scrollable flight cards */}
          <Box
            style={{
              flex: FLIGHTS_CONTENT_SPLIT.LIST,
              minWidth: 0,
              minHeight: 0,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header — does not scroll */}
            <Box style={{ flex: '0 0 auto' }}>
              {/* Mobile: label + sort/filter toolbar (no right column on mobile) */}
              {isLgDown && (
                <Group justify="space-between" align="center" gap="xs" wrap="nowrap" mb="sm">
                  <Text
                    component="p"
                    fw={700}
                    m={0}
                    style={{
                      minWidth: 0,
                      paddingRight: 4,
                      color: 'var(--mantine-color-dark-8)',
                      lineHeight: 1.25,
                      fontSize: '1rem',
                    }}
                  >
                    {flightsFoundLabel}
                  </Text>
                  <MobileSortToolbar
                    sortVariant="value"
                    menuItems={FLIGHT_SORT_MENU_ITEMS}
                    selectedSort={flightSortBy}
                    onSortChange={setFlightSortBy}
                    secondaryAction={{
                      label: 'Change preferences',
                      icon: <SlidersHorizontal size={18} />,
                      onClick: handleChangePreferences,
                    }}
                    primaryButton={{
                      label: activeFilterCount > 0 ? `Filters (${activeFilterCount})` : 'Filters',
                      onClick: () => setFiltersDialogOpen(true),
                    }}
                  />
                </Group>
              )}

              {/* Desktop: label only — filters/sort live in the right column */}
              {!isLgDown && (
                <Text
                  component="p"
                  fw={700}
                  m={0}
                  mb="sm"
                  style={{
                    color: 'var(--mantine-color-dark-8)',
                    lineHeight: 1.25,
                    fontSize: '1.5rem',
                  }}
                >
                  {flightsFoundLabel}
                </Text>
              )}

              {isMulticitySearchUi && multicityLegs && multicityLegs.length > 0 && (
                <Box mb="sm">
                  <Text size="sm" c="dimmed" mb={4}>
                    Select one flight per leg. Each leg uses its own supplier session.
                  </Text>
                  <MulticityLegPillTabs
                    legs={multicityLegs}
                    value={activeLegTab}
                    onChange={setActiveLegTab}
                  />
                  {(() => {
                    const active = multicityLegs[activeLegTab];
                    if (!active) return null;
                    const errMsg =
                      active.errors
                        ?.map((e) => e.message)
                        .filter(Boolean)
                        .join(' ') ||
                      (!active.sessionId && (active.fareItineraries?.length ?? 0) === 0
                        ? 'No flights found for this leg. Try changing dates or airports.'
                        : null);
                    return errMsg ? (
                      <Alert color="yellow" mb="sm">
                        {errMsg}
                      </Alert>
                    ) : null;
                  })()}
                </Box>
              )}
            </Box>

            {/* Scrollable flight cards */}
            <Box style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingInline: 8 }}>
              <FlightResults
                flights={filteredSortedDisplay as ComponentProps<typeof FlightResults>['flights']}
                onFlightSelect={handleFlightSelect}
                selectingFlightId={selectingFlightId}
                selectedFlightId={
                  isMulticitySearchUi && multicityLegs && multicityLegs[activeLegTab]
                    ? (multicitySelectedLegs[
                        multicityLegs[activeLegTab]!.legIndex ?? activeLegTab
                      ]?.selectedFlightData?.id ?? null)
                    : null
                }
              />
            </Box>
          </Box>

          {/* Right column: filters/sort header + map — hidden on mobile/tablet */}
          <Box
            visibleFrom="lg"
            style={{
              flex: FLIGHTS_CONTENT_SPLIT.MAP,
              minWidth: 0,
              minHeight: 0,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Filters + Sort above the map */}
            <Group gap="sm" mb="sm" justify="flex-end" style={{ flex: '0 0 auto' }}>
              <Select
                value={flightSortBy}
                onChange={(value) => value && setFlightSortBy(value as FlightSortOption)}
                data={FLIGHT_SORT_MENU_ITEMS.map((opt) => ({
                  value: opt.value,
                  label: opt.label,
                }))}
                size="sm"
                style={{ minWidth: 220 }}
                allowDeselect={false}
              />
              <Tooltip label="Change preferences" withArrow>
                <ActionIcon
                  variant="outline"
                  size="lg"
                  radius="xl"
                  aria-label="Change preferences"
                  onClick={handleChangePreferences}
                >
                  <SlidersHorizontal size={16} />
                </ActionIcon>
              </Tooltip>
              <Button
                variant="outline"
                size="sm"
                leftSection={<Filter size={16} />}
                onClick={() => setFiltersDialogOpen(true)}
                style={{ borderRadius: 100 }}
              >
                {activeFilterCount > 0 ? `Filters (${activeFilterCount})` : 'Filters'}
              </Button>
            </Group>

            {/* Map fills remaining height */}
            <Box style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <MapComponent {...mapProps} />
            </Box>
          </Box>
        </Group>
      )}

      {/* Filters dialog */}
      <FlightFiltersDialog
        opened={filtersDialogOpen}
        onClose={() => setFiltersDialogOpen(false)}
        filterState={filterState}
        onFilterChange={(next) => dispatch(setFlightFilters(next))}
        allFlights={filterPanelFlights as FilterableFlight[]}
        isRoundTrip={isRoundTrip}
        filteredFlightCount={displayedFlightCount}
      />

      {showMulticityBottomBar && multicityLegs ? (
        <MulticitySelectionBottomBar
          allLegs={multicityLegs}
          selectedLegs={multicitySelectedLegs}
          onReviewBook={() => navigate(flightDetailsPath(FLIGHT_DETAILS_MULTICITY_SEGMENT))}
        />
      ) : null}
    </Box>
  );
}
