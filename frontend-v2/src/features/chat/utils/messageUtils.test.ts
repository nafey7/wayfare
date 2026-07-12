import { describe, it, expect } from 'vitest';
import { getFlightSearchMessageSummary, getHotelSearchMessageSummary } from './messageUtils';

describe('getFlightSearchMessageSummary', () => {
  it('returns "Here are your flight options." for empty string', () => {
    expect(getFlightSearchMessageSummary('')).toBe('Here are your flight options.');
  });

  it('returns "Here are your flight options." for whitespace-only string', () => {
    expect(getFlightSearchMessageSummary('   \n\t  ')).toBe('Here are your flight options.');
  });

  it('handles null/undefined by treating as empty (coerced)', () => {
    // @ts-expect-error intentional test of runtime behavior
    expect(getFlightSearchMessageSummary(null)).toBe('Here are your flight options.');
    // @ts-expect-error intentional test of runtime behavior
    expect(getFlightSearchMessageSummary(undefined)).toBe('Here are your flight options.');
  });

  it('returns intro only when text has \\n\\n** before category sections', () => {
    const text =
      'I found several one-way flights from London to New York.\n\nHere are the top options:\n\n**Best Value**\n...';
    expect(getFlightSearchMessageSummary(text)).toBe(
      'I found several one-way flights from London to New York.\n\nHere are the top options:'
    );
  });

  it('handles single \\n** before category (robust regex)', () => {
    const text = 'Intro text.\n**Cheapest**\nFlight details...';
    expect(getFlightSearchMessageSummary(text)).toBe('Intro text.');
  });

  it('returns full text when no category markers present', () => {
    const text = 'Some plain intro without category markers.';
    expect(getFlightSearchMessageSummary(text)).toBe(text);
  });

  it('returns trimmed intro when category marker at end', () => {
    const text = '  Short intro  \n**Best Value**';
    expect(getFlightSearchMessageSummary(text)).toBe('Short intro');
  });

  it('returns intro only when text has ### Best Value / Cheapest / Fastest headings', () => {
    const text =
      'Of course. I found several one-way flights from London (LHR) to New York (JFK) on April 26, 2026. Here are your top options:\n\n### Best Value\n*   **United Airlines**: 08:45 - 16:35...';
    expect(getFlightSearchMessageSummary(text)).toBe(
      'Of course. I found several one-way flights from London (LHR) to New York (JFK) on April 26, 2026. Here are your top options:'
    );
  });
});

describe('getHotelSearchMessageSummary', () => {
  it('builds summary from extraData when summary and search_params present', () => {
    const text = 'ignored when structured data exists';
    const extraData = {
      data: {
        summary: {
          total_hotels: 5,
          nights: 3,
          price_range: { min: 120, currency: 'EUR' },
        },
        search_params: {
          destination_city: 'Barcelona',
        },
      },
    };
    expect(getHotelSearchMessageSummary(text, extraData)).toContain('Barcelona');
    expect(getHotelSearchMessageSummary(text, extraData)).toContain('5 hotel');
  });

  it('falls back to shared markdown intro when extraData missing', () => {
    const text = 'Intro only\n### Best Value\nDetails';
    expect(getHotelSearchMessageSummary(text, undefined)).toBe('Intro only');
  });

  it('returns hotel default when extraData missing and text is empty', () => {
    expect(getHotelSearchMessageSummary('', undefined)).toBe('Here are your hotel options.');
  });
});
