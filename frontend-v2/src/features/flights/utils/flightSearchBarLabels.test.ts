import { describe, it, expect } from 'vitest';
import { buildMulticityTripChain } from './multicityPricing';
import {
  isCityWideAirportSelection,
  multicityChainEndpointLabel,
  routeEndpointDisplayLabel,
} from './flightSearchBarLabels';

describe('routeEndpointDisplayLabel', () => {
  it('shows city only when isCityOption is true', () => {
    expect(
      routeEndpointDisplayLabel(
        {
          city: 'Paris',
          iata: 'CDG',
          isCityOption: true,
        },
        '',
        'Origin'
      )
    ).toBe('Paris');
  });

  it('shows city (IATA) when isCityOption is false', () => {
    expect(
      routeEndpointDisplayLabel(
        {
          city: 'Paris',
          iata: 'CDG',
          isCityOption: false,
        },
        '',
        'Origin'
      )
    ).toBe('Paris (CDG)');
  });

  it('uses incompleteFallback when airport is missing and segment text is empty', () => {
    expect(routeEndpointDisplayLabel(undefined, '', 'Origin')).toBe('Origin');
    expect(routeEndpointDisplayLabel({ city: '', iata: 'X' }, '', 'Origin')).toBe('Origin');
  });

  it('uses segment text when airport is missing but text is available (e.g. chat URL params)', () => {
    expect(routeEndpointDisplayLabel(undefined, 'LHR', 'Origin')).toBe('LHR');
    expect(routeEndpointDisplayLabel(undefined, 'London', 'Origin')).toBe('London');
  });

  it('shows city only for legacy city-wide state when isCityOption was not persisted', () => {
    expect(
      routeEndpointDisplayLabel(
        {
          city: 'Paris',
          iata: 'CDG',
          name: 'Paris (Any)',
          country: 'France',
        },
        'Paris',
        'Origin'
      )
    ).toBe('Paris');
  });
});

describe('isCityWideAirportSelection', () => {
  it('is true when isCityOption is true', () => {
    expect(
      isCityWideAirportSelection(
        { iata: 'CDG', name: 'Paris (Any)', city: 'Paris', isCityOption: true },
        ''
      )
    ).toBe(true);
  });

  it('is true when segment text matches city (legacy)', () => {
    expect(
      isCityWideAirportSelection(
        { iata: 'CDG', name: 'Paris (Any)', city: 'Paris' },
        'Paris'
      )
    ).toBe(true);
  });

  it('is true when name ends with (Any) and isCityOption is unset', () => {
    expect(
      isCityWideAirportSelection(
        { iata: 'CDG', name: 'Paris (Any)', city: 'Paris' },
        ''
      )
    ).toBe(true);
  });

  it('is false for a specific airport when segment text is city (IATA) style', () => {
    expect(
      isCityWideAirportSelection(
        { iata: 'MAD', name: 'Barajas', city: 'Madrid', isCityOption: false },
        'Madrid (MAD)'
      )
    ).toBe(false);
  });
});

describe('multicityChainEndpointLabel', () => {
  it('uses city name for city-wide selection and IATA for specific airport', () => {
    expect(
      multicityChainEndpointLabel(
        { iata: 'CDG', name: 'Paris (Any)', city: 'Paris', country: 'FR', isCityOption: true },
        ''
      )
    ).toBe('Paris');
    expect(
      multicityChainEndpointLabel(
        { iata: 'MAD', name: 'Barajas', city: 'Madrid', country: 'ES', isCityOption: false },
        ''
      )
    ).toBe('MAD');
  });

  it('uses city name when isCityOption was not persisted but segment text is the city (Autocomplete city-wide)', () => {
    expect(
      multicityChainEndpointLabel(
        {
          iata: 'CDG',
          name: 'Paris (Any)',
          city: 'Paris',
          country: 'FR',
        },
        'Paris'
      )
    ).toBe('Paris');
    expect(
      multicityChainEndpointLabel(
        {
          iata: 'MAD',
          name: 'Madrid (Any)',
          city: 'Madrid',
          country: 'ES',
        },
        'Madrid'
      )
    ).toBe('Madrid');
  });

  it('builds a multi-city summary line with city names instead of representative IATA for city-wide legs', () => {
    const chain = buildMulticityTripChain([
      {
        legIndex: 0,
        origin: multicityChainEndpointLabel(
          { iata: 'CDG', name: 'x', city: 'Paris', country: 'FR', isCityOption: true },
          ''
        ),
        destination: multicityChainEndpointLabel(
          { iata: 'MAD', name: 'x', city: 'Madrid', country: 'ES', isCityOption: true },
          ''
        ),
      },
      {
        legIndex: 1,
        origin: multicityChainEndpointLabel(
          { iata: 'MAD', name: 'x', city: 'Madrid', country: 'ES', isCityOption: true },
          ''
        ),
        destination: multicityChainEndpointLabel(
          { iata: 'BCN', name: 'El Prat', city: 'Barcelona', country: 'ES', isCityOption: false },
          ''
        ),
      },
    ]);
    expect(chain).toBe('Paris -> Madrid -> BCN');
  });
});
