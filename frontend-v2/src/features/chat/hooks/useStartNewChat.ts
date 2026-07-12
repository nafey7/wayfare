import { useCallback } from 'react';
import { useStore } from 'react-redux';

import { useAppDispatch, useAppSelector, type RootState } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { setChatId, clearMessages, setMessages } from '@/store/slices/chatSlice';
import { resetBooking as resetFlightBooking } from '@/store/slices/flightBookingSlice';
import { resetBooking as resetHotelBooking } from '@/store/slices/hotelBookingSlice';
import {
  ANON_CHAT_KEY,
  setLastItineraryState,
  setTripMeta,
  clearActiveSavedItineraryIdForBooking,
} from '@/store/slices/uiSlice';
import { createBotMessage } from '@/features/chat/utils/chatMessages';
import { clearPublicChatId } from '@/features/chat/utils/publicChatSession';

const WELCOME_TEXT =
  "Hello! I'm your Voya travel assistant. I can help you plan trips, search for flights and hotels, and create itineraries. What would you like to do?";

/**
 * sessionStorage key that signals useConversations should skip auto-selecting
 * the most recent conversation on its next mount. Only set for authenticated
 * users — for guests the equivalent is clearPublicChatId() below.
 */
export const NEW_CHAT_PENDING_KEY = 'voya_new_chat_pending';

function makeWelcomeMessage() {
  return createBotMessage(WELCOME_TEXT, undefined, 'message', undefined, {
    messages: [{ text: WELCOME_TEXT }],
    suggestions: [
      { title: '✈️ Search flights', command: 'Search flights' },
      { title: '🏨 Find hotels', command: 'Find hotels' },
      { title: '📋 Plan a trip', command: 'Plan a trip' },
    ],
  });
}

/**
 * Returns a callback that resets the chat AND all chat-scoped trip state
 * back to a blank new conversation (same as the "New Chat" button in
 * ConversationSidebar).
 *
 * Despite the name, the scope is intentionally broader than just chat
 * messages — anything that's keyed to the previous conversation and would
 * otherwise leak into the new one is cleared here:
 *
 * - chat: `chatId` cleared, messages replaced with a fresh welcome message.
 * - flight booking wizard: full `flightBookingSlice` reset.
 * - hotel booking wizard: full `hotelBookingSlice` reset.
 * - `uiSlice.lastItineraryState[chatId]` cleared (per-chat itinerary draft).
 * - `uiSlice.tripMeta[chatId]` cleared (per-chat trip metadata).
 * - `uiSlice.activeSavedItineraryIdForBooking` cleared (booking-linkage id).
 *
 * Sidebar / restoration behavior:
 * - Authenticated: sets a sessionStorage flag so useConversations skips
 *   auto-selecting the most recent conversation when LayoutWithChat mounts.
 * - Guest: clears the persisted public chat ID from localStorage so
 *   useGuestChatTranscriptLifecycle doesn't restore the old conversation
 *   when PublicChatWithContentLayout mounts.
 *
 * Safe to call from any page. New chat-scoped slices should be added to
 * the reset list here so future callers don't have to remember them.
 */
export function useStartNewChat(): () => void {
  const dispatch = useAppDispatch();
  const store = useStore<RootState>();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  return useCallback(() => {
    if (isAuthenticated) {
      sessionStorage.setItem(NEW_CHAT_PENDING_KEY, '1');
    } else {
      clearPublicChatId();
    }
    const activeChatId = store.getState().chat?.chatId ?? ANON_CHAT_KEY;
    dispatch(setChatId(null));
    dispatch(clearMessages());
    dispatch(setMessages([makeWelcomeMessage()]));
    dispatch(resetFlightBooking());
    dispatch(resetHotelBooking());
    dispatch(setLastItineraryState({ chatId: activeChatId, state: null }));
    dispatch(setTripMeta({ chatId: activeChatId, meta: null }));
    dispatch(clearActiveSavedItineraryIdForBooking());
  }, [dispatch, store, isAuthenticated]);
}
