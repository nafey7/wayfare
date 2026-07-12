import { useState, useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { flightsApi } from '@/api/flightsApi';
import { setSearchFormParams } from '@/store/slices/flightBookingSlice';
import { convertUIToFormParams } from '../utils/urlParams';
import type { FlightSearchParamsUI } from '@/types/flights';

const isIataCode = (v: string) => /^[A-Z]{2,4}$/i.test(v.trim());

/**
 * Pick the best airport match for a city name query.
 * Groups by country and picks the country with the most airports (major hub).
 * e.g. "London" → London GB (6 airports) wins over London CA (1).
 * Fallback only — used when backend doesn't provide IATA codes.
 */
function pickBestAirport(
  airports: Array<{ iata: string; city: string; country: string }>,
  query: string,
): string | null {
  const queryLower = query.toLowerCase();
  const matching = airports.filter((a) => a.city.toLowerCase() === queryLower);
  if (!matching.length) return null;

  // Pick country with most airports (largest city hub)
  const countByCountry = new Map<string, number>();
  for (const a of matching) {
    countByCountry.set(a.country, (countByCountry.get(a.country) ?? 0) + 1);
  }
  const topCountry = [...countByCountry.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  return matching.find((a) => a.country === topCountry)?.iata ?? matching[0]?.iata ?? null;
}

/**
 * Resolves city names in search params to IATA codes for the FlightLogic API.
 *
 * When coming from chat, from/to may contain city names (e.g. "London").
 * If the backend provided originIata/destinationIata, those are used directly
 * (they come from the backend's airport resolver which has priority mappings).
 * Otherwise falls back to the airport search API with pickBestAirport heuristic.
 *
 * Also syncs Redux form state (keeps original city names for search bar display).
 */
export function useResolvedSearchParams(
  restoredParams: FlightSearchParamsUI | null,
): FlightSearchParamsUI | null {
  const dispatch = useAppDispatch();
  const [resolvedParams, setResolvedParams] = useState<FlightSearchParamsUI | null>(null);

  useEffect(() => {
    if (!restoredParams) {
      setResolvedParams(null);
      return;
    }

    const needsOrigin = !isIataCode(restoredParams.from);
    const needsDest = !isIataCode(restoredParams.to);

    if (!needsOrigin && !needsDest) {
      setResolvedParams(restoredParams);
      dispatch(setSearchFormParams(convertUIToFormParams(restoredParams)));
      return;
    }

    // Use backend-provided IATA codes when available (accurate, from airport resolver)
    const hasBackendCodes =
      (needsOrigin ? !!restoredParams.originIata : true) &&
      (needsDest ? !!restoredParams.destinationIata : true);

    if (hasBackendCodes) {
      const resolved: FlightSearchParamsUI = {
        ...restoredParams,
        from: needsOrigin ? restoredParams.originIata! : restoredParams.from,
        to: needsDest ? restoredParams.destinationIata! : restoredParams.to,
      };
      setResolvedParams(resolved);
      dispatch(setSearchFormParams(convertUIToFormParams(restoredParams)));
      return;
    }

    // Fallback: resolve via airport search API (for old URLs without IATA codes)
    let cancelled = false;

    const resolveCode = async (query: string) => {
      const result = await dispatch(
        flightsApi.endpoints.searchAirports.initiate({ query, limit: 50 }),
      );
      return pickBestAirport(result.data ?? [], query);
    };

    const resolve = async () => {
      const from = needsOrigin ? (await resolveCode(restoredParams.from)) ?? restoredParams.from : restoredParams.from;
      if (cancelled) return;
      const to = needsDest ? (await resolveCode(restoredParams.to)) ?? restoredParams.to : restoredParams.to;
      if (cancelled) return;

      setResolvedParams({ ...restoredParams, from, to });
      dispatch(setSearchFormParams(convertUIToFormParams(restoredParams)));
    };

    resolve();
    return () => { cancelled = true; };
  }, [restoredParams, dispatch]);

  return resolvedParams;
}
