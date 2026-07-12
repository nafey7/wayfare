import { createListenerMiddleware, isAnyOf } from '@reduxjs/toolkit';

import { itinerariesApi } from '@/api/itinerariesApi';
import {
  addGuestItinerary,
  getGuestItineraries,
  removeGuestItinerary,
} from '@/features/chat/utils/guestItineraries';
import { devLog } from '@/utils/devLog';
import { setCredentials } from './slices/authSlice';
import { setLastItineraryState } from './slices/uiSlice';
import type { RootState } from '.';

/**
 * Listener middleware that bridges guest itinerary data with the backend:
 *
 * 1. When `setLastItineraryState` fires and the user is NOT authenticated,
 *    the itinerary is appended to the `voya_guest_itineraries` localStorage array.
 *
 * 2. When `setCredentials` fires (login OR registration), every guest itinerary
 *    is saved to the backend then the local array is cleared.
 *    Entries are removed one-by-one on success so a partial network failure
 *    only loses the entries that failed rather than the entire set.
 */
export const guestItineraryListener = createListenerMiddleware();

guestItineraryListener.startListening({
  actionCreator: setLastItineraryState,
  effect: (action, { getState }) => {
    const state = getState() as RootState;
    if (state.auth.isAuthenticated) return;
    const navState = action.payload.state;
    if (!navState?.structuredItinerary) return;
    const { structuredItinerary, tripMeta, savedItineraryId } = navState;
    addGuestItinerary({ structuredItinerary, tripMeta, savedItineraryId });
  },
});

// Prevent double-save when setCredentials fires more than once in quick succession
// (e.g. login followed by a token refresh that re-emits setCredentials).
// Block-scoped so each startListening call gets its own flag; tests don't share state.
{
  let isSyncing = false;

  guestItineraryListener.startListening({
    matcher: isAnyOf(setCredentials),
    effect: async (_action, listenerApi) => {
      if (isSyncing) return;
      const pending = getGuestItineraries();
      if (!pending.length) return;

      isSyncing = true;
      try {
        // Save oldest first so DB timestamps reflect the original generation order.
        for (const entry of [...pending].reverse()) {
          const meta = entry.tripMeta;
          const tripMeta = meta
            ? {
                origin: meta.origin,
                destination: meta.destination,
                departureDate: meta.departure_date,
                returnDate: meta.return_date,
                adults: meta.adults,
                children: meta.children,
                infants: meta.infants,
                tripType: meta.trip_type,
              }
            : undefined;
          try {
            await listenerApi
              .dispatch(
                itinerariesApi.endpoints.saveItinerary.initiate({
                  structuredItinerary: entry.structuredItinerary,
                  tripMeta,
                }),
              )
              .unwrap();
            // Remove only this entry on success; failed entries stay in localStorage
            // so they can be retried on the next login.
            removeGuestItinerary(entry);
          } catch (e) {
            devLog('Failed to sync guest itinerary to DB after auth', e);
          }
        }
      } finally {
        isSyncing = false;
      }
    },
  });
}
