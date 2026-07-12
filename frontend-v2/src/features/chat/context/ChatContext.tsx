import { createContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { useStore } from 'react-redux';
import { useChatHistoryLoader } from '@/features/chat/hooks/useChatHistoryLoader';
import { useLocation, useNavigate } from 'react-router-dom';

import {
  PENDING_CHAT_MESSAGE_KEY,
  REDIRECT_TO_CHAT_AFTER_SEARCH_KEY,
} from '@/features/auth/constants';
import { useIsMdUp } from '@/hooks/useIsMdUp';
import { getContentRoutePrefix, isPublicChatRoute } from '@/features/routing';
import { useAppSelector, useAppDispatch, type RootState } from '@/store';
import {
  selectMessages,
  selectChatId,
  selectChatLoading,
  selectChatConfig,
  selectConfigLoaded,
  selectConversations,
  selectConversationsLoaded,
  addMessage,
  removeTypingIndicator,
  setChatId,
  setLoading,
  clearMessages,
} from '@/store/slices/chatSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import {
  selectChatOpen,
  selectSoundEnabled,
  selectAutoScroll,
  selectChatFullScreen,
  selectUnreadCount,
  setChatOpen,
  toggleSound,
  toggleAutoScroll,
  toggleFullScreen,
  clearUnreadCount,
  openAuthModal,
  setPlacesSessionToken,
} from '@/store/slices/uiSlice';
import { applyHotelSearchUrlFromFormState } from '@/store/thunks/applyHotelSearchUrlFromFormState';
import {
  useSendPublicMessageMutation,
  useRefreshPublicPlacesSessionTokenMutation,
  useClearLatestChatMutation,
} from '@/api';
import type { ChatMessage, ChatResponse, FrontendConfig } from '@/types/chat';
import {
  createBotMessage,
  createTypingMessage,
  createUserMessage,
} from '@/features/chat/utils/chatMessages';
import { applySuccessfulChatResponse as applySuccessfulChatResponseCore } from '@/features/chat/utils/applySuccessfulChatResponse';
import { useFrontendConfigSync } from '@/features/chat/hooks/useFrontendConfigSync';
import { useSendChatMessage } from '@/features/chat/hooks/useSendChatMessage';
import { useGuestChatTranscriptLifecycle } from '@/features/chat/hooks/useGuestChatTranscriptLifecycle';
import { useGuestChatClaim } from '@/features/chat/hooks/useGuestChatClaim';
import { trackEvent } from '@/utils/gtm';
import { PLACES_SESSION_FORBIDDEN_EVENT } from '@/features/chat/constants/placesSessionEvents';
import {
  getOrCreatePublicChatSessionId,
  getPublicChatId,
  getPublicChatSessionId,
  clearPublicChatId,
  markPublicChatRouteUserMessaged,
  clearPublicChatRouteUserMessagedFlag,
} from '@/features/chat/utils/publicChatSession';
import { clearGuestChatTranscript } from '@/features/chat/utils/publicChatGuestTranscript';
import {
  computePlacesSessionForbiddenBackoffMs,
  MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS,
  TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS,
  shouldCountPlacesSessionRefreshFailureTowardCap,
} from '@/features/chat/utils/placesSessionForbiddenRefresh';

const MESSAGE_NOTIFICATION_SOUND_URL = '/assets/sounds/message.mp3';
let messageNotificationAudio: HTMLAudioElement | null = null;

function playMessageNotificationSound(): void {
  if (!messageNotificationAudio) {
    messageNotificationAudio = new Audio(MESSAGE_NOTIFICATION_SOUND_URL);
  }
  messageNotificationAudio.currentTime = 0;
  void messageNotificationAudio.play().catch(() => {
    // Ignore audio play errors
  });
}

function isPublicChatHttpError(
  err: unknown
): err is { status: number; data?: { code?: string; detail?: string } } {
  return (
    typeof err === 'object' &&
    err !== null &&
    'status' in err &&
    typeof (err as { status: unknown }).status === 'number'
  );
}

