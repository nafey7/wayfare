import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Group, Loader } from '@mantine/core';

import { useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';

import { consumePublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';
import { hasCompleteRegistrationPublicChatHandoffSignals } from '@/features/chat/utils/publicChatSignupIntent';
import { shouldPostAuthPreferChatOverHome } from '@/features/chat/utils/publicChatSession';
import { devLog } from '@/utils/devLog';

import { ROUTES, isGuestPublicChatTranscriptRoute, isPublicChatContentRoute, publicToAuthRoute } from './constants';

interface PublicRouteProps {
  children: ReactNode;
}

/**
 * Public pages: guests see `children`. Authenticated users are redirected away
 * (`/home`, or `/chat` when guest chat was used on `/` or `/public/chat` — see below).
 *
 * When `public_chat_enabled` is on, config is loaded, and **`voya_public_chat_route_user_messaged_v1`**
 * is set (guest sent a message on **`/public/chat`**), signed-in users on **`/`** or **`/public/chat`**
 * go to **`/chat`**; otherwise they go to **`/home`** (same as guests who never messaged on `/public/chat`).
 *
 * **`/complete-registration`:** if `voya_public_chat_return_to` is valid, consume it and redirect there.
 * Do **not** redirect to `/chat` when peek is empty — `CompleteRegistrationPage` runs after
 * `setCredentials` and would lose a race to `<Navigate to=/chat>` if we did (handler often
 * clears stash before this tree commits).
 */
export function PublicRoute({ children }: PublicRouteProps) {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const chatConfig = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);
  const location = useLocation();

  if (isAuthenticated) {
    const pathname = location.pathname;
    if (isPublicChatContentRoute(pathname)) {
      const authPath = publicToAuthRoute(pathname);
      const target = location.search ? `${authPath}${location.search}` : authPath;
      return <Navigate to={target} replace state={location.state} />;
    }
    if (pathname === ROUTES.COMPLETE_REGISTRATION && !configLoaded) {
      return (
        <Group justify="center" align="center" style={{ minHeight: '40vh' }}>
          <Loader data-testid="loading-indicator" />
        </Group>
      );
    }
    if (pathname === ROUTES.COMPLETE_REGISTRATION && configLoaded) {
      const stashedReturn = consumePublicChatReturnTo();
      if (stashedReturn) {
        devLog('PublicRoute /complete-registration → stashed return-to (consume)', { stashedReturn });
        return <Navigate to={stashedReturn} replace />;
      }
      // Do not <Navigate to=/chat> when peek is empty: the submit handler may have already
      // consumed the stash before this commit — that raced navigate(returnTo) from the page.
      // Handoff → /chat is done imperatively in CompleteRegistrationPage.
      if (!hasCompleteRegistrationPublicChatHandoffSignals()) {
        return <Navigate to={ROUTES.HOME} replace />;
      }
      return <>{children}</>;
    }
    // URL param takes priority over localStorage: user's current intent from the URL.
    const urlPrompt = new URLSearchParams(location.search).get('prompt');
    if (urlPrompt?.trim()) {
      // Guest thread on `/` or `/public/chat` is already in Redux; `?prompt=` would duplicate-send on `/chat`.
      if (
        configLoaded &&
        chatConfig.publicChatEnabled &&
        isGuestPublicChatTranscriptRoute(location.pathname)
      ) {
        return <Navigate to={ROUTES.CHAT} replace />;
      }
      return (
        <Navigate
          to={`${ROUTES.CHAT}?prompt=${encodeURIComponent(urlPrompt.trim())}`}
          replace
        />
      );
    }
    // Guest messaged on `/public/chat` (localStorage flag): continue in `/chat` after sign-in.
    if (
      configLoaded &&
      isGuestPublicChatTranscriptRoute(location.pathname) &&
      shouldPostAuthPreferChatOverHome(chatConfig.publicChatEnabled)
    ) {
      return <Navigate to={ROUTES.CHAT} replace />;
    }
    return <Navigate to={ROUTES.HOME} replace />;
  }

  return <>{children}</>;
}
