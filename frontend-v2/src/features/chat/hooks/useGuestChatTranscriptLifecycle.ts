import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import { isGuestPublicChatTranscriptRoute } from '@/features/routing';
import {
  getPublicChatId,
  getPublicChatSessionId,
  shouldSkipAuthWelcomeAfterPublicChatRoute,
  clearPublicChatRouteUserMessagedFlag,
} from '@/features/chat/utils/publicChatSession';
import {
  saveGuestChatTranscript,
  peekGuestChatTranscript,
  clearGuestChatTranscriptForSession,
} from '@/features/chat/utils/publicChatGuestTranscript';
import { createBotMessage } from '@/features/chat/utils/chatMessages';
import type { AppDispatch } from '@/store';
import type { ChatMessage } from '@/types/chat';
import { addMessage, setChatId, setMessages } from '@/store/slices/chatSlice';

interface UseGuestChatTranscriptLifecycleArgs {
  dispatch: AppDispatch;
  pathname: string;
  isAuthenticated: boolean;
  publicChatEnabled: boolean;
  configLoaded: boolean;
  messages: ChatMessage[];
  /**
   * Active conversation id from Redux. When set on an authenticated mount we
   * skip seeding a welcome — ``ChatContext`` will fetch ``/chat/{chatId}``
   * and populate the transcript instead.
   */
  chatId: string | null;
  /**
   * True once ``GET /chat/conversations`` has resolved. Authenticated users
   * MUST wait for this before seeding a welcome — on a page refresh
   * ``chatId`` is briefly null until the auto-select logic in
   * ``useConversations`` picks the most recent thread, and seeding a
   * welcome in that gap would race the history fetch and leave the user
   * stuck on "Hello!" with no transcript.
   */
  conversationsLoaded: boolean;
  /**
   * Conversation count from Redux. Used together with
   * ``conversationsLoaded`` to decide whether the authenticated user is
   * truly first-time (=> seed welcome) vs. has existing chats (=> wait
   * for history fetch).
   */
  conversationsCount: number;
}

/**
 * Guest transcript persistence, post-auth hydration from localStorage, default welcome seeding,
 * and cleanup of stored transcripts — previously inline in ChatProvider.
 */
