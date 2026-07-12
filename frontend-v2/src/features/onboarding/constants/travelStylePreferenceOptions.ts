import type { PreferenceOption } from '@/features/profile/types/preferences';

/**
 * Onboarding trip step — same option ids/labels as /profile TravelStylesSection
 * for Travel Pace, Budget Mindset, and Primary travel goal only.
 */
export const TRAVEL_PACE_PREFERENCE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'relaxed', label: 'Relaxed', value: 'relaxed' },
  { id: 'balanced', label: 'Balanced', value: 'balanced' },
  { id: 'packed', label: 'Packed', value: 'packed' },
  { id: 'ultraEfficient', label: 'Ultra-efficient (power traveler)', value: 'ultraEfficient' },
];

export const BUDGET_MINDSET_PREFERENCE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'comfort', label: 'Comfort-focused', value: 'comfort' },
  { id: 'bestValue', label: 'Best value', value: 'bestValue' },
  { id: 'premium', label: 'Premium experience', value: 'premium' },
  { id: 'luxury', label: 'Luxury only', value: 'luxury' },
];

export const PRIMARY_GOAL_PREFERENCE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'business', label: 'Business', value: 'business' },
  { id: 'culture', label: 'Culture & history', value: 'culture' },
  { id: 'food', label: 'Food & wine', value: 'food' },
  { id: 'nature', label: 'Nature & outdoors', value: 'nature' },
  { id: 'family', label: 'Family-friendly', value: 'family' },
  { id: 'luxury', label: 'Luxury & fine experiences', value: 'luxury' },
  { id: 'hidden', label: 'Hidden gems', value: 'hidden' },
  { id: 'nightlife', label: 'Nightlife', value: 'nightlife' },
  { id: 'photography', label: 'Photography spots', value: 'photography' },
];
