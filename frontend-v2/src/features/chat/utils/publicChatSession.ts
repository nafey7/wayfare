/**
 * Guest chat identity for public chat (localStorage, shared across tabs on this origin).
 * Keys align with backend plan: guest session UUID + optional chat thread id.
 *
 * **Clearing policy**: Do not remove guest keys on sign-in alone. Clear `chat_id` when the
 * guest explicitly starts a new conversation (`clearChat` in guest mode). Both keys are
 * cleared by `useGuestChatClaim` when `POST /api/chat/claim` succeeds (guest thread
 * attached to the user). Until then, leaving keys in place avoids breaking continuity if
 * the user signs out and keeps chatting as a guest.
 */

import {
  readLocalStorageString,
  removeLocalStorageKey,
  writeLocalStorageString,
} from '@/utils/typedLocalStorage';

const SESSION_ID_KEY = 'voya_public_chat_session_id';
const CHAT_ID_KEY = 'voya_public_chat_id';

/**
 * Set when the user sends at least one message on `/public/chat` (not `/`).
 * After sign-up, authenticated `/chat` skips the default welcome so it does not race transcript hydrate.
 */
const PUBLIC_CHAT_ROUTE_USER_MESSAGED_KEY = 'voya_public_chat_route_user_messaged_v1';

/** localStorage key for guest → auth conversion funnel (set before login, consumed after). */
export const PUBLIC_CHAT_CONVERSION_INTENT_KEY = 'voya_public_chat_conversion_intent';

export type PublicChatConversionIntent =
  | 'itinerary_view'
  | 'itinerary_save'
  | 'hotel_full_results'
  | 'hotel_view_search'
  | 'hotel_view_recommendations'
  | 'hotel_book_now'
  | 'hotel_show_all_book'
  | 'flight_book_now'
  | 'flight_view_recommendations'
  | 'flight_show_all_book';

const _VALID_CONVERSION_INTENTS: readonly PublicChatConversionIntent[] = [
  'itinerary_view',
  'itinerary_save',
  'hotel_full_results',
  'hotel_view_search',
  'hotel_view_recommendations',
  'hotel_book_now',
  'hotel_show_all_book',
  'flight_book_now',
  'flight_view_recommendations',
  'flight_show_all_book',
] as const;

/** Guest browser session id (UUID string) for X-Public-Chat-Session. */
export function getPublicChatSessionId(): string | null {
  return readLocalStorageString(SESSION_ID_KEY);
}

/** Returns existing session id or creates one and persists it for this browser profile. */
export function getOrCreatePublicChatSessionId(): string {
  const existing = getPublicChatSessionId();
  if (existing) {
    return existing;
  }
  const id = crypto.randomUUID();
  setPublicChatSessionId(id);
  return id;
}

export function setPublicChatSessionId(sessionId: string): void {
  writeLocalStorageString(SESSION_ID_KEY, sessionId);
}

/** Active guest chat thread id returned by POST /api/public/chat/message. */
export function getPublicChatId(): string | null {
  return readLocalStorageString(CHAT_ID_KEY);
}

export function setPublicChatId(chatId: string | null): void {
  if (chatId === null || chatId === '') {
    removeLocalStorageKey(CHAT_ID_KEY);
    return;
  }
  writeLocalStorageString(CHAT_ID_KEY, chatId);
}

/** Clear guest chat id only (e.g. new conversation). Session id may remain until full reset. */
export function clearPublicChatId(): void {
  removeLocalStorageKey(CHAT_ID_KEY);
}

/** Clears both guest session id and guest chat id (e.g. after successful claim or full reset). */
export function clearPublicChatSession(): void {
  removeLocalStorageKey(SESSION_ID_KEY);
  removeLocalStorageKey(CHAT_ID_KEY);
  removeLocalStorageKey(PUBLIC_CHAT_ROUTE_USER_MESSAGED_KEY);
}

/** Call when the guest sends a message on `/public/chat` only. */
export function markPublicChatRouteUserMessaged(): void {
  writeLocalStorageString(PUBLIC_CHAT_ROUTE_USER_MESSAGED_KEY, '1');
}

/**
 * True after the guest sent at least one message on `/public/chat` (not `/`).
 * Drives: (1) skip default welcome on authenticated `/chat`, (2) post-auth redirect to `/chat`
 * when {@link shouldPostAuthPreferChatOverHome} is used with `public_chat_enabled`.
 */
export function shouldSkipAuthWelcomeAfterPublicChatRoute(): boolean {
  return readLocalStorageString(PUBLIC_CHAT_ROUTE_USER_MESSAGED_KEY) === '1';
}

/** Prefer `/chat` over `/home` after sign-in when the user messaged on `/public/chat` and public chat is on. */
export function shouldPostAuthPreferChatOverHome(publicChatEnabled: boolean): boolean {
  return publicChatEnabled && shouldSkipAuthWelcomeAfterPublicChatRoute();
}

export function clearPublicChatRouteUserMessagedFlag(): void {
  removeLocalStorageKey(PUBLIC_CHAT_ROUTE_USER_MESSAGED_KEY);
}

/** Persist intent when a guest hits a sign-up–gated CTA (cleared after successful auth). */
export function setPublicChatConversionIntent(intent: PublicChatConversionIntent): void {
  writeLocalStorageString(PUBLIC_CHAT_CONVERSION_INTENT_KEY, intent);
}

/** Read and remove stored conversion intent (call once after login). */
export function consumePublicChatConversionIntent(): PublicChatConversionIntent | null {
  const raw = readLocalStorageString(PUBLIC_CHAT_CONVERSION_INTENT_KEY);
  if (!raw) {
    return null;
  }
  removeLocalStorageKey(PUBLIC_CHAT_CONVERSION_INTENT_KEY);
  return _VALID_CONVERSION_INTENTS.includes(raw as PublicChatConversionIntent)
    ? (raw as PublicChatConversionIntent)
    : null;
}
