type DateLike = Date | string | null | undefined;

/** Returns true if the date (Date object or YYYY-MM-DD string) is strictly before today (local midnight). */
export function isPastDate(date: DateLike): boolean {
  if (!date) return false;
  let d: Date;
  if (date instanceof Date) {
    d = new Date(date);
  } else {
    const dateStr = (date as string).slice(0, 10);
    const parts = dateStr.split('-');
    d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    if (Number.isNaN(d.getTime())) return false;
  }
  d.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

export interface DateSlot {
  label: string;
  value: DateLike;
}

/**
 * Checks a list of labelled date slots for past dates.
 * Returns the first error message found, or null if all are valid.
 * Skips null/undefined slots (presence checks are the caller's responsibility).
 */
export function validateDatesNotInPast(slots: DateSlot[]): string | null {
  for (const { label, value } of slots) {
    if (value && isPastDate(value)) {
      return `${label} cannot be in the past.`;
    }
  }
  return null;
}
