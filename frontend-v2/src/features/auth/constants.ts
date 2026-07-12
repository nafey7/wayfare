/**
 * localStorage key for search query to replay in chat after auth.
 */
export const PENDING_CHAT_MESSAGE_KEY = 'pendingChatMessage';

/**
 * localStorage key for redirect flag: redirect to /chat after auth when set.
 */
export const REDIRECT_TO_CHAT_AFTER_SEARCH_KEY = 'redirectToChatAfterSearch';

/**
 * Route base paths where auth completion is handled by AuthModal, CompleteRegistrationPage,
 * or PublicRoute rather than ChatContext. ChatContext skips consuming pending
 * message on these routes. Matches exact path and any subpaths (e.g. /reset-password/token123).
 */
const PUBLIC_ROUTE_BASES = [
  '/',
  '/public/chat',
  '/forgot-password',
  '/reset-password',
  '/complete-registration',
] as const;

/** Exact public routes (for backward compatibility and tests). */
export const PUBLIC_ROUTES: readonly string[] = PUBLIC_ROUTE_BASES;

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTE_BASES.some(
    (base) => pathname === base || (base !== '/' && pathname.startsWith(base + '/'))
  );
}
