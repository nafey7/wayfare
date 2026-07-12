import { describe, it, expect } from 'vitest';
import { mapFareItinerariesToFlightCards } from './mapFareItinerariesToFlightCards';
import type { FareItineraryCamel } from '@/types/flightBackend';

const minimalItinerary = (fareSourceCode: string): FareItineraryCamel => ({
  flightLegs: [
    {
      flightSegments: [
        {
          departureDatetime: { value: '2026-06-01T08:00:00' },
          arrivalDatetime: { value: '2026-06-01T10:00:00' },
          flightDuration: { totalMinutes: 120 },
          departureAirport: { iataCode: 'BCN', cityName: 'Barcelona' },
          arrivalAirport: { iataCode: 'LHR', cityName: 'London' },
          marketingAirline: { airlineName: 'Test Air', iataCode: 'TA' },
          marketingFlightNumber: { formattedNumber: 'TA100' },
        },
      ],
      totalStops: 0,
    },
  ],
  pricing: {
    fareSourceCode,
    fareType: 'Published',
    fareTotals: { totalFare: { amount: '199', currency: 'USD' } },
  },
});

describe('mapFareItinerariesToFlightCards', () => {
  it('maps one-way style itineraries with fare id as card id', () => {
    const rows = mapFareItinerariesToFlightCards({
      fareItineraries: [minimalItinerary('ABC123')],
      travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
    });
    expect(rows).toHaveLength(1);
    expect(rows[0]!.id).toBe('ABC123');
    expect(rows[0]!.price).toBe(199);
  });

  it('uses composite id when legIndex is set (multicity)', () => {
    const rows = mapFareItinerariesToFlightCards({
      fareItineraries: [minimalItinerary('XYZ')],
      travellers: { adults: 2, children: 0, infants: 0, cabinClass: 'Economy' },
      legIndex: 1,
    });
    expect(rows[0]!.id).toBe('1::XYZ');
    expect(rows[0]!.passengers).toBe(2);
  });
});
