/**
 * Passenger storage utilities (issue #418).
 * Maps between stored passenger API responses and form data.
 */
import type { StoredPassenger } from '@/types/passengers';

/** Form data shape for passenger details (matches PassengerFormData in PassengerInfoPage). */
export interface PassengerFormData {
  title: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  nationality: string;
  passportNumber: string;
  passportExpiry: string;
  passportCountry: string;
}

/** Minimum age for adult passengers (FlightLogic/industry: ADT = 12+) */
const ADULT_MIN_AGE = 12;

/** Compute age in full years from date of birth (YYYY-MM-DD). Returns null if invalid. */
export function getAgeFromDateOfBirth(dateOfBirth: string | null | undefined): number | null {
  if (!dateOfBirth?.trim()) return null;
  const match = dateOfBirth.trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  const [, y, m, d] = match;
  const dob = new Date(parseInt(y!, 10), parseInt(m!, 10) - 1, parseInt(d!, 10));
  if (isNaN(dob.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) age -= 1;
  return age;
}

/** Child age range (FlightLogic/industry: CHD = 2-11). */
const CHILD_MIN_AGE = 2;
const CHILD_MAX_AGE = 11;
/** Infant max age (FlightLogic/industry: INF = under 2). */
const INFANT_MAX_AGE = 1;

/** Validate adult passenger age (must be >= 12). Returns error message or null if valid. */
export function validateAdultAge(dateOfBirth: string | null | undefined): string | null {
  if (!dateOfBirth?.trim()) return null; // Required-field validation handles empty
  const age = getAgeFromDateOfBirth(dateOfBirth);
  if (age === null) return null; // Invalid format handled elsewhere
  if (age < 0) return 'Date of birth cannot be in the future';
  if (age < ADULT_MIN_AGE) {
    return `Adult passengers must be at least ${ADULT_MIN_AGE} years old. Current age: ${age} years.`;
  }
  return null;
}

/** Validate child passenger age (must be 2-11). Returns error message or null if valid. */
export function validateChildAge(dateOfBirth: string | null | undefined): string | null {
  if (!dateOfBirth?.trim()) return null;
  const age = getAgeFromDateOfBirth(dateOfBirth);
  if (age === null) return null;
  if (age < 0) return 'Date of birth cannot be in the future';
  if (age < CHILD_MIN_AGE) {
    return `Child passengers must be at least ${CHILD_MIN_AGE} years old. Current age: ${age} years. Passengers under 2 must be booked as infants.`;
  }
  if (age > CHILD_MAX_AGE) {
    return `Child passengers must be under 12 years old. Current age: ${age} years. Passengers 12+ must be booked as adults.`;
  }
  return null;
}

/** Validate infant passenger age (must be under 2). Returns error message or null if valid. */
export function validateInfantAge(dateOfBirth: string | null | undefined): string | null {
  if (!dateOfBirth?.trim()) return null;
  const age = getAgeFromDateOfBirth(dateOfBirth);
  if (age === null) return null;
  if (age < 0) return 'Date of birth cannot be in the future';
  if (age > INFANT_MAX_AGE) {
    return `Infant passengers must be under 2 years old. Current age: ${age} years. Passengers 2+ must be booked as children or adults.`;
  }
  return null;
}

/** Masked passport number pattern (e.g. ****4589) */
const MASKED_NUMBER_PATTERN = /^\*{4}\d{1,10}$/;
/** Masked expiry pattern (e.g. 2028-**-**) */
const MASKED_EXPIRY_PATTERN = /^\d{4}-\*\*-\*\*$/;

/** Detect if value looks masked (not usable for booking). */
export function isMaskedPassportValue(
  value: string | null | undefined,
  kind: 'number' | 'expiry'
): boolean {
  if (value == null || value === '') return true; // Treat null/empty as "nothing to send"
  return kind === 'number'
    ? MASKED_NUMBER_PATTERN.test(value.trim())
    : MASKED_EXPIRY_PATTERN.test(value.trim());
}

/** Detect if frequent flyer number is masked (same pattern as passport: ****7890). */
export function isMaskedFrequentFlyerValue(
  value: string | null | undefined
): boolean {
  if (value == null || value === '') return true;
  return MASKED_NUMBER_PATTERN.test(value.trim());
}

/** Detect if a sensitive value is masked (for use in update payloads). */
export function isMaskedSensitiveValue(
  value: string | null | undefined,
  kind: 'passport_number' | 'passport_expiry' | 'frequent_flyer'
): boolean {
  if (value == null || value === '') return true;
  switch (kind) {
    case 'passport_number':
      return isMaskedPassportValue(value, 'number');
    case 'passport_expiry':
      return isMaskedPassportValue(value, 'expiry');
    case 'frequent_flyer':
      return isMaskedFrequentFlyerValue(value);
    default:
      return false;
  }
}

/** True when passport fields are present and not masked. */
export function hasValidPassportData(p: {
  passportNumber?: string;
  passportExpiry?: string;
  passportCountry?: string;
}): boolean {
  const num = p.passportNumber?.trim();
  const exp = p.passportExpiry?.trim();
  const country = p.passportCountry?.trim();
  if (!num || !exp || !country) return false;
  if (isMaskedPassportValue(num, 'number')) return false;
  if (isMaskedPassportValue(exp, 'expiry')) return false;
  return true;
}

/** Map stored passenger (API response) to form data. Masked fields shown as-is (e.g. ****4589). */
export function storedPassengerToFormData(s: StoredPassenger): PassengerFormData {
  return {
    title: s.title,
    firstName: s.firstName,
    lastName: s.lastName,
    dateOfBirth: s.dateOfBirth,
    nationality: s.nationality,
    passportNumber: s.passportNumber ?? '',
    passportExpiry: s.passportExpiry ?? '',
    passportCountry: s.passportCountry ?? '',
  };
}

/** Format saved passenger for dropdown label. */
export function formatSavedPassengerLabel(s: StoredPassenger): string {
  const name = `${s.firstName} ${s.lastName}`.trim() || 'Saved passenger';
  const extra = s.passportNumber ? ` (${s.passportNumber})` : '';
  return `${name}${extra}`;
}
