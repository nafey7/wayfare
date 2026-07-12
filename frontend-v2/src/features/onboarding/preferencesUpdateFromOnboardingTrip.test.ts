import { describe, it, expect } from 'vitest';
import type { PrimaryGoal } from '@/types/onboarding';
import { preferencesUpdateFromOnboardingTrip } from './preferencesUpdateFromOnboardingTrip';

const base = {
  origin: '',
  destination: 'Tokyo',
  departureDate: '2026-05-01',
  returnDate: null,
  passengers: { adults: 1, children: 0, infants: 0 },
  tripType: 'oneWay' as const,
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [] as PrimaryGoal[],
  freeText: '',
};

describe('preferencesUpdateFromOnboardingTrip', () => {
  it('returns null when no preference fields are set', () => {
    expect(
      preferencesUpdateFromOnboardingTrip({ ...base, budgetMindset: null, travelPace: null, primaryGoals: [] })
    ).toBeNull();
  });

  it('includes travel pace when set', () => {
    const r = preferencesUpdateFromOnboardingTrip({
      ...base,
      travelPace: 'relaxed',
    });
    expect(r).toEqual({
      travelStyle: { travelPace: 'relaxed' },
    });
  });

  it('includes budget mindset and primary goals when set', () => {
    const r = preferencesUpdateFromOnboardingTrip({
      ...base,
      budgetMindset: 'bestValue',
      primaryGoals: ['food', 'culture'] as PrimaryGoal[],
    });
    expect(r).toEqual({
      travelStyle: {
        budgetMindset: 'bestValue',
        primaryGoals: ['food', 'culture'],
      },
    });
  });
});
