import { describe, expect, it } from 'vitest';

import type { HotelItinerary, RoomRate } from '@/types/hotels';

import {
  amenityStringsToColumns,
  buildGalleryImageList,
  buildRoomsAndGuestsLabel,
  buildStayPriceRangeLabel,
  getHotelDisplayName,
  hotelSearchFacilityLabels,
} from './hotelDetailDisplayUtils';

describe('buildGalleryImageList', () => {
  it('dedupes identical URLs after resolve (hotel images)', () => {
    const hotel = {
      images: ['https://cdn.example/h1.jpg', 'https://cdn.example/h1.jpg'],
    } as HotelItinerary;
    expect(buildGalleryImageList(hotel)).toEqual(['https://cdn.example/h1.jpg']);
  });

  it('dedupes thumbnail when same as first gallery image', () => {
    const hotel = {
      images: ['https://cdn.example/h1.jpg'],
      thumbnailUrl: 'https://cdn.example/h1.jpg',
    } as HotelItinerary;
    expect(buildGalleryImageList(hotel)).toEqual(['https://cdn.example/h1.jpg']);
  });

  it('appends unique room images after hotel images', () => {
    const hotel = { images: ['https://cdn.example/h1.jpg'] } as HotelItinerary;
    const rooms: RoomRate[] = [
      { rateBasisId: 'a', images: ['https://cdn.example/r1.jpg'] },
      { rateBasisId: 'b', images: ['https://cdn.example/r2.jpg'] },
    ];
    expect(buildGalleryImageList(hotel, rooms)).toEqual([
      'https://cdn.example/h1.jpg',
      'https://cdn.example/r1.jpg',
      'https://cdn.example/r2.jpg',
    ]);
  });

  it('dedupes room image that matches a hotel image', () => {
    const hotel = { images: ['https://cdn.example/same.jpg'] } as HotelItinerary;
    const rooms: RoomRate[] = [{ rateBasisId: 'a', images: ['https://cdn.example/same.jpg'] }];
    expect(buildGalleryImageList(hotel, rooms)).toEqual(['https://cdn.example/same.jpg']);
  });

  it('returns empty array when nothing resolvable', () => {
    expect(buildGalleryImageList(undefined, [])).toEqual([]);
  });
});

describe('hotelSearchFacilityLabels', () => {
  it('uses facilities from search response when present', () => {
    const hotel = {
      facilities: ['Wi-fi', 'Pool'],
      amenities: ['Legacy'],
    } as HotelItinerary;
    expect(hotelSearchFacilityLabels(hotel)).toEqual(['Wi-fi', 'Pool']);
  });

  it('falls back to amenities when facilities missing or empty', () => {
    expect(
      hotelSearchFacilityLabels({ facilities: [], amenities: ['Bar'] } as unknown as HotelItinerary),
    ).toEqual(['Bar']);
    expect(hotelSearchFacilityLabels({ amenities: ['Spa'] } as HotelItinerary)).toEqual(['Spa']);
  });

  it('returns empty for undefined hotel or no lists', () => {
    expect(hotelSearchFacilityLabels(undefined)).toEqual([]);
    expect(hotelSearchFacilityLabels({} as HotelItinerary)).toEqual([]);
  });
});

describe('buildRoomsAndGuestsLabel', () => {
  it('returns em dash for empty occupancy', () => {
    expect(buildRoomsAndGuestsLabel([])).toBe('—');
  });

  it('formats single room with adults only', () => {
    expect(buildRoomsAndGuestsLabel([{ roomNo: 1, adult: 2, child: 0 }])).toBe('1 room · 2 adults');
  });

  it('pluralizes rooms and includes children when present', () => {
    expect(
      buildRoomsAndGuestsLabel([
        { roomNo: 1, adult: 1, child: 1 },
        { roomNo: 2, adult: 2, child: 0 },
      ]),
    ).toBe('2 rooms · 3 adults · 1 child');
  });
});

describe('amenityStringsToColumns', () => {
  it('returns empty columns for empty labels', () => {
    expect(amenityStringsToColumns([])).toEqual({ columnOne: [], columnTwo: [] });
  });

  it('splits items into two columns with stable unique ids (duplicate labels ok)', () => {
    const { columnOne, columnTwo } = amenityStringsToColumns(['Pool', 'Wi‑fi', 'Pool']);
    expect(columnOne).toHaveLength(2);
    expect(columnTwo).toHaveLength(1);
    const ids = [...columnOne, ...columnTwo].map((i) => i.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(columnOne[0]?.label).toBe('Pool');
    expect(columnOne[1]?.label).toBe('Wi‑fi');
    expect(columnTwo[0]?.label).toBe('Pool');
  });
});

describe('buildStayPriceRangeLabel', () => {
  it('single room: shows that room total', () => {
    const rooms: RoomRate[] = [{ rateBasisId: '1', totalPrice: 450, currency: 'USD' }];
    expect(buildStayPriceRangeLabel(rooms, 3)).toMatch(/\$450/);
    expect(buildStayPriceRangeLabel(rooms, 3)).not.toMatch(/–/);
  });

  it('multiple rooms with different totals: shows min – max', () => {
    const rooms: RoomRate[] = [
      { rateBasisId: 'a', totalPrice: 200, currency: 'USD' },
      { rateBasisId: 'b', totalPrice: 500, currency: 'USD' },
    ];
    const label = buildStayPriceRangeLabel(rooms, 2);
    expect(label).toContain('–');
    expect(label).toMatch(/\$200/);
    expect(label).toMatch(/\$500/);
  });

  it('multiple rooms with same total: single formatted price', () => {
    const rooms: RoomRate[] = [
      { rateBasisId: 'a', totalPrice: 300, currency: 'EUR' },
      { rateBasisId: 'b', totalPrice: 300, currency: 'EUR' },
    ];
    const label = buildStayPriceRangeLabel(rooms, 1);
    expect(label).not.toContain('–');
    expect(label).toMatch(/300/);
  });

  it('single room with string totalPrice (API decimal JSON): shows formatted price', () => {
    const rooms = [{ rateBasisId: '1', totalPrice: '450.5', currency: 'USD' }] as unknown as RoomRate[];
    const label = buildStayPriceRangeLabel(rooms, 2);
    expect(label).not.toBe('—');
    expect(label).toMatch(/450/);
  });

  it('multiple rooms with different currencies: fallback label (no mixed-currency range)', () => {
    const rooms: RoomRate[] = [
      { rateBasisId: 'a', totalPrice: 200, currency: 'USD' },
      { rateBasisId: 'b', totalPrice: 200, currency: 'EUR' },
    ];
    expect(buildStayPriceRangeLabel(rooms, 2)).toBe('See room options');
  });
});

describe('getHotelDisplayName', () => {
  it('prefers name over hotelName', () => {
    expect(getHotelDisplayName({ name: ' A ', hotelName: 'B' })).toBe('A');
  });

  it('uses hotelName when name is empty', () => {
    expect(getHotelDisplayName({ name: '', hotelName: 'Alt' })).toBe('Alt');
  });

  it('returns fallback for null or empty fields', () => {
    expect(getHotelDisplayName(null)).toBe('Hotel');
    expect(getHotelDisplayName({ name: '   ' }, 'X')).toBe('X');
  });
});
