import { Stack } from '@mantine/core';
import {
  ChipSection,
  RadioField,
} from './PreferenceFieldComponents';
import type { PreferenceOption } from '@/features/profile/types/preferences';
import type { TravelStylePreferences } from '@/types/profile';

const TRAVEL_PACE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'relaxed', label: 'Relaxed', value: 'relaxed' },
  { id: 'balanced', label: 'Balanced', value: 'balanced' },
  { id: 'packed', label: 'Packed', value: 'packed' },
  { id: 'ultraEfficient', label: 'Ultra-efficient (power traveler)', value: 'ultraEfficient' },
];

const BUDGET_OPTIONS: PreferenceOption<string>[] = [
  { id: 'comfort', label: 'Comfort-focused', value: 'comfort' },
  { id: 'bestValue', label: 'Best value', value: 'bestValue' },
  { id: 'premium', label: 'Premium experience', value: 'premium' },
  { id: 'luxury', label: 'Luxury only', value: 'luxury' },
];

// 'unique' (boutique/unique) is a valid backend value but is not offered here — users who saved
// it retain the preference server-side and enter the preference-sort path, but see no radio
// selected until they explicitly choose a new option.
const ACCOMMODATION_OPTIONS: PreferenceOption<string>[] = [
  { id: '4star', label: '4-star chain', value: '4' },
  { id: '5star', label: '5-star luxury', value: '5' },
  { id: 'noPref', label: 'No preference', value: 'noPref' },
];

const ACTIVITY_OPTIONS: PreferenceOption<string>[] = [
  { id: 'structured', label: 'Structured days', value: 'structured' },
  { id: 'guided', label: 'Guided tours preferred', value: 'guided' },
  { id: 'freeTime', label: 'Free time built-in', value: 'freeTime' },
  { id: 'selfExplore', label: 'Self-exploration preferred', value: 'selfExplore' },
  { id: 'noPref', label: 'No preference', value: 'noPref' },
];

const PRIMARY_GOAL_OPTIONS: PreferenceOption<string>[] = [
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

const GETTING_AROUND_OPTIONS: PreferenceOption<string>[] = [
  { id: 'public', label: 'Public transport', value: 'public' },
  { id: 'rideshare', label: 'Rideshare (Uber/Bolt)', value: 'rideshare' },
  { id: 'walking', label: 'Walking-friendly areas', value: 'walking' },
  { id: 'rental', label: 'Rental car', value: 'rental' },
  { id: 'private', label: 'Private transfers', value: 'private' },
  { id: 'trains', label: 'Trains between cities', value: 'trains' },
  { id: 'noPref', label: 'No preference', value: 'noPref' },
];

export interface TravelStylesSectionProps {
  preferences: TravelStylePreferences;
  documentExists: boolean;
  onChange: (prefs: TravelStylePreferences) => void;
}

/**
 * Travel styles subsection — Travel Pace, Budget Mindset, Accommodation, Activity Density,
 * Primary travel goal, and Getting Around preferences.
 * Only populates when documentExists; otherwise shows empty state.
 */
export function TravelStylesSection({
  preferences,
  documentExists,
  onChange,
}: TravelStylesSectionProps) {
  const travelPace = documentExists ? (preferences.travelPace ?? '') : '';
  const budgetMindset = documentExists ? (preferences.budgetMindset ?? '') : '';
  const accommodation = documentExists ? (preferences.accommodation ?? '') : '';
  const activityDensity = documentExists ? (preferences.activityDensity ?? '') : '';
  const primaryGoals = new Set(preferences.primaryGoals ?? []);
  const gettingAround = new Set(preferences.gettingAround ?? []);

  const handleTogglePrimaryGoals = (value: string) => {
    const arr = preferences.primaryGoals ?? [];
    const next = new Set(arr);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange({ ...preferences, primaryGoals: Array.from(next) });
  };
  const handleToggleGettingAround = (value: string) => {
    const arr = preferences.gettingAround ?? [];
    const next = new Set(arr);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange({ ...preferences, gettingAround: Array.from(next) });
  };

  return (
    <Stack gap={24}>
      <RadioField
        label="Travel Pace"
        options={TRAVEL_PACE_OPTIONS}
        value={travelPace || null}
        onChange={(v) => onChange({ ...preferences, travelPace: v || null })}
      />
      <RadioField
        label="Budget Mindset"
        options={BUDGET_OPTIONS}
        value={budgetMindset || null}
        onChange={(v) => onChange({ ...preferences, budgetMindset: v || null })}
      />
      <RadioField
        label="Accommodation Preference Level"
        options={ACCOMMODATION_OPTIONS}
        value={accommodation || null}
        onChange={(v) => onChange({ ...preferences, accommodation: (!v || v === 'noPref') ? null : v })}
      />
      <RadioField
        label="Activity Density Preference"
        options={ACTIVITY_OPTIONS}
        value={activityDensity || null}
        onChange={(v) => onChange({ ...preferences, activityDensity: v || null })}
      />
      <ChipSection
        label="Primary travel goal"
        options={PRIMARY_GOAL_OPTIONS}
        selectedValues={primaryGoals}
        onToggle={handleTogglePrimaryGoals}
      />
      <ChipSection
        label="Getting Around"
        options={GETTING_AROUND_OPTIONS}
        selectedValues={gettingAround}
        onToggle={handleToggleGettingAround}
      />
    </Stack>
  );
}
