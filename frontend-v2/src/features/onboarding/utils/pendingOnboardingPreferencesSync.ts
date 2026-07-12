/**
 * Persists onboarding "Preferences" (travel pace, budget, primary goals) for post-auth
 * sync. Survives `resetOnboarding()` and public-chat handoff because it uses a dedicated
 * key; cleared only after a successful `updatePreferences` call or on logout.
 */

import { preferencesUpdateFromOnboardingTrip } from '@/features/onboarding/preferencesUpdateFromOnboardingTrip';
import type { OnboardingTripDetails } from '@/types/onboarding';
import type { PreferencesUpdateRequest } from '@/types/profile';

export const PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY =
  'voya_pending_onboarding_preferences_payload';

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* quota / private mode */
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function getPendingOnboardingPreferencesPayload(): PreferencesUpdateRequest | null {
  const raw = safeGet(PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PreferencesUpdateRequest;
  } catch {
    return null;
  }
}

function stashPayload(body: PreferencesUpdateRequest): void {
  safeSet(PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY, JSON.stringify(body));
}

/**
 * When `preferencesUpdateFromOnboardingTrip` is non-null, writes/updates the stash.
 * Does not remove the stash when the trip has no preference fields — avoids wiping data
 * after onboarding reset or when only origin/dates/etc. change.
 */
export function upsertPendingOnboardingPreferencesStashFromTrip(
  trip: OnboardingTripDetails
): void {
  const body = preferencesUpdateFromOnboardingTrip(trip);
  if (body) stashPayload(body);
}

export function clearPendingOnboardingPreferencesSync(): void {
  safeRemove(PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY);
  safeRemove('voya_pending_onboarding_preferences_sync');
}
