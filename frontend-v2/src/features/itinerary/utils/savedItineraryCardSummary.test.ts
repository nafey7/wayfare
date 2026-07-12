import { describe, expect, it } from 'vitest';

import type { SavedItinerary } from '@/types/itineraries';

import {
  destinationWithoutCountry,
  getSavedItineraryCardSummary,
  itineraryHasLinkedBookings,
} from './savedItineraryCardSummary';

function baseItinerary(overrides: Partial<SavedItinerary> = {}): SavedItinerary {
  return {
    id: '507f1f77bcf86cd799439011', // pragma: allowlist secret
    structuredItinerary: {},
    tripMeta: null,
    createdAt: '2026-04-01T12:00:00.000Z',
    updatedAt: '2026-04-01T12:00:00.000Z',
    ...overrides,
  };
}

describe('destinationWithoutCountry', () => {
  it('returns text before first comma', () => {
    expect(destinationWithoutCountry('Paris, France')).toBe('Paris');
  });

  it('returns full string when no comma', () => {
    expect(destinationWithoutCountry('Paris')).toBe('Paris');
  });

  it('trims segments', () => {
    expect(destinationWithoutCountry('  Tokyo , Japan ')).toBe('Tokyo');
  });

  it('handles Unknown for empty', () => {
    expect(destinationWithoutCountry('')).toBe('Unknown');
    expect(destinationWithoutCountry(null)).toBe('Unknown');
  });
});

describe('getSavedItineraryCardSummary', () => {
  it('maps camelCase tripMeta and first itinerary item image', () => {
    const itinerary = baseItinerary({
      tripMeta: {
        origin: 'London',
        destination: 'Paris, France',
        departureDate: '2026-04-20',
        returnDate: '2026-04-23',
        adults: 2,
        children: 1,
        infants: 0,
      },
      structuredItinerary: {
        itineraryItems: [
          {
            day: 1,
            title: 'Day 1',
            imageUrl: 'https://example.com/hero.jpg',
          },
        ],
      },
    });
    const s = getSavedItineraryCardSummary(itinerary);
    expect(s.id).toBe(itinerary.id);
    expect(s.destinationLabel).toBe('Paris');
    expect(s.origin).toBe('London');
    expect(s.heroImageUrl).toBe('https://example.com/hero.jpg');
    expect(s.dateRangeLabel).toContain('Apr');
    expect(s.dateRangeLabel).toContain('2026');
    expect(s.nightsLabel).toBe('3 nights');
    expect(s.passengersLabel).toBe('2 adults, 1 child');
    expect(s.dayCount).toBe(1);
    expect(s.preview).toBe('Day 1');
    expect(s.hasLinkedBookings).toBe(false);
  });

  it('sets hasLinkedBookings when flight or hotel refs exist', () => {
    const withFlight = baseItinerary({
      linkedBookings: {
        flightVoyaReferences: ['VOYA-F-1'],
        hotelVoyaReferences: [],
      },
    });
    expect(getSavedItineraryCardSummary(withFlight).hasLinkedBookings).toBe(true);

    const withHotel = baseItinerary({
      linkedBookings: {
        flightVoyaReferences: [],
        hotelVoyaReferences: ['VOYA-H-1'],
      },
    });
    expect(getSavedItineraryCardSummary(withHotel).hasLinkedBookings).toBe(true);

    const empty = baseItinerary({
      linkedBookings: { flightVoyaReferences: [], hotelVoyaReferences: [] },
    });
    expect(getSavedItineraryCardSummary(empty).hasLinkedBookings).toBe(false);
  });

  it('maps tripMeta dates from camelCase keys', () => {
    const itinerary = baseItinerary({
      tripMeta: {
        destination: 'Rome',
        departureDate: '2026-05-01',
        returnDate: '2026-05-05',
        adults: 1,
      },
    });
    const s = getSavedItineraryCardSummary(itinerary);
    expect(s.nightsLabel).toBe('4 nights');
    expect(s.passengersLabel).toBe('1 adult');
  });

  it('falls back nights from item count when dates missing', () => {
    const itinerary = baseItinerary({
      tripMeta: { destination: 'X' },
      structuredItinerary: {
        itineraryItems: [{ day: 1 }, { day: 2 }, { day: 3 }, { day: 4 }],
      },
    });
    const s = getSavedItineraryCardSummary(itinerary);
    expect(s.nightsLabel).toBe('3 nights');
  });

  it('itineraryHasLinkedBookings matches reference arrays', () => {
    expect(
      itineraryHasLinkedBookings({
        flightVoyaReferences: ['a'],
        hotelVoyaReferences: [],
      }),
    ).toBe(true);
    expect(itineraryHasLinkedBookings(undefined)).toBe(false);
  });

  it('returns em dash for passengers when all zero', () => {
    const itinerary = baseItinerary({
      tripMeta: {
        destination: 'Y',
        adults: 0,
        children: 0,
        infants: 0,
      },
    });
    expect(getSavedItineraryCardSummary(itinerary).passengersLabel).toBe('—');
  });
});
