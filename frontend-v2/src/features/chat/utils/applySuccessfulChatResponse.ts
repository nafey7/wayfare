import type { NavigateFunction } from 'react-router-dom';

import type { AppDispatch } from '@/store';
import {
  addMessage,
  removeTypingIndicator,
  setChatId,
  updateConversationName,
  updateConversationOnMessage,
} from '@/store/slices/chatSlice';
import {
  incrementUnreadCount,
  setPlacesSessionToken,
  setTripMeta,
} from '@/store/slices/uiSlice';
import { syncItineraryToSearchParams } from '@/store/thunks/syncItineraryToSearchParams';
import type { ChatMessage, ChatMessageContent, ChatResponse } from '@/types/chat';
import { trackEvent } from '@/utils/gtm';
import { setPublicChatId } from '@/features/chat/utils/publicChatSession';
import {
  hydrateFlightSearchResultsFromPayload,
  hydrateMulticityFlightSearchResultsFromPayload,
  hydrateFlightDateRangeFromPayload,
} from '@/features/chat/utils/hydrateFlightRecommendationsFromChatResponse';
import {
  hydrateHotelSearchResultsFromPayload,
  hydrateMultistayHotelSearchResultsFromPayload,
} from '@/features/chat/utils/hydrateHotelRecommendationsFromChatResponse';
import { commitItineraryRichResultToUiState } from '@/features/chat/utils/itineraryNavigateFromChatExtraData';
import { navigateAuthenticatedChatRichResultIfApplicable } from '@/features/chat/utils/navigateAuthenticatedChatRichResult';
import { ROUTES, isPublicChatRoute } from '@/features/routing/constants';

function itineraryRoutePrefix(pathname: string): string {
  return isPublicChatRoute(pathname) ? ROUTES.PUBLIC_CHAT : '';
}

function mapJourneyTypeToTripType(journeyType?: string): 'one_way' | 'round_trip' | undefined {
  if (journeyType === 'OneWay') return 'one_way';
  if (journeyType === 'Return') return 'round_trip';
  return undefined;
}

export type CreateBotMessageFn = (
  text: string,
  messageId?: string,
  type?: string,
  extraData?: Record<string, unknown>,
  content?: Partial<ChatMessageContent>
) => ChatMessage;

export interface ApplySuccessfulChatResponseDeps {
  dispatch: AppDispatch;
  navigate: NavigateFunction;
  /** Used so auto-redirect runs on `/chat` (authenticated) and `/public/chat` (guest), not other routes. */
  pathname: string;
  chatId: string | null;
  isAuthenticated: boolean;
  /** Fresh read at response time (e.g. from store.getState()); avoids stale closure if chat toggled during request. */
  getChatPanelOpen: () => boolean;
  /** Fresh read of all current chat messages at response time; used to derive user_message_index for analytics. */
  getMessages: () => ChatMessage[];
  playSound: () => void;
  setIsTyping: (v: boolean) => void;
  createBotMessage: CreateBotMessageFn;
  /**
   * When false, skips auto-navigation to recommendations/itinerary pages after rich results.
   * Set to false on viewports below `md` so users stay on `/chat` and see inline cards instead.
   * Defaults to true (preserves existing desktop behavior).
   */
  allowRichResultAutoNavigation?: boolean;
}

/**
 * Handles a successful chat API response: messages, trip meta, analytics, sound, unread.
 * On `/chat` (authenticated) and `/public/chat` (guest), rich results auto-navigate to the
 * same content pages as the View flights / hotels / itinerary CTAs.
 */
