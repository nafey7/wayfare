import type { AppThunk } from '@/store';
import { setLastHotelPath } from '@/store/slices/uiSlice';
import { buildHotelSearchUrlPath } from '@/features/hotels/utils/urlParams';

/**
 * Builds `/hotels/search?q=…` from current hotel booking form state, persists it for tab chips
 * (`lastHotelPath`), and returns the path for callers that need to navigate (e.g. chat).
 */
export function applyHotelSearchUrlFromFormState(): AppThunk<string | null> {
  return (dispatch, getState) => {
    const hotelPath = buildHotelSearchUrlPath(getState().hotelBooking.searchFormParams);
    if (hotelPath) {
      dispatch(setLastHotelPath(hotelPath));
    }
    return hotelPath;
  };
}
