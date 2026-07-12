import { describe, it, expect } from 'vitest';
import { buildAirportAutocompleteOptions } from './airportAutocompleteOptions';

describe('buildAirportAutocompleteOptions', () => {
  it('returns empty array for empty input', () => {
    expect(buildAirportAutocompleteOptions([])).toEqual([]);
  });

  it.each([
    {
      scenario: 'city search returning one airport',
      input: [{ iata: 'ORY', name: 'Paris Orly', city: 'Paris', country: 'France' }],
      expectedCity: { city: 'Paris', iata: 'ORY', isCityOption: true, name: 'Paris (Any)' },
      expectedAirport: { iata: 'ORY', name: 'Paris Orly', city: 'Paris', country: 'France' },
    },
    {
      scenario: 'IATA-specific search returning one airport',
      input: [
        {
          iata: 'LHR',
          name: 'London Heathrow Airport',
          city: 'London',
          country: 'United Kingdom',
        },
      ],
      expectedCity: { city: 'London', iata: 'LHR', isCityOption: true, name: 'London (Any)' },
      expectedAirport: {
        iata: 'LHR',
        name: 'London Heathrow Airport',
        city: 'London',
        country: 'United Kingdom',
      },
    },
  ])(
    'produces city-wide + airport row for a single-airport result ($scenario)',
    ({ input, expectedCity, expectedAirport }) => {
      const options = buildAirportAutocompleteOptions(input);

      expect(options).toHaveLength(2);

      const cityWide = options.find((o) => o.isCityOption);
      expect(cityWide).toMatchObject(expectedCity);

      const airport = options.find((o) => !o.isCityOption);
      expect(airport).toMatchObject(expectedAirport);
      expect(airport?.isCityOption).toBeFalsy();
    }
  );

  it('lists city-wide row plus each airport when a city has multiple airports', () => {
    const options = buildAirportAutocompleteOptions([
      {
        iata: 'CDG',
        name: 'Charles de Gaulle',
        city: 'Paris',
        country: 'France',
      },
      {
        iata: 'ORY',
        name: 'Paris Orly',
        city: 'Paris',
        country: 'France',
      },
    ]);

    const cityWide = options.find((o) => o.isCityOption);
    expect(cityWide).toMatchObject({ city: 'Paris', isCityOption: true });

    const individuals = options.filter((o) => !o.isCityOption);
    expect(individuals.map((o) => o.iata).sort()).toEqual(['CDG', 'ORY']);
    expect(options).toHaveLength(3);
  });
});