export function applySuccessfulChatResponse(
  deps: ApplySuccessfulChatResponseDeps,
  response: ChatResponse,
  message: string,
  options: { persistGuestChatId: boolean }
): void {
  const {
    dispatch,
    navigate,
    pathname,
    chatId,
    isAuthenticated,
    getChatPanelOpen,
    getMessages,
    playSound,
    setIsTyping,
    createBotMessage,
    allowRichResultAutoNavigation = true,
  } = deps;

  // Use the response's chat_id when available (new chat — deps.chatId is null until
  // the first response arrives). Falls back to deps.chatId for follow-up messages.
  const effectiveChatId = response.chat_id ?? chatId;

  dispatch(removeTypingIndicator());
  setIsTyping(false);

  const pst = response.places_session_token;
  if (typeof pst === 'string' && pst.trim()) {
    dispatch(setPlacesSessionToken(pst.trim()));
  }

  if (response.chat_id) {
    dispatch(setChatId(response.chat_id));
    if (options.persistGuestChatId) {
      setPublicChatId(response.chat_id);
    }

    // Update conversation sidebar metadata
    if (isAuthenticated) {
      dispatch(
        updateConversationOnMessage({
          chatId: response.chat_id,
          preview: message,
        })
      );

      // Auto-naming: backend sends conversation_name on first message
      const conversationName = (response.data as Record<string, unknown> | undefined)
        ?.conversation_name as string | undefined;
      if (conversationName) {
        dispatch(
          updateConversationName({ chatId: response.chat_id, name: conversationName })
        );
      }
    }
  }

  const userMessageIndex = getMessages().filter((m) => m.from === 'user').length;

  trackEvent('chat_message_sent', {
    chat_id: response.chat_id ?? chatId ?? null,
    is_authenticated: !!isAuthenticated,
    message_length: message.length,
    user_message_index: userMessageIndex,
  });

  // Issue #1034 debug: log what we received from the backend so we can verify
  // the artifact-split payload shape (flat flights[] / hotels[] at top level,
  // no `categories` in data.data). Browser console; remove after rollout.
  try {
    const data = (response.data ?? {}) as Record<string, unknown>;
    const inner = data.data as Record<string, unknown> | undefined;
    const flights = data.flights as unknown[] | undefined;
    const hotels = data.hotels as unknown[] | undefined;
    const multicityLegs = inner?.multicity_legs as unknown[] | undefined;
    const dates = inner?.dates as unknown[] | undefined;

    console.info('[chat:incoming]', {
      type: response.type,
      chat_id: response.chat_id,
      msg_len: (response.message ?? '').length,
      data_bytes: data ? JSON.stringify(data).length : 0,
      flights: Array.isArray(flights) ? flights.length : null,
      hotels: Array.isArray(hotels) ? hotels.length : null,
      multicity_legs: Array.isArray(multicityLegs) ? multicityLegs.length : null,
      date_range_dates: Array.isArray(dates) ? dates.length : null,
      inner_has_categories: !!inner?.categories,
    });
  } catch {
    // swallow logging errors
  }

  const chainResponses = (response.data as Record<string, unknown>)?.chain_responses as
    | Array<Record<string, unknown>>
    | undefined;

  let hadMulticityChain = false;
  let hadMultistayChain = false;

  // When the main response is itinerary_results, chain responses are supplementary
  // (they pre-populate Flights/Stays tabs silently). Don't add them as chat bubbles.
  const isItineraryMainResponse = response.type === 'itinerary_results';

  // Itinerary chains (>= 1): supplementary data that pre-populates tabs silently.
  // Non-itinerary chains (> 1): multi-agent results (e.g. "book everything") each shown as a bubble.
  const hasChains = chainResponses && chainResponses.length > 0;
  const processChains = hasChains && (isItineraryMainResponse || chainResponses!.length > 1);

  if (processChains) {
    // For itinerary_results: add the main bot message first, then process chains silently.
    if (isItineraryMainResponse) {
      const mainMsg = createBotMessage(
        response.message,
        response.message_id,
        response.type,
        response.data
      );
      dispatch(addMessage(mainMsg));
    }

    for (const chainResp of chainResponses!) {
      const { type: crType, message: crMessage, ...crData } = chainResp;

      const internalTypes = ['hand_back', 'hand_back_to_supervisor'];
      if (internalTypes.includes(crType as string)) continue;

      if (!isItineraryMainResponse) {
        const chainMsg = createBotMessage(
          (crMessage as string) || '',
          undefined,
          (crType as string) || 'message',
          crData
        );
        dispatch(addMessage(chainMsg));
      }

      if (crType === 'flight_search_results') {
        hydrateFlightSearchResultsFromPayload(dispatch, crData);
      }
      if (crType === 'multicity_flight_search_results') {
        hydrateMulticityFlightSearchResultsFromPayload(dispatch, crData, effectiveChatId);
        hadMulticityChain = true;
      }
      if (crType === 'flight_date_range_results') {
        hydrateFlightDateRangeFromPayload(dispatch, crData);
      }
      if (crType === 'hotel_search_results') {
        hydrateHotelSearchResultsFromPayload(dispatch, crData);
      }
      if (crType === 'multistay_hotel_search_results') {
        hydrateMultistayHotelSearchResultsFromPayload(dispatch, crData);
        hadMultistayChain = true;
      }
      if (crType === 'itinerary_results') {
        commitItineraryRichResultToUiState(
          dispatch,
          crData as Record<string, unknown>,
          itineraryRoutePrefix(pathname),
          effectiveChatId
        );
      }
    }
  } else {
    const botMessage = createBotMessage(
      response.message,
      response.message_id,
      response.type,
      response.data
    );
    dispatch(addMessage(botMessage));
  }

  if (response.type === 'flight_search_results' && response.data) {
    hydrateFlightSearchResultsFromPayload(dispatch, response.data);
  }

  if (response.type === 'multicity_flight_search_results' && response.data) {
    hydrateMulticityFlightSearchResultsFromPayload(dispatch, response.data, chatId);
  }

  if (response.type === 'flight_date_range_results' && response.data) {
    hydrateFlightDateRangeFromPayload(dispatch, response.data);
  }

  if (response.type === 'itinerary_results' && response.data) {
    const data = response.data as Record<string, unknown>;
    const adults = data.adults as number | undefined;
    const children = data.children as number | undefined;
    const infants = data.infants as number | undefined;
    // Use destination_hub_list to reliably detect multi-city country destinations —
    // more robust than relying on trip_type flowing through all response layers.
    const hubList = data.destination_hub_list as unknown[] | undefined;
    const isMultiHubCountry = Array.isArray(hubList) && hubList.length > 1;
    const tripType = isMultiHubCountry
      ? ('multi_city' as const)
      : (data.trip_type as 'round_trip' | 'one_way' | undefined);
    // Itinerary's flight_search_params is the richest source of cabin_class;
    // fall back to top-level cabin_class on older payload shapes.
    const flightSearchParams =
      (data.flight_search_params as Record<string, unknown> | undefined) ?? {};
    const cabinClass =
      (flightSearchParams.cabin_class as string | undefined) ??
      (data.cabin_class as string | undefined);
    dispatch(
      syncItineraryToSearchParams({
        origin: data.origin as string | undefined,
        destination: data.destination as string | undefined,
        departure_date: (data.departure_date as string | null) ?? undefined,
        return_date: (data.return_date as string | null) ?? undefined,
        origin_iata: data.origin_iata as string | undefined,
        destination_iata: data.destination_iata as string | undefined,
        origin_name: data.origin_name as string | undefined,
        destination_name: data.destination_name as string | undefined,
        adults,
        children,
        infants,
        trip_type: tripType,
        cabin_class: cabinClass,
        skipHotelSync: hadMultistayChain,
      })
    );
    commitItineraryRichResultToUiState(dispatch, data, itineraryRoutePrefix(pathname), effectiveChatId, {
      skipFlightHydration: hadMulticityChain,
      skipHotelHydration: hadMultistayChain,
    });
  }

  if (response.type === 'flight_search_results' && response.data) {
    const root = response.data as Record<string, unknown>;
    const data = (root.data ?? {}) as Record<string, unknown>;
    const searchParams = (data.search_params ?? root.search_params ?? {}) as Record<string, unknown>;
    const passengers = (searchParams.passengers ?? {}) as Record<string, unknown>;
    const adults =
      (passengers.adults as number | undefined) ?? (searchParams.adults as number | undefined);
    const children =
      (passengers.children as number | undefined) ?? (searchParams.children as number | undefined);
    const infants =
      (passengers.infants as number | undefined) ?? (searchParams.infants as number | undefined);

    dispatch(
      setTripMeta({
        chatId: effectiveChatId ?? '__anon__',
        meta: {
          origin: searchParams.origin as string | undefined,
          destination: searchParams.destination as string | undefined,
          departure_date: searchParams.departure_date as string | undefined,
          return_date: searchParams.return_date as string | undefined,
          adults,
          children,
          infants,
          trip_type: mapJourneyTypeToTripType(searchParams.journey_type as string | undefined),
        },
      })
    );
  }

  if (response.type === 'hotel_search_results' && response.data) {
    hydrateHotelSearchResultsFromPayload(dispatch, response.data);
    const root = response.data as Record<string, unknown>;
    const data = (root.data ?? {}) as Record<string, unknown>;
    const searchParams = (data.search_params ?? root.search_params ?? {}) as Record<string, unknown>;
    const destinationCity =
      (searchParams.destination_city as string | undefined) ??
      (searchParams.destination as string | undefined);

    dispatch(
      setTripMeta({
        chatId: effectiveChatId ?? '__anon__',
        meta: {
          destination: destinationCity,
          departure_date: searchParams.check_in_date as string | undefined,
          return_date: searchParams.check_out_date as string | undefined,
          adults: searchParams.adults as number | undefined,
          children: searchParams.children as number | undefined,
        },
      })
    );
  }

  trackEvent('chat_bot_response_received', {
    chat_id: response.chat_id ?? chatId ?? null,
    intent_name: (response as { intent_name?: string }).intent_name ?? 'unknown',
    message_type: response.type ?? 'message',
    response_length: response.message?.length ?? 0,
  });

  playSound();

  if (!getChatPanelOpen()) {
    dispatch(incrementUnreadCount());
  }

  if (allowRichResultAutoNavigation) {
    navigateAuthenticatedChatRichResultIfApplicable(
      dispatch,
      navigate,
      pathname,
      isAuthenticated,
      response,
      effectiveChatId
    );
  }
}
