import { Navigate } from 'react-router-dom';
import { useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectHasCompletedLocationStep } from '@/store/slices/onboardingSlice';
import { ROUTES } from '@/features/routing/constants';

/**
 * Entry point for the `/onboarding` route. Redirects to the correct
 * screen based on the user's state.
 *
 * Decision matrix (intended end state):
 *
 *  Signed-in + profile location          → Screen 3 (trip)
 *  Signed-in + no profile location       → Screen 2 (location)
 *  Guest with completed location step    → Screen 3 (trip)
 *  Guest without completed location step → Screen 1 (welcome)
 *
 * Today, the "signed-in + no profile location" branch is not implemented: the
 * User model does not yet expose home location fields, so every signed-in user
 * is routed to the trip step. See TODO below.
 */
export function OnboardingRouter() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const hasLocation = useAppSelector(selectHasCompletedLocationStep);

  if (isAuthenticated) {
    // TODO(onboarding / profile API): When `User` includes home country/city (or similar),
    // set `hasProfileLocation` from those fields and send users missing location to
    // ROUTES.ONBOARDING_LOCATION per the matrix above. Until then, keep signed-in users on trip.
    const hasProfileLocation = true;
    return (
      <Navigate
        to={
          hasProfileLocation
            ? ROUTES.ONBOARDING_TRIP
            : ROUTES.ONBOARDING_LOCATION
        }
        replace
      />
    );
  }

  if (hasLocation) {
    return <Navigate to={ROUTES.ONBOARDING_TRIP} replace />;
  }

  return <Navigate to={ROUTES.ONBOARDING_WELCOME} replace />;
}
