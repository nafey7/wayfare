import { describe, it, expect } from 'vitest';
import {
  parseDestinationLocation,
  getItineraryMapCenterFromTripMeta,
  DEFAULT_ITINERARY_MAP_FALLBACK,
} from './destinationLocation';

describe('parseDestinationLocation', () => {
  it('returns valid coords when within bounds', () => {
    expect(parseDestinationLocation({ latitude: 48.8566, longitude: 2.3522 })).toEqual({
      latitude: 48.8566,
      longitude: 2.3522,
    });
    expect(parseDestinationLocation({ latitude: -90, longitude: -180 })).toEqual({
      latitude: -90,
      longitude: -180,
    });
    expect(parseDestinationLocation({ latitude: 90, longitude: 180 })).toEqual({
      latitude: 90,
      longitude: 180,
    });
  });

  it('returns undefined when out of bounds', () => {
    expect(parseDestinationLocation({ latitude: 91, longitude: 0 })).toBeUndefined();
    expect(parseDestinationLocation({ latitude: -91, longitude: 0 })).toBeUndefined();
    expect(parseDestinationLocation({ latitude: 0, longitude: 181 })).toBeUndefined();
    expect(parseDestinationLocation({ latitude: 0, longitude: -181 })).toBeUndefined();
  });

  it('returns undefined for invalid input', () => {
    expect(parseDestinationLocation(null)).toBeUndefined();
    expect(parseDestinationLocation(undefined)).toBeUndefined();
    expect(parseDestinationLocation('invalid')).toBeUndefined();
    expect(parseDestinationLocation({ latitude: NaN, longitude: 2 })).toBeUndefined();
    expect(parseDestinationLocation({ latitude: 48, longitude: NaN })).toBeUndefined();
    expect(parseDestinationLocation({ latitude: '48', longitude: '2' })).toEqual({
      latitude: 48,
      longitude: 2,
    });
  });
});

describe('getItineraryMapCenterFromTripMeta', () => {
  it('uses destination_location when present (snake_case)', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination: 'Dubai',
        destination_location: { latitude: 25.2048493, longitude: 55.2707828 },
      })
    ).toEqual({
      centerLatitude: 25.2048493,
      centerLongitude: 55.2707828,
      zoomLevel: 10,
    });
  });

  it('uses destinationLocation when present (camelCase from saved itinerary API)', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination: 'Dubai',
        destinationLocation: { latitude: 25.2, longitude: 55.27 },
      })
    ).toEqual({
      centerLatitude: 25.2,
      centerLongitude: 55.27,
      zoomLevel: 10,
    });
  });

  it('prefers destination_location (snake_case) over destinationLocation when both present', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination_location: { latitude: 1.0, longitude: 2.0 },
        destinationLocation: { latitude: 99.0, longitude: 99.0 },
      })
    ).toEqual({
      centerLatitude: 1.0,
      centerLongitude: 2.0,
      zoomLevel: 10,
    });
  });

  it('falls back to the default center when destination_location coords are out of bounds', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination: 'Paris',
        destination_location: { latitude: 91, longitude: 0 },
      })
    ).toEqual({
      centerLatitude: DEFAULT_ITINERARY_MAP_FALLBACK.lat,
      centerLongitude: DEFAULT_ITINERARY_MAP_FALLBACK.lng,
      zoomLevel: 10,
    });
  });

  it('falls back to the default center when destinationLocation coords are out of bounds', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination: 'Paris',
        destinationLocation: { latitude: 0, longitude: 181 },
      })
    ).toEqual({
      centerLatitude: DEFAULT_ITINERARY_MAP_FALLBACK.lat,
      centerLongitude: DEFAULT_ITINERARY_MAP_FALLBACK.lng,
      zoomLevel: 10,
    });
  });

  it('uses the single default center when backend coords are missing', () => {
    expect(
      getItineraryMapCenterFromTripMeta({
        destination: 'Paris',
      })
    ).toEqual({
      centerLatitude: DEFAULT_ITINERARY_MAP_FALLBACK.lat,
      centerLongitude: DEFAULT_ITINERARY_MAP_FALLBACK.lng,
      zoomLevel: 10,
    });
    expect(getItineraryMapCenterFromTripMeta(undefined)).toEqual({
      centerLatitude: DEFAULT_ITINERARY_MAP_FALLBACK.lat,
      centerLongitude: DEFAULT_ITINERARY_MAP_FALLBACK.lng,
      zoomLevel: 10,
    });
  });
});
