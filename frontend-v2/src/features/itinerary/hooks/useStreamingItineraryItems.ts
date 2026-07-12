/**
 * Read the streaming itinerary partial from Redux and shape it for the
 * itinerary skeleton render (#1117 piece 4d).
 *
 * Backend (``generate_itinerary`` tool) emits ``itinerary_partial``
 * custom events as the LLM streams its structured output. Each payload
 * is whatever the parser has assembled so far — day titles arrive
 * first, ``expandedContent.activities`` populate later, the final yield
 * is the complete itinerary that lands in the ``complete`` event.
 *
 * The hook returns ``{ items, active }``:
 * - ``active`` mirrors ``streamingItinerary.active`` so callers can
 *   gate UI on "are we currently streaming an itinerary".
 * - ``items`` is the partial shaped into the
 *   :class:`ItineraryItem` array the existing components expect; ``null``
 *   when no partial has arrived yet (skeleton callers render their own
 *   placeholder) or when streaming isn't active.
 *
 * Defensive about shape: backend payloads can have either camelCase or
 * snake_case keys depending on which provider's parser streams them
 * (OpenAI vs Gemini). We accept both and pick the first match.
 */

import { useMemo } from 'react';

import { useAppSelector } from '@/store/hooks';
import { selectStreamingItinerary } from '@/store/slices/chatSlice';
import type { ItineraryItem } from '../components/ItineraryDetailsComponent';

export interface StreamingItineraryItems {
  /** Shaped partial — null when streaming is inactive or no partial yet. */
  items: ItineraryItem[] | null;
  /** True between the first ``itinerary_partial`` and the terminal complete/error. */
  active: boolean;
}

export function useStreamingItineraryItems(): StreamingItineraryItems {
  const slot = useAppSelector(selectStreamingItinerary);

  return useMemo<StreamingItineraryItems>(() => {
    if (!slot.active) {
      return { items: null, active: false };
    }
    const partial = slot.partial;
    if (!partial || typeof partial !== 'object') {
      // Stream is active but no partial has arrived yet — caller should
      // render a generic "thinking" placeholder.
      return { items: null, active: true };
    }
    const rawItems = pickArray(partial, ['itineraryItems', 'itinerary_items']);
    if (!rawItems) {
      return { items: null, active: true };
    }
    const shaped = rawItems
      .map((raw) => shapeDay(raw))
      .filter((d): d is ItineraryItem => d !== null);
    return { items: shaped.length ? shaped : null, active: true };
  }, [slot]);
}

function pickArray(
  obj: Record<string, unknown>,
  keys: readonly string[],
): unknown[] | null {
  for (const k of keys) {
    const v = obj[k];
    if (Array.isArray(v)) return v;
  }
  return null;
}

function pickString(obj: Record<string, unknown>, keys: readonly string[]): string {
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === 'string') return v;
  }
  return '';
}

function pickRecord(
  obj: Record<string, unknown>,
  keys: readonly string[],
): Record<string, unknown> | null {
  for (const k of keys) {
    const v = obj[k];
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      return v as Record<string, unknown>;
    }
  }
  return null;
}

function shapeDay(raw: unknown): ItineraryItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  const day = obj.day;
  if (typeof day !== 'number') return null;

  const title = pickString(obj, ['title']);
  if (!title) return null;

  const description = pickString(obj, ['description']);
  const imageUrl = pickString(obj, ['imageUrl', 'image_url']);

  // ``expandedContent`` may be undefined during early partials (the LLM
  // has emitted the day title but not yet the activities). The
  // skeleton renderer handles the missing case by showing placeholder
  // rows.
  const expanded = pickRecord(obj, ['expandedContent', 'expanded_content']);

  return {
    day,
    title,
    description,
    imageUrl,
    expandedContent: expanded as unknown as ItineraryItem['expandedContent'],
  };
}
