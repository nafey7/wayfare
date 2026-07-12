import { lazy, Suspense, useState, useCallback, useEffect, useLayoutEffect, useRef, useMemo } from 'react';
import { CONTENT_SPLIT } from '@/components/layout/layoutConstants';
import {
  Alert,
  Box,
  Button,
  Container,
  Group,
  Loader,
  Text,
  Title,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Map as MapIcon } from 'lucide-react';
import { MapComponent, type MapComponentProps } from '@/features/itinerary/components';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { APIProvider } from '@vis.gl/react-google-maps';
import { ROUTES, isPublicChatRoute } from '@/features/routing/constants';
import { getContentRoutePrefix } from '@/features/routing';
import { usePublicChatConversionGate } from '@/features/chat/hooks/usePublicChatConversionGate';
import { showErrorToastFromError, showErrorToast } from '@/utils/toast';
import { useAppDispatch, useAppSelector } from '@/store';
import { HotelResults } from '../components/HotelResults';
import { HotelFiltersDialog } from '../components/HotelFiltersDialog';
import { HotelSortAndFiltersHeader } from '../components/HotelSortAndFiltersHeader';
import { HotelMultistayLegTabs } from '../components/HotelMultistayLegTabs';
import { HotelMultistayBottomBar } from '../components/HotelMultistayBottomBar';
import {
  setSearchFormParams,
  setSearchParams,
  setSessionId,
  setSelectedHotel,
  setRoomRatesResponse,
  setHotelFilters,
  selectHotelSearchFormParams,
  selectHotelFilters,
  selectHotelSessionId,
  selectHotelSearchParams,
  selectHotelSearchTriggerFromChips,
  resetSearchTriggerFromChips,
  selectHotelTripType,
  selectMultistaySegments,
  selectMultistayLegs,
  selectMultistayActiveLegTab,
  setMultistayLegSearchResults,
  setMultistayActiveLegTab,
  setCachedHotelResults,
  clearCachedHotelResults,
  selectCachedHotelResults,
  selectCachedHotelResultsTrusted,
  selectHotelResultsCacheTimestamp,
  selectHotelResultsCachedParams,
} from '@/store/slices/hotelBookingSlice';
import { isSearchCacheExpired, areHotelParamsEqual } from '@/utils/searchResultsCache';
import {
  useLazySearchHotelsQuery,
  useGetMoreResultsMutation,
  useGetRoomRatesMutation,
  hotelsApi,
} from '@/api/hotelsApi';
import { useLazyResolveCityQuery } from '@/api/geocodingApi';
import type { HotelSearchRequest, Hotel, HotelItinerary } from '@/types/hotels';
import {
  serializeHotelSearchParamsToUrl,
  deserializeHotelSearchParamsFromUrl,
  deserializeChatHotelFiltersFromUrl,
  chatHotelFiltersToFilterState,
} from '../utils/urlParams';
import { persistHotelRoomsContext } from '../utils/hotelRoomsContextStorage';
import { toFilterableHotel, filterHotels, countActiveHotelFilters, type FilterableHotel } from '../utils/hotelFilters';
import {
  sortHotels,
  getHotelSortMenuItems,
  type HotelSortOption,
} from '../utils/hotelSort';
import { sortHotelsByPreference } from '../utils/hotelPreferenceScore';
import { useGetProfileQuery } from '@/api/usersApi';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { buildHotelSearchRequestFromFormParams } from '../utils/buildHotelSearchRequest';
import { hasValidCoords, getHotelKey } from '@/features/hotels/utils/hotelMapCoords';
import { getHotelSearchPageMapProps } from '../utils/hotelMapLocation';
import { HotelsMobileSheetView } from '../components/mobile/HotelsMobileSheetView';
import { HotelsMobileMap } from '../components/mobile/HotelsMobileMap';
import { validateDatesNotInPast } from '@/utils/dateValidation';

const HotelSearchMobileMapOverlay = lazy(() =>
  import('../components/mobile/HotelSearchMobileMapOverlay').then((m) => ({
    default: m.HotelSearchMobileMapOverlay,
  }))
);

const HOTELS_PAGE_SIZE = 24;

const Z_INDEX_OVERLAY_LOADING = 200;
const Z_INDEX_SEARCH_MAP_FAB = 1050;

function showCityResolutionError(err: unknown, cityName: string) {
  if (err && typeof err === 'object' && 'status' in err && (err as { status: number }).status === 404) {
    showErrorToastFromError(
      err,
      cityName
        ? `Could not determine country for "${cityName}". Try "City, Country" (e.g. "Paris, France") or specify the country.`
        : 'Could not resolve city. Try "City, Country" format.'
    );
  } else {
    showErrorToastFromError(err, 'Hotel search failed. Please try again.');
  }
}

/**
 * Hotel Search Page — search form + results (combined).
 * Route: /hotels/search
 * Supports ?q=base64(params) and ?initial_step=results&auto_search=true for deep linking.
 */
