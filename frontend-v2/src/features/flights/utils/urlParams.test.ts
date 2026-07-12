import { describe, it, expect, vi } from 'vitest';
import {
  serializeSearchParamsToUrl,
  deserializeSearchParamsFromUrl,
  convertUIToFormParams,
  convertFormParamsToUI,
  serializeChatFiltersToUrl,
  deserializeChatFiltersFromUrl,
} from './urlParams';
import type { ChatFlightFilters } from '@/features/chat/utils/chatSearchParamsToUI';
import type { FlightSearchParamsUI } from '@/types/flights';
import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';

const sampleUI: FlightSearchParamsUI = {
  tripType: 'round-trip',
  from: 'LHR',
  to: 'JFK',
  date: new Date('2026-03-15'),
  returnDate: new Date('2026-03-22'),
  travellers: {
    adults: 2,
    children: 1,
    infants: 0,
    cabinClass: 'Economy',
  },
};

const sampleForm: FlightSearchFormParams = {
  tripType: 'round-trip',
  from: 'LHR',
  to: 'JFK',
  date: '2026-03-15T00:00:00.000Z',
  returnDate: '2026-03-22T00:00:00.000Z',
  travellers: {
    adults: 2,
    children: 1,
    infants: 0,
    cabinClass: 'Economy',
  },
};

