import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAppSelector, useAppDispatch } from '@/store';
import { selectAuthModalOpen, openAuthModal, closeAuthModal } from '@/store/slices/uiSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';
import { ROUTES } from '@/features/routing';
import { useStartNewChat } from '@/features/chat/hooks/useStartNewChat';
import { useGuestNewConversationGuard } from '@/features/chat/hooks/useGuestNewConversationGuard';
import type { ItineraryCardItem } from './components/ExampleItinerariesSection';
import { itineraryCardChatPrompt } from './utils/exampleItineraryChat';

export function useLandingPageController() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const chatConfig = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);
  const publicChatEnabled = chatConfig.publicChatEnabled;
  const authModalOpen = useAppSelector(selectAuthModalOpen);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const startNewChat = useStartNewChat();
  const { requestNewConversation, dialogProps: confirmDialogProps } =
    useGuestNewConversationGuard();
  /** Last `prompt` query value we auto-submitted; reset when param is absent so a new `?prompt=` can run again. */
  const lastProcessedPromptRef = useRef<string | null>(null);
  /** Detect `publicChatEnabled` flipping from false to true (e.g. ChatProvider after config) so we do not skip the guest public-chat path with a stale `lastProcessedPromptRef`. */
  const prevPublicChatEnabledRef = useRef<boolean | undefined>(undefined);

  const startChatWithPrompt = useCallback(
    (prompt: string) => {
      if (isAuthenticated) {
        requestNewConversation(() => {
          startNewChat();
          navigate(`${ROUTES.CHAT}?prompt=${encodeURIComponent(prompt)}`);
        });
      } else if (publicChatEnabled) {
        requestNewConversation(() => {
          startNewChat();
          navigate(`${ROUTES.PUBLIC_CHAT}?prompt=${encodeURIComponent(prompt)}`);
        });
      } else {
        dispatch(openAuthModal());
      }
    },
    [isAuthenticated, navigate, dispatch, publicChatEnabled, requestNewConversation, startNewChat]
  );

  const handleSearchSubmit = useCallback(
    (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) return;
      if (!isAuthenticated && !configLoaded) return;
      startChatWithPrompt(trimmed);
    },
    [isAuthenticated, configLoaded, startChatWithPrompt]
  );

  const handleCardPlanClick = useCallback(
    (item: ItineraryCardItem) => {
      if (!isAuthenticated && !configLoaded) return;
      startChatWithPrompt(itineraryCardChatPrompt(item));
    },
    [isAuthenticated, configLoaded, startChatWithPrompt]
  );

  const handleCtaClick = useCallback(() => {
    navigate(ROUTES.ONBOARDING);
  }, [navigate]);

  useEffect(() => {
    const prev = prevPublicChatEnabledRef.current;
    prevPublicChatEnabledRef.current = publicChatEnabled;
    if (
      prev === false &&
      publicChatEnabled === true &&
      lastProcessedPromptRef.current !== null
    ) {
      lastProcessedPromptRef.current = null;
    }
  }, [publicChatEnabled]);

  // Auto-submit from `?prompt=` when the value changes (same route, no remount).
  // On the marketing landing (`/`), guests with public chat are sent to `/public/chat` so the prompt auto-sends there.
  useEffect(() => {
    const prompt = new URLSearchParams(location.search).get('prompt');
    const trimmed = prompt?.trim() ?? '';
    if (!trimmed) {
      lastProcessedPromptRef.current = null;
      return;
    }
    // Guest: wait until frontend config resolves so we do not treat `publicChatEnabled` as false from
    // stale Redux, mark the prompt processed, then skip the correct branch after config loads.
    if (!isAuthenticated && !configLoaded) {
      return;
    }
    if (lastProcessedPromptRef.current === trimmed) return;
    lastProcessedPromptRef.current = trimmed;
    if (!isAuthenticated && publicChatEnabled && location.pathname === '/') {
      navigate(`${ROUTES.PUBLIC_CHAT}?prompt=${encodeURIComponent(trimmed)}`, { replace: true });
      return;
    }
    handleSearchSubmit(trimmed);
  }, [
    location.search,
    location.pathname,
    isAuthenticated,
    publicChatEnabled,
    configLoaded,
    handleSearchSubmit,
    navigate,
  ]);

  return {
    authModalOpen,
    handleSearchSubmit,
    handleCtaClick,
    handleCardPlanClick,
    confirmDialogProps,
    openAuthModal: () => dispatch(openAuthModal()),
    closeAuthModal: () => dispatch(closeAuthModal()),
  };
}
