import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  resetOnboarding,
  selectOnboardingTripDetails,
} from '@/store/slices/onboardingSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing/constants';
import { buildItineraryPromptFromOnboarding } from '@/features/onboarding/buildItineraryPromptFromTrip';
import { stashPostAuthOnboardingPath } from '@/features/onboarding/utils/postAuthOnboardingPath';
import type { OnboardingTripDetails } from '@/types/onboarding';

/**
 * Fire background flight/hotel/itinerary searches per ARCH-01.
 *
 * Currently stubbed — onboarding form collects city names; adapter work is
 * needed before wiring these for real:
 *  - resolve city → IATA via /api/itinerary/capabilities/resolve-location
 *  - transform TripDetails → FlightSearchRequestBackend / HotelSearchRequestBackend
 *  - hydrate Redux (`cachedFlightResults`, hotel recs) so chat/search surfaces pick them up
 *
 * See Phase 6 of the onboarding plan for implementation details.
 */
function triggerBackgroundSearches(details: OnboardingTripDetails): void {
  if (import.meta.env.DEV) {

    console.info('[onboarding] background searches triggered (stubbed)', {
      origin: details.origin,
      destination: details.destination,
      departureDate: details.departureDate,
      returnDate: details.returnDate,
      tripType: details.tripType,
      passengers: details.passengers,
    });
  }

  // TODO (Phase 6): replace stub with actual search dispatch
}

interface StartPlanningResult {
  startPlanning: () => void;
  continueToChat: () => void;
  /**
   * Guest users need chat config (e.g. `publicChatEnabled`) before routing/auth modal; until
   * then `startPlanning` / `continueToChat` are no-ops. UI should disable CTAs and show loading.
   */
  isGuestAwaitingChatConfig: boolean;
}

export function useStartPlanning(): StartPlanningResult {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const tripDetails = useAppSelector(selectOnboardingTripDetails);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const chatConfig = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);

  const navigateToChat = useCallback(
    (options?: { prompt: string }):
      | { handled: true; shouldReset: boolean }
      | { handled: false } => {
      if (!isAuthenticated && !configLoaded) return { handled: false };
      const search = (() => {
        if (!options?.prompt?.trim()) return;
        return `?${new URLSearchParams({ prompt: options.prompt.trim() })}`;
      })();
      if (isAuthenticated) {
        navigate({ pathname: ROUTES.CHAT, search });
        return { handled: true, shouldReset: true };
      }
      if (chatConfig.publicChatEnabled) {
        navigate({ pathname: ROUTES.PUBLIC_CHAT, search });
        return { handled: true, shouldReset: true };
      }
      stashPostAuthOnboardingPath(ROUTES.ONBOARDING_TRIP);
      dispatch(openAuthModal());
      return { handled: true, shouldReset: false };
    },
    [isAuthenticated, configLoaded, chatConfig.publicChatEnabled, navigate, dispatch]
  );

  function commitAndReset() {
    dispatch(resetOnboarding());
  }

  const isGuestAwaitingChatConfig = !isAuthenticated && !configLoaded;

  return {
    isGuestAwaitingChatConfig,
    startPlanning() {
      triggerBackgroundSearches(tripDetails);
      const prompt = buildItineraryPromptFromOnboarding(tripDetails);
      const r = navigateToChat({ prompt });
      if (r.handled && r.shouldReset) {
        commitAndReset();
      }
    },
    continueToChat() {
      const r = navigateToChat();
      if (r.handled && r.shouldReset) {
        commitAndReset();
      }
    },
  };
}
