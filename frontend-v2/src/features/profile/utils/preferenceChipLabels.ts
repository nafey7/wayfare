/**
 * Value-to-label mappings for profile header preference chips.
 * Aligned with TravelStylesSection and FlightsSection option labels.
 */

const BUDGET_MINDSET_LABELS: Record<string, string> = {
  comfort: 'Comfort-focused',
  bestValue: 'Best value',
  premium: 'Premium experience',
  luxury: 'Luxury only',
};

const ACCOMMODATION_LABELS: Record<string, string> = {
  '4star': '4-star chain',
  '5star': '5-star luxury',
  unique: 'Unique stays',
  noPref: 'No preference',
};

const MAX_STOPS_LABELS: Record<string, string> = {
  nonstop: 'Non-stop',
  '1stop': '1 Stop',
  '2stops': '2+ Stops',
  any: 'Any',
};

const SEAT_PREFERENCE_LABELS: Record<string, string> = {
  window: 'Window seat',
  aisle: 'Aisle seat',
  noPreference: 'No preference',
};

export function getBudgetMindsetLabel(value: string): string | null {
  return BUDGET_MINDSET_LABELS[value] ?? null;
}

export function getAccommodationLabel(value: string): string | null {
  return ACCOMMODATION_LABELS[value] ?? null;
}

export function getMaxStopsLabel(value: string): string | null {
  return MAX_STOPS_LABELS[value] ?? null;
}

export function getSeatPreferenceLabel(value: string): string | null {
  return SEAT_PREFERENCE_LABELS[value] ?? null;
}
