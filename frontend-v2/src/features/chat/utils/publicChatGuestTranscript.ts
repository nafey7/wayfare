import type { ChatMessage, ChatMessageType } from '@/types/chat';

import { getPublicChatSessionId } from '@/features/chat/utils/publicChatSession';

const TRANSCRIPT_KEY_PREFIX = 'voya_public_chat_guest_transcript_v1:';

/** Keep stored payload small so localStorage quota errors are unlikely (large flight/hotel payloads). */
const MAX_GUEST_TRANSCRIPT_MESSAGES = 30;

const VALID_TYPES: ReadonlySet<ChatMessageType> = new Set([
  'message',
  'typing',
  'flight_search_results',
  'multicity_flight_search_results',
  'flight_date_range_results',
  'hotel_search_results',
  'itinerary_results',
]);

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null;
}

/** Minimal shape check so corrupted/tampered localStorage cannot poison Redux. */
function isValidGuestTranscriptMessage(m: unknown): m is ChatMessage {
  if (!isRecord(m)) return false;
  if (typeof m._id !== 'string' || m._id.length === 0) return false;
  if (m.from !== 'bot' && m.from !== 'user') return false;
  if (typeof m.type !== 'string' || !VALID_TYPES.has(m.type as ChatMessageType)) return false;
  if (m.contentType !== 'message' && m.contentType !== 'form') return false;
  const content = m.content;
  if (!isRecord(content)) return false;
  const msgs = content.messages;
  if (!Array.isArray(msgs) || msgs.length === 0) return false;
  for (const line of msgs) {
    if (!isRecord(line) || typeof line.text !== 'string') return false;
  }
  return true;
}

function storageKey(sessionId: string): string {
  return `${TRANSCRIPT_KEY_PREFIX}${sessionId}`;
}

/**
 * Persist guest thread messages for restore after a full-page auth break (e.g. email link to
 * `/complete-registration`). Call only from guest public-chat routes (see ChatContext).
 */
export function saveGuestChatTranscript(messages: ChatMessage[], sessionId: string): void {
  if (!sessionId || typeof localStorage === 'undefined') return;
  const capped =
    messages.length > MAX_GUEST_TRANSCRIPT_MESSAGES
      ? messages.slice(-MAX_GUEST_TRANSCRIPT_MESSAGES)
      : messages;
  try {
    localStorage.setItem(storageKey(sessionId), JSON.stringify(capped));
  } catch {
    // quota / private mode
  }
}

/**
 * Read stored transcript without removing it. Removal happens after the authenticated UI has
 * applied messages (see ChatContext) so we never drop data before the user sees it.
 */
export function peekGuestChatTranscript(sessionId: string): ChatMessage[] | null {
  if (!sessionId || typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(storageKey(sessionId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    if (!parsed.every(isValidGuestTranscriptMessage)) return null;
    return parsed;
  } catch {
    return null;
  }
}

/** Remove stored transcript for a guest session (after successful on-screen restore, or guest new chat). */
export function clearGuestChatTranscriptForSession(sessionId: string): void {
  if (!sessionId || typeof localStorage === 'undefined') return;
  try {
    localStorage.removeItem(storageKey(sessionId));
  } catch {
    // ignore
  }
}

/** Guest "new conversation": clear transcript for the current browser guest session id. */
export function clearGuestChatTranscript(): void {
  const sid = getPublicChatSessionId();
  if (sid) {
    clearGuestChatTranscriptForSession(sid);
  }
}
