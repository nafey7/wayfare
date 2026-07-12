import { differenceInCalendarDays, format, isValid, parseISO } from 'date-fns';

import type { LinkedBookings, SavedItinerary } from '@/types/itineraries';

/** Display fields for saved-itinerary cards (profile upcoming trips, itineraries list). */
export interface SavedItineraryCardSummary {
  id: string;
  /** Destination without trailing country (e.g. "Paris" from "Paris, France"). */
  destinationLabel: string;
  origin: string;
  /** First day hero image, or null if missing. */
  heroImageUrl: string | null;
  /** Human-readable date range or single date. */
  dateRangeLabel: string;
  /** e.g. "3 nights" or "—". */
  nightsLabel: string;
  /** e.g. "2 adults" or "2 adults, 1 child". */
  passengersLabel: string;
  /** Number of itinerary day blocks (for list page). */
  dayCount: number;
  /** First day title preview (for list page). */
  preview: string;
  /** True when GET /itineraries included linked flight or hotel booking refs. */
  hasLinkedBookings: boolean;
  /** Full linked bookings data from the API (flight + hotel refs and event summaries). */
  linkedBookings: LinkedBookings | null;
}

/** Whether the itinerary has at least one linked BOOKED flight or hotel (from API). */
export function itineraryHasLinkedBookings(linkedBookings: LinkedBookings | undefined): boolean {
  if (!linkedBookings) return false;
  const flights = linkedBookings.flightVoyaReferences?.length ?? 0;
  const hotels = linkedBookings.hotelVoyaReferences?.length ?? 0;
  return flights > 0 || hotels > 0;
}

function getStructuredItems(structured: Record<string, unknown>): unknown[] {
  const items = structured.itineraryItems;
  return Array.isArray(items) ? items : [];
}

function firstItemImageUrl(structured: Record<string, unknown>): string | null {
  const items = getStructuredItems(structured);
  const first = items[0] as Record<string, unknown> | undefined;
  if (!first || typeof first !== 'object') return null;
  const url = first.imageUrl;
  return typeof url === 'string' && url.trim() ? url.trim() : null;
}

/**
 * Strip trailing country from destination when formatted as "City, Country".
 */
export function destinationWithoutCountry(destination: string | undefined | null): string {
  if (destination == null || !String(destination).trim()) return 'Unknown';
  const s = String(destination).trim();
  const idx = s.indexOf(',');
  if (idx === -1) return s;
  return s.slice(0, idx).trim() || s;
}

function formatIsoDateLabel(iso: string): string {
  const parsed = parseISO(iso);
  if (!isValid(parsed)) return iso;
  return format(parsed, 'MMM d, yyyy');
}

function buildDateRangeLabel(departure: string | undefined, returnDate: string | undefined): string {
  if (departure && returnDate) {
    return `${formatIsoDateLabel(departure)} – ${formatIsoDateLabel(returnDate)}`;
  }
  if (departure) return formatIsoDateLabel(departure);
  if (returnDate) return formatIsoDateLabel(returnDate);
  return '—';
}

function buildNightsLabel(
  departure: string | undefined,
  returnDate: string | undefined,
  itemCount: number,
): string {
  if (departure && returnDate) {
    const d0 = parseISO(departure);
    const d1 = parseISO(returnDate);
    if (isValid(d0) && isValid(d1)) {
      const nights = Math.max(0, differenceInCalendarDays(d1, d0));
      return `${nights} ${nights === 1 ? 'night' : 'nights'}`;
    }
  }
  if (itemCount > 1) {
    const fallback = Math.max(0, itemCount - 1);
    return `${fallback} ${fallback === 1 ? 'night' : 'nights'}`;
  }
  if (itemCount === 1) return '1 night';
  return '—';
}

function buildPassengersLabel(
  adults: number | undefined,
  children: number | undefined,
  infants: number | undefined,
): string {
  const a = typeof adults === 'number' && !Number.isNaN(adults) ? adults : 0;
  const c = typeof children === 'number' && !Number.isNaN(children) ? children : 0;
  const i = typeof infants === 'number' && !Number.isNaN(infants) ? infants : 0;
  const total = a + c + i;
  if (total === 0) return '—';

  const parts: string[] = [];
  if (a > 0) parts.push(`${a} ${a === 1 ? 'adult' : 'adults'}`);
  if (c > 0) parts.push(`${c} ${c === 1 ? 'child' : 'children'}`);
  if (i > 0) parts.push(`${i} ${i === 1 ? 'infant' : 'infants'}`);
  return parts.join(', ');
}

/**
 * Maps a saved itinerary API row to card display fields.
 */
function metaDateString(meta: Record<string, unknown>, camelKey: string): string | undefined {
  const v = meta[camelKey];
  if (typeof v === 'string' && v) return v;
  return undefined;
}

export function getSavedItineraryCardSummary(itinerary: SavedItinerary): SavedItineraryCardSummary {
  const meta = (itinerary.tripMeta ?? {}) as Record<string, unknown>;
  const structured = (itinerary.structuredItinerary ?? {}) as Record<string, unknown>;
  const items = getStructuredItems(structured);
  const firstDay = items[0] as { title?: string } | undefined;

  const rawDestination = meta.destination as string | undefined;
  const destinationLabel = destinationWithoutCountry(rawDestination);
  const origin = typeof meta.origin === 'string' ? meta.origin : '';

  const departureDate = metaDateString(meta, 'departureDate');
  const returnDate = metaDateString(meta, 'returnDate');

  const adults = meta.adults as number | undefined;
  const children = meta.children as number | undefined;
  const infants = meta.infants as number | undefined;

  return {
    id: itinerary.id,
    destinationLabel,
    origin,
    heroImageUrl: firstItemImageUrl(structured),
    dateRangeLabel: buildDateRangeLabel(departureDate, returnDate),
    nightsLabel: buildNightsLabel(departureDate, returnDate, items.length),
    passengersLabel: buildPassengersLabel(adults, children, infants),
    dayCount: items.length,
    preview: typeof firstDay?.title === 'string' ? firstDay.title : '',
    hasLinkedBookings: itineraryHasLinkedBookings(itinerary.linkedBookings),
    linkedBookings: itinerary.linkedBookings ?? null,
  };
}
