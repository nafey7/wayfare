import { addDays, format, parseISO } from 'date-fns';
import type { HotelSearchFormParams } from '@/types/hotels';

/** Destination + stay dates after shared validation (see `normalizeHotelSearchFormParams`). */
export type NormalizedHotelSearchDates = {
  destination: string;
  checkin: string;
  checkout: string;
};

/**
 * Shared validation for destination + stay dates used by the API request builder and URL deep-link helper.
 *
 * @param fillCheckout When true, missing checkout defaults to the night after check-in (URL deep-link behavior).
 * When false, both dates must be present (strict API search request).
 */
export function normalizeHotelSearchFormParams(
  params: HotelSearchFormParams,
  options: { fillCheckout: boolean }
): NormalizedHotelSearchDates | null {
  const dest = params.destination?.trim();
  if (!dest) return null;

  const checkinRaw = params.checkin?.trim() ?? '';
  if (!checkinRaw) return null;

  let checkoutRaw = params.checkout?.trim() ?? '';

  if (!checkoutRaw) {
    if (!options.fillCheckout) return null;
    try {
      const d = parseISO(checkinRaw);
      if (Number.isNaN(d.getTime())) return null;
      checkoutRaw = format(addDays(d, 1), 'yyyy-MM-dd');
    } catch {
      return null;
    }
  }

  const cin = parseISO(checkinRaw);
  const cout = parseISO(checkoutRaw);
  if (Number.isNaN(cin.getTime()) || Number.isNaN(cout.getTime())) return null;
  if (cout <= cin) return null;

  return {
    destination: dest,
    checkin: checkinRaw,
    checkout: checkoutRaw,
  };
}
