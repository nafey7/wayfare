import { peekGuestChatTranscript } from '@/features/chat/utils/publicChatGuestTranscript';
import {
  getPublicChatSessionId,
  shouldSkipAuthWelcomeAfterPublicChatRoute,
} from '@/features/chat/utils/publicChatSession';
import {
  readLocalStorageString,
  removeLocalStorageKey,
  writeLocalStorageString,
} from '@/utils/typedLocalStorage';

const PENDING_COMPLETE_REGISTRATION_KEY = 'voya_public_chat_pending_complete_registration_v1';

/** Set from the auth modal when email registration succeeds on a public-chat surface (Tab A). */
export function setPublicChatPendingCompleteRegistration(): void {
  writeLocalStorageString(PENDING_COMPLETE_REGISTRATION_KEY, '1');
}

export function isPublicChatPendingCompleteRegistration(): boolean {
  return readLocalStorageString(PENDING_COMPLETE_REGISTRATION_KEY) === '1';
}

export function clearPublicChatPendingCompleteRegistration(): void {
  removeLocalStorageKey(PENDING_COMPLETE_REGISTRATION_KEY);
}

/**
 * True when post–complete-registration navigation should prefer `/chat` (intent from Tab A
 * or guest transcript in localStorage).
 */
export function hasCompleteRegistrationPublicChatHandoffSignals(): boolean {
  if (isPublicChatPendingCompleteRegistration()) {
    return true;
  }
  if (shouldSkipAuthWelcomeAfterPublicChatRoute()) {
    return true;
  }
  const sid = getPublicChatSessionId();
  return Boolean(sid && peekGuestChatTranscript(sid)?.length);
}
