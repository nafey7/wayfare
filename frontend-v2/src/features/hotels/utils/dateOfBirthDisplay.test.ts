import { describe, expect, it } from 'vitest';
import { formatIsoDobForDisplay } from './dateOfBirthDisplay';

describe('formatIsoDobForDisplay', () => {
  it('formats valid ISO dates', () => {
    expect(formatIsoDobForDisplay('1990-03-15')).toBe('03/15/1990');
  });

  it('returns em dash for empty', () => {
    expect(formatIsoDobForDisplay('')).toBe('—');
    expect(formatIsoDobForDisplay(undefined)).toBe('—');
  });

  it('passes through non-ISO strings', () => {
    expect(formatIsoDobForDisplay('invalid')).toBe('invalid');
  });
});
