import type { OnboardingTripDetails } from '@/types/onboarding';
import type { PreferencesUpdateRequest, TravelStylePreferences } from '@/types/profile';

/**
 * Maps onboarding trip "Preferences" (pace, budget, goals) to a partial preferences PUT
 * body. Returns null when there is nothing to persist (all optional fields empty).
 */
export function preferencesUpdateFromOnboardingTrip(
  details: OnboardingTripDetails
): PreferencesUpdateRequest | null {
  const travelStyle: Partial<TravelStylePreferences> = {};
  if (details.travelPace) {
    travelStyle.travelPace = details.travelPace;
  }
  if (details.budgetMindset) {
    travelStyle.budgetMindset = details.budgetMindset;
  }
  if (details.primaryGoals.length > 0) {
    travelStyle.primaryGoals = [...details.primaryGoals];
  }

  if (Object.keys(travelStyle).length === 0) {
    return null;
  }
  return { travelStyle };
}
