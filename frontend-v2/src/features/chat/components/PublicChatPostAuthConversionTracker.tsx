import { useEffect, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { consumePublicChatConversionIntent } from '@/features/chat/utils/publicChatSession';
import { consumePendingItinerarySave } from '@/features/chat/utils/pendingItinerarySave';
import { itinerariesApi } from '@/api/itinerariesApi';
import { trackEvent } from '@/utils/gtm';
import { showSuccessToast, showWarningToast } from '@/utils/toast';

/**
 * When a guest opens the auth modal from a gated public-chat CTA, we store a conversion intent.
 * After login, emit one analytics event and clear the intent key (no-op if GTM is absent, e.g. localhost).
 * Navigation from `/public/chat` to `/chat` is handled by `PublicRoute` in `App.tsx`, not here.
 *
 * For `itinerary_save` intent: also auto-save the stashed itinerary data via POST /api/itineraries.
 */
export function PublicChatPostAuthConversionTracker() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const prevAuthenticated = useRef<boolean | null>(null);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (prevAuthenticated.current === false && isAuthenticated) {
      const intent = consumePublicChatConversionIntent();
      if (intent) {
        trackEvent('public_chat_post_auth_conversion', { intent });
      }

      if (intent === 'itinerary_save') {
        const pending = consumePendingItinerarySave();
        if (pending) {
          dispatch(
            itinerariesApi.endpoints.saveItinerary.initiate({
              structuredItinerary: pending.structured_itinerary,
              tripMeta: pending.trip_meta as Record<string, unknown> | undefined,
            })
          )
            .unwrap()
            .then(() => {
              showSuccessToast('Itinerary saved to your account!');
              trackEvent('public_chat_itinerary_auto_saved', { status: 'success' });
            })
            .catch(() => {
              showWarningToast(
                "Couldn't save your itinerary automatically — you can save it from the itinerary page."
              );
              trackEvent('public_chat_itinerary_auto_saved', { status: 'error' });
            });
        }
      }
    }
    prevAuthenticated.current = isAuthenticated;
  }, [isAuthenticated, dispatch]);

  return null;
}
