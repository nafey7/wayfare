import {
  PENDING_CHAT_MESSAGE_KEY,
  REDIRECT_TO_CHAT_AFTER_SEARCH_KEY,
} from '../constants';

export type RedirectCheckResult =
  | { redirect: 'chat'; prompt: string }
  | { redirect: 'fallback' };

/**
 * Read localStorage for post-auth redirect to chat (search submit flow).
 * When `clear` is true, keys are cleared after reading.
 */
function readRedirectToChatAfterAuth(clear: boolean): RedirectCheckResult {
  try {
    const redirectFlag = localStorage.getItem(REDIRECT_TO_CHAT_AFTER_SEARCH_KEY);
    const pendingRaw = localStorage.getItem(PENDING_CHAT_MESSAGE_KEY);
    const redirectToChat =
      redirectFlag === '1' ||
      !!pendingRaw?.trim();
    if (redirectToChat) {
      const pendingTrimmed = pendingRaw?.trim();
      if (pendingTrimmed) {
        if (clear) {
          localStorage.removeItem(PENDING_CHAT_MESSAGE_KEY);
          localStorage.removeItem(REDIRECT_TO_CHAT_AFTER_SEARCH_KEY);
        }
        return { redirect: 'chat', prompt: pendingTrimmed };
      }
    }
    if (clear) {
      localStorage.removeItem(PENDING_CHAT_MESSAGE_KEY);
      localStorage.removeItem(REDIRECT_TO_CHAT_AFTER_SEARCH_KEY);
    }
  } catch {
    // Ignore storage errors
  }
  return { redirect: 'fallback' };
}

/**
 * Check localStorage for post-auth redirect to chat and clear keys.
 */
export function checkRedirectToChatAfterAuth(): RedirectCheckResult {
  return readRedirectToChatAfterAuth(true);
}

/**
 * Read pending post-auth redirect without clearing keys yet.
 * Useful in auth handlers where a rerender may happen before navigation completes.
 */
export function getRedirectToChatAfterAuth(): RedirectCheckResult {
  return readRedirectToChatAfterAuth(false);
}

/**
 * Store search query and redirect flag so user is sent to chat after auth.
 */
export function setRedirectToChatAfterSearch(message: string): void {
  try {
    localStorage.setItem(PENDING_CHAT_MESSAGE_KEY, message);
    localStorage.setItem(REDIRECT_TO_CHAT_AFTER_SEARCH_KEY, '1');
  } catch {
    // Ignore storage errors
  }
}
