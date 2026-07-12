import { describe, it, expect } from 'vitest';

import {
  buildItineraryPromptFromOnboarding,
  DEFAULT_ITINERARY_DAYS,
} from './buildItineraryPromptFromTrip';
import type { OnboardingTripDetails } from '@/types/onboarding';

const base: OnboardingTripDetails = {
  origin: 'LON',
  destination: 'PAR',
  departureDate: '2026-06-10',
  returnDate: '2026-06-15',
  passengers: { adults: 2, children: 0, infants: 0 },
  tripType: 'roundTrip',
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [],
  freeText: '',
};

describe('buildItineraryPromptFromOnboarding', () => {
  it('uses inclusive day count for round trip with return date', () => {
    const p = buildItineraryPromptFromOnboarding(base);
    expect(p).toContain('6 day trip');
    expect(p).toMatch(/10 Jun 2026/);
    expect(p).toMatch(/15 Jun 2026/);
  });

  it('defaults to 5 days when return date is missing', () => {
    const p = buildItineraryPromptFromOnboarding({
      ...base,
      returnDate: null,
      tripType: 'oneWay',
    });
    expect(p).toContain(String(DEFAULT_ITINERARY_DAYS));
    expect(p).toContain('no return date');
  });

  it('includes optional preferences', () => {
    const p = buildItineraryPromptFromOnboarding({
      ...base,
      budgetMindset: 'comfort',
      travelPace: 'relaxed',
      primaryGoals: ['food', 'culture'],
    });
    expect(p).toContain('Comfort-focused');
    expect(p).toContain('Relaxed');
    expect(p).toContain('Food & wine');
  });
});
