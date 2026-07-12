import { describe, it, expect } from 'vitest';
import { computePreferenceScore, sortFlightsByPreference } from './flightPreferenceScore';
import type { FilterableFlight } from './flightFilters';
import type { FlightsPreferences } from '@/types/profile';

function makeFlight(
  id: string,
  price: number,
  stops: number,
  depTime: string,
  airlines: Array<{ code: string; name: string }> = []
): FilterableFlight {
  return {
    id,
    price,
    legs: [
      {
        stops,
        departure: { time: depTime },
        arrival: { time: '12:00' },
        airlinesInfo: airlines,
      },
    ],
  };
}

const basePrefs: FlightsPreferences = {
  preferredAirlines: ['BA'],
  maxStops: 'nonstop',
  departureWindow: ['08:00', '12:00'],
};

describe('computePreferenceScore', () => {
  it('all three attributes match → score 3', () => {
    const flight = makeFlight('f1', 200, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]);
    expect(computePreferenceScore(flight, basePrefs)).toBe(3);
  });

  it('zero attributes match → score 0', () => {
    const flight = makeFlight('f2', 200, 2, '22:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(0);
  });

  it('airlines only match → score 1', () => {
    const flight = makeFlight('f3', 200, 2, '22:00', [{ code: 'BA', name: 'British Airways' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(1);
  });

  it('stops only match (nonstop pref, 0-stop flight) → score 1', () => {
    const flight = makeFlight('f4', 200, 0, '22:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(1);
  });

  it('stops mismatch (nonstop pref, 1-stop flight) → score 0 for stops', () => {
    const flight = makeFlight('f5', 200, 1, '22:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(0);
  });

  it('departure window match (normal window) → score 1', () => {
    const flight = makeFlight('f6', 200, 2, '09:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(1);
  });

  it('departure window miss → score 0 for window', () => {
    const flight = makeFlight('f7', 200, 2, '15:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(0);
  });

  it('midnight-spanning window, departure at 23:30 → match', () => {
    const flight = makeFlight('f8', 200, 2, '23:30', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: [],
      maxStops: null,
      departureWindow: ['22:00', '06:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(1);
  });

  it('midnight-spanning window, departure at 12:00 → no match', () => {
    const flight = makeFlight('f9', 200, 2, '12:00', [{ code: 'LH', name: 'Lufthansa' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: [],
      maxStops: null,
      departureWindow: ['22:00', '06:00'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(0);
  });

  it('prefs = null → score 0', () => {
    const flight = makeFlight('f10', 200, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]);
    expect(computePreferenceScore(flight, null)).toBe(0);
  });

  it('airline name match (case-insensitive) when code does not match', () => {
    const flight = makeFlight('f11', 200, 2, '22:00', [
      { code: 'FR', name: 'British Airways' },
    ]);
    const prefs: FlightsPreferences = {
      preferredAirlines: ['British Airways'],
      maxStops: null,
      departureWindow: ['00:00', '23:59'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(1);
  });

  it('default window ["00:00","23:59"] → always scores 0 for departure window', () => {
    const flight = makeFlight('f12', 200, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]);
    const prefs: FlightsPreferences = {
      preferredAirlines: [],
      maxStops: null,
      departureWindow: ['00:00', '23:59'],
    };
    expect(computePreferenceScore(flight, prefs)).toBe(0);
  });
});

describe('sortFlightsByPreference', () => {
  it('sorts by descending score with price as tiebreaker', () => {
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    const flightA = makeFlight('a', 200, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]); // score 3
    const flightB = makeFlight('b', 100, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]); // score 3, cheaper
    const flightC = makeFlight('c', 50, 1, '15:00', [{ code: 'LH', name: 'Lufthansa' }]);        // score 0

    const result = sortFlightsByPreference([flightA, flightC, flightB], prefs);
    expect(result.map((f) => f.id)).toEqual(['b', 'a', 'c']);
  });

  it('prefs = null → returns price-ascending order', () => {
    const flightA = makeFlight('a', 300, 0, '10:00');
    const flightB = makeFlight('b', 100, 0, '10:00');
    const flightC = makeFlight('c', 200, 0, '10:00');

    const result = sortFlightsByPreference([flightA, flightC, flightB], null);
    expect(result.map((f) => f.price)).toEqual([100, 200, 300]);
  });

  it('does not mutate input array', () => {
    const prefs: FlightsPreferences = {
      preferredAirlines: ['BA'],
      maxStops: 'nonstop',
      departureWindow: ['08:00', '12:00'],
    };
    const flights = [
      makeFlight('a', 200, 0, '10:00', [{ code: 'BA', name: 'British Airways' }]),
      makeFlight('b', 100, 1, '22:00'),
    ];
    const original = [...flights];
    sortFlightsByPreference(flights, prefs);
    expect(flights[0]!.id).toBe('a');
    expect(flights).toEqual(original);
  });
});
