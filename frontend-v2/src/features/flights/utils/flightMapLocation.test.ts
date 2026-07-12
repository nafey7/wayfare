import { describe, expect, it } from 'vitest';
import {
  getFlightRecommendationsMapProps,
  getFlightSearchPageMapProps,
  getItineraryMapOverrideFromTripMeta,
} from './flightMapLocation';
import type { ExtractedFlightSearchData } from '@/types/api.helpers';

function makeFlightSearchData(): ExtractedFlightSearchData {
  return {
    session_id: 'sess-456',
    flights: [],
    data: {
      search_params: {
        origin: 'London',
        destination: 'New York',
        origin_iata: 'LHR',
        destination_iata: 'JFK',
        departure_date: '2026-06-01',
        return_date: null,
        journey_type: 'OneWay',
        passengers: {
          adults: 1,
          children: 0,
          infants: 0,
        },
      },
      summary: {
        total_flights: 12,
        direct_count: 4,
        price_range: {
          min: 300,
          max: 900,
          currency: 'USD',
        },
      },
      categories: {
        cheapest: { label: 'Cheapest', flights: [] },
        fastest: { label: 'Fastest', flights: [] },
        best_value: { label: 'Best Value', flights: [] },
      },
    },
  };
}

describe('getFlightRecommendationsMapProps', () => {
  it('falls back to backend-provided coordinates when no city override is present', () => {
    const data = makeFlightSearchData();
    data.origin_location = { latitude: 51.47, longitude: -0.4543 };
    data.destination_location = { latitude: 40.6413, longitude: -73.7781 };

    const mapProps = getFlightRecommendationsMapProps(data);

    expect(mapProps.markers).toEqual([
      {
        latitude: 51.47,
        longitude: -0.4543,
        label: 'Origin: London',
      },
      {
        latitude: 40.6413,
        longitude: -73.7781,
        label: 'Destination: New York',
      },
    ]);
    expect(mapProps.routePath).toEqual([
      { latitude: 51.47, longitude: -0.4543 },
      { latitude: 40.6413, longitude: -73.7781 },
    ]);
  });

  it('uses API coordinate overrides ahead of static fallbacks when provided', () => {
    const data = makeFlightSearchData();
    const mapProps = getFlightRecommendationsMapProps(data, {
      origin: { latitude: 1.23, longitude: 4.56 },
      destination: { latitude: 7.89, longitude: 0.12 },
    });

    expect(mapProps.markers).toEqual([
      {
        latitude: 1.23,
        longitude: 4.56,
        label: 'Origin: London',
      },
      {
        latitude: 7.89,
        longitude: 0.12,
        label: 'Destination: New York',
      },
    ]);
    expect(mapProps.routePath).toEqual([
      { latitude: 1.23, longitude: 4.56 },
      { latitude: 7.89, longitude: 0.12 },
    ]);
  });

  it('falls back to known IATA and city coordinates when backend values are missing', () => {
    const mapProps = getFlightRecommendationsMapProps(makeFlightSearchData());

    expect(mapProps.markers).toEqual([
      {
        latitude: 51.47,
        longitude: -0.4543,
        label: 'Origin: London',
      },
      {
        latitude: 40.6413,
        longitude: -73.7781,
        label: 'Destination: New York',
      },
    ]);
    expect(mapProps.routePath).toEqual([
      { latitude: 51.47, longitude: -0.4543 },
      { latitude: 40.6413, longitude: -73.7781 },
    ]);
    expect(mapProps.zoomLevel).toBe(4);
  });

  it('pins the searched city when backend resolves an alternative nearby airport', () => {
    // User searched Amsterdam→Barcelona; backend returned cheapest from RTM (Rotterdam).
    // origin='Rotterdam', origin_city='Amsterdam' — map must show Amsterdam.
    const data = makeFlightSearchData();
    data.data.search_params.origin = 'Rotterdam';
    data.data.search_params.origin_city = 'Amsterdam';
    // Backend sets origin_location to Rotterdam coordinates.
    data.origin_location = { latitude: 51.9244, longitude: 4.4777 };

    const mapProps = getFlightRecommendationsMapProps(data);

    // Pin label shows searched city, not alternative airport.
    expect(mapProps.markers[0]?.label).toBe('Origin: Amsterdam');
    // Pin position uses Amsterdam coords (from fallback table), not Rotterdam.
    expect(mapProps.markers[0]?.latitude).toBeCloseTo(52.3676);
    expect(mapProps.markers[0]?.longitude).toBeCloseTo(4.9041);
  });

  it('pins the searched city when backend resolves an alternative nearby airport (destination)', () => {
    // User searched Barcelona; backend returned cheapest from GRO (Girona).
    // destination='Girona', destination_city='Barcelona' — map must show Barcelona.
    const data = makeFlightSearchData();
    data.data.search_params.destination = 'Girona';
    data.data.search_params.destination_city = 'Barcelona';
    // Backend sets destination_location to Girona coordinates.
    data.destination_location = { latitude: 41.9003, longitude: 2.7604 };

    const mapProps = getFlightRecommendationsMapProps(data);

    // Pin label shows searched city, not alternative airport.
    expect(mapProps.markers[1]?.label).toBe('Destination: Barcelona');
    // Pin position uses Barcelona coords (from fallback table), not Girona.
    expect(mapProps.markers[1]?.latitude).toBeCloseTo(41.3851);
    expect(mapProps.markers[1]?.longitude).toBeCloseTo(2.1734);
  });

  it('returns the default empty map when no search data is available', () => {
    const mapProps = getFlightRecommendationsMapProps(null);

    expect(mapProps).toEqual({
      centerLatitude: 34.0522,
      centerLongitude: -118.2437,
      zoomLevel: 10,
      markers: [],
    });
  });
});

