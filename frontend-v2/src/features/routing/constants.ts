/**
 * App route path constants and pathname helpers.
 * Use these instead of hardcoded strings to keep routing consistent.
 */

/** React Router `path` prop is relative to the parent; strip a leading `/` from `ROUTES.*`. */
export function toRelativePath(route: string): string {
  if (!route.startsWith('/')) {
    return route;
  }
  return route.slice(1);
}

export const ROUTES = {
  CHAT: '/chat',
  /** Full-page guest chat (JWT not required); feature-flagged via `public_chat_enabled`. */
  PUBLIC_CHAT: '/public/chat',
  PUBLIC_CHAT_ITINERARY: '/public/chat/itinerary',
  PUBLIC_CHAT_FLIGHTS_SEARCH: '/public/chat/flights/search',
  PUBLIC_CHAT_HOTELS_SEARCH: '/public/chat/hotels/search',
  /** Email link: set password after registering (PublicRoute, CompleteRegistrationPage). */
  COMPLETE_REGISTRATION: '/complete-registration',
  HOME: '/home',
  PROFILE: '/profile',
  ITINERARY: '/itinerary',
  ITINERARIES: '/itineraries',
  ITINERARY_VIEW: '/itinerary/:id',
  ITINERARY_SAVED_VIEW: '/itineraries/:id',
  FLIGHTS: '/flights',
  FLIGHTS_SEARCH: '/flights/search',
  HOTELS: '/hotels',
  HOTELS_SEARCH: '/hotels/search',
  /** Campaign landing page by slug, e.g. `/l/business-travel`. */
  CAMPAIGN: '/l',
  /** Admin: G2A / voucher batch management (LayoutNoChat). */
  ADMIN_DISCOUNTS: '/admin/discounts',
  /** Admin: booking management (LayoutNoChat). */
  ADMIN_BOOKINGS: '/admin/bookings',
  /** Pre-signup onboarding wizard entry point (redirects to correct step). */
  ONBOARDING: '/onboarding',
  ONBOARDING_WELCOME: '/onboarding/welcome',
  ONBOARDING_LOCATION: '/onboarding/location',
  ONBOARDING_TRIP: '/onboarding/trip',
} as const;

/** Admin discount batch detail by `batch_id` (UUID). */
export function adminDiscountBatchDetailPath(batchId: string): string {
  return `${ROUTES.ADMIN_DISCOUNTS}/${encodeURIComponent(batchId)}`;
}

/** Build path to view itinerary in chat layout (from chat flow). */
export function itineraryView(id: string): string {
  return `/itinerary/${id}`;
}

/** Build path to view saved itinerary without chat (from /itineraries list). */
export function itinerarySavedView(id: string): string {
  return `/itineraries/${id}`;
}

/** Linked flight bookings picker for a saved itinerary (no sidebar). */
export function itinerarySavedFlightBookingsList(id: string): string {
  return `/itineraries/${id}/bookings/flights`;
}

/** Linked hotel bookings picker for a saved itinerary (no sidebar). */
export function itinerarySavedHotelBookingsList(id: string): string {
  return `/itineraries/${id}/bookings/hotels`;
}

/** Linked flight bookings picker with chat layout. */
export function itineraryChatFlightBookingsList(id: string): string {
  return `/itinerary/${id}/bookings/flights`;
}

/** Linked hotel bookings picker with chat layout. */
export function itineraryChatHotelBookingsList(id: string): string {
  return `/itinerary/${id}/bookings/hotels`;
}

/** Build a campaign landing page path, e.g. `/l/business-travel`. */
export function campaignPath(slug: string): string {
  return `${ROUTES.CAMPAIGN}/${encodeURIComponent(slug)}`;
}

/** Flight booking detail by VOYA reference. */
export function flightBookingDetail(ref: string): string {
  return `/flights/bookings/${encodeURIComponent(ref)}`;
}

/** Hotel booking detail by VOYA reference. */
export function hotelBookingDetail(ref: string): string {
  return `/hotels/bookings/${encodeURIComponent(ref)}`;
}

/** Reserved `:fareSourceCode` path segment for multi-city trip summary (not a supplier fare token). */
export const FLIGHT_DETAILS_MULTICITY_SEGMENT = 'multicity' as const;

