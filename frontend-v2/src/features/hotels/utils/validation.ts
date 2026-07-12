/**
 * Hotel guest/contact validation utilities.
 * E.164: + followed by 1–15 digits (no spaces/dashes in stored value).
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
/** E.164: optional +, then 7–15 digits (allowing leading + and digits only). */
const E164_REGEX = /^\+?[0-9]{7,15}$/;

/**
 * Validates email format.
 */
export function validateEmail(value: string): boolean {
  return EMAIL_REGEX.test((value ?? '').trim());
}

/**
 * Builds E.164 phone from country dial code and local number.
 * @param countryCode - Dial code without + (e.g. "1", "44")
 * @param localNumber - Local number (digits only, strips non-digits)
 */
export function buildE164Phone(countryCode: string, localNumber: string): string {
  const digits = (localNumber ?? '').replace(/\D/g, '');
  const code = (countryCode ?? '').replace(/\D/g, '');
  if (!code || !digits) return '';
  return `+${code}${digits}`;
}

/**
 * Validates that a string is valid E.164 (e.g. +15551234567).
 */
export function validatePhoneE164(value: string): boolean {
  const v = (value ?? '').trim();
  return v.length > 0 && E164_REGEX.test(v.replace(/\s/g, ''));
}

/**
 * Validates country code + local number together form a valid E.164.
 */
export function validatePhoneWithCountryCode(
  countryCode: string,
  localNumber: string
): boolean {
  const e164 = buildE164Phone(countryCode, localNumber);
  return validatePhoneE164(e164);
}