/**
 * #1038: true when an itinerary chat response shipped a non-empty
 * pre-fetched ``hotels`` array. Used to skip the legacy "open the search
 * form pre-populated" hotel-URL override that would otherwise clobber the
 * hydrator's ``lastHotelPath = '/hotels/search'``.
 */
function hasPrefetchedHotelsOnResponse(response: ChatResponse): boolean {
  const data = (response.data ?? {}) as Record<string, unknown>;
  return Array.isArray(data.hotels) && (data.hotels as unknown[]).length > 0;
}


/**
 * Chat context value type
 */
export interface ChatContextValue {
  // Messages
  messages: ChatMessage[];
  isTyping: boolean;
  chatId: string | null;

  // Input
  chatInput: string;
  setChatInput: (value: string) => void;

  // Actions
  sendMessage: (message: string) => Promise<void>;
  clearChat: () => Promise<void>;

  // UI State
  isOpen: boolean;
  openChat: () => void;
  closeChat: () => void;
  toggleChat: () => void;

  // Settings
  soundEnabled: boolean;
  toggleSound: () => void;
  autoScroll: boolean;
  toggleAutoScroll: () => void;
  isFullScreen: boolean;
  toggleFullScreen: () => void;

  // Status
  isAuthenticated: boolean;
  loading: boolean;
  unreadCount: number;
  messagesLoaded: boolean;
  config: FrontendConfig;
}

export const ChatContext = createContext<ChatContextValue | undefined>(undefined);

