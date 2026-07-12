import { createListenerMiddleware, isAnyOf } from '@reduxjs/toolkit';

import { usersApi } from '@/api/usersApi';
import {
  clearPendingOnboardingPreferencesSync,
  getPendingOnboardingPreferencesPayload,
} from '@/features/onboarding/utils/pendingOnboardingPreferencesSync';
import { setCredentials, clearAuth } from '@/store/slices/authSlice';
import { resetOnboarding } from '@/store/slices/onboardingSlice';
import { devLog } from '@/utils/devLog';

/**
 * After sign-in or registration completion, persist /onboarding/trip "Preferences"
 * (travel pace, budget, primary goals) to user preferences in the DB.
 */
export const authOnboardingPreferencesListener = createListenerMiddleware();

authOnboardingPreferencesListener.startListening({
  matcher: isAnyOf(setCredentials, clearAuth),
  effect: async (action, listenerApi) => {
    if (clearAuth.match(action)) {
      clearPendingOnboardingPreferencesSync();
      return;
    }

    const body = getPendingOnboardingPreferencesPayload();
    if (!body) {
      return;
    }

    try {
      await listenerApi
        .dispatch(usersApi.endpoints.updatePreferences.initiate(body))
        .unwrap();
      listenerApi.dispatch(resetOnboarding());
      clearPendingOnboardingPreferencesSync();
    } catch (e) {
      devLog('Failed to save onboarding trip preferences after auth', e);
    }
  },
});