export function HotelSearchPage() {
  const isLgDown = useMediaQuery('(max-width: 1199px)') ?? false;
  const isMobile = useMediaQuery('(max-width: 599px)') ?? false;
  const isMdDown = useMediaQuery('(max-width: 899px)') ?? false;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchMapOpen, setSearchMapOpen] = useState(false);
  const searchMapFabRef = useRef<HTMLButtonElement>(null);
  const [selectedDesktopPinKey, setSelectedDesktopPinKey] = useState<string | null>(null);
  const desktopCardElRefs = useRef<Map<string, HTMLElement>>(new Map());
  const pendingScrollKey = useRef<string | null>(null);
  const filteredHotelsRef = useRef<FilterableHotel[]>([]);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const encodedHotelQ = searchParams.get('q') ?? '';
  const { ensureAuthenticated } = usePublicChatConversionGate();
  const onPublicRoute = isPublicChatRoute(location.pathname);
  const handleChangePreferences = useCallback(() => {
    if (onPublicRoute) {
      navigate(ROUTES.ONBOARDING);
      return;
    }
    navigate('/profile?section=hotel');
  }, [navigate, onPublicRoute]);
  const routePrefix = getContentRoutePrefix(location.pathname);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [resolutionFailed, setResolutionFailed] = useState(false);
  const activeSearchParams = useAppSelector(selectHotelSearchParams);
  const nearbyLocation = activeSearchParams?.nearbyLocation;
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const { data: profile } = useGetProfileQuery(undefined, { skip: !isAuthenticated });
  const hotelsPrefs = profile?.preferences?.hotels ?? null;
  const travelStylePrefs = profile?.preferences?.travelStyle ?? null;
  const [sortBy, setSortBy] = useState<HotelSortOption>(isAuthenticated ? 'preference-match' : 'price-low');
  const [selectingTokenId, setSelectingTokenId] = useState<string | null>(null);
  const [extraHotels, setExtraHotels] = useState<(Hotel | HotelItinerary)[]>([]);
  const [nextToken, setNextToken] = useState<string | null>(null);
  const [resultsPage, setResultsPage] = useState(1);
  const [getMoreResults, { isLoading: isLoadingMore }] = useGetMoreResultsMutation();
  const [triggerSearch, { data: lazyData, isLoading, error }] = useLazySearchHotelsQuery();
  const [getRoomRates] = useGetRoomRatesMutation();
  const [resolveCity] = useLazyResolveCityQuery();
  const hasRestoredFromUrl = useRef(false);
  const lastUrlParams = useRef<string | null>(null);
  const lastRestoredFilters = useRef<string>('');
  const prevHotelChipTrigger = useRef(0);
  const autoSearchAttemptedRef = useRef(false);

  // Measure content area offset so the mobile sheet overlay starts below the navbar + search bar.
  const pageContainerRef = useRef<HTMLDivElement>(null);
  const [sheetTopOffset, setSheetTopOffset] = useState(0);
  useLayoutEffect(() => {
    if (!isMobile) return;
    const el = pageContainerRef.current;
    if (!el) return;
    setSheetTopOffset(Math.round(el.getBoundingClientRect().top));
  }, [isMobile]);

  // Multi-stay state
  const tripType = useAppSelector(selectHotelTripType);
  const multistaySegments = useAppSelector(selectMultistaySegments);
  const multistayLegs = useAppSelector(selectMultistayLegs);
  const activeLegTab = useAppSelector(selectMultistayActiveLegTab);
  const [isMultistaySearching, setIsMultistaySearching] = useState(false);
  // Hoisted here so the mount-only useEffect below can read it at capture time.
  const multistayHasResults = multistayLegs.some((leg) => leg.hotels.length > 0);

  useEffect(() => {
    // Changing the hotel search query URL is treated as a new search, so we reset
    // the sort selection to the default for the current mode. For nearby-location
    // searches that start from the widget, that default is still `recommended`.
    // This will override a manual sort selection on back/forward navigation.
    setSortBy(nearbyLocation ? 'recommended' : isAuthenticated ? 'preference-match' : 'price-low');
    if (!encodedHotelQ) setHasSearched(false);
    setResolutionFailed(false);
  }, [encodedHotelQ, nearbyLocation, isAuthenticated]);

  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const searchTriggerFromChips = useAppSelector(selectHotelSearchTriggerFromChips);
  const filterState = useAppSelector(selectHotelFilters);
  const sessionId = useAppSelector(selectHotelSessionId);

  // Redux search results cache
  const cachedHotelResults = useAppSelector(selectCachedHotelResults);
  const cachedHotelResultsTrusted = useAppSelector(selectCachedHotelResultsTrusted);
  const hotelCacheTimestamp = useAppSelector(selectHotelResultsCacheTimestamp);
  const cachedHotelResultsParams = useAppSelector(selectHotelResultsCachedParams);
  // Redux cache is the display source; lazyData is stored to Redux on arrival then dropped by RTK on unsubscribe (keepUnusedDataFor: 0).
  const searchResponse = cachedHotelResults;

  // URL-derived form params for cache comparison — avoids searchFormParams staleness on URL change.
  const urlDerivedHotelForm = useMemo(
    () => (encodedHotelQ ? deserializeHotelSearchParamsFromUrl(encodedHotelQ) : null),
    [encodedHotelQ]
  );

  // Synchronous cache hit: URL params are present and match the Redux cache (back-navigation).
  // We intentionally do NOT fall back to searchFormParams here: when the user clears the URL
  // (navigating from ?q= to no ?q=), searchFormParams still holds the previous search values
  // and would incorrectly keep the results visible instead of showing the empty state.
  // The from-chat case (no URL, Redux pre-populated) is handled by the mount-only autoSearch
  // useEffect which sets hasSearched=true synchronously on the first effect run.
  const hasReduxCacheHit = Boolean(
    urlDerivedHotelForm != null &&
    cachedHotelResults &&
    !isSearchCacheExpired(hotelCacheTimestamp) &&
    areHotelParamsEqual(urlDerivedHotelForm, cachedHotelResultsParams)
  );

  // Store successful API results in the Redux cache so back-navigation skips the network call.
  useEffect(() => {
    if (!lazyData || !searchFormParams.destination) return;
    dispatch(setCachedHotelResults({ data: lazyData, params: searchFormParams }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lazyData]);

  // Restore search params and filters from URL on mount or when ?q= changes (back/forward navigation).
  useEffect(() => {
    const encodedParams = searchParams.get('q');
    if (!encodedParams || encodedParams === lastUrlParams.current) return;

    lastUrlParams.current = encodedParams;
    const restored = deserializeHotelSearchParamsFromUrl(encodedParams);
    if (!restored) return;

    dispatch(setSearchFormParams(restored));
    hasRestoredFromUrl.current = true;

    // Restore chat filters from ?f= param (set by chat "View all results" link)
    const encodedFilters = searchParams.get('f');
    if (encodedFilters && lastRestoredFilters.current !== encodedFilters) {
      const chatFilters = deserializeChatHotelFiltersFromUrl(encodedFilters);
      if (chatFilters) {
        dispatch(setHotelFilters(chatHotelFiltersToFilterState(chatFilters)));
        lastRestoredFilters.current = encodedFilters;
      }
    }

    const form = restored;
    if (!form.destination?.trim() || !form.checkin || !form.checkout) return;

    // Check Redux cache synchronously before any network calls.
    // If params match and cache is fresh, show results immediately — no resolveCity, no API call.
    // setSearchFormParams(restored) was already dispatched above so activeSearchParams is already
    // current; we intentionally skip setSearchParams(request) here because resolveCity hasn't run
    // yet and nearbyLocation is not available. This is safe: the cache was populated by a prior
    // search that already persisted the full params (including nearbyLocation) to activeSearchParams.
    const hotelUrlParamsMatch = areHotelParamsEqual(form, cachedHotelResultsParams);
    const hotelUrlCacheExpired = isSearchCacheExpired(hotelCacheTimestamp);
    if (hotelUrlParamsMatch && !hotelUrlCacheExpired) {
      setHasSearched(true);
      setResultsPage(1);
      return;
    }

    const baseRequest: HotelSearchRequest = {
      checkin: form.checkin,
      checkout: form.checkout,
      cityName: form.destination.trim(),
      occupancy: (form.rooms ?? []).map((r) => ({
        roomNo: r.roomNo,
        adult: r.adult ?? 1,
        child: r.child ?? 0,
        childAge: (r.child ?? 0) > 0 ? (r.childAge ?? [0]).slice(0, r.child!) : [0],
      })),
      nationality: form.nationality || 'US',
    };

    (async () => {
      try {
        const resolved = await resolveCity(form.destination!.trim()).unwrap();
        const request: HotelSearchRequest = { ...baseRequest, countryName: resolved.country };
        dispatch(setSearchParams(request));
        triggerSearch(request).catch((err) => {
          console.error('Hotel search from URL failed:', err);
        });
        setHasSearched(true);
        setResultsPage(1);
      } catch (err) {
        console.error('Hotel search from URL failed:', err);
        setResolutionFailed(true);
        showCityResolutionError(err, form.destination?.trim() ?? '');
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, dispatch, triggerSearch, resolveCity]); // cachedHotelResultsParams/hotelCacheTimestamp intentionally omitted — read as snapshot when URL changes, not reactive deps

  // Sync base results from RTK Query cache/response; reset load-more when search changes
  useEffect(() => {
    if (searchResponse) {
      setExtraHotels([]);
      setNextToken(searchResponse.nextToken ?? null);
    }
  }, [searchResponse]);

  // Store sessionId from search response
  useEffect(() => {
    const sessionId = searchResponse?.sessionId;
    if (sessionId) {
      dispatch(setSessionId(sessionId));
      try {
        localStorage.setItem('hotelSessionId', sessionId);
      } catch {
        // ignore
      }
    }
  }, [searchResponse, dispatch]);

  const handleSearch = useCallback(
    async (request: HotelSearchRequest) => {
      const cityName = request.cityName?.trim();
      if (!cityName) return;
      const pastDateError = validateDatesNotInPast([
        { label: 'Check-in date', value: request.checkin },
        { label: 'Check-out date', value: request.checkout },
      ]);
      if (pastDateError) {
        showErrorToast(pastDateError);
        return;
      }
      try {
        setIsSearching(true);
        const resolved = await resolveCity(cityName).unwrap();
        const requestWithCountry: HotelSearchRequest = {
          ...request,
          countryName: resolved.country,
        };

        const newFormParams = {
          destination: request.cityName ?? '',
          checkin: request.checkin,
          checkout: request.checkout,
          rooms: request.occupancy,
          nationality: request.nationality ?? 'US',
        };

        const encoded = serializeHotelSearchParamsToUrl(newFormParams);

        // Redux cache hit: same params, fresh cache — navigate and show cached results.
        if (
          areHotelParamsEqual(newFormParams, cachedHotelResultsParams) &&
          !isSearchCacheExpired(hotelCacheTimestamp)
        ) {
          navigate(`${routePrefix}/hotels/search?q=${encodeURIComponent(encoded)}`, { replace: true });
          lastUrlParams.current = encoded;
          dispatch(setSearchFormParams(newFormParams));
          dispatch(setSearchParams(requestWithCountry));
          setResultsPage(1);
          setHasSearched(true);
          return;
        }

        // Cache miss: clear stale cache and fetch fresh results.
        dispatch(clearCachedHotelResults());
        navigate(`${routePrefix}/hotels/search?q=${encodeURIComponent(encoded)}`, { replace: true });
        lastUrlParams.current = encoded;

        dispatch(setSearchFormParams(newFormParams));
        dispatch(setSearchParams(requestWithCountry));

        await triggerSearch(requestWithCountry);
        setResultsPage(1);
        setHasSearched(true);
      } catch (err) {
        console.error('Hotel search failed:', err);
        showCityResolutionError(err, cityName ?? '');
      } finally {
        setIsSearching(false);
      }
    },
    [navigate, dispatch, triggerSearch, resolveCity, routePrefix, cachedHotelResultsParams, hotelCacheTimestamp]
  );

  // Auto-search on mount when all required params are already in Redux but no ?q= in URL.
  // Cache hit (e.g. arriving from chat): render Redux cache directly — no navigation, no
  // resolveCity, no triggerSearch. Mirrors FlightSearchPage's mount-only effect.
  // Cache miss: navigate to ?q= so URL restoration runs resolveCity + triggerSearch.

  useEffect(() => {
    if (autoSearchAttemptedRef.current || encodedHotelQ || hasSearched) return;
    // Multi-stay results are pre-populated by chat chain hydration — no fresh search needed.
    if (tripType === 'multi-stay' && multistayHasResults) {
      setHasSearched(true);
      return;
    }
    if (!buildHotelSearchRequestFromFormParams(searchFormParams)) return;

    const hotelMountParamsMatch = areHotelParamsEqual(searchFormParams, cachedHotelResultsParams);
    const hotelMountCacheExpired = isSearchCacheExpired(hotelCacheTimestamp);
    // See docs/CHAT_NAV_BAR_SYNC.md — trust cache populated by live-chat hydrators
    // even when its stored params differ from the current form (e.g. backend gave
    // mismatching `adults` on the prefetch vs the itinerary metadata).
    const hotelCacheHit =
      Boolean(cachedHotelResults) &&
      !hotelMountCacheExpired &&
      (cachedHotelResultsTrusted || hotelMountParamsMatch);

    if (import.meta.env.DEV) {
      console.log('[HotelChat] mount-only cache-hit check', {
        searchFormParams,
        cachedHotelResultsParams,
        paramsMatch_strict: hotelMountParamsMatch,
        trusted: cachedHotelResultsTrusted,
        hasCachedResults: Boolean(cachedHotelResults),
        cacheExpired: hotelMountCacheExpired,
        cacheHit: hotelCacheHit,
      });
    }

    if (hotelCacheHit) {
      // Cache hit — display cached results without touching the URL or the network.
      // Intentionally does NOT flip autoSearchAttemptedRef so React 18 StrictMode's
      // second effect pass can also short-circuit here.
      setHasSearched(true);
      setResultsPage(1);
      return;
    }

    const encoded = serializeHotelSearchParamsToUrl(searchFormParams);
    if (!encoded) return;
    autoSearchAttemptedRef.current = true;
    navigate(`${routePrefix}/hotels/search?q=${encodeURIComponent(encoded)}`, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional mount-only
  }, []); // intentional mount-only: check cache, else navigate to ?q= for URL-restoration search

  // Base results from RTK Query cache + load-more additions
  const accumulatedHotels = useMemo(
    () => [...(searchResponse?.hotels ?? []), ...extraHotels],
    [searchResponse?.hotels, extraHotels]
  );

  const nights = useMemo(() => {
    const params = searchFormParams;
    if (!params.checkin || !params.checkout) return 1;
    const a = new Date(params.checkin);
    const b = new Date(params.checkout);
    const diff = Math.max(0, Math.ceil((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24)));
    return diff || 1;
  }, [searchFormParams]);

  const { filteredHotels, hotelObjects } = useMemo(() => {
    const filterable = accumulatedHotels.map(toFilterableHotel);
    const filtered = filterHotels(filterable, filterState);
    const sorted =
      sortBy === 'preference-match'
        ? sortHotelsByPreference(filtered, hotelsPrefs, travelStylePrefs)
        : sortHotels(filtered, sortBy);
    const byTokenId = new Map<string, Hotel | HotelItinerary>(
      accumulatedHotels.map((h) => [h.tokenId ?? h.id, h])
    );
    const objects = sorted.map((f) => byTokenId.get(f.tokenId) ?? byTokenId.get(f.id)).filter(Boolean) as (Hotel | HotelItinerary)[];
    return { filteredHotels: sorted, hotelObjects: objects };
  }, [accumulatedHotels, filterState, sortBy, hotelsPrefs, travelStylePrefs]);

  // Keep a stable ref so the pin-scroll effect can read the latest filtered list
  // without adding filteredHotels as a dependency (which would re-run on every filter change).
  filteredHotelsRef.current = filteredHotels;

  // Reset to first page when sort or filters change; clear any pending scroll so a
  // stale key doesn't fire on a card that happens to reuse it after the filter narrows.
  useEffect(() => {
    setResultsPage(1);
    pendingScrollKey.current = null;
  }, [sortBy, filterState]);

  // Desktop: scroll the card list so the pin-selected card is visible.
  // If the hotel is on a different page, switch to that page first; onCardRef
  // will complete the scroll once the card mounts.
  useEffect(() => {
    if (!selectedDesktopPinKey) {
      pendingScrollKey.current = null;
      return;
    }
    const card = desktopCardElRefs.current.get(selectedDesktopPinKey);
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }
    // Card not rendered — find which page it lives on and navigate there.
    const idx = filteredHotelsRef.current.findIndex(
      (h) => (h.tokenId ?? h.id) === selectedDesktopPinKey
    );
    if (idx === -1) return;
    const targetPage = Math.floor(idx / HOTELS_PAGE_SIZE) + 1;
    pendingScrollKey.current = selectedDesktopPinKey;
    setResultsPage(targetPage);
  }, [selectedDesktopPinKey]);

  const activeFilterCount = useMemo(() => countActiveHotelFilters(filterState), [filterState]);
  const desktopMapHotels = useMemo(() => hotelObjects.filter(hasValidCoords), [hotelObjects]);
  const cityPinMapProps = useMemo(
    () => getHotelSearchPageMapProps(searchFormParams.destination),
    [searchFormParams.destination]
  );

  useEffect(() => {
    if (!isLgDown) setFiltersOpen(false);
  }, [isLgDown]);

  const handleHotelSelect = useCallback(
    async (hotel: Hotel | HotelItinerary) => {
      if (onPublicRoute && !ensureAuthenticated('hotel_show_all_book')) return;

      const it = hotel as HotelItinerary;
      const tokenId = hotel.tokenId ?? hotel.id;
      const productId = it.productId ?? '';
      const hotelId = hotel.id;
      if (!sessionId || !productId || !hotelId) {
        showErrorToastFromError(
          new Error('Missing session or hotel details. Please run the search again.')
        );
        return;
      }
      setSelectingTokenId(tokenId);
      try {
        const roomRatesResult = await getRoomRates({
          sessionId,
          tokenId,
          productId,
          hotelId,
        }).unwrap();
        dispatch(
          setSelectedHotel({
            hotel: it,
            tokenId,
            productId: it.productId ?? null,
            hotelId: hotel.id,
          })
        );
        dispatch(setRoomRatesResponse(roomRatesResult));
        persistHotelRoomsContext({
          tokenId,
          sessionId,
          productId,
          hotelId,
          selectedHotel: it,
          searchFormParams,
        });
        // Rooms detail is auth-only here (`ensureAuthenticated` above). Use the canonical app path, not
        // `routePrefix` — public users who pass the gate are routed like signed-in users.
        navigate(`/hotels/rooms/${tokenId}`);
      } catch (err) {
        showErrorToastFromError(err);
      } finally {
        setSelectingTokenId(null);
      }
    },
    [dispatch, navigate, sessionId, getRoomRates, searchFormParams, onPublicRoute, ensureAuthenticated]
  );

  const handleLoadMore = useCallback(async () => {
    if (!sessionId || !nextToken) return;
    try {
      const res = await getMoreResults({ sessionId, nextToken, ...(nearbyLocation ? { nearbyLocation } : {}) }).unwrap();
      setExtraHotels((prev) => [...prev, ...(res.hotels ?? [])]);
      setNextToken(res.nextToken ?? null);
    } catch (err) {
      console.error('Load more hotels failed:', err);
      showErrorToastFromError(err, 'Failed to load more hotels.');
    }
  }, [sessionId, nextToken, getMoreResults, nearbyLocation]);

  const handleMultistaySearch = useCallback(async () => {
    const invalid = multistaySegments.find((s) => !s.destination.trim() || !s.checkin || !s.checkout);
    if (invalid) {
      showErrorToast('Please fill in all destinations and dates for each stay.');
      return;
    }
    for (let i = 0; i < multistaySegments.length; i++) {
      const seg = multistaySegments[i];
      const pastDateError = validateDatesNotInPast([
        { label: `Stay ${i + 1}: check-in date`, value: seg?.checkin },
        { label: `Stay ${i + 1}: check-out date`, value: seg?.checkout },
      ]);
      if (pastDateError) {
        showErrorToast(pastDateError);
        return;
      }
    }
    setIsMultistaySearching(true);
    try {
      const resolvedResults = await Promise.allSettled(
        multistaySegments.map((seg) => resolveCity(seg.destination.trim()).unwrap())
      );
      const searchPromises = multistaySegments.map(async (seg, i) => {
        const resolvedEntry = resolvedResults[i];
        if (resolvedEntry?.status === 'rejected') {
          showErrorToast(`Stay ${i + 1} (${seg.destination}): location could not be resolved.`);
        }
        const countryName = resolvedEntry?.status === 'fulfilled'
          ? (resolvedEntry as PromiseFulfilledResult<{ country: string }>).value.country
          : undefined;
        const request: HotelSearchRequest = {
          checkin: seg.checkin!,
          checkout: seg.checkout!,
          cityName: seg.destination.trim(),
          countryName,
          occupancy: seg.rooms.map((r) => ({
            roomNo: r.roomNo,
            adult: r.adult ?? 1,
            child: r.child ?? 0,
            childAge: (r.child ?? 0) > 0 ? (r.childAge ?? [0]).slice(0, r.child!) : [0],
          })),
          nationality: 'US',
        };
        const result = await dispatch(
          hotelsApi.endpoints.searchHotels.initiate(request, { forceRefetch: true })
        ).unwrap();
        dispatch(
          setMultistayLegSearchResults({
            legIndex: i,
            sessionId: result.sessionId ?? '',
            hotels: (result.hotels ?? []) as HotelItinerary[],
          })
        );
        return result;
      });
      const legSearchOutcomes = await Promise.allSettled(searchPromises);
      legSearchOutcomes.forEach((outcome, i) => {
        if (outcome.status === 'rejected') {
          showErrorToast(`Stay ${i + 1} (${multistaySegments[i]?.destination ?? ''}): search failed.`);
        }
      });
      dispatch(setMultistayActiveLegTab(0));
    } catch (err) {
      showErrorToastFromError(err, 'Multi-stay hotel search failed. Please try again.');
    } finally {
      setIsMultistaySearching(false);
    }
  }, [multistaySegments, dispatch, resolveCity]);

  // Header chips: run search when trigger increments (mirrors FlightSearchPage).
  useEffect(() => {
    if (searchTriggerFromChips === prevHotelChipTrigger.current) return;
    prevHotelChipTrigger.current = searchTriggerFromChips;
    if (searchTriggerFromChips === 0) return;
    dispatch(resetSearchTriggerFromChips());
    if (tripType === 'multi-stay') {
      void handleMultistaySearch();
    } else {
      const request = buildHotelSearchRequestFromFormParams(searchFormParams);
      if (!request) return;
      void handleSearch(request);
    }
  }, [searchTriggerFromChips, searchFormParams, handleSearch, handleMultistaySearch, dispatch, tripType]);

  const handleMultistayHotelSelect = useCallback(
    async (hotel: Hotel | HotelItinerary, legIndex: number) => {
      if (onPublicRoute && !ensureAuthenticated('hotel_show_all_book')) return;
      const leg = multistayLegs[legIndex];
      if (!leg?.sessionId) {
        showErrorToast('Missing session. Please search again.');
        return;
      }
      const it = hotel as HotelItinerary;
      const tokenId = hotel.tokenId ?? hotel.id;
      const productId = it.productId ?? '';
      const hotelId = hotel.id;
      setSelectingTokenId(tokenId);
      try {
        const roomRatesResult = await getRoomRates({
          sessionId: leg.sessionId,
          tokenId,
          productId,
          hotelId,
        }).unwrap();
        dispatch(setSelectedHotel({ hotel: it, tokenId, productId: it.productId ?? null, hotelId }));
        dispatch(setRoomRatesResponse(roomRatesResult));
        dispatch(setSessionId(leg.sessionId));
        const seg = multistaySegments[legIndex];
        persistHotelRoomsContext({
          tokenId,
          sessionId: leg.sessionId,
          productId,
          hotelId,
          selectedHotel: it,
          searchFormParams: {
            destination: seg?.destination ?? '',
            checkin: seg?.checkin ?? null,
            checkout: seg?.checkout ?? null,
            rooms: seg?.rooms ?? [],
            nationality: 'US',
          },
        });
        navigate(`/hotels/rooms/${tokenId}?leg=${legIndex}`);
      } catch (err) {
        showErrorToastFromError(err);
      } finally {
        setSelectingTokenId(null);
      }
    },
    [dispatch, navigate, multistayLegs, multistaySegments, getRoomRates, onPublicRoute, ensureAuthenticated]
  );

  const listHotelCount = useMemo(() => {
    const ch = searchResponse?.curatedHotels;
    const curatedIds = new Set<string>();
    if (ch?.bestValue) curatedIds.add(ch.bestValue.tokenId ?? ch.bestValue.id);
    if (ch?.cheapest) curatedIds.add(ch.cheapest.tokenId ?? ch.cheapest.id);
    if (ch?.highestRated) curatedIds.add(ch.highestRated.tokenId ?? ch.highestRated.id);
    return hotelObjects.filter((h) => !curatedIds.has(h.tokenId ?? h.id)).length;
  }, [hotelObjects, searchResponse?.curatedHotels]);
  const listPageCount = Math.max(1, Math.ceil(listHotelCount / HOTELS_PAGE_SIZE));
  const effectiveListPage = Math.max(1, Math.min(resultsPage, listPageCount));

  // Multi-stay: active leg computed hotels
  const activeLegRawHotels = multistayLegs[activeLegTab]?.hotels ?? [];
  const { filteredHotels: activeLegFilteredHotels, hotelObjects: activeLegHotelObjects } = useMemo(() => {
    const filterable = activeLegRawHotels.map(toFilterableHotel);
    const filtered = filterHotels(filterable, filterState);
    const sorted =
      sortBy === 'preference-match'
        ? sortHotelsByPreference(filtered, hotelsPrefs, travelStylePrefs)
        : sortHotels(filtered, sortBy);
    const byTokenId = new Map<string, Hotel | HotelItinerary>(
      activeLegRawHotels.map((h) => [h.tokenId ?? h.id, h])
    );
    const objects = sorted
      .map((f) => byTokenId.get(f.tokenId) ?? byTokenId.get(f.id))
      .filter(Boolean) as (Hotel | HotelItinerary)[];
    return { filteredHotels: sorted, hotelObjects: objects };
  }, [activeLegRawHotels, filterState, sortBy, hotelsPrefs, travelStylePrefs]);

  const multistayMapProps = useMemo((): MapComponentProps | null => {
    const withCoords = activeLegHotelObjects.filter(hasValidCoords);
    if (withCoords.length === 0) return null;
    const markers = withCoords.map((h) => ({ latitude: h.latitude, longitude: h.longitude, label: h.name }));
    const lat = markers.reduce((s, m) => s + m.latitude, 0) / markers.length;
    const lng = markers.reduce((s, m) => s + m.longitude, 0) / markers.length;
    return { centerLatitude: lat, centerLongitude: lng, zoomLevel: markers.length === 1 ? 14 : 11, markers };
  }, [activeLegHotelObjects]);

  const activeLegNights = useMemo(() => {
    const seg = multistaySegments[activeLegTab];
    if (!seg?.checkin || !seg.checkout) return 1;
    const a = new Date(seg.checkin);
    const b = new Date(seg.checkout);
    return Math.max(1, Math.ceil((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24)));
  }, [multistaySegments, activeLegTab]);


  const searchMapPinCount = useMemo(
    () => hotelObjects.filter(hasValidCoords).length,
    [hotelObjects]
  );
  const showSearchMapFab =
    isMdDown &&
    !isMobile &&
    hasSearched &&
    !isLoading &&
    !isSearching &&
    searchMapPinCount > 0;

  useEffect(() => {
    if (!showSearchMapFab) setSearchMapOpen(false);
  }, [showSearchMapFab]);

  const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const mapId = import.meta.env.VITE_GOOGLE_MAPS_MAP_ID as string | undefined;
  const mountSearchMobileMapsProvider = showSearchMapFab && !!mapsApiKey?.trim();

  const showMultistayBottomBar =
    tripType === 'multi-stay' && multistayHasResults && !isMultistaySearching;

  const overlayLoadingStyle: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    zIndex: Z_INDEX_OVERLAY_LOADING,
    backgroundColor: 'var(--mantine-color-body)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const isSingleStayResultsShowing =
    tripType !== 'multi-stay' && (hasSearched || hasReduxCacheHit) && !isLoading && !isSearching && !isMobile;

  const isMultistayResultsShowing =
    tripType === 'multi-stay' && multistayHasResults && !isMultistaySearching && !isMobile;

  const isFullWidthResultsShowing = isSingleStayResultsShowing || isMultistayResultsShowing;

  return (
    <Box
      ref={pageContainerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      <Container
        size="xl"
        px={0}
        pt={0}
        pb={showMultistayBottomBar ? 'sm' : 0}
        style={{
          flex: isFullWidthResultsShowing ? '0 0 auto' : '1 1 auto',
          overflowY: isFullWidthResultsShowing ? undefined : 'auto',
        }}
      >
        {/* Single stay: initial empty state — suppressed when Redux already has valid cached results */}
        {tripType !== 'multi-stay' && !hasSearched && !hasReduxCacheHit && !encodedHotelQ && (
          <Box ta="center" py={64}>
            <Title order={5} c="dimmed" fw={500}>
              Search hotels
            </Title>
            <Text c="dimmed" mt="md">
              Choose destination, dates, and guests in the search bar above to search.
            </Text>
          </Box>
        )}

        {/* Multi-stay: initial empty state */}
        {tripType === 'multi-stay' && !multistayHasResults && !isMultistaySearching && (
          <Box ta="center" py={48}>
            <Title order={5} c="dimmed" fw={500}>
              Add your stays above and search
            </Title>
          </Box>
        )}

        {/* Single stay: loading state — suppressed when Redux already has valid cached results */}
        {tripType !== 'multi-stay' &&
          (isLoading || isSearching || (!!encodedHotelQ && !hasSearched && !hasReduxCacheHit && !error && !resolutionFailed)) && (
            <Group justify="center" align="center" py={64}>
              <Loader />
              <Text c="dimmed">Searching for hotels…</Text>
            </Group>
          )}

        {/* Multi-stay: loading state */}
        {tripType === 'multi-stay' && isMultistaySearching && (
          <Group justify="center" align="center" py={64}>
            <Loader />
            <Text c="dimmed">Searching all stays…</Text>
          </Group>
        )}

        {/* Single stay: error */}
        {tripType !== 'multi-stay' && error && (
          <Box mb="xl">
            <Alert color="red">
              {error && 'data' in error && typeof error.data === 'object' && error.data && 'detail' in error.data
                ? String((error.data as { detail: unknown }).detail)
                : 'Hotel search failed. Please try again.'}
            </Alert>
          </Box>
        )}

      </Container>

      {/* Multi-stay: leg tabs + per-leg results — full-width, mirrors single-stay layout */}
      {isMultistayResultsShowing && (
        <Box
          style={{
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            paddingInline: 8,
          }}
        >
          <Box style={{ flex: '0 0 auto' }}>
            <HotelMultistayLegTabs
              segments={multistaySegments}
              legs={multistayLegs}
              activeLegIndex={activeLegTab}
              onLegChange={(i) => dispatch(setMultistayActiveLegTab(i))}
            />
          </Box>
          <Group
            gap="md"
            align="stretch"
            wrap="nowrap"
            style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}
          >
            {/* Left column: title + scrollable hotel cards */}
            <Box
              style={{
                flex: CONTENT_SPLIT.LIST,
                minWidth: 0,
                minHeight: 0,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Box style={{ flex: '0 0 auto' }}>
                <Title order={5} fw={700} mb="md">
                  {activeLegHotelObjects.length} hotel{activeLegHotelObjects.length !== 1 ? 's' : ''}{' '}
                  in {multistaySegments[activeLegTab]?.destination || `Stay ${activeLegTab + 1}`}
                </Title>
              </Box>
              <Box style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingInline: 8 }}>
                <HotelResults
                  hotels={activeLegFilteredHotels}
                  hotelObjects={activeLegHotelObjects}
                  nights={activeLegNights}
                  onHotelSelect={(hotel) => handleMultistayHotelSelect(hotel, activeLegTab)}
                  selectingTokenId={selectingTokenId}
                  nextToken={null}
                  onLoadMore={undefined}
                  isLoadingMore={false}
                  page={1}
                  pageSize={HOTELS_PAGE_SIZE}
                  onPageChange={() => {}}
                />
              </Box>
            </Box>

            {/* Right column: sort/filter + map */}
            <Box
              visibleFrom="lg"
              style={{
                flex: CONTENT_SPLIT.MAP,
                minWidth: 0,
                minHeight: 0,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <HotelSortAndFiltersHeader
                sortBy={sortBy}
                onSortChange={setSortBy}
                sortMenuItems={getHotelSortMenuItems(false)}
                activeFilterCount={activeFilterCount}
                onFiltersClick={() => setFiltersOpen(true)}
                onChangePreferences={handleChangePreferences}
                mb="sm"
                justify="flex-end"
                style={{ flex: '0 0 auto' }}
              />
              <Box style={{ flex: 1, minHeight: 0, overflow: 'hidden', borderRadius: 8 }}>
                {multistayMapProps ? (
                  <MapComponent {...multistayMapProps} />
                ) : (
                  <Box
                    style={{
                      height: '100%',
                      background: 'var(--mantine-color-gray-1)',
                      borderRadius: 8,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Text size="sm" c="dimmed">Map unavailable</Text>
                  </Box>
                )}
              </Box>
            </Box>
          </Group>
        </Box>
      )}

      {/* Single stay: results — desktop/tablet two-column layout (mobile uses HotelsMobileSheetView below) */}
      {isSingleStayResultsShowing && (
        <Group
          gap="md"
          align="stretch"
          wrap="nowrap"
          style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}
        >
          {/* Left column: label + scrollable hotel cards */}
          <Box
            style={{
              flex: CONTENT_SPLIT.LIST,
              minWidth: 0,
              minHeight: 0,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header — does not scroll */}
            <Box style={{ flex: '0 0 auto' }}>
              <Group justify="space-between" align="flex-start" gap="md" mb="md" wrap="wrap">
                <Title order={5} fw={700} m={0} style={{ lineHeight: 1.3 }}>
                  {listHotelCount} hotel{listHotelCount !== 1 ? 's' : ''}
                  {listPageCount > 1 && (
                    <Text
                      component="span"
                      size="md"
                      c="dimmed"
                      ml="xs"
                      style={{ fontWeight: 500 }}
                    >
                      · page {effectiveListPage} of {listPageCount}
                    </Text>
                  )}
                </Title>
                {/* Mobile/tablet: sort + filter inline — right column hidden below lg */}
                <HotelSortAndFiltersHeader
                  sortBy={sortBy}
                  onSortChange={setSortBy}
                  sortMenuItems={getHotelSortMenuItems(Boolean(nearbyLocation))}
                  activeFilterCount={activeFilterCount}
                  onFiltersClick={() => setFiltersOpen(true)}
                  onChangePreferences={handleChangePreferences}
                  align="center"
                  style={{ flexShrink: 0 }}
                  hiddenFrom="lg"
                  selectMinWidth={180}
                />
              </Group>
            </Box>
            {/* Scrollable hotel cards */}
            <Box style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingInline: 8 }}>
              <HotelResults
                hotels={filteredHotels}
                hotelObjects={hotelObjects}
                nights={nights}
                onHotelSelect={handleHotelSelect}
                selectingTokenId={selectingTokenId}
                curatedHotels={searchResponse?.curatedHotels}
                nextToken={nextToken}
                onLoadMore={handleLoadMore}
                isLoadingMore={isLoadingMore}
                page={resultsPage}
                pageSize={HOTELS_PAGE_SIZE}
                onPageChange={setResultsPage}
                highlightedKey={selectedDesktopPinKey}
                onCardRef={(key, el) => {
                  if (el) {
                    desktopCardElRefs.current.set(key, el);
                    if (pendingScrollKey.current === key) {
                      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                      pendingScrollKey.current = null;
                    }
                  } else {
                    desktopCardElRefs.current.delete(key);
                  }
                }}
              />
            </Box>
          </Box>

          {/* Right column: sort/filter + map — desktop only */}
          <Box
            visibleFrom="lg"
            style={{
              flex: CONTENT_SPLIT.MAP,
              minWidth: 0,
              minHeight: 0,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <HotelSortAndFiltersHeader
              sortBy={sortBy}
              onSortChange={setSortBy}
              sortMenuItems={getHotelSortMenuItems(Boolean(nearbyLocation))}
              activeFilterCount={activeFilterCount}
              onFiltersClick={() => setFiltersOpen(true)}
              onChangePreferences={handleChangePreferences}
              mb="sm"
              justify="flex-end"
              style={{ flex: '0 0 auto' }}
            />
            {/* Map fills remaining height */}
            <Box style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
              {mapsApiKey?.trim() && desktopMapHotels.length > 0 ? (
                <APIProvider apiKey={mapsApiKey}>
                  <HotelsMobileMap
                    mapId={mapId}
                    hotels={desktopMapHotels}
                    nights={nights}
                    selectedId={selectedDesktopPinKey}
                    onPinClick={(hotel) => {
                      const key = getHotelKey(hotel);
                      setSelectedDesktopPinKey((prev) => (prev === key ? null : key));
                    }}
                    onMapClick={() => setSelectedDesktopPinKey(null)}
                  />
                </APIProvider>
              ) : mapsApiKey?.trim() && cityPinMapProps ? (
                <APIProvider apiKey={mapsApiKey}>
                  <MapComponent {...cityPinMapProps} />
                </APIProvider>
              ) : (
                <Box
                  style={{
                    height: '100%',
                    background: 'var(--mantine-color-gray-1)',
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Text size="sm" c="dimmed">Map unavailable</Text>
                </Box>
              )}
            </Box>
          </Box>
        </Group>
      )}

      {/* Mobile Airbnb-style map + sheet (position: fixed, replaces list on phones) */}
      {tripType !== 'multi-stay' && (hasSearched || hasReduxCacheHit) && !isLoading && !isSearching && isMobile && !error && (
        <HotelsMobileSheetView
          hotels={hotelObjects}
          nights={nights}
          selectingTokenId={selectingTokenId}
          onHotelSelect={handleHotelSelect}
          onOpenFilters={() => setFiltersOpen(true)}
          activeFilterCount={activeFilterCount}
          sortBy={sortBy}
          onSortChange={setSortBy}
          sortMenuItems={getHotelSortMenuItems(Boolean(nearbyLocation))}
          onChangePreferences={handleChangePreferences}
          topOffset={sheetTopOffset}
        />
      )}

      {/* Filters dialog — all screen sizes */}
      <HotelFiltersDialog
        opened={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        filterState={filterState}
        onFilterChange={(next) => dispatch(setHotelFilters(next))}
        allHotels={accumulatedHotels.map(toFilterableHotel)}
        filteredHotelCount={filteredHotels.length}
      />

      {showSearchMapFab && (
        <Button
          ref={searchMapFabRef}
          radius={9999}
          size="md"
          onClick={() => setSearchMapOpen(true)}
          aria-label="Open map view"
          leftSection={<MapIcon size={18} />}
          style={{
            position: 'fixed',
            bottom: 'calc(24px + env(safe-area-inset-bottom))',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: Z_INDEX_SEARCH_MAP_FAB,
          }}
        >
          Map
        </Button>
      )}

      {/* Mobile search map — lazy loaded; single APIProvider while FAB is shown (avoids SDK reload on each overlay open). */}
      {mountSearchMobileMapsProvider && (
        <APIProvider apiKey={mapsApiKey!}>
          {searchMapOpen && (
            <Suspense
              fallback={
                <Box style={overlayLoadingStyle}>
                  <Loader />
                </Box>
              }
            >
              <HotelSearchMobileMapOverlay
                hotels={hotelObjects}
                nights={nights}
                rooms={searchFormParams.rooms?.length ?? 1}
                onSelectHotel={handleHotelSelect}
                selectingTokenId={selectingTokenId}
                onClose={() => setSearchMapOpen(false)}
                returnFocusRef={searchMapFabRef}
              />
            </Suspense>
          )}
        </APIProvider>
      )}

      {!mountSearchMobileMapsProvider && searchMapOpen && showSearchMapFab && (
        <Suspense
          fallback={
            <Box style={overlayLoadingStyle}>
              <Loader />
            </Box>
          }
        >
          <HotelSearchMobileMapOverlay
            hotels={hotelObjects}
            nights={nights}
            rooms={searchFormParams.rooms?.length ?? 1}
            onSelectHotel={handleHotelSelect}
            selectingTokenId={selectingTokenId}
            onClose={() => setSearchMapOpen(false)}
            returnFocusRef={searchMapFabRef}
          />
        </Suspense>
      )}

      {showMultistayBottomBar && (
        <HotelMultistayBottomBar
          segments={multistaySegments}
          legs={multistayLegs}
          onProceedToReview={() => navigate(`${routePrefix}/hotels/review-booking`)}
        />
      )}
    </Box>
  );
}