/**
 * Chat context provider
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  const reduxStore = useStore<RootState>();
  const location = useLocation();
  const navigate = useNavigate();
  const isMdUp = useIsMdUp();

  // Redux state
  const messages = useAppSelector(selectMessages);
  const chatId = useAppSelector(selectChatId);
  const loading = useAppSelector(selectChatLoading);
  const config = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isOpen = useAppSelector(selectChatOpen);
  const soundEnabled = useAppSelector(selectSoundEnabled);
  const autoScroll = useAppSelector(selectAutoScroll);
  const isFullScreen = useAppSelector(selectChatFullScreen);
  const unreadCount = useAppSelector(selectUnreadCount);
  const conversations = useAppSelector(selectConversations);
  const conversationsLoaded = useAppSelector(selectConversationsLoaded);

  // Local state
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useFrontendConfigSync(dispatch);

  useChatHistoryLoader({ isAuthenticated, chatId });

  useGuestChatClaim({
    dispatch,
    isAuthenticated,
    publicChatEnabled: config.publicChatEnabled,
    configLoaded,
  });

  const messagesLoaded = useGuestChatTranscriptLifecycle({
    dispatch,
    pathname: location.pathname,
    isAuthenticated,
    publicChatEnabled: config.publicChatEnabled,
    configLoaded,
    messages,
    chatId,
    conversationsLoaded,
    conversationsCount: conversations.length,
  });

  // Chat send pipelines. ``useSendChatMessage`` covers authenticated
  // turns with SSE-first + transparent fallback to POST /chat/message
  // (#1117). Public/guest chat still goes through the legacy mutation.
  const { sendMessage: sendChatMessage } = useSendChatMessage();
  const [sendPublicMessageMutation] = useSendPublicMessageMutation();
  const [refreshPlacesSessionToken] = useRefreshPublicPlacesSessionTokenMutation();
  const [clearChatMutation] = useClearLatestChatMutation();
  const placesSessionRefreshInFlight = useRef(false);
  /** Completed refresh runs from PLACES_SESSION_FORBIDDEN (caps loops even when API returns 200 + token but images still 403). */
  const placesSessionForbiddenRefreshCount = useRef(0);
  const placesSessionForbiddenBackoffUntil = useRef(0);
  const placesSessionForbiddenLastSessionId = useRef<string | null>(null);

  const getChatPanelOpen = useCallback(
    () => selectChatOpen(reduxStore.getState()),
    [reduxStore]
  );

  // Play message sound
  const playSound = useCallback(() => {
    if (soundEnabled) {
      playMessageNotificationSound();
    }
  }, [soundEnabled]);

  const applySuccessfulChatResponse = useCallback(
    (response: ChatResponse, message: string, options: { persistGuestChatId: boolean }) => {
      applySuccessfulChatResponseCore(
        {
          dispatch,
          navigate,
          pathname: location.pathname,
          chatId,
          isAuthenticated,
          getChatPanelOpen,
          getMessages: () => selectMessages(reduxStore.getState()),
          playSound,
          setIsTyping,
          createBotMessage,
          allowRichResultAutoNavigation: isMdUp,
        },
        response,
        message,
        options
      );
    },
    [chatId, dispatch, getChatPanelOpen, isAuthenticated, isMdUp, location.pathname, navigate, playSound]
  );

  const sendMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      if (!isAuthenticated && !config.publicChatEnabled) {
        dispatch(openAuthModal());
        dispatch(setChatOpen(false));
        return;
      }

      if (!isAuthenticated && config.publicChatEnabled) {
        if (isPublicChatRoute(location.pathname)) {
          markPublicChatRouteUserMessaged();
        }
        const userMessage = createUserMessage(message);
        // Don't pre-clear recommendations Redux — the new response's hydrate
        // will overwrite with fresh data, and clearing causes a flash to old
        // location.state data when the page is `/flights/recommendations`.
        dispatch(addMessage(userMessage));
        setChatInput('');
        setIsTyping(true);
        dispatch(addMessage(createTypingMessage()));
        dispatch(setLoading(true));
        try {
          const sessionId = getOrCreatePublicChatSessionId();
          const bodyChatId = getPublicChatId() ?? chatId ?? undefined;
          const response = await sendPublicMessageMutation({
            body: {
              message,
              ...(bodyChatId ? { chat_id: bodyChatId } : {}),
            },
            sessionId,
          }).unwrap();
          applySuccessfulChatResponse(response, message, { persistGuestChatId: true });
          if (response.type === 'itinerary_results' && !hasPrefetchedHotelsOnResponse(response)) {
            // #1038: when the personalised-itinerary backend pre-fetched
            // hotels, ``hydrateHotelSideSearchFromItinerary`` already set
            // ``lastHotelPath`` to ``/hotels/search``. The
            // ``applyHotelSearchUrlFromFormState`` thunk overwrites that
            // back to ``/hotels/search?q=...`` for the legacy "open the
            // search form pre-populated" behaviour — skip it when hotels
            // are already cached.
            const hotelPath = dispatch(applyHotelSearchUrlFromFormState());
            const onHotelSearch = location.pathname.replace(/\/$/, '').endsWith('/hotels/search');
            if (hotelPath && onHotelSearch) {
              const prefix = getContentRoutePrefix(location.pathname);
              navigate(`${prefix}${hotelPath}`, { replace: true });
            }
          }
        } catch (err) {
          console.error('Chat error:', err);
          dispatch(removeTypingIndicator());
          setIsTyping(false);
          if (isPublicChatHttpError(err) && err.status === 429) {
            const code = err.data?.code;
            if (code === 'public_rate_limit' || code === 'public_session_limit') {
              dispatch(openAuthModal());
              dispatch(
                addMessage(
                  createBotMessage(
                    'You have reached the guest message limit. Sign up to continue chatting.',
                    undefined,
                    'message'
                  )
                )
              );
            } else {
              dispatch(
                addMessage(
                  createBotMessage(
                    'Sorry, I encountered an error. Please try again.',
                    undefined,
                    'message'
                  )
                )
              );
            }
          } else {
            dispatch(
              addMessage(
                createBotMessage(
                  'Sorry, I encountered an error. Please try again.',
                  undefined,
                  'message'
                )
              )
            );
          }
        } finally {
          dispatch(setLoading(false));
        }
        return;
      }

      const userMessage = createUserMessage(message);
      // Don't pre-clear recommendations Redux — the new response's hydrate
      // will overwrite with fresh data, and clearing causes a flash to old
      // location.state data when the page is `/flights/recommendations` or
      // `/hotels/search`.
      dispatch(addMessage(userMessage));
      setChatInput('');

      setIsTyping(true);
      dispatch(addMessage(createTypingMessage()));
      dispatch(setLoading(true));

      try {
        // Streaming-first: useSendChatMessage tries POST /chat/message/stream
        // and transparently falls back to POST /chat/message on 404 (backend
        // flag off in this env) or network failure. SSE-supported turns
        // dispatch ``itinerary_partial`` events into Redux as the LLM
        // streams its structured output (#1117) — the skeleton renderer
        // picks those up automatically; this caller only sees the final
        // ChatResponse, identical to the non-streaming shape.
        const response = await sendChatMessage({
          message,
          chat_id: chatId ?? undefined,
        });
        applySuccessfulChatResponse(response, message, { persistGuestChatId: false });

        // Sync chat-derived hotel search URL into header chips on itinerary responses.
        // `applySuccessfulChatResponse` already syncs trip meta; this additionally
        // mirrors the itinerary into the hotel search URL so the last-hotel-path
        // chip navigates to a pre-populated /hotels/search, and replaces the
        // current URL if the user is already on the hotel search page.
        //
        // #1038: skip when the response carried pre-fetched hotels — the
        // itinerary-side hydrator already wrote ``lastHotelPath ='/hotels/search'``
        // and we don't want to clobber it. Without this gate, clicking the
        // Stays tab would fire a fresh ``/api/hotels/search`` even though
        // we already have the results in Redux.
        if (response.type === 'itinerary_results' && !hasPrefetchedHotelsOnResponse(response)) {
          const hotelPath = dispatch(applyHotelSearchUrlFromFormState());
          const onHotelSearch = location.pathname.replace(/\/$/, '').endsWith('/hotels/search');
          if (hotelPath && onHotelSearch) {
            const prefix = getContentRoutePrefix(location.pathname);
            navigate(`${prefix}${hotelPath}`, { replace: true });
          }
        }
      } catch (err) {
        console.error('Chat error:', err);
        dispatch(removeTypingIndicator());
        setIsTyping(false);
        const errorMessage = createBotMessage(
          'Sorry, I encountered an error. Please try again.',
          undefined,
          'message'
        );
        dispatch(addMessage(errorMessage));
      } finally {
        dispatch(setLoading(false));
      }
    },
    [
      applySuccessfulChatResponse,
      chatId,
      config.publicChatEnabled,
      dispatch,
      isAuthenticated,
      location.pathname,
      navigate,
      sendChatMessage,
      sendPublicMessageMutation,
    ]
  );

  // Clear chat
  const clearChat = useCallback(async () => {
    if (!isAuthenticated && config.publicChatEnabled) {
      dispatch(clearMessages());
      dispatch(setChatId(null));
      clearPublicChatId();
      clearGuestChatTranscript();
      clearPublicChatRouteUserMessagedFlag();
      return;
    }
    if (!isAuthenticated) {
      return;
    }
    try {
      await clearChatMutation().unwrap();
      dispatch(clearMessages());
      dispatch(setChatId(null));
    } catch (error) {
      console.error('Failed to clear chat:', error);
    }
  }, [clearChatMutation, config.publicChatEnabled, dispatch, isAuthenticated]);

  // Chat open/close handlers
  const closeChat = useCallback(() => dispatch(setChatOpen(false)), [dispatch]);
  const toggleChatOpen = useCallback(() => {
    if (!isOpen) {
      trackEvent('chat_opened', { is_authenticated: !!isAuthenticated });
    }
    dispatch(setChatOpen(!isOpen));
  }, [dispatch, isOpen, isAuthenticated]);

  // Settings handlers
  const handleToggleSound = useCallback(() => dispatch(toggleSound()), [dispatch]);
  const handleToggleAutoScroll = useCallback(() => dispatch(toggleAutoScroll()), [dispatch]);
  const handleToggleFullScreen = useCallback(() => dispatch(toggleFullScreen()), [dispatch]);

  // Clear unread count when opening chat
  const openChatAndClearUnread = useCallback(() => {
    if (!isOpen) {
      trackEvent('chat_opened', { is_authenticated: !!isAuthenticated });
    }
    dispatch(setChatOpen(true));
    dispatch(clearUnreadCount());
  }, [dispatch, isOpen, isAuthenticated]);

  // Drop legacy pending-message keys on login when public chat is on (no post-auth auto-send).
  useEffect(() => {
    if (!isAuthenticated || !configLoaded || !config.publicChatEnabled) return;
    try {
      localStorage.removeItem(PENDING_CHAT_MESSAGE_KEY);
      localStorage.removeItem(REDIRECT_TO_CHAT_AFTER_SEARCH_KEY);
    } catch {
      // Ignore localStorage errors
    }
  }, [isAuthenticated, configLoaded, config.publicChatEnabled]);

  /** Guest Places photos: mint a new session JWT when an image load returns 401/403. */
  useEffect(() => {
    if (isAuthenticated || !config.publicChatEnabled) {
      return;
    }
    const onForbidden = (): void => {
      const sessionId = getPublicChatSessionId();
      if (!sessionId) {
        return;
      }
      if (sessionId !== placesSessionForbiddenLastSessionId.current) {
        placesSessionForbiddenLastSessionId.current = sessionId;
        placesSessionForbiddenRefreshCount.current = 0;
        placesSessionForbiddenBackoffUntil.current = 0;
      }
      if (placesSessionRefreshInFlight.current) {
        return;
      }
      if (placesSessionForbiddenRefreshCount.current >= MAX_PLACES_SESSION_FORBIDDEN_REFRESH_ATTEMPTS) {
        return;
      }
      const now = Date.now();
      if (now < placesSessionForbiddenBackoffUntil.current) {
        return;
      }
      placesSessionRefreshInFlight.current = true;
      const recordCompletedRefresh = (): void => {
        placesSessionForbiddenRefreshCount.current += 1;
        const completed = placesSessionForbiddenRefreshCount.current;
        // After the last allowed refresh, onForbidden returns early on count >= MAX before
        // backoff is consulted, so this timestamp is effectively unused — kept for symmetry.
        placesSessionForbiddenBackoffUntil.current =
          Date.now() + computePlacesSessionForbiddenBackoffMs(completed);
      };
      void refreshPlacesSessionToken({ sessionId })
        .unwrap()
        .then((body) => {
          const t = body.places_session_token?.trim();
          if (t) {
            dispatch(setPlacesSessionToken(t));
          }
          recordCompletedRefresh();
        })
        .catch((err: unknown) => {
          if (shouldCountPlacesSessionRefreshFailureTowardCap(err)) {
            recordCompletedRefresh();
          } else {
            placesSessionForbiddenBackoffUntil.current =
              Date.now() + TRANSIENT_PLACES_SESSION_REFRESH_BACKOFF_MS;
          }
        })
        .finally(() => {
          placesSessionRefreshInFlight.current = false;
        });
    };
    window.addEventListener(PLACES_SESSION_FORBIDDEN_EVENT, onForbidden);
    return () => window.removeEventListener(PLACES_SESSION_FORBIDDEN_EVENT, onForbidden);
  }, [isAuthenticated, config.publicChatEnabled, dispatch, refreshPlacesSessionToken]);

  const value: ChatContextValue = {
    // Messages
    messages,
    isTyping,
    chatId,

    // Input
    chatInput,
    setChatInput,

    // Actions
    sendMessage,
    clearChat,

    // UI State
    isOpen,
    openChat: openChatAndClearUnread,
    closeChat,
    toggleChat: toggleChatOpen,

    // Settings
    soundEnabled,
    toggleSound: handleToggleSound,
    autoScroll,
    toggleAutoScroll: handleToggleAutoScroll,
    isFullScreen,
    toggleFullScreen: handleToggleFullScreen,

    // Status
    isAuthenticated,
    loading,
    unreadCount,
    messagesLoaded,
    config,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
