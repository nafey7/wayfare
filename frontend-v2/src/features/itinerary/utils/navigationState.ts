import type { ItineraryNavigationState } from '../types';

/**
 * Safely parse location.state into ItineraryNavigationState.
 * Returns undefined when state is invalid or missing structuredItinerary with itineraryItems array.
 */
export function parseItineraryNavigationState(
  state: unknown
): ItineraryNavigationState | undefined {
  if (!state || typeof state !== 'object') return undefined;
  const s = state as Record<string, unknown>;
  const si = s.structuredItinerary;
  const items = (si as Record<string, unknown> | undefined)?.itineraryItems;
  const valid =
    si &&
    typeof si === 'object' &&
    Array.isArray(items);
  if (!valid) return undefined;
  return state as ItineraryNavigationState;
}
