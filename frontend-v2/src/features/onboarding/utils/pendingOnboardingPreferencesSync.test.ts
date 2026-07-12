import { describe, it, expect, beforeEach, vi } from 'vitest';

import {
  PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY,
  clearPendingOnboardingPreferencesSync,
  getPendingOnboardingPreferencesPayload,
  upsertPendingOnboardingPreferencesStashFromTrip,
} from './pendingOnboardingPreferencesSync';
import type { OnboardingTripDetails } from '@/types/onboarding';

const baseTrip = (): OnboardingTripDetails => ({
  origin: '',
  destination: '',
  departureDate: null,
  returnDate: null,
  passengers: { adults: 1, children: 0, infants: 0 },
  tripType: 'roundTrip',
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [],
  freeText: '',
});

describe('pendingOnboardingPreferencesSync', () => {
  let store: Record<string, string>;

  beforeEach(() => {
    store = {};
    vi.stubGlobal('localStorage', {
      getItem: vi.fn((k: string) => store[k] ?? null),
      setItem: vi.fn((k: string, v: string) => {
        store[k] = v;
      }),
      removeItem: vi.fn((k: string) => {
        delete store[k];
      }),
    });
  });

  it('upserts JSON payload when trip has persistable prefs', () => {
    upsertPendingOnboardingPreferencesStashFromTrip({
      ...baseTrip(),
      travelPace: 'balanced',
    });
    const raw = store[PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY];
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw!)).toEqual({
      travelStyle: { travelPace: 'balanced' },
    });
  });

  it('does not write when there is nothing to persist', () => {
    upsertPendingOnboardingPreferencesStashFromTrip(baseTrip());
    expect(store[PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY]).toBeUndefined();
  });

  it('getPendingOnboardingPreferencesPayload returns parsed body', () => {
    upsertPendingOnboardingPreferencesStashFromTrip({
      ...baseTrip(),
      primaryGoals: ['food'],
    });
    expect(getPendingOnboardingPreferencesPayload()).toEqual({
      travelStyle: { primaryGoals: ['food'] },
    });
  });

  it('clearPendingOnboardingPreferencesSync removes payload key', () => {
    upsertPendingOnboardingPreferencesStashFromTrip({
      ...baseTrip(),
      travelPace: 'relaxed',
    });
    clearPendingOnboardingPreferencesSync();
    expect(getPendingOnboardingPreferencesPayload()).toBeNull();
  });
});
