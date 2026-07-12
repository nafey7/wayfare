import { describe, expect, it } from 'vitest';
import { getHotelSearchPageMapProps } from './hotelMapLocation';

describe('getHotelSearchPageMapProps', () => {
  it('returns correct center and zoom for a known city (London)', () => {
    const props = getHotelSearchPageMapProps('London');
    expect(props).not.toBeNull();
    expect(props!.centerLatitude).toBeCloseTo(51.5074);
    expect(props!.centerLongitude).toBeCloseTo(-0.1278);
    expect(props!.zoomLevel).toBe(12);
    expect(props!.markers).toHaveLength(1);
    expect(props!.markers[0]!.label).toBe('London');
  });

  it('is case-insensitive (lowercase city name)', () => {
    const props = getHotelSearchPageMapProps('london');
    expect(props).not.toBeNull();
    expect(props!.centerLatitude).toBeCloseTo(51.5074);
  });

  it('returns correct props for Paris', () => {
    const props = getHotelSearchPageMapProps('Paris');
    expect(props).not.toBeNull();
    expect(props!.centerLatitude).toBeCloseTo(48.8566);
    expect(props!.centerLongitude).toBeCloseTo(2.3522);
  });

  it('returns null for an unknown city', () => {
    expect(getHotelSearchPageMapProps('XYZ Unknown City 12345')).toBeNull();
  });

  it('returns null for null input', () => {
    expect(getHotelSearchPageMapProps(null)).toBeNull();
  });

  it('returns null for undefined input', () => {
    expect(getHotelSearchPageMapProps(undefined)).toBeNull();
  });
});