export function flightDetailsPath(fareSourceCode: string): string {
  return `${ROUTES.FLIGHTS}/details/${encodeURIComponent(fareSourceCode)}`;
}


/**
 * Returns true if pathname is the chat route or a chat subroute (e.g. /chat/:id).
 */
export function isChatRoute(pathname: string): boolean {
  return pathname === ROUTES.CHAT || pathname.startsWith(`${ROUTES.CHAT}/`);
}

/**
 * Returns true for the public full-page chat route (and any subpaths).
 */
export function isPublicChatRoute(pathname: string): boolean {
  return (
    pathname === ROUTES.PUBLIC_CHAT || pathname.startsWith(`${ROUTES.PUBLIC_CHAT}/`)
  );
}

/**
 * Routes where guest public chat is actually mounted and Redux messages reflect that thread.
 * Do not use for transcript persistence on other public routes (e.g. `/complete-registration`),
 * or a fresh welcome-only state will overwrite a saved transcript in localStorage.
 *
 * Includes `/` (landing): public chat transcript is also rendered there, not only under `/public/chat`.
 */
export function isGuestPublicChatTranscriptRoute(pathname: string): boolean {
  return pathname === '/' || isPublicChatRoute(pathname);
}

/**
 * Returns true if pathname is an itinerary, flights, or hotels route (2-column layout with chat).
 * Excludes /itineraries and /itineraries/:id (saved list view – no chat).
 */
export function isTwoColumnRoute(pathname: string): boolean {
  const isItineraryWithChat =
    pathname === ROUTES.ITINERARY || pathname.startsWith(`${ROUTES.ITINERARY}/`);
  return (
    isItineraryWithChat ||
    pathname.startsWith(ROUTES.FLIGHTS) ||
    pathname.startsWith(ROUTES.HOTELS)
  );
}

const PUBLIC_CHAT_PREFIX = ROUTES.PUBLIC_CHAT;

/**
 * True for any route under `/public/chat/` that is NOT exactly `/public/chat`
 * (i.e. the content sub-routes like itinerary, flights, hotels).
 */
export function isPublicChatContentRoute(pathname: string): boolean {
  return pathname.startsWith(`${PUBLIC_CHAT_PREFIX}/`) && pathname !== PUBLIC_CHAT_PREFIX;
}

/**
 * Strip `/public/chat` prefix → authenticated equivalent.
 * `/public/chat/flights/search` → `/flights/search`
 *
 * When `pathname` is exactly `/public/chat`, `rest` is `''` and this returns
 * {@link ROUTES.CHAT}: the authenticated shell for the same full-page chat surface.
 * Content handoffs use {@link isPublicChatContentRoute} and never rely on this bare
 * case; the `rest || ROUTES.CHAT` branch exists so prefix stripping always yields a
 * valid in-app path if called with the root public-chat URL.
 */
export function publicToAuthRoute(pathname: string): string {
  if (pathname.startsWith(PUBLIC_CHAT_PREFIX)) {
    const rest = pathname.slice(PUBLIC_CHAT_PREFIX.length);
    return rest || ROUTES.CHAT;
  }
  return pathname;
}

/**
 * Prepend `/public/chat` prefix to an authenticated path.
 * `/flights/search` → `/public/chat/flights/search`
 */
export function authToPublicRoute(pathname: string): string {
  return `${PUBLIC_CHAT_PREFIX}${pathname}`;
}

/**
 * Determine the content domain from pathname regardless of `/public/chat` prefix.
 * Returns `'flights' | 'hotels' | 'itinerary' | null`.
 */
export function getContentDomain(
  pathname: string,
): 'flights' | 'hotels' | 'itinerary' | null {
  const stripped = pathname.startsWith(PUBLIC_CHAT_PREFIX)
    ? pathname.slice(PUBLIC_CHAT_PREFIX.length)
    : pathname;
  if (stripped.startsWith('/flights')) return 'flights';
  if (stripped.startsWith('/hotels')) return 'hotels';
  if (stripped.startsWith('/itinerary')) return 'itinerary';
  return null;
}

/**
 * Returns the route prefix for content navigation:
 * `'/public/chat'` on public chat routes, `''` on authenticated routes.
 */
export function getContentRoutePrefix(pathname: string): string {
  return isPublicChatRoute(pathname) ? PUBLIC_CHAT_PREFIX : '';
}
