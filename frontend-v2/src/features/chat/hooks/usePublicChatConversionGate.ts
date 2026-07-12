import { useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import {
  isPublicChatContentRoute,
  publicToAuthRoute,
} from '@/features/routing/constants';
import { stashPublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';
import {
  setPublicChatConversionIntent,
  type PublicChatConversionIntent,
} from '@/features/chat/utils/publicChatSession';

export type { PublicChatConversionIntent };

/**
 * Shared guest → sign-up gate for rich chat CTAs (itinerary, hotel, flight booking).
 * Returns whether the guarded action may run; opens the auth modal when the user is logged out.
 */
export function usePublicChatConversionGate() {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const { pathname, search } = useLocation();

  const ensureAuthenticated = useCallback(
    (intent?: PublicChatConversionIntent) => {
      if (isAuthenticated) return true;
      if (intent) {
        setPublicChatConversionIntent(intent);
      }
      if (isPublicChatContentRoute(pathname)) {
        const authPath = publicToAuthRoute(pathname);
        stashPublicChatReturnTo(authPath, search);
      }
      dispatch(openAuthModal());
      return false;
    },
    [dispatch, isAuthenticated, pathname, search]
  );

  return { isAuthenticated, ensureAuthenticated };
}
