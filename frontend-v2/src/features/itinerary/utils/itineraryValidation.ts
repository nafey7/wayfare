import type { ItineraryDetailsComponentProps } from '../components';

type ItineraryDetailsPropsWithoutHover = Omit<
  ItineraryDetailsComponentProps,
  'onTravelBarHover'
>;

/**
 * Type guard for itinerary data passed to ItineraryDetailsComponent.
 * Validates that data has a non-empty itineraryItems array with required fields.
 */
export function isValidItineraryProps(
  data: unknown
): data is ItineraryDetailsPropsWithoutHover {
  if (!data || typeof data !== 'object') return false;
  const d = data as Record<string, unknown>;
  const items = d.itineraryItems;
  if (!Array.isArray(items) || items.length === 0) return false;
  for (const item of items) {
    if (!item || typeof item !== 'object') return false;
    const i = item as Record<string, unknown>;
    if (typeof i.day !== 'number') return false;
    if (typeof i.title !== 'string') return false;
    if (typeof i.description !== 'string') return false;
    if (typeof i.imageUrl !== 'string') return false;
  }
  return true;
}
