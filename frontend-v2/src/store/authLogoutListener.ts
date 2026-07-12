import { createListenerMiddleware } from '@reduxjs/toolkit';

import { clearAuth } from '@/store/slices/authSlice';
import { clearPlacesSessionToken } from '@/store/slices/uiSlice';

/**
 * Keeps guest Places session token in sync when auth is cleared (logout / 401).
 */
export const authLogoutListener = createListenerMiddleware();

authLogoutListener.startListening({
  actionCreator: clearAuth,
  effect: (_action, listenerApi) => {
    listenerApi.dispatch(clearPlacesSessionToken());
  },
});