export function useGuestChatTranscriptLifecycle({
  dispatch,
  pathname,
  isAuthenticated,
  publicChatEnabled,
  configLoaded,
  messages,
  chatId,
  conversationsLoaded,
  conversationsCount,
}: UseGuestChatTranscriptLifecycleArgs): boolean {
  const [messagesLoaded, setMessagesLoaded] = useState(false);
  const welcomeMessageAdded = useRef(false);
  const didHydrateGuestTranscriptRef = useRef(false);
  /** Session id whose transcript was peek-restored; clear localStorage only after messages are on screen. */
  const pendingGuestTranscriptStorageClearRef = useRef<string | null>(null);

  useEffect(() => {
    if (isAuthenticated || !publicChatEnabled) return;
    const stored = getPublicChatId();
    if (stored) {
      dispatch(setChatId(stored));
    }
  }, [isAuthenticated, publicChatEnabled, dispatch]);

  useEffect(() => {
    if (isAuthenticated) return;
    didHydrateGuestTranscriptRef.current = false;
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated || !publicChatEnabled) return;
    if (!isGuestPublicChatTranscriptRoute(pathname)) return;
    const sid = getPublicChatSessionId();
    if (!sid) return;
    saveGuestChatTranscript(messages, sid);
  }, [messages, isAuthenticated, publicChatEnabled, pathname]);

  useLayoutEffect(() => {
    if (
      isAuthenticated &&
      publicChatEnabled &&
      configLoaded &&
      !didHydrateGuestTranscriptRef.current &&
      messages.length === 0
    ) {
      const sid = getPublicChatSessionId();
      const restored = sid ? peekGuestChatTranscript(sid) : null;
      if (restored?.length) {
        didHydrateGuestTranscriptRef.current = true;
        welcomeMessageAdded.current = true;
        dispatch(setMessages(restored));
        // chat_id + guest keys are managed by useGuestChatClaim post-auth.
        // We only clear the route-messaged flag here; localStorage cleanup
        // for transcript happens once messages are confirmed on screen.
        clearPublicChatRouteUserMessagedFlag();
        pendingGuestTranscriptStorageClearRef.current = sid;
        setMessagesLoaded(true);
        return;
      }
      didHydrateGuestTranscriptRef.current = true;
    }

    if (messages.length > 0 || welcomeMessageAdded.current) {
      setMessagesLoaded(true);
      return;
    }

    if (isAuthenticated && !configLoaded) {
      setMessagesLoaded(true);
      return;
    }

    if (isAuthenticated && publicChatEnabled && shouldSkipAuthWelcomeAfterPublicChatRoute()) {
      welcomeMessageAdded.current = true;
      clearPublicChatRouteUserMessagedFlag();
      setMessagesLoaded(true);
      return;
    }

    if (!isAuthenticated && !isGuestPublicChatTranscriptRoute(pathname)) {
      setMessagesLoaded(true);
      return;
    }

    // Authenticated user: defer the welcome until we know whether they
    // have existing conversations.
    //
    // - If ``chatId`` is already set, ``ChatContext`` will fetch the
    //   transcript — don't seed.
    // - Otherwise, until ``conversationsLoaded`` is true we don't yet know
    //   whether the auto-select in ``useConversations`` is about to pick a
    //   recent thread; seeding now would race that fetch.
    // - Once loaded, only seed when there are zero conversations (truly
    //   first-time user); ``useConversations`` also handles that branch
    //   but seeding here covers the case where it hasn't run yet.
    if (isAuthenticated) {
      if (chatId) {
        welcomeMessageAdded.current = true;
        setMessagesLoaded(true);
        return;
      }
      if (!conversationsLoaded) {
        // Wait — effect will re-run when ``conversationsLoaded`` flips.
        return;
      }
      if (conversationsCount > 0) {
        // ``useConversations`` will set ``chatId`` momentarily; the
        // history-fetch effect will then load the transcript.
        welcomeMessageAdded.current = true;
        setMessagesLoaded(true);
        return;
      }
      // Fall through: no conversations → seed welcome below.
    }

    welcomeMessageAdded.current = true;
    const welcomeMessage = createBotMessage(
      "Hello! I'm your Voya travel assistant. I can help you search for flights and hotels. What would you like to do today?",
      undefined,
      'message',
      undefined,
      {
        suggestions: [
          { title: 'Search flights', command: 'search flights' },
          { title: 'Find hotels', command: 'find hotels' },
        ],
      }
    );
    dispatch(addMessage(welcomeMessage));
    setMessagesLoaded(true);
  }, [
    isAuthenticated,
    publicChatEnabled,
    configLoaded,
    messages.length,
    dispatch,
    pathname,
    chatId,
    conversationsLoaded,
    conversationsCount,
  ]);

  useEffect(() => {
    const sid = pendingGuestTranscriptStorageClearRef.current;
    if (!sid) return;
    if (!isAuthenticated || !publicChatEnabled) return;
    if (!messagesLoaded || messages.length === 0) return;
    clearGuestChatTranscriptForSession(sid);
    pendingGuestTranscriptStorageClearRef.current = null;
  }, [isAuthenticated, publicChatEnabled, messagesLoaded, messages.length]);

  useEffect(() => {
    if (!isAuthenticated || !publicChatEnabled) return;
    if (pendingGuestTranscriptStorageClearRef.current) return;
    if (messages.length === 0) return;
    const sid = getPublicChatSessionId();
    if (!sid || !peekGuestChatTranscript(sid)) return;
    clearGuestChatTranscriptForSession(sid);
  }, [isAuthenticated, publicChatEnabled, messages.length]);

  return messagesLoaded;
}