describe('getFlightSearchPageMapProps', () => {
  it('resolves known IATA codes to markers and draws a route', () => {
    const mapProps = getFlightSearchPageMapProps({
      from: 'Amsterdam',
      to: 'Barcelona',
      fromIata: 'AMS',
      toIata: 'BCN',
    });

    expect(mapProps.markers).toEqual([
      { latitude: 52.3676, longitude: 4.9041, label: 'Origin: Amsterdam' },
      { latitude: 41.3851, longitude: 2.1734, label: 'Destination: Barcelona' },
    ]);
    expect(mapProps.routePath).toEqual([
      { latitude: 52.3676, longitude: 4.9041 },
      { latitude: 41.3851, longitude: 2.1734 },
    ]);
    expect(mapProps.zoomLevel).toBe(4);
  });

  it('falls back to city name lookup when IATA code is not in the table', () => {
    const mapProps = getFlightSearchPageMapProps({
      from: 'London',
      to: 'Dubai',
    });

    expect(mapProps.markers[0]?.label).toBe('Origin: London');
    expect(mapProps.markers[0]?.latitude).toBeCloseTo(51.5074);
    expect(mapProps.markers[1]?.label).toBe('Destination: Dubai');
    expect(mapProps.markers[1]?.latitude).toBeCloseTo(25.2048);
    expect(mapProps.routePath).toHaveLength(2);
  });

  it('prefers IATA lookup over city-name fallback', () => {
    // fromIata='LHR' matches the table; city 'London' also matches — IATA wins (checked first)
    const mapProps = getFlightSearchPageMapProps({
      from: 'London',
      to: 'Paris',
      fromIata: 'LHR',
      toIata: 'CDG',
    });

    expect(mapProps.markers[0]?.latitude).toBeCloseTo(51.47); // LHR, not London city centre
    expect(mapProps.markers[1]?.latitude).toBeCloseTo(48.8566); // CDG / Paris
  });

  it('omits a marker and route when a location cannot be resolved', () => {
    const mapProps = getFlightSearchPageMapProps({
      from: 'Unknown City XYZ',
      to: 'Barcelona',
      toIata: 'BCN',
    });

    expect(mapProps.markers).toHaveLength(1);
    expect(mapProps.markers[0]?.label).toBe('Destination: Barcelona');
    expect(mapProps.routePath).toBeUndefined();
  });

  it('returns default center with no markers when both locations are unknown', () => {
    const mapProps = getFlightSearchPageMapProps({
      from: 'Nowhere A',
      to: 'Nowhere B',
    });

    expect(mapProps.markers).toHaveLength(0);
    expect(mapProps.routePath).toBeUndefined();
    expect(mapProps.centerLatitude).toBe(34.0522);
    expect(mapProps.centerLongitude).toBe(-118.2437);
    expect(mapProps.zoomLevel).toBe(10);
  });

  it('centers the map on the single resolved marker when only one location is known', () => {
    const mapProps = getFlightSearchPageMapProps({
      from: 'Amsterdam',
      to: 'Unknown City XYZ',
      fromIata: 'AMS',
    });

    expect(mapProps.markers).toHaveLength(1);
    expect(mapProps.centerLatitude).toBeCloseTo(52.3676);
    expect(mapProps.centerLongitude).toBeCloseTo(4.9041);
    expect(mapProps.zoomLevel).toBe(10);
  });

  it('coordinateOverrides win over IATA and city-name fallbacks', () => {
    const overrides = {
      origin: { latitude: 1.0, longitude: 2.0 },
      destination: { latitude: 3.0, longitude: 4.0 },
    };
    const mapProps = getFlightSearchPageMapProps(
      { from: 'Amsterdam', to: 'Barcelona', fromIata: 'AMS', toIata: 'BCN' },
      overrides
    );

    expect(mapProps.markers[0]?.latitude).toBe(1.0);
    expect(mapProps.markers[0]?.longitude).toBe(2.0);
    expect(mapProps.markers[1]?.latitude).toBe(3.0);
    expect(mapProps.markers[1]?.longitude).toBe(4.0);
    expect(mapProps.routePath).toEqual([
      { latitude: 1.0, longitude: 2.0 },
      { latitude: 3.0, longitude: 4.0 },
    ]);
  });
});

