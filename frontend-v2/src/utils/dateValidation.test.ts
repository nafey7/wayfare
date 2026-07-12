import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { isPastDate, validateDatesNotInPast } from './dateValidation';

const TODAY = new Date(2026, 4, 13); // 2026-05-13

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(TODAY);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('isPastDate', () => {
  it('returns false for null/undefined', () => {
    expect(isPastDate(null)).toBe(false);
    expect(isPastDate(undefined)).toBe(false);
  });

  it('returns false for today (not strictly past)', () => {
    expect(isPastDate(new Date(2026, 4, 13))).toBe(false);
    expect(isPastDate('2026-05-13')).toBe(false);
  });

  it('returns false for a future date', () => {
    expect(isPastDate(new Date(2026, 4, 14))).toBe(false);
    expect(isPastDate('2026-05-14')).toBe(false);
  });

  it('returns true for yesterday', () => {
    expect(isPastDate(new Date(2026, 4, 12))).toBe(true);
    expect(isPastDate('2026-05-12')).toBe(true);
  });

  it('returns true for a date in a previous year', () => {
    expect(isPastDate('2025-01-01')).toBe(true);
  });

  it('ignores time component — same-day non-midnight Date is not past', () => {
    const laterToday = new Date(2026, 4, 13, 23, 59, 59);
    expect(isPastDate(laterToday)).toBe(false);
  });

  it('handles ISO datetime strings by taking only the date portion', () => {
    expect(isPastDate('2026-05-14T10:00:00.000Z')).toBe(false);
    expect(isPastDate('2026-05-12T10:00:00.000Z')).toBe(true);
  });

  it('returns false for malformed strings instead of throwing', () => {
    expect(isPastDate('not-a-date')).toBe(false);
  });
});

describe('validateDatesNotInPast', () => {
  it('returns null when all dates are in the future or today', () => {
    expect(
      validateDatesNotInPast([
        { label: 'Departure', value: '2026-05-14' },
        { label: 'Return', value: '2026-05-20' },
      ])
    ).toBeNull();
  });

  it('returns null for null/undefined values (skips them)', () => {
    expect(
      validateDatesNotInPast([
        { label: 'Departure', value: null },
        { label: 'Return', value: undefined },
      ])
    ).toBeNull();
  });

  it('returns error message for the first past date found', () => {
    expect(
      validateDatesNotInPast([
        { label: 'Departure date', value: '2026-05-12' },
        { label: 'Return date', value: '2026-05-20' },
      ])
    ).toBe('Departure date cannot be in the past.');
  });

  it('returns error for second slot when first is valid', () => {
    expect(
      validateDatesNotInPast([
        { label: 'Check-in date', value: '2026-05-14' },
        { label: 'Check-out date', value: '2026-05-12' },
      ])
    ).toBe('Check-out date cannot be in the past.');
  });

  it('skips null slots and still catches a later past date', () => {
    expect(
      validateDatesNotInPast([
        { label: 'Leg 1', value: null },
        { label: 'Leg 2', value: '2026-05-01' },
      ])
    ).toBe('Leg 2 cannot be in the past.');
  });
});
