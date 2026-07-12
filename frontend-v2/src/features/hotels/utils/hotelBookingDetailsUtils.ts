/**
 * Pure helpers for hotel trip booking details page.
 * Field reads prefer camelCase (RTK transformResponse) with snake_case fallbacks for nested supplier payloads.
 */
import { differenceInCalendarDays, format, isValid, parseISO } from 'date-fns';
import type { HotelTripDetailsResponse } from '@/types/hotels';

/** Guest row for the booking details passenger list (shared with the panel). */
export interface HotelGuestPassengerRow {
  roleLabel: string;
  fullName: string;
  dob?: string | null;
  nationality?: string | null;
  passportLines?: string[];
  contactLines?: string[];
}

/** Next-step checklist line (shared with booking details panel). */
export interface HotelNextStepItem {
  id: string;
  text: string;
  /** Softer body color for secondary lines (stable vs. relying on list order). */
  tone?: 'default' | 'muted';
}

/** Ordered key lists: try earlier keys first (camelCase before snake_case where both exist). */
export function pickStr(details: Record<string, unknown>, ...keys: string[]): string | null {
  for (const k of keys) {
    const v = details[k];
    if (v != null && v !== '') return String(v);
  }
  return null;
}

export function parseDateLoose(s: string | null): Date | null {
  if (!s) return null;
  const iso = parseISO(s);
  if (isValid(iso)) return iso;
  const d = new Date(s);
  return isValid(d) ? d : null;
}

/** Nights label only when `daysStr` is a plain integer string; otherwise use computed nights from dates or omit awkward "X nights" when X is non-numeric. */
export function formatStayDateLine(
  checkIn: string | null,
  checkOut: string | null,
  daysStr: string | null,
): string {
  const d0 = parseDateLoose(checkIn);
  const d1 = parseDateLoose(checkOut);
  const nightsFromDates =
    d0 && d1 ? String(differenceInCalendarDays(d1, d0)) : null;

  let nightsForLabel: string | null = null;
  if (daysStr && /^\d+$/.test(daysStr.trim())) {
    nightsForLabel = daysStr.trim();
  } else if (nightsFromDates) {
    nightsForLabel = nightsFromDates;
  }

  const nightPart = nightsForLabel
    ? `${nightsForLabel} ${Number(nightsForLabel) === 1 ? 'night' : 'nights'}`
    : '';

  if (d0 && d1) {
    if (d0.getFullYear() === d1.getFullYear() && d0.getMonth() === d1.getMonth()) {
      const left = format(d0, 'MMM d');
      const right = format(d1, 'd');
      return nightPart ? `${left}–${right} • ${nightPart}` : `${left}–${right}`;
    }
    return nightPart
      ? `${format(d0, 'MMM d, yyyy')} – ${format(d1, 'MMM d, yyyy')} • ${nightPart}`
      : `${format(d0, 'MMM d, yyyy')} – ${format(d1, 'MMM d, yyyy')}`;
  }
  if (checkIn || checkOut) {
    const a = checkIn ?? '—';
    const b = checkOut ?? '—';
    return nightPart ? `${a} – ${b} • ${nightPart}` : `${a} – ${b}`;
  }
  return nightPart || '—';
}

export function collectHotelImages(details: Record<string, unknown>): string[] {
  const out: string[] = [];
  const single = pickStr(
    details,
    'image',
    'imageUrl',
    'thumbnailUrl',
    'thumbnail',
    'hotelImageUrl',
  );
  if (single) out.push(single);
  const imgs = details.images;
  if (Array.isArray(imgs)) {
    for (const x of imgs) {
      if (typeof x === 'string' && x) out.push(x);
      else if (x && typeof x === 'object' && 'url' in x) {
        const u = (x as { url?: unknown }).url;
        if (typeof u === 'string' && u) out.push(u);
      }
    }
  }
  const rooms = details.rooms as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(rooms)) {
    for (const r of rooms) {
      const u = pickStr(r, 'image', 'imageUrl');
      if (u) out.push(u);
    }
  }
  return [...new Set(out)];
}

