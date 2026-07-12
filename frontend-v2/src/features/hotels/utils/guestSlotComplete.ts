import type { HotelGuestDetails } from '@/types/hotels';

export interface GuestSlotForComplete {
  isChild: boolean;
}

/**
 * Whether this slot’s guest row is valid for “complete” UI (summary, payment).
 * When `g` is missing, the slot is treated as complete until `touched` — avoids showing
 * errors before the user has interacted or submitted (same UX as empty manual fields).
 */
export function isGuestSlotComplete(
  g: HotelGuestDetails | undefined,
  slot: GuestSlotForComplete,
  touched: boolean
): boolean {
  if (!g) return !touched;
  const base =
    !!g.title &&
    !!(g.firstName ?? '').trim() &&
    !!(g.lastName ?? '').trim() &&
    (!slot.isChild || (g.age != null && g.age >= 0 && g.age <= 17));
  return base;
}
