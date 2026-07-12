import type { HotelGuestDetails } from '@/types/hotels';
import type { StoredPassenger } from '@/types/passengers';

/** Canonical key for matching guest names to saved passengers. */
export function normalizedNameKey(first: string, last: string): string {
  return `${first.trim().toLowerCase()}\0${last.trim().toLowerCase()}`;
}

/**
 * When profiles load or slot count changes, fill undefined slots from name+type match (one id per booking).
 */
export function inferInitialSavedPassengerMap(
  prev: Record<number, string | 'manual'>,
  savedPassengers: StoredPassenger[],
  guests: HotelGuestDetails[],
  totalSlots: number
): Record<number, string | 'manual'> {
  if (savedPassengers.length === 0 || guests.length !== totalSlots) return prev;

  let hasGap = false;
  for (let i = 0; i < totalSlots; i++) {
    if (prev[i] === undefined) {
      hasGap = true;
      break;
    }
  }
  let hasStale = false;
  for (const k of Object.keys(prev)) {
    if (Number(k) >= totalSlots) {
      hasStale = true;
      break;
    }
  }
  if (!hasGap && !hasStale) return prev;

  const nameToPassenger = new Map<string, StoredPassenger>();
  for (const p of savedPassengers) {
    const k = normalizedNameKey(p.firstName, p.lastName);
    if (!nameToPassenger.has(k)) nameToPassenger.set(k, p);
  }

  const next: Record<number, string | 'manual'> = {};
  const assignedIds = new Set<string>();
  for (let i = 0; i < totalSlots; i++) {
    if (prev[i] !== undefined) {
      next[i] = prev[i]!;
      const v = next[i]!;
      if (v !== 'manual') assignedIds.add(v);
    }
  }
  for (let i = 0; i < totalSlots; i++) {
    if (next[i] !== undefined) continue;
    const g = guests[i];
    if (!g) continue;
    const match = nameToPassenger.get(
      normalizedNameKey(g.firstName ?? '', g.lastName ?? '')
    );
    const t = match?.typeHotel ?? match?.type ?? 'adult';
    const typeOk = match && ((g.isChild && t === 'child') || (!g.isChild && t === 'adult'));
    const id = typeOk && match ? match.id : null;
    if (id && !assignedIds.has(id)) {
      next[i] = id;
      assignedIds.add(id);
    } else {
      next[i] = 'manual';
    }
  }
  return next;
}

/** One saved passenger per booking: assigning an id clears it from other slots. */
export function applySavedPassengerSelectionWithDedup(
  prev: Record<number, string | 'manual'>,
  globalIndex: number,
  value: string | 'manual',
  totalSlots: number
): Record<number, string | 'manual'> {
  const next = { ...prev };
  if (typeof value === 'string' && value !== 'manual') {
    for (let i = 0; i < totalSlots; i++) {
      if (i !== globalIndex && next[i] === value) {
        next[i] = 'manual';
      }
    }
  }
  next[globalIndex] = value;
  return next;
}