describe('getItineraryMapOverrideFromTripMeta', () => {
  const destCoords = { latitude: 41.3851, longitude: 2.1734 };
  const originCoords = { latitude: 52.3676, longitude: 4.9041 };

  it('returns null when tripMeta is null/undefined', () => {
    expect(
      getItineraryMapOverrideFromTripMeta(null, { from: 'Amsterdam', to: 'Barcelona' })
    ).toBeNull();
    expect(
      getItineraryMapOverrideFromTripMeta(undefined, { from: 'Amsterdam', to: 'Barcelona' })
    ).toBeNull();
  });

  it('emits destination override when tripMeta.destination matches nav-bar to (case-insensitive)', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona', destination_location: destCoords },
      { from: 'Amsterdam', to: 'BARCELONA' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('reads camelCase destinationLocation as well as snake_case', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona', destinationLocation: destCoords },
      { from: '', to: 'Barcelona' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('drops destination override when nav-bar destination has been edited away (stale guard)', () => {
    // User loaded an itinerary to Barcelona, then changed the nav-bar to Paris
    // before searching. The Barcelona pin must NOT be seeded.
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona', destination_location: destCoords },
      { from: 'Amsterdam', to: 'Paris' }
    );
    expect(result).toBeNull();
  });

  it('emits origin override only when tripMeta.origin matches nav-bar from', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      {
        origin: 'Amsterdam',
        destination: 'Barcelona',
        origin_location: originCoords,
        destination_location: destCoords,
      },
      { from: 'amsterdam', to: 'Barcelona' }
    );
    expect(result).toEqual({ origin: originCoords, destination: destCoords });
  });

  it('emits only the side that matches when one side is stale', () => {
    // Destination still matches, origin was edited — only destination should pin.
    const result = getItineraryMapOverrideFromTripMeta(
      {
        origin: 'Amsterdam',
        destination: 'Barcelona',
        origin_location: originCoords,
        destination_location: destCoords,
      },
      { from: 'Paris', to: 'Barcelona' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('returns null when tripMeta has no coords at all', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona' },
      { from: '', to: 'Barcelona' }
    );
    expect(result).toBeNull();
  });

  it('returns null when current nav-bar destination is empty', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona', destination_location: destCoords },
      { from: 'Amsterdam', to: '' }
    );
    expect(result).toBeNull();
  });

  it('trims whitespace before matching', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: '  Barcelona  ', destination_location: destCoords },
      { from: '', to: 'barcelona' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('matches when tripMeta destination has country suffix but nav-bar does not', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona, Spain', destination_location: destCoords },
      { from: '', to: 'Barcelona' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('matches when nav-bar destination has country suffix but tripMeta does not', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona', destination_location: destCoords },
      { from: '', to: 'Barcelona, Spain' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('matches via IATA fallback when nav-bar string differs from tripMeta city', () => {
    // tripMeta stores IATA, nav-bar shows city name — match via toIata.
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'BCN', destination_location: destCoords },
      { from: '', to: 'Barcelona', toIata: 'BCN' }
    );
    expect(result).toEqual({ destination: destCoords });
  });

  it('still drops override when neither string nor IATA match', () => {
    const result = getItineraryMapOverrideFromTripMeta(
      { destination: 'Barcelona, Spain', destination_location: destCoords },
      { from: '', to: 'Paris, France', toIata: 'CDG' }
    );
    expect(result).toBeNull();
  });
});
