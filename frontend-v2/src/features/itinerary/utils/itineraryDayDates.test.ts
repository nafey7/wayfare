import { describe, it, expect } from 'vitest';
import { computeItineraryDayLabel } from './itineraryDayDates';

describe('computeItineraryDayLabel', () => {
  describe('day 1 returns the departure date', () => {
    it('formats a Wednesday in May correctly', () => {
      expect(computeItineraryDayLabel('2024-05-15', 1)).toBe('WED 15 MAY');
    });

    it('formats a Saturday in January correctly', () => {
      expect(computeItineraryDayLabel('2024-01-06', 1)).toBe('SAT 6 JAN');
    });
  });

  describe('day offset advances correctly', () => {
    it('day 2 is +1 day from departure', () => {
      expect(computeItineraryDayLabel('2024-05-15', 2)).toBe('THU 16 MAY');
    });

    it('day 3 is +2 days from departure', () => {
      expect(computeItineraryDayLabel('2024-05-15', 3)).toBe('FRI 17 MAY');
    });
  });

  describe('month boundary overflow', () => {
    it('Jan 31 + 1 day → Feb 1', () => {
      expect(computeItineraryDayLabel('2024-01-31', 2)).toBe('THU 1 FEB');
    });

    it('Dec 31 + 1 day → Jan 1 next year', () => {
      expect(computeItineraryDayLabel('2024-12-31', 2)).toBe('WED 1 JAN');
    });
  });

  describe('leap year handling', () => {
    it('Feb 28 + 1 day in leap year (2024) → Feb 29', () => {
      expect(computeItineraryDayLabel('2024-02-28', 2)).toBe('THU 29 FEB');
    });

    it('Feb 28 + 1 day in non-leap year (2025) → Mar 1', () => {
      expect(computeItineraryDayLabel('2025-02-28', 2)).toBe('SAT 1 MAR');
    });
  });

  describe('returns empty string for invalid input', () => {
    it('returns "" for undefined', () => {
      expect(computeItineraryDayLabel(undefined, 1)).toBe('');
    });

    it('returns "" for empty string', () => {
      expect(computeItineraryDayLabel('', 1)).toBe('');
    });

    it('returns "" for non-date string', () => {
      expect(computeItineraryDayLabel('not-a-date', 1)).toBe('');
    });

    it('returns "" for slash-separated date format', () => {
      expect(computeItineraryDayLabel('2024/06/15', 1)).toBe('');
    });

    it('returns "" for dayNumber 0', () => {
      expect(computeItineraryDayLabel('2024-06-15', 0)).toBe('');
    });

    it('returns "" for negative dayNumber', () => {
      expect(computeItineraryDayLabel('2024-06-15', -1)).toBe('');
    });
  });

  describe('timezone safety', () => {
    it('parses "2024-06-15" so local getDate() is 15, not 14', () => {
      // Regression guard: new Date("2024-06-15") is UTC midnight and shifts to
      // the previous calendar day in UTC- timezones. Our parser must avoid that.
      const label = computeItineraryDayLabel('2024-06-15', 1);
      expect(label).toMatch(/\b15\b/);
      expect(label).toContain('JUN');
    });
  });
});
