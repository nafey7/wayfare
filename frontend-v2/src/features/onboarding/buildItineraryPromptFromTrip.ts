import dayjs from 'dayjs';
import {
  BUDGET_MINDSET_PREFERENCE_OPTIONS,
  PRIMARY_GOAL_PREFERENCE_OPTIONS,
  TRAVEL_PACE_PREFERENCE_OPTIONS,
} from '@/features/onboarding/constants/travelStylePreferenceOptions';
import type { OnboardingTripDetails, PrimaryGoal } from '@/types/onboarding';

/** When return date is missing (one-way or incomplete round trip), the itinerary request assumes this many days. */
export const DEFAULT_ITINERARY_DAYS = 5;

function labelMap(options: { value: string; label: string }[]): Record<string, string> {
  return Object.fromEntries(options.map((o) => [o.value, o.label]));
}

const BUDGET_LABEL = labelMap(BUDGET_MINDSET_PREFERENCE_OPTIONS);
const PACE_LABEL = labelMap(TRAVEL_PACE_PREFERENCE_OPTIONS);
const GOAL_LABEL = labelMap(PRIMARY_GOAL_PREFERENCE_OPTIONS) as Record<PrimaryGoal, string>;

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = dayjs(iso, 'YYYY-MM-DD', true);
  if (!d.isValid()) return null;
  return d.format('D MMM YYYY');
}

function tripLengthLabel(trip: OnboardingTripDetails): string {
  const dep = trip.departureDate;
  const ret = trip.returnDate;
  if (trip.tripType === 'roundTrip' && dep && ret) {
    const d0 = dayjs(dep, 'YYYY-MM-DD', true);
    const d1 = dayjs(ret, 'YYYY-MM-DD', true);
    if (d0.isValid() && d1.isValid() && !d1.isBefore(d0)) {
      const days = d1.diff(d0, 'day') + 1;
      return `${days} day trip (${formatDate(dep)} → ${formatDate(ret)})`;
    }
  }
  return `approximately ${DEFAULT_ITINERARY_DAYS} days (no return date — plan a ${DEFAULT_ITINERARY_DAYS}-day itinerary)`;
}

/**
 * User message sent automatically on "Start planning" so the chat can build flights, hotels, and a day-by-day plan.
 */
export function buildItineraryPromptFromOnboarding(trip: OnboardingTripDetails): string {
  const lines: string[] = [
    'Please create a travel itinerary for me with the following trip details.',
  ];

  const from = trip.origin?.trim() || 'Not specified';
  const to = trip.destination?.trim() || 'Not specified';
  lines.push(`- Flying from: ${from}`);
  lines.push(`- Destination: ${to}`);

  const depFmt = formatDate(trip.departureDate);
  if (depFmt) lines.push(`- Departure date: ${depFmt}`);

  if (trip.tripType === 'roundTrip' && trip.returnDate) {
    const retFmt = formatDate(trip.returnDate);
    if (retFmt) lines.push(`- Return date: ${retFmt}`);
  } else {
    lines.push(`- Trip type: ${trip.tripType === 'oneWay' ? 'One way' : 'Round trip (return date to be confirmed)'}`);
  }

  lines.push(`- Trip length: ${tripLengthLabel(trip)}`);

  const { adults, children, infants } = trip.passengers;
  const pax: string[] = [];
  pax.push(`${adults} adult${adults === 1 ? '' : 's'}`);
  if (children > 0) pax.push(`${children} child${children === 1 ? '' : 'ren'}`);
  if (infants > 0) pax.push(`${infants} infant${infants === 1 ? '' : 's'}`);
  lines.push(`- Travelers: ${pax.join(', ')}`);

  if (trip.budgetMindset) {
    lines.push(`- Budget mindset: ${BUDGET_LABEL[trip.budgetMindset] ?? trip.budgetMindset}`);
  }
  if (trip.travelPace) {
    lines.push(`- Travel pace: ${PACE_LABEL[trip.travelPace] ?? trip.travelPace}`);
  }
  if (trip.primaryGoals.length > 0) {
    const goals = trip.primaryGoals.map((g) => GOAL_LABEL[g] ?? g);
    lines.push(`- Primary travel goals: ${goals.join(', ')}`);
  }

  return lines.join('\n');
}