describe('urlParams', () => {
  describe('serializeSearchParamsToUrl', () => {
    it('returns base64-encoded JSON', () => {
      const encoded = serializeSearchParamsToUrl(sampleUI);
      expect(encoded).toBeTruthy();
      expect(() => atob(encoded)).not.toThrow();
      const decoded = JSON.parse(atob(encoded));
      expect(decoded.tripType).toBe('round-trip');
      expect(decoded.from).toBe('LHR');
      expect(decoded.to).toBe('JFK');
      expect(decoded.travellers.adults).toBe(2);
    });

    it('converts Date to ISO string in serialized output', () => {
      const encoded = serializeSearchParamsToUrl(sampleUI);
      const decoded = JSON.parse(atob(encoded));
      expect(decoded.date).toMatch(/^\d{4}-\d{2}-\d{2}/);
      expect(decoded.returnDate).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });

    it('handles null date and returnDate', () => {
      const ui: FlightSearchParamsUI = {
        ...sampleUI,
        date: null,
        returnDate: null,
      };
      const encoded = serializeSearchParamsToUrl(ui);
      const decoded = JSON.parse(atob(encoded));
      expect(decoded.date).toBeNull();
      expect(decoded.returnDate).toBeNull();
    });

    it('returns empty string on serialization error', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const bad = {
        ...sampleUI,
        get date() {
          throw new Error('serialization error');
        },
      } as unknown as FlightSearchParamsUI;
      const encoded = serializeSearchParamsToUrl(bad);
      expect(encoded).toBe('');
      consoleSpy.mockRestore();
    });
  });

  describe('deserializeSearchParamsFromUrl', () => {
    it('decodes base64 and parses to FlightSearchParamsUI with Date objects', () => {
      const encoded = serializeSearchParamsToUrl(sampleUI);
      const result = deserializeSearchParamsFromUrl(encoded);
      expect(result).not.toBeNull();
      expect(result!.tripType).toBe('round-trip');
      expect(result!.from).toBe('LHR');
      expect(result!.to).toBe('JFK');
      expect(result!.date).toBeInstanceOf(Date);
      expect(result!.date!.toISOString()).toMatch(/2026-03-15/);
      expect(result!.returnDate).toBeInstanceOf(Date);
      expect(result!.travellers.adults).toBe(2);
    });

    it('returns null for invalid base64', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const result = deserializeSearchParamsFromUrl('not-valid-base64!!!');
      expect(result).toBeNull();
      consoleSpy.mockRestore();
    });

    it('returns null for invalid JSON inside base64', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const result = deserializeSearchParamsFromUrl(btoa('{ invalid json'));
      expect(result).toBeNull();
      consoleSpy.mockRestore();
    });

    it('handles segments when present', () => {
      const uiWithSegments: FlightSearchParamsUI = {
        ...sampleUI,
        tripType: 'multi-city',
        segments: [
          { from: 'LHR', to: 'JFK', date: new Date('2026-03-15') },
          { from: 'JFK', to: 'LHR', date: new Date('2026-03-22') },
        ],
      };
      const encoded = serializeSearchParamsToUrl(uiWithSegments);
      const result = deserializeSearchParamsFromUrl(encoded);
      expect(result!.segments).toHaveLength(2);
      expect(result!.segments![0]!.from).toBe('LHR');
      expect(result!.segments![0]!.date).toBeInstanceOf(Date);
    });
  });

  describe('convertUIToFormParams', () => {
    it('converts Date to ISO string', () => {
      const form = convertUIToFormParams(sampleUI);
      expect(form.date).toBe(sampleUI.date!.toISOString());
      expect(form.returnDate).toBe(sampleUI.returnDate!.toISOString());
    });
    it('preserves tripType, from, to, travellers', () => {
      const form = convertUIToFormParams(sampleUI);
      expect(form.tripType).toBe(sampleUI.tripType);
      expect(form.from).toBe(sampleUI.from);
      expect(form.to).toBe(sampleUI.to);
      expect(form.travellers).toEqual(sampleUI.travellers);
    });
  });

  describe('convertFormParamsToUI', () => {
    it('converts ISO string to Date', () => {
      const ui = convertFormParamsToUI(sampleForm);
      expect(ui.date).toBeInstanceOf(Date);
      expect(ui.date!.toISOString()).toBe(sampleForm.date);
      expect(ui.returnDate).toBeInstanceOf(Date);
    });
    it('preserves tripType, from, to, travellers', () => {
      const ui = convertFormParamsToUI(sampleForm);
      expect(ui.tripType).toBe(sampleForm.tripType);
      expect(ui.from).toBe(sampleForm.from);
      expect(ui.to).toBe(sampleForm.to);
      expect(ui.travellers).toEqual(sampleForm.travellers);
    });
  });

  describe('round-trip', () => {
    it('serialize -> deserialize preserves data', () => {
      const encoded = serializeSearchParamsToUrl(sampleUI);
      const decoded = deserializeSearchParamsFromUrl(encoded);
      expect(decoded).not.toBeNull();
      expect(decoded!.tripType).toBe(sampleUI.tripType);
      expect(decoded!.from).toBe(sampleUI.from);
      expect(decoded!.to).toBe(sampleUI.to);
      expect(decoded!.travellers.adults).toBe(sampleUI.travellers.adults);
      expect(decoded!.date!.getTime()).toBe(sampleUI.date!.getTime());
      expect(decoded!.returnDate!.getTime()).toBe(sampleUI.returnDate!.getTime());
    });

    it('convertUIToFormParams -> convertFormParamsToUI preserves data', () => {
      const form = convertUIToFormParams(sampleUI);
      const back = convertFormParamsToUI(form);
      expect(back.tripType).toBe(sampleUI.tripType);
      expect(back.date!.getTime()).toBe(sampleUI.date!.getTime());
      expect(back.returnDate!.getTime()).toBe(sampleUI.returnDate!.getTime());
    });
  });

  describe('serializeChatFiltersToUrl / deserializeChatFiltersFromUrl', () => {
    const sampleFilters: ChatFlightFilters = {
      priceMin: 100,
      priceMax: 500,
      directOnly: true,
      airlines: ['BA'],
      outboundDurationMax: 600,
      inboundDurationMax: null,
    };

    it('round-trips chat filters through serialize/deserialize', () => {
      const encoded = serializeChatFiltersToUrl(sampleFilters);
      expect(encoded).toBeTruthy();
      const decoded = deserializeChatFiltersFromUrl(encoded);
      expect(decoded).not.toBeNull();
      expect(decoded!.priceMin).toBe(100);
      expect(decoded!.priceMax).toBe(500);
      expect(decoded!.directOnly).toBe(true);
      expect(decoded!.airlines).toEqual(['BA']);
      expect(decoded!.outboundDurationMax).toBe(600);
      expect(decoded!.inboundDurationMax).toBeNull();
    });

    it('handles empty/null filter values', () => {
      const emptyFilters: ChatFlightFilters = {
        priceMin: null,
        priceMax: null,
        directOnly: false,
        airlines: [],
        outboundDurationMax: null,
        inboundDurationMax: null,
      };
      const encoded = serializeChatFiltersToUrl(emptyFilters);
      const decoded = deserializeChatFiltersFromUrl(encoded);
      expect(decoded).not.toBeNull();
      expect(decoded!.priceMin).toBeNull();
      expect(decoded!.priceMax).toBeNull();
      expect(decoded!.directOnly).toBe(false);
      expect(decoded!.airlines).toEqual([]);
    });

    it('returns null for invalid base64', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      expect(deserializeChatFiltersFromUrl('not-valid!!!')).toBeNull();
      consoleSpy.mockRestore();
    });

    it('returns null for invalid JSON inside base64', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      expect(deserializeChatFiltersFromUrl(btoa('{ invalid json'))).toBeNull();
      consoleSpy.mockRestore();
    });

    it('defaults missing fields in deserialized filters', () => {
      const partial = btoa(JSON.stringify({ priceMax: 300 }));
      const decoded = deserializeChatFiltersFromUrl(partial);
      expect(decoded).not.toBeNull();
      expect(decoded!.priceMax).toBe(300);
      expect(decoded!.priceMin).toBeNull();
      expect(decoded!.directOnly).toBe(false);
      expect(decoded!.airlines).toEqual([]);
      expect(decoded!.outboundDurationMax).toBeNull();
      expect(decoded!.inboundDurationMax).toBeNull();
    });
  });
});
