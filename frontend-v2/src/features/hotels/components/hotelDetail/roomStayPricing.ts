import type { RoomRate } from '@/types/hotels';
import { DEFAULT_CURRENCY } from '../../utils/hotelUtils';

/**
 * Display-only pricing for a room rate and stay length.
 *
 * Backend note: FlightLogic `netPrice` is the stay total; `integrations/flightlogic/hotel_adapter.py`
 * `_convert_room_option` currently assigns that value to both `price_per_night` and `total_price`.
 * When nights > 1, we detect duplicate/near-duplicate values and derive per-night as total ÷ nights.
 */

export interface RoomStayPricing {
  /** Total amount for the full stay (what the guest pays for the booking period). */
  total: number;
  /** Average or quoted price per night for display (never equals total when nights > 1 unless stay is 1 night). */
  perNight: number;
  /** Number of nights used for derivation (at least 1). */
  nights: number;
  currency: string;
}

const REL_EPS = 0.02; // 2% relative tolerance for float comparisons
const ABS_EPS = 0.05; // minimum currency step

function nearlyEqual(a: number, b: number): boolean {
  const scale = Math.max(Math.abs(a), Math.abs(b), 1);
  return Math.abs(a - b) <= Math.max(ABS_EPS, REL_EPS * scale);
}

function getCurrency(room: RoomRate): string {
  return room.currency ?? room.price?.currency ?? DEFAULT_CURRENCY;
}

/** Backend may serialize Decimal / FlightLogic prices as JSON strings (e.g. `"476.11"`). */
function parseAmount(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const t = value.trim();
    if (!t) return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/**
 * Resolves total vs per-night amounts for display and GTM.
 *
 * FlightLogic exposes a stay total as `netPrice`; our backend adapter currently sets both
 * `price_per_night` and `total_price` to that stay total (see `hotel_adapter._convert_room_option`).
 * When `nights > 1`, we derive per-night as `total / nights` if the two fields are duplicates
 * or if `perNight * nights` does not match `total`.
 */
export function resolveRoomStayPricing(room: RoomRate, stayNights: number): RoomStayPricing {
  const currency = getCurrency(room);
  const n = Math.max(1, stayNights > 0 ? stayNights : 1);

  const rawTotal = parseAmount(room.totalPrice ?? room.price?.amount);
  const rawPerNight = parseAmount(room.pricePerNight ?? room.price?.perNight);

  if (rawTotal == null && rawPerNight == null) {
    return { total: 0, perNight: 0, nights: n, currency };
  }

  if (rawTotal != null && rawPerNight == null) {
    const total = rawTotal;
    const perNight = n > 0 ? total / n : total;
    return { total, perNight, nights: n, currency };
  }

  if (rawTotal == null && rawPerNight != null) {
    const perNight = rawPerNight;
    const total = perNight * n;
    return { total, perNight, nights: n, currency };
  }

  const total = rawTotal as number;
  const pN = rawPerNight as number;

  if (n === 1) {
    return { total, perNight: total, nights: n, currency };
  }

  // Multi-night: detect adapter duplicate (per night === total) or near-duplicate
  if (nearlyEqual(pN, total)) {
    return { total, perNight: total / n, nights: n, currency };
  }

  const product = pN * n;
  if (nearlyEqual(product, total)) {
    return { total, perNight: pN, nights: n, currency };
  }

  // Prefer stay total as source of truth when inconsistent
  return { total, perNight: total / n, nights: n, currency };
}
