import { describe, it, expect } from 'vitest';
import {
  storedPassengerToFormData,
  formatSavedPassengerLabel,
  isMaskedPassportValue,
  isMaskedFrequentFlyerValue,
  isMaskedSensitiveValue,
  hasValidPassportData,
  getAgeFromDateOfBirth,
  validateAdultAge,
  validateChildAge,
  validateInfantAge,
} from './passengerStorageUtils';
import type { StoredPassenger } from '@/types/passengers';

const mockStoredPassenger: StoredPassenger = {
  id: 'p1',
  userId: 'u1',
  title: 'Mr',
  firstName: 'John',
  lastName: 'Doe',
  dateOfBirth: '1990-05-15',
  nationality: 'US',
  email: 'john@example.com',
  phone: '+1555123456',
  passportNumber: '****4589',
  passportExpiry: '2028-**-**',
  passportCountry: 'US',
  frequentFlyerNumber: null,
  type: 'adult',
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
};

describe('passengerStorageUtils', () => {
  describe('storedPassengerToFormData', () => {
    it('maps stored passenger to form data with masked fields preserved', () => {
      const result = storedPassengerToFormData(mockStoredPassenger);
      expect(result.title).toBe('Mr');
      expect(result.firstName).toBe('John');
      expect(result.lastName).toBe('Doe');
      expect(result.dateOfBirth).toBe('1990-05-15');
      expect(result.nationality).toBe('US');
      expect(result.passportNumber).toBe('****4589');
      expect(result.passportExpiry).toBe('2028-**-**');
      expect(result.passportCountry).toBe('US');
    });

    it('converts null sensitive fields to empty string', () => {
      const stored = { ...mockStoredPassenger, passportNumber: null, passportExpiry: null, passportCountry: null };
      const result = storedPassengerToFormData(stored);
      expect(result.passportNumber).toBe('');
      expect(result.passportExpiry).toBe('');
      expect(result.passportCountry).toBe('');
    });
  });

  describe('formatSavedPassengerLabel', () => {
    it('formats name with masked passport when present', () => {
      expect(formatSavedPassengerLabel(mockStoredPassenger)).toBe('John Doe (****4589)');
    });

    it('formats name only when no passport', () => {
      const noPassport = { ...mockStoredPassenger, passportNumber: null };
      expect(formatSavedPassengerLabel(noPassport)).toBe('John Doe');
    });

    it('returns fallback when name is empty (without passport)', () => {
      const empty = { ...mockStoredPassenger, firstName: '', lastName: '', passportNumber: null };
      expect(formatSavedPassengerLabel(empty)).toBe('Saved passenger');
    });
  });

  describe('isMaskedPassportValue', () => {
    it('returns true for masked passport number', () => {
      expect(isMaskedPassportValue('****4589', 'number')).toBe(true);
    });
    it('returns false for real passport number', () => {
      expect(isMaskedPassportValue('AB1234567', 'number')).toBe(false); // pragma: allowlist secret
    });
    it('returns true for masked expiry', () => {
      expect(isMaskedPassportValue('2028-**-**', 'expiry')).toBe(true);
    });
    it('returns false for real expiry date', () => {
      expect(isMaskedPassportValue('2028-05-15', 'expiry')).toBe(false);
    });
    it('returns true for null or empty (treat as nothing to send)', () => {
      expect(isMaskedPassportValue(null, 'number')).toBe(true);
      expect(isMaskedPassportValue(undefined, 'number')).toBe(true);
      expect(isMaskedPassportValue('', 'number')).toBe(true);
    });
    it('returns false for edge case foo**bar (strict pattern, not broad)', () => {
      expect(isMaskedPassportValue('foo**bar', 'number')).toBe(false);
    });
  });

  describe('isMaskedFrequentFlyerValue', () => {
    it('returns true for masked frequent flyer', () => {
      expect(isMaskedFrequentFlyerValue('****7890')).toBe(true);
    });
    it('returns false for real frequent flyer number', () => {
      expect(isMaskedFrequentFlyerValue('FF1234567')).toBe(false);
    });
    it('returns true for null or empty', () => {
      expect(isMaskedFrequentFlyerValue(null)).toBe(true);
      expect(isMaskedFrequentFlyerValue('')).toBe(true);
    });
  });

  describe('isMaskedSensitiveValue', () => {
    it('delegates to correct helper by kind', () => {
      expect(isMaskedSensitiveValue('****4589', 'passport_number')).toBe(true);
      expect(isMaskedSensitiveValue('2028-**-**', 'passport_expiry')).toBe(true);
      expect(isMaskedSensitiveValue('****7890', 'frequent_flyer')).toBe(true);
      expect(isMaskedSensitiveValue('AB1234567', 'passport_number')).toBe(false); // pragma: allowlist secret
    });
  });

  describe('getAgeFromDateOfBirth', () => {
    it('returns null for empty or invalid input', () => {
      expect(getAgeFromDateOfBirth(null)).toBeNull();
      expect(getAgeFromDateOfBirth('')).toBeNull();
      expect(getAgeFromDateOfBirth('  ')).toBeNull();
      expect(getAgeFromDateOfBirth('not-a-date')).toBeNull();
    });

    it('calculates age correctly for valid DOB', () => {
      const currentYear = new Date().getFullYear();
      expect(getAgeFromDateOfBirth(`${currentYear - 25}-01-15`)).toBe(25);
      // Use Jan 1 of 12 years ago so birthday has passed by any test run date
      expect(getAgeFromDateOfBirth(`${currentYear - 12}-01-01`)).toBe(12);
    });

    it('returns 11 for 11-year-old (boundary)', () => {
      const currentYear = new Date().getFullYear();
      expect(getAgeFromDateOfBirth(`${currentYear - 11}-01-01`)).toBe(11);
    });
  });

  describe('validateAdultAge', () => {
    it('returns null for valid adult (12+)', () => {
      const currentYear = new Date().getFullYear();
      expect(validateAdultAge(`${currentYear - 25}-01-15`)).toBeNull();
      expect(validateAdultAge(`${currentYear - 12}-01-01`)).toBeNull();
    });

    it('returns error for under 12', () => {
      const currentYear = new Date().getFullYear();
      const err = validateAdultAge(`${currentYear - 11}-01-15`);
      expect(err).not.toBeNull();
      expect(err).toContain('at least 12 years old');
      expect(err).toContain('11');
    });

    it('returns error for future date of birth', () => {
      const futureYear = new Date().getFullYear() + 1;
      const err = validateAdultAge(`${futureYear}-06-01`);
      expect(err).toContain('cannot be in the future');
    });

    it('returns null for empty (delegates to required-field validation)', () => {
      expect(validateAdultAge(null)).toBeNull();
      expect(validateAdultAge('')).toBeNull();
    });
  });

  describe('validateChildAge', () => {
    it('returns null for valid child (2-11)', () => {
      const currentYear = new Date().getFullYear();
      expect(validateChildAge(`${currentYear - 5}-06-15`)).toBeNull();
      expect(validateChildAge(`${currentYear - 2}-01-01`)).toBeNull();
      expect(validateChildAge(`${currentYear - 11}-01-01`)).toBeNull();
    });

    it('returns error for under 2', () => {
      const currentYear = new Date().getFullYear();
      const err = validateChildAge(`${currentYear - 1}-01-15`);
      expect(err).toContain('at least 2 years old');
      expect(err).toContain('infants');
    });

    it('returns error for 12 or older', () => {
      const currentYear = new Date().getFullYear();
      const err = validateChildAge(`${currentYear - 12}-01-01`);
      expect(err).toContain('under 12 years old');
      expect(err).toContain('adults');
    });

    it('returns error for future date of birth', () => {
      const futureYear = new Date().getFullYear() + 1;
      const err = validateChildAge(`${futureYear}-06-01`);
      expect(err).toContain('cannot be in the future');
    });
  });

  describe('validateInfantAge', () => {
    it('returns null for valid infant (under 2)', () => {
      const currentYear = new Date().getFullYear();
      expect(validateInfantAge(`${currentYear - 1}-06-15`)).toBeNull();
      expect(validateInfantAge(`${currentYear - 1}-12-01`)).toBeNull();
    });

    it('returns error for 2 or older', () => {
      const currentYear = new Date().getFullYear();
      const err = validateInfantAge(`${currentYear - 2}-01-01`);
      expect(err).toContain('under 2 years old');
      expect(err).toContain('children or adults');
    });

    it('returns error for future date of birth', () => {
      const futureYear = new Date().getFullYear() + 1;
      const err = validateInfantAge(`${futureYear}-06-01`);
      expect(err).toContain('cannot be in the future');
    });
  });

  describe('hasValidPassportData', () => {
    it('returns false when passport fields are masked', () => {
      expect(hasValidPassportData({ passportNumber: '****4589', passportExpiry: '2028-**-**', passportCountry: 'US' })).toBe(false);
    });
    it('returns true when passport fields are valid', () => {
      expect(hasValidPassportData({ passportNumber: 'AB1234567', passportExpiry: '2028-05-15', passportCountry: 'US' })).toBe(true); // pragma: allowlist secret
    });
    it('returns false when any field is missing', () => {
      expect(hasValidPassportData({ passportNumber: 'AB1234567', passportExpiry: '2028-05-15', passportCountry: '' })).toBe(false); // pragma: allowlist secret
    });
  });
});