export function buildMapsHref(details: Record<string, unknown>): string | null {
  const latRaw = details.latitude ?? details.hotel_latitude ?? details.lat;
  const lngRaw = details.longitude ?? details.hotel_longitude ?? details.lng;
  const lat = typeof latRaw === 'number' ? latRaw : parseFloat(String(latRaw ?? ''));
  const lng = typeof lngRaw === 'number' ? lngRaw : parseFloat(String(lngRaw ?? ''));
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  }
  const addr = pickStr(details, 'address');
  const city = pickStr(details, 'city');
  const q = [addr, city].filter(Boolean).join(', ');
  if (q) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
  return null;
}

export function mapGuests(details: Record<string, unknown>): HotelGuestPassengerRow[] {
  const guests = details.guests as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(guests) || guests.length === 0) {
    return [{ roleLabel: 'Guest 1', fullName: '—' }];
  }
  let adultIdx = 0;
  let childIdx = 0;
  return guests.map((g, idx) => {
    const title = String(g.title ?? '');
    const first = String(g.first_name ?? g.firstName ?? '');
    const last = String(g.last_name ?? g.lastName ?? '');
    const full = [title, first, last].filter(Boolean).join(' ') || `Guest ${idx + 1}`;
    const isChild = Boolean(g.isChild ?? g.is_child);
    const roleLabel = isChild
      ? `Child ${++childIdx}`
      : `Adult ${++adultIdx}`;
    const dob = pickStr(g, 'date_of_birth', 'dob', 'dateOfBirth');
    const nat = pickStr(g, 'nationality');
    const passNum = pickStr(g, 'passport_number', 'passportNumber');
    const passC = pickStr(g, 'passport_country', 'passportCountry');
    const passExp = pickStr(g, 'passport_expiry', 'passportExpiry');
    const passportLines: string[] = [];
    if (passNum || passC) {
      passportLines.push([passNum, passC].filter(Boolean).join(' · ') || '—');
    }
    if (passExp) passportLines.push(`Exp: ${passExp}`);
    const email = pickStr(g, 'email');
    const phone = pickStr(g, 'phone', 'phone_number', 'phoneNumber');
    const contactLines = [email, phone].filter((x): x is string => Boolean(x));
    return {
      roleLabel,
      fullName: full,
      dob: dob ?? undefined,
      nationality: nat ?? undefined,
      passportLines: passportLines.length ? passportLines : undefined,
      contactLines: contactLines.length ? contactLines : undefined,
    };
  });
}

const NEGATIVE_PAYMENT = new Set([
  'failed',
  'declined',
  'cancelled',
  'canceled',
  'refunded',
  'pending',
  'requires_payment_method',
  'processing',
]);

const POSITIVE_PAYMENT = new Set([
  'paid',
  'captured',
  'succeeded',
  'completed',
  'approved',
  'paid_out',
]);

/**
 * Whether to show the green "Approved" chip next to the payment amount.
 * Conservative: unknown or ambiguous states do not show the chip.
 */
export function deriveShowPaymentApprovedChip(
  detail: HotelTripDetailsResponse | null,
  bd: Record<string, unknown>,
): boolean {
  const bookingStatus = detail?.bookingStatus?.toUpperCase() ?? '';
  if (bookingStatus === 'CANCELLED') return false;
  if (bookingStatus === 'PENDING') return false;

  const payStatusRaw = pickStr(
    bd,
    'paymentStatus',
    'payment_status',
    'paymentState',
    'payment_state',
  );
  if (payStatusRaw) {
    const u = payStatusRaw.toLowerCase().replace(/\s+/g, '_');
    if (NEGATIVE_PAYMENT.has(u)) return false;
    if (POSITIVE_PAYMENT.has(u)) return true;
    return false;
  }

  if (bookingStatus === 'BOOKED') return true;

  const paidAt = pickStr(
    bd,
    'paidAt',
    'paid_at',
    'paymentDate',
    'payment_date',
  );
  if (paidAt) return true;

  return false;
}
