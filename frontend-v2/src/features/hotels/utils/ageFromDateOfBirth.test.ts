import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ageFromIsoDateOfBirth } from './ageFromDateOfBirth';

describe('ageFromIsoDateOfBirth', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns undefined for empty or invalid input', () => {
    expect(ageFromIsoDateOfBirth('')).toBeUndefined();
    expect(ageFromIsoDateOfBirth(undefined)).toBeUndefined();
    expect(ageFromIsoDateOfBirth('not-a-date')).toBeUndefined();
    expect(ageFromIsoDateOfBirth('2023-02-29')).toBeUndefined();
  });

  it('computes full years with birthday not yet reached this year', () => {
    expect(ageFromIsoDateOfBirth('2010-07-01')).toBe(15);
  });

  it('computes full years when birthday has passed', () => {
    expect(ageFromIsoDateOfBirth('2010-05-01')).toBe(16);
  });
});
