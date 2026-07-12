/**
 * Age in full years from an ISO date-of-birth string (`YYYY-MM-DD`).
 * Returns `undefined` if the string cannot be parsed to a valid calendar date.
 */
export function ageFromIsoDateOfBirth(dob: string | null | undefined): number | undefined {
  const trimmed = dob?.trim();
  if (!trimmed) return undefined;
  const m = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return undefined;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(d)) return undefined;
  const birth = new Date(y, mo - 1, d);
  if (birth.getFullYear() !== y || birth.getMonth() !== mo - 1 || birth.getDate() !== d) {
    return undefined;
  }
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}
