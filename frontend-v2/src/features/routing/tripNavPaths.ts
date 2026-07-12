import { ROUTES } from './constants';

/**
 * Itinerary / Flights / Hotels targets for the top trip nav.
 * Pre-signup (guest) surfaces use `/public/chat/...` content routes; authenticated
 * users use the same paths as the logged-in app shell.
 *
 * Flights and hotels both route to `/search` — chat / itinerary side-search
 * results are stored in the in-memory result caches (`cachedFlightResults`,
 * `cachedHotelResults`), which FlightSearchPage / HotelSearchPage read directly
 * via their URL-restoration cache-hit branches.
 */
export function getTripNavPaths(usePublicContentPaths: boolean) {
  if (usePublicContentPaths) {
    return {
      itinerary: ROUTES.PUBLIC_CHAT_ITINERARY,
      flights: ROUTES.PUBLIC_CHAT_FLIGHTS_SEARCH,
      hotels: ROUTES.PUBLIC_CHAT_HOTELS_SEARCH,
    };
  }
  return {
    itinerary: ROUTES.ITINERARY,
    flights: ROUTES.FLIGHTS_SEARCH,
    hotels: ROUTES.HOTELS_SEARCH,
  };
}
