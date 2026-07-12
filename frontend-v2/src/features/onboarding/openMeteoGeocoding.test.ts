import { describe, it, expect, vi, afterEach } from 'vitest';

import {
  draftLocationToCityOption,
  searchCitiesOpenMeteo,
  tripCityOptionFromStored,
} from './openMeteoGeocoding';

describe('searchCitiesOpenMeteo', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns [] for short queries', async () => {
    await expect(searchCitiesOpenMeteo('')).resolves.toEqual([]);
    await expect(searchCitiesOpenMeteo('a')).resolves.toEqual([]);
  });

  it('maps results and prefers larger places', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              id: 1,
              name: 'Small',
              country: 'X',
              country_code: 'XX',
              feature_code: 'PPL',
              population: 100,
            },
            {
              id: 2,
              name: 'Big',
              country: 'Y',
              country_code: 'YY',
              feature_code: 'PPLC',
              population: 5000000,
            },
          ],
        }),
      })
    );

    const out = await searchCitiesOpenMeteo('te');
    expect(out).toHaveLength(2);
    const [first, second] = out;
    expect(first!.label).toContain('Big');
    expect(first!.value).toBe('om-2');
    expect(first!.countryCode).toBe('YY');
    expect(first!.cityName).toBe('Big');
    expect(second!.value).toBe('om-1');
  });

  it('filters by country code when provided', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              id: 1,
              name: 'Paris',
              country: 'France',
              country_code: 'FR',
              feature_code: 'PPLC',
              population: 2000000,
            },
            {
              id: 2,
              name: 'Paris',
              country: 'United States',
              country_code: 'US',
              feature_code: 'PPL',
              population: 25000,
            },
          ],
        }),
      })
    );

    const fr = await searchCitiesOpenMeteo('par', undefined, 'FR');
    expect(fr).toHaveLength(1);
    expect(fr[0]!.countryCode).toBe('FR');

    const us = await searchCitiesOpenMeteo('par', undefined, 'US');
    expect(us).toHaveLength(1);
    expect(us[0]!.countryCode).toBe('US');
  });

  it('throws on non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      })
    );
    await expect(searchCitiesOpenMeteo('par')).rejects.toThrow(/503/);
  });
});

describe('tripCityOptionFromStored', () => {
  it('returns null for empty', () => {
    expect(tripCityOptionFromStored('')).toBeNull();
    expect(tripCityOptionFromStored('   ')).toBeNull();
  });

  it('matches legacy catalog by city name', () => {
    const o = tripCityOptionFromStored('London');
    expect(o?.label).toContain('London');
    expect(o?.value).toMatch(/London\|/);
  });

  it('wraps freeform stored strings', () => {
    const o = tripCityOptionFromStored('Nara · Japan');
    expect(o?.displayLine).toBe('Nara · Japan');
    expect(o?.value.startsWith('text:')).toBe(true);
  });
});

describe('draftLocationToCityOption', () => {
  it('returns null when city or country missing', () => {
    expect(
      draftLocationToCityOption({
        country: 'X',
        countryCode: 'XX',
        city: '',
        iata: '',
        currency: '',
        currencySymbol: '',
      })
    ).toBeNull();
  });

  it('builds a stable option for the location picker', () => {
    const o = draftLocationToCityOption({
      country: 'Germany',
      countryCode: 'DE',
      city: 'Berlin',
      iata: '',
      currency: 'EUR',
      currencySymbol: '€',
    });
    expect(o?.label).toBe('Berlin · Germany');
    expect(o?.countryCode).toBe('DE');
  });
});
