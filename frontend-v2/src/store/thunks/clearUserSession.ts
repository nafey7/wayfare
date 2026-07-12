import { baseApi } from '@/api/baseApi';
import type { AppThunk } from '@/store';
import { clearAuth } from '@/store/slices/authSlice';
import { resetChat } from '@/store/slices/chatSlice';
import { clearCachedFlightResults } from '@/store/slices/flightBookingSlice';
import { clearCachedHotelResults } from '@/store/slices/hotelBookingSlice';
import { resetOnboarding } from '@/store/slices/onboardingSlice';
import {
  clearActiveSavedItineraryIdForBooking,
  resetItineraryStateByChatId,
} from '@/store/slices/uiSlice';

/**
 * Clears all user-scoped state on sign-out or auth expiry.
 * Single dispatch site so adding new user-scoped caches only requires updating here.
 */
export function clearUserSession(): AppThunk {
  return (dispatch) => {
    dispatch(clearAuth());
    dispatch(clearCachedFlightResults());
    dispatch(clearCachedHotelResults());
    dispatch(resetChat());
    dispatch(clearActiveSavedItineraryIdForBooking());
    dispatch(resetItineraryStateByChatId());
    dispatch(resetOnboarding());
    dispatch(baseApi.util.resetApiState());
  };
}
