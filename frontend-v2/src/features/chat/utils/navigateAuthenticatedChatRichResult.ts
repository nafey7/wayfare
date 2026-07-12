import type { NavigateFunction } from 'react-router-dom';

import type { AppDispatch } from '@/store';
import type { ChatResponse } from '@/types/chat';
import {
  extractFlightSearchResults,
  extractFlightDateRangeResults,
  dateRangeToFlightSearchData,
  extractHotelSearchResults,
} from '@/types/api.helpers';
import { extractMulticityFlightSearchResults } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import {
  ROUTES,
  isPublicChatContentRoute,
  isPublicChatRoute,
} from '@/features/routing';
import { trackEvent } from '@/utils/gtm';
import { navigateItineraryFromChatExtraData } from '@/features/chat/utils/itineraryNavigateFromChatExtraData';

const RICH_RESULT_TYPES = new Set([
  'flight_search_results',
  'multicity_flight_search_results',
  'flight_date_range_results',
  'hotel_search_results',
  'itinerary_results',
]);

/** Last rich payload wins (matches last hydrate in applySuccessfulChatResponse chain loop). */
export function lastRichNavigationPayload(
  response: ChatResponse
): { type: string; payload: unknown } | null {
  // When the main response is itinerary_results, chain responses are supplementary
  // (they pre-populate the Flights/Stays tabs). Navigation should always go to the
  // itinerary page — never to a sub-page driven by a chain response.
  if (response.type === 'itinerary_results') {
    return { type: 'itinerary_results', payload: response.data };
  }

  const rootData = response.data as Record<string, unknown> | undefined;
  const chain = rootData?.chain_responses as Array<Record<string, unknown>> | undefined;

  if (chain && chain.length > 1) {
    let last: { type: string; payload: unknown } | null = null;
    for (const chainResp of chain) {
      const t = chainResp.type as string;
      if (RICH_RESULT_TYPES.has(t)) {
        const payload = { ...chainResp } as Record<string, unknown>;
        delete payload.type;
        delete payload.message;
        last = { type: t, payload };
      }
    }
    return last;
  }

  const t = response.type;
  if (t && RICH_RESULT_TYPES.has(t)) {
    return { type: t, payload: response.data };
  }
  return null;
}

/** `/chat` and `/chat/:id` only — not `/public/chat` (guest uses {@link isPublicChatRoute} + {@link isPublicChatContentRoute} below). */
function isAuthenticatedChatPage(pathname: string): boolean {
  return pathname === ROUTES.CHAT || pathname.startsWith(`${ROUTES.CHAT}/`);
}

/**
 * On `/chat` (authenticated) or `/public/chat` (guest): auto-navigate to the content page
 * matching the rich result type. No-op on content sub-routes or unrelated routes.
 *
 * Kept as `navigateAuthenticatedChatRichResultIfApplicable` for backward-compat with callers;
 * now also handles unauthenticated public chat.
 */
export function navigateAuthenticatedChatRichResultIfApplicable(
  dispatch: AppDispatch,
  navigate: NavigateFunction,
  pathname: string,
  isAuthenticated: boolean,
  response: ChatResponse,
  chatId: string | null = null
): void {
  const onAuthChat = isAuthenticated && isAuthenticatedChatPage(pathname);
  const onPublicChat =
    !isAuthenticated &&
    isPublicChatRoute(pathname) &&
    !isPublicChatContentRoute(pathname);
  if (!onAuthChat && !onPublicChat) return;

  const rich = lastRichNavigationPayload(response);
  if (!rich) return;

  const { type, payload } = rich;
  const routePrefix = onPublicChat ? ROUTES.PUBLIC_CHAT : '';

  switch (type) {
    case 'flight_search_results': {
      const extracted = extractFlightSearchResults(payload);
      if (!extracted) return;
      trackEvent('chat_rich_result_auto_navigate', { result_type: type, public: onPublicChat });
      navigate(`${routePrefix}${ROUTES.FLIGHTS_SEARCH}`, {
        state: { fromChat: true },
      });
      return;
    }
    case 'multicity_flight_search_results': {
      const normalized = extractMulticityFlightSearchResults(payload);
      if (!normalized) return;
      trackEvent('chat_rich_result_auto_navigate', { result_type: type, public: onPublicChat });
      navigate(`${routePrefix}${ROUTES.FLIGHTS_SEARCH}`, {
        state: { fromChat: true },
      });
      return;
    }
    case 'flight_date_range_results': {
      const dateRange = extractFlightDateRangeResults(payload);
      if (!dateRange) return;
      const extracted = dateRangeToFlightSearchData(dateRange);
      if (!extracted) return;
      trackEvent('chat_rich_result_auto_navigate', { result_type: type, public: onPublicChat });
      navigate(`${routePrefix}${ROUTES.FLIGHTS_SEARCH}`, {
        state: { fromChat: true },
      });
      return;
    }
    case 'hotel_search_results': {
      const extracted = extractHotelSearchResults(payload);
      if (!extracted) return;
      trackEvent('chat_rich_result_auto_navigate', { result_type: type, public: onPublicChat });
      navigate(`${routePrefix}${ROUTES.HOTELS_SEARCH}`, {
        state: { fromChat: true },
      });
      return;
    }
    case 'itinerary_results': {
      trackEvent('chat_rich_result_auto_navigate', { result_type: type, public: onPublicChat });
      // Skip flat flight hydration when multicity chain responses already set per-leg results.
      const chainArr = (payload as Record<string, unknown> | undefined)?.chain_responses as
        | Array<Record<string, unknown>>
        | undefined;
      const hasMulticityChain =
        Array.isArray(chainArr) && chainArr.some((cr) => cr.type === 'multicity_flight_search_results');
      const hasMultistayChain =
        Array.isArray(chainArr) && chainArr.some((cr) => cr.type === 'multistay_hotel_search_results');
      navigateItineraryFromChatExtraData(
        dispatch,
        navigate,
        payload as Record<string, unknown> | undefined,
        routePrefix,
        chatId,
        { skipFlightHydration: hasMulticityChain, skipHotelHydration: hasMultistayChain }
      );
      return;
    }
    default:
      return;
  }
}
