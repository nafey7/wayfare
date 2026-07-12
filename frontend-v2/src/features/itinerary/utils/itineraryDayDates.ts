const DAY_ABBREVS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'] as const;
const MONTH_ABBREVS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] as const;

/**
 * Parse an ISO date string ("2024-06-15") into a local-midnight Date.
 *
 * Using explicit year/month/day construction instead of `new Date(isoString)` so the
 * date is always interpreted in the local timezone — `new Date("2024-06-15")` creates
 * a UTC midnight instant that shifts to the previous calendar day in UTC- timezones.
 */
function parseISODate(dateStr: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return null;
  const parts = dateStr.split('-');
  const year = Number(parts[0]);
  const month = Number(parts[1]) - 1; // 0-indexed
  const day = Number(parts[2]);
  if (isNaN(year) || isNaN(month) || isNaN(day)) return null;
  return new Date(year, month, day);
}

/**
 * Return the date label for an itinerary day, e.g. "THU 15 MAY".
 *
 * @param departureDate ISO date string ("2024-06-15"). Returns '' when absent or invalid.
 * @param dayNumber     1-indexed day number (Day 1 = departure date, Day 2 = +1 day, …).
 *
 * JS `Date` constructor overflows months naturally — new Date(2024, 0, 32) → 1 Feb 2024 —
 * so 30/31-day boundaries and leap years are handled without any manual calendar logic.
 */
export function computeItineraryDayLabel(
  departureDate: string | undefined,
  dayNumber: number,
): string {
  if (!departureDate) return '';
  if (dayNumber < 1) return '';
  const base = parseISODate(departureDate);
  if (!base) return '';
  const date = new Date(base.getFullYear(), base.getMonth(), base.getDate() + (dayNumber - 1));
  const dow = DAY_ABBREVS[date.getDay()]!;
  const day = date.getDate();
  const month = MONTH_ABBREVS[date.getMonth()]!;
  return `${dow} ${day} ${month}`;
}
